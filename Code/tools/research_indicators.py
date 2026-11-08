"""실제 지표를 수집하고 기존 일봉 규칙에 하나씩 추가해 비교한다.

실행: python main.py --test indicators. 종목 규칙은 기존 훈련·검증에서 고정한다.
지표를 넣은 모든 비교를 남기며, 이미 본 시험 기간을 새 독립 검증으로 부르지 않는다.
"""
import csv
import hashlib
import io
import json
import shutil
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from app.runtime import acquire_run_lock, load_run_settings, release_run_lock
from broker.legacy_toss import TossMarketClient, read_credentials
from paths import PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT, CONFIG_ROOT
from research.backtest import validate_costs
from research.daily import benchmark_daily, develop_rules, prepare_daily_bars, simulate_daily
from research.history import collect_history, write_json
from research.indicators import make_entry_filter, prepare_series, validate_settings
from strategy.engine import parse_timestamp
from tools.research_cycles import collect_daily_records, load_cycle_settings

VIX_URL = "https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"


def collect_index(client, symbol, settings, path):
    """시장 지표 봉은 시작 시각이다. 원본을 보존하고 일봉 날짜 라벨만 연구에 쓴다."""
    end = parse_timestamp(settings["history_end"])
    start = end - timedelta(days=settings["history_days"])
    if path.exists():
        record = json.loads(path.read_text(encoding="utf-8"))
        if (record.get("symbol") != symbol or record.get("requested_start") != start.isoformat()
                or record.get("requested_end") != end.isoformat() or record.get("origin") != "toss_market_indicator"):
            raise ValueError("지표 캐시의 출처·종목·기간이 요청과 다릅니다.")
        if record.get("complete"):
            return record
    before = end.isoformat()
    candles = {}
    complete = False
    for page_number in range(settings["max_pages_per_symbol"]):
        page = client.get("/api/v1/market-indicators/" + symbol + "/candles",
                          {"interval": "1d", "count": 200, "before": before})
        rows = page.get("candles", [])
        previous_count = len(candles)
        for row in rows:
            moment = parse_timestamp(row["timestamp"])
            if start <= moment <= end:
                if row["timestamp"] in candles and candles[row["timestamp"]] != row:
                    raise ValueError("지표 페이지 경계의 값이 서로 다릅니다.")
                candles[row["timestamp"]] = row
        if not rows or min(parse_timestamp(row["timestamp"]) for row in rows) < start or not page.get("nextBefore"):
            complete = True
            break
        if len(candles) == previous_count or parse_timestamp(page["nextBefore"]) >= parse_timestamp(before):
            raise ValueError("시장 지표 과거 페이지가 진행하지 않습니다.")
        before = page["nextBefore"]
        time.sleep(settings["request_interval_seconds"])
    record = {"symbol": symbol, "origin": "toss_market_indicator", "requested_start": start.isoformat(),
              "requested_end": end.isoformat(), "retrieved_at": datetime.now(timezone.utc).isoformat(),
              "complete": complete, "candles": sorted(candles.values(), key=lambda row: row["timestamp"])}
    write_json(path, record)
    if not complete:
        raise ValueError("시장 지표 수집 페이지 한도입니다. 완전한 기간을 확보한 뒤 비교하세요.")
    print(f"{symbol}: 실제 일봉 {len(candles)}개", flush=True)
    return record


def collect_vix(path):
    """공식 Cboe CSV 원본을 캐시에 보관한다. 현재 배포 이력이며 과거 빈티지는 미확인이다."""
    if not path.exists():
        with urllib.request.urlopen(VIX_URL, timeout=30) as response:
            raw = response.read().decode("utf-8-sig")
        # HTML 오류 페이지를 캐시로 인정하지 않는다.
        if not {"DATE", "CLOSE"} <= set(csv.DictReader(io.StringIO(raw)).fieldnames or []):
            raise ValueError("Cboe VIX CSV의 날짜·종가 열이 없습니다.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, encoding="utf-8")
        write_json(path.with_suffix(".metadata.json"), {"source": VIX_URL,
                   "retrieved_at": datetime.now(timezone.utc).isoformat(), "historical_vintages_verified": False})
    return [{"date": datetime.strptime(row["DATE"], "%m/%d/%Y").date().isoformat(), "value": row["CLOSE"]}
            for row in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))]


