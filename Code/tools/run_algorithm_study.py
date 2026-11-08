"""--test algorithms: 12개 고정 가설을 실행 전 선언하고 모든 성공·실패를 기록한다.

새 수집·인증·운용 계좌 접근 없이 장기 KIS 일봉을 사용한다. 후보 선정 함수에는
2025년 이후 평가 결과를 전달하지 않는다. 모든 평가 결과를 보존하며 재실행도 덮어쓰지 않는다.
"""
import copy
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from importlib.metadata import version

from paths import CODE_ROOT, CONFIG_ROOT, DATA_ROOT, RESULTS_ROOT
from research.algorithm_study import FAMILIES, benchmark, make_features, replay
from research.algorithm_analysis import analyze
from research.daily import prepare_daily_bars
from research.backtest import validate_costs

LABELS = {"ma_trend": "MA50/200 추세", "donchian": "55일 고점 돌파",
          "trend_pullback": "상승 추세 RSI2 눌림", "bollinger_reversion": "추세 내 볼린저 회귀",
          "momentum_rotation": "126일 모멘텀 순위", "low_vol_trend": "저변동성 추세"}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def record_event(registry, event):
    """한 사건을 한 줄로 추가한다. 이전 실험 기록은 수정·삭제하지 않는다."""
    row = {"recorded_at": datetime.now(timezone.utc).isoformat(), **event}
    with registry.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def choose_candidate(results, settings):
    """개발·검증만 사용한다. 적격 후보가 없으면 현금 대기를 명시적으로 선택한다."""
    eligible, checks = [], {}
    for variant, stages in results.items():
        development = stages["development"]["base"]["summary"]
        validation = stages["validation"]["base"]["summary"]
        stressed = stages["validation"]["double_cost"]["summary"]
        policy = settings["selection"]
        passed = {"development_positive": development["net_return"] > 0,
                  "validation_positive": validation["net_return"] > 0,
                  "validation_stress_positive": stressed["net_return"] > 0,
                  "validation_sample": validation["trades"] >= policy["minimum_validation_trades"],
                  "validation_drawdown": validation["max_drawdown"] <= policy["maximum_validation_drawdown"],
                  "validation_profit_factor": (validation["profit_factor"] is not None and
                       validation["profit_factor"] >= policy["minimum_validation_profit_factor"]),
                  "validation_positive_years": sum(value > 0 for value in validation["year_returns"].values())
                       >= policy["minimum_positive_validation_years"]}
        checks[variant] = passed
        if all(passed.values()):
            eligible.append(variant)
    selected = max(eligible, key=lambda name: results[name]["validation"]["base"]["summary"]["net_return"]
                   - 2 * results[name]["validation"]["base"]["summary"]["max_drawdown"]) if eligible else None
    return {"selected": selected, "eligible": eligible, "checks": checks,
            "cash_when_none": True, "evaluation_used_for_selection": False}


