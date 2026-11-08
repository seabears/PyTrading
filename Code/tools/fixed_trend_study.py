"""고정한 일봉 후보를 현금·SPY·기존 단기 결과와 비교한다. 자동 실전 채택은 하지 않는다."""
import copy
import hashlib
import json
import os
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from paths import CODE_ROOT, CONFIG_ROOT, DATA_ROOT, RESULTS_ROOT
from research.algorithm_study import benchmark, replay
from research.algorithm_analysis import analyze
from tools.run_algorithm_study import load_inputs, write_json


def audit_forward(folder):
    """저장된 실제 관측만 집계한다. 체결 0을 검증된 무위험 수익으로 표현하지 않는다."""
    path = folder / "decisions.jsonl"
    reasons, actions = Counter(), Counter()
    first, last, total, invalid, fills, regular = None, None, 0, 0, 0, 0
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                    stamp = row["snapshot"]["now"]
                    datetime.fromisoformat(stamp)
                    decision = row["decision"]
                    reasons[decision["reason"]] += 1
                    actions[decision["action"]] += 1
                    first = min(first, stamp) if first else stamp
                    last = max(last, stamp) if last else stamp
                    total += 1
                    fills += bool(decision.get("paper_fill"))
                    regular += row["snapshot"].get("regular_session_open") is True
                except (ValueError, KeyError, TypeError):
                    invalid += 1
    return {"folder": str(folder), "observations": total, "invalid_rows": invalid,
        "first": first, "last": last, "reasons": dict(reasons), "actions": dict(actions),
        "fills": fills, "regular_session_observations": regular,
        "continuous_running_proven": False, "no_records_is_not_zero_loss_proof": True}


def review_gate(summary, sessions, policy):
    """양수 몇 일만으로 채택하지 않는다. 연구 검토 자격이며 실전 승인 조건은 아니다."""
    checks = {"enough_sessions": sessions >= policy["minimum_forward_sessions"],
        "enough_closed_trades": summary["trades"] >= policy["minimum_closed_trades_for_review"],
        "net_positive": summary["net_return"] > 0,
        "drawdown_within_limit": summary["max_drawdown"] <= policy["maximum_review_drawdown"]}
    return {"checks": checks, "review_eligible": all(checks.values()), "live_approved": False}


def plot_report(folder, results, initial):
    os.environ["MPLCONFIGDIR"] = str(DATA_ROOT / "cache/plots")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(2, 1, figsize=(12, 8))
    for label, name in (("Frozen daily trend", "historical/base"), ("SPY 50% + cash", "historical/spy-base")):
        curve = results[name]["curve"]
        dates = [datetime.fromisoformat(point["date"]) for point in curve]
        axes[0].plot(dates, [(point["equity"] / initial - 1) * 100 for point in curve], label=label)
    axes[0].axhline(0, color="gray", linestyle="--", label="Cash, no interest")
    axes[0].set_title("Historical replay through 2026-10-21 / reused data, simulated fills")
    axes[0].set_ylabel("Net account return (%)")
    names = ["Short intraday", "Frozen daily", "SPY 50%", "Cash"]
    rows = [results["overlap/short-base"]["summary"], results["overlap/base"]["summary"],
            results["overlap/spy-base"]["summary"], {"net_return": 0, "max_drawdown": 0}]
    positions = list(range(len(rows)))
    axes[1].bar([value - .18 for value in positions], [row["net_return"] * 100 for row in rows], width=.35, label="Net return")
    axes[1].bar([value + .18 for value in positions], [row["max_drawdown"] * 100 for row in rows], width=.35, label="Maximum drawdown")
    axes[1].set_xticks(positions, names)
    axes[1].set_title("Same dates: 2026-09-18 to 2026-10-21 / daily MDD misses intraday dips")
    axes[1].set_ylabel("Percent")
    for axis in axes:
        axis.legend(fontsize=8)
        axis.grid(axis="y", alpha=.2)
    figure.tight_layout()
    figure.savefig(folder / "comparison.png", dpi=150)
    plt.close(figure)