def collect_indicator_series(runtime, settings):
    """토스 인증 충돌을 피하기 위해 실행 잠금을 잡고 읽기 전용으로 수집한다."""
    directory = DATA_ROOT / "history/indicators" / settings["history_end"][:10]
    directory.mkdir(parents=True, exist_ok=True)
    runtime["output_dir"].mkdir(parents=True, exist_ok=True)
    lock = acquire_run_lock(runtime["output_dir"] / "run.lock")
    try:
        client = TossMarketClient(*read_credentials(False, runtime["env_file"]))
        kospi = collect_index(client, "KOSPI", settings, directory / "KOSPI.json")
        bond = collect_index(client, "KR_BOND_3Y", settings, directory / "KR_BOND_3Y.json")
        spy_path = directory / "SPY.json"
        end = parse_timestamp(settings["history_end"])
        if spy_path.exists():
            saved = json.loads(spy_path.read_text(encoding="utf-8"))
            if (saved.get("symbol") != "SPY" or saved.get("market") != "US" or saved.get("interval") != "1d"
                    or saved.get("origin") != "toss_actual_historical_candles"
                    or saved.get("requested_start") != (end - timedelta(days=settings["history_days"])).isoformat()
                    or saved.get("requested_end") != end.isoformat()):
                raise ValueError("SPY 캐시의 출처·기간·봉 단위가 다릅니다.")
        spy = collect_history(client, "US", "SPY", spy_path, settings,
                              now=parse_timestamp(settings["history_end"]), interval="1d")
        if spy["stop_reason"] in {"page_limit", "repeated_page"}:
            raise ValueError("SPY 수집이 기간 끝까지 진행되지 않았습니다.")
    finally:
        release_run_lock(lock)
    def market_rows(record):
        return [{"date": row["timestamp"][:10], "value": row["closePrice"]} for row in record["candles"]]
    series = {"KOSPI": prepare_series(market_rows(kospi)), "KR_BOND_3Y": prepare_series(market_rows(bond)),
              "SPY": prepare_series(market_rows(spy)), "VIX": prepare_series(collect_vix(directory / "VIX.csv"))}
    if any(not item["dates"] for item in series.values()):
        raise ValueError("비교에 필요한 시장 지표가 비어 있습니다.")
    return series, directory


