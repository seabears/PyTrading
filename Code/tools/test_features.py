"""main.py --test의 기능 선택과 실행. 실제 연결 확인은 메뉴에서 명확하게 구분한다."""
import unittest

FEATURE_TESTS = {
    "universe": ["Test.app.test_universe", "Test.app.test_watchlist_tui"],
    "entry-timing": ["Test.research.test_entry_timing"],
    "industry-peers": ["Test.research.test_industry_study"],
    "refinements": ["Test.research.test_algorithm_refinements"],
    "algorithms": ["Test.research.test_algorithm_study"],
    "engine-backtest": ["Test.research.test_engine_backtest"],
    "api": ["Test.broker.test_kis_api", "Test.broker.test_no_borrowing", "Test.broker.test_disallowed_products", "Test.broker.test_product_policy"],
    "technical": ["Test.research.test_technical"],
    "news": ["Test.news.test_collector", "Test.news.test_review", "Test.news.test_filtering"],
    "broker": ["Test.broker.test_toss", "Test.broker.test_spec", "Test.broker.test_kis"],
    "strategy": ["Test.strategy.test_engine", "Test.strategy.test_exits"],
    "paper": ["Test.trading.test_paper"],
    "settings": ["Test.app.test_runtime"],
    "runner": ["Test.app.test_runner", "Test.tools.test_checks", "Test.app.test_entrypoint", "Test.tools.test_functions"],
    "research": ["Test.research.test_kis_history", "Test.research.test_backtest", "Test.research.test_daily", "Test.research.test_indicators", "Test.research.test_peers", "Test.research.test_diagnostics", "Test.research.test_portfolio", "Test.research.test_long_history"],
}
FEATURE_TESTS["earnings"] = ["Test.news.test_earnings", "Test.news.test_earnings_validation"]
FEATURE_TESTS["safety"] = ["Test.trading.test_safety"]
FEATURE_TESTS["consensus"] = ["Test.news.test_consensus"]
FEATURE_TESTS["runner"].append("Test.tools.test_price_research")
FEATURE_TESTS["research"].append("Test.research.test_fixed_trend")
FEATURE_TESTS["operations"] = ["Test.app.test_audit_logs", "Test.app.test_regular_verifier", "Test.app.test_quote_recovery", "Test.trading.test_review_edges", "Test.trading.test_review_regressions", "Test.app.test_operations", "Test.trading.test_daily_internal_risk", "Test.broker.test_execution_guard"]
FEATURE_TESTS['readiness'] = ['Test.trading.test_demo_account', 'Test.trading.test_demo_runner', 'Test.broker.test_trial_api', 'Test.broker.test_trial_integration', 'Test.broker.test_demo_session_cli', 'Test.trading.test_demo_session', 'Test.trading.test_demo_readiness', 'Test.trading.test_risk_ledger', 'Test.trading.test_order_backup',
    'Test.broker.test_demo_http_audit', 'Test.trading.test_risk_sources', 'Test.trading.test_readiness_edges', 'Test.broker.test_kis_readonly']
