"""과거 유사 시장에 따른 전략 선택을 시험한다. 운용 코드에는 연결하지 않는다.

실행: 프로젝트 루트에서 python Test/research/analog_experiment.py
설정은 이 파일의 EXPERIMENT에서만 바꾼다. 실험마다 조건·원본 해시·소스를 보존한다.
"""
import copy
import hashlib
import json
import math
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Code"))
sys.path.insert(0, str(Path(__file__).parent))

from analog_logic import STATE_FIELDS, choose_strategy, market_states
from broker.sessions import calendar_for
from research.algorithm_study import FAMILIES, make_features, replay, summarize
from research.backtest import execution_price
from research.daily import prepare_daily_bars
from tools.run_algorithm_study import record_event, write_json


EXPERIMENT = {
    "evaluation_start": "2021-01-01",
    "primary": "analog12",
    "policy": {"minimum_history": 24, "neighbors": 12, "minimum_neighbors": 8,
               "maximum_distance": 1.5, "drawdown_penalty": 1.0,
               "minimum_positive_fraction": 0.5},
    "sensitivity_neighbors": [8, 24],
    "market_filter": True,
    "rebalance": "monthly_flatten_all_at_last_close",
    "prior_data_exposure": True,
    "activate_live": False,
}


def protected_hashes():
    """읽기만 허용한 운용 코드·설정의 변경 여부를 확인한다. 인증 파일은 읽지 않는다."""
    paths = list((PROJECT / "Code").rglob("*.py")) + list((PROJECT / "Config").rglob("*.json"))
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def full_months(proxy_bars):
    """마지막 자료가 월말 거래일에 못 미치는 현재 진행 중인 달은 평가에서 뺀다."""
    grouped = {}
    for bar in proxy_bars:
        grouped.setdefault(bar["date"][:7], []).append(bar["date"])
    output = []
    for month, days in grouped.items():
        schedule = calendar_for("US", int(month[:4])).schedule
        expected = [label.date().isoformat() for label in schedule.index if label.strftime("%Y-%m") == month]
        if days == expected:
            output.append({"month": month, "start": days[0], "end": days[-1], "days": days})
    return output


def close_month(result, series, costs, settings, ending):
    """월말 평가에 이미 차감된 매도 비용으로 청산한다. 비용을 두 번 빼지 않는다."""
    result = copy.deepcopy(result)
    for symbol, position in result["positions"].items():
        bar = next((bar for bar in reversed(series[symbol]) if bar["date"] == ending), None)
        if bar is None:
            raise ValueError("월말 실제 봉 없이 청산할 수 없습니다: " + symbol + " " + ending)
        sell_price = execution_price(bar["close"], "SELL", costs, settings["spread_ratio"])
        received = position["quantity"] * sell_price * (1 - costs["sell_cost_ratio"])
        result["trades"].append({"symbol": symbol, "signal_date": position["signal_date"],
            "entry_date": position["entry_date"], "exit_date": ending,
            "quantity": position["quantity"], "entry_cost": position["cost"],
            "entry_price": position["price"], "exit_price": sell_price,
            "pnl": received - position["cost"], "reason": "experiment_month_end"})
    last = result["curve"][-1]
    last.update(cash=last["equity"], positions=0, exposure=0)
    result["positions"] = {}
    initial = costs["starting_cash"]["US"]
    result["summary"] = summarize(result["curve"], result["trades"], initial)
    if not math.isclose(initial + sum(trade["pnl"] for trade in result["trades"]), last["equity"], abs_tol=1e-6):
        raise ArithmeticError("월말 청산 손익과 최종 평가액 불일치")
    return result


def cash_result(days, initial):
    return {"curve": [{"date": day, "equity": initial, "cash": initial, "positions": 0, "exposure": 0} for day in days], "trades": []}


