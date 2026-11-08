"""진입 차단·손실 거래·단일 조건 제거를 분석한다. 실행: python main.py --test diagnostics.

조건 설정은 ../Config/diagnostics.json. 비교 종목은 peers.json. 규칙은 직전 사업군 연구에서 고정한 것을 재사용한다.
훈련·검증 평균으로만 후보를 고르고, 이미 본 시험은 탐색 확인과 거래 설명에만 사용한다.
"""
import json
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.runtime import acquire_run_lock, load_run_settings, release_run_lock
from paths import PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT, CONFIG_ROOT
from research.backtest import validate_costs
from research.daily import benchmark_daily, prepare_daily_bars, simulate_daily
from research.history import write_json
from research.indicators import make_entry_filter, validate_settings
from tools.research_cycles import collect_daily_records, load_cycle_settings
from tools.research_indicators import collect_indicator_series
from tools.research_peers import load_companies, split_reference, select_historical_companies
from broker.toss import parse_symbol


def load_condition_settings():
    settings = json.loads((CONFIG_ROOT / "diagnostics.json").read_text(encoding="utf-8"))
    if not isinstance(settings, dict) or set(settings) != {"variants", "relaxed_chase_ratio", "extended_holding_days", "minimum_positive_validation_fraction"}:
        raise ValueError("diagnostics.json의 설정 이름을 확인하세요.")
    if settings["variants"] != ["baseline", "no_volume", "no_trend", "relaxed_chase", "longer_hold", "market_vix", "trend_follow"]:
        raise ValueError("기존 6개 조건과 trend_follow 비교 목록·순서를 유지하세요.")
    for name in ("relaxed_chase_ratio", "minimum_positive_validation_fraction"):
        if isinstance(settings[name], bool) or not isinstance(settings[name], (float, int)) or not 0 < settings[name] < 1:
            raise ValueError("조건 비율은 0 초과 1 미만의 숫자여야 합니다.")
    if type(settings["extended_holding_days"]) is not int or not 1 <= settings["extended_holding_days"] <= 60:
        raise ValueError("보유 연장은 1~60일 정수여야 합니다.")
    return settings


def variant_rule(reference_rule, name, settings):
    """원본을 보존한다. 기존 조건 제거와 별도 장기 추세 가설을 구분한다."""
    rule = dict(reference_rule)
    if name == "no_volume":
        rule["volume_filter"] = False
    elif name == "no_trend":
        rule["trend_filter"] = False
    elif name == "relaxed_chase":
        rule["max_chase"] = settings["relaxed_chase_ratio"]
    elif name == "longer_hold":
        rule["holding_days"] = max(rule["holding_days"], settings["extended_holding_days"])
    elif name == "trend_follow":
        # 단일 조건 제거와 별개인 새 진입 가설이다. 드문 최고가 돌파 대신 장기 상승 추세를 따른다.
        rule.update({"family": "trend_follow", "lookback": 50, "trend_days": 200, "trend_filter": True,
                     "volume_filter": False, "holding_days": 60, "stop_loss": 0.05, "trailing_stop": 0.12, "max_chase": 0.03})
    elif name not in {"baseline", "market_vix"}:
        raise ValueError("지원하지 않는 조건 비교입니다.")
    return rule


def loss_rows(result, bars):
    """손실 거래의 전체 일봉 범위를 설명한다. 일중 체결 이전의 정확한 MFE/MAE가 아니다."""
    rows = []
    for trade in result["trades"]:
        if trade["pnl"] >= 0:
            continue
        holding = [bar for bar in bars if trade["entry_date"] <= bar["date"] <= trade["exit_date"]]
        rows.append({**trade, "holding_bars": len(holding), "return_on_entry_cost": trade["pnl"] / trade["entry_cost"],
                     "full_day_high_vs_entry": max(bar["high"] for bar in holding) / trade["entry_price"] - 1,
                     "full_day_low_vs_entry": min(bar["low"] for bar in holding) / trade["entry_price"] - 1})
    return rows


