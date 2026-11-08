"""일봉 돌파 진입 고정·매도 조건 비교. 운용 Code와 Config는 읽기만 한다.

프로젝트 루트: python Test/research/exit_comparison_experiment.py
수정 위치: POLICY, PERIODS, exit_comparison_core.VARIANTS. 실험마다 설정을 보존한다.
"""
import copy
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Code"))
sys.path.insert(0, str(Path(__file__).parent))

from exit_comparison_core import VARIANTS, replay
from research.algorithm_study import make_features
from research.daily import prepare_daily_bars
from research.entry_inputs import daily_inputs
from tools.run_algorithm_study import record_event, write_json


POLICY = {"spread_ratio": .001, "risk_budget": .0025, "maximum_entry_gap": .03,
          "holding_sessions": 20, "opportunity_spacing": 31}
PERIODS = {"development": {"start": "2020-01-01", "end": "2022-12-31"},
           "validation": {"start": "2023-01-01", "end": "2024-12-31"},
           "evaluation": {"start": "2025-01-01", "end": "2026-10-23"},
           "continuous": {"start": "2020-01-01", "end": "2026-10-23"}}
SELECTION = {"minimum_trades": 30, "maximum_drawdown": .05, "worst_month_floor": -.02,
             "minimum_baseline_profit_fraction": .75, "maximum_baseline_drawdown_fraction": .8,
             "drawdown_score_penalty": 2}


def protected_hashes():
    files = list((PROJECT / "Code").rglob("*.py")) + list((PROJECT / "Config").rglob("*.json"))
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def build_opportunities(records, series, features):
    """최초 신호부터 31거래일 간격. 미래 관측 창·손익에 따른 사건 제외는 하지 않는다."""
    feature_index = {symbol: {row["date"]: row for row in rows} for symbol, rows in features.items()}
    opportunities, audit = {}, []
    for symbol, bars, anchors, coverage in daily_inputs(records, {"all": PERIODS["continuous"]}):
        next_allowed = -1
        for anchor in anchors:
            selected = anchor["index"] >= next_allowed
            audit.append({"symbol": symbol, "date": anchor["date"], "selected": selected})
            if not selected:
                continue
            next_allowed = anchor["index"] + POLICY["opportunity_spacing"]
            feature = feature_index[symbol][anchor["date"]]
            score = feature["momentum63"] / max(feature["volatility"] or 0, .001)
            opportunities.setdefault(anchor["date"], []).append({**anchor, "score": score, "close": feature["close"]})
    return opportunities, audit


def choose_candidate(summaries):
    """이후 평가 전에 개발·검증으로만 판단한다. 적격 후보가 없으면 선정하지 않는다."""
    baseline = summaries["hold20"]["validation"]["base"]
    checks, eligible = {}, []
    for variant in VARIANTS:
        name = variant["name"]
        if name == "hold20":
            continue
        development = summaries[name]["development"]
        validation = summaries[name]["validation"]
        base = validation["base"]
        passed = {
            "development_positive_both_costs": development["base"]["net_return"] > 0 and development["double_cost"]["net_return"] > 0,
            "validation_positive_both_costs": base["net_return"] > 0 and validation["double_cost"]["net_return"] > 0,
            "enough_trades": base["trades"] >= SELECTION["minimum_trades"],
            "drawdown_limit": base["max_drawdown"] <= SELECTION["maximum_drawdown"],
            "worst_month_limit": base["worst_month"] >= SELECTION["worst_month_floor"],
            "retain_baseline_profit": base["net_return"] >= SELECTION["minimum_baseline_profit_fraction"] * max(0, baseline["net_return"]),
            "reduce_baseline_drawdown": base["max_drawdown"] <= SELECTION["maximum_baseline_drawdown_fraction"] * baseline["max_drawdown"],
        }
        checks[name] = passed
        if all(passed.values()):
            eligible.append(name)
    selected = max(eligible, key=lambda name: summaries[name]["validation"]["base"]["net_return"] -
                   SELECTION["drawdown_score_penalty"] * summaries[name]["validation"]["base"]["max_drawdown"]) if eligible else None
    return {"selected": selected, "eligible": eligible, "checks": checks, "used_evaluation": False}


def pct(value):
    return "—" if value is None else f"{value:.2%}"


