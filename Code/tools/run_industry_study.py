"""--test industry-peers: 산업군·개별 종목에 같은 고정 규칙을 적용하고 누적 기록한다.

기준 후보는 이전 연구에서 정한 breakout_trailing35다. 이번 산업군 결과를 보고
규칙·종목을 선택하지 않는다. 기존 평가 자료와 시간적으로 겹치는 연구용 재생이다.
"""
import copy
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from paths import CODE_ROOT, CONFIG_ROOT, DATA_ROOT, RESULTS_ROOT
from research.algorithm_study import make_features, replay, resolve_strategy
from research.algorithm_analysis import analyze
from research.algorithm_refinements import feature_periods
from research.daily import prepare_daily_bars
from research.industry_study import group_benchmark, peer_statistics
from tools.run_algorithm_study import record_event, write_json


def load_inputs():
    study = json.loads((CONFIG_ROOT / "industry-study.json").read_text(encoding="utf-8"))
    dataset = Path(json.loads((DATA_ROOT / "industry-peers/datasets/latest.json").read_text(encoding="utf-8"))["folder"])
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("complete") is not True or manifest["errors"]:
        raise ValueError("완료된 동종 기업 시세 스냅샷이 필요합니다. --test industry-history를 실행하세요.")
    groups = manifest["plan"]["groups"]
    symbols = [symbol for group in groups.values() for symbol in group["symbols"]]
    if len(symbols) != len(set(symbols)) or len(symbols) < 2:
        raise ValueError("산업군 종목 중복 또는 부족")
    names = [variant["name"] for variant in study["variants"]]
    if len(names) != len(set(names)) or study["primary_variant"] not in names:
        raise ValueError("규칙 이름 중복 또는 기준 규칙 누락")
    if type(study["group_maximum_positions"]) is not int or study["group_maximum_positions"] < 1:
        raise ValueError("산업군 최대 보유는 양의 정수여야 합니다.")
    policies = []
    for variant in study["variants"]:
        policy = resolve_strategy(variant["family"], variant["strategy"])
        if set(variant["risk"]) - {"stop_atr", "trailing_atr"} or any(
            type(value) not in (int, float) or not 0 < value < 20 for value in variant["risk"].values()):
            raise ValueError("위험 조정은 유효한 ATR 배수만 허용합니다.")
        policies.append({"strategy": policy})
    extras = feature_periods(policies)
    series, features, hashes = {}, {}, {}
    for row in manifest["rows"]:
        symbol = row["symbol"]
        path = dataset / "daily" / f"US-{symbol}.json"
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("시세 스냅샷 해시 불일치: " + symbol)
        record = json.loads(raw)
        if (record.get("origin") != "kis_actual_historical_candles" or record.get("market") != "US"
                or record.get("symbol") != symbol or record.get("adjusted") is not True
                or record.get("collection_complete") is not True):
            raise ValueError("실제 KIS 수정 일봉 확인 실패: " + symbol)
        bars = prepare_daily_bars(record)
        series[symbol] = bars
        features[symbol] = make_features(bars, extras)
        hashes[str(path)] = row["sha256"]
    if set(series) != set(symbols) | {"SPY"}:
        raise ValueError("산업군 구성과 데이터 스냅샷 종목 불일치")
    proxy = {feature["date"]: feature for feature in features.pop("SPY")}
    proxy_bars = series.pop("SPY")
    end = min(row["last"] for row in manifest["rows"])
    if study["periods"]["evaluation"]["end"] == "dataset_end":
        study["periods"]["evaluation"]["end"] = end
    previous_end = "1900-01-01"
    for stage in ("development", "validation", "evaluation"):
        period = study["periods"][stage]
        if not previous_end < period["start"] < period["end"] <= end:
            raise ValueError("기간 순서·스냅샷 종료 날짜를 확인하세요.")
        previous_end = period["end"]
    runtime = json.loads((CONFIG_ROOT / "settings.json").read_text(encoding="utf-8"))
    prior_symbols = {key.split(":", 1)[1] for key in manifest.get("reference_watchlist", runtime["symbols"])}
    new_symbols = sorted(set(symbols) - prior_symbols)
    costs = json.loads((CODE_ROOT / runtime["paper_settings"]).resolve().read_text(encoding="utf-8"))
    settings = json.loads((CONFIG_ROOT / "algorithm-study.json").read_text(encoding="utf-8"))
    return study, dataset, manifest, series, features, proxy, proxy_bars, hashes, new_symbols, costs, settings