def load_inputs(extra_periods=None, dataset_root=None):
    settings = json.loads((CONFIG_ROOT / "algorithm-study.json").read_text(encoding="utf-8"))
    if (not settings["families"] or len(set(settings["families"])) != len(settings["families"])
            or set(settings["families"]) - set(FAMILIES)):
        raise ValueError("가설 목록에 미지원·중복 알고리즘이 있습니다.")
    if settings["market_filters"] != [False, True]:
        raise ValueError("시장 필터 비교는 false·true 두 조건으로 고정합니다.")
    for name in ("spread_ratio", "maximum_entry_gap", "risk_per_trade"):
        value = settings[name]
        if type(value) not in (int, float) or not 0 < value < 1:
            raise ValueError("비율은 0 초과 1 미만이어야 합니다.")
    for name in ("stop_atr", "trailing_atr"):
        if type(settings[name]) not in (int, float) or not 0 < settings[name] < 20:
            raise ValueError("ATR 배수는 0 초과 20 미만이어야 합니다.")
    if type(settings["cooldown_days"]) is not int or settings["cooldown_days"] < 0:
        raise ValueError("대기 거래일은 0 이상의 정수여야 합니다.")
    previous_end = "1900-01-01"
    for name in ("development", "validation", "evaluation"):
        period = settings["periods"][name]
        datetime.fromisoformat(period["start"])
        datetime.fromisoformat(period["end"])
        if not previous_end < period["start"] < period["end"]:
            raise ValueError("개발·검증·평가 날짜는 겹치지 않고 순서대로 있어야 합니다.")
        previous_end = period["end"]
    runtime = json.loads((CONFIG_ROOT / "settings.json").read_text(encoding="utf-8"))
    costs = json.loads((CODE_ROOT / runtime["paper_settings"]).resolve().read_text(encoding="utf-8"))
    validate_costs(costs)
    symbols = runtime["symbols"]
    if len(symbols) != len(set(symbols)) or any(not symbol.startswith("US:") for symbol in symbols):
        raise ValueError("중복 없는 미국 종목 목록이 필요합니다.")
    series, features, hashes, coverage = {}, {}, {}, {}
    for key in [*symbols, "US:SPY"]:
        # 새 연구 자료는 별도 폴더로 지정하며 기존 시세는 덮어쓰지 않는다.
        daily_root = (dataset_root or (DATA_ROOT / "history")) / "daily"
        path = daily_root / (key.replace(":", "-") + ".json")
        raw = path.read_bytes()
        record = json.loads(raw)
        if (record.get("origin") != "kis_actual_historical_candles" or record.get("market") != "US"
                or record.get("symbol") != key.split(":")[1] or record.get("adjusted") is not True
                or record.get("collection_complete") is not True):
            raise ValueError(key + ": 출처·종목·수정 일봉·수집 완료를 확인하세요.")
        bars = prepare_daily_bars(record)
        values = make_features(bars, extra_periods)
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        coverage[key] = {"first": bars[0]["date"], "last": bars[-1]["date"], "bars": len(bars),
                         "first_ready": values[200]["date"] if len(values) > 200 else None,
                         "quarantined": len(record.get("rejected", []))}
        series[key], features[key] = bars, values
    proxy_bars = series.pop("US:SPY")
    proxy_features = {row["date"]: row for row in features.pop("US:SPY")}
    return settings, costs, series, features, proxy_bars, proxy_features, hashes, coverage


def plot_report(folder, results, references, selection):
    os.environ["MPLCONFIGDIR"] = str(DATA_ROOT / "cache/plots")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as dates
    figure, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)
    for number, (name, stages) in enumerate(results.items()):
        result = stages["evaluation"]["base"]
        initial = result["curve"][0]["equity"]
        # 초기 시점에 현금으로 시작하므로 첫 평가액은 초기 현금과 같다.
        points = result["curve"]
        times = [datetime.fromisoformat(p["date"]) for p in points]
        axes[0].plot(times, [(p["equity"] / initial - 1) * 100 for p in points], label=name,
                     color=plt.get_cmap("tab20")(number),
                     linewidth=2.5 if name == selection["selected"] else 1, alpha=.9)
        peak, drawdowns = initial, []
        for point in points:
            peak = max(peak, point["equity"])
            drawdowns.append((point["equity"] / peak - 1) * 100)
        axes[1].plot(times, drawdowns, color=plt.get_cmap("tab20")(number), linewidth=1, alpha=.8)
    reference = references["evaluation"]["base"]["curve"]
    initial = references["evaluation"]["initial"]
    axes[0].plot([datetime.fromisoformat(p["date"]) for p in reference],
                 [(p["equity"] / initial - 1) * 100 for p in reference], color="black", linestyle="--", label="SPY 50% budget")
    axes[0].set_title("12 fixed daily hypotheses: retrospective 2025-2026 evaluation / simulated fills")
    axes[0].set_ylabel("Net account return (%)")
    axes[1].set_ylabel("Daily close drawdown (%)")
    axes[0].legend(fontsize=7, ncol=3)
    for axis in axes:
        axis.axhline(0, color="gray", linewidth=.6)
        axis.grid(alpha=.2)
    locator = dates.AutoDateLocator(minticks=4, maxticks=8)
    axes[1].xaxis.set_major_locator(locator)
    axes[1].xaxis.set_major_formatter(dates.ConciseDateFormatter(locator))
    figure.tight_layout()
    figure.savefig(folder / "performance.png", dpi=150)
    plt.close(figure)
    figure, axis = plt.subplots(figsize=(12, 7))
    names = list(results)
    positions = list(range(len(names)))
    axis.barh([p - .18 for p in positions], [results[name]["evaluation"]["base"]["summary"]["net_return"] * 100 for name in names], height=.35, label="base")
    axis.barh([p + .18 for p in positions], [results[name]["evaluation"]["double_cost"]["summary"]["net_return"] * 100 for name in names], height=.35, label="double cost + spread")
    axis.set_yticks(positions, names)
    axis.axvline(0, color="gray", linewidth=.7)
    axis.set_xlabel("Net account return (%)")
    axis.set_title("All hypotheses retained, including losing results")
    axis.legend()
    figure.tight_layout()
    figure.savefig(folder / "comparison.png", dpi=150)
    plt.close(figure)


