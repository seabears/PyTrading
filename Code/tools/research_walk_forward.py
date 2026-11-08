"""세 번째 수정: 과거 63/21일로 규칙을 고르고 다음 21일에만 적용한다.

실행 python main.py --test adaptive. 기존 시험 날짜를 재사용한 탐색임을 명시한다.
"""
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

from paths import PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT
from research.daily import prepare_daily_bars
from research.history import write_json
from research.portfolio import candidate_rules, simulate_portfolio, simulate_walk_forward, replay_selected_rules, stress_recorded_trades
from tools.research_portfolio import plot_report


def main(strict_selection=False):
    pointer = json.loads((RESULTS_ROOT / "portfolio/latest.json").read_text(encoding="utf-8"))
    previous = json.loads((Path(pointer["folder"]) / "results.json").read_text(encoding="utf-8"))
    settings, costs = previous["settings"], previous["costs"]
    base = RESULTS_ROOT / ("adaptive-robust" if strict_selection else "adaptive")
    folder = base / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True)
    write_json(folder / "declaration.json", {"training_days": 63, "validation_days": 21, "selection_days": 21,
               "cash_if_no_eligible_candidate": True, "strict_selection": strict_selection, "test_reused": True, "previous_report": pointer["folder"]})
    source = folder / "source"
    source.mkdir()
    for path in (PROJECT_ROOT / "research/portfolio.py", PROJECT_ROOT / "tools/research_walk_forward.py"):
        shutil.copy2(path, source / path.name)
    markets = {}
    for market, old in previous["markets"].items():
        series = {}
        for symbol in old["symbols"]:
            path = DATA_ROOT / "history/adjusted" / (symbol.replace(":", "-") + "-" + settings["test_end"][:10] + ".json")
            series[symbol] = prepare_daily_bars(json.loads(path.read_text(encoding="utf-8")))
        period = (settings["test_start"], settings["test_end"][:10])
        result = simulate_walk_forward(series, market, costs, settings["assumed_spread_ratio"], *period, strict_selection=strict_selection)
        stressed = {**costs, **{key: costs[key] * 2 for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
        stress = simulate_walk_forward(series, market, stressed, settings["assumed_spread_ratio"] * 2, *period, strict_selection=strict_selection)
        execution_stress = replay_selected_rules(series, market, stressed, settings["assumed_spread_ratio"] * 2, result["selections"])
        recorded_stress = stress_recorded_trades(result["trades"], costs["starting_cash"][market], costs, stressed,
                                                settings["assumed_spread_ratio"], settings["assumed_spread_ratio"] * 2)
        benchmark = simulate_portfolio(series, market, candidate_rules()[0], costs, settings["assumed_spread_ratio"], *period, buy_and_hold=True)
        markets[market] = {"test": result, "benchmark": benchmark, "stress": stress, "execution_stress": execution_stress}
        markets[market]["recorded_trade_stress"] = recorded_stress
        summary = result["summary"]
        markets[market]["checks"] = {"positive": summary["net_return"] > 0,
                                    "beats_benchmark": summary["net_return"] > benchmark["summary"]["net_return"],
                                    "double_cost_reselection_positive": stress["summary"]["net_return"] > 0,
                                    "fixed_selection_double_cost_positive": execution_stress["summary"]["net_return"] > 0,
                                    "fixed_trades_double_cost_positive": recorded_stress["net_return"] > 0,
                                    "drawdown_limit": summary["max_drawdown"] <= settings["maximum_test_drawdown"],
                                    "minimum_trades": summary["trades"] >= settings["minimum_test_trades"],
                                    "independent_period": False}
        print(f"{market} 순차 재선정: 수익 {result['summary']['net_return']:.2%}, 낙폭 {result['summary']['max_drawdown']:.2%}, {result['summary']['trades']}거래", flush=True)
    report = {"settings": settings, "costs": costs, "markets": markets, "test_reused": True, "strict_selection": strict_selection}
    write_json(folder / "results.json", report)
    lines = ["# 순차 규칙 선택·회전 비용 검토", "", "실제 토스 수정주가 요청 일봉, 가상 체결·비용 반영. 재사용 시험 구간의 탐색이며 독립 검증이 아니다.",
             "최근 과거 훈련 63일·검증 21일로 48개 후보를 비교해 다음 21거래일에만 적용한다.",
             "훈련·검증 모두 흑자이고 검증 거래 3건 이상인 후보 중 수익−낙폭 최대를 고른다. 없으면 현금.",
             "엄격 선택에서는 검증 2배 비용 흑자·단순 보유 초과·낙폭 5% 이하도 요구한다." if strict_selection else "기본 순차 선택이며 비용 스트레스는 사후 평가한다.",
             "각 교체 구간 말 청산 비용을 지불한다. 계좌 자금을 다음 구간에 이월한다. 2배 비용은 같은 선택 알고리즘을 비용 2배로 재평가한 결과다.",
             "순위 교체는 최소 5거래일 보유 후 허용한다. 고정·추적 손절과 시험 구간 말 청산은 즉시 처리한다.",
             "고정 선택 재생은 손절선·정수 수량 변화로 청산 경로가 달라질 수 있다. 거래 날짜·수량까지 고정한 순수 비용 민감도도 별도로 계산한다.",
             "| 시장 | 최종 수익 | 2배 비용 재선정 | 고정 선택·비용 2배 | 고정 거래·비용 2배 | 단순 보유 | 낙폭 | 거래 |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for market, result in markets.items():
        summary = result["test"]["summary"]
        lines.append(f"| {market} | {summary['net_return']:.2%} | {result['stress']['summary']['net_return']:.2%} | {result['execution_stress']['summary']['net_return']:.2%} | {result['recorded_trade_stress']['net_return']:.2%} | {result['benchmark']['summary']['net_return']:.2%} | {summary['max_drawdown']:.2%} | {summary['trades']} |")
    lines.extend(["", "## 구간별 고정 선택", "", "| 시장 | 선택일 | 적용 시작 | 적용 끝 | 선택 후보 |", "| --- | --- | --- | --- | --- |"])
    for market, result in markets.items():
        for selection in result["test"]["selections"]:
            selected = selection["selected"]
            lines.append(f"| {market} | {selection['selected_at']} | {selection['start']} | {selection['end']} | {selected['rule'] if selected else '현금'} |")
    lines.extend(["", "## 판정", ""])
    for market, result in markets.items():
        lines.extend(f"- {market} {name}: {'통과' if passed else '실패'}" for name, passed in result["checks"].items())
    lines.extend(["", "수익 양수도 이번 재사용 구간의 탐색 결과다. 흑자·초과 수익·비용 스트레스·충분한 표본·독립 시험을 모두 확인하기 전 실전 승인하지 않는다.",
                  "현재 선정 종목의 생존 편향, 수정주가·배당·역사 비용·실제 체결 검증 한계는 이전 포트폴리오 보고서와 같다.",
                  "장중 뉴스 엔진에는 적용하지 않았다.", "", "![순차 규칙 선택의 가상 수익](portfolio.png)"])
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    plot_report(folder, report)
    write_json(base / "latest.json", {"folder": str(folder)})
    print(f"순차 검증 보고서: {folder / 'report.md'}")


if __name__ == "__main__":
    main()