def plot_report(folder, study, groups, groups_results, singles, new_symbols, primary):
    os.environ["MPLCONFIGDIR"] = str(DATA_ROOT / "cache/plots")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    variants = [variant["name"] for variant in study["variants"]]
    group_names = list(groups)
    figure, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    for axis, scenario in zip(axes, ("base", "double_cost")):
        matrix = np.array([[groups_results[group][variant]["evaluation"][scenario]["summary"]["net_return"] * 100
                            for variant in variants] for group in group_names])
        limit = max(1, max(abs(groups_results[group][variant]["evaluation"][cost]["summary"]["net_return"] * 100)
                           for group in group_names for variant in variants for cost in ("base", "double_cost")))
        colors = axis.imshow(matrix, cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
        axis.set_xticks(range(len(variants)), variants, rotation=30, ha="right", fontsize=8)
        axis.set_yticks(range(len(group_names)), group_names)
        axis.set_title(scenario + ": shared account within each industry")
        for row in range(len(group_names)):
            for column in range(len(variants)):
                axis.text(column, row, f"{matrix[row, column]:+.1f}%", ha="center", va="center", fontsize=8)
    figure.subplots_adjust(bottom=.25, right=.88, wspace=.12)
    color_axis = figure.add_axes([.91, .25, .015, .63])
    figure.colorbar(colors, cax=color_axis, label="Net account return (%)")
    evaluation = study["periods"]["evaluation"]
    figure.suptitle(f"Industries / {evaluation['start']} to {evaluation['end']} / simulated fills")
    figure.savefig(folder / "industries.png", dpi=150)
    plt.close(figure)
    symbols = [symbol for group in groups.values() for symbol in group["symbols"]]
    figure, axis = plt.subplots(figsize=(12, 10))
    positions = list(range(len(symbols)))
    for offset, scenario, color in ((-.18, "base", "#408b72"), (.18, "double_cost", "#d18b45")):
        axis.barh([p + offset for p in positions],
                  [singles[symbol][primary]["evaluation"][scenario]["summary"]["net_return"] * 100 for symbol in symbols],
                  height=.35, color=color, label=scenario)
    axis.set_yticks(positions, [symbol + (" [new peer]" if symbol in new_symbols else "") for symbol in symbols], fontsize=8)
    axis.axvline(0, color="gray", linewidth=.6)
    axis.set_xlabel("Independent account net return (%), max 10% initial allocation")
    axis.set_title(f"{primary}: {evaluation['start']} to {evaluation['end']} / simulated fills")
    axis.legend()
    figure.tight_layout()
    figure.savefig(folder / "stocks.png", dpi=150)
    plt.close(figure)


def write_report(folder, declaration, group_results, single_results, references, stats):
    study, groups = declaration["study"], declaration["groups"]
    primary = study["primary_variant"]
    lines = ["# 동종 산업군 확장 실험", "", "실제 KIS 수정 일봉 + 가상 호가·체결·비용의 탐색이다. 실거래 수익이 아니다.",
        "기준 규칙을 이전 연구에서 선택한 돌파·추적 손절 3.5 ATR로 고정했다. 이번 결과를 보고 종목·산업군별 승자로 교체하지 않았다.", "",
        "## 수집·실험 범위", "",
        f"- {len(groups)}산업군 {len(single_results)}종목 + SPY. 기존 목록 밖 동종 기업 {len(declaration['new_symbols'])}개 추가 수집.",
        f"- 신규 기업: {', '.join(declaration['new_symbols'])}.",
        f"- 원본 데이터 스냅샷: `{declaration['dataset']}`. 기존 Data/history와 연구 기록을 지우지 않았다.",
        "- 산업군별로 초기 1만 USD 공동 계좌, 종목당 초기 자금 최대 10%, 최대 3개 보유. 산업군 계좌끼리는 별개이며 수익률을 합산하지 않는다.",
        "- 종목별 시험은 초기 1만 USD 독립 계좌·최대 1개·초기 자금 최대 10%로 비교. 수익률 분모는 전체 현금 포함 1만 USD.",
        f"- {len(study['variants'])}규칙 × ({len(groups)}산업군+{len(single_results)}개별 종목) × {len(study['periods'])}기간 × 2비용. 같은 시세의 가설 비교이며 독립 시세 표본 수가 아니다.",
        "- 기본 비용: 매수 0.1%, 매도 0.2%, 편도 슬리피지 0.1%, 스프레드 0.1% 가정. 두 배 비용에서는 네 비율 모두 두 배.",
        "- 완성 일봉 신호→다음 날 시가, SPY 200일선 위에서 신규 진입, 갭 3% 취소, ATR14 단순평균·위험 예산 0.25%·최대 보유 126거래일.",
        "- 매도 보호선은 전날까지의 고점으로 적용. 미청산 가상 매도 비용을 평가에 반영. 실제 주문은 호출하지 않는다.", "",
        "## 사업 기준 산업군", "", "공식 GICS 분류가 아니라 기업 공시·IR의 사업 성격을 참고한 연구용 그룹이다.", "",
        "|그룹|기업|구성 차이·유의점|", "|---|---|---|"]
    lines += [f"|{group['name']}|{', '.join(group['symbols'])}|{group['note']}|" for group in groups.values()]
    lines += ["", "## 고정 규칙", "", "|이름|설정|", "|---|---|"]
    lines += [f"|{variant['name']}|{variant['family']}, 전략 조정 {variant['strategy']}, 위험 조정 {variant['risk']}|" for variant in study["variants"]]
    lines += ["", "빈 조정은 이전 기본값: 고점 55일·저점 20일, MA50/200, 손절 2.5 ATR·추적 3 ATR. momentum21은 126일 모멘텀/변동성 상위·21거래일 회전."]
    for stage, period in study["periods"].items():
        lines += ["", f"## 기준 규칙 산업군 성과: {stage} {period['start']} ~ {period['end']}", "",
                  "|산업군|순수익률|비용 두 배|MDD|완료 거래|미청산|평균 노출|동종 균등보유 참고|", "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for group_id, group in groups.items():
            row = group_results[group_id][primary][stage]["base"]["summary"]
            stress = group_results[group_id][primary][stage]["double_cost"]["summary"]
            reference = references[group_id][stage]["base"]["summary"]
            lines.append(f"|{group['name']}|{row['net_return']:.2%}|{stress['net_return']:.2%}|{row['max_drawdown']:.2%}|{row['trades']}|{row['open_positions']}|{row['average_exposure']:.1%}|{reference['net_return']:.2%}|")
    lines += ["", "## 이후 평가: 6개 규칙 전체", "", "|산업군|규칙|수익률|비용 두 배|MDD|거래|", "|---|---|---:|---:|---:|---:|"]
    for group_id, group in groups.items():
        for variant in study["variants"]:
            row = group_results[group_id][variant["name"]]["evaluation"]["base"]["summary"]
            stress = group_results[group_id][variant["name"]]["evaluation"]["double_cost"]["summary"]
            lines.append(f"|{group['name']}|{variant['name']}|{row['net_return']:.2%}|{stress['net_return']:.2%}|{row['max_drawdown']:.2%}|{row['trades']}|")
    lines += ["", "## 기준 규칙을 개별 기업에 그대로 적용", "",
              "이후 평가 기간. 새로 수집한 종목과 기존 종목을 구분한다. 표본 미달을 제외해 숨기지 않는다.", "",
              "|산업군|종목|신규 수집|수익률|비용 두 배|완료 거래|표본 10거래|", "|---|---|---|---:|---:|---:|---|"]
    for group_id, group in groups.items():
        for symbol in group["symbols"]:
            row = single_results[symbol][primary]["evaluation"]["base"]["summary"]
            stress = single_results[symbol][primary]["evaluation"]["double_cost"]["summary"]
            lines.append(f"|{group['name']}|{symbol}|{'예' if symbol in declaration['new_symbols'] else '기존'}|{row['net_return']:.2%}|{stress['net_return']:.2%}|{row['trades']}|{'충족' if row['trades'] >= study['minimum_completed_trades_per_stock'] else '부족'}|")
    lines += ["", "## 신규 기업으로의 적용 범위", "", "|구분|종목|기본 비용 양수|두 배 비용 양수|10거래 이상|10거래 이상·두 비용 모두 양수|", "|---|---:|---:|---:|---:|---:|"]
    for scope, row in stats[primary]["evaluation"].items():
        lines.append(f"|{scope}|{row['stocks']}|{row['positive_base']}|{row['positive_double_cost']}|{row['enough_sample_stocks']}|{row['positive_both_with_enough_sample']}|")
    lines += ["", "## 자료 범위·오류 격리", "", "|종목|일봉|시작|종료|오류 제외|", "|---|---:|---|---|---:|"]
    lines += [f"|{row['symbol']}|{row['count']}|{row['first']}|{row['last']}|{row['rejected']}|" for row in declaration["data_rows"]]
    lines += ["", "## 해석·한계", "",
        "- 수익이 좋은 산업군만 고르거나 산업군별 규칙을 사후 변경하지 않았다. 기존 종목·평가 기간을 이미 본 상태의 확장 탐색이다.",
        "- 신규 기업은 이번 연구에서 새로 수집한 기업이다. 동일 시장·기간의 상관된 관측으로 완전 독립 검증은 아니다. 현재 기업을 소급한 생존·종목 선택 편향도 있다.",
        "- 10거래 기준은 최소한의 표본 표시일 뿐 통계적 수익성 보장이 아니다. 산업군 간 수익률 평균·양수 비율도 성공 확률이 아니다.",
        "- 동종 균등보유는 산업군 초기 투자 상한 30%를 구성 기업에 균등 배분한다. 실제 노출·집중도는 전략과 다르다.",
        "- 수정주가 가상 정수 수량이며 배당 현금·세금·현금 이자·환율·실제 호가·부분 체결 미반영. 특히 리츠·통신의 전체 투자 수익을 과소 표시할 수 있다.",
        "- SHEL 자료는 2022년부터다. 이전 티커를 연결하거나 관측 시작을 상장일로 간주하지 않았다. 일봉 오류는 원본에 남기고 격리했다.",
        "- 일부 날짜 누락 보유는 마지막 평가를 유지하고 진단에 기록한다. 일봉 종가 MDD는 장중 손실보다 작을 수 있다.",
        "- 실전 채택 판정은 하지 않는다. 새 기간 모의 운용·배당 포함 비교·종목군 확대가 필요하다.",
        "", "## 신규 기업 확인 출처", ""]
    lines += [f"- [{symbol} 공식 IR·공시]({url})" for symbol, url in declaration["sources"].items()]
    lines += ["", "![산업군 성과](industries.png)", "", "![개별 기업](stocks.png)", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    study, dataset, manifest, series, features, proxy, proxy_bars, hashes, new_symbols, costs, settings = load_inputs()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder = RESULTS_ROOT / "industry-peers" / run_id
    (folder / "runs").mkdir(parents=True)
    groups = manifest["plan"]["groups"]
    registry = DATA_ROOT / "research/experiments/registry.jsonl"
    registry.parent.mkdir(parents=True, exist_ok=True)
    declaration = {"run_id": run_id, "dataset": str(dataset), "study": study, "groups": groups,
                   "new_symbols": new_symbols, "data_hashes": hashes, "data_rows": manifest["rows"],
                   "sources": manifest["plan"]["new_symbol_sources"], "costs": costs, "settings": settings,
                   "prior_data_exposure": True, "live_strategy_changed": False, "python": sys.version}
    source = folder / "source"
    source.mkdir()
    for relative in ("research/algorithm_study.py", "research/algorithm_analysis.py", "research/industry_study.py",
                     "tools/run_industry_study.py", "research/backtest.py", "research/daily.py"):
        raw = (CODE_ROOT / relative).read_bytes()
        declaration.setdefault("code_hashes", {})[relative] = hashlib.sha256(raw).hexdigest()
        (source / relative.replace("/", "-")).write_bytes(raw)
    write_json(folder / "declaration.json", declaration)
    record_event(registry, {"run_id": run_id, "study": "industry_peers", "status": "declared", "folder": str(folder),
                           "primary_fixed_before_trials": study["primary_variant"], "variants": study["variants"], "groups": groups})
    group_results = {key: {v["name"]: {} for v in study["variants"]} for key in groups}
    singles = {symbol: {v["name"]: {} for v in study["variants"]} for symbol in series}
    analyses, references, all_checks = {}, {key: {} for key in groups}, {}
    try:
        for stage in ("development", "validation", "evaluation"):
            period = study["periods"][stage]
            for scope, scopes in (("group", {key: group["symbols"] for key, group in groups.items()}),
                                  ("stock", {symbol: [symbol] for symbol in series})):
                for scope_id, symbols in scopes.items():
                    subset = {symbol: series[symbol] for symbol in symbols}
                    subset_features = {symbol: features[symbol] for symbol in symbols}
                    account_costs = {**costs, "max_positions_per_market": study["group_maximum_positions"] if scope == "group" else 1}
                    if scope == "group":
                        references[scope_id][stage] = {}
                    for variant in study["variants"]:
                        name = variant["name"]
                        target = group_results[scope_id][name] if scope == "group" else singles[scope_id][name]
                        target[stage] = {}
                        for scenario in ("base", "double_cost"):
                            scenario_costs = copy.deepcopy(account_costs)
                            scenario_settings = {**settings, **variant["risk"]}
                            if scenario == "double_cost":
                                for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
                                    scenario_costs[key] *= 2
                                scenario_settings["spread_ratio"] *= 2
                            event = {"run_id": run_id, "scope": scope, "scope_id": scope_id, "algorithm": name, "stage": stage, "scenario": scenario}
                            record_event(registry, {**event, "status": "started"})
                            result = replay(subset, subset_features, proxy, variant["family"], True,
                                            scenario_costs, scenario_settings, **period, strategy_config=variant["strategy"])
                            analysis = analyze(result, subset, scenario_costs, scenario_settings["spread_ratio"])
                            key = f"{scope}-{scope_id}-{name}-{stage}-{scenario}"
                            write_json(folder / "runs" / (key + ".json"), result)
                            target[stage][scenario] = result
                            analyses[key] = analysis
                            all_checks[key] = analysis["checks"]
                            record_event(registry, {**event, "status": "completed", "summary": result["summary"], "result": str(folder / "runs" / (key + ".json"))})
                            if scope == "group" and name == study["variants"][0]["name"]:
                                references[scope_id][stage][scenario] = group_benchmark(subset, proxy, scenario_costs, scenario_settings, **period)
                    if scope == "group":
                        row = group_results[scope_id][study["primary_variant"]][stage]["base"]["summary"]
                        print(f"{stage} {scope_id}: 기준 수익 {row['net_return']:.2%}, MDD {row['max_drawdown']:.2%}, {row['trades']}거래", flush=True)
                if scope == "stock":
                    print(f"{stage}: {len(scopes)}종목 개별 적용 완료", flush=True)
        statistics = {variant["name"]: {stage: peer_statistics([
                {"symbol": symbol, **{scenario: singles[symbol][variant["name"]][stage][scenario]["summary"] for scenario in ("base", "double_cost")}}
                for symbol in series], set(new_symbols), study["minimum_completed_trades_per_stock"])
                for stage in study["periods"]} for variant in study["variants"]}
        write_json(folder / "peer-statistics.json", statistics)
        write_json(folder / "analysis.json", analyses)
        write_json(folder / "validation.json", all_checks)
        for name, results in (("group-summaries", group_results), ("stock-summaries", singles)):
            write_json(folder / (name + ".json"), {scope: {variant: {stage: {scenario: result["summary"] for scenario, result in scenarios.items()}
                for stage, scenarios in stages.items()} for variant, stages in variants.items()} for scope, variants in results.items()})
        write_json(folder / "benchmarks.json", references)
        write_report(folder, declaration, group_results, singles, references, statistics)
        plot_report(folder, study, groups, group_results, singles, new_symbols, study["primary_variant"])
        record_event(registry, {"run_id": run_id, "study": "industry_peers", "status": "finished", "folder": str(folder),
                               "replays": len(all_checks), "primary": study["primary_variant"]})
    except Exception as error:
        record_event(registry, {"run_id": run_id, "study": "industry_peers", "status": "failed", "error_type": type(error).__name__})
        raise
    write_json(folder.parent / "latest.json", {"folder": str(folder)})
    destination = DATA_ROOT / "reports/industry-peers"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("report.md", "industries.png", "stocks.png", "declaration.json", "peer-statistics.json", "group-summaries.json", "stock-summaries.json", "validation.json"):
        shutil.copy2(folder / name, destination / name)
    write_json(destination / "latest.json", {"folder": str(folder)})
    for previous_name in ("test-log.txt", "validation.md", "continuous.png", "data-coverage.png"):
        previous_path = destination / previous_name
        if previous_path.exists():
            previous_path.replace(destination / ("previous-" + previous_name))
    with (CODE_ROOT.parent / "Docs/RESEARCH_LOG.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n## {run_id}: 8산업군·28종목·신규 동종 기업 {len(new_symbols)}개 확장\n\n")
        stream.write(f"- 새 데이터 스냅샷: `{dataset}`. 기존 시세·실험 유지.\n")
        stream.write(f"- 6고정 규칙·산업군 공동 계좌와 개별 종목 비교 총 {len(all_checks)}회. 기준 {study['primary_variant']}는 이전 연구에서 고정.\n")
        stream.write(f"- 결과: `{folder}`. [최신 산업군 보고서](../Data/reports/industry-peers/report.md).\n")
        stream.write("- 현재 사업 기준의 그룹·생존 편향·과거 기간 재사용·배당 미반영 한계. 실제 주문과 운용 전략 변경 없음.\n")
    print("보고서:", destination / "report.md", flush=True)
