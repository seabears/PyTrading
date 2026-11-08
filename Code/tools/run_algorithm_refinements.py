"""--test refinements: 한 항목씩 조정한 36개 가설을 기록하며 216회 재생한다.

기존 기간을 재사용하는 후속 탐색이다. 개발·검증 기반 선정을 먼저 저장하고 이후
평가를 계산한다. 기존 12개 실험과 운용 설정을 덮어쓰거나 자동으로 교체하지 않는다.
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
from research.algorithm_study import benchmark, replay
from research.algorithm_analysis import analyze
from research.algorithm_refinements import build_variants, feature_periods, select_variant
from tools.run_algorithm_study import load_inputs, record_event, write_json


def plot_report(folder, variants, results, selection, references, initial):
    os.environ["MPLCONFIGDIR"] = str(DATA_ROOT / "cache/plots")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as dates
    names = [variant["name"] for variant in variants if variant["parent"] is None]
    if selection["selected"] and selection["selected"] not in names:
        names.append(selection["selected"])
    figure, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    for name in names:
        curve = results[name]["evaluation"]["base"]["curve"]
        times = [datetime.fromisoformat(point["date"]) for point in curve]
        axes[0].plot(times, [(point["equity"] / initial - 1) * 100 for point in curve], label=name,
                     linewidth=2.5 if name == selection["selected"] else 1)
        peak, drawdowns = initial, []
        for point in curve:
            peak = max(peak, point["equity"])
            drawdowns.append((point["equity"] / peak - 1) * 100)
        axes[1].plot(times, drawdowns, label=name)
    curve = references["evaluation"]["base"]["curve"]
    axes[0].plot([datetime.fromisoformat(point["date"]) for point in curve],
                 [(point["equity"] / initial - 1) * 100 for point in curve], "k--", label="SPY 50% initial budget")
    axes[0].set_title("Prior selected variant and fixed baselines / retrospective evaluation")
    axes[0].set_ylabel("Net account return (%)")
    axes[1].set_ylabel("Daily close drawdown (%)")
    for axis in axes:
        axis.axhline(0, color="gray", linewidth=.6)
        axis.grid(alpha=.2)
    axes[0].legend(fontsize=8, ncol=2)
    locator = dates.AutoDateLocator(minticks=4, maxticks=8)
    axes[1].xaxis.set_major_locator(locator)
    axes[1].xaxis.set_major_formatter(dates.ConciseDateFormatter(locator))
    figure.tight_layout()
    figure.savefig(folder / "performance.png", dpi=150)
    plt.close(figure)
    figure, axes = plt.subplots(1, 2, figsize=(14, 6), sharex=True, sharey=True)
    families = list(dict.fromkeys(variant["family"] for variant in variants))
    for axis, scenario in zip(axes, ("base", "double_cost")):
        for index, family in enumerate(families):
            selected = [variant for variant in variants if variant["family"] == family]
            rows = [results[variant["name"]]["evaluation"][scenario]["summary"] for variant in selected]
            color = plt.get_cmap("tab10")(index)
            axis.scatter([row["max_drawdown"] * 100 for row in rows],
                         [row["net_return"] * 100 for row in rows], color=color, alpha=.7, label=family)
            baseline = results[family + "__base"]["evaluation"][scenario]["summary"]
            axis.scatter(baseline["max_drawdown"] * 100, baseline["net_return"] * 100,
                         marker="s", facecolors="none", edgecolors=[color], s=120)
        if selection["selected"]:
            row = results[selection["selected"]]["evaluation"][scenario]["summary"]
            axis.scatter(row["max_drawdown"] * 100, row["net_return"] * 100,
                         marker="*", color="black", s=180, label="selected before evaluation")
        axis.axhline(0, color="gray", linewidth=.6)
        axis.set_title(scenario + ": all 36 variants")
        axis.set_xlabel("Daily maximum drawdown (%)")
        axis.grid(alpha=.2)
    axes[0].set_ylabel("Net account return (%)")
    axes[1].legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(folder / "robustness.png", dpi=150)
    plt.close(figure)
    figure, axes = plt.subplots(2, 2, figsize=(15, 12))
    for axis, family in zip(axes.flat, families):
        selected = [variant for variant in variants if variant["family"] == family and variant["parent"]]
        baseline = results[family + "__base"]["evaluation"]["base"]["summary"]["net_return"]
        changes = [(results[variant["name"]]["evaluation"]["base"]["summary"]["net_return"] - baseline) * 100 for variant in selected]
        axis.barh([variant["change"] for variant in selected], changes,
                  color=["#408b72" if change > 0 else "#c35d60" for change in changes])
        axis.axvline(0, color="gray", linewidth=.6)
        axis.set_title(family + ": one change at a time")
        axis.set_xlabel("Evaluation return difference vs baseline (percentage points)")
        axis.tick_params(axis="y", labelsize=8)
    figure.tight_layout()
    figure.savefig(folder / "sensitivity.png", dpi=150)
    plt.close(figure)


def write_report(folder, declaration, results, analyses, selection, references, controls):
    variants = declaration["variants"]
    lines = ["# 알고리즘 소폭 조정 실험", "", "실제 KIS 수정 일봉 + 가상 체결·비용. 실거래 성과가 아니다.",
        "기존 평가 자료를 다시 사용한 후속 탐색이다. 이전 결과에서 돌파·추세 계열이 상대적으로 양호해 이번 연구 범위를 정했다.",
        "범위 결정 자체가 과거 결과의 영향을 받았으므로 미사용 검증으로 해석하지 않는다.", "", "## 사전 고정 조건", "",
        f"- {len(variants)}개 가설 × 개발·검증·이후 평가 × 기본·비용 두 배 = {len(variants) * 6}회 재생.",
        "- 기준에서 한 항목만 바꾸며 파라미터 조합을 전수 탐색하지 않았다. 각 가설의 부모·변경 전후 값은 declaration.json에 기록.",
        "- 돌파 40/55/70일·저점 이탈 15/20/25일, MA40/50/60·MA150/200/250, ATR 손절 2/2.5/3·추적 2.5/3/3.5.",
        "- 보유 84/126/168거래일, 회전 전략의 주기 5/10/21/42거래일 및 시장 필터 해제를 각각 비교.",
        "- 초기 1만 USD 공동 계좌, 종목별 초기 자금 10%, 최대 5종목, 거래 위험 0.25%. 자금·위험 예산을 늘려 수익률을 끌어올리지 않았다.",
        "- 공통: 종가 신호→다음 시가, 진입 갭 3% 취소, 이전 고점 기준 ATR 손절, 당일 고가의 보호선은 다음 날부터 적용.",
        "- 기본 매수 비용 0.1%·매도 0.2%·편도 슬리피지 0.1%·스프레드 0.1%; 두 배 조건은 이 네 비율을 모두 두 배. 실제 요율이 아니다.",
        "- 미청산 가상 매도 비용 포함 평가. 기간 끝 강제 거래는 추가하지 않는다. 구간별 자금은 새로 시작하며 수익률을 단순 합산하지 않는다.", "",
        "## 후보 선정", "",
        "기존 기준에 개발 구간 비용 스트레스 양수, 검증 스트레스 PF>1·MDD≤8%, 계열의 검증 스트레스 양수 비율≥75%를 추가했다.",
        "이전 연구의 사전 선정 후보가 이후 비용 증가를 견디지 못했기 때문에 비용·주변 설정 안정성을 강화했다. 기준은 이번 실행 전에 고정했다.",
        "개발·검증을 통과한 후보 중 검증 비용 두 배 수익률−2×MDD가 가장 큰 후보를 선택한다. 이후 평가 결과는 재선정에 쓰지 않는다.",
        f"- 사전 선정: **{selection['selected'] or '현금 — 적격 후보 없음'}**.",
        f"- 통과 후보: {len(selection['eligible'])}개.", ""]
    lines += [f"- {family}: 검증 비용 두 배 양수 {fraction:.1%}" for family, fraction in sorted(selection["family_validation_stress_positive_fraction"].items())]
    if selection["selected"]:
        name = selection["selected"]
        row = results[name]["evaluation"]["base"]["summary"]
        stress = results[name]["evaluation"]["double_cost"]["summary"]
        lines += ["", f"선정 후보의 이후 누적 수익 **{row['net_return']:.2%}**, 최대 낙폭 **{row['max_drawdown']:.2%}**, 비용 두 배 **{stress['net_return']:.2%}**, 완료 {row['trades']}거래."]
    for stage, period in declaration["base_settings"]["periods"].items():
        lines += ["", f"## {stage}: {period['start']} ~ {period['end']}", "",
                  "|후보|한 항목 변경|순수익률|비용 두 배|MDD|완료 거래|평균 노출|", "|---|---|---:|---:|---:|---:|---:|"]
        for variant in variants:
            name = variant["name"]
            row = results[name][stage]["base"]["summary"]
            stress = results[name][stage]["double_cost"]["summary"]
            lines.append(f"|{name}|{variant['change']}|{row['net_return']:.2%}|{stress['net_return']:.2%}|{row['max_drawdown']:.2%}|{row['trades']}|{row['average_exposure']:.1%}|")
        row = references[stage]["base"]["summary"]
        lines += [f"|SPY 초기 50% 보유|참고군, 위험·평균 노출 다름|{row['net_return']:.2%}|{references[stage]['double_cost']['summary']['net_return']:.2%}|{row['max_drawdown']:.2%}|—|{row['average_exposure']:.1%}|"]
    lines += ["", "## 변경 효과: 이후 평가의 기준 대비 차이", "",
              "단위는 %포인트. 같은 평가 자료에서 관측한 설명적 차이이며 미래 개선 효과가 아니다.", "",
              "|변경|개발 차이|검증 차이|이후 차이|", "|---|---:|---:|---:|"]
    for variant in variants:
        if not variant["parent"]:
            continue
        changes = [(results[variant["name"]][stage]["base"]["summary"]["net_return"] - results[variant["parent"]][stage]["base"]["summary"]["net_return"]) * 100
                   for stage in ("development", "validation", "evaluation")]
        lines.append(f"|{variant['name']}|{changes[0]:+.2f}|{changes[1]:+.2f}|{changes[2]:+.2f}|")
    control_status = (f"이전 실험의 같은 기준값 결과와 전체 거래·평가 곡선 일치: {sum(controls.values())}/{len(controls)}회."
                      if controls else "동일 시세·설정의 이전 기준값 자료가 없어 결과 재현 비교는 미검증.")
    lines += ["", "## 검산·회귀 검증", "", "- " + control_status,
              f"- 전 {len(variants) * 6}회 재생에서 거래 비용·종목 기여·현금·보유 한도 검산 통과. analysis.json 참고.",
              "- 원본 시세·이전 실험 기록·운용 설정은 유지했다. 실행 코드·자료 해시는 declaration.json과 source에 보존.",
              "", "## 해석·한계", "",
              "- 이번 결과를 보고 선택한 최고 수익 후보로 갈아타지 않는다. 사전 선정과 사후 순위는 구분한다.",
              "- 현재 종목 소급 선택·생존편향, 기존 자료 재사용, 수정주가 가상 정수 수량의 한계가 있다. 신규 상장은 지표 준비 전에는 대기한다.",
              "- 배당·현금 이자·환율·실제 세금·호가·부분 체결 미반영. 일봉 종가 MDD는 장중 급락 위험을 축소할 수 있다.",
              "- 비용 두 배와 주변 설정에서 안정적이어도 실전 수익이 증명된 것은 아니다. 다음 독립 검증은 새 기간 모의 운용이다.",
              "", "![선정 후보와 기준 전략](performance.png)", "", "![전체 조정안](robustness.png)", "", "![한 항목 변경 효과](sensitivity.png)", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    plan = json.loads((CONFIG_ROOT / "algorithm-refinements.json").read_text(encoding="utf-8"))
    base_settings = json.loads((CONFIG_ROOT / "algorithm-study.json").read_text(encoding="utf-8"))
    variants = build_variants(plan, base_settings)
    base_settings, costs, series, features, proxy_bars, proxy_features, hashes, coverage = load_inputs(feature_periods(variants))
    reference_pointer = RESULTS_ROOT / "algorithms/latest.json"
    previous_folder = json.loads(reference_pointer.read_text(encoding="utf-8"))["folder"] if reference_pointer.exists() else None
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder = RESULTS_ROOT / "refinements" / run_id
    folder.mkdir(parents=True)
    registry_folder = DATA_ROOT / "research/experiments"
    registry_folder.mkdir(parents=True, exist_ok=True)
    registry = registry_folder / "registry.jsonl"
    declaration = {"run_id": run_id, "study": "one_parameter_at_a_time", "plan": plan,
                   "base_settings": base_settings, "costs": costs, "variants": variants,
                   "data_hashes": hashes, "coverage": coverage, "symbols": list(series),
                   "previous_experiment": previous_folder, "prior_data_exposure": True,
                   "live_config_modified": False, "python": sys.version}
    source_folder = folder / "source"
    source_folder.mkdir()
    for relative in ("research/algorithm_study.py", "research/algorithm_refinements.py", "research/algorithm_analysis.py",
                     "tools/run_algorithm_refinements.py", "tools/run_algorithm_study.py", "research/backtest.py", "research/daily.py"):
        raw = (CODE_ROOT / relative).read_bytes()
        declaration.setdefault("code_hashes", {})[relative] = hashlib.sha256(raw).hexdigest()
        (source_folder / relative.replace("/", "-")).write_bytes(raw)
    write_json(folder / "declaration.json", declaration)
    record_event(registry, {"run_id": run_id, "status": "declared", "study": "refinements", "folder": str(folder),
                           "variants": variants, "selection": plan, "previous_experiment": previous_folder})
    results = {variant["name"]: {} for variant in variants}
    analyses = {variant["name"]: {} for variant in variants}
    references, controls = {}, {}
    stress_costs = copy.deepcopy(costs)
    for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
        stress_costs[key] *= 2
    selection = None
    try:
        for stage in ("development", "validation", "evaluation"):
            period = base_settings["periods"][stage]
            if stage == "evaluation":
                selection = select_variant(results, variants, plan)
                write_json(folder / "selection-before-evaluation.json", selection)
                record_event(registry, {"run_id": run_id, "status": "selected_before_evaluation", **selection})
            references[stage] = {scenario: benchmark(proxy_bars, scenario_costs,
                {**base_settings, "spread_ratio": base_settings["spread_ratio"] * (2 if scenario == "double_cost" else 1)}, **period)
                for scenario, scenario_costs in (("base", costs), ("double_cost", stress_costs))}
            for number, variant in enumerate(variants, 1):
                name = variant["name"]
                results[name][stage], analyses[name][stage] = {}, {}
                for scenario, scenario_costs in (("base", costs), ("double_cost", stress_costs)):
                    event = {"run_id": run_id, "algorithm": name, "stage": stage, "scenario": scenario}
                    record_event(registry, {**event, "status": "started"})
                    settings = {**base_settings, **variant["risk"],
                                "spread_ratio": base_settings["spread_ratio"] * (2 if scenario == "double_cost" else 1)}
                    result = replay(series, features, proxy_features, variant["family"], variant["market_filter"],
                                    scenario_costs, settings, **period, strategy_config=variant["strategy"])
                    analysis = analyze(result, series, scenario_costs, settings["spread_ratio"])
                    # 같은 시세·비용·기간이면 기존 기준값 결과가 그대로 재현되어야 한다.
                    if variant["parent"] is None and previous_folder:
                        previous_path = Path(previous_folder) / f"{variant['family']}_market-{stage}-{scenario}.json"
                        if previous_path.exists():
                            previous_declaration = json.loads((previous_path.parent / "declaration.json").read_text(encoding="utf-8"))
                            same_inputs = (previous_declaration["data_hashes"] == hashes
                                           and previous_declaration["costs"] == costs
                                           and previous_declaration["settings"] == base_settings)
                            if same_inputs:
                                previous = json.loads(previous_path.read_text(encoding="utf-8"))
                                controls[name + "/" + stage + "/" + scenario] = result == previous
                                if result != previous:
                                    raise ArithmeticError("기준값 회귀 검증 실패: " + name)
                    result_path = folder / f"{name}-{stage}-{scenario}.json"
                    write_json(result_path, result)
                    results[name][stage][scenario], analyses[name][stage][scenario] = result, analysis
                    record_event(registry, {**event, "status": "completed", "summary": result["summary"], "result": str(result_path)})
                if number % 6 == 0:
                    row = results[name][stage]["base"]["summary"]
                    print(f"{stage} {number}/{len(variants)}: {name} {row['net_return']:.2%}", flush=True)
        write_json(folder / "summaries.json", {name: {stage: {scenario: result["summary"] for scenario, result in scenarios.items()}
                    for stage, scenarios in stages.items()} for name, stages in results.items()})
        write_json(folder / "analysis.json", analyses)
        write_json(folder / "references.json", references)
        write_json(folder / "baseline-controls.json", controls)
        checks = {name + "/" + stage + "/" + scenario: analysis["checks"]
                  for name, stages in analyses.items() for stage, scenarios in stages.items() for scenario, analysis in scenarios.items()}
        write_json(folder / "validation.json", checks)
        check_count = sum(len(row) for row in checks.values())
        (folder / "validation.md").write_text(
            f"# 결과 검산\n\n{len(checks)}회 재생의 비용·현금·종목 기여 {check_count}항목 통과. validation.json 참고.\n\n"
            f"이전 기준값 비교 {sum(controls.values())}/{len(controls)}회. 0회이면 미검증. baseline-controls.json 참고.\n\n"
            "전체 자동 검증은 별도 `python Code/main.py --test all`로 실행한다.\n", encoding="utf-8")
        write_report(folder, declaration, results, analyses, selection, references, controls)
        plot_report(folder, variants, results, selection, references, costs["starting_cash"]["US"])
        record_event(registry, {"run_id": run_id, "status": "finished", "study": "refinements",
                               "selected": selection["selected"], "folder": str(folder), "replays": len(variants) * 6})
    except Exception as error:
        record_event(registry, {"run_id": run_id, "status": "failed", "error_type": type(error).__name__})
        raise
    write_json(folder.parent / "latest.json", {"folder": str(folder)})
    destination = DATA_ROOT / "reports/refinements"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("report.md", "performance.png", "robustness.png", "sensitivity.png", "declaration.json",
                 "summaries.json", "selection-before-evaluation.json", "baseline-controls.json", "validation.json", "validation.md"):
        shutil.copy2(folder / name, destination / name)
    # 앞 실행의 자동 테스트 로그를 새 실행에서 통과한 것처럼 표시하지 않는다.
    for old_name in ("test-log.txt", "behavior-equivalence.json"):
        old_path = destination / old_name
        if old_path.exists():
            old_path.replace(destination / ("previous-" + old_name))
    write_json(destination / "latest.json", {"folder": str(folder)})
    journal = CODE_ROOT.parent / "Docs/RESEARCH_LOG.md"
    with journal.open("a", encoding="utf-8") as stream:
        stream.write(f"\n## {run_id}: 한 항목씩 조정한 {len(variants)}개 가설·{len(variants) * 6}회 재생\n\n")
        stream.write("- 변경 이유: 이전 연구의 선정 저변동성 후보가 이후 비용 스트레스에서 손실. 돌파·추세·회전의 주변 설정과 비용 안정성을 함께 확인.\n")
        stream.write(f"- 범위·선정 기준은 결과 전에 선언. 사전 선정: {selection['selected'] or '현금 — 적격 후보 없음'}.\n")
        stream.write(f"- 결과 폴더: `{folder}`. [최신 소폭 조정 보고서](../Data/reports/refinements/report.md).\n")
        stream.write("- 기존 자료 재사용 후속 탐색이며 독립 검증 아님. 실제 주문·운용 설정 변경 없음.\n")
    print("보고서:", destination / "report.md", flush=True)