def compound_months(months, decisions, results, scenario, initial):
    """월별 기준 계좌를 가상 단위로 연결한다. 월 수익률을 더하지 않는다.

    매월 1만 달러 기준 계좌의 배분을 현재 자산에 비례해 복제한다. 복제 단위는
    소수이므로 실제 정수 주식 계좌와 동일하지 않다. 모든 비교군에 같은 가정을 쓴다.
    """
    capital = initial
    curve, trades, monthly = [], [], []
    for month, decision in zip(months, decisions):
        family = decision["selected"]
        result = cash_result(month["days"], initial) if family == "cash" else results[(month["month"], family, scenario)]
        scale = capital / initial
        for point in result["curve"]:
            curve.append({**point, "equity": point["equity"] * scale, "cash": point["cash"] * scale,
                          "exposure": point["exposure"] * scale})
        for trade in result["trades"]:
            trades.append({**trade, "pnl": trade["pnl"] * scale,
                           "quantity": trade["quantity"] * scale, "entry_cost": trade["entry_cost"] * scale})
        month_return = curve[-1]["equity"] / capital - 1
        monthly.append({"month": month["month"], "selected": family, "net_return": month_return,
                        "ending_equity": curve[-1]["equity"]})
        capital = curve[-1]["equity"]
    summary = summarize(curve, trades, initial)
    selected = [decision["selected"] for decision in decisions]
    summary.update(cash_months=selected.count("cash"), months=len(months),
                   strategy_changes=sum(first != second for first, second in zip(selected, selected[1:])),
                   selected_counts=dict(Counter(selected)),
                   month_end_trades=sum(trade["reason"] == "experiment_month_end" for trade in trades))
    if not math.isclose(initial + sum(trade["pnl"] for trade in trades), capital, abs_tol=1e-5):
        raise ArithmeticError("연결 계좌 손익 불일치")
    return {"summary": summary, "curve": curve, "trades": trades, "monthly": monthly}


