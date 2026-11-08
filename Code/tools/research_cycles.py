"""수정 방향 3개를 훈련·검증에서 반복 비교하고 새 역사 기간에서 한 번 시험한다.

실행: python main.py --test research. 실패를 숨기거나 실시간 규칙을 자동 교체하지 않는다.
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone

from app.runtime import acquire_run_lock, load_run_settings, release_run_lock
from broker.legacy_toss import TossMarketClient, read_credentials
from paths import PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT, CONFIG_ROOT
from research.backtest import validate_costs
from research.daily import benchmark_daily, develop_rules, prepare_daily_bars, simulate_daily
from research.history import collect_history, write_json
from strategy.engine import parse_timestamp


def load_cycle_settings():
    settings = json.loads((CONFIG_ROOT / "research-cycles.json").read_text(encoding="utf-8"))
    required = {"history_end", "history_days", "max_pages_per_symbol", "request_interval_seconds",
                "training_fraction", "validation_fraction", "minimum_training_trades", "minimum_validation_trades",
                "minimum_test_trades", "maximum_test_drawdown", "assumed_spread_ratio", "rounds"}
    if not isinstance(settings, dict) or set(settings) != required:
        raise ValueError("research-cycles.json의 설정 이름을 확인하세요.")
    end = parse_timestamp(settings["history_end"])
    if end >= datetime.now(timezone.utc):
        raise ValueError("역사 검증 종료 시각은 현재보다 이전이어야 합니다.")
    for name in ("history_days", "max_pages_per_symbol", "minimum_training_trades", "minimum_validation_trades", "minimum_test_trades"):
        if type(settings[name]) is not int or not 1 <= settings[name] <= 3650:
            raise ValueError("수집·거래 표본 설정은 1~3650의 정수여야 합니다.")
    for name in ("training_fraction", "validation_fraction", "maximum_test_drawdown", "assumed_spread_ratio", "request_interval_seconds"):
        if isinstance(settings[name], bool) or not isinstance(settings[name], (int, float)) or not 0 < settings[name] < 1:
            raise ValueError("연구 비율·요청 간격은 0 초과 1 미만 숫자여야 합니다.")
    if settings["training_fraction"] + settings["validation_fraction"] >= 1 or settings["request_interval_seconds"] < 0.05:
        raise ValueError("미사용 시험 기간과 최소 요청 간격 0.05초를 지켜야 합니다.")
    if settings["rounds"] != ["breakout", "trend_filter", "pullback"]:
        raise ValueError("연구 단계는 breakout, trend_filter, pullback 순서로 적으세요.")
    return settings


def collect_daily_records(runtime, settings):
    """새 창은 기존 분봉과 별도 파일이다. 완료 캐시는 인증 없이 재사용한다."""
    records = {}
    pending = []
    end = parse_timestamp(settings["history_end"])
    for market, symbol in runtime["symbols"]:
        path = DATA_ROOT / "history/daily" / (market + "-" + symbol + "-" + end.date().isoformat() + ".json")
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("origin") != "toss_actual_historical_candles" or record.get("market") != market or record.get("symbol") != symbol:
                raise ValueError("저장된 일봉 출처·시장·종목이 요청과 다릅니다.")
            if record.get("requested_end") != end.isoformat() or record.get("interval") != "1d":
                raise ValueError("저장된 일봉의 요청 기간·단위가 다릅니다.")
            if record.get("collection_complete"):
                records[market + ":" + symbol] = record
                continue
        pending.append((market, symbol, path))
    if pending:
        runtime["output_dir"].mkdir(parents=True, exist_ok=True)
        lock = acquire_run_lock(runtime["output_dir"] / "run.lock")
        try:
            client = TossMarketClient(*read_credentials(False, runtime["env_file"]))
            for market, symbol, path in pending:
                records[market + ":" + symbol] = collect_history(client, market, symbol, path, settings, now=end, interval="1d")
        finally:
            release_run_lock(lock)
    return records


def previous_test_periods():
    """새 데이터 파일 이름만으로 미사용 시험이 되지 않는다. 날짜 겹침도 확인한다."""
    periods = []
    old_log = RESULTS_ROOT / "backtest/experiments.jsonl"
    if old_log.exists():
        for line in old_log.read_text(encoding="utf-8").splitlines():
            report = json.loads(line)
            for key, result in report["results"].items():
                period = result["periods"]["test"]
                if period["start"] and period["end"]:
                    periods.append({"key": key, "start": period["start"], "end": period["end"], "fingerprint": "previous_intraday_research"})
    path = DATA_ROOT / "history/daily-test-periods.json"
    if path.exists():
        periods.extend(json.loads(path.read_text(encoding="utf-8")))
    return periods


def overlaps_previous_test(key, start, end, fingerprint, periods):
    return any(item["key"] == key and item["fingerprint"] != fingerprint
               and start <= item["end"] and end >= item["start"] for item in periods)


def write_cycle_report(folder, report):
    lines = ["# 반복 수정·역사 검증 결과", "", "실제 토스 일봉·가상 체결. 뉴스·장중 매매의 수익성 검증은 아니다.",
             "1단계 돌파 → 2단계 장기 추세 필터 → 3단계 추세 속 반등. 각 단계 8개, 총 24개 후보/종목.",
             "모든 수정·선택은 훈련 60%·검증 20%에서만 하고 고정한 후보를 시험 20%에 적용했다.",
             "새 역사 구간은 이전 분봉 연구보다 과거다. 시간순 분할은 지켰지만 향후 실시간 검증을 대체하지 않는다.", "",
             "| 종목 | 훈련 순수익 | 검증 순수익 | 시험 순수익 | 시험 거래 | 단순 보유 | 2배 비용 | 판정 |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for key, result in report["results"].items():
        selected = result["development"]["selected"]
        lines.append(f"| {key} | {selected['training']['net_return']:.4%} | {selected['validation']['net_return']:.4%} | {result['test']['summary']['net_return']:.4%} | {result['test']['summary']['trades']} | {result['benchmark']:.4%} | {result['stress']['net_return']:.4%} | {result['verdict']} |")
    lines.extend(["", "## 비용·조건", "", f"비용 설정: `{json.dumps(report['costs'], ensure_ascii=False)}`", ""])
    lines.extend([f"가정 스프레드 {report['settings']['assumed_spread_ratio']:.3%}, 다음 거래일 시가 체결, 초기 자금의 {report['costs']['allocation_fraction']:.1%} 투자.",
                  "KRW/USD 합산 없음. 단순 보유도 같은 초기 비중·비용. 현재 비용은 토스 실제 요율이 아닌 기존 보수적 가정이다.",
                  "수집 출처: [토스 공식 시세 API](https://developers.tossinvest.com/docs/market-data).", ""])
    for key, result in report["results"].items():
        lines.extend([f"## {key}", "", f"고정 후보: `{result['development']['selected']['rule']}`", "",
                      f"원자료: {result['bar_count']}일봉, {result['raw_start']}~{result['raw_end']}", ""])
        for part, period in result["periods"].items():
            lines.append(f"- {part}: {period['start']}~{period['end']} ({period['bars']}봉)")
        lines.extend(["", "| 단계 | 가장 높은 훈련 순수익 | 검증한 상위 3개 중 가장 높은 순수익 |", "| --- | ---: | ---: |"])
        for stage in result["development"]["rounds"]:
            train_best = max(trial["training"]["net_return"] for trial in stage["trials"])
            valid_best = max(trial["validation"]["net_return"] for trial in stage["trials"] if "validation" in trial)
            lines.append(f"| {stage['round']} | {train_best:.4%} | {valid_best:.4%} |")
        lines.append("")
        for name, passed in result["checks"].items():
            lines.append(f"- {name}: {'통과' if passed else '실패'}")
        lines.extend(["", f"이미 시험한 날짜와 겹침: {result['test_reused']}", ""])
    lines.extend(["## 판정·미검증", "", "- 훈련·검증·시험 모두 양수, 훈련 10건·검증 5건·시험 30건 이상, 시험 단순 보유 초과, 낙폭 5% 이하, 2배 비용 양수일 때만 연구 후보 통과.",
                  "- 적은 거래에서 나온 양수도 충분한 수익성 근거로 취급하지 않는다.",
                  "- 과거 원문 확인 뉴스, 장중 호가·체결·부분 체결·지연, 배당·기업행동, 역사 요율·세금은 미검증.",
                  "- 일봉 라벨은 실제 주문 시각이 아니다. 당일 저가로 손절을 보수 처리하며 고가로 갱신한 추적 손절은 다음 날 적용.",
                  "- 개별 종목의 독립 가상 계좌. 다종목 자금 경합·시장 위험·환율 수익은 미재현.",
                  "- 수정 전에 시험한 기간과 겹치면 탐색으로 표시한다. 새 과거 구간도 미래 수익 보장은 아니다.",
                  "- 선택 후보는 실시간 전략에 자동 적용하지 않았다.", "", "![새 역사 구간 시험 결과](cycles.png)"])
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_cycles(folder, report):
    import os
    os.environ.setdefault("MPLCONFIGDIR", str(DATA_ROOT / "cache/plots"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plot
    figure, axes = plot.subplots(len(report["results"]), 1, figsize=(10, 7), squeeze=False, constrained_layout=True)
    for axis, (key, result) in zip(axes[:, 0], report["results"].items()):
        curve = result["test"]["curve"]
        starting = report["costs"]["starting_cash"][key.split(":")[0]]
        axis.plot(range(len(curve)), [(row["equity"] / starting - 1) * 100 for row in curve], label="Rule: simulated fills, costs included")
        axis.axhline(result["benchmark"] * 100, color="#e67e22", linestyle="--", label="Buy/hold FINAL return")
        axis.axhline(0, color="gray", linewidth=0.7)
        indices = sorted({0, len(curve) // 2, len(curve) - 1})
        axis.set_xticks(indices, [curve[index]["date"] for index in indices])
        axis.set_title(key + (": reused historical test" if result["test_reused"] else ": additional historical test"))
        axis.set_ylabel("Account return (%)")
        axis.grid(alpha=0.2)
        axis.legend()
    figure.suptitle("Daily research: actual historical prices, NOT intraday/live performance")
    figure.savefig(folder / "cycles.png", dpi=150)
    plot.close(figure)


def main():
    runtime = load_run_settings()
    settings = load_cycle_settings()
    records = collect_daily_records(runtime, settings)
    costs = json.loads(runtime["paper_settings"].read_text(encoding="utf-8"))
    validate_costs(costs)
    fingerprint = hashlib.sha256((PROJECT_ROOT / "research/daily.py").read_bytes() +
                                 (PROJECT_ROOT / "research/backtest.py").read_bytes() +
                                 (PROJECT_ROOT / "research/history.py").read_bytes() +
                                 json.dumps({"settings": settings, "costs": costs}, sort_keys=True).encode()).hexdigest()
    base = RESULTS_ROOT / "research-cycles"
    base.mkdir(parents=True, exist_ok=True)
    lock = acquire_run_lock(base / "run.lock")
    try:
        folder = base / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        folder.mkdir()
        prepared = {}
        frozen = {}
        for key, record in records.items():
            bars = prepare_daily_bars(record)
            if len(bars) < 500:
                raise ValueError(f"{key}: 3년 일봉 연구에 필요한 500봉을 확보하지 못했습니다.")
            first = int(len(bars) * settings["training_fraction"])
            second = int(len(bars) * (settings["training_fraction"] + settings["validation_fraction"]))
            parts = {"training": bars[:first], "validation": bars[first:second], "test": bars[second:]}
            development = develop_rules(parts["training"], parts["validation"], record["market"], costs, settings)
            prepared[key] = (parts, development, bars)
            frozen[key] = {"rule": development["selected"]["rule"], "test_start": parts["test"][0]["date"], "test_end": parts["test"][-1]["date"]}
            for stage in development["rounds"]:
                candidates = [trial for trial in stage["trials"] if "validation" in trial]
                best = max(candidate["validation"]["net_return"] for candidate in candidates)
                print(f"{key}: {stage['round']} 8개 후보, 검증 최고 {best:.4%}", flush=True)
        # 시험 성과를 계산하기 전에 선정 규칙·시험 날짜·코드 지문을 디스크에 고정한다.
        write_json(folder / "frozen-candidates.json", {"fingerprint": fingerprint, "candidates": frozen})
        source_folder = folder / "source"
        source_folder.mkdir()
        for name in ("daily.py", "backtest.py", "history.py"):
            shutil.copy2(PROJECT_ROOT / "research" / name, source_folder / name)
        previous = previous_test_periods()
        results = {}
        used = []
        for key, (parts, development, bars) in prepared.items():
            market = key.split(":")[0]
            rule = development["selected"]["rule"]
            warmup = parts["training"] + parts["validation"]
            test = simulate_daily(parts["test"], market, rule, costs, settings["assumed_spread_ratio"], warmup)
            stress_costs = {**costs, "buy_cost_ratio": costs["buy_cost_ratio"] * 2, "sell_cost_ratio": costs["sell_cost_ratio"] * 2,
                            "slippage_ratio": costs["slippage_ratio"] * 2}
            validate_costs(stress_costs)
            stress = simulate_daily(parts["test"], market, rule, stress_costs, settings["assumed_spread_ratio"] * 2, warmup)["summary"]
            benchmark = benchmark_daily(parts["test"], market, costs, settings["assumed_spread_ratio"])
            reused = overlaps_previous_test(key, parts["test"][0]["date"], parts["test"][-1]["date"], fingerprint, previous)
            selected = development["selected"]
            checks = {"training_positive": selected["training"]["net_return"] > 0,
                      "validation_positive": selected["validation"]["net_return"] > 0,
                      "test_positive": test["summary"]["net_return"] > 0,
                      "training_sample": selected["training"]["trades"] >= settings["minimum_training_trades"],
                      "validation_sample": selected["validation"]["trades"] >= settings["minimum_validation_trades"],
                      "test_sample": test["summary"]["trades"] >= settings["minimum_test_trades"],
                      "test_beats_benchmark": test["summary"]["net_return"] > benchmark,
                      "test_drawdown": test["summary"]["max_drawdown"] <= settings["maximum_test_drawdown"],
                      "double_cost_positive": stress["net_return"] > 0, "test_not_reused": not reused}
            verdict = "historical_research_candidate_passed" if all(checks.values()) else "rejected"
            if reused:
                verdict = "exploratory_test_reused"
            results[key] = {"development": development, "test": test, "stress": stress, "benchmark": benchmark,
                            "checks": checks, "verdict": verdict, "test_reused": reused, "bar_count": len(bars),
                            "raw_start": bars[0]["date"], "raw_end": bars[-1]["date"],
                            "periods": {name: {"bars": len(rows), "start": rows[0]["date"], "end": rows[-1]["date"]} for name, rows in parts.items()}}
            used.append({"key": key, "start": parts["test"][0]["date"], "end": parts["test"][-1]["date"], "fingerprint": fingerprint})
            print(f"{key}: 시험 {test['summary']['net_return']:.4%}, {test['summary']['trades']}거래, {verdict}", flush=True)
        registry_path = DATA_ROOT / "history/daily-test-periods.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else []
        for period in used:
            if period not in registry:
                registry.append(period)
        write_json(registry_path, registry)
        report = {"created_at": datetime.now(timezone.utc).isoformat(), "fingerprint": fingerprint,
                  "settings": settings, "costs": costs, "results": results, "live_strategy_updated": False}
        write_json(folder / "results.json", report)
        write_cycle_report(folder, report)
        try:
            plot_cycles(folder, report)
        except ImportError:
            print("그래프에는 선택적 matplotlib가 필요합니다. 보고서·계산 결과는 저장했습니다.")
        write_json(base / "latest.json", {"folder": str(folder)})
        print(f"반복 연구 보고서: {folder / 'report.md'}")
    finally:
        release_run_lock(lock)


if __name__ == "__main__":
    main()