def plot_results(folder, results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as dates
    figure, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)
    for number, variant in enumerate(VARIANTS):
        name = variant["name"]
        points = results[name]["continuous"]["base"]["curve"]
        color = plt.get_cmap("tab10")(number)
        times = [datetime.fromisoformat(point["date"]) for point in points]
        axes[0].plot(times, [(point["equity"] / 10000 - 1) * 100 for point in points], color=color, label=name)
        peak, drawdowns = 10000, []
        for point in points:
            peak = max(peak, point["equity"])
            drawdowns.append((point["equity"] / peak - 1) * 100)
        axes[1].plot(times, drawdowns, color=color, label=name)
    axes[0].set_title("Same daily breakout opportunities, shared cash, different protective exits")
    axes[0].set_ylabel("Cumulative net account return (%)")
    axes[1].set_ylabel("Daily close drawdown (%)")
    for axis in axes:
        axis.grid(alpha=.2)
        axis.axhline(0, color="gray", linewidth=.6)
        axis.legend(ncol=3, fontsize=8)
    locator = dates.AutoDateLocator(minticks=4, maxticks=9)
    axes[1].xaxis.set_major_locator(locator)
    axes[1].xaxis.set_major_formatter(dates.ConciseDateFormatter(locator))
    figure.tight_layout()
    figure.savefig(folder / "performance.png", dpi=150)
    plt.close(figure)
    figure, axes = plt.subplots(1, 2, figsize=(14, 6))
    names = [row["name"] for row in VARIANTS]
    positions = list(range(len(names)))
    for stage, axis in zip(("continuous", "evaluation"), axes):
        axis.barh([position - .18 for position in positions], [results[name][stage]["base"]["summary"]["net_return"] * 100 for name in names], height=.35, label="Base costs")
        axis.barh([position + .18 for position in positions], [results[name][stage]["double_cost"]["summary"]["net_return"] * 100 for name in names], height=.35, label="Double costs")
        axis.set_yticks(positions, names)
        axis.set_title(stage + ": simulated net returns")
        axis.set_xlabel("Net account return (%)")
        axis.axvline(0, color="gray", linewidth=.6)
        axis.legend()
    figure.tight_layout()
    figure.savefig(folder / "comparison.png", dpi=150)
    plt.close(figure)
    figure, axis = plt.subplots(figsize=(12, 6))
    gross = [results[name]["continuous"]["base"]["summary"]["closed_gross_pnl"] for name in names]
    net = [results[name]["continuous"]["base"]["summary"]["realized_pnl"] for name in names]
    axis.bar([position - .18 for position in positions], gross, width=.35, label="Closed trades: reference-price gross P&L")
    axis.bar([position + .18 for position in positions], net, width=.35, label="Closed trades: net P&L after all costs")
    axis.set_xticks(positions, names, rotation=15)
    axis.set_ylabel("USD (open-position P&L excluded)")
    axis.set_title("Cost bridge on the SAME completed trades; not a separate zero-cost strategy")
    axis.axhline(0, color="gray", linewidth=.6)
    axis.grid(axis="y", alpha=.2)
    axis.legend()
    figure.tight_layout()
    figure.savefig(folder / "costs.png", dpi=150)
    plt.close(figure)