def plot_results(folder, accounts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as dates
    figure, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    for name, scenarios in accounts.items():
        points = scenarios["base"]["curve"]
        initial = 10000
        width = 2.8 if name == EXPERIMENT["primary"] else 1.1
        alpha = 1 if name == EXPERIMENT["primary"] else .65
        times = [datetime.fromisoformat(point["date"]) for point in points]
        axes[0].plot(times, [(point["equity"] / initial - 1) * 100 for point in points], linewidth=width, alpha=alpha, label=name)
        if name in ("analog12", "history_all", "recent12", "fixed_donchian"):
            peak, drawdowns = initial, []
            for point in points:
                peak = max(peak, point["equity"])
                drawdowns.append((point["equity"] / peak - 1) * 100)
            axes[1].plot(times, drawdowns, linewidth=width, label=name)
    axes[0].set_title("Historical market analog selection: monthly flattening, simulated fills")
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
    figure, axis = plt.subplots(figsize=(12, 7))
    names = list(accounts)
    positions = list(range(len(names)))
    axis.barh([value - .18 for value in positions], [accounts[name]["base"]["summary"]["net_return"] * 100 for name in names], height=.35, label="Base costs")
    axis.barh([value + .18 for value in positions], [accounts[name]["double_cost"]["summary"]["net_return"] * 100 for name in names], height=.35, label="Double costs, same choices")
    axis.set_yticks(positions, names)
    axis.set_xlabel("Cumulative net return (%)")
    axis.set_title("All declared policies retained; no winner promoted to live trading")
    axis.axvline(0, color="gray", linewidth=.6)
    axis.legend()
    figure.tight_layout()
    figure.savefig(folder / "comparison.png", dpi=150)
    plt.close(figure)


def percent(value):
    return "—" if value is None else f"{value:.2%}"


def write_report(folder, declaration, accounts, decisions, current, checks):
    primary = accounts[EXPERIMENT["primary"]]["base"]["summary"]
    lines = ["# 과거 유사 상황에 따른 전략 선택 — 시험 전용", "",
        "실제 KIS 수정 일봉 + 가상 체결·비용으로 수행한 소급 실험이다. 운용 코드·설정·계좌에 적용하지 않았다.", "",
        f"- 기간: {declaration['evaluation_first']} ~ {declaration['evaluation_last']}, {primary['months']}개 완료 월. 현재 진행 중인 2026년 10월은 성과 평가에서 제외.",
        f"- 종목: 앞선 동종 기업 연구와 같은 {len(declaration['symbols'])}개. 데이터 원본 {declaration['dataset']}. 미국 시장 공통 상황을 비교하며 개별 종목 차트의 유사도는 이번 시험 대상이 아니다.",
        "- 사전 고정 주 실험 analog12: 유사도 가까운 과거 사례 최대 12개. analog8/24는 민감도 비교이며 결과를 보고 주 실험을 교체하지 않는다.", "",
        "## 선택·체결 조건", "",
        "1. 매월 말까지의 SPY 5·20·60일 수익률, MA50과 거리, 20일 변동성, 60일 고점 대비 하락, 거래량 비율, 준비된 종목의 MA50 상회 비중을 계산한다.",
        "2. 그 시점에 다음 달 성과까지 이미 확정된 과거 사례만 보관한다. 정규화 척도도 이 사례들의 상태에서만 계산한다. 사례의 결과 월은 서로 겹치지 않지만 60일 선행 창은 겹치므로 독립 표본으로 보지 않는다.",
        "3. 8개 지표를 과거 표준편차로 나눈 평균 제곱 거리의 제곱근으로 비교한다. 거리 1.5 이내, 과거 완료 사례 24개 이상·유사 사례 8개 이상이 필요하다.",
        "4. 가까운 사례 가중치=1/(1+거리). 점수=가중 평균 순수익−가중 평균 최대 낙폭. 기본·두 배 비용 평균 수익 모두 양수, 양수 사례 절반 이상, 점수>0인 최고 전략을 고른다. 없으면 무이자 현금 대기.",
        "5. 후보는 MA 추세·55일 돌파·추세 속 눌림·볼린저 회귀·모멘텀 회전·저변동 추세의 기존 6개. SPY>MA200 시장 필터를 모두 적용한다.",
        "6. 선택 후 다음 달에만 적용한다. 매월 첫날은 현금에서 시작하고 첫 종가 계획부터 다음 시가에 체결한다. 기존 재생기의 ATR 손절·익일 적용 추적 손절·전략 매도·갭 제한을 그대로 사용한다.",
        "7. 월말 종가에 전량 정리한다. 월말 매도 비용은 평가액에 이미 반영되어 두 번 차감하지 않는다. 모든 고정 전략·최근 성과·전체 과거 비교군에도 같은 월별 정리 조건을 적용했다.",
        "8. 월별 1만 USD 기준 계좌를 현재 자산에 비례해 복제하는 가상 단위 NAV다. 기준 계좌 내 수량은 정수지만 복제 비율은 소수다. 실제 정수 주식 계좌와 같지 않다. 월 수익률은 복리 연결하며 더하지 않는다.",
        "9. 최대 5종목, 종목별 월초 기준 자금 10%, 거래 위험 예산 0.25%, ATR14×2.5 손절·×3 추적 손절, 진입 갭 절댓값 3% 제한·매도 후 3거래일 대기.",
        "10. 매수 비용 0.1%·매도 0.2%·편도 슬리피지 0.1%·스프레드 0.1% 가정. 두 배 비용은 네 비율 모두 두 배이며 미래 평가에서 선택 경로는 기본 비용과 동일하게 유지한다.", "",
        "## 결과", "",
        "history_all은 전체 과거 성과, recent12는 최근 12개 완료 월만 사용한다. 두 비교군은 유사도 없이 같은 위험 점수·통과 기준을 적용한다.", "",
        "|방식|누적 순수익|비용 두 배|최대 낙폭|완료 거래|승률|PF|현금 월|전략 변경|", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, scenarios in accounts.items():
        row = scenarios["base"]["summary"]
        factor = "—" if row["profit_factor"] is None else f"{row['profit_factor']:.2f}"
        lines.append(f"|{name}|{percent(row['net_return'])}|{percent(scenarios['double_cost']['summary']['net_return'])}|{percent(row['max_drawdown'])}|{row['trades']}|{percent(row['win_rate'])}|{factor}|{row['cash_months']}/{row['months']}|{row['strategy_changes']}|")
    lines += ["", "### 주 실험의 선택 내역", "", "`" + json.dumps(primary["selected_counts"], ensure_ascii=False) + "`", "",
        "### 연도별 순수익", "", "|방식|2021|2022|2023|2024|2025|2026년 1~9월|", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, scenarios in accounts.items():
        annual = scenarios["base"]["summary"]["year_returns"]
        lines.append("|" + name + "|" + "|".join(percent(annual.get(str(year))) for year in range(2021, 2027)) + "|")
    lines += ["", "## 자료 마지막 날의 참고 진단", "",
        f"{current['decision_date']} 상태에 가장 가까운 완료 과거 사례. 선택 결과 `{current['selected']}`. 이는 월중 참고 진단이며 월말 선택 백테스트의 다음 거래나 주문이 아니다.", "",
        "|과거 상태 기준일|성과 관측 시작|성과 관측 종료|거리|", "|---|---|---|---:|"]
    for row in current["neighbors"]:
        lines.append(f"|{row['anchor_date']}|{row['outcome_start']}|{row['outcome_end']}|{row['distance']:.3f}|")
    lines += ["", "## 검증·한계", "",
        f"- 월별 원본 재생 {checks['monthly_replays']}회, 정책별 계좌 {checks['policy_accounts']}개. 월별·연결 손익을 검산했다. 선택에 미래 결과가 들어가지 않는 날짜 검사 {checks['date_checks']}건 통과.",
        "- 운용 Code·Config 전체 해시가 실행 전후 동일함을 확인했다. 키·계좌 API·뉴스·실제 주문을 사용하지 않았다.",
        "- 이미 본 자료로 새 가설을 평가하는 탐색이다. 지금 선택한 종목 목록을 과거에 소급한 선택·생존 편향이 있고 배당 현금·환율·실제 호가·시장 충격·체결 지연은 미반영이다.",
        "- 28종목에 대해 미국 시장 공통 국면만 비교했다. 금리·경제 지표·개별 산업 및 종목별 유사 패턴은 이번 시험에 포함하지 않았다.",
        "- 장중 유사도는 시험하지 않았다. 약 한 달 분봉으로 여러 시장 국면을 찾기 어렵기 때문에 장기 일봉에 한정했다.",
        "- 월별 청산과 소수 가상 단위는 연구를 단순화한 가정이다. 이전의 계속 보유하는 계좌 백테스트 수익률과 직접 비교하지 않는다.",
        "- 고정 전략 중 사후 최고 결과는 참고 기준일 뿐, 그 전략을 과거에 미리 골랐다는 뜻이 아니다. 대기 비중과 평균 투자 비중 차이도 함께 봐야 한다.",
        "- 이번 한 번의 결과로 유사도 기준·이웃 수를 재조정하지 않았다. 실전 반영은 하지 않는다.", "",
        "![누적 수익·낙폭](performance.png)", "", "![전체 비교](comparison.png)", "",
        f"실행 보존 폴더: `{folder}`", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    protected_before = protected_hashes()
    dataset = Path(json.loads((PROJECT / "Data/industry-peers/datasets/latest.json").read_text(encoding="utf-8"))["folder"])
    paths = sorted((dataset / "daily").glob("*.json"))
    raw_records = {str(path): path.read_bytes() for path in paths}
    data_hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in raw_records.items()}
    records = {record["symbol"]: record for record in (json.loads(raw) for raw in raw_records.values())}
    all_series = {symbol: prepare_daily_bars(record) for symbol, record in records.items()}
    proxy_bars = all_series.pop("SPY")
    series = all_series
    features = {symbol: make_features(bars) for symbol, bars in series.items()}
    proxy_features = {row["date"]: row for row in make_features(proxy_bars)}
    states = market_states(proxy_bars, features)
    months = full_months(proxy_bars)
    paired_months = []
    for previous, month in zip(months, months[1:]):
        if previous["end"] in states:
            paired_months.append({**month, "anchor_date": previous["end"]})
    evaluation = [month for month in paired_months if month["start"] >= EXPERIMENT["evaluation_start"]]
    settings = json.loads((PROJECT / "Config/algorithm-study.json").read_text(encoding="utf-8"))
    costs = json.loads((PROJECT / "Config/paper.json").read_text(encoding="utf-8"))
    stressed_costs, stressed_settings = copy.deepcopy(costs), copy.deepcopy(settings)
    for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
        stressed_costs[key] *= 2
    stressed_settings["spread_ratio"] *= 2
    scenarios = {"base": (costs, settings), "double_cost": (stressed_costs, stressed_settings)}
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder = PROJECT / "Data/tests/results/market-analog" / run_id
    (folder / "source").mkdir(parents=True)
    (folder / "monthly").mkdir()
    declaration = {"run_id": run_id, "experiment": EXPERIMENT, "state_fields": STATE_FIELDS,
        "symbols": list(series), "dataset": str(dataset), "data_hashes": data_hashes,
        "costs": costs, "settings": settings, "protected_before": protected_before,
        "source_first": proxy_bars[0]["date"], "source_last": proxy_bars[-1]["date"],
        "evaluation_first": evaluation[0]["start"], "evaluation_last": evaluation[-1]["end"],
        "family_order": FAMILIES, "independent_unseen_test": False}
    source_paths = [Path(__file__), Path(__file__).with_name("analog_logic.py"), Path(__file__).with_name("test_analog_logic.py"),
                    PROJECT / "Code/research/algorithm_study.py", PROJECT / "Code/research/backtest.py", PROJECT / "Code/research/daily.py", PROJECT / "Code/broker/sessions.py"]
    for source_path in source_paths:
        raw = source_path.read_bytes()
        declaration.setdefault("code_hashes", {})[str(source_path)] = hashlib.sha256(raw).hexdigest()
        (folder / "source" / source_path.name).write_bytes(raw)
    write_json(folder / "declaration.json", declaration)
    registry = PROJECT / "Data/research/experiments/registry.jsonl"
    record_event(registry, {"study": "market_analog_test_only", "run_id": run_id, "status": "declared", "folder": str(folder), "experiment": EXPERIMENT})
    results, cases = {}, []
    try:
        for month in paired_months:
            case = {"anchor_date": month["anchor_date"], "state": states[month["anchor_date"]],
                    "outcome_start": month["start"], "outcome_end": month["end"], "outcomes": {}}
            for family in FAMILIES:
                case["outcomes"][family] = {}
                for scenario, (scenario_costs, scenario_settings) in scenarios.items():
                    result = replay(series, features, proxy_features, family, True, scenario_costs, scenario_settings,
                                    start=month["start"], end=month["end"])
                    result = close_month(result, series, scenario_costs, scenario_settings, month["end"])
                    if result["summary"]["minimum_cash"] < -1e-6 or result["summary"]["maximum_positions"] > 5:
                        raise ArithmeticError("계좌 자금·보유 제한 위반")
                    for decision in result["decisions"]:
                        if decision["signal_date"] >= decision["execution_date"]:
                            raise ArithmeticError("다음 봉 체결 규칙 위반")
                    results[(month["month"], family, scenario)] = result
                    case["outcomes"][family][scenario] = result["summary"]
                    write_json(folder / "monthly" / (month["month"] + "-" + family + "-" + scenario + ".json"), result)
            cases.append(case)
            if month["month"].endswith("12") or month == paired_months[-1]:
                print("월별 원본 재생:", month["month"], len(results), flush=True)
        write_json(folder / "cases.json", cases)
        policies = {"analog12": (EXPERIMENT["policy"], None)}
        for neighbors in EXPERIMENT["sensitivity_neighbors"]:
            policies["analog" + str(neighbors)] = ({**EXPERIMENT["policy"], "neighbors": neighbors}, None)
        policies["history_all"] = (EXPERIMENT["policy"], "all_history")
        policies["recent12"] = (EXPERIMENT["policy"], "recent")
        decisions = {}
        for name, (policy, control) in policies.items():
            decisions[name] = [choose_strategy(states[month["anchor_date"]], cases, month["anchor_date"], FAMILIES, policy, control)
                               for month in evaluation]
        for family in FAMILIES:
            decisions["fixed_" + family] = [{"decision_date": month["anchor_date"], "selected": family} for month in evaluation]
        decisions["cash"] = [{"decision_date": month["anchor_date"], "selected": "cash"} for month in evaluation]
        date_checks = 0
        for traces in decisions.values():
            for trace in traces:
                for neighbor in trace.get("neighbors", []):
                    if not neighbor["anchor_date"] < trace["decision_date"] or neighbor["outcome_end"] > trace["decision_date"]:
                        raise ArithmeticError("선택에 미래 성과 사용")
                    date_checks += 1
        accounts = {name: {scenario: compound_months(evaluation, trace, results, scenario, costs["starting_cash"]["US"])
                           for scenario in scenarios} for name, trace in decisions.items()}
        write_json(folder / "decisions.json", decisions)
        for name, scenarios_for_policy in accounts.items():
            write_json(folder / (name + ".json"), scenarios_for_policy)
            summary = scenarios_for_policy["base"]["summary"]
            print(f"{name}: {summary['net_return']:.2%}, MDD {summary['max_drawdown']:.2%}, 현금 {summary['cash_months']}/{summary['months']}월", flush=True)
        current = choose_strategy(states[proxy_bars[-1]["date"]], cases, proxy_bars[-1]["date"], FAMILIES, EXPERIMENT["policy"])
        write_json(folder / "current-diagnostic.json", current)
        protected_after = protected_hashes()
        if protected_before != protected_after:
            raise ArithmeticError("실험 중 운용 코드·설정 해시 변경")
        checks = {"monthly_replays": len(results), "policy_accounts": len(accounts) * len(scenarios),
                  "date_checks": date_checks, "code_config_unchanged": True, "monthly_pnl_reconciled": True,
                  "compounded_pnl_reconciled": True, "next_bar_execution": True}
        summaries = {name: {scenario: result["summary"] for scenario, result in scenarios_for_policy.items()} for name, scenarios_for_policy in accounts.items()}
        write_json(folder / "summaries.json", summaries)
        write_json(folder / "validation.json", checks)
        write_report(folder, declaration, accounts, decisions, current, checks)
        plot_results(folder, accounts)
        destination = PROJECT / "Data/reports/market-analog"
        destination.mkdir(parents=True, exist_ok=True)
        for name in ("report.md", "performance.png", "comparison.png", "declaration.json", "summaries.json", "validation.json", "current-diagnostic.json"):
            shutil.copy2(folder / name, destination / name)
        write_json(folder.parent / "latest.json", {"folder": str(folder)})
        write_json(destination / "latest.json", {"folder": str(folder)})
        record_event(registry, {"study": "market_analog_test_only", "run_id": run_id, "status": "finished", "folder": str(folder), "validation": checks})
        with (PROJECT / "Docs/RESEARCH_LOG.md").open("a", encoding="utf-8") as stream:
            stream.write(f"\n## {run_id}: 과거 유사 상황으로 전략 선택 — 반영 없이 시험만\n\n- 사용자 요청에 따라 운용 Code·Config·계좌 변경 없이 Test/research의 실험만 실행.\n- 28종목, 월별 6개 원본 전략, 유사도 12개 주 실험·8/24 민감도·전체/최근 과거·고정 전략 비교. 월말 모두 청산하는 동일 조건.\n- 평가 {evaluation[0]['start']} ~ {evaluation[-1]['end']}. 주 실험 누적 {accounts['analog12']['base']['summary']['net_return']:.2%}, MDD {accounts['analog12']['base']['summary']['max_drawdown']:.2%}.\n- 보고서 [유사 상황 시험](../Data/reports/market-analog/report.md). 실행 보존 `{folder}`.\n")
        print("보고서:", destination / "report.md", flush=True)
    except Exception as error:
        record_event(registry, {"study": "market_analog_test_only", "run_id": run_id, "status": "failed", "error_type": type(error).__name__})
        raise


if __name__ == "__main__":
    main()
