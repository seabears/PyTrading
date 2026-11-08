"""기존 테스트 호출 호환. 계좌 서비스 상태를 합성하거나 미가입으로 인증하지 않는다."""
from trading.cash_service_policy import require_cash_only


def confirm_cash_only(manager, *, at=None, enabled=False):
    """구버전 테스트는 USD 전용 정책만 설정한다. 가입 상태는 입력받아도 사용하지 않는다."""
    manager.state.setdefault('broker_identity','synthetic-account-fingerprint')
    manager.state['requested_cash_service']='cash_only'
    return require_cash_only(manager)
