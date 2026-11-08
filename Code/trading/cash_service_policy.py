"""USD 보유 현금 범위 정책. 통합증거금 가입 상태를 조회하거나 승인 조건으로 쓰지 않는다.

2026-11-01 사용자 요청에 따라 가입/미가입 상태 검사를 제거했다.
unknown/cash_only는 구버전 설정 호환값이며 실제 계좌 상태를 뜻하지 않는다.
통합 여력을 선택하는 integrated 설정은 계속 거절한다. 현금·예약 금액 검사는
require_usd_funding에서 위험 원장의 계좌 연결 및 최신성 검사 이후 수행한다.
"""
from decimal import Decimal
from trading.risk_ledger import amount


def validate_service_setting(service):
    """서비스 가입 여부와 무관하게 통합 여력 필드 선택을 금지한다."""
    if service == "integrated":
        raise ValueError("integrated_margin_prohibited")
    if service not in {"unknown", "cash_only"}:
        raise ValueError("cash_service_setting_invalid")


def require_cash_only(manager, now=None):
    """구버전 호출 호환: 계좌 상태가 아닌 USD 전용 사용 정책만 검사한다.

    반환값은 정책 식별용이다. 미가입 확인 결과나 매수 승인 근거가 아니다.
    now는 구버전 호출 호환 인자이며 현금·위험 자료의 최신성 검사는 별도로 유지한다.
    """
    validate_service_setting(manager.state.get("requested_cash_service", "unknown"))
    return {"policy_version": "usd_cash_bound_v1", "funding_currency": "USD",
            "integrated_buying_power_allowed": False,
            "account_enrollment_status_required": False}


def require_usd_funding(manager, order):
    """현재 위험 원장 USD 현금에서 모든 매수 예약과 신규 주문 비용을 확보한다.

    API 여력에는 원격 예약을 다시 빼지 않는다. 이 검사는 별도의 보유 현금 상한이다.
    원격/로컬 예약을 현금 기준에서 한 번씩만 확보하며, 기존 비용 완충1.003을 유지한다.
    체결 후 비용 등이 미확정이면 기존 RiskLedger 검증이 먼저 차단한다.
    """
    require_cash_only(manager)
    from trading.risk_ledger import RiskLedger
    from trading.buying_power import ACTIVE_BUYS
    RiskLedger(manager).validate_snapshot(manager.state['account'])
    cash = amount(manager.state['risk_ledger']['last_evaluation']['cash_balance'])
    reserved = Decimal(0)
    for existing in manager.state['orders'].values():
        if existing['id'] == order['id'] or existing['side'] != 'BUY' or existing['status'] not in ACTIVE_BUYS:
            continue
        reserved += Decimal(existing['quantity']-existing.get('filled',0)) * amount(existing['price']) * Decimal('1.003')
    required = Decimal(order['quantity']-order.get('filled',0)) * amount(order['price']) * Decimal('1.003')
    if required + reserved > cash:
        raise ValueError('usd_cash_funding_limit_exceeded')
    return {'cash_basis_usd': str(cash), 'reserved_usd': str(reserved),
            'required_usd': str(required), 'account_status_checked': False}
