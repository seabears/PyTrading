"""유사 사업군에서 기존 규칙의 적용 결과를 비교한다. 실행: python main.py --test peers.

비교 회사·기준 종목은 ../Config/peers.json에서 수정한다. 비교 종목별 규칙 재최적화는 하지 않는다.
기준 종목 훈련·검증에서 선택하고 고정한 규칙을 공통 날짜에 적용한다. 종목별 독립 모의 계좌다.
"""
import hashlib
import json
import shutil
from datetime import date, datetime, timezone

from app.runtime import acquire_run_lock, load_run_settings, release_run_lock
from broker.toss import parse_symbol
from paths import PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT, CONFIG_ROOT
from research.backtest import validate_costs
from research.daily import benchmark_daily, develop_rules, prepare_daily_bars, simulate_daily
from research.history import write_json
from research.indicators import make_entry_filter, validate_settings
from tools.research_cycles import collect_daily_records, load_cycle_settings
from tools.research_indicators import collect_indicator_series


def load_companies():
    """실행 종목과 연구 대상을 분리하고 오타·중복·알 수 없는 기준 종목을 검사한다."""
    value = json.loads((CONFIG_ROOT / "peers.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {"companies"} or not isinstance(value["companies"], list):
        raise ValueError("peers.json에는 companies 목록이 필요합니다.")
    companies = value["companies"]
    if not 2 <= len(companies) <= 30:
        raise ValueError("비교 대상은 2~30개 회사여야 합니다.")
    seen = set()
    for company in companies:
        required = {"symbol", "name", "group", "reference", "source"}
        if not isinstance(company, dict) or not required <= set(company) or set(company) - required - {"listed_on"}:
            raise ValueError("비교 회사 설정의 항목 이름을 확인하세요.")
        if any(not isinstance(value, str) for value in company.values()):
            raise ValueError("비교 회사의 각 설정은 문자열이어야 합니다.")
        parse_symbol(company["symbol"])
        if company["symbol"] in seen or company["reference"] not in {"KR:005930", "US:AAPL"}:
            raise ValueError("비교 종목 중복 또는 지원하지 않는 기준 종목입니다.")
        if company["group"] not in {"memory", "devices", "chip_design", "platform_cloud", "mobility_space"} or not company["name"] or not company["source"].startswith("https://"):
            raise ValueError("사업군·회사 이름·출처를 확인하세요.")
        seen.add(company["symbol"])
        if "listed_on" in company:
            date.fromisoformat(company["listed_on"])
    if not {"KR:005930", "US:AAPL"} <= seen:
        raise ValueError("규칙을 고를 기준 종목 삼성전자·애플을 포함하세요.")
    return companies


def select_historical_companies(companies, test_start):
    """시험 시작 이후 상장 종목의 상장 전 동명 티커 자료를 잘못 쓰지 않는다."""
    available, skipped = [], []
    for company in companies:
        if company.get("listed_on", "0001-01-01") >= test_start:
            skipped.append({"symbol": company["symbol"], "name": company["name"], "source": company["source"],
                            "reason": "시험 시작 이후 상장: 기존 기간의 예열·시험 표본 부족", "listed_on": company["listed_on"]})
        else:
            available.append(company)
    return available, skipped


def split_reference(bars, settings):
    first = int(len(bars) * settings["training_fraction"])
    second = int(len(bars) * (settings["training_fraction"] + settings["validation_fraction"]))
    if first < 100 or second <= first or second >= len(bars):
        raise ValueError("기준 종목의 훈련·검증·시험 자료가 부족합니다.")
    return bars[:first], bars[first:second], bars[second:]


def peer_period(bars, start, end):
    """모든 비교 종목에 같은 날짜 창을 사용한다. 과거 봉은 지표 예열에만 사용한다."""
    warmup = [bar for bar in bars if bar["date"] < start]
    testing = [bar for bar in bars if start <= bar["date"] <= end]
    if len(warmup) < 100 or len(testing) < 100:
        raise ValueError("유사 종목의 공통 기간 또는 예열 자료가 부족합니다.")
    if (date.fromisoformat(testing[0]["date"]) - date.fromisoformat(start)).days > 7 or (date.fromisoformat(end) - date.fromisoformat(testing[-1]["date"])).days > 7:
        raise ValueError("유사 종목 자료가 공통 시험 시작·끝 날짜까지 이어지지 않습니다.")
    return warmup, testing


def write_report(folder, report):
    lines = ["# 유사 사업군 비교", "", "실제 토스 일봉·가상 체결, 비용 포함. 장중·뉴스 전략 수익성 검증과 구분한다.",
             f"공통 시험 날짜: {report['test_start']}~{report['test_end']}. 휴장일 차이로 봉 개수는 다를 수 있다.",
             "삼성전자·애플의 훈련·검증에서 고른 규칙을 다른 종목에도 고정 적용했다. 비교 종목별 재최적화는 없다.",
             "이미 분석한 역사 날짜에 사후 선정한 비교 회사다. 독립 검증 통과로 취급하지 않는다.", "",
             "| 사업군 | 회사 | 조건 | 계좌 수익 | 거래 | 최대 낙폭 | 단순 보유 | 2배 비용 |", "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for company in report["companies"]:
        result = report["results"][company["symbol"]]
        for mode, comparison in result["comparisons"].items():
            summary = comparison["test"]["summary"]
            lines.append(f"| {company['group']} | {company['name']} ({company['symbol']}) | {mode} | {summary['net_return']:.4%} | {summary['trades']} | {summary['max_drawdown']:.4%} | {result['benchmark']:.4%} | {comparison['stress']['net_return']:.4%} |")
    lines.extend(["", "## 조건·제한", "", f"비용: `{report['costs']}`", f"지표: `{report['indicator_settings']}`",
                  "baseline은 가격·거래량 규칙, market_vix는 시장 추세·VIX 조건을 추가한다. 각 조건을 모두 공개한다.",
                  "각 종목 초기 자금의 10% 투자, 다음 날 시가 체결, 정수 수량·비용·스프레드·갭 손절 포함.",
                  "원화·달러 손익을 합산하지 않는다. 여러 종목을 동시에 보유하는 포트폴리오 결과가 아니다.",
                  "메모리 비교는 삼성전자 반도체 사업과 SK하이닉스·마이크론의 메모리 사업을 기준으로 한다.",
                  "전자기기 비교는 PC·가전·전자기기 일부 사업의 유사성이다. LG는 가전·전장, Sony는 게임·음악·영화·센서 비중도 크며 HP·Dell은 PC 중심이다.",
                  "삼성전자·애플과 완전히 같은 매출 구성 또는 스마트폰 경쟁사 집합으로 해석하지 않는다.",
                  "Arm·엔비디아는 메모리 제조사와 구분한 칩 설계/IP 사업군이다. 삼성전자에서 고른 가격 규칙을 전이 적용한다.",
                  "알파벳·아마존은 플랫폼·클라우드 사업군이다. 애플의 가격 규칙을 전이 적용하며 같은 사업 모델로 간주하지 않는다.",
                  "구글은 알파벳 소속이다. GOOG(Class C)·GOOGL(Class A)은 같은 회사의 다른 주식 종류이며 독립 회사 표본으로 합산하지 않는다.",
                  "Arm은 2023년 9월 상장으로 원자료 기간이 짧다. 기존 규칙을 고정 적용하므로 비교 시작일을 상장일에 맞춰 재조정하지 않는다.",
                  "현재 상장된 회사를 사후 선정했으므로 생존 편향이 있다. 같은 사업군 수익은 서로 상관돼 독립 표본으로 합산하지 않는다.",
                  "토스 adjusted=false 일봉 사용. 분할·분사·배당과 역사 비용은 미검증이며 특히 Sony 기업행동의 영향은 별도 확인 필요하다.",
                  "기간 수익이 양수여도 시험 거래 30건 미만, 단순 보유 미달, 비용 스트레스 실패는 각각 남긴다.",
                  "기준 종목으로 사후 설계한 규칙의 전이 탐색이며 실제 매수·실시간 설정 변경은 수행하지 않는다.", ""])
    for company in report["companies"]:
        result = report["results"][company["symbol"]]
        lines.extend([f"## {company['name']}", "", f"사업 근거: [{company['name']} 공식 자료]({company['source']})",
                      f"기준 규칙: {company['reference']}, `{report['rules'][company['reference']]}`",
                      f"원자료 {result['raw_start']}~{result['raw_end']}, 시험 {result['test_bars']}일봉."])
        for mode, comparison in result["comparisons"].items():
            lines.append(f"- {mode} 조건 검사: `{comparison['checks']}`; 진입 차단 {comparison['test']['entry_filter_blocks']}/{comparison['test']['entry_filter_checks']}; 판정 탐색/독립 검증 미통과.")
        lines.append("")
    lines.extend(["", "## 시험 제외 목록", ""])
    for company in report.get("skipped", []):
        lines.append(f"- [{company['name']}]({company['source']}) ({company['symbol']}): {company['reason']}, 상장 {company['listed_on']}.")
    lines.extend(["![유사 사업군 비교](peers.png)", ""])
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")


def plot_report(folder, report):
    import os
    os.environ.setdefault("MPLCONFIGDIR", str(DATA_ROOT / "cache/plots"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plot
    groups = list(dict.fromkeys(company["group"] for company in report["companies"]))
    figure, axes = plot.subplots(len(groups), 1, figsize=(12, 4 * len(groups)), squeeze=False, constrained_layout=True)
    for axis, group in zip(axes[:, 0], groups):
        companies = [company for company in report["companies"] if company["group"] == group]
        positions = list(range(len(companies)))
        for offset, mode in ((-0.2, "baseline"), (0.2, "market_vix")):
            axis.bar([index + offset for index in positions], [report["results"][company["symbol"]]["comparisons"][mode]["test"]["summary"]["net_return"] * 100 for company in companies], width=0.4, label=mode)
        axis.set_xticks(positions, [company["symbol"] for company in companies])
        axis.set_title(group + ": fixed reference rule")
        axis.set_ylabel("Account return (%), 10% allocation")
        axis.axhline(0, color="gray", linewidth=0.7)
        axis.grid(axis="y", alpha=0.2)
        axis.legend()
    figure.suptitle("Sector peers: actual daily prices, simulated fills; exploratory comparison")
    figure.savefig(folder / "peers.png", dpi=150)
    plot.close(figure)


def main():
    runtime, settings = load_run_settings(), load_cycle_settings()
    companies = load_companies()
    records = collect_daily_records({**runtime, "symbols": [("KR", "005930"), ("US", "AAPL")]}, settings)
    series, directory = collect_indicator_series(runtime, settings)
    policy = validate_settings(json.loads((CONFIG_ROOT / "indicators.json").read_text(encoding="utf-8")))
    costs = json.loads(runtime["paper_settings"].read_text(encoding="utf-8"))
    validate_costs(costs)
    rules, periods = {}, []
    for reference in ("KR:005930", "US:AAPL"):
        training, validation, testing = split_reference(prepare_daily_bars(records[reference]), settings)
        rules[reference] = develop_rules(training, validation, reference.split(":")[0], costs, settings)["selected"]["rule"]
        periods.append((testing[0]["date"], testing[-1]["date"]))
    start, end = max(period[0] for period in periods), min(period[1] for period in periods)
    companies, skipped = select_historical_companies(companies, start)
    research_runtime = {**runtime, "symbols": [parse_symbol(company["symbol"]) for company in companies]}
    records = collect_daily_records(research_runtime, settings)
    base = RESULTS_ROOT / "peers"
    base.mkdir(parents=True, exist_ok=True)
    lock = acquire_run_lock(base / "run.lock")
    try:
        folder = base / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        folder.mkdir()
        source = folder / "source"
        source.mkdir()
        for path in (PROJECT_ROOT / "tools/research_peers.py", PROJECT_ROOT / "research/daily.py", PROJECT_ROOT / "research/indicators.py", PROJECT_ROOT / "research/backtest.py"):
            shutil.copy2(path, source / path.name)
        data_hashes = {key: hashlib.sha256(json.dumps(record["candles"], sort_keys=True).encode()).hexdigest() for key, record in records.items()}
        indicator_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in directory.iterdir() if path.is_file()}
        write_json(folder / "frozen.json", {"companies": companies, "rules": rules, "start": start, "end": end,
                   "costs": costs, "settings": settings, "indicator_settings": policy, "data_hashes": data_hashes, "indicator_hashes": indicator_hashes})
        stress_costs = {**costs, **{name: costs[name] * 2 for name in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
        validate_costs(stress_costs)
        results = {}
        for company in companies:
            key = company["symbol"]
            market = key.split(":")[0]
            bars = prepare_daily_bars(records[key])
            warmup, testing = peer_period(bars, start, end)
            inputs = {"market": series["KOSPI" if market == "KR" else "SPY"], "vix": series["VIX"]}
            comparisons = {}
            for mode in ("baseline", "market_vix"):
                entry_filter = make_entry_filter(mode, inputs, policy)
                test = simulate_daily(testing, market, rules[company["reference"]], costs, settings["assumed_spread_ratio"], warmup, entry_filter)
                stress = simulate_daily(testing, market, rules[company["reference"]], stress_costs, settings["assumed_spread_ratio"] * 2, warmup, entry_filter)["summary"]
                benchmark = benchmark_daily(testing, market, costs, settings["assumed_spread_ratio"])
                comparisons[mode] = {"test": test, "stress": stress, "checks": {
                    "positive": test["summary"]["net_return"] > 0,
                    "sample_30": test["summary"]["trades"] >= settings["minimum_test_trades"],
                    "beats_hold": test["summary"]["net_return"] > benchmark,
                    "drawdown": test["summary"]["max_drawdown"] <= settings["maximum_test_drawdown"],
                    "double_cost_positive": stress["net_return"] > 0, "independent_validation": False}}
                print(f"{company['name']} {mode}: {test['summary']['net_return']:.4%}, {test['summary']['trades']}거래, 보유 {benchmark:.4%}", flush=True)
            results[key] = {"comparisons": comparisons, "benchmark": benchmark, "test_bars": len(testing), "raw_start": bars[0]["date"], "raw_end": bars[-1]["date"]}
        report = {"companies": companies, "skipped": skipped, "rules": rules, "results": results, "costs": costs, "indicator_settings": policy,
                  "test_start": start, "test_end": end, "live_strategy_updated": False}
        write_json(folder / "results.json", report)
        write_report(folder, report)
        try:
            plot_report(folder, report)
        except ImportError:
            print("그래프에는 matplotlib가 필요합니다. JSON·보고서는 저장했습니다.")
        write_json(base / "latest.json", {"folder": str(folder)})
        print(f"유사 사업군 비교: {folder / 'report.md'}")
    finally:
        release_run_lock(lock)