def write_report(folder, report):
    lines = ["# 경제·시장 지표 비교", "", "실제 과거 시세·지표, 비용 포함 가상 체결. 일봉 탐색 연구이며 장중 수익성 검증이 아니다.",
             "이미 본 시험 기간을 재사용했다. 이 결과로 독립 검증 통과를 주장하거나 실시간 규칙을 바꾸지 않는다.",
             "종목 규칙은 기존 24개 후보를 훈련·검증에서 선정. 동일 규칙에 baseline/market/vix/market_vix, 한국만 bond를 비교했다.",
             "지표 설정을 시험 결과에 맞춰 재조정하지 않았다. 모든 비교를 아래에 공개한다.", "",
             "| 종목 | 지표 | 훈련 수익 | 검증 수익 | 재사용 시험 수익 | 시험 거래 | 2배 비용 | 시험 진입 차단/검사 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for key, result in report["results"].items():
        for mode, trial in result["comparisons"].items():
            lines.append(f"| {key} | {mode} | {trial['training']['net_return']:.4%} | {trial['validation']['net_return']:.4%} | {trial['test']['summary']['net_return']:.4%} | {trial['test']['summary']['trades']} | {trial['stress']['net_return']:.4%} | {trial['test']['entry_filter_blocks']}/{trial['test']['entry_filter_checks']} |")
    lines.extend(["", "## 조건·판정", "", f"지표 설정: `{report['indicator_settings']}`", f"비용 설정: `{report['costs']}`",
                  "초기 자금의 10%씩 진입, 다음 날 시가, 정수 수량, 수수료·슬리피지·스프레드 포함. 실제 역사 요율은 미확인.",
                  "market: 한국 코스피/미국 SPY 종가가 50관측일 평균 초과. SPY는 S&P 500 ETF 대용치다.",
                  "vix: VIX 25 이하. market_vix: 두 조건 동시 만족. bond: 한국 3년 국채 수익률의 20관측일 상승 0.25%p 이하.",
                  "지표 날짜가 신호 날짜보다 2일 이상 이전이어야 하며 7일 넘게 오래되면 매수 보류. 손절은 지표와 무관하게 작동한다.",
                  "이 시간 지연은 보수적 연구 가정이다. 수정 이력·실제 배포 지연의 완전한 재현은 미검증이다.",
                  "GDP·CPI·고용 발표는 당시 발표 빈티지를 확보하지 않아 제외. 현 시점 수정값으로 과거를 재현하지 않는다.",
                  "데이터 누락·짧은 수집 범위도 매수 보류가 되어 성과에 영향을 준다. 원자료 범위를 반드시 함께 확인한다.", ""])
    for name, bounds in report["coverage"].items():
        lines.append(f"- {name}: {bounds['start']}~{bounds['end']}, {bounds['observations']}관측")
    for key, result in report["results"].items():
        lines.extend(["", f"{key}: 검증에서 고른 지표={result['validation_selected_mode']}; 시험 단순 보유={result['benchmark']:.4%}; 판정=탐색/독립 검증 미통과.",
                      f"시험 날짜={result['test_start']}~{result['test_end']}. 종목 고정 규칙: `{result['rule']}`"])
    lines.extend(["", "출처: [토스 공식 API](https://developers.tossinvest.com/docs/market-data), [Cboe VIX](https://www.cboe.com/tradable-products/vix/vix-historical-data), [경제 지표 빈티지 ALFRED](https://alfred.stlouisfed.org/).", "", "![지표별 비교](indicators.png)"])
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_report(folder, report):
    import os
    os.environ.setdefault("MPLCONFIGDIR", str(DATA_ROOT / "cache/plots"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plot
    figure, axes = plot.subplots(2, 1, figsize=(10, 8), constrained_layout=True)
    for axis, (key, result) in zip(axes, report["results"].items()):
        modes = list(result["comparisons"])
        positions = list(range(len(modes)))
        axis.bar([position - 0.2 for position in positions], [result["comparisons"][mode]["validation"]["net_return"] * 100 for mode in modes], width=0.4, label="Validation")
        axis.bar([position + 0.2 for position in positions], [result["comparisons"][mode]["test"]["summary"]["net_return"] * 100 for mode in modes], width=0.4, label="REUSED test (exploration)")
        axis.set_xticks(positions, modes)
        axis.set_title(key)
        axis.set_ylabel("Account return (%)")
        axis.axhline(0, color="gray", linewidth=0.7)
        axis.margins(y=0.22)
        axis.legend()
    figure.suptitle("Actual daily inputs, simulated fills; NOT independent validation")
    figure.savefig(folder / "indicators.png", dpi=150)
    plot.close(figure)


def main():
    runtime, settings = load_run_settings(), load_cycle_settings()
    policy = validate_settings(json.loads((CONFIG_ROOT / "indicators.json").read_text(encoding="utf-8")))
    records = collect_daily_records(runtime, settings)
    series, directory = collect_indicator_series(runtime, settings)
    costs = json.loads(runtime["paper_settings"].read_text(encoding="utf-8"))
    validate_costs(costs)
    base = RESULTS_ROOT / "indicators"
    base.mkdir(parents=True, exist_ok=True)
    lock = acquire_run_lock(base / "run.lock")
    try:
        folder = base / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        folder.mkdir()
        source = folder / "source"
        source.mkdir()
        for path in (PROJECT_ROOT / "research/daily.py", PROJECT_ROOT / "research/indicators.py",
                     PROJECT_ROOT / "research/backtest.py", PROJECT_ROOT / "research/history.py",
                     PROJECT_ROOT / "tools/research_indicators.py"):
            shutil.copy2(path, source / path.name)
        hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in directory.iterdir() if path.is_file()}
        prepared, frozen = {}, {}
        for key, record in records.items():
            bars = prepare_daily_bars(record)
            first = int(len(bars) * settings["training_fraction"])
            second = int(len(bars) * (settings["training_fraction"] + settings["validation_fraction"]))
            parts = {"training": bars[:first], "validation": bars[first:second], "test": bars[second:]}
            market = record["market"]
            rule = develop_rules(parts["training"], parts["validation"], market, costs, settings)["selected"]["rule"]
            inputs = {"market": series["KOSPI" if market == "KR" else "SPY"], "vix": series["VIX"], "bond": series["KR_BOND_3Y"]}
            comparisons = {}
            for mode in ["baseline", "market", "vix", "market_vix"] + (["bond"] if market == "KR" else []):
                entry_filter = make_entry_filter(mode, inputs, policy)
                training = simulate_daily(parts["training"], market, rule, costs, settings["assumed_spread_ratio"], entry_filter=entry_filter)
                validation = simulate_daily(parts["validation"], market, rule, costs, settings["assumed_spread_ratio"], parts["training"], entry_filter)
                comparisons[mode] = {"training": training["summary"], "validation": validation["summary"],
                                     "training_filter": {"checks": training["entry_filter_checks"], "blocks": training["entry_filter_blocks"]},
                                     "validation_filter": {"checks": validation["entry_filter_checks"], "blocks": validation["entry_filter_blocks"]}}
            selected = max(comparisons, key=lambda mode: (comparisons[mode]["validation"]["trades"] >= settings["minimum_validation_trades"], comparisons[mode]["validation"]["net_return"]))
            prepared[key] = (parts, rule, inputs, comparisons, selected)
            frozen[key] = {"rule": rule, "validation_selected_mode": selected, "test_start": parts["test"][0]["date"], "test_end": parts["test"][-1]["date"]}
        write_json(folder / "frozen.json", {"candidates": frozen, "indicator_settings": policy, "data_hashes": hashes, "settings": settings, "costs": costs})
        results = {}
        stress_costs = {**costs, **{name: costs[name] * 2 for name in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
        validate_costs(stress_costs)
        for key, (parts, rule, inputs, comparisons, selected) in prepared.items():
            market = key.split(":")[0]
            for mode, comparison in comparisons.items():
                entry_filter = make_entry_filter(mode, inputs, policy)
                warmup = parts["training"] + parts["validation"]
                comparison["test"] = simulate_daily(parts["test"], market, rule, costs, settings["assumed_spread_ratio"], warmup, entry_filter)
                comparison["stress"] = simulate_daily(parts["test"], market, rule, stress_costs, settings["assumed_spread_ratio"] * 2, warmup, entry_filter)["summary"]
                print(f"{key} {mode}: 검증 {comparison['validation']['net_return']:.4%}, 재사용 시험 {comparison['test']['summary']['net_return']:.4%}, {comparison['test']['summary']['trades']}거래", flush=True)
            results[key] = {"rule": rule, "comparisons": comparisons, "validation_selected_mode": selected,
                            "benchmark": benchmark_daily(parts["test"], market, costs, settings["assumed_spread_ratio"]),
                            "test_start": parts["test"][0]["date"], "test_end": parts["test"][-1]["date"], "verdict": "exploration_only"}
        report = {"indicator_settings": policy, "costs": costs, "results": results, "live_strategy_updated": False,
                  "coverage": {name: {"start": item['dates'][0].isoformat(), "end": item['dates'][-1].isoformat(), "observations": len(item['dates'])} for name, item in series.items()}}
        write_json(folder / "results.json", report)
        write_report(folder, report)
        try:
            plot_report(folder, report)
        except ImportError:
            print("그래프에는 matplotlib가 필요합니다. 결과 JSON·보고서는 저장했습니다.")
        write_json(base / "latest.json", {"folder": str(folder)})
        print(f"경제·시장 지표 연구: {folder / 'report.md'}")
    finally:
        release_run_lock(lock)