def main():
    plan_path = CONFIG_ROOT / "fixed-trend-study.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    candidate = plan["candidate"]
    pointer = DATA_ROOT / "fixed-trend/datasets/latest.json"
    dataset = Path(json.loads(pointer.read_text(encoding="utf-8"))["folder"]).resolve()
    if not dataset.is_relative_to((DATA_ROOT / "fixed-trend/datasets").resolve()):
        raise ValueError("연구 데이터 경로 범위 오류")
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("complete") is not True or manifest.get("errors"):
        raise ValueError("불완전 수집 결과는 평가하지 않습니다.")
    collected_plan = json.loads((dataset / "plan-before-collection.json").read_text(encoding="utf-8"))
    if collected_plan != plan:
        raise ValueError("수집 전에 고정한 연구 조건과 현재 조건이 다릅니다.")
    for row in manifest["rows"]:
        path = dataset / "daily" / ("US-" + row["symbol"] + ".json")
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("시세 해시 불일치")
    settings, costs, series, features, proxy, proxy_features, hashes, coverage = load_inputs(dataset_root=dataset)
    settings = {**settings, **candidate["risk"]}
    scenarios = {"base": costs, "double_cost": copy.deepcopy(costs)}
    for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
        scenarios["double_cost"][key] *= 2
    periods = {"historical": {"start": plan["historical_start"], "end": plan["previous_cutoff"]},
        "overlap": {"start": plan["short_comparison_start"], "end": plan["short_comparison_end"]},
        "fresh": {"start": plan["fresh_start"], "end": plan["collection_end"]}}
    folder = RESULTS_ROOT / "fixed-trend" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True)
    operational = {name: audit_forward(DATA_ROOT / name) for name in ("paper-price-research", "paper-kis")}
    declaration = {"plan": plan, "candidate": candidate, "dataset": str(dataset),
        "hashes": hashes, "coverage": coverage, "settings": settings, "costs": costs,
        "periods": periods, "stress_spread_unchanged_to_match_prior_short_test": True,
        "historical_data_reused": True, "fresh_is_historical_replay_not_real_time": True,
        "live_config_modified": False, "automatic_adoption": False}
    for relative in ("research/algorithm_study.py", "research/algorithm_analysis.py", "tools/fixed_trend_study.py", "tools/run_algorithm_study.py", "research/daily.py", "research/backtest.py"):
        raw = (CODE_ROOT / relative).read_bytes()
        target = folder / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        declaration.setdefault("code_hashes", {})[relative] = hashlib.sha256(raw).hexdigest()
    write_json(folder / "declaration-before-results.json", declaration)
    write_json(folder / "operational-audit.json", operational)
    results, checks = {}, {}
    for period_name, period in periods.items():
        for scenario, scenario_costs in scenarios.items():
            name = period_name + "/" + scenario
            result = replay(series, features, proxy_features, candidate["family"], candidate["market_filter"],
                scenario_costs, settings, **period, strategy_config=candidate["strategy"])
            analysis = analyze(result, series, scenario_costs, settings["spread_ratio"])
            results[name] = result
            checks[name] = analysis["checks"]
            results[period_name + "/spy-" + scenario] = benchmark(proxy, scenario_costs, settings, **period)
            write_json(folder / (name.replace("/", "-") + ".json"), result)
            print(name, json.dumps(result["summary"], ensure_ascii=False), flush=True)
    # 단기 결과는 이전 원본·기간·비용을 확인하고 재사용한다.
    prior_pointer = DATA_ROOT / "reports/price-research/latest.json"
    prior = Path(json.loads(prior_pointer.read_text(encoding="utf-8"))["folder"]).resolve()
    if not prior.is_relative_to((RESULTS_ROOT / "price-research").resolve()):
        raise ValueError("단기 결과 경로 범위 오류")
    old_decl = json.loads((prior / "declaration.json").read_text(encoding="utf-8"))
    if old_decl["start"] != periods["overlap"]["start"] or old_decl["end"] != periods["overlap"]["end"] or old_decl["paper"] != costs:
        raise ValueError("단기 비교 기간·비용이 일치하지 않습니다.")
    for scenario in scenarios:
        path = prior / (scenario + ".json")
        raw = path.read_bytes()
        results["overlap/short-" + scenario] = json.loads(raw)
        shutil.copy2(path, folder / ("short-" + scenario + ".json"))
        declaration.setdefault("prior_short_hashes", {})[scenario] = hashlib.sha256(raw).hexdigest()
    # 수정 가격을 다시 받으면 같은 과거 날짜도 바뀔 수 있어 차이를 기록한다.
    revisions = {}
    for key in [*series, "US:SPY"]:
        path = DATA_ROOT / "history/daily" / (key.replace(":", "-") + ".json")
        old = json.loads(path.read_text(encoding="utf-8"))
        new = json.loads((dataset / "daily" / path.name).read_text(encoding="utf-8"))
        previous = {row["timestamp"][:10]: row for row in old["candles"]}
        revisions[key] = sum(row != previous[row["timestamp"][:10]] for row in new["candles"] if row["timestamp"][:10] in previous)
    write_json(folder / "historical-revisions.json", revisions)
    sessions = len(results["fresh/base"]["curve"])
    gate = review_gate(results["fresh/base"]["summary"], sessions, plan)
    write_json(folder / "review-gate.json", gate)
    write_json(folder / "declaration.json", declaration)
    write_json(folder / "validation.json", checks)
    write_json(folder / "results.json", results)
    plot_report(folder, results, costs["starting_cash"]["US"])
    lines = ["# 고정 일봉 후보·운용 기록 점검", "",
        f"고정 후보: {candidate['name']}. 이전 개발·검증 선정 결과를 그대로 사용했고 새 결과로 재선정하지 않았다.",
        "현재 시세를 새로 받은 과거 재생 결과다. 실제 주문·실시간 운용 수익이 아니다. 기존 시세·계좌·운용 전략은 변경하지 않았다.", "",
        "## 실제 모의 관측 기록", "", "|계좌|관측 수|정규장 관측|체결|마지막 관측|", "|---|---:|---:|---:|---|"]
    for name, row in operational.items():
        lines.append(f"|{name}|{row['observations']}|{row['regular_session_observations']}|{row['fills']}|{row['last']}|")
    lines += ["", "미관측은 손실 0의 증거가 아니다. 현재 저장 기록으로 지속 운용을 입증할 수 없다.", "",
        "## 비용 반영 비교", "", "|기간|전략|순수익|MDD|완료 거래|", "|---|---|---:|---:|---:|"]
    for period_name in periods:
        for name, label in (("base", "고정 일봉"), ("double_cost", "고정 일봉 비용 두 배"), ("spy-base", "SPY 50%+현금"), ("short-base", "기존 단기"), ("short-double_cost", "기존 단기 비용 두 배")):
            key = period_name + "/" + name
            if key not in results:
                continue
            row = results[key]["summary"]
            lines.append(f"|{period_name}|{label}|{row['net_return']:.2%}|{row['max_drawdown']:.2%}|{row.get('trades', row.get('closed_trades', 0))}|")
        lines.append(f"|{period_name}|현금(무이자)|0.00%|0.00%|0|")
    lines += ["", "## 기간과 해석", ""]
    lines += [f"- {name}: {period['start']} ~ {period['end']}" for name, period in periods.items()]
    lines += ["", "각 기간은 초기 1만 USD의 별도 계좌로 시작한다. 수익률을 합산하지 않는다. SPY는 최대 투자 한도 50%에 맞춘 정수 수량 단순 보유이며 배당 재투자 지수가 아니다.",
        "동일 기간 비교도 완전한 대조 실험은 아니다. 일봉은 종가 신호 후 다음 시가·ATR 손절·거래 위험 0.25%, 단기는 분봉 판단·거래 위험 0.5% 등 계좌 정책이 다르다. 일봉 MDD는 종가만 보므로 단기의 분별 MDD보다 작게 보일 수 있다.",
        "비용 두 배는 매수·매도 비용·슬리피지만 두 배이며 호가 스프레드는 기존 단기 시험과 동일하게 0.1%로 유지했다. 비용 가정이며 실제 세율·요율이 아니다.",
        "신규 구간은 기존 평가 종료일 뒤의 과거 재생으로 실시간 모의 운용이 아니다. 현재 종목 소급 선택 편향·수정주가 재수신·배당 현금 미반영·가상 체결 한계가 있다.",
        f"신규 구간은 {sessions}거래일이며 검토 자격 통과: {gate['review_eligible']}. 최소 20거래일·완료 30거래·수익 양수·MDD 8% 이하를 모두 확인해야 연구 검토 자격만 생긴다. 자동 실전 승인은 하지 않는다.",
        "과거 단기 결과는 원본 파일을 복사하고 해시·기간·비용을 기록해 재사용했다. 장기 분봉이 없어 장기 단기전략 수익률을 만들어내지 않았다.", "",
        "## 연도별 고정 일봉 성과", "", "|연도|기본 비용|비용 두 배|", "|---|---:|---:|"]
    historical = results["historical/base"]["summary"]
    stress = results["historical/double_cost"]["summary"]
    for year, returns in historical["year_returns"].items():
        lines.append(f"|{year}|{returns:.2%}|{stress['year_returns'][year]:.2%}|")
    lines += ["", f"장기 일봉 평균 투자 노출은 초기 자금의 {historical['average_exposure']:.1%}, 완료 거래 Profit Factor는 {historical['profit_factor']:.3f}다. 작은 낙폭은 낮은 투자 비중의 영향도 받는다. SPY 50% 보유와 위험이 같다고 볼 수 없다. 2026년은 10월 21일까지의 부분 기간이다.",
        "", "## 재수집된 과거 수정 가격", ""]
    changes = {key: count for key, count in revisions.items() if count}
    lines += [f"- {key}: 이전과 다른 봉 {count}개" for key, count in changes.items()]
    if not changes:
        lines.append("이전 겹치는 봉과 숫자 차이를 발견하지 못했다.")
    lines += ["수정 가격 변경의 원인은 이번 작업에서 검증하지 않았다. 새 원본·기존 원본을 모두 보존했으며 새 데이터에서의 재생을 이전 결과의 완전 재현이라고 주장하지 않는다.", "",
        "## 이후 실행", "", "기존 가격 연구는 python Code/price_paper.py로 별도 가상 계좌에 관측을 계속할 수 있다. 일봉 후보는 아직 실시간 체결 경로에 연결하지 않았다. 새 데이터 몇 일의 결과로 연결을 자동 승인하지 않는다.",
        "다음은 실제 정규장 관측을 누적하고, 동일한 고정 일봉 규칙의 지속 계좌·다음 시가 가상 체결 경로를 검증하는 단계다. 뉴스·실적과 분리하고 FMP는 사용하지 않는다.",
        "", "![성과 비교](comparison.png)", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")
    destination = DATA_ROOT / "reports/fixed-trend"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("report.md", "comparison.png", "declaration.json", "operational-audit.json", "review-gate.json", "validation.json", "historical-revisions.json"):
        shutil.copy2(folder / name, destination / name)
    for path in (destination, folder.parent):
        write_json(path / "latest.json", {"folder": str(folder)})
    with (CONFIG_ROOT.parent / "Docs/RESEARCH_LOG.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n\n## {folder.name} — 고정 일봉 후보·기존 단기·현금·SPY 비교\n\n- 후보 {candidate['name']} 고정. 새 스냅샷 {dataset}. 기존 모의 기록·원본 해시·수정 이력·비용 검산 보존.\n- 기존 구간 재사용, 신규 구간 {sessions}거래일 과거 재생. 실시간 성과로 해석하지 않음. 실전 자동 채택 없음.\n- 결과: {folder}.\n")
    print("보고서:", destination / "report.md", flush=True)
