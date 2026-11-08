"""실제 과거 시세로 제한된 규칙 후보를 비교하고 보고서·그래프를 저장한다."""
import hashlib
import json
import shutil
from datetime import datetime, timezone

from app.runtime import acquire_run_lock, load_run_settings, release_run_lock
from paths import PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT, CONFIG_ROOT
from research.backtest import compare_rules, validate_costs
from research.history import load_research_settings, prepare_sessions, write_json


def write_report(folder, report):
    lines = ["# 실제 과거 분봉 연구 결과", "", "뉴스가 없는 가격·거래량 연구이며 기존 실시간 뉴스 전략의 수익률이 아니다.",
             "후보 24개/종목: 훈련 60% → 상위 3개 검증 20% → 고정한 1개 최종 시험 20%.",
             f"다음 5분봉 시가 체결, 정수 수량, 초기 자금의 {report['costs']['allocation_fraction']:.1%} 투자, 당일 청산 또는 최대 5세션 보유. KRW/USD는 합산하지 않는다.", "",
             "| 종목 | 훈련/검증/시험 세션 | 시험 순수익률 | 단순 보유 | 최대 낙폭 | 완료 거래 | 판정 |",
             "| --- | --- | ---: | ---: | ---: | ---: | --- |"]
    if report["holdout_reused"]:
        lines.insert(2, "**현재 결과는 이미 사용한 시험 기간의 탐색 계산이다. 독립 수익성 검증 통과로 사용할 수 없다.**\n")
    for key, result in report["results"].items():
        summary = result["test"]["summary"]
        counts = "/".join(str(result["periods"][part]["sessions"]) for part in ("training", "validation", "test"))
        lines.append(f"| {key} | {counts} | {summary['net_return']:.4%} | {result['buy_and_hold_test_return']:.4%} | {summary['max_drawdown']:.4%} | {summary['trades']} | {result['verdict']} |")
    lines.extend(["", "## 조건과 근거", "", f"비용 설정: `{json.dumps(report['costs'], ensure_ascii=False)}`",
                  f"가정 스프레드: {report['settings']['assumed_spread_ratio']:.3%}. 비용·슬리피지·스프레드 2배도 시험한다.",
                  "수익률은 미투자 현금을 포함한 시장별 가상 계좌 기준이다. 단순 보유도 같은 투자 비중·비용을 쓴다.",
                  "실제 과거 분봉 출처: [토스 공식 시세 API](https://developers.tossinvest.com/docs/market-data).", ""])
    for key, result in report["results"].items():
        lines.extend([f"### {key}", "", f"고정 후보: `{result['selected_rule']}`", "",
                      f"수집 페이지: {result['history']['pages']}, 분봉: {result['history']['minutes']}, 완전 세션: {result['history']['complete_sessions']}.",
                      f"수집 종료 이유: {result['history']['stop_reason']}.", ""])
        for part, period in result["periods"].items():
            lines.append(f"- {part}: {period['start']} ~ {period['end']} ({period['sessions']}세션)")
        lines.append("")
        selected_trial = next(trial for trial in result["trials"] if trial["trial_id"] == result["selected_trial_id"])
        lines.extend(["| 구간 | 순수익률 | 완료 거래 |", "| --- | ---: | ---: |"])
        for part in ("training", "validation"):
            summary = selected_trial[part]
            lines.append(f"| {part} | {summary['net_return']:.4%} | {summary['trades']} |")
        lines.append("")
        for name, passed in result["checks"].items():
            lines.append(f"- {name}: {'통과' if passed else '실패'}")
        lines.extend(["", f"2배 비용 시험 수익률: {result['double_cost_test']['net_return']:.4%}", ""])
    lines.extend(["## 미검증·제약", "", "- 과거 확정 뉴스와 당시 수신 시각이 없어 뉴스 전략은 미검증이다.",
                  "- 과거 호가·잔량·부분 체결·주문 지연, 거래소 공식 역사 달력, 배당·기업행동은 미검증이다.",
                  "- 정규장 시각과 완전 분봉이 있는 날만 사용하며 조기 종료·누락일은 제외한다. 선택 편향이 생길 수 있다.",
                  "- 한 종목당 독립 가상 계좌다. 다종목 공유 자금·동시 신호 우선순위는 재현하지 않는다.",
                  "- 후보 비교에서 발생하는 과최적화를 없애지는 못한다. 2종목·단기간의 양수 수익도 미래 수익 증명이 아니다.",
                  "- 통과 조건: 60세션 이상, 훈련/검증/시험 양수, 시험 단순 보유 초과, 시험 거래 30건 이상, 낙폭 5% 이하, 2배 비용에서도 양수.",
                  f"- 동일 표본의 최종 시험 재사용: {report['holdout_reused']}. 다른 규칙으로 시험을 재사용하면 탐색 결과로만 기록한다.",
                  "- 실시간 전략 설정 변경·실제 주문은 수행하지 않았다.", "", "![최종 시험 가상 계좌 수익률](backtest.png)"])
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_report(folder, report):
    import os
    os.environ.setdefault("MPLCONFIGDIR", str(DATA_ROOT / "cache/plots"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plot
    figure, axes = plot.subplots(len(report["results"]), 1, figsize=(10, 7), squeeze=False, constrained_layout=True)
    for axis, (key, result) in zip(axes[:, 0], report["results"].items()):
        start = report["costs"]["starting_cash"][key.split(":")[0]]
        daily = {}
        for row in result["test"]["curve"]:
            daily[row["date"]] = (row["equity"] / start - 1) * 100
        dates = list(daily)
        axis.plot(range(len(dates)), list(daily.values()), marker="o", markersize=3, label="Rule: costs included")
        axis.axhline(result["buy_and_hold_test_return"] * 100, color="#e67e22", linestyle="--", label="Buy/hold FINAL return")
        axis.axhline(0, color="gray", linewidth=0.7)
        if dates:
            indices = sorted({0, len(dates) // 2, len(dates) - 1})
            axis.set_xticks(indices, [dates[index] for index in indices])
        axis.set_title(key + (": exploratory REUSED holdout" if report["holdout_reused"] else ": frozen test period"))
        axis.set_ylabel("Account return (%)")
        axis.grid(alpha=0.2)
        axis.legend()
    figure.suptitle("Actual historical bars, simulated fills: NOT a live performance record")
    figure.savefig(folder / "backtest.png", dpi=150)
    plot.close(figure)


def main():
    from tools.collect_history import main as collect
    collect()
    runtime = load_run_settings()
    settings = load_research_settings(CONFIG_ROOT / "research.json")
    costs = json.loads(runtime["paper_settings"].read_text(encoding="utf-8"))
    validate_costs(costs)
    folder = RESULTS_ROOT / "backtest"
    folder.mkdir(parents=True, exist_ok=True)
    lock = acquire_run_lock(folder / "run.lock")
    try:
        if (folder / "results.json").exists():
            previous = json.loads((folder / "results.json").read_text(encoding="utf-8"))
            stamp = previous["created_at"].replace(":", "-")
            archive = folder / "runs" / stamp
            archive.mkdir(parents=True, exist_ok=True)
            for name in ("results.json", "report.md", "backtest.png"):
                if (folder / name).exists():
                    shutil.copy2(folder / name, archive / name)
        results = {}
        digest = hashlib.sha256()
        legacy_digest = hashlib.sha256()
        for market, symbol in runtime["symbols"]:
            path = DATA_ROOT / "history" / (market + "-" + symbol + ".json")
            data = path.read_bytes()
            legacy_digest.update(data)
            record = json.loads(data)
            if record.get("origin") != "toss_actual_historical_candles" or record.get("market") != market or record.get("symbol") != symbol:
                raise ValueError("과거 시세의 출처·시장·종목 기록이 설정과 다릅니다.")
            # 수집 시각만 바꿔 같은 가격 표본을 새 미사용 시험이라고 부르지 않는다.
            digest.update(json.dumps({"market": market, "symbol": symbol, "candles": record["candles"]}, sort_keys=True).encode())
            sessions = prepare_sessions(record)
            if len(sessions) < 10:
                raise ValueError(f"{market}:{symbol}: 완전 세션 {len(sessions)}개. 비교에 필요한 과거 분봉이 부족합니다.")
            result = compare_rules(sessions, costs, settings)
            result["history"] = {"pages": record["pages"], "minutes": len(record["candles"]),
                                 "complete_sessions": len(sessions), "stop_reason": record["stop_reason"]}
            results[market + ":" + symbol] = result
            summary = result["test"]["summary"]
            print(f"{market}:{symbol}: 시험 계산 {summary['net_return']:.4%}, {summary['trades']}거래", flush=True)
        # 같은 원자료를 다른 코드·설정으로 반복 시험하면 새 미사용 표본이라고 부르지 않는다.
        fingerprint = hashlib.sha256((PROJECT_ROOT / "research/backtest.py").read_bytes() +
                                     (PROJECT_ROOT / "research/history.py").read_bytes() +
                                     json.dumps({"settings": settings, "costs": costs}, sort_keys=True).encode()).hexdigest()
        registry_path = DATA_ROOT / "history/holdout-registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}
        dataset_id = digest.hexdigest()
        # 초기 연구의 메타데이터 포함 지문도 이어받아 같은 표본의 기록을 놓치지 않는다.
        previous_fingerprint = registry.get(dataset_id, registry.get(legacy_digest.hexdigest()))
        reused = previous_fingerprint is not None and previous_fingerprint != fingerprint
        registry.setdefault(dataset_id, fingerprint)
        write_json(registry_path, registry)
        report = {"created_at": datetime.now(timezone.utc).isoformat(), "origin": "actual_toss_bars_simulated_fills",
                  "dataset_sha256": dataset_id, "experiment_sha256": fingerprint,
                  "holdout_reused": reused, "costs": costs, "settings": settings, "results": results,
                  "live_strategy_updated": False}
        if reused:
            for result in results.values():
                result["verdict"] = "exploratory_holdout_reused"
        for key, result in results.items():
            print(f"{key}: 최종 판정 {result['verdict']}")
        write_json(folder / "results.json", report)
        # 비교 조건·실패 결과도 남겨서 다음 수정이 이전 실험을 덮어쓰지 않게 한다.
        with (folder / "experiments.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(report, ensure_ascii=False, allow_nan=False) + "\n")
        write_report(folder, report)
        try:
            plot_report(folder, report)
        except ImportError:
            print("그래프에는 선택적 matplotlib가 필요합니다. 계산 결과와 보고서는 저장됐습니다.")
        print(f"보고서: {folder / 'report.md'}")
    finally:
        release_run_lock(lock)


if __name__ == "__main__":
    main()