FEATURE_TESTS["api"].extend(["Test.broker.test_removed_finance", "Test.broker.test_prohibited_policy"])
FEATURE_TESTS["readiness"].extend(["Test.trading.test_demo_balance", "Test.trading.test_user_cash", "Test.trading.test_buying_power", "Test.trading.test_demo_cash_review", "Test.trading.test_demo_risk_assessment", "Test.trading.test_demo_accounting_cycle", "Test.trading.test_demo_user_basis", "Test.trading.test_demo_day_gate"])
FEATURE_TESTS["readiness"].extend(["Test.trading.test_adoption_requests","Test.trading.test_strategy_adoption","Test.trading.test_execution_modes","Test.trading.test_strategy_model_basis","Test.trading.test_strategy_posttrade","Test.trading.test_execution_review_three","Test.trading.test_broker_diagnostics"])
FUNCTION_LABELS = {
    "news": "뉴스 수집·후보 분류 실행 (실제 인터넷 뉴스)",
    "broker": "선택 증권사 시세 조회 실행 (인증 파일·인터넷 사용)",
    "strategy": "매매 판단 실행 (합성 시세, 조건·계산값 표시)",
    "paper": "모의 계좌 실행 (합성 체결, 현금·보유·복원 표시)",
    "settings": "설정 로드 실행 (적용값·경로 표시, 인증값은 읽지 않음)",
    "runner": "전체 연결 한 번 실행 (실제 시세·뉴스, 별도 모의 계좌)",
    "backtest": "과거 시세 모의매매·규칙 비교 (실제 분봉, 연구 전용)",
    "research": "수정 방향 3개 반복 비교 (별도 3년 일봉, 연구 전용)",
    "indicators": "경제·시장 지표 비교 (코스피·SPY·VIX·국채, 연구 전용)",
    "peers": "사업군 비교 (설정 종목·상장일 검사, 고정 규칙)",
    "diagnostics": "진입 차단·손실 거래·7개 조건 효과 분석 (연구 전용)",
    "portfolio": "공동 자금·48개 회전 가설·고정 후보의 이후 기간 시험",
    "adaptive": "과거 자료로만 순차 규칙 선택·다음 기간 모의 평가",
    "adaptive-robust": "비용 두 배·단순 보유 초과를 요구하는 순차 선택",
    "defensive": "시장 추세 약화 시 실제 인버스 ETF·현금 모의 비교",
    "long-history": "2020년부터 기간 확장·같은 규칙·연도별 수익 평가",
    "exits": "원가·이익 보호 매도 조건 비교 (저장된 장기 실제 일봉)",
    "strategies": "VWAP·거래량 / MA·모멘텀 비교 (저장 자료, 연구 전용)",
}
FUNCTION_LABELS["industry-peers"] = "8산업군·동종 기업 개별 고정 규칙 비교 (저장 일봉)"
FUNCTION_LABELS["industry-continuous"] = "동종 기업 기준 규칙을 2020년부터 연속 재생 (저장 자료)"
FUNCTION_LABELS["industry-history"] = "동종 기업 KIS 일봉 새 스냅샷 수집 (기존 시세 보존)"
FUNCTION_LABELS["refinements"] = "한 항목씩 조정·주변 설정 안정성 비교 (저장 일봉, 기록 보존)"
FUNCTION_LABELS["algorithms"] = "12개 일봉 알고리즘·기간 분리·비용 비교와 연구 기록 (저장 자료)"
FUNCTION_LABELS["engine-backtest"] = "현재 운용 엔진 그대로 30종목 공동 계좌 재생 (저장 KIS 분봉)"
FUNCTION_LABELS["history"] = "현재 30종목 KIS 시세 새 수집 (검증 후 기존 시세 교체)"
FUNCTION_LABELS["api"] = "KIS 전체 API 구현 검사 (합성 입력, 인증·주문 없음)"
FUNCTION_LABELS["api-live"] = "KIS 실제 연결 확인 (AAPL 시세·실시간 호가, 주문 없음)"
FUNCTION_LABELS["entry-timing"] = "일봉·장중 매수 시점 비교 (저장 자료, 사건 손익·미체결)"
FUNCTION_LABELS["earnings"] = "실적 뉴스·호재/악재 모의 매매 실행 (합성 입력)"
FUNCTION_LABELS["earnings-live"] = "실적 뉴스 실제 수집 확인 (증권사 인증·주문 없음)"
FUNCTION_LABELS["earnings-audit"] = "SEC·IR 원문 대조와 발표 후 가격 진단 (저장 원본)"
FUNCTION_LABELS["safety"] = "일일 손실·위험 예산·긴급 중지 안전장치 실행 (합성 입력)"
FUNCTION_LABELS["consensus"] = "예상치 공급자 실제 응답·회계 기준 점검 (저장 공개 데모)"
FUNCTION_LABELS["price-research"] = "별도 가격·거래량 설정·30종목·비용·기간 비교 (저장 분봉)"
FUNCTION_LABELS["price-forward-check"] = "별도 가격 연구 실시간 1회 확인 (KIS 인증·시세, 실제 주문 없음)"
FUNCTION_LABELS["fixed-trend-data"] = "고정 일봉 후보용 KIS 새 일봉 수집 (기존 자료 보존)"
FUNCTION_LABELS["fixed-trend"] = "고정 일봉 후보·기존 단기·현금·SPY 비교와 모의 기록 점검"
FUNCTION_LABELS["operations-live"] = "실제 KIS 1회 주기·지연 측정 (별도 관측 계좌, 실제 주문 없음)"
FUNCTION_LABELS["quote-latency"] = "실제 KIS 호가 HTTP 지연 진단 (장중·체결 성능 아님)"
FUNCTION_LABELS["daily-live"] = "고정 일봉 실제 시세 내부 모의 1회 (실제 주문 없음)"
TEST_CHOICES = ["menu", "all", *FUNCTION_LABELS, "unit",
                *("unit-" + feature for feature in FEATURE_TESTS),
                "news-live", "broker-live", "replay"]
