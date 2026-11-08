"""진단 실행에만 적용하는 증권사 주문 금지 범위. 인증·시세 조회는 유지한다.

전역 설정 파일을 바꾸지 않는다. 중첩 실행과 예외 종료 뒤에는 호출 전 상태로
돌아간다. 모드 선택과 별개로 금융 전송 경계에서도 이 범위를 검사한다.
"""
from contextlib import contextmanager
from contextvars import ContextVar

_diagnostic_active = ContextVar('pytrading_diagnostic_active', default=False)


def diagnostic_active():
    return _diagnostic_active.get()


@contextmanager
def diagnostic_scope():
    """이 호출 흐름의 전략 체결을 내부 모의로 한정하고 증권사 주문을 금지한다."""
    token = _diagnostic_active.set(True)
    try:
        yield
    finally:
        _diagnostic_active.reset(token)


def require_broker_orders_allowed():
    """HTTP 전송 전 실패로 분류한다. 모의·실계좌 주문/정정/취소 모두 금지한다."""
    if diagnostic_active():
        from broker.kis_api.client import KisPreflightError
        raise KisPreflightError('diagnostic_broker_order_transmission_prohibited')
