"""산업군 기준 규칙을 2020년부터 연속 재생한다. 구간별 시험과 자본을 섞지 않는다."""
import copy
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from paths import CODE_ROOT, DATA_ROOT, RESULTS_ROOT
from research.algorithm_study import make_features, replay
from research.algorithm_analysis import analyze
from research.daily import prepare_daily_bars
from research.industry_study import peer_statistics
from tools.run_algorithm_study import record_event, write_json


def main():
    parent = Path(json.loads((RESULTS_ROOT / "industry-peers/latest.json").read_text(encoding="utf-8"))["folder"])
    previous = json.loads((parent / "declaration.json").read_text(encoding="utf-8"))
    primary = next(variant for variant in previous["study"]["variants"] if variant["name"] == previous["study"]["primary_variant"])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder = RESULTS_ROOT / "industry-continuous" / run_id
    (folder / "runs").mkdir(parents=True)
    period = {"start": previous["study"]["periods"]["development"]["start"],
              "end": previous["study"]["periods"]["evaluation"]["end"]}
    declaration = {"run_id": run_id, "study": "industry_continuous", "parent_study": str(parent),
                   "primary": primary, "period": period, "data_hashes": previous["data_hashes"],
                   "costs": previous["costs"], "settings": previous["settings"], "groups": previous["groups"],
                   "new_symbols": previous["new_symbols"], "choice_modified": False, "prior_data_exposure": True}
    source = folder / "source"
    source.mkdir()
    for relative in ("tools/run_industry_continuous.py", "research/algorithm_study.py", "research/algorithm_analysis.py", "research/backtest.py"):
        raw = (CODE_ROOT / relative).read_bytes()
        declaration.setdefault("code_hashes", {})[relative] = hashlib.sha256(raw).hexdigest()
        (source / relative.replace("/", "-")).write_bytes(raw)
    write_json(folder / "declaration.json", declaration)
    registry = DATA_ROOT / "research/experiments/registry.jsonl"
    record_event(registry, {"run_id": run_id, "study": "industry_continuous", "status": "declared",
                           "folder": str(folder), "primary": primary, "period": period})
    series, features, proxy = {}, {}, None
    for name, expected in previous["data_hashes"].items():
        raw = Path(name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("데이터 스냅샷 해시 변경")
        record = json.loads(raw)
        bars = prepare_daily_bars(record)
        rows = make_features(bars)
        if record["symbol"] == "SPY":
            proxy = {row["date"]: row for row in rows}
        else:
            series[record["symbol"]], features[record["symbol"]] = bars, rows
    summaries, analyses, checks = {"group": {}, "stock": {}}, {}, {}
    try:
        for scope, scopes in (("group", {key: group["symbols"] for key, group in previous["groups"].items()}),
                              ("stock", {symbol: [symbol] for symbol in series})):
            for scope_id, symbols in scopes.items():
                subset = {symbol: series[symbol] for symbol in symbols}
                subset_features = {symbol: features[symbol] for symbol in symbols}
                summaries[scope][scope_id] = {}
                for scenario in ("base", "double_cost"):
                    costs = copy.deepcopy(previous["costs"])
                    costs["max_positions_per_market"] = previous["study"]["group_maximum_positions"] if scope == "group" else 1
                    settings = {**previous["settings"], **primary["risk"]}
                    if scenario == "double_cost":
                        for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
                            costs[key] *= 2
                        settings["spread_ratio"] *= 2
                    event = {"run_id": run_id, "scope": scope, "scope_id": scope_id, "scenario": scenario}
                    record_event(registry, {**event, "status": "started"})
                    result = replay(subset, subset_features, proxy, primary["family"], True, costs, settings, **period, strategy_config=primary["strategy"])
                    analysis = analyze(result, subset, costs, settings["spread_ratio"])
                    key = scope + "-" + scope_id + "-" + scenario
                    write_json(folder / "runs" / (key + ".json"), result)
                    summaries[scope][scope_id][scenario] = result["summary"]
                    analyses[key], checks[key] = analysis, analysis["checks"]
                    record_event(registry, {**event, "status": "completed", "summary": result["summary"]})
                if scope == "group":
                    row = summaries[scope][scope_id]["base"]
                    print(f"연속 {scope_id}: {row['net_return']:.2%}, MDD {row['max_drawdown']:.2%}, {row['trades']}거래", flush=True)
        statistics = peer_statistics([{"symbol": symbol, **rows} for symbol, rows in summaries["stock"].items()],
                                     set(previous["new_symbols"]), previous["study"]["minimum_completed_trades_per_stock"])
        write_json(folder / "summaries.json", summaries)
        write_json(folder / "analysis.json", analyses)
        write_json(folder / "validation.json", checks)
        write_json(folder / "peer-statistics.json", statistics)
        lines = ["", "## 추가: 초기화 없는 2020년 이후 연속 재생", "",
                 f"기간 {period['start']} ~ {period['end']}, 기준 {primary['name']} 그대로. 기간별 수익률을 더하지 않고 계좌를 연속 운용했다.",
                 "8산업군+28개별 종목 × 두 비용 조건 = 72회 추가. 상장 전·지표 준비 전에는 현금 대기.", "",
                 "|산업군|연속 순수익률|비용 두 배|최대 낙폭|완료 거래|", "|---|---:|---:|---:|---:|"]
        for group_id, group in previous["groups"].items():
            row = summaries["group"][group_id]["base"]
            stress = summaries["group"][group_id]["double_cost"]
            lines.append(f"|{group['name']}|{row['net_return']:.2%}|{stress['net_return']:.2%}|{row['max_drawdown']:.2%}|{row['trades']}|")
        lines += ["", "### 기준 규칙의 신규 동종 기업 표본", "",
                  "|구분|종목|기본 비용 양수|두 배 비용 양수|10거래 이상|10거래 이상·두 비용 양수|", "|---|---:|---:|---:|---:|---:|"]
        for scope, row in statistics.items():
            lines.append(f"|{scope}|{row['stocks']}|{row['positive_base']}|{row['positive_double_cost']}|{row['enough_sample_stocks']}|{row['positive_both_with_enough_sample']}|")
        lines += ["", "연도별 성과와 전체 거래는 별도 연속 실험 폴더의 summaries.json과 runs에 보존했다.",
                  f"연속 실험 경로: `{folder}`. 이 결과는 이미 본 과거 기간의 탐색이며 새 미래 검증이 아니다.", ""]
        (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")
        with (parent / "report.md").open("a", encoding="utf-8") as stream:
            stream.write("\n".join(lines))
        shutil.copy2(parent / "report.md", DATA_ROOT / "reports/industry-peers/report.md")
        write_json(folder.parent / "latest.json", {"folder": str(folder)})
        write_json(parent / "continuous-study.json", {"folder": str(folder)})
        record_event(registry, {"run_id": run_id, "study": "industry_continuous", "status": "finished", "folder": str(folder), "replays": len(checks)})
    except Exception as error:
        record_event(registry, {"run_id": run_id, "study": "industry_continuous", "status": "failed", "error_type": type(error).__name__})
        raise
    with (CODE_ROOT.parent / "Docs/RESEARCH_LOG.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n### {run_id}: 동종 기업 연속 시험\n\n")
        stream.write(f"- 구간별 거래 수 부족을 확인해 동일 기준 규칙을 {period['start']}부터 초기화 없이 72회 추가 재생.\n")
        stream.write(f"- 규칙·종목 교체 없음. 결과 `{folder}`.\n")
    print("연속 시험:", folder, flush=True)