def write_report(folder, declaration, summaries, selection, plan):
    lines = ["# 일봉 매수 고정·보호 매도 비교", "", "저장된 KIS 실제 수정 일봉에 가상 체결·비용을 적용했다. 운용 설정·계좌에는 반영하지 않았다.", "",
        "## 실험 조건", "",
        "- 28종목과 SPY, 2018년부터 지표 준비 후 2020-01-01~2026-10-23 평가. 개발 2020~2022, 검증 2023~2024, 이후 평가 2025~2026-10-23, 전체 연속 계좌를 별도로 보존.",
        "- 매수: 종가가 직전 55거래일 고점 돌파, 신호일 SPY>MA200, 종목 관측 봉 201개 이상. 직전 55거래일 누락 시 신호 제외. 거래량 필터는 사용하지 않는다.",
        "- 앞선 진입 연구처럼 종목별 첫 신호 후 31거래일 간격을 고정한다. 미래 자료의 유무·손익으로 사건을 제외하지 않는다. 기간 끝의 미청산도 비용 반영 평가한다.",
        "- 다음 거래일 시가 진입. 시가가 원래 돌파선 아래 또는 신호 종가 대비 +3% 초과면 취소. 동시에 자금이 부족하면 63일 모멘텀/20일 변동성 순, 동률은 종목명 순.",
        "- 초기 공동 자금 10,000 USD, 최대 5종목·종목별 초기 자금 10%. 모든 조건의 수량은 min(가용 예산/매수 원가, 초기 자금 0.25%/(신호 ATR14×2.5))의 정수다. 매도 폭에 맞춰 수량을 바꾸지 않아 실제 위험은 조건별로 다르다.",
        "- 모든 조건은 최대 20거래일 보유 후 그날 종가에 예정 청산한다. hold20은 가격 손절이 없는 기준이다. 월별 자금 초기화·월말 강제 청산·유사도 전략 선택은 하지 않는다.",
        "- fixed3/5: 진입 기준가의 -3%/-5%. atr25: 진입 시점 신호 ATR14×2.5 아래. atr25_trail3: ATR 손절+관측 최고가−그날 ATR14×3. fixed3_trail4: 3% 손절+관측 최고가 대비 -4% 추적.",
        "- 당일 고가·ATR로 갱신한 추적 손절선은 다음 거래일부터 적용. 시가 갭은 손절선 대신 더 불리한 실제 시가로 체결. 진입 당일 초기 손절은 적용한다.",
        "- 순서: 기존 보유 갭 매도→전날 계획 매수→봉 내 손절→20거래일 만기 종가 매도. 장중 매도로 생긴 현금을 이미 지난 시가에 재사용하지 않는다.",
        "- 매수 비용 0.1%, 매도 0.2%, 편도 슬리피지 0.1%, 스프레드 0.1% 가정. 두 배 비용은 네 비율 모두 두 배. 실제 요율·호가·부분 체결을 재현하지 않는다.", ""]
    for stage in ("continuous", "development", "validation", "evaluation"):
        lines += [f"## {stage}: {PERIODS[stage]['start']} ~ {PERIODS[stage]['end']}", "",
            "|매도 조건|순수익|비용 두 배|최대 낙폭|최악의 월|완료 거래|승률|평균 투자 비중|미청산|",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for variant in VARIANTS:
            name = variant["name"]
            row = summaries[name][stage]["base"]
            lines.append(f"|{name}|{pct(row['net_return'])}|{pct(summaries[name][stage]['double_cost']['net_return'])}|{pct(row['max_drawdown'])}|{pct(row['worst_month'])} ({row['worst_month_date']})|{row['trades']}|{pct(row['win_rate'])}|{pct(row['average_exposure'])}|{row['open_positions']}|")
        lines.append("")
    lines += ["## 같은 완료 거래의 비용 분해 — 연속 계좌", "", "미청산 손익은 아래 합계에 들어가지 않는다. 최종 계좌는 초기 자금+완료 순손익+미청산 순손익으로 별도 검산한다.", "",
        "|조건|가격 변화 손익 USD|스프레드|슬리피지|수수료·가정 비용|완료 순손익|미청산 순손익|", "|---|---:|---:|---:|---:|---:|---:|"]
    for variant in VARIANTS:
        row = summaries[variant["name"]]["continuous"]["base"]
        lines.append("|" + variant["name"] + "|" + "|".join(f"{row[key]:.2f}" for key in ("closed_gross_pnl", "closed_spread_cost", "closed_slippage_cost", "closed_fees", "realized_pnl", "open_net_pnl")) + "|")
    lines += ["", "## 사전 기준에 따른 후보", "",
        "이후 평가를 계산하기 전에 개발·검증으로만 선정: 두 구간 모두 기본/두 배 비용 수익 양수, 검증 30완료 거래 이상, MDD≤5%, 최악 월≥-2%, 기준 수익의 75% 이상 유지·기준 MDD 20% 이상 감소. 통과 후보는 검증 수익−2×MDD로 선정.", "",
        f"선정: **{selection['selected'] or '없음'}**. 미래 평가와 전체 연속 성과를 보고 후보를 바꾸지 않았다.", "",
        "|조건|탈락한 개발·검증 기준|", "|---|---|"]
    for name, checks in selection["checks"].items():
        lines.append(f"|{name}|{', '.join(key for key, passed in checks.items() if not passed) or '전부 통과'}|")
    lines += ["", "## 다음 자료의 모의 검증 계획", "", f"상태: `{plan['status']}`. 운용이나 자동 실행에는 연결하지 않았다.",
        "선정 및 이후 평가 기준을 통과한 후보만 동일 조건을 고정하고 새로운 자료에서 최소 60거래일 및 완료 30거래 이상 검증할 계획이다. 현재 보유 자료를 새 미래 검증으로 세지 않는다.",
        "", "## 한계", "",
        "- 앞선 여러 연구에서 본 자료를 다시 사용하는 탐색이다. 당시 상장 전체 종목이 아닌 현재 선택된 28종목을 소급했으며 생존·종목 선택 편향이 있다.",
        "- 배당 현금·환율·실제 세금·시장 충격·체결 지연은 미반영이다. 수정주가에 따른 연구용 정수 수량이며 실주문 수량으로 쓰지 않는다.",
        "- 일봉 OHLC로 장중 경로를 알 수 없다. 손절 체결은 선언한 가정이며 보장 가격이 아니다. MDD는 일별 종가 평가 기준으로 장중 급락을 축소할 수 있다.",
        "- 같은 매수 기회를 제공해도 보유 기간·공동 현금 경쟁이 달라 실제 체결 종목은 달라질 수 있다. 이 차이도 계좌 결과에 포함했다.",
        "- 앞선 사건당 평균 수익을 이번 계좌 누적 수익과 직접 비교하면 안 된다. 단계별 자금은 초기화하지만 전체 연속 계좌는 초기화하지 않았다.",
        "- 시세 누락 시 보유 평가를 마지막 실제 종가로 유지하고 diagnostics에 기록한다. 봉을 만들어 손절·만기 체결하지 않는다. 구간 끝 가상 매도 비용은 평가액에만 반영하고 완료 거래를 만들지 않는다.", "",
        "![연속 수익·낙폭](performance.png)", "", "![비용 스트레스](comparison.png)", "", "![같은 거래의 비용 분해](costs.png)", "",
        f"실행 보존: `{folder}`", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    protected_before = protected_hashes()
    dataset = Path(json.loads((PROJECT / "Data/industry-peers/datasets/latest.json").read_text(encoding="utf-8"))["folder"])
    records, hashes = {}, {}
    for path in sorted((dataset / "daily").glob("*.json")):
        raw = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        record = json.loads(raw)
        records[record["symbol"]] = record
    series = {symbol: prepare_daily_bars(record) for symbol, record in records.items() if symbol != "SPY"}
    features = {symbol: make_features(bars) for symbol, bars in series.items()}
    days = [bar["date"] for bar in prepare_daily_bars(records["SPY"])]
    if days[-1] < PERIODS["evaluation"]["end"]:
        raise ValueError("선언한 종료일까지 자료가 없습니다.")
    opportunities, audit = build_opportunities(records, series, features)
    costs = json.loads((PROJECT / "Config/paper.json").read_text(encoding="utf-8"))
    stressed_costs = copy.deepcopy(costs)
    for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
        stressed_costs[key] *= 2
    scenarios = {"base": (costs, POLICY), "double_cost": (stressed_costs, {**POLICY, "spread_ratio": POLICY["spread_ratio"] * 2})}
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder = PROJECT / "Data/tests/results/exit-comparison" / run_id
    (folder / "source").mkdir(parents=True)
    (folder / "runs").mkdir()
    declaration = {"run_id": run_id, "dataset": str(dataset), "data_hashes": hashes,
        "policy": POLICY, "periods": PERIODS, "variants": VARIANTS, "selection": SELECTION,
        "costs": costs, "symbols": list(series), "opportunity_count": sum(map(len, opportunities.values())),
        "protected_before": protected_before, "prior_data_exposure": True, "live_activation": False}
    for path in (Path(__file__), Path(__file__).with_name("exit_comparison_core.py"), Path(__file__).with_name("test_exit_comparison.py"),
                 PROJECT / "Code/research/entry_inputs.py", PROJECT / "Code/research/algorithm_study.py", PROJECT / "Code/research/daily.py", PROJECT / "Code/research/backtest.py"):
        raw = path.read_bytes()
        declaration.setdefault("code_hashes", {})[str(path)] = hashlib.sha256(raw).hexdigest()
        (folder / "source" / path.name).write_bytes(raw)
    write_json(folder / "declaration.json", declaration)
    write_json(folder / "opportunities.json", opportunities)
    write_json(folder / "signal-audit.json", audit)
    registry = PROJECT / "Data/research/experiments/registry.jsonl"
    record_event(registry, {"study": "protective_exit_comparison", "run_id": run_id, "status": "declared", "folder": str(folder), "policy": POLICY, "variants": VARIANTS, "selection": SELECTION})
    results, summaries = {variant["name"]: {} for variant in VARIANTS}, {variant["name"]: {} for variant in VARIANTS}
    try:
        selection = None
        for stage, period in PERIODS.items():
            if stage == "evaluation":
                selection = choose_candidate(summaries)
                write_json(folder / "selection-before-evaluation.json", selection)
                record_event(registry, {"study": "protective_exit_comparison", "run_id": run_id, "status": "selected_before_evaluation", "selection": selection})
            for variant in VARIANTS:
                name = variant["name"]
                results[name][stage], summaries[name][stage] = {}, {}
                for scenario, (scenario_costs, policy) in scenarios.items():
                    result = replay(series, features, days, opportunities, variant, scenario_costs, policy, **period)
                    results[name][stage][scenario], summaries[name][stage][scenario] = result, result["summary"]
                    write_json(folder / "runs" / (name + "-" + stage + "-" + scenario + ".json"), result)
                row = summaries[name][stage]["base"]
                print(f"{stage} {name}: 수익 {row['net_return']:.2%}, MDD {row['max_drawdown']:.2%}, 최악 월 {row['worst_month']:.2%}, {row['trades']}거래", flush=True)
        selected = selection["selected"]
        evaluation_passed = False
        if selected:
            evaluation = summaries[selected]["evaluation"]
            evaluation_passed = (evaluation["base"]["net_return"] > 0 and evaluation["double_cost"]["net_return"] > 0
                and evaluation["base"]["max_drawdown"] <= SELECTION["maximum_drawdown"]
                and evaluation["base"]["worst_month"] >= SELECTION["worst_month_floor"]
                and evaluation["base"]["trades"] >= SELECTION["minimum_trades"])
        plan = {"status": "candidate_for_new_data_validation" if evaluation_passed else "no_qualified_candidate",
            "candidate_selected_before_evaluation": selected, "evaluation_passed": evaluation_passed,
            "source_data_cutoff": PERIODS["evaluation"]["end"], "minimum_new_sessions": 60,
            "minimum_completed_trades": 30, "maximum_drawdown": .05, "worst_month_floor": -.02,
            "automatic_execution": False, "live_activation": False, "frozen_policy": POLICY,
            "frozen_variant": next((variant for variant in VARIANTS if variant["name"] == selected), None)}
        unchanged = protected_before == protected_hashes()
        if not unchanged:
            raise ArithmeticError("운용 Code·Config가 변경되었습니다.")
        checks = {"replays": sum(len(scenarios) for stages in results.values() for scenarios in stages.values()),
                  "closed_trade_cost_reconciliations": sum(row["trades"] for stages in summaries.values() for scenarios in stages.values() for row in scenarios.values()),
                  "account_pnl_reconciliations": 48, "cash_positions_within_limits": True,
                  "live_code_config_unchanged": unchanged, "source_hashes": hashes}
        for filename, value in (("summaries", summaries), ("validation", checks), ("forward-plan", plan)):
            write_json(folder / (filename + ".json"), value)
        write_report(folder, declaration, summaries, selection, plan)
        plot_results(folder, results)
        destination = PROJECT / "Data/reports/exit-comparison"
        destination.mkdir(parents=True, exist_ok=True)
        for name in ("report.md", "performance.png", "comparison.png", "costs.png", "summaries.json", "validation.json", "declaration.json", "selection-before-evaluation.json", "forward-plan.json"):
            shutil.copy2(folder / name, destination / name)
        write_json(folder.parent / "latest.json", {"folder": str(folder)})
        write_json(destination / "latest.json", {"folder": str(folder)})
        record_event(registry, {"study": "protective_exit_comparison", "run_id": run_id, "status": "finished", "folder": str(folder), "selection": selection, "forward_plan": plan})
        with (PROJECT / "Docs/RESEARCH_LOG.md").open("a", encoding="utf-8") as stream:
            stream.write(f"\n## {run_id}: 같은 일봉 돌파 매수·6개 보호 매도 비교\n\n- 28종목·같은 31거래일 간격 기회·공동 자금·20거래일 만기, 고정/ATR/추적 손절. 4기간×2비용, 48회.\n- 개발·검증 사전 선정: {selected or '없음'}. 신규 자료 모의 검증 상태: {plan['status']}. 실전·운용 설정 반영 없음.\n- [보고서](../Data/reports/exit-comparison/report.md), 실행 보존 `{folder}`.\n")
        print("보고서:", destination / "report.md", flush=True)
    except Exception as error:
        record_event(registry, {"study": "protective_exit_comparison", "run_id": run_id, "status": "failed", "error_type": type(error).__name__})
        raise


if __name__ == "__main__":
    main()
