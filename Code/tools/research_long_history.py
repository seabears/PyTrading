"""현재 규칙을 바꾸지 않고 2020년부터 장기·연도별 모의 성과를 평가한다.

실행: python main.py --test long-history. 기간·수집 한도는 ../Config/long-history.json.
종목 수익을 보고 제외하지 않는다. 상장 이력·동일 회사 중복 제외는 결과 전에 선언한다.
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone, date
from pathlib import Path

from app.runtime import acquire_run_lock, load_run_settings, release_run_lock
from paths import PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT, CONFIG_ROOT
from research.daily import prepare_daily_bars
from research.history import write_json
from research.portfolio import candidate_rules, reversal_rules, common_dates, simulate_portfolio, simulate_walk_forward, replay_selected_rules, stress_recorded_trades
from tools.analyze_conditions import price_discontinuities
from tools.research_peers import load_companies
from tools.research_portfolio import plot_report


def load_settings():
    settings = json.loads((CONFIG_ROOT / "long-history.json").read_text(encoding="utf-8"))
    if not 365 <= settings["history_days"] <= 3650 or not 1 <= settings["max_pages_per_symbol"] <= 30:
        raise ValueError("장기 수집 범위는 365~3650일, 1~30페이지여야 합니다.")
    if not .05 <= settings["request_interval_seconds"] <= 2:
        raise ValueError("요청 간격은 0.05~2초여야 합니다.")
    end = date.fromisoformat(settings["test_end"][:10])
    if end >= datetime.now(timezone.utc).date():
        raise ValueError("완료된 과거 거래일까지만 평가할 수 있습니다.")
    for cohort in settings["cohorts"]:
        if date.fromisoformat(cohort["start"]) >= end:
            raise ValueError("장기 시험 시작은 종료일보다 이전이어야 합니다.")
    return settings


def annual_results(result, starting_cash):
    """연말 계좌 가치/직전 연말 가치로 계산한다. 매년 자금을 다시 시작하지 않는다."""
    curve = result["curve"]
    years = sorted({row["date"][:4] for row in curve})
    previous_equity = starting_cash
    rows = []
    for year in years:
        yearly_curve = [row for row in curve if row["date"].startswith(year)]
        final_equity = yearly_curve[-1]["equity"]
        peak = previous_equity
        maximum_drawdown = 0.0
        for row in yearly_curve:
            peak = max(peak, row["equity"])
            maximum_drawdown = max(maximum_drawdown, 1 - row["equity"] / peak)
        completed = [trade for trade in result["trades"] if trade["exit_date"].startswith(year)]
        rows.append({"year": year, "start": yearly_curve[0]["date"], "end": yearly_curve[-1]["date"],
                     "return": final_equity / previous_equity - 1, "max_drawdown": maximum_drawdown, "trades": len(completed)})
        previous_equity = final_equity
    return rows


def write_report(folder, report):
    lines = ["# 기간 확장: 고정된 선택 방식의 장기 평가", "", "실제 토스 수정주가 요청 일봉·가상 체결·비용 포함. 실거래 수익이 아니다.",
             "이전 4개월 결과를 보고 추가로 과거를 확장했다. 일부 기간은 기존 개발·시험과 겹치므로 새로운 독립 검증으로 부르지 않는다.",
             "48개 가설·최근 훈련 63일/검증 21일·다음 21일 적용·엄격 선택·최소 5일 보유를 유지했다.",
             "전체 기간에 현금을 이월하며, 순차 선택 구간 말 청산 비용을 적용한다. 원화·달러는 별도 계좌다.",
             "| 종목군 | 시장 | 실제 기간 | 최종 수익 | 고정 거래 비용 2배 | 단순 보유 | 최대 낙폭 | 거래 |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, cohort in report["cohorts"].items():
        for market, result in cohort["markets"].items():
            summary = result["test"]["summary"]
            curve = result["test"]["curve"]
            lines.append(f"| {name} | {market} | {curve[0]['date']}~{curve[-1]['date']} | {summary['net_return']:.2%} | {result['recorded_trade_stress']['net_return']:.2%} | {result['benchmark']['summary']['net_return']:.2%} | {summary['max_drawdown']:.2%} | {summary['trades']} |")
    for name, cohort in report["cohorts"].items():
        lines.extend(["", f"## {name}: 연도별"])
        for market, result in cohort["markets"].items():
            lines.extend(["", f"### {market}", "", "| 시장 | 연도 | 실제 시작~끝 | 계좌 수익 | 보유 수익 | 연중 낙폭 | 완료 거래 |",
                          "| --- | --- | --- | ---: | ---: | ---: | ---: |"])
            benchmarks = {row["year"]: row for row in result["annual_benchmark"]}
            for row in result["annual"]:
                lines.append(f"| {market} | {row['year']} | {row['start']}~{row['end']} | {row['return']:.2%} | {benchmarks[row['year']]['return']:.2%} | {row['max_drawdown']:.2%} | {row['trades']} |")
            lines.extend(["", f"{market} 종목: {', '.join(result['symbols'])}"])
            lines.extend(f"- {market} {check}: {'통과' if passed else '실패'}" for check, passed in result["checks"].items())
        lines.extend(["", f"![{name} 계좌·비용·기준선]({name}/portfolio.png)"])
    lines.extend(["", "## 자료·제외 사유·한계", "", "- long: Arm은 2023년부터, 현재 SONY 티커 응답은 2021년부터 자료가 있어 2020년 예열 자료 부족으로 제외. 두 종목 모두 recent에는 포함한다.",
                  "- SpaceX는 2026년 상장으로 충분한 예열 자료가 없어 두 종목군에서 제외. GOOG는 GOOGL과 동일 회사 중복으로 제외한다.",
                  "- 각 시장에서 모든 종목의 공통 거래일을 사용한다. 누락일 수와 날짜는 results.json의 coverage에 저장한다.",
                  "- 과거 기업행동 수정주가의 독립 검증, 배당·분사·역사 비용·세금·실제 호가·환율은 미검증이다.",
                  "- 현재 생존 종목을 과거에 적용한 선정·생존 편향이 남는다. 상관된 기술주 거래를 독립 표본으로 합산하지 않는다.",
                  "- 2026년은 연초~10월의 부분 연도이며, recent의 2024년도 부분 연도다. 30거래는 연구 하한일 뿐 수익성 증명이 아니다.",
                  "- 고정 거래 비용 2배는 같은 체결 날짜·수량의 비용 민감도다. 고정 선택을 비용 2배로 재운용한 곡선도 별도 저장한다.",
                  "- 단순 보유는 초기 총 30% 투자 후 비중이 가격과 함께 증가한다. 전략은 구간마다 예산을 재산정하므로 실제 시장 노출·위험은 서로 다르다. 현금 이자는 포함하지 않았다.",
                  "- 기간을 늘린 것만으로 과최적화가 없어지지 않는다. 이번 결과를 보고 규칙을 다시 고치면 후속 결과도 탐색이다.",
                  "- 실시간 장중 뉴스 엔진·실제 주문 설정은 변경하지 않았다."])
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    settings = load_settings()
    runtime = load_run_settings()
    pointer = json.loads((RESULTS_ROOT / "adaptive-robust/latest.json").read_text(encoding="utf-8"))
    previous = json.loads((Path(pointer["folder"]) / "results.json").read_text(encoding="utf-8"))
    costs = previous["costs"]
    spread = previous["settings"]["assumed_spread_ratio"]
    base = RESULTS_ROOT / "long-history"
    folder = base / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True)
    companies = load_companies()
    wanted = {company["symbol"] for company in companies if any(company["symbol"] not in cohort["excluded_symbols"] for cohort in settings["cohorts"])}
    companies = [company for company in companies if company["symbol"] in wanted]
    rules = candidate_rules() + reversal_rules()
    write_json(folder / "declaration.json", {"settings": settings, "costs": costs, "spread": spread,
               "companies": companies, "frozen_rules": rules, "previous_report": pointer["folder"], "purpose": "extend_history_without_retuning"})
    source = folder / "source"
    source.mkdir()
    for path in (PROJECT_ROOT / "research/portfolio.py", PROJECT_ROOT / "tools/research_long_history.py", PROJECT_ROOT / "research/history.py"):
        shutil.copy2(path, source / path.name)
    # 자료 기간이 늘었으므로 기존 3년 캐시와 파일명을 분리한다. collect_adjusted의 검증을 그대로 쓴다.
    from broker.legacy_toss import TossMarketClient, read_credentials, parse_symbol
    from research.history import collect_history
    from strategy.engine import parse_timestamp
    runtime["output_dir"].mkdir(parents=True, exist_ok=True)
    lock = acquire_run_lock(runtime["output_dir"] / "run.lock")
    records = {}
    try:
        client = None
        for company in companies:
            market, symbol = parse_symbol(company["symbol"])
            path = DATA_ROOT / "history/long-adjusted" / f"{market}-{symbol}-{settings['test_end'][:10]}.json"
            if path.exists():
                saved = json.loads(path.read_text(encoding="utf-8"))
                if (saved.get("origin") != "toss_actual_historical_candles" or saved.get("market") != market
                        or saved.get("symbol") != symbol or saved.get("adjusted") is not True
                        or saved.get("interval") != "1d" or saved.get("requested_end") != parse_timestamp(settings["test_end"]).isoformat()):
                    raise ValueError("장기 시세 캐시의 출처·종목·기간·수정주가 설정이 다릅니다.")
                if saved.get("collection_complete"):
                    records[company["symbol"]] = saved
                    continue
            if client is None:
                client = TossMarketClient(*read_credentials(False, runtime["env_file"]))
            records[company["symbol"]] = collect_history(client, market, symbol, path, settings, now=parse_timestamp(settings["test_end"]), interval="1d", adjusted=True)
    finally:
        release_run_lock(lock)
    series = {symbol: prepare_daily_bars(record) for symbol, record in records.items()}
    warnings = {symbol: price_discontinuities(bars) for symbol, bars in series.items() if price_discontinuities(bars)}
    if warnings:
        write_json(folder / "data-quality-failure.json", warnings)
        raise ValueError("장기 수정주가에도 큰 가격 단절이 있어 분석을 중단했습니다.")
    cohorts = {}
    stressed = {**costs, **{key: costs[key] * 2 for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
    for cohort in settings["cohorts"]:
        markets = {}
        for market in ("KR", "US"):
            selected = {symbol: bars for symbol, bars in series.items() if symbol.startswith(market + ":") and symbol not in cohort["excluded_symbols"]}
            start, end = cohort["start"], settings["test_end"][:10]
            days = common_dates(selected, start, end)
            if not days or days[0] > start[:4] + "-01-10" and cohort["name"] == "long":
                raise ValueError(f"{cohort['name']} {market}: 요청한 장기 시작 자료가 부족합니다.")
            print(f"{cohort['name']} {market}: {days[0]}~{days[-1]}, {len(days)}거래일, {len(selected)}종목 순차 평가 시작", flush=True)
            result = simulate_walk_forward(selected, market, costs, spread, start, end, strict_selection=True, rules_override=rules)
            stress = replay_selected_rules(selected, market, stressed, spread * 2, result["selections"])
            recorded = stress_recorded_trades(result["trades"], costs["starting_cash"][market], costs, stressed, spread, spread * 2)
            benchmark = simulate_portfolio(selected, market, rules[0], costs, spread, start, end, buy_and_hold=True)
            summary = result["summary"]
            checks = {"positive": summary["net_return"] > 0, "beats_benchmark": summary["net_return"] > benchmark["summary"]["net_return"],
                      "double_cost_positive": recorded["net_return"] > 0, "drawdown_limit": summary["max_drawdown"] <= .05,
                      "minimum_trades": summary["trades"] >= 30, "independent_period": False}
            coverage = {}
            for symbol, bars in selected.items():
                own_dates = {bar["date"] for bar in bars if start <= bar["date"] <= end}
                removed = sorted(own_dates - set(days))
                coverage[symbol] = {"raw_start": bars[0]["date"], "raw_end": bars[-1]["date"], "removed_dates": removed}
            markets[market] = {"test": result, "stress": stress, "recorded_trade_stress": recorded, "benchmark": benchmark,
                               "annual": annual_results(result, costs["starting_cash"][market]), "annual_benchmark": annual_results(benchmark, costs["starting_cash"][market]),
                               "symbols": list(selected), "checks": checks, "coverage": coverage}
            print(f"{cohort['name']} {market}: 수익 {summary['net_return']:.2%}, 낙폭 {summary['max_drawdown']:.2%}, {summary['trades']}거래", flush=True)
        cohorts[cohort["name"]] = {"markets": markets}
        cohort_folder = folder / cohort["name"]
        cohort_folder.mkdir()
        write_json(cohort_folder / "results.json", {"settings": settings, "costs": costs, "markets": markets})
        plot_report(cohort_folder, {"costs": costs, "markets": markets})
    report = {"settings": settings, "costs": costs, "cohorts": cohorts,
              "source_hashes": {symbol: hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest() for symbol, record in records.items()}}
    write_json(folder / "results.json", report)
    write_report(folder, report)
    write_json(base / "latest.json", {"folder": str(folder)})
    print(f"장기 평가 보고서: {folder / 'report.md'}")


if __name__ == "__main__":
    main()
