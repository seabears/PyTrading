"""주문 식별의 불변 필드. 숫자 표현은 정상화하되 다른 주문을 같은 것으로 추정하지 않는다."""

from datetime import datetime
from decimal import Decimal


def broker_key(value):
    """숫자 ID의 선행 0만 제거한다. 날짜를 포함해 일자 간 번호 재사용을 구분한다."""
    if not isinstance(value, str) or not value:
        raise ValueError("order_identifier_missing")
    if ":" not in value:
        return value  # 내부 합성 어댑터의 불투명 ID. KIS는 아래 날짜/번호 필드를 추가 검사한다.
    day, number = value.split(":", 1)
    datetime.strptime(day, "%Y%m%d")
    if not number.isdecimal():
        raise ValueError("order_number_invalid")
    return day + ":" + str(int(number))


def context(state):
    """원장의 실행 모드와 비밀값을 노출하지 않는 계좌 지문을 반환한다."""
    fingerprint = state.get("broker_identity")
    if state["mode"] != "internal" and not fingerprint:
        raise ValueError("account_identity_unverified")
    return {
        "mode": state["mode"],
        "account_fingerprint": fingerprint or "internal:" + state["alias"],
        "limit_only": state["mode"] == "kis_demo",
    }


def validate_identity(order, event, state):
    """체결량을 적용하기 전에 원주문의 변경 불가 계약 필드를 모두 대조한다."""
    required = {
        "broker_id",
        "symbol",
        "side",
        "quantity",
        "price",
        "order_type",
        "original_broker_id",
        "order_day",
        "order_number",
        "account_fingerprint",
        "mode",
        "event_id",
        "filled",
        "notional",
        "status",
    }
    if not required <= event.keys():
        raise ValueError("order_fields_missing")
    if broker_key(order["broker_id"]) != broker_key(event["broker_id"]):
        raise ValueError("order_identifier_mismatch")
    expected = context(state)
    for field in ("mode", "account_fingerprint"):
        if event[field] != expected[field]:
            raise ValueError("account_or_mode_mismatch")
    if type(event["quantity"]) is not int:
        raise ValueError("order_quantity_type_invalid")
    if any(event[field] != order[field] for field in ("symbol", "side", "quantity")):
        raise ValueError("order_identity_mismatch")
    if event["order_type"] != order.get("order_type", "LIMIT") or Decimal(
        str(event["price"])
    ) != Decimal(order["price"]):
        raise ValueError("order_type_or_price_mismatch")
    if event["original_broker_id"] is not None:
        raise ValueError("unexpected_original_order_link")
    identifier = broker_key(event["broker_id"])
    if (
        ":" in identifier
        and broker_key(event["order_day"] + ":" + str(event["order_number"])) != identifier
    ):
        raise ValueError("order_date_or_number_mismatch")
    if state["mode"] != "internal" and ":" not in identifier:
        raise ValueError("dated_broker_identifier_required")
