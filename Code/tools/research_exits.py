"""기존 장기 연구의 진입 규칙 선택을 고정하고 매도 보호 조건만 비교한다.

실행: python main.py --test exits. 이미 수집한 실제 일봉만 사용하며 주문하지 않는다.
결과를 보고 활성화 수익·보호 비율을 최적화하지 않는다. 같은 과거의 탐색 비교다.
"""
import copy
import hashlib
import json
import os
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from paths import PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT
from research.daily import prepare_daily_bars
from research.history import write_json
from research.portfolio import replay_selected_rules, stress_recorded_trades
from strategy.exits import PROFIT_EXIT_DEFAULTS


def main():
    pointer = RESULTS_ROOT / "long-history/latest.json"
    if not pointer.exists():
        raise ValueError("먼저 python main.py --test long-history로 장기 자료를 생성하세요.")
    original_folder = Path(json.loads(pointer.read_text(encoding="utf-8"))["folder"])
    original = json.loads((original_folder / "results.json").read_text(encoding="utf-8"))
    costs = original["costs"]
    declaration = json.loads((original_folder / "declaration.json").read_text(encoding="utf-8"))
    spread = declaration["spread"]
    policies = {"baseline": None,
                "breakeven": {**PROFIT_EXIT_DEFAULTS, "profit_lock_trigger": 0},
                "profit_lock": {**PROFIT_EXIT_DEFAULTS, "breakeven_trigger": 0},
                "combined": dict(PROFIT_EXIT_DEFAULTS)}
    folder = RESULTS_ROOT / "exits" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True)
    write_json(folder / "declaration.json", {"policies": policies, "original_folder": str(original_folder),
               "costs": costs, "spread": spread, "purpose": "frozen_entry_selection_exit_comparison"})
    source_folder = folder / "source"
    source_folder.mkdir()
    for relative_path in ("strategy/exits.py", "research/portfolio.py", "tools/research_exits.py"):
        shutil.copy2(PROJECT_ROOT / relative_path, source_folder)
    outcomes, source_hashes = {}, {}
    stressed = {**costs, **{name: costs[name] * 2 for name in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
    for cohort_name, cohort in original["cohorts"].items():
        for market, previous in cohort["markets"].items():
            series = {}
            for symbol in previous["symbols"]:
                path = DATA_ROOT / "history/long-adjusted" / (symbol.replace(":", "-") + "-" + original["settings"]["test_end"][:10] + ".json")
                raw = path.read_bytes()
                record = json.loads(raw)
                if (record.get("origin") != "toss_actual_historical_candles" or record.get("adjusted") is not True
                        or not record.get("collection_complete") or record.get("interval") != "1d"
                        or record.get("market") + ":" + record.get("symbol") != symbol):
                    raise ValueError("출처·수정주가·완료 여부가 확인된 실제 캐시만 비교합니다.")
                source_hashes[symbol] = hashlib.sha256(raw).hexdigest()
                series[symbol] = prepare_daily_bars(record)
            key = cohort_name + "-" + market
            outcomes[key] = {}
            for name, policy in policies.items():
                # 과거에 선택됐던 진입 가설·선택 날짜·현금 대기 구간을 그대로 사용한다.
                selections = [{**selection, "trials": []} for selection in previous["test"]["selections"]]
                selections = copy.deepcopy(selections)
                if policy:
                    for selection in selections:
                        if selection["selected"]:
                            selection["selected"]["rule"]["profit_exits"] = policy
                result = replay_selected_rules(series, market, costs, spread, selections)
                if name == "baseline" and (result["curve"] != previous["test"]["curve"] or result["trades"] != previous["test"]["trades"]):
                    raise AssertionError("기준 재현이 기존 장기 결과와 다릅니다. 비교를 중단합니다.")
                result["double_cost"] = stress_recorded_trades(result["trades"], costs["starting_cash"][market], costs, stressed, spread, spread * 2)
                result["exit_reasons"] = dict(Counter(trade["reason"] for trade in result["trades"]))
                losses = [trade for trade in result["trades"] if trade["pnl"] < 0]
                result["loss_trades"] = len(losses)
                result["gross_loss"] = sum(trade["pnl"] for trade in losses)
                outcomes[key][name] = result
                print(f"{key} {name}: 수익 {result['summary']['net_return']:.2%}, 낙폭 {result['summary']['max_drawdown']:.2%}, 손실 거래 {len(losses)}", flush=True)
    write_json(folder / "results.json", {"markets": outcomes, "source_hashes": source_hashes})
    write_report(folder, outcomes)
    plot_comparison(folder, outcomes, costs)
    write_json(folder.parent / "latest.json", {"folder": str(folder)})
    print(f"매도 비교 보고서: {folder / 'report.md'}")


def write_report(folder, outcomes):
    periods = [f"- {key}: {variants['baseline']['curve'][0]['date']}~{variants['baseline']['curve'][-1]['date']}"
               for key, variants in outcomes.items()]
    lines = ["# 매도 보호 조건 비교", "", "실제 토스 수정주가 일봉, 가상 체결·비용 포함. 실거래 수익이 아니다.",
             "기존 장기 연구의 진입 규칙 선택을 고정했다. 재선정 없이 매도 조건만 추가했다.",
             "기준 4개 구간의 계좌 곡선·거래 기록을 이전 결과와 완전히 일치시키는 재현 검사를 통과했다.",
             "", *periods,
             "", "- breakeven: 비용 차감 고점 수익 3%부터 순이익 0.2%에 해당하는 매도 기준 활성화.",
             "- profit_lock: 비용 차감 고점 수익 5%부터 고점 순이익의 50% 보호.",
             "- combined: 두 조건 중 더 높은 가격, 기존 손절·추적 손절과도 더 높은 가격 사용.",
             "- 오늘 고가는 다음 날부터 보호 기준에 반영. 갭 하락은 기준가보다 낮은 시가 체결 후 비용 차감.",
             "", "| 기간·시장 | 매도 조건 | 수익률 | 비용 2배 | 최대 낙폭 | 거래 | 손실 거래 | 보호 매도 |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for key, variants in outcomes.items():
        for name, result in variants.items():
            summary = result["summary"]
            protected = sum(result["exit_reasons"].get(reason, 0) for reason in ("breakeven_protection", "profit_lock"))
            lines.append(f"| {key} | {name} | {summary['net_return']:.2%} | {result['double_cost']['net_return']:.2%} | {summary['max_drawdown']:.2%} | {summary['trades']} | {result['loss_trades']} | {protected} |")
    lines.extend(["", "![매도 조건별 계좌 수익 비교](comparison.png)", "", "## 판정과 적용 범위", "",
                  "| 기간·시장 | 결합 조건 수익 개선 | 낙폭 감소 | 비용 2배 양수 |", "| --- | --- | --- | --- |"])
    for key, variants in outcomes.items():
        base, combined = variants["baseline"]["summary"], variants["combined"]["summary"]
        checks = [combined["net_return"] > base["net_return"], combined["max_drawdown"] < base["max_drawdown"], variants["combined"]["double_cost"]["net_return"] > 0]
        lines.append(f"| {key} | {' | '.join('통과' if passed else '실패' for passed in checks)} |")
    lines.extend(["", "- 손실 발생 전 매도를 보장하지 않는다. 보호는 먼저 수익이 난 포지션에서만 켜진다. 매수 직후 하락에는 기존 손절이 작동한다.",
                  "- 실제 장중 엔진은 유효한 현재 매수 호가로 판단하며 기본 60초마다 조회한다. 보호 기준은 거래소에 제출한 예약 손절 주문이 아니다.",
                  "- 일봉 연구의 기존 손절 폭·진입 조건은 장중 엔진과 다르다. 장중 수익성으로 해석할 수 없다.",
                  "- 동일 과거를 반복 사용한 탐색이다. 독립 검증·실거래 체결·수익성은 미검증. 장기 종목 선정·수정주가 한계는 원본 보고서와 같다.",
                  "- 손실 거래 수는 총 거래 수와 함께 본다. 보호 매도 후 이후 진입·수량은 달라질 수 있다. 비용 2배는 각 변형의 거래 날짜·수량을 고정한 비용 민감도다.",
                  "- 기능은 장중 모의 엔진에 추가했다. 연구 후보·엄격 선택 기준을 변경하지 않았으며, 과거 결과를 보고 매도 임계값을 다시 조정하지 않았다."])
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_comparison(folder, outcomes, costs):
    # 결과 폴더에 캐시를 두어 사용자 홈 접근 권한과 관계없이 그래프를 생성한다.
    os.environ["MPLCONFIGDIR"] = str(folder / "plot-cache")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(2, 2, figsize=(13, 8))
    for axis, (key, variants) in zip(axes.flat, outcomes.items()):
        starting = costs["starting_cash"][key.split("-")[-1]]
        for name, result in variants.items():
            axis.plot([datetime.fromisoformat(row["date"]) for row in result["curve"]],
                      [100 * (row["equity"] / starting - 1) for row in result["curve"]], label=name)
        baseline_curve = variants["baseline"]["curve"]
        axis.set_title(f"{key}: {baseline_curve[0]['date']} to {baseline_curve[-1]['date']}")
        axis.set_ylabel("Simulated account return (%)")
        axis.grid(alpha=.25)
        axis.legend(fontsize=8)
        axis.tick_params(axis="x", labelrotation=30)
    figure.suptitle("Exit protection comparison - frozen entry selection, simulated fills")
    figure.tight_layout()
    figure.savefig(folder / "comparison.png", dpi=150)
    plt.close(figure)


if __name__ == "__main__":
    main()
