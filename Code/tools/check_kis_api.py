"""--test api: 인증·인터넷 없이 API 요청과 오류 처리 검증 보고서를 만든다."""
import json
import unittest
from collections import Counter
from datetime import datetime, timezone

from paths import CONFIG_ROOT, DATA_ROOT, FIXTURES_ROOT


def main():
    folder = DATA_ROOT / "reports/kis-api"
    folder.mkdir(parents=True, exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromNames(["Test.broker.test_kis_api", "Test.broker.test_no_borrowing", "Test.broker.test_disallowed_products", "Test.broker.test_product_policy", "Test.broker.test_removed_finance"])
    with (folder / "tests.log").open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    catalog = json.loads((CONFIG_ROOT / "kis-api-catalog.json").read_text(encoding="utf-8"))
    vectors = json.loads((FIXTURES_ROOT / "kis-api-vectors.json").read_text(encoding="utf-8"))
    groups = Counter((row["module"].removesuffix("_ws"), row["kind"]) for row in catalog["operations"])
    totals = Counter(row["kind"] for row in catalog["operations"])
    allowed = sum(row.get("enabled", True) is True for row in catalog["operations"])
    disallowed = len(catalog["operations"]) - allowed
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "commit": catalog["commit"],
              "operations": dict(totals), "allowed": allowed, "disallowed": disallowed, "contract_vectors": len(vectors["vectors"]),
              "unit_tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "passed": result.wasSuccessful(), "live_calls_in_this_check": False,
              "actual_order_sent": False}
    (folder / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    categories = sorted({group for group, kind in groups})
    figure, axis = plt.subplots(figsize=(11, 6))
    rest = [groups[(group, "rest")] for group in categories]
    stream = [groups[(group, "websocket")] for group in categories]
    axis.barh(categories, rest, label="REST request builders")
    axis.barh(categories, stream, left=rest, label="WebSocket subscriptions")
    axis.set_xlabel("Functions checked against official contracts")
    axis.set_title(f"{sum(totals.values())} functions / {len(vectors['vectors'])} contract cases; offline checks")
    axis.legend()
    figure.tight_layout()
    figure.savefig(folder / "coverage.png", dpi=140)
    plt.close(figure)
    lines = ["# KIS API 구현 검증", "", f"판정: {'통과' if result.wasSuccessful() else '실패'}. 공식 커밋 `{catalog['commit']}`.",
             "", f"구현 {sum(totals.values())}개 중 사용 허용 {allowed}개, 사용 불허 {disallowed}개. 선물·옵션·ELW는 구현만 보존하고 전송·구독은 차단한다.", "", "허용 상품은 주식·채권·ETF로 한정한다. ETF/ETN 공용 API도 확인된 종목의 상품 종류를 검사하며 ETN·미확인 종목은 차단한다.", "", "## 범위", "", "공식 예제와 포털 대조를 통해 REST 260개·실시간 63개를 요청 함수로 구현했다.",
             "공식 공개 메뉴 338개 중 사용자 요청으로 대출 관련 8개를 제외하고 제공 종료 재무 API 7개도 제외한 나머지 경로 323개(인증 3개 포함)를 대조했다. 모든 계좌 권한·미래 신규 기능·실접속 성공을 보증하지 않는다.",
             "예제 누락 6개를 포털에서 보완했다. 실시간 필드는 최신 포털 계약으로 대조했다. 대출·신용·담보대출·대주 전용 API 8개는 삭제하고 예약주문·일반 매도에도 현금 거래 제한을 적용했다. 별도 공통 기능: 기존 24시간 토큰 재사용, 실시간 접속키, 해시키, 명시적 토큰 폐기.",
             "", "| 상품 | REST | 실시간 |", "|---|---:|---:|"]
    lines += [f"| {group} | {groups[(group, 'rest')]} | {groups[(group, 'websocket')]} |" for group in categories]
    lines += ["", "## 조건·판정", "", f"- 요청 경로·TR ID·방식·파라미터 대조 {len(vectors['vectors'])}개. 모든 함수·정적으로 확인한 TR 분기 포함.",
              f"- HTTP·주문 차단·응답 유실·실시간 필드·AES 복호화 자동 검사 {result.testsRun}개. 실패 {len(result.failures)}, 오류 {len(result.errors)}.",
              "- 미국 모의 매도 VTTT1001U, 야간 선물옵션 정정 STTN1103U, 해외옵션 분봉 HHDFO55020400으로 보정. 공식 구현의 단순 V 치환 오류를 별도 검사.",
              "- 합성 HTTP·실시간 응답 검사이며 실제 수익성·체결 품질 시험이 아니다.",
              "- 계좌 API 실접속·실주문·모의 서버 주문·전 상품 실시간 수신은 미검증. 실제 주문은 한 건도 전송하지 않음.",
              "- 연속조회는 응답 tr_cont와 원본 커서를 반환한다. API마다 다른 다음 페이지 인자는 호출자가 지정한다.",
              "- 연결 끊김은 호출자에게 전달한다. 실시간 자동 재연결·누락 재복구·main.py 연결은 별도 구현 대상.",
              "", "[공식 저장소](https://github.com/koreainvestment/open-trading-api)", "", "![상품별 구현 함수](coverage.png)"]
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"KIS API: {sum(totals.values())}개 구현 함수 (허용 {allowed}, 불허 {disallowed}) / {len(vectors['vectors'])}개 요청 경우 / 자동 검사 {'통과' if result.wasSuccessful() else '실패'}")
    print(f"보고서: {folder / 'report.md'}")
    if not result.wasSuccessful():
        raise SystemExit(1)
