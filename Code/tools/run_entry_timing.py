"""매수 시점 연구 실행. 저장 자료만 사용하며 운용 설정·계좌는 수정하지 않는다."""
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from paths import CODE_ROOT, CONFIG_ROOT, DATA_ROOT, RESULTS_ROOT
from research.entry_inputs import daily_inputs, intraday_inputs
from research.entry_timing import study_series, summarize
from tools.run_algorithm_study import record_event, write_json


def grouped_summary(rows, baseline, field):
    order = {"development": 0, "validation": 1, "evaluation": 2}
    values = sorted({row[field] for row in rows}, key=lambda value: order[value] if field == "stage" else value)
    return {value: summarize([row for row in rows if row[field] == value], baseline)
            for value in values}


def load_verified(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("실험 선언 뒤 원본 데이터가 변경되었습니다.")
    return json.loads(raw)


def make_plots(folder, summaries, time_groups):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(2, 2, figsize=(15, 10))
    for r, kind in enumerate(("daily", "intraday")):
        horizon = max(row["horizon"] for row in summaries[kind])
        rows = [row for row in summaries[kind] if row["horizon"] == horizon]
        names = [row["mode"] for row in rows]
        x = list(range(len(rows)))
        axes[r, 0].bar([n - .18 for n in x], [row["mean_all"] * 100 for row in rows], width=.35, label="Base costs")
        axes[r, 0].bar([n + .18 for n in x], [row["mean_all_double"] * 100 for row in rows], width=.35, label="Double costs")
        axes[r, 0].set_title(f"{kind}: same exit, {horizon} {'sessions' if kind == 'daily' else 'minutes'} after anchor")
        axes[r, 0].set_ylabel("Mean event return incl. no-fill cash (%)")
        axes[r, 0].set_xticks(x, names, rotation=25, ha="right")
        axes[r, 0].legend(fontsize=8)
        axes[r, 1].bar(x, [row["fill_rate"] * 100 for row in rows], color="steelblue")
        axes[r, 1].set_ylim(0, 105)
        axes[r, 1].set_xticks(x, names, rotation=25, ha="right")
        axes[r, 1].set_title(f"{kind}: common anchors n={rows[0]['events']}")
        axes[r, 1].set_ylabel("Fill rate by common exit (%)")
    for axis in axes.flat:
        axis.axhline(0, color="gray", linewidth=.6)
        axis.grid(axis="y", alpha=.2)
    figure.suptitle("Entry timing event study — retrospective, simulated fills; NOT account returns")
    figure.tight_layout()
    figure.savefig(folder / "timing.png", dpi=150)
    plt.close(figure)
    figure, axes = plt.subplots(1, 2, figsize=(14, 5))
    for axis, kind, group_field in ((axes[0], "daily", "stage"), (axes[1], "intraday", "time_bucket")):
        groups = time_groups[kind]
        for mode in sorted({row["mode"] for rows in groups.values() for row in rows}):
            points = [(name, next(row for row in rows if row["mode"] == mode and row["horizon"] == (20 if kind == "daily" else 30))) for name, rows in groups.items()]
            axis.plot(range(len(points)), [row["mean_all"] * 100 for name, row in points], marker="o", label=mode)
        names = list(groups)
        axis.set_xticks(range(len(names)), names, rotation=20, ha="right")
        axis.set_ylabel("Mean event return incl. cash (%)")
        axis.set_title(kind + ": " + group_field + " (not independent samples)")
        axis.axhline(0, color="gray", linewidth=.6)
        axis.grid(alpha=.2)
        axis.legend(fontsize=7)
    figure.tight_layout()
    figure.savefig(folder / "segments.png", dpi=150)
    plt.close(figure)


def percent(value):
    return "—" if value is None else f"{value:.2%}"


def report(folder, declaration, summaries, audits, segments):
    daily_primary = {row["mode"]: row for row in summaries["daily"] if row["horizon"] == 20}
    minute_primary = {row["mode"]: row for row in summaries["intraday"] if row["horizon"] == 30}
    immediate, confirmed = daily_primary["next_open"], daily_primary["confirm_1"]
    minute = minute_primary["next_minute"]
    lines = ["# 매수 타이밍 연구: 일봉과 장중", "",
        "동일 돌파 사건의 진입 시점만 바꾼 탐색 연구다. 표의 수익은 사건당 수익이며 계좌 수익률·연수익률이 아니다.",
        "중복 자금·포지션 크기·실제 매도 알고리즘을 적용한 전략 백테스트와 구분한다. 운용 설정·계좌는 바꾸지 않았다.", "",
        "## 이번 결과의 해석", "",
        f"- 일봉 20거래일 공통 종료: 즉시 진입 체결 평균 {percent(immediate['mean_filled'])}, 미체결 포함 {percent(immediate['mean_all'])}. 추가 상승 확인은 체결 평균 {percent(confirmed['mean_filled'])}지만 미체결 포함 {percent(confirmed['mean_all'])}다.",
        f"- 확인 후 진입은 체결 {confirmed['fills']}/{confirmed['events']}, 즉시는 {immediate['fills']}/{immediate['events']}. 양쪽이 모두 체결된 {confirmed['paired_count']}건에서는 확인 후 진입 수익이 평균 {percent(confirmed['paired_delta'])} 차이였다. 체결 평균 증가만으로 개선을 주장할 수 없다.",
        f"- 장중 즉시 진입 30분의 비용 전 평균 {percent(minute['mean_gross_filled'])}, 비용 후 {percent(minute['mean_filled'])}. 현재 가정에서 6개 장중 조건 모두 비용 후 사건 평균이 음수다.",
        "- 장중 대기 조건의 손실 감소에는 거래 취소·보유 시간 단축 효과가 섞인다. 좋은 진입 가격을 찾았다는 증거와 구분해야 한다.",
        f"- 안정성은 미확인이다. 일봉 즉시 진입의 평균 MAE {percent(immediate['mean_mae'])}, 최악 MAE {percent(immediate['worst_mae'])}. 이번 실험은 보호 매도 없이 진입을 분리해 측정했다.", "",
        "## 고정 조건", "",
        "- 일봉: 28개 동종 기업, 직전 55거래일 고점 종가 돌파 + SPY 종가>MA200. 종목 201개 관측 봉 이후, 직전 55일 누락 시 신호 제외.",
        "- 일봉 단계: 2020–2022 / 2023–2024 / 2025–2026-10-23. 이미 여러 연구에서 본 자료이며 미사용 검증으로 주장하지 않는다.",
        "- 장중: 기존 운용 목록 30종목의 저장 분봉. 동일 정규장 내 연속 5분봉 21개, 직전 20개 고점 돌파·평균 거래량 2배. 신호에 시장 필터 없음.",
        "- 주문은 신호 또는 확인 봉 완성 후 다음 봉 시가. 현재 주문 봉의 고가·저가·종가·거래량은 판단에 사용하지 않는다.",
        "- delay: 지정 기간 대기하며 완성된 확인 봉 종가가 돌파선 아래면 취소. confirm은 추가로 마지막 확인 종가≥최초 신호 종가를 요구한다.",
        "- retest: 최대 대기 기간 안에 저가≤돌파선+신호 ATR14×0.25, 종가≥돌파선 및 종가≤최초 신호 종가일 때 다음 시가 진입. 장중은 5분마다 확인.",
        "- 시가가 돌파선 아래 또는 직전 확인 종가 대비 갭이 일봉 3% / 장중 0.3% 초과면 취소. 별도 gap 조건은 각각 1% / 0.1%로 강화.",
        "- 매수 비용 0.1%, 매도 비용 0.2%, 편도 슬리피지 0.1%, 스프레드 0.1% 가정. 두 배 비용은 네 비율 모두 두 배. 실제 요율·호가 이력이 아니다.",
        "- 같은 종목의 사건 간격은 일봉 31거래일 이상 / 장중 46분 이상. 미래 손익과 관계없이 첫 신호를 선택한다. 종목 간 사건 상관은 남는다.",
        "- 모든 조건에 같은 관측 창을 적용: 일봉 30거래일 / 장중 45분 후까지 자료가 있어야 채택. 단계 경계·누락·마감 임박·끝부분은 별도 audit에 보존.",
        "- 주 지표는 **즉시 진입 기준과 같은 날짜/시각에 매도**. 일봉 5·10·20거래일, 장중 5·15·30분. 그 뒤에 진입하는 조건은 해당 짧은 창에서 미체결로 기록.",
        "- 보조 mean_holding은 진입 후 같은 봉 수 보유. 이때는 매도 시점도 이동하므로 주 비교와 다르다.",
        "- MAE는 진입 후 공통 매도까지 저가 기준 최대 역행률(비용 제외). 계좌 MDD나 실제 손절 체결 결과가 아니다.", ""]
    for kind in ("daily", "intraday"):
        lines += [f"## {kind} 전체 결과", "", "사건 평균은 미체결을 현금 수익 0으로 포함한다. 체결 평균은 매수된 표본만 사용하므로 단독으로 우열을 판단하지 않는다.", "",
            "|조건|관측 길이|체결/사건|비용 전 체결 평균|비용 후 체결 평균|현금 포함 평균|두 배 비용|짝 비교 차이|짝 표본|평균 MAE|", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for row in summaries[kind]:
            lines.append(f"|{row['mode']}|{row['horizon']}|{row['fills']}/{row['events']}|{percent(row['mean_gross_filled'])}|{percent(row['mean_filled'])}|{percent(row['mean_all'])}|{percent(row['mean_all_double'])}|{percent(row['paired_delta'])}|{row['paired_count']}|{percent(row['mean_mae'])}|")
        lines += ["", "짝 비교 차이는 양쪽 모두 체결된 같은 사건에서 조건−즉시진입 차이다. 미체결에 따른 기회 손익은 summaries.json의 opportunity_delta에 별도 보존.",
                  "", "사건 처리 수: `" + json.dumps(dict(Counter(row["status"] for row in audits[kind])), ensure_ascii=False) + "`", ""]
        for segment, rows in segments[kind].items():
            lines += [f"### {segment}", "", "|조건|체결/사건|현금 포함 평균|두 배 비용|", "|---|---:|---:|---:|"]
            for row in rows:
                if row["horizon"] == (20 if kind == "daily" else 30):
                    lines.append(f"|{row['mode']}|{row['fills']}/{row['events']}|{percent(row['mean_all'])}|{percent(row['mean_all_double'])}|")
            lines.append("")
    lines += ["## 한계와 다음 검증", "",
        "- 장중 자료는 약 한 달로 시장 국면·종목별·시간대별 표본이 작다. 연율 환산·최적 시각·안정적 수익을 주장하지 않는다.",
        "- 장중 21개 5분봉 준비로 가장 빠른 신호는 뉴욕 11:15. 장 시작 직후는 시험 대상이 아니며, 마감 전 45분은 공통 관측 창 부족으로 제외된다.",
        "- 현재 목록을 과거로 소급한 종목 선택·생존 편향, 배당 현금 미반영, 수정 일봉과 비수정 분봉 차이가 있다. 일봉과 장중의 표본·보유 시간도 달라 두 수치를 직접 비교하지 않는다.",
        "- 지연 없는 데이터·전량 체결을 가정한다. 누락 창 제외도 편향을 남길 수 있어 제외 수를 공개한다. 통계적 독립성이나 유의성은 검증하지 않았다.",
        "- 취소된 사건과 시간대별·종목별·연도별 결과도 저장했다. 전체에서 좋아 보이는 조건을 자동 채택하지 않는다.",
        "- 다음 단계는 후보를 사전 고정하고 새로운 장중 자료를 누적한 뒤, 동일 공동 자금·매도 규칙에서 재검증하는 것이다.", "",
        "![진입 비교](timing.png)", "", "![기간·시간대 비교](segments.png)", "",
        f"실행 보존 경로: `{folder}`", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    config = json.loads((CONFIG_ROOT / "entry-timing.json").read_text(encoding="utf-8"))
    paper = json.loads((CONFIG_ROOT / "paper.json").read_text(encoding="utf-8"))
    costs = {key: paper[key] for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}
    daily_folder = Path(json.loads((DATA_ROOT / "industry-peers/datasets/latest.json").read_text(encoding="utf-8"))["folder"]) / "daily"
    # 기존 분봉은 새 동종 기업 13종목과 별개다. 현재 운용 목록만 읽는다.
    settings = json.loads((CONFIG_ROOT / "settings.json").read_text(encoding="utf-8"))
    minute_files = [DATA_ROOT / "history/minute" / ("US-" + symbol.split(":")[-1] + ".json") for symbol in settings["symbols"]]
    daily_files = sorted(daily_folder.glob("*.json"))
    files = daily_files + minute_files
    hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder = RESULTS_ROOT / "entry-timing" / run_id
    (folder / "source").mkdir(parents=True)
    declaration = {"run_id": run_id, "config": config, "costs": costs, "data_hashes": hashes,
        "daily_source": str(daily_folder), "minute_symbols": settings["symbols"],
        "prior_data_exposure": True, "live_config_modified": False, "automatic_selection": False}
    for relative in ("research/entry_timing.py", "research/entry_inputs.py", "tools/run_entry_timing.py",
                     "research/algorithm_study.py", "research/backtest.py", "research/daily.py", "research/engine_backtest.py", "broker/toss.py", "broker/sessions.py"):
        raw = (CODE_ROOT / relative).read_bytes()
        declaration.setdefault("code_hashes", {})[relative] = hashlib.sha256(raw).hexdigest()
        (folder / "source" / relative.replace("/", "-")).write_bytes(raw)
    write_json(folder / "declaration.json", declaration)
    registry = DATA_ROOT / "research/experiments/registry.jsonl"
    record_event(registry, {"study": "entry_timing", "run_id": run_id, "status": "declared", "folder": str(folder), "config": config})
    rows, audits, coverage = {}, {}, {}
    try:
        records = {}
        for path in files:
            if path in daily_files:
                record = load_verified(path, hashes[str(path)])
                records[record["symbol"]] = record
        for kind in ("daily", "intraday"):
            rows[kind], audits[kind], coverage[kind] = [], [], {}
            if kind == "daily":
                sources = daily_inputs(records, config["periods"])
            else:
                sources = (item for path in minute_files for item in intraday_inputs(path.stem.removeprefix("US-"), load_verified(path, hashes[str(path)])))
            for symbol, bars, anchors, source_coverage in sources:
                result, audit = study_series(bars, anchors, costs=costs, spread=config["spread_ratio"], **config[kind])
                rows[kind].extend(result)
                audits[kind].extend(audit)
                coverage[kind].setdefault(symbol, []).append(source_coverage)
            if not rows[kind]:
                raise ValueError(kind + " 성숙 사건이 없습니다.")
            write_json(folder / (kind + "-events.json"), rows[kind])
            write_json(folder / (kind + "-audit.json"), audits[kind])
            print(kind + ": " + str(Counter(row["status"] for row in audits[kind])), flush=True)
        summaries = {kind: summarize(rows[kind], config[kind]["modes"][0]["name"]) for kind in rows}
        segments = {kind: grouped_summary(rows[kind], config[kind]["modes"][0]["name"], "stage" if kind == "daily" else "time_bucket") for kind in rows}
        details = {kind: {"symbol": grouped_summary(rows[kind], config[kind]["modes"][0]["name"], "symbol"),
                   "year": grouped_summary([{**row, "year": row["date"][:4]} for row in rows[kind]], config[kind]["modes"][0]["name"], "year")} for kind in rows}
        # 성숙 사건·조건·관측 길이의 각 조합은 정확히 한 번만 기록되어야 한다.
        checks = {}
        for kind, result in rows.items():
            accepted = sum(row["status"] == "accepted" for row in audits[kind])
            expected = accepted * len(config[kind]["modes"]) * len(config[kind]["horizons"])
            checks[kind] = {"expected_rows": expected, "actual_rows": len(result),
                "unique_rows": len({(row["event_id"], row["mode"], row["horizon"]) for row in result})}
            assert expected == len(result) == checks[kind]["unique_rows"]
            for row in result:
                if row["common_net"] is not None:
                    assert row["signal_index"] < row["entry_index"] <= row["common_exit_index"]
                    assert row["common_double"] < row["common_net"]
                    assert row["mae"] <= 0 <= row["mfe"]
        for name, value in (("summaries", summaries), ("segments", segments), ("details", details), ("coverage", coverage), ("validation", checks)):
            write_json(folder / (name + ".json"), value)
        report(folder, declaration, summaries, audits, segments)
        make_plots(folder, summaries, segments)
        write_json(folder.parent / "latest.json", {"folder": str(folder)})
        destination = DATA_ROOT / "reports/entry-timing"
        destination.mkdir(parents=True, exist_ok=True)
        for name in ("report.md", "timing.png", "segments.png", "summaries.json", "segments.json", "details.json", "coverage.json", "validation.json", "declaration.json"):
            shutil.copy2(folder / name, destination / name)
        write_json(destination / "latest.json", {"folder": str(folder)})
        record_event(registry, {"study": "entry_timing", "run_id": run_id, "status": "finished", "folder": str(folder), "checks": checks})
        with (CODE_ROOT.parent / "Docs/RESEARCH_LOG.md").open("a", encoding="utf-8") as stream:
            stream.write(f"\n## {run_id}: 일봉·장중 매수 시점 사건 연구\n\n- 사전 고정 8개 일봉 / 6개 장중 조건, 세 관측 길이, 기본·두 배 비용. 미체결·제외 사건도 보존.\n- 계좌 수익이 아닌 같은 매도 시점의 사건 수익 비교. 자동 선택·운용 변경 없음.\n- 결과 `{folder}`. [보고서](../Data/reports/entry-timing/report.md).\n")
        print("보고서:", destination / "report.md", flush=True)
    except Exception as error:
        record_event(registry, {"study": "entry_timing", "run_id": run_id, "status": "failed", "error_type": type(error).__name__})
        raise