FEATURE_LABELS = {
    "universe": "사용자 지정·일별 자동 추가/제외·보유 관리·읽기 전용 검색",
    "operations": "저장 장애·복구·운영 감시·일봉 계획·주문 원장 장애",
    "entry-timing": "진입 정보 시점·비용·미체결·관측 창·분봉 준비",
    "industry-peers": "공식 종목 확인·상품 차단·산업군 비교·신규 표본",
    "refinements": "전략 기간 조정·기본값 보존·미래 정보 차단·선정 경계",
    "algorithms": "알고리즘 인과성·공동 자금·갭 손절·선정 분리",
    "engine-backtest": "운용 엔진 일치·미래 정보 차단·공동 자금·비용",
    "api": "KIS 전체 상품 API 요청·HTTP·실시간 프레임",
    "technical": "VWAP·MA·ATR·시장 국면·비용 포함 재생",
    "news": "뉴스 수집 형식·분류·검토 등록",
    "broker": "토스 인증 형식·시세·거래 시간",
    "strategy": "매수·매도 판단 규칙",
    "paper": "모의 계좌·비용·보유·복원",
    "settings": "설정 파일·동시 실행 잠금",
    "runner": "지속 실행·재시도·종료·재생",
    "research": "과거 시세·다음 봉 체결·비용·검증 기간 분리",
}


FEATURE_LABELS["earnings"] = "실적 뉴스 분류·시각·중복·비용·모의 매매 연결"


FEATURE_LABELS["safety"] = "매수 제한·매도 유지·재시작·저장 실패·계좌 검산"


FEATURE_LABELS["consensus"] = "예상치 기간·기준·수신 시각·불명 값·데모 매매 차단"


FEATURE_LABELS['readiness'] = '근거 기반 위험 원장·주문 백업/복구·조회 전용 모의계좌 사전 검사'


