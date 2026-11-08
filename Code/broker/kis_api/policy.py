"""사용자 고정 방침: 대출·신용융자·담보대출·대주 기능은 제공하거나 전송하지 않는다.

계좌의 현금 잔고·일반 증거금 조회와 시장 시세 기능은 유지한다.
카탈로그를 예전 버전으로 되돌려도 전용 대출 경로는 이 검사에서 차단한다.
"""
from broker.kis import KisApiError

REMOVED_OPERATIONS = frozenset({
    "domestic_stock.credit_balance", "domestic_stock.credit_by_company",
    "domestic_stock.daily_credit_balance", "domestic_stock.daily_loan_trans",
    "domestic_stock.inquire_credit_psamount", "domestic_stock.lendable_by_company",
    "domestic_stock.order_credit", "overseas_stock.colable_by_company",
})

REMOVED_PATHS = frozenset({
    "/uapi/domestic-stock/v1/ranking/credit-balance",
    "/uapi/domestic-stock/v1/quotations/credit-by-company",
    "/uapi/domestic-stock/v1/quotations/daily-credit-balance",
    "/uapi/domestic-stock/v1/quotations/daily-loan-trans",
    "/uapi/domestic-stock/v1/trading/inquire-credit-psamount",
    "/uapi/domestic-stock/v1/quotations/lendable-by-company",
    "/uapi/domestic-stock/v1/trading/order-credit",
    "/uapi/overseas-price/v1/quotations/colable-by-company",
})


def validate_no_borrowing(name, path, parameters):
    """요청 생성 시점과 전송 직전에 검사한다. 주문 허용 옵션과 무관하게 적용한다."""
    if name in REMOVED_OPERATIONS or path in REMOVED_PATHS:
        raise KisApiError("대출·신용·담보대출·대주 API는 삭제되어 사용할 수 없습니다.")
    if not isinstance(parameters, dict):
        raise ValueError("KIS 요청 파라미터는 객체여야 합니다.")
    for key, value in parameters.items():
        normalized = str(key).upper()
        if normalized.startswith(("LOAN_", "CRDT_")) or normalized == "LDNG_DT":
            if str(value).strip():
                raise KisApiError("대출·신용 관련 입력값은 사용할 수 없습니다.")
    if "ORD_OBJT_CBLC_DVSN_CD" in parameters and str(parameters["ORD_OBJT_CBLC_DVSN_CD"]) != "10":
        raise KisApiError("예약주문 잔고 구분은 현금(10)만 허용합니다.")
    if path in {"/uapi/domestic-stock/v1/trading/order-resv", "/uapi/domestic-stock/v1/trading/order-resv-rvsecncl"}:
        if str(parameters.get("ORD_OBJT_CBLC_DVSN_CD", "")) != "10":
            raise KisApiError("예약주문은 현금 잔고 구분(10)을 명시해야 합니다.")
    if "SLL_TYPE" in parameters:
        allowed = {"", "00"} if path.startswith("/uapi/overseas-stock/") else {"", "01"}
        if str(parameters["SLL_TYPE"]) not in allowed:
            raise KisApiError("일반 매도만 허용합니다. 대차매도는 사용할 수 없습니다.")
