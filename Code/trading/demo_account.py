"""모의 초기 기준·주문 여력·미확정 비용을 구분한다.

사용자가 확인한 초기금은 감사용 기준이다. 현재 현금 또는 위험 승인으로
자동 전환하지 않는다. USD 금액은 기존 위험 원장의 6자리 Decimal을 사용한다.
"""
import copy
from datetime import datetime, timezone

from trading.risk_ledger import amount, digest


def select_buying_power(capacity, service="unknown", *, manager=None):
    """USD 외화 주문가능액だけを選ぶ。가입 상태나 현금 잔액을 인증하지 않는다."""
    from trading.cash_service_policy import validate_service_setting
    validate_service_setting(service)
    output = capacity["output"]
    if output.get("tr_crcy_cd") != "USD":
        raise ValueError("unsupported_currency")
    field = "ovrs_ord_psbl_amt"
    if output.get(field) in {None, ""}:
        raise ValueError("selected_buying_power_field_missing")
    return {"service": "cash_only", "field": field, "amount": str(amount(output[field])),
            "selection_confirmed": True, "currency": "USD",
            "account_enrollment_status_checked": False,
            "cash_is_order_capacity_not_actual_usd_balance": True}


def record_initial_reference(manager, reference):
    """계좌 지문과 사용자 확인값을 묶어 보존한다. 과거 이력·현재 현금을 인증하지 않는다."""
    if manager.state["mode"] != "kis_demo" or not manager.state.get("broker_identity"):
        raise ValueError("reference_requires_bound_demo_account")
    if set(reference) != {"currency", "amount", "source", "confirmed_on"}:
        raise ValueError("initial_reference_schema_invalid")
    if (reference["currency"] != "USD" or reference["source"] != "user_confirmation"
            or amount(reference["amount"]) <= 0):
        raise ValueError("initial_reference_invalid")
    from datetime import date
    date.fromisoformat(reference["confirmed_on"])
    value = {**reference, "amount": str(amount(reference["amount"])),
             "account_fingerprint": manager.state["broker_identity"], "mode": "kis_demo",
             "scope": "initial_virtual_cash_reference_not_current_cash_or_risk_approval"}
    previous = manager.state.get("initial_capital_reference")
    if previous and previous != value:
        raise ValueError("initial_reference_change_requires_review")
    manager.state["initial_capital_reference"] = value
    manager._save()
    return copy.deepcopy(value)


def observe_settlement(manager, remote_orders, inventory, *, observed_at, source_hashes):
    """누적 체결은 관측 사실로 저장하고, 확정 비용·체결시각을 만들어내지 않는다.

    OrderManager의 전체 계약 대조가 끝난 뒤만 호출한다. 같은 주문의 누적값은
    덮어쓰므로 중복 통보가 비용·체결 수를 더하지 않는다. 실제 비용 정산 전에는
    실현손익·순손익을 None으로 둔다.
    """
    from strategy.engine import parse_timestamp
    from trading.execution_observation import observe_execution
    observe_execution(manager, remote_orders, inventory, observed_at=observed_at,
                      complete=True, source_hashes=source_hashes)
    before = copy.deepcopy(manager.state)
    try:
        settlement = manager.state.setdefault("demo_settlement", {"schema": 1, "orders": {}})
        for row in remote_orders:
            if not row["filled"]:
                continue
            key = row["broker_id"]
            value = {"quantity": row["filled"], "notional_usd": str(amount(row["notional"])),
                     "symbol": row["symbol"], "side": row["side"], "observed_at": observed_at,
                     "execution_at": None, "individual_execution_ids": None,
                     "final_costs_usd": None, "cost_state": "PENDING_EVIDENCE",
                     "source_hashes": dict(source_hashes)}
            old = settlement["orders"].get(key, {})
            # 재조회는 확정 비용을 취소하지 않는다. 추가 체결은 새 비용 정산을 요구한다.
            if (old.get("cost_state") == "CONFIRMED" and old.get("final_costs_usd") is not None
                    and old.get("quantity") == value["quantity"]
                    and amount(old["notional_usd"]) == amount(value["notional_usd"])):
                value.update(final_costs_usd=old["final_costs_usd"], cost_state="CONFIRMED",
                             cost_source=copy.deepcopy(old.get("cost_source")))
            settlement["orders"][key] = value
        complete = all(row.get("final_costs_usd") is not None for row in settlement["orders"].values())
        settlement.update(last_observed_at=observed_at, account_fingerprint=manager.state["broker_identity"],
                          net_realized_pnl_usd=None, final_costs_complete=complete,
                          reconciliation_required=not complete)
        manager._save()
        return copy.deepcopy(settlement)
    except Exception:
        manager.state = before
        manager.ready = False
        manager._execution_observation_valid = False
        raise