def price_discontinuities(bars):
    """큰 가격 단절은 기업행동 또는 실제 급변일 수 있다. 임의 보정 없이 확인 대상으로 남긴다."""
    warnings = []
    for previous, latest in zip(bars, bars[1:]):
        ratio = latest["open"] / previous["close"]
        if ratio <= 0.5 or ratio >= 2:
            warnings.append({"date": latest["date"], "open_vs_previous_close": ratio})
    return warnings


def aggregate_development(results, companies, variants, exclude_price_warnings=False):
    """종목별 계좌 수익의 단순 평균이다. 포트폴리오 또는 독립 거래 표본 통계가 아니다.

    GOOG는 GOOGL과 같은 회사이므로 후보 선택 평균에서는 제외하고 개별 보고서에는 남긴다.
    """
    keys = [company["symbol"] for company in companies if company["symbol"] != "US:GOOG"
            and (not exclude_price_warnings or not results[company["symbol"]]["price_warnings"])]
    if not keys:
        raise ValueError("가격 단절을 제외한 개발 비교 대상이 없습니다.")
    aggregates = {}
    for name in variants:
        training = [results[key]["comparisons"][name]["training"]["summary"] for key in keys]
        validation = [results[key]["comparisons"][name]["validation"]["summary"] for key in keys]
        stress = [results[key]["comparisons"][name]["validation_stress"] for key in keys]
        aggregates[name] = {"training_mean": sum(item["net_return"] for item in training) / len(keys),
                            "validation_mean": sum(item["net_return"] for item in validation) / len(keys),
                            "validation_positive_fraction": sum(item["net_return"] > 0 for item in validation) / len(keys),
                            "validation_mean_drawdown": sum(item["max_drawdown"] for item in validation) / len(keys),
                            "validation_stress_mean": sum(item["net_return"] for item in stress) / len(keys),
                            "validation_trades": sum(item["trades"] for item in validation), "company_count": len(keys)}
        benchmark_mean = sum(results[key]["validation_benchmark"] for key in keys) / len(keys)
        aggregates[name]["validation_benchmark_mean"] = benchmark_mean
        aggregates[name]["validation_excess_mean"] = aggregates[name]["validation_mean"] - benchmark_mean
    return aggregates


def choose_candidate(aggregates, settings):
    """시험 성과는 입력하지 않는다. 자격 미달이면 선정 없음으로 남긴다."""
    eligible = [name for name, item in aggregates.items() if item["training_mean"] > 0
                and item["validation_mean"] > 0 and item["validation_stress_mean"] > 0 and item["validation_excess_mean"] > 0
                and item["validation_positive_fraction"] >= settings["minimum_positive_validation_fraction"]]
    return max(eligible, key=lambda name: aggregates[name]["validation_mean"] - aggregates[name]["validation_mean_drawdown"]) if eligible else None


