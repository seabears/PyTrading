"""저장한 공식 원문을 대조하고 제한된 발표 후 수익 진단을 보존한다."""
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from statistics import mean

from paths import DATA_ROOT, CONFIG_ROOT, RESULTS_ROOT, CODE_ROOT
from news.earnings_audit import audit_identity, extract_release, audit_release, event_diagnostic
from research.daily import prepare_daily_bars


def main():
    audit_root = DATA_ROOT / "earnings-audit"
    raw_folder = audit_root / "raw"
    as_of = "2026-10-25"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder = RESULTS_ROOT / "earnings-audit" / run_id
    folder.mkdir(parents=True)
    identity = [audit_identity(row, raw_folder, as_of) for row in json.loads((audit_root / "identity-audit.json").read_text(encoding="utf-8"))]
    releases = json.loads((audit_root / "releases.json").read_text(encoding="utf-8"))
    audits, source_hashes = [], {}
    for row in releases:
        path = raw_folder / (row["release_id"] + "-ir.html")
        try:
            raw = path.read_bytes()
            source_hashes[str(path)] = hashlib.sha256(raw).hexdigest()
            facts_path = raw_folder / (row["symbol"] + "-companyfacts.json")
            facts = json.loads(facts_path.read_text(encoding="utf-8"))
            source_hashes[str(facts_path)] = hashlib.sha256(facts_path.read_bytes()).hexdigest()
            release = extract_release(raw, row["symbol"])
            result = audit_release({**row, **release}, facts, as_of)
            audits.append(result)
            print(row["release_id"], result["period_end"], result["checks"], flush=True)
        except (OSError, ValueError, KeyError) as error:
            audits.append({**row, "status": "unverified_parse_or_download", "error_type": type(error).__name__})
            print(row["release_id"], "UNVERIFIED", type(error).__name__, flush=True)
    series = {}
    for symbol in ("AAPL", "MSFT", "NVDA", "SPY"):
        path = DATA_ROOT / "history/daily" / ("US-" + symbol + ".json")
        source_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        series[symbol] = prepare_daily_bars(json.loads(path.read_text(encoding="utf-8")))
    costs_full = json.loads((CONFIG_ROOT / "paper.json").read_text(encoding="utf-8"))
    costs = {key: costs_full[key] for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}
    diagnostic = event_diagnostic(audits, series, series["SPY"], costs, .001)
    metrics = {}
    for horizon in (1, 5, 20):
        selected = [row for row in diagnostic if row["horizon"] == horizon]
        metrics[str(horizon)] = {"events": len(selected), "net_mean": mean(row["net_return"] for row in selected) if selected else None,
            "stress_mean": mean(row["double_cost_return"] for row in selected) if selected else None,
            "spy_excess_mean": mean(row["excess_return"] for row in selected) if selected else None,
            "win_rate": mean(row["net_return"] > 0 for row in selected) if selected else None}
    price_cutoff = min(bars[-1]["date"] for bars in series.values())
    earnings_ledger = DATA_ROOT / "paper-kis/earnings-events.jsonl"
    observable = 0
    if earnings_ledger.exists():
        for line in earnings_ledger.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["event"].get("available_at", "9999")[:10] <= price_cutoff:
                observable += 1
    validation = {"identity_counts": dict(Counter(row["coverage"] for row in identity)),
        "release_checks": dict(Counter(value for row in audits for key, value in row.get("checks", {}).items() if key != "non_gaap_eps")),
        "fully_cross_checked_releases": sum(row.get("actuals_cross_checked", False) for row in audits),
        "release_count": len(audits), "original_strategy_status": "not_validated_missing_pre_release_consensus_and_first_seen_history",
        "actual_system_observable_events_before_price_cutoff": observable, "diagnostic_metrics": metrics,
        "price_cutoff": price_cutoff, "source_hashes": source_hashes, "live_unverified_headlines_blocked": True}
    for name, value in (("identity", identity), ("releases", audits), ("diagnostic-events", diagnostic), ("validation", validation)):
        (folder / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "source").mkdir()
    for relative in ("news/earnings_audit.py", "news/earnings_validation.py", "news/earnings.py", "strategy/engine.py", "tools/check_earnings_audit.py"):
        shutil.copy2(CODE_ROOT / relative, folder / "source" / relative.replace("/", "-"))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    names = [row["release_id"] for row in audits]
    matches = [sum(value == "matched" for key, value in row.get("checks", {}).items() if key != "non_gaap_eps") for row in audits]
    unverified = [2 - count for count in matches]
    axes[0].barh(names, matches, label="IR vs SEC matched")
    axes[0].barh(names, unverified, left=matches, label="Mismatch or unverified")
    axes[0].set_xlim(0, 2.1)
    axes[0].set_xticks([0, 1, 2])
    axes[0].set_title("GAAP EPS + revenue; non-GAAP excluded")
    axes[0].legend(fontsize=8)
    horizons = [1, 5, 20]
    axes[1].bar([position - .18 for position in range(3)], [(metrics[str(h)]["net_mean"] or 0) * 100 for h in horizons], width=.35, label="Net event mean")
    axes[1].bar([position + .18 for position in range(3)], [(metrics[str(h)]["spy_excess_mean"] or 0) * 100 for h in horizons], width=.35, label="Minus SPY same window")
    axes[1].set_xticks(range(3), [str(h) + " sessions" for h in horizons])
    axes[1].set_ylabel("Mean event return (%)")
    axes[1].set_title("Unconditional filing-date diagnostic\nNOT the earnings-surprise trading strategy")
    axes[1].axhline(0, color="gray", linewidth=.6)
    axes[1].legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(folder / "audit.png", dpi=150)
    plt.close(figure)

    lines = ["# 실적 원문 신뢰성·수익성 검증", "", "수치의 원문 일치와 예상 대비 호재·악재 및 매매 수익성을 분리해 검사했다.", "",
        "## 결론", "",
        f"- 관찰 30종목 SEC 회사 식별·원본 확보 결과: {validation['identity_counts']}.",
        f"- 대표 3기업·9발표의 매출/GAAP EPS 18항목: {validation['release_checks']}. 두 수치 모두 대조된 발표 {validation['fully_cross_checked_releases']}개.",
        "- 분기 EPS가 표준 SEC XBRL에 없으면 미검증으로 남겼다. 연간 EPS−누적 EPS, GAAP EPS와 조정 EPS의 혼합, 다른 회계 분기의 대체를 금지했다. 조정 EPS는 별도 비GAAP 조정표 대조를 마치지 않아 검증 완료로 올리지 않았다.",
        "- 회사 발표에는 시장 예상치가 없는 경우가 많다. 발표 전 예상치 원본 스냅샷과 당시 수신 이력이 확보되지 않아 기존 ‘예상 상회/하회+가격·거래량’ 전략의 수익성은 판정 불가다.",
        "- 그래서 원문·기간·통화·기준·발표 전 예상치의 증거를 통과하지 못한 제목 신호는 모의 매수·뉴스 매도에 사용하지 않도록 변경했다. 가격 손절·보유 관리와 수집은 계속한다.", "",
        "## 실제 원문 수치 대조", "", "매출은 IR의 0.1 billion 반올림 오차 ±0.05 billion을 허용한다. EPS는 ±0.005. 제출 당시 최초 분기 값을 사용하며 이후 변경 여부도 기록한다.", "",
        "|발표|분기 종료|IR 매출 USD bn|IR GAAP EPS|IR 조정 EPS|매출 대조|GAAP EPS 대조|원문|", "|---|---|---:|---:|---:|---|---|---|"]
    for row in audits:
        if "checks" not in row:
            lines.append(f"|{row['release_id']}|미검증||||||[IR]({row['url']})|")
            continue
        adjusted = "—" if row["ir_eps_non_gaap"] is None else str(row["ir_eps_non_gaap"])
        lines.append(f"|{row['release_id']}|{row['period_end']}|{row['ir_revenue']/1e9:.1f}|{row['ir_eps_gaap']}|{adjusted}|{row['checks']['revenue']}|{row['checks']['gaap_eps']}|[IR]({row['url']})|")
    lines += ["", "SEC 원본 API: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json 및 submissions. 각 종목의 공식 CIK·파일 해시는 identity.json, 개별 수치의 accn·기간·단위·제출일은 releases.json에 보존했다.",
        "", "## 제한된 발표 후 가격 진단", "",
        "실적 수치 두 개가 대조된 발표만 대상으로, IR 발표일·SEC 해당 분기 제출일 중 늦은 날짜가 지난 다음 거래일 시가에 무조건 매수한 사후 진단이다. 발표일 당일 시가에 샀다고 가정하지 않았다.",
        "이는 당시 시스템이 실제로 수신했다는 기록이 없는 가상 관찰자 가정이다. 호재·악재 분류, 당시 예상치·가이던스·5분봉 필터·공동 자금·손절을 재현한 전략이 아니다. 사건당 수익을 합산·복리화하지 않았다. 가격은 기존 KIS 실제 수정 일봉, 비용은 매수0.1%·매도0.2%·슬리피지 편도0.1%·스프레드0.1% 가정.",
        "", "|보유 길이|사건 수|평균 순수익|비용 두 배|SPY 대비 평균 차이|승률|", "|---|---:|---:|---:|---:|---:|"]
    fmt = lambda value: "—" if value is None else f"{value:.2%}"
    for horizon, row in metrics.items():
        lines.append(f"|{horizon}거래일|{row['events']}|{fmt(row['net_mean'])}|{fmt(row['stress_mean'])}|{fmt(row['spy_excess_mean'])}|{fmt(row['win_rate'])}|")
    lines += ["", "위 소수 사건의 평균을 프로그램 수익률이나 실적 전략의 수익성으로 해석하면 안 된다. 현재 3개 대형 기술주·최근 일부 발표에 한정되어 선택 편향과 표본 상관이 크다.",
        "", "## 남은 필수 증거", "",
        f"- 저장 시세 종료 {price_cutoff}까지 실제 시스템 수신 이력으로 연결 가능한 사건 {observable}건. 공식 문서를 오늘 조회한 것을 과거 수신 기록으로 소급하지 않았다.",
        "- 발표 전에 저장된 컨센서스의 실제/조정 EPS 기준, 통화, 회계기간, 제공자 URL·원본 해시·수신 시각. 발표 후 기사에서 인용한 예상치를 사전 스냅샷으로 간주하지 않는다.",
        "- 같은 발표의 정정·가이던스 변경을 원문과 연결하는 검증, 더 많은 기업·다른 기간·완료 거래 표본. 현재 검증 통과한 실적 매매 사건은 없다.",
        "- SEC/IR의 숫자가 일치한다는 것은 해당 발표 간 정합성 검사이며, 시장 예상치의 정확성·발표 당시 전달 지연·투자 수익을 보증하는 검사가 아니다.", "",
        "![원문 대조와 별도 사후 진단](audit.png)", "", f"원본·실행 보존 `{folder}`. 다운로드 원본 `{raw_folder}`.", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")
    destination = DATA_ROOT / "reports/earnings-audit"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("report.md", "audit.png", "validation.json", "identity.json", "releases.json", "diagnostic-events.json"):
        shutil.copy2(folder / name, destination / name)
    for parent in (destination, folder.parent):
        (parent / "latest.json").write_text(json.dumps({"folder": str(folder)}, indent=2), encoding="utf-8")
    print("Audit:", json.dumps(validation, ensure_ascii=False)[:1200], flush=True)
    print("보고서:", destination / "report.md", flush=True)
