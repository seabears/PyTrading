"""저장된 공급자 공개 응답을 비교하고 예상치 관측 스냅샷을 만든다. 키·운용 계좌는 변경하지 않는다."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from paths import DATA_ROOT, RESULTS_ROOT, CODE_ROOT
from news.consensus import alpha_calendar, alpha_observations
from news.earnings_validation import quarter_facts


def main():
    probe = Path(json.loads((DATA_ROOT / "consensus-probe/latest.json").read_text(encoding="utf-8"))["folder"]).resolve()
    if not probe.is_relative_to((DATA_ROOT / "consensus-probe").resolve()):
        raise ValueError("공급자 응답 경로가 데이터 폴더 밖입니다.")
    manifest = json.loads((probe / "manifest.json").read_text(encoding="utf-8"))
    # FMP는 사용하지 않는다. 기존 조사 원본은 보존하되 이번 검증에서는 읽지 않는다.
    allowed_sources = {"alpha-estimates", "alpha-history", "alpha-calendar"}
    manifest = [row for row in manifest if row["name"] in allowed_sources]
    sources = {row["name"]: row for row in manifest}
    estimates_metadata = sources["alpha-estimates"]
    def read_source(name):
        metadata = sources[name]
        path = Path(metadata["path"]).resolve()
        if not path.is_relative_to(probe):
            raise ValueError("공급자 원본 경로 오류")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != metadata["sha256"]:
            raise ValueError("공급자 원본 해시가 변경되었습니다.")
        return raw
    estimates = json.loads(read_source("alpha-estimates"))
    report = alpha_observations(estimates, estimates_metadata["received_at"], demo=True)
    calendar = alpha_calendar(read_source("alpha-calendar"))
    history = json.loads(read_source("alpha-history"))
    facts_path = DATA_ROOT / "earnings-audit/raw/IBM-companyfacts.json"
    comparisons = []
    if facts_path.exists():
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        as_of = estimates_metadata["received_at"][:10]
        for row in history.get("quarterlyEarnings", [])[:6]:
            official = quarter_facts(facts, "EarningsPerShareDiluted", "USD/shares", row["fiscalDateEnding"], as_of)
            vendor = float(row["reportedEPS"])
            comparisons.append({"period_end": row["fiscalDateEnding"], "provider_eps": vendor,
                "sec_gaap_eps": official.get("val"), "sec_status": official["status"],
                "same_number": abs(vendor - official["val"]) < .005 if official["status"] == "found" else None,
                "accounting_basis_verified": False, "differences_are_not_proof_of_vendor_error": True})
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder = RESULTS_ROOT / "consensus-sources" / run_id
    (folder / "source").mkdir(parents=True)
    snapshot = DATA_ROOT / "consensus-snapshots" / run_id
    (snapshot / "raw").mkdir(parents=True)
    for name in ("alpha-estimates", "alpha-history", "alpha-calendar"):
        metadata = sources[name]
        raw = read_source(name)
        (snapshot / "raw" / Path(metadata["path"]).name).write_bytes(raw)
    (snapshot / "observations.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (snapshot / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    future = [row for row in report["observations"] if row["future_period_candidate"]]
    result = {"source_probe_folder": str(probe), "observation_snapshot": str(snapshot),
        "received_at": estimates_metadata["received_at"], "observations": len(report["observations"]),
        "future_period_observations": len(future), "trading_eligible": 0, "calendar": calendar,
        "excluded_providers": ["fmp"], "ibm_eps_comparisons": comparisons,
        "production_provider_selected": False, "personal_key_tested": False,
        "initial_personal_key_probe_candidate": "alpha_vantage", "accounting_basis_approved": False,
        "live_strategy_changed": False, "paper_account_changed": False}
    (folder / "assessment.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for relative in ("news/consensus.py", "tools/check_consensus.py"):
        shutil.copy2(CODE_ROOT / relative, folder / "source" / relative.replace("/", "-"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    labels = ["Quarter metric observations", "Future-period candidates", "Trading-approved"]
    counts = [len(report["observations"]), len(future), 0]
    axes[0].bar(labels, counts, color=["steelblue", "orange", "gray"])
    for index, count in enumerate(counts):
        axes[0].text(index, count + .5, str(count), ha="center")
    axes[0].set_title("Actual IBM demo response: EPS + revenue")
    axes[0].set_ylabel("Metric observations (not companies or returns)")
    matched = [row for row in comparisons if row["sec_gaap_eps"] is not None]
    for index, row in enumerate(matched):
        axes[1].bar(index - .18, row["provider_eps"], width=.35, color="steelblue", label="Provider reported EPS, basis unspecified" if index == 0 else None)
        axes[1].bar(index + .18, row["sec_gaap_eps"], width=.35, color="orange", label="SEC GAAP diluted EPS" if index == 0 else None)
    axes[1].set_xticks(range(len(matched)), [row["period_end"] for row in matched], rotation=25, ha="right")
    axes[1].set_ylabel("Reported numeric values; not approved as comparable")
    axes[1].set_title("Accounting basis must be resolved before surprise")
    axes[1].legend(fontsize=7)
    for axis in axes:
        axis.grid(axis="y", alpha=.2)
    figure.tight_layout()
    figure.savefig(folder / "comparison.png", dpi=150)
    plt.close(figure)
    lines = ["# 예상치 데이터 제공원 실제 응답 점검", "", "공식 공개 데모·무인증 응답만 확인했다. 개인 계정의 권한·전체 30종목 품질·수익성은 검증하지 않았다.", "",
        "## 실제 확인 결과", "", "|제공원·기능|실제 응답|판정|", "|---|---|---|",
        f"|Alpha Vantage EARNINGS|HTTP {sources['alpha-history']['http_status']}, IBM 분기 보고 EPS·예상 EPS·surprise 필드|과거 실제 수신 이력이나 GAAP/조정 기준으로 간주하지 않음|",
        f"|Alpha Vantage EARNINGS_ESTIMATES|HTTP {sources['alpha-estimates']['http_status']}, EPS·매출 예상·분석가 수·수정 이력|독립 분기 지표 {len(report['observations'])}관측, 미래 기간 후보 {len(future)}관측, 매매 승인 0|",
        f"|Alpha Vantage EARNINGS_CALENDAR|HTTP {sources['alpha-calendar']['http_status']}, CSV 헤더·자료 {calendar['count']}건|발표 일정 없음으로 단정하지 않음|",
        "FMP는 사용자 요청으로 사용 대상에서 제외했다. 키 발급·연결·데이터 수집을 진행하지 않는다.", "",
        "수신 시각은 로컬에서 실제 응답을 받은 UTC로 저장했다. API date는 회계기간 종료일이며 수신 시각·발표 시각으로 바꾸지 않았다. '7일 전 예상치' 같은 현재 응답의 수정 이력을 과거에 수집한 스냅샷으로 만들지 않았다.",
        "", "## 회계 기준의 실제 차이", "",
        "공개 데모의 보고 EPS와 SEC GAAP EPS는 아래처럼 다를 수 있다. 공급자 기준이 명시되지 않아 같은 수치라고 전제하지 않았다. 차이를 공급자 오류로 단정하지도 않는다.", "",
        "|기간 종료|공급자 reported EPS|SEC GAAP EPS|숫자 일치|", "|---|---:|---:|---|"]
    for row in comparisons:
        lines.append(f"|{row['period_end']}|{row['provider_eps']}|{row['sec_gaap_eps']}|{row['same_number']}|")
    lines += ["", "## 제공원 검토 결론", "",
        "개인 키를 이용한 첫 연결 시험 후보는 Alpha Vantage다. 공개 데모에서 필요한 예상치 필드를 실제 확인했기 때문이다. 운영 제공원으로 확정하거나 회계 기준을 승인한 상태는 아니다.",
        "[Alpha Vantage 공식 지원 문서](https://www.alphavantage.co/support/)는 일반 무료 사용 한도를 하루 25회로 안내한다. 30종목을 하루 한 번씩 조회해도 이를 넘으므로 초기 시험은 소수 종목·발표 임박 대상으로 제한해야 한다. 개인 키에서 해당 엔드포인트의 실제 이용 권한도 확인해야 한다.",
        "과거 FMP 조사 자료는 이력으로만 보존하며 현재 검증 입력·스냅샷에는 포함하지 않는다.",
        "[Alpha Vantage 공식 문서](https://www.alphavantage.co/documentation/)의 공개 데모는 IBM 접근 예제다. 이를 현재 관찰 30종목의 완전한 최신 데이터나 생산 계정의 권한으로 주장하지 않는다.",
        "", "## 다음 수집 조건", "",
        "1. 개인 API 키로 소수 종목의 예상치·달력 권한을 확인한다. 키는 채팅·코드·보고서 대신 별도 인증 파일에서 읽도록 연결해야 한다.",
        "2. 회사·기간 시작/종료·통화·단위·GAAP/조정 EPS 기준·발표 예정 시각을 확인한다. 불명 값은 그대로 unknown으로 두고 매매 승인을 막는다.",
        "3. 발표 전에 원본 응답·실제 수신 UTC·SHA256을 매번 새 파일에 저장한다. 발표 후 IR/SEC의 같은 기준 실제 실적과 대조한다.",
        "4. 검증 완료 이후의 KIS 시세로 모의 매매를 재생한다. 현재 관측은 데모·회계 기준 불명 때문에 매매용 검증 목록에 넣지 않았다.", "",
        "## 현재 모의매매의 의미", "",
        "- 과거 백테스트: 저장된 실제 과거 시세를 재생한 가상 계좌 결과다.",
        "- 현재 프로그램의 실시간 모의매매: main.py를 계속 실행하면 실제 시세로 판단하고 가상 현금·보유·거래 기록을 바꾼다. 실제 주문 전송은 없다. 체결은 호가+고정 슬리피지·비용 가정이다.",
        "- 증권사 모의투자 서버: 주문을 모의 서버에 보내 접수·체결 응답을 다루는 별도 방식이다. 현재 프로그램은 이 경로에 연결된 상태가 아니다.",
        "지금까지 보고한 수익률은 과거 재생 결과이고, 최근 BUY/SELL 기능 검증은 합성 입력 테스트였다. 상시 실시간 운용 수익률을 검증한 기록은 아니다. 현재 실적 검증 통과 사건이 없어 실적 기반 신규 매수는 대기한다.",
        "", "![관측 자료·회계 기준 차이](comparison.png)", "",
        f"원본 수신 폴더: `{probe}`. 스냅샷 보존: `{snapshot}`. 결과 보존: `{folder}`.", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")
    destination = DATA_ROOT / "reports/consensus-sources"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("report.md", "comparison.png", "assessment.json"):
        shutil.copy2(folder / name, destination / name)
    for place in (folder.parent, destination):
        (place / "latest.json").write_text(json.dumps({"folder": str(folder)}, indent=2), encoding="utf-8")
    print("Observations:", len(report["observations"]), "future-period candidates:", len(future), "trading-approved: 0", flush=True)
    print("IBM EPS numeric comparisons:", json.dumps(comparisons, ensure_ascii=False), flush=True)
    print("보고서:", destination / "report.md", flush=True)