def write_report(folder, report):
    lines = ["# 진입 차단·손실·조건 비교 보고서", "", f"실제 과거 일봉·가상 체결, {len(report['companies'])}종목. 장중·뉴스 전략 검증은 아니다.",
             f"공통 검증 시작={report['validation_start']}, 탐색 시험={report['test_start']}~{report['test_end']}.",
             "기존 6개 조건과 별도 장기 추세 가설 1개를 사전 선언했다. 시험 수익으로 조건을 선택하지 않았다.",
             "훈련·검증도 앞선 연구에 쓰인 자료다. 아래 선정은 개발 후보이며 독립 검증 통과가 아니다.", "",
             "## 사전 비교 조건", "", "| 이름 | 변경 |", "| --- | --- |",
             "| baseline | 기존 돌파·거래량·장기 추세·추격 3%·보유 10/20일 |",
             "| no_volume | 거래량 조건만 제거 |", "| no_trend | 종목 장기 추세 조건만 제거 |",
             f"| relaxed_chase | 신호 종가·다음 시가 추격 제한을 {report['condition_settings']['relaxed_chase_ratio']:.0%}로 완화 |",
             f"| longer_hold | 보유 한도 최소 {report['condition_settings']['extended_holding_days']}일; 기존 20일 규칙은 동일 |",
             "| market_vix | 기존 규칙에 시장 추세·VIX 조건 추가 |",
             "| trend_follow | 50일 평균>200일 평균의 상승 추세, 거래량/최고가 돌파 제외, 60일 보유 한도, 고정 손절 5%·추적 손절 12% |", "",
             "기존 6개 비교는 손절·추적 손절을 유지한다. trend_follow는 50/200일 추세, 최대 60봉 보유, 고정 손절 5%, 추적 손절 12%인 별도 가설이다. 모든 비교의 비중·비용은 같다. 뉴스는 당시 검증 사건 자료가 없어 비교에서 제외했다.", "",
             "## 개발 구간 결과와 선택", "", "GOOG를 제외한 회사 계좌 수익의 단순 평균. 상관된 거래 수를 독립 표본으로 해석하지 않는다.",
             "| 조건 | 훈련 평균 | 검증 평균 | 검증 흑자 회사 비율 | 검증 평균 낙폭 | 검증 2배 비용 | 검증 거래 합계 |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name, item in report["aggregates"].items():
        lines.append(f"| {name} | {item['training_mean']:.4%} | {item['validation_mean']:.4%} | {item['validation_positive_fraction']:.1%} | {item['validation_mean_drawdown']:.4%} | {item['validation_stress_mean']:.4%} | {item['validation_trades']} |")
    lines.extend(["", "위 평균에는 단절 경고 종목도 포함된다. 조건 선택에는 큰 가격 단절 경고가 없는 아래 종목 평균만 사용한다.", "",
                  "| 조건 | 경고 제외 훈련 평균 | 경고 제외 검증 평균 | 흑자 비율 | 검증 2배 비용 | 단순 보유 대비 차이 | 대상 회사 수 |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for name, item in report["quality_aggregates"].items():
        lines.append(f"| {name} | {item['training_mean']:.4%} | {item['validation_mean']:.4%} | {item['validation_positive_fraction']:.1%} | {item['validation_stress_mean']:.4%} | {item['validation_excess_mean']:+.4%}p | {item['company_count']} |")
    lines.extend(["", "품질 제외는 시험 시작 전에 발견되는 가격 단절에만 적용한다. 해당 종목의 개별 결과는 삭제하지 않는다.",
                  f"개발 후보: **{report['candidate'] or '선정 없음'}**.",
                  f"자격: 훈련·검증 평균 양수, 검증 2배 비용 평균 양수, 검증 흑자 회사 비율 {report['condition_settings']['minimum_positive_validation_fraction']:.0%} 이상. 적격 중 검증 평균 수익−평균 낙폭이 높은 조건을 선택한다.",
                  "단순 보유 대비 검증 평균 수익도 양수여야 후보로 선정한다. 충분한 거래 수·새 기간 검증은 별도이며 개발 후보만으로 배포하지 않는다.", "",
                  "## 기존 규칙의 시험 진입 차단", "", "아래 최초 차단 사유는 가격 신호→거래량→추세→추격 순서다. 조건별 독립 실패는 중복 집계되어 합산하지 않는다.",
                  "| 종목 | 검사 가능 일 | 가격 신호 없음 | 거래량 | 추세 | 추격 | 신호 예약 | 다음 시가 취소 | 수량 부족 | 진입 | 종가 보유 일 |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for company in report["companies"]:
        result = report["results"][company["symbol"]]
        diagnostic = result["comparisons"]["baseline"]["test"]["diagnostics"]
        blocks = diagnostic["first_blocks"]
        lines.append(f"| {company['name']} | {diagnostic['eligible_days']} | {blocks.get('price_signal', 0)} | {blocks.get('volume', 0)} | {blocks.get('trend', 0)} | {blocks.get('chase', 0)} | {diagnostic['orders_planned']} | {diagnostic['gap_cancellations']} | {diagnostic['cash_cancellations']} | {diagnostic['entries']} | {diagnostic['position_days']} |")
    lines.extend(["", "같은 날 보유·재진입 대기 상태는 별도 집계하여 거래 조건 실패로 세지 않는다. 취소 수는 비용을 반영한 다음 날 체결가격 기준이다.",
                  "종가 보유 일은 일봉 처리 후 보유 상태다. 당일 진입·청산은 0일로 잡힐 수 있어 정확한 일중 노출 시간을 대신하지 않는다.", "",
                  "## 손실 거래", "", "기존 규칙의 손실만 표시. 고가·저가는 진입/청산일 전체 봉 범위라 청산 후 가격도 포함될 수 있다. 정확한 체결 전 MFE/MAE로 해석하지 않는다.",
                  "| 종목 | 진입→청산 | 보유 봉 | 진입금액 대비 손익 | 청산 이유 | 일봉 고가/진입 | 일봉 저가/진입 |", "| --- | --- | ---: | ---: | --- | ---: | ---: |"])
    for company in report["companies"]:
        for row in report["results"][company["symbol"]]["losses"]:
            reason = row['stop_type'] or row['reason']
            if row['gap_through_stop']:
                reason += " (갭 하락)"
            lines.append(f"| {company['name']} | {row['entry_date']}→{row['exit_date']} | {row['holding_bars']} | {row['return_on_entry_cost']:.2%} | {reason} | {row['full_day_high_vs_entry']:.2%} | {row['full_day_low_vs_entry']:.2%} |")
    lines.extend(["", "## 재사용 시험 비교", "", "모든 비교를 공개하며 가장 좋은 시험 조건을 사후 선택하지 않는다.",
                  "| 종목 | 조건 | 수익 | 거래 | 낙폭 | 단순 보유 | 2배 비용 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"])
    for company in report["companies"]:
        result = report["results"][company["symbol"]]
        for name, comparison in result["comparisons"].items():
            summary = comparison["test"]["summary"]
            lines.append(f"| {company['name']} | {name} | {summary['net_return']:.4%} | {summary['trades']} | {summary['max_drawdown']:.4%} | {result['benchmark']:.4%} | {comparison['test_stress']['net_return']:.4%} |")
    lines.extend(["", "## 종목별 검증 수익", "", "조건별 편차를 보여준다. 평균 개선이 모든 회사의 개선을 뜻하지 않는다.", "",
                  "| 종목 | baseline | no_volume | no_trend | relaxed_chase | longer_hold | market_vix | trend_follow |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for company in report["companies"]:
        comparisons = report["results"][company["symbol"]]["comparisons"]
        values = " | ".join(f"{comparisons[name]['validation']['summary']['net_return']:.4%}" for name in report["condition_settings"]["variants"])
        lines.append(f"| {company['name']} | {values} |")
    lines.extend(["", "## 가격 단절 확인", "", "전일 종가 대비 다음 시가가 절반 이하·2배 이상인 날짜. 해당 없더라도 기업행동 검증 완료는 아니다."])
    warnings = [(key, row) for key, result in report["results"].items() for row in result["price_warnings"]]
    lines.extend([f"- {key}: {row['date']}, 시가/전일 종가 {row['open_vs_previous_close']:.3f}" for key, row in warnings] or ["- 위 기준의 큰 가격 단절은 발견되지 않았다."])
    lines.extend(["", "## 해석·다음 조건", "", *report["findings"], "",
                  "초기 자금 10% 투자, 종목별 독립 계좌. 평균은 실제 다종목 포트폴리오 수익이 아니다. GOOG·GOOGL은 같은 회사다.",
                  f"비용: `{report['costs']}`", "기업행동·배당·역사 비용·분봉 체결·검증된 과거 뉴스는 미검증이다. 실시간 규칙은 변경하지 않았다.",
                  "새 장중 관찰 자료에서 규칙을 고정해 모의 평가해야 한다. 30거래는 최소 연구 표본 조건이지 수익성 보장이 아니다.",
                  "", "![조건 비교](conditions.png)"])
    for company in report.get("skipped", []):
        lines.extend(["", f"시험 제외: [{company['name']}]({company['source']}), {company['reason']}, 상장 {company['listed_on']}."])
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_findings(report):
    baseline = report["quality_aggregates"]["baseline"]
    findings = []
    for name, item in report["quality_aggregates"].items():
        if name == "baseline":
            continue
        findings.append(f"- {name}: 가격 단절 경고 제외 검증 평균 차이 {item['validation_mean'] - baseline['validation_mean']:+.4%}p, 검증 거래 합계 {item['validation_trades']} (기존 {baseline['validation_trades']}). 가설별 효과는 개별 회사 표와 함께 확인한다.")
    losses = [row for key, result in report["results"].items() if key != "US:GOOG" for row in result["losses"]]
    stopped = sum(row["reason"] == "gap_adjusted_stop" for row in losses)
    findings.append(f"- 기존 규칙의 시험 손실 거래 {len(losses)}건 중 손절 {stopped}건. 손절을 무조건 넓히면 개선된다는 근거로 해석하지 않는다.")
    fixed = sum(row["stop_type"] == "fixed_stop" for row in losses)
    trailing = sum(row["stop_type"] == "trailing_stop" for row in losses)
    gaps = sum(row["gap_through_stop"] for row in losses)
    findings.append(f"- 손실 청산의 세부 유형: 고정 손절 {fixed}건, 추적 손절 {trailing}건, 손절선 아래 시가로 체결 {gaps}건(중복). 진입 직후 역행과 상승 후 되돌림을 분리해 확인한다.")
    diagnostics = [result["comparisons"]["baseline"]["test"]["diagnostics"] for key, result in report["results"].items() if key != "US:GOOG"]
    price_blocks = sum(item["first_blocks"].get("price_signal", 0) for item in diagnostics)
    total_blocks = sum(sum(item["first_blocks"].values()) for item in diagnostics)
    findings.append(f"- 기존 규칙 최초 차단 {total_blocks}일 중 가격 신호 없음 {price_blocks}일. 검사 순서에 따른 집계다. 거래량만 제거해도 돌파 기회 자체가 늘어나지는 않는다.")
    cash_cancellations = sum(item["cash_cancellations"] for item in diagnostics)
    findings.append(f"- 정수 수량·초기 자금 10% 예산 때문에 취소 {cash_cancellations}건. 한 주 가격이 예산보다 비싸면 조건을 통과해도 체결되지 않는다.")
    worse = [company["name"] for company in report["companies"] if company["symbol"] != "US:GOOG"
             and report["results"][company["symbol"]]["comparisons"]["relaxed_chase"]["test"]["summary"]["net_return"]
             < report["results"][company["symbol"]]["comparisons"]["baseline"]["test"]["summary"]["net_return"] - 1e-10]
    findings.append("- 추격 6%의 재사용 시험 결과가 악화된 회사: " + (", ".join(worse) if worse else "없음") + ". 시험 결과로 이 회사만 사후 제외하지 않는다.")
    excluded = [key for key, result in report["results"].items() if result["price_warnings"]]
    findings.append("- 개발 후보 선택에서 가격 단절 미확인으로 제외한 종목: " + (", ".join(excluded) if excluded else "없음") + ". 기업행동 보정 전의 해당 훈련 성과는 채택 근거로 쓰지 않는다.")
    if report["candidate"]:
        findings.append(f"- 다음 일봉 개발 후보는 {report['candidate']}로 고정한다. 과거 시험 최고 수익을 고른 결과가 아니다. 새 일봉 기간에서 검증하고 장중·뉴스 전략은 별도로 검증한다. 일봉 6% 기준을 장중에 그대로 적용하지 않는다.")
    else:
        findings.append("- 적격 조건이 없어 신규 규칙을 채택하지 않는다. 뉴스·분봉 관찰 자료 확보와 다른 진입 가설을 우선한다.")
    return findings


def plot_report(folder, report):
    import os
    os.environ.setdefault("MPLCONFIGDIR", str(DATA_ROOT / "cache/plots"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plot
    names = list(report["quality_aggregates"])
    positions = list(range(len(names)))
    figure, axes = plot.subplots(2, 1, figsize=(12, 9), constrained_layout=True)
    axes[0].bar(positions, [report["quality_aggregates"][name]["validation_mean"] * 100 for name in names], label="Validation mean: GOOG and flagged data excluded")
    axes[0].set_xticks(positions, names)
    axes[0].set_ylabel("Return (%)")
    axes[0].axhline(0, color="gray")
    benchmark = report["quality_aggregates"][names[0]]["validation_benchmark_mean"] * 100
    axes[0].axhline(benchmark, color="#c46939", linestyle="--", label=f"Same-budget buy and hold: {benchmark:.2f}%")
    axes[0].legend()
    totals = {}
    for key, result in report["results"].items():
        if key == "US:GOOG":
            continue
        for name, count in result["comparisons"]["baseline"]["test"]["diagnostics"]["first_blocks"].items():
            totals[name] = totals.get(name, 0) + count
    axes[1].bar(list(totals), list(totals.values()), color="#c46939")
    axes[1].set_title("Baseline REUSED test: mutually exclusive first entry blocks")
    axes[1].set_ylabel("Eligible stock-days (correlated)")
    figure.suptitle("Condition diagnostics: actual daily inputs, exploratory simulation, GOOG excluded from aggregates")
    figure.savefig(folder / "conditions.png", dpi=150)
    plot.close(figure)


def main():
    runtime, settings = load_run_settings(), load_cycle_settings()
    condition_settings = load_condition_settings()
    companies = load_companies()
    pointer = json.loads((RESULTS_ROOT / "peers/latest.json").read_text(encoding="utf-8"))
    previous = json.loads((Path(pointer["folder"]) / "frozen.json").read_text(encoding="utf-8"))
    rules = previous["rules"]
    companies, skipped = select_historical_companies(companies, previous["start"])
    records = collect_daily_records({**runtime, "symbols": [parse_symbol(company["symbol"]) for company in companies]}, settings)
    series, _ = collect_indicator_series(runtime, settings)
    policy = validate_settings(json.loads((CONFIG_ROOT / "indicators.json").read_text(encoding="utf-8")))
    costs = json.loads(runtime["paper_settings"].read_text(encoding="utf-8"))
    validate_costs(costs)
    stress_costs = {**costs, **{name: costs[name] * 2 for name in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
    validate_costs(stress_costs)
    validation_start = max(split_reference(prepare_daily_bars(records[key]), settings)[1][0]["date"] for key in rules)
    test_start, test_end = previous["start"], previous["end"]
    base = RESULTS_ROOT / "diagnostics"
    base.mkdir(parents=True, exist_ok=True)
    lock = acquire_run_lock(base / "run.lock")
    try:
        folder = base / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        folder.mkdir()
        source = folder / "source"
        source.mkdir()
        for path in (PROJECT_ROOT / "tools/analyze_conditions.py", PROJECT_ROOT / "research/daily.py", PROJECT_ROOT / "research/indicators.py", PROJECT_ROOT / "research/backtest.py"):
            shutil.copy2(path, source / path.name)
        data_hashes = {key: hashlib.sha256(json.dumps(record["candles"], sort_keys=True).encode()).hexdigest() for key, record in records.items()}
        write_json(folder / "declared-conditions.json", {"condition_settings": condition_settings, "rules": rules, "companies": companies,
                   "validation_start": validation_start, "test_start": test_start, "test_end": test_end, "costs": costs, "indicator_settings": policy,
                   "data_hashes": data_hashes, "quality_policy": "exclude_company_if_pre_test_open_previous_close_ratio_le_0.5_or_ge_2"})
        results, prepared = {}, {}
        for company in companies:
            key, market = company["symbol"], company["symbol"].split(":")[0]
            bars = prepare_daily_bars(records[key])
            training = [bar for bar in bars if bar["date"] < validation_start]
            validation = [bar for bar in bars if validation_start <= bar["date"] < test_start]
            testing = [bar for bar in bars if test_start <= bar["date"] <= test_end]
            if len(training) < 100 or len(validation) < 100 or len(testing) < 100:
                raise ValueError(f"{key}: 조건 비교의 공통 기간 표본이 부족합니다.")
            inputs = {"market": series["KOSPI" if market == "KR" else "SPY"], "vix": series["VIX"]}
            comparisons = {}
            for name in condition_settings["variants"]:
                rule = variant_rule(rules[company["reference"]], name, condition_settings)
                entry_filter = make_entry_filter("market_vix" if name == "market_vix" else "baseline", inputs, policy)
                comparisons[name] = {"rule": rule,
                    "training": simulate_daily(training, market, rule, costs, settings["assumed_spread_ratio"], entry_filter=entry_filter),
                    "validation": simulate_daily(validation, market, rule, costs, settings["assumed_spread_ratio"], training, entry_filter),
                    "validation_stress": simulate_daily(validation, market, rule, stress_costs, settings["assumed_spread_ratio"] * 2, training, entry_filter)["summary"]}
            results[key] = {"comparisons": comparisons, "validation_benchmark": benchmark_daily(validation, market, costs, settings["assumed_spread_ratio"]),
                            "price_warnings": price_discontinuities([bar for bar in bars if bar["date"] < test_start])}
            prepared[key] = (market, training + validation, testing, inputs)
        aggregates = aggregate_development(results, companies, condition_settings["variants"])
        quality_aggregates = aggregate_development(results, companies, condition_settings["variants"], exclude_price_warnings=True)
        candidate = choose_candidate(quality_aggregates, condition_settings)
        write_json(folder / "selected-before-test.json", {"candidate": candidate, "aggregates": aggregates, "quality_aggregates": quality_aggregates})
        for key, (market, warmup, testing, inputs) in prepared.items():
            result = results[key]
            for name, comparison in result["comparisons"].items():
                entry_filter = make_entry_filter("market_vix" if name == "market_vix" else "baseline", inputs, policy)
                comparison["test"] = simulate_daily(testing, market, comparison["rule"], costs, settings["assumed_spread_ratio"], warmup, entry_filter)
                comparison["test_stress"] = simulate_daily(testing, market, comparison["rule"], stress_costs, settings["assumed_spread_ratio"] * 2, warmup, entry_filter)["summary"]
            result["benchmark"] = benchmark_daily(testing, market, costs, settings["assumed_spread_ratio"])
            result["losses"] = loss_rows(result["comparisons"]["baseline"]["test"], testing)
        report = {"companies": companies, "skipped": skipped, "results": results, "aggregates": aggregates, "quality_aggregates": quality_aggregates, "candidate": candidate,
                  "condition_settings": condition_settings, "costs": costs, "validation_start": validation_start,
                  "test_start": test_start, "test_end": test_end, "live_strategy_updated": False}
        report["findings"] = build_findings(report)
        write_json(folder / "results.json", report)
        write_report(folder, report)
        try:
            plot_report(folder, report)
        except ImportError:
            print("그래프에는 matplotlib가 필요합니다. JSON·보고서는 저장했습니다.")
        write_json(base / "latest.json", {"folder": str(folder)})
        for line in report["findings"]:
            print(line)
        print(f"조건 분석 보고서: {folder / 'report.md'}")
    finally:
        release_run_lock(lock)
