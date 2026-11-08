"""48개 포트폴리오 가설 반복 비교 → 후보 고정 → 이후 기간 한 번 평가.

실행: python main.py --test portfolio. 수정 위치: ../Config/portfolio-research.json,
research/portfolio.py. 뉴스·장중 실시간 규칙과 독립이며 실제 주문을 보내지 않는다.
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone

from app.runtime import acquire_run_lock, load_run_settings, release_run_lock
from broker.legacy_toss import TossMarketClient, parse_symbol, read_credentials
from paths import PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT, CONFIG_ROOT
from research.backtest import validate_costs
from research.daily import prepare_daily_bars
from research.history import collect_history, write_json
from research.portfolio import candidate_rules, common_dates, simulate_portfolio, reversal_rules
from strategy.engine import parse_timestamp
from tools.analyze_conditions import price_discontinuities
from tools.research_peers import load_companies, select_historical_companies
from tools.research_cycles import previous_test_periods


def collect_adjusted(companies, settings, runtime, end_value):
    """수정주가 요청 자료는 원시 시세와 별도 저장한다. 완료 캐시는 인증 없이 재사용한다."""
    records = {}
    client = None
    end = parse_timestamp(end_value)
    for company in companies:
        market, symbol = parse_symbol(company["symbol"])
        path = DATA_ROOT / "history/adjusted" / f"{market}-{symbol}-{end.date().isoformat()}.json"
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            if (record.get("origin") != "toss_actual_historical_candles" or record.get("market") != market
                    or record.get("symbol") != symbol or record.get("interval") != "1d"
                    or record.get("requested_end") != end.isoformat()):
                raise ValueError("저장한 수정주가 자료의 출처·종목·기간이 요청과 다릅니다.")
            if record.get("collection_complete") and record.get("adjusted") is True:
                records[company["symbol"]] = record
                continue
        if client is None:
            client = TossMarketClient(*read_credentials(False, runtime["env_file"]))
        records[company["symbol"]] = collect_history(client, market, symbol, path, settings, now=end, interval="1d", adjusted=True)
    return records


def develop_market(series, market, costs, settings):
    """이 함수에는 최종 시험 가격이 없다. 모든 후보와 탈락 사유를 저장한다."""
    development_end = settings["development_end"][:10]
    validation_start = settings["validation_start"]
    training_end = max(day for day in common_dates(series, settings["training_start"], validation_start) if day < validation_start)
    spread = settings["assumed_spread_ratio"]
    stressed = {**costs, **{name: costs[name] * 2 for name in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
    baseline_rule = candidate_rules()[0]
    benchmarks = {"training": simulate_portfolio(series, market, baseline_rule, costs, spread, settings["training_start"], training_end, True)["summary"],
                  "validation": simulate_portfolio(series, market, baseline_rule, costs, spread, validation_start, development_end, True)["summary"]}
    trials = []
    rules = candidate_rules() + reversal_rules()
    for trial_number, rule in enumerate(rules, 1):
        training = simulate_portfolio(series, market, rule, costs, spread, settings["training_start"], training_end)["summary"]
        validation = simulate_portfolio(series, market, rule, costs, spread, validation_start, development_end)["summary"]
        stress = simulate_portfolio(series, market, rule, stressed, spread * 2, validation_start, development_end)["summary"]
        checks = {"training_positive": training["net_return"] > 0,
                  "validation_positive": validation["net_return"] > 0,
                  "validation_beats_benchmark": validation["net_return"] > benchmarks["validation"]["net_return"],
                  "double_cost_positive": stress["net_return"] > 0,
                  "validation_drawdown": validation["max_drawdown"] <= settings["maximum_test_drawdown"]}
        trial = {"trial_number": trial_number, "rule": rule, "training": training,
                 "validation": validation, "validation_double_cost": stress, "checks": checks}
        trials.append(trial)
        print(f"{market} {trial_number}/{len(rules)} {rule['family']}: 검증 {validation['net_return']:.2%}, 낙폭 {validation['max_drawdown']:.2%}", flush=True)
    eligible = [trial for trial in trials if all(trial["checks"].values())]
    # 적격 없음도 저장한다. 실패 후보를 참고 평가할 경우 승인 후보와 명시적으로 구분한다.
    pool = eligible or trials
    selected = max(pool, key=lambda trial: trial["validation"]["net_return"] - trial["validation"]["max_drawdown"])
    return {"trials": trials, "selected": selected, "eligible_count": len(eligible),
            "development_passed": bool(eligible), "benchmarks": benchmarks}


def verify_continuity(old_records, new_records, test_start):
    """새 요청이 과거 수정주가를 바꾸면 서로 다른 가격 척도를 섞지 않고 중단한다."""
    for symbol, record in old_records.items():
        old = {bar["date"]: bar for bar in prepare_daily_bars(record)}
        new = {bar["date"]: bar for bar in prepare_daily_bars(new_records[symbol])}
        overlap = [day for day in old if day in new and day < test_start]
        if len(overlap) < 120:
            raise ValueError(f"{symbol}: 수정주가 연속성 검사 표본 부족")
        for day in overlap:
            for field in ("open", "high", "low", "close"):
                if abs(new[day][field] / old[day][field] - 1) > .0001:
                    raise ValueError(f"{symbol}: 이후 요청에서 과거 수정주가 변경. 재개발 필요: {day}")


def write_report(folder, report):
    lines = ["# 포트폴리오 반복 개발·이후 기간 시험", "", "실제 토스 일봉, 수정주가 요청, 가상 체결·비용 반영. 장중 뉴스 전략의 실거래 성과가 아니다.",
             f"시험: {report['settings']['test_start']}~{report['settings']['test_end'][:10]}. 시장별 공통 거래일만 사용한다.",
             "48개 후보/시장: 기존 24개 모멘텀 가설 + 추세 속 눌림·과매도 반등 24개 가설. 이전 실행은 별도 폴더에 보존한다.",
             "시장별 단일 자금 풀, 초기 자금 10%/종목·최대 3종목. 모멘텀 고정 손절 8%·추적 손절 12%, 반등 가설은 5%·8%. 빈 슬롯은 현금.",
             "검증에서 후보를 고정하고 이후 시험한다. 적격 후보가 없으면 참고 후보의 결과를 표시하되 승인하지 않는다.", "",
             "| 시장 | 훈련 수익 | 검증 수익 | 최종 시험 수익 | 단순 보유 | 2배 비용 | 낙폭 | 거래 | 판정 |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for market, result in report["markets"].items():
        candidate = result["development"]["selected"]
        summary = result["test"]["summary"]
        lines.append(f"| {market} | {candidate['training']['net_return']:.2%} | {candidate['validation']['net_return']:.2%} | {summary['net_return']:.2%} | {result['benchmark']['summary']['net_return']:.2%} | {result['stress']['summary']['net_return']:.2%} | {summary['max_drawdown']:.2%} | {summary['trades']} | {result['verdict']} |")
    for market, result in report["markets"].items():
        lines.extend(["", f"## {market}", "", f"종목: {', '.join(result['symbols'])}",
                      f"고정 후보: `{result['development']['selected']['rule']}`", f"개발 적격 후보: {result['development']['eligible_count']}개", "",
                      "| 후보 | 훈련 | 검증 | 검증 낙폭 | 검증 2배 비용 | 적격 |", "| --- | ---: | ---: | ---: | ---: | --- |"])
        for trial in result["development"]["trials"]:
            lines.append(f"| {trial['trial_number']} | {trial['training']['net_return']:.2%} | {trial['validation']['net_return']:.2%} | {trial['validation']['max_drawdown']:.2%} | {trial['validation_double_cost']['net_return']:.2%} | {all(trial['checks'].values())} |")
        lines.extend(["", *[f"- {name}: {'통과' if passed else '실패'}" for name, passed in result["checks"].items()]])
    lines.extend(["", "## 자료 품질·해석", "", "- 현재 선정한 종목군을 과거에 적용하므로 생존·선정 편향이 남는다. GOOG는 동일 회사 중복으로 제외, SpaceX는 예열 이력 부족으로 제외했다.",
                  "- API에 adjusted=true를 요청했지만 배당·분사 보정 방식과 수정 단위의 정수 수량은 독립 검증되지 않았다. 수정주가 단위의 가상 수량이다.",
                  "- 단순 보유는 동일 종목군·총 30% 초기 투자 비중·비용을 사용한다. 전략의 실제 노출은 더 작거나 가격 상승으로 더 커질 수 있다.",
                  "- KRW·USD 수익을 합산하지 않는다. 동일 섹터의 상관된 거래는 독립 표본이 아니다.",
                  "- 유동성·역사 세금·환율·뉴스·장중 호가·부분 체결·실제 체결 지연은 미검증이다.",
                  "- 최종 시험을 재실행하거나 이미 본 날짜와 겹치면 탐색으로 판정한다. 같은 구간에서 흑자가 나올 때까지 조정하면 새 검증이 아니다.",
                  "- 최소 30거래·낙폭 5%·초과 수익 등은 연구 기준이며 통과해도 실전 수익성 승인으로 취급하지 않는다.",
                  f"- 시험 기간 재사용: {report['test_reused']}", f"- 비용 가정: `{report['costs']}`", "",
                  "![실제 자료를 사용한 가상 포트폴리오 수익](portfolio.png)"])
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_report(folder, report):
    import os
    os.environ.setdefault("MPLCONFIGDIR", str(DATA_ROOT / "cache/plots"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plot
    figure, axes = plot.subplots(2, 1, figsize=(11, 8), constrained_layout=True)
    for axis, (market, result) in zip(axes, report["markets"].items()):
        starting = report["costs"]["starting_cash"][market]
        adaptive = "selections" in result["test"]
        for name, label in (("test", "Past-only rolling selection" if adaptive else "Frozen rotation rule"),
                            ("benchmark", "Same-universe 30% buy/hold"),
                            ("stress", ("Double-cost rolling selection" if "selections" in result["stress"] else "Fixed selections, double execution costs") if adaptive else "Rule with double costs")):
            curve = result[name]["curve"]
            axis.plot(range(len(curve)), [(row["equity"] / starting - 1) * 100 for row in curve], label=label)
        curve = result["test"]["curve"]
        indices = sorted({0, len(curve) // 2, len(curve) - 1})
        axis.set_xticks(indices, [curve[index]["date"] for index in indices])
        axis.set_title(market + " — actual price inputs, simulated fills")
        axis.set_ylabel("Account return (%)")
        axis.legend()
        axis.grid(alpha=.25)
    figure.savefig(folder / "portfolio.png", dpi=150)
    plot.close(figure)


def main():
    settings = json.loads((CONFIG_ROOT / "portfolio-research.json").read_text(encoding="utf-8"))
    if not settings["training_start"] < settings["validation_start"] < settings["development_end"][:10] < settings["test_start"] < settings["test_end"][:10]:
        raise ValueError("훈련·검증·시험 날짜가 겹치거나 순서가 잘못됐습니다.")
    runtime = load_run_settings()
    costs = json.loads(runtime["paper_settings"].read_text(encoding="utf-8"))
    validate_costs(costs)
    companies, skipped = select_historical_companies(load_companies(), settings["training_start"])
    companies = [company for company in companies if company["symbol"] != "US:GOOG"]
    base = RESULTS_ROOT / "portfolio"
    base.mkdir(parents=True, exist_ok=True)
    runtime["output_dir"].mkdir(parents=True, exist_ok=True)
    lock = acquire_run_lock(runtime["output_dir"] / "run.lock")
    folder = base / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir()
    try:
        write_json(folder / "declaration.json", {"settings": settings, "costs": costs, "companies": companies,
                   "skipped": skipped, "candidates": candidate_rules() + reversal_rules(), "purpose": "bounded_portfolio_development"})
        old_records = collect_adjusted(companies, settings, runtime, settings["development_end"])
        series = {symbol: prepare_daily_bars(record) for symbol, record in old_records.items()}
        warnings = {symbol: price_discontinuities(bars) for symbol, bars in series.items() if price_discontinuities(bars)}
        if warnings:
            write_json(folder / "data-quality-failure.json", warnings)
            raise ValueError("수정주가 요청 자료에도 큰 가격 단절이 있습니다. 기업행동 확인 전 시험 중단")
        development = {}
        for market in ("KR", "US"):
            selected_series = {symbol: bars for symbol, bars in series.items() if symbol.startswith(market + ":")}
            development[market] = develop_market(selected_series, market, costs, settings)
        hashes = {symbol: hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest() for symbol, record in old_records.items()}
        # 이후 기간을 가져오기 전에 후보·개발 결과·코드·원자료 지문을 보관한다.
        write_json(folder / "frozen.json", {"development": development, "data_hashes": hashes})
        source = folder / "source"
        source.mkdir()
        for path in (PROJECT_ROOT / "research/portfolio.py", PROJECT_ROOT / "research/history.py", PROJECT_ROOT / "tools/research_portfolio.py"):
            shutil.copy2(path, source / path.name)
        registry_path = DATA_ROOT / "history/portfolio-test-periods.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else []
        previous_periods = registry + previous_test_periods()
        reused = any(settings["test_start"] <= period["end"] and settings["test_end"][:10] >= period["start"] for period in previous_periods)
        # 실패·중단한 실행도 이미 열어본 기간으로 기록한다.
        registry.append({"start": settings["test_start"], "end": settings["test_end"][:10], "folder": str(folder)})
        write_json(registry_path, registry)
        new_records = collect_adjusted(companies, settings, runtime, settings["test_end"])
        verify_continuity(old_records, new_records, settings["test_start"])
        new_series = {symbol: prepare_daily_bars(record) for symbol, record in new_records.items()}
        if any(price_discontinuities(bars) for bars in new_series.values()):
            raise ValueError("이후 기간 수정주가 자료에도 큰 가격 단절이 있습니다. 확인 전 시험 중단")
        markets = {}
        stressed = {**costs, **{name: costs[name] * 2 for name in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
        for market in ("KR", "US"):
            selected_series = {symbol: bars for symbol, bars in new_series.items() if symbol.startswith(market + ":")}
            rule = development[market]["selected"]["rule"]
            arguments = (selected_series, market, rule)
            period = (settings["test_start"], settings["test_end"][:10])
            test = simulate_portfolio(*arguments, costs, settings["assumed_spread_ratio"], *period)
            benchmark = simulate_portfolio(*arguments, costs, settings["assumed_spread_ratio"], *period, buy_and_hold=True)
            stress = simulate_portfolio(*arguments, stressed, settings["assumed_spread_ratio"] * 2, *period)
            summary = test["summary"]
            checks = {"development_passed": development[market]["development_passed"], "test_positive": summary["net_return"] > 0,
                      "beats_benchmark": summary["net_return"] > benchmark["summary"]["net_return"],
                      "double_cost_positive": stress["summary"]["net_return"] > 0,
                      "drawdown_limit": summary["max_drawdown"] <= settings["maximum_test_drawdown"],
                      "minimum_trades": summary["trades"] >= settings["minimum_test_trades"], "unused_period": not reused}
            verdict = "historical_candidate_passed" if all(checks.values()) else "rejected"
            markets[market] = {"development": development[market], "symbols": list(selected_series), "test": test,
                               "benchmark": benchmark, "stress": stress, "checks": checks, "verdict": verdict}
            print(f"{market}: 최종 수익 {summary['net_return']:.2%}, 보유 {benchmark['summary']['net_return']:.2%}, {summary['trades']}거래, {verdict}")
        report = {"settings": settings, "costs": costs, "markets": markets, "test_reused": reused,
                  "test_data_hashes": {symbol: hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest() for symbol, record in new_records.items()}}
        write_json(folder / "results.json", report)
        write_report(folder, report)
        plot_report(folder, report)
        write_json(base / "latest.json", {"folder": str(folder)})
        print(f"최종 포트폴리오 보고서: {folder / 'report.md'}")
    finally:
        release_run_lock(lock)


if __name__ == "__main__":
    main()