def write_report(folder, declaration, results, references, selection):
    costs, settings = declaration["costs"], declaration["settings"]
    lines = ["# 다양한 알고리즘 실험 기록", "", "KIS 실제 수정 일봉에 가상 체결·비용을 적용한 연구다. 실제 수익이 아니다.",
             "12개 가설과 선정 기준을 실행 전에 declaration.json에 고정했다. 손실 결과도 전부 저장한다.", "",
             "## 비교 조건", "",
             f"- 현재 지정 {len(declaration['symbols'])}종목. 초기 {costs['starting_cash']['US']:,.0f} USD, 종목별 초기 자금 {costs['allocation_fraction']:.0%}, 최대 {costs['max_positions_per_market']}개 공동 자금.",
             "- 전 종목을 과거부터 상장된 것으로 취급하지 않는다. 각 종목 201개 관측 일봉 이후부터 진입 가능. 신규 상장은 그 전까지 대기.",
             "- 당일 종가 신호→다음 거래일 시가. 진입 갭 3% 초과 취소, ATR14 단순평균 ×2.5 손절·×3 추적 손절, 초기 자금 0.25%/거래 위험 예산.",
             "- 당일 고가로 올린 추적 손절은 다음 날 적용. 갭 손절은 불리한 시가. 당일 손절 자금으로 이미 지난 시가에 매수하지 않는다.",
             "- 매수 비용 0.1%, 매도 비용 0.2%, 편도 슬리피지 0.1%, 스프레드 0.1%의 가정. double_cost는 이 네 비율 모두 두 배. 실제 증권사 요율이 아니다.",
             "- 시장 필터 on: 신호일 SPY 종가가 200일 평균 위일 때 신규 진입. 순위 회전 전략은 필터 불충족 시 다음 정기 회전에서 현금 대기.",
             "- 미청산 포지션의 가상 매도 비용도 평가액에 차감. 구간 끝 강제 매도 거래를 만들어 승률·거래 수를 늘리지 않는다.",
             "- 같은 한도 참고군은 SPY에 초기 자금 50% 단순 보유 + 무이자 현금. 실제 평균 노출은 전략마다 달라 직접적인 위험 동등 비교는 아니다.", "",
             "## 고정 알고리즘", "",
             "|이름|진입·우선순위|전략 매도|", "|---|---|---|"]
    descriptions = {
        "ma_trend": ("종가>MA50>MA200, 63일 모멘텀 양수; 모멘텀/변동성 순", "종가<MA50"),
        "donchian": ("종가가 이전 55일 고점 돌파; 모멘텀/변동성 순", "이전 20일 저점 이탈"),
        "trend_pullback": ("종가>MA200, MA50>MA200, 단순평균 RSI2<10", "RSI2>60 또는 MA10 회복"),
        "bollinger_reversion": ("종가>MA200, 20일 z-score<-2", "MA20 회복"),
        "momentum_rotation": ("종가>MA200, 126일 모멘텀/20일 변동성 상위5; 5거래일 회전", "순위·추세 약화"),
        "low_vol_trend": ("종가>MA200, 63일 모멘텀 양수; 낮은 변동성 상위5; 21거래일 회전", "순위·추세 약화")}
    for family in settings["families"]:
        enter, exit_signal = descriptions[family]
        lines.append(f"|{LABELS[family]}|{enter}|{exit_signal}|")
    lines += ["", "각 전략에 시장 필터 off/on을 적용해 12개. 회귀·눌림 최대 보유 10일, 나머지 126일. 공통 손절이 우선이다.",
              "", "## 기간별 결과", ""]
    for stage, period in settings["periods"].items():
        lines += [f"### {stage}: {period['start']} ~ {period['end']}", "",
                  "|알고리즘|순수익률|비용 두 배|MDD|완료 거래|승률|PF|평균 노출|미청산|", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for name, stages in results.items():
            base = stages[stage]["base"]["summary"]
            stress = stages[stage]["double_cost"]["summary"]
            win = "—" if base["win_rate"] is None else f"{base['win_rate']:.1%}"
            factor = "—" if base["profit_factor"] is None else f"{base['profit_factor']:.2f}"
            lines.append(f"|{name}|{base['net_return']:.2%}|{stress['net_return']:.2%}|{base['max_drawdown']:.2%}|{base['trades']}|{win}|{factor}|{base['average_exposure']:.1%}|{base['open_positions']}|")
        reference = references[stage]["base"]["summary"]
        lines += [f"|SPY 최대 한도 보유|{reference['net_return']:.2%}|{references[stage]['double_cost']['summary']['net_return']:.2%}|{reference['max_drawdown']:.2%}|—|—|—|{reference['average_exposure']:.1%}|—|",
                  "|무이자 현금|0.00%|0.00%|0.00%|0|—|—|0.0%|0|", ""]
    lines += ["## 사전 기준으로 선택한 결과", "",
              "개발 수익 양수 + 검증 수익·비용 두 배 수익 양수 + 검증 완료 30거래 이상 + MDD≤8% + PF≥1.1 + 검증 연도 2개 모두 양수.",
              "통과 후보는 검증 수익률−2×MDD로 선정한다. 적격 후보가 없으면 현금. 이후 평가 결과는 선정에 사용하지 않는다.", "",
              f"- 선택: **{selection['selected'] or '현금 대기 — 적격 후보 없음'}**.",
              f"- 적격 후보: {', '.join(selection['eligible']) or '없음'}."]
    if selection["selected"]:
        result = results[selection["selected"]]["evaluation"]["base"]["summary"]
        lines += [f"- 이후 평가 수익 {result['net_return']:.2%}, MDD {result['max_drawdown']:.2%}, 완료 {result['trades']}거래."]
    lines += ["", "|후보|검증에서 탈락한 조건|", "|---|---|"]
    lines += [f"|{name}|{', '.join(key for key, passed in checks.items() if not passed) or '모두 통과'}|" for name, checks in selection["checks"].items()]
    lines += ["", "## 자료 범위", "", "|종목|첫 날짜|마지막 날짜|일봉|지표 준비 시작|격리 오류 봉|", "|---|---|---|---:|---|---:|"]
    lines += [f"|{name}|{row['first']}|{row['last']}|{row['bars']}|{row['first_ready'] or '아직 없음'}|{row['quarantined']}|" for name, row in declaration["coverage"].items()]
    lines += ["", "## 해석·한계", "",
              "- 개발·검증·이후 평가를 시간순으로 분리했지만, 이 자료는 앞선 연구에서도 일부 사용했다. 독립적인 미사용 테스트로 주장하지 않는다.",
              "- 현재 사용자가 정한 종목을 과거에 소급했다. 생존편향·현재 종목 선택 편향이 있으며 당시 상장 전체 종목의 결과가 아니다.",
              "- 수정주가의 가상 정수 수량이다. 배당 현금·상장폐지·과거 실제 호가·시장 충격·부분 체결·실제 세금·현금 이자·환율은 미반영.",
              "- 장기 일봉 MDD는 종가 기준이며 장중 급락을 축소할 수 있다. 1분봉 운용 전략과 주기·손절 모델이 달라 수익률만 직접 비교하지 않는다.",
              "- 12개 중 이후 평가의 승자를 보고 재선정하면 과적합 위험이 생긴다. 사전 선정 결과와 전체 결과를 모두 보존했다.",
              "- 연도별·종목별 손익, 진단, 거래 내역은 각 실험 JSON에 저장했다. 운용 설정은 변경하지 않았다.",
              "- 실제 적용 전 새로운 기간의 모의 운용·더 다양한 종목군·비용과 데이터 누락 영향을 검증해야 한다.",
              "", "![성과](performance.png)", "", "![비용 비교](comparison.png)", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")


def append_analysis_report(folder, analyses, results, selection):
    """다음 실행에서도 비용 분해와 사전 선정 후보의 이후 성과를 보고서에 남긴다."""
    lines = ["", "## 완료 거래의 비용 분해", "",
             "이후 평가 기간의 완료 거래만 계산했다. 미청산 손익과 종목별 기여는 analysis.json 참고.", "",
             "|후보|가격 손익 USD|비용 USD|완료 거래 순손익 USD|평균 보유 일수(달력)|", "|---|---:|---:|---:|---:|"]
    for name, stages in analyses.items():
        row = stages["evaluation"]["base"]
        cost = row["closed_spread_cost"] + row["closed_slippage_cost"] + row["closed_fees"]
        days = row["average_holding_calendar_days"]
        holding = "—" if days is None else f"{days:.1f}"
        lines.append(f"|{name}|{row['closed_gross_price_pnl']:.2f}|{cost:.2f}|{row['closed_net_pnl']:.2f}|{holding}|")
    selected = selection["selected"]
    if selected:
        stage = results[selected]["evaluation"]
        lines += ["", f"사전 선정 {selected}: 이후 기본 비용 {stage['base']['summary']['net_return']:.2%}, 두 배 비용 {stage['double_cost']['summary']['net_return']:.2%}.",
                  "이후 결과를 보고 다른 후보로 교체하지 않았다. 실전 채택 전 별도 기간 모의 검증이 필요하다."]
    with (folder / "report.md").open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


def main():
    settings, costs, series, features, proxy_bars, proxy_features, hashes, coverage = load_inputs()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder = RESULTS_ROOT / "algorithms" / run_id
    folder.mkdir(parents=True)
    registry_folder = DATA_ROOT / "research/experiments"
    registry_folder.mkdir(parents=True, exist_ok=True)
    registry = registry_folder / "registry.jsonl"
    variants = [{"name": family + ("_market" if filtered else "_plain"), "family": family, "market_filter": filtered}
                for family in settings["families"] for filtered in settings["market_filters"]]
    stressed = copy.deepcopy(costs)
    for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
        stressed[key] *= 2
    scenarios = {"base": (costs, settings), "double_cost": (stressed, {**settings, "spread_ratio": settings["spread_ratio"] * 2})}
    declaration = {"run_id": run_id, "settings": settings, "costs": costs, "variants": variants,
                   "symbols": list(series), "coverage": coverage, "data_hashes": hashes,
                   "environment": {"python": sys.version, "exchange_calendars": version("exchange_calendars")},
                   "live_config_modified": False, "prior_data_exposure": True}
    source_folder = folder / "source"
    source_folder.mkdir()
    for relative in ("research/algorithm_study.py", "research/algorithm_analysis.py", "tools/run_algorithm_study.py", "research/backtest.py", "research/daily.py"):
        raw = (CODE_ROOT / relative).read_bytes()
        declaration.setdefault("code_hashes", {})[relative] = hashlib.sha256(raw).hexdigest()
        (source_folder / relative.replace("/", "-")).write_bytes(raw)
    write_json(folder / "declaration.json", declaration)
    record_event(registry, {"run_id": run_id, "status": "declared", "folder": str(folder), "hypotheses": variants,
                           "periods": settings["periods"], "selection": settings["selection"]})
    results = {variant["name"]: {} for variant in variants}
    references = {}
    selection = None
    try:
        analyses = {variant["name"]: {} for variant in variants}
        for stage in ("development", "validation", "evaluation"):
            period = settings["periods"][stage]
            if stage == "evaluation":
                selection = choose_candidate(results, settings)
                write_json(folder / "selection-before-evaluation.json", selection)
                record_event(registry, {"run_id": run_id, "status": "selected_before_evaluation", **selection})
            references[stage] = {"initial": costs["starting_cash"]["US"]}
            for scenario, (scenario_costs, scenario_settings) in scenarios.items():
                references[stage][scenario] = benchmark(proxy_bars, scenario_costs, scenario_settings, **period)
            for variant in variants:
                name = variant["name"]
                results[name][stage] = {}
                analyses[name][stage] = {}
                for scenario, (scenario_costs, scenario_settings) in scenarios.items():
                    event = {"run_id": run_id, "algorithm": name, "stage": stage, "scenario": scenario}
                    record_event(registry, {**event, "status": "started"})
                    result = replay(series, features, proxy_features, variant["family"], variant["market_filter"],
                                    scenario_costs, scenario_settings, **period)
                    analyses[name][stage][scenario] = analyze(result, series, scenario_costs, scenario_settings["spread_ratio"])
                    result_path = folder / f"{name}-{stage}-{scenario}.json"
                    write_json(result_path, result)
                    results[name][stage][scenario] = result
                    record_event(registry, {**event, "status": "completed", "summary": result["summary"],
                                           "result": str(result_path)})
                summary = results[name][stage]["base"]["summary"]
                print(f"{stage} {name}: 수익 {summary['net_return']:.2%}, MDD {summary['max_drawdown']:.2%}, {summary['trades']}거래", flush=True)
        write_json(folder / "references.json", references)
        write_json(folder / "analysis.json", analyses)
        write_json(folder / "summaries.json", {name: {stage: {scenario: result["summary"] for scenario, result in scenarios.items()}
            for stage, scenarios in stages.items()} for name, stages in results.items()})
        write_report(folder, declaration, results, references, selection)
        append_analysis_report(folder, analyses, results, selection)
        checks = {name + "/" + stage + "/" + scenario: analysis["checks"]
                  for name, stages in analyses.items() for stage, scenarios in stages.items()
                  for scenario, analysis in scenarios.items()}
        write_json(folder / "validation.json", checks)
        check_count = sum(len(row) for row in checks.values())
        (folder / "validation.md").write_text(
            f"# 결과 검산\n\n{len(checks)}회 재생의 비용·자금·종목 손익 {check_count}항목 통과. validation.json 참고.\n\n"
            "전체 자동 검증은 별도 `python Code/main.py --test all`로 실행한다.\n", encoding="utf-8")
        plot_report(folder, results, references, selection)
        record_event(registry, {"run_id": run_id, "status": "finished", "selected": selection["selected"], "folder": str(folder)})
    except Exception as error:
        record_event(registry, {"run_id": run_id, "status": "failed", "error_type": type(error).__name__})
        raise
    write_json(folder.parent / "latest.json", {"folder": str(folder)})
    destination = DATA_ROOT / "reports/algorithms"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("report.md", "performance.png", "comparison.png", "declaration.json", "summaries.json", "selection-before-evaluation.json", "analysis.json", "validation.json", "validation.md"):
        shutil.copy2(folder / name, destination / name)
    if (destination / "test-log.txt").exists():
        (destination / "test-log.txt").replace(destination / "previous-test-log.txt")
    write_json(destination / "latest.json", {"folder": str(folder)})
    journal = CODE_ROOT.parent / "Docs/RESEARCH_LOG.md"
    if not journal.exists():
        journal.write_text("# 알고리즘 연구 일지\n\n성공·손실·미검증을 함께 보존한다. 과거 결과로 실전 수익을 보장하지 않는다.\n", encoding="utf-8")
    with journal.open("a", encoding="utf-8") as stream:
        stream.write(f"\n## {run_id}: 12개 일봉 알고리즘, 72회 재생\n\n")
        stream.write("- 시작점: 현재 5분봉 전략의 기본 비용 수익 -10.47%, 181완료 거래. 거래 빈도·비용 문제를 확인한 뒤 장기 일봉 가설을 분리했다.\n")
        stream.write(f"- 가설: 6종류 × 시장 필터 유무. 개발·검증·이후 평가 × 기본·두 배 비용을 모두 보존.\n- 사전 기준 선택: {selection['selected'] or '현금 — 적격 후보 없음'}.\n")
        stream.write(f"- 결과 폴더: `{folder}`. 보고서: [최신 보고서](../Data/reports/algorithms/report.md). 실행 당시 보고서는 결과 폴더에 보존.\n")
        stream.write("- 운용 설정 변경 없음. 현재 종목 소급 편향·기존 자료 재사용·가상 체결 한계 있음.\n")
    print("보고서:", destination / "report.md", flush=True)