def run_tests(feature: str) -> int:
    """기능별 모듈을 명시한다. 테스트 하나가 다른 테스트를 가져오지 않는다."""
    modules = [module for names in FEATURE_TESTS.values() for module in names] if feature == "all" else FEATURE_TESTS[feature]
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    from unittest.mock import patch
    with patch("socket.socket.connect", side_effect=AssertionError("자동 검증에서 실제 네트워크 연결 금지")):
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def run_feature(feature: str) -> int:
    """기능 이름은 직접 실행, unit-접두사는 예상 결과와 비교하는 자동 검증이다."""
    if feature == "all":
        return run_tests("all")
    if feature == "unit":
        selected = select_unit_test()
        return run_feature(selected) if selected is not None else 0
    if feature.startswith("unit-"):
        return run_tests(feature.removeprefix("unit-"))
    # 이전 직접 연결·재생 이름은 같은 기능으로 연결한다.
    feature = {"news-live": "news", "broker-live": "broker", "replay": "paper"}.get(feature, feature)
    if feature == "daily-live":
        from app.daily_service import run
        check = lambda: run(watch=False)
    elif feature == "quote-latency":
        from tools.quote_latency import main as check
    elif feature == "operations-live":
        from tools.measure_operations import main as check
    elif feature == "fixed-trend":
        from tools.fixed_trend_study import main as check
    elif feature == "fixed-trend-data":
        from tools.collect_fixed_study import main as check
    elif feature == "price-forward-check":
        from tools.price_forward import main as run
        check = lambda: run(watch=False)
    elif feature == "price-research":
        from tools.price_research import main as check
    elif feature == "consensus":
        from tools.check_consensus import main as check
    elif feature == "safety":
        from tools.check_safety import main as check
    elif feature == "earnings":
        from tools.check_earnings import main as check
    elif feature == "earnings-audit":
        from tools.check_earnings_audit import main as check
    elif feature == "earnings-live":
        from tools.check_earnings import live as check
    elif feature == "entry-timing":
        from tools.run_entry_timing import main as check
    elif feature == "industry-continuous":
        from tools.run_industry_continuous import main as check
    elif feature == "industry-peers":
        from tools.run_industry_study import main as check
    elif feature == "industry-history":
        from tools.collect_industry_history import main as check
    elif feature == "refinements":
        from tools.run_algorithm_refinements import main as check
    elif feature == "algorithms":
        from tools.run_algorithm_study import main as check
    elif feature == "engine-backtest":
        from tools.research_engine_backtest import main as check
    elif feature == "api-live":
        from tools.check_kis_api_live import main as check
    elif feature == "api":
        from tools.check_kis_api import main as check
    elif feature == "history":
        from tools.collect_kis_history import main as check
    elif feature == "news":
        from tools.check_news import main as check
    elif feature == "broker":
        from tools.check_broker import main as check
    elif feature == "strategy":
        from tools.check_strategy import main as check
    elif feature == "paper":
        from tools.replay_demo import main as check
    elif feature == "settings":
        from tools.show_settings import main as check
    elif feature == "runner":
        from tools.run_once import main as check
    elif feature == "backtest":
        from tools.check_backtest import main as check
    elif feature == "research":
        from tools.research_cycles import main as check
    elif feature == "indicators":
        from tools.research_indicators import main as check
    elif feature == "peers":
        from tools.research_peers import main as check
    elif feature == "diagnostics":
        from tools.analyze_conditions import main as check
    elif feature == "portfolio":
        from tools.research_portfolio import main as check
    elif feature == "adaptive":
        from tools.research_walk_forward import main as check
    elif feature == "adaptive-robust":
        from tools.research_walk_forward import main
        check = lambda: main(strict_selection=True)
    elif feature == "defensive":
        from tools.research_defensive import main as check
    elif feature == "long-history":
        from tools.research_long_history import main as check
    elif feature == "strategies":
        from tools.research_technical import main as check
    elif feature == "exits":
        from tools.research_exits import main as check
    else:
        raise ValueError("지원하지 않는 테스트 기능입니다.")
    from broker.diagnostic import diagnostic_scope
    try:
        # --test 기능 실행은 실제 모드 설정과 무관하게 증권사 변경 요청을 금지한다.
        # unit/all의 합성 전송 검사는 위에서 반환하므로 이 범위와 섞이지 않는다.
        with diagnostic_scope():
            check()
    except SystemExit as result:
        return result.code or 0
    return 0


def select_feature():
    """--test만 입력하면 번호로 기능을 고른다. 취소는 None을 반환한다."""
    choices = ["all", *FUNCTION_LABELS, "unit"]
    print("실행해 볼 기능을 선택하세요. 모든 실행에서 실제 주문을 제출하지 않습니다.")
    print("0: 전체 자동 검증 (인터넷·실제 인증키 사용 안 함)")
    for number, feature in enumerate(FUNCTION_LABELS, 1):
        print(f"{number}: {FUNCTION_LABELS[feature]}")
    print(f"{len(FUNCTION_LABELS) + 1}: 기능별 자동 검증 선택")
    return read_menu_choice(choices)


def select_unit_test():
    print("자동 검증할 기능을 선택하세요. 인터넷·실제 인증키를 사용하지 않습니다.")
    print("0: 전체 자동 검증")
    for number, feature in enumerate(FEATURE_TESTS, 1):
        print(f"{number}: {FEATURE_LABELS[feature]}")
    return read_menu_choice(["all", *("unit-" + feature for feature in FEATURE_TESTS)])


def read_menu_choice(choices):
    """두 메뉴가 같은 입력 처리 규칙을 사용한다."""
    try:
        answer = input("실행할 번호: ").strip()
        if answer.isdigit() and 0 <= int(answer) < len(choices):
            return choices[int(answer)]
        print("표시된 번호를 입력하세요.")
        raise SystemExit(1)
    except (EOFError, KeyboardInterrupt):
        print("\n테스트 선택을 종료했습니다.")
        return None
