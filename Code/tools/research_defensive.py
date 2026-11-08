"""다섯 번째 탐색: 시장 추세가 약할 때 실제 1배 인버스 ETF 또는 현금.

지수 수익의 부호를 바꾼 합성 ETF를 사용하지 않는다. 실제 ETF 일봉·비용을 재생한다.
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.runtime import acquire_run_lock, load_run_settings, release_run_lock
from paths import PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT
from research.daily import prepare_daily_bars
from research.history import write_json
from research.portfolio import candidate_rules, reversal_rules, simulate_walk_forward
from tools.research_portfolio import collect_adjusted, plot_report


DEFENSIVE_MARKETS = {
    "KR": {"market_proxy": "KR:069500", "defensive_symbol": "KR:114800"},
    "US": {"market_proxy": "US:SPY", "defensive_symbol": "US:SH"},
}


def main():
    pointer = json.loads((RESULTS_ROOT / "portfolio/latest.json").read_text(encoding="utf-8"))
    previous = json.loads((Path(pointer["folder"]) / "results.json").read_text(encoding="utf-8"))
    settings, costs = previous["settings"], previous["costs"]
    folder = RESULTS_ROOT / "defensive" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True)
    write_json(folder / "declaration.json", {"test_reused": True, "market_trend_days": 50,
               "markets": DEFENSIVE_MARKETS, "selection_days": 21, "stock_universe": {market: result["symbols"] for market, result in previous["markets"].items()}})
    source = folder / "source"
    source.mkdir()
    for path in (PROJECT_ROOT / "research/portfolio.py", PROJECT_ROOT / "tools/research_defensive.py"):
        shutil.copy2(path, source / path.name)
    runtime = load_run_settings()
    runtime["output_dir"].mkdir(parents=True, exist_ok=True)
    lock = acquire_run_lock(runtime["output_dir"] / "run.lock")
    try:
        instruments = [{"symbol": symbol} for policy in DEFENSIVE_MARKETS.values() for symbol in policy.values()]
        records = collect_adjusted(instruments, settings, runtime, settings["test_end"])
    finally:
        release_run_lock(lock)
    markets = {}
    for market, old in previous["markets"].items():
        series = {}
        for symbol in old["symbols"]:
            path = DATA_ROOT / "history/adjusted" / (symbol.replace(":", "-") + "-" + settings["test_end"][:10] + ".json")
            series[symbol] = prepare_daily_bars(json.loads(path.read_text(encoding="utf-8")))
        for symbol in DEFENSIVE_MARKETS[market].values():
            series[symbol] = prepare_daily_bars(records[symbol])
        rules = [{**rule, **DEFENSIVE_MARKETS[market]} for rule in candidate_rules() + reversal_rules()]
        arguments = (series, market, costs, settings["assumed_spread_ratio"], settings["test_start"], settings["test_end"][:10])
        result = simulate_walk_forward(*arguments, strict_selection=True, rules_override=rules)
        stressed = {**costs, **{key: costs[key] * 2 for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
        stress = simulate_walk_forward(series, market, stressed, settings["assumed_spread_ratio"] * 2,
                                       settings["test_start"], settings["test_end"][:10], strict_selection=True, rules_override=rules)
        # 비교군 변경으로 겉보기 초과 수익을 만들지 않는다. 원래 주식군 30% 보유와 비교한다.
        markets[market] = {"test": result, "stress": stress, "benchmark": old["benchmark"]}
        print(f"{market} 방어형: 수익 {result['summary']['net_return']:.2%}, 비용 두 배 {stress['summary']['net_return']:.2%}", flush=True)
    report = {"settings": settings, "costs": costs, "markets": markets, "test_reused": True,
              "source_hashes": {symbol: hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest() for symbol, record in records.items()}}
    write_json(folder / "results.json", report)
    lines = ["# 다섯 번째 탐색: 시장 추세·실제 인버스 ETF", "", "실제 토스 일봉·가상 체결. 재사용 구간 탐색이며 실전 수익성 승인이 아니다.",
             "시장 대용 ETF 종가가 50일 평균 아래이면 주식 신규 진입 대신 실제 인버스 ETF 하나만 평가한다. 조건 미달이면 현금.",
             "한국은 069500/114800, 미국은 SPY/SH. 일간 역방향 목표 ETF이며 장기간 지수 수익의 단순 음수가 아니다.",
             "[KODEX 공식 자료](https://m.samsungfund.com/sheet/20120413/SHEET2232Kodex%EC%9D%B8%EB%B2%84%EC%8A%A4.pdf), [ProShares 공식 설명](https://www.proshares.com/our-etfs/leveraged-and-inverse/sh)",
             "과거 63/21일로 후보를 고르고 다음 21일 적용. 엄격 선택·최대 10%/종목·3종목·비용 가정은 앞선 연구와 같다.",
             "선택의 검증 기준선은 추가 ETF 포함 30% 동일 비중, 최종 보고 기준선은 이전 주식군의 30% 단순 보유다. 이를 구분해 해석한다.",
             "| 시장 | 수익 | 비용 2배 | 기존 주식군 보유 | 낙폭 | 거래 |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for market, result in markets.items():
        summary = result["test"]["summary"]
        lines.append(f"| {market} | {summary['net_return']:.2%} | {result['stress']['summary']['net_return']:.2%} | {result['benchmark']['summary']['net_return']:.2%} | {summary['max_drawdown']:.2%} | {summary['trades']} |")
    lines.extend(["", "## 판정·미검증", "", "과거 시험을 이미 본 뒤 도입한 가설이다. 흑자가 나와도 새로운 기간에서 동일 정책을 고정하여 검증해야 한다.",
                  "ETF의 장기 누적 수익·선물 비용·괴리율·분배금·역사 세금·실제 호가 체결은 별도 확인이 필요하다.",
                  "현재 선정 종목의 생존 편향과 수정주가 가상 수량 한계가 남는다. 실시간 뉴스 전략에는 적용하지 않았다.",
                  "모든 과거 후보·선택 내역은 results.json에 저장한다.", "", "![방어형 탐색의 가상 계좌 수익](portfolio.png)"])
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    plot_report(folder, report)
    write_json(RESULTS_ROOT / "defensive/latest.json", {"folder": str(folder)})
    print(f"방어형 검토 보고서: {folder / 'report.md'}")


if __name__ == "__main__":
    main()
