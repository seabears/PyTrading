"""위험 승인과 분리한 주문·수량 관측 및 보유 축소 검사.

새 매수는 RiskLedger를 계속 요구한다. 비용 미확정으로 매수가 중단돼도
계좌·전체 주문·매도가능 수량이 확인된 보유의 축소·취소는 별도로 관리한다.
"""
import copy
from datetime import datetime, timezone

from strategy.engine import parse_timestamp
from trading.orders import ACTIVE, money


def observe_execution(manager, events, inventory, *, observed_at, complete, source_hashes):
    """전체 계약 대조 후 주문 상태만 원자적으로 갱신한다. 현금/PnL·ready는 승인하지 않는다."""
    manager.ready = False
    manager._execution_observation_valid = False
    before = copy.deepcopy(manager.state)
    manager._cancel_verified = {}
    try:
        if not complete or not source_hashes or not manager.state.get("broker_identity"):
            raise ValueError("execution_observation_incomplete")
        age = (datetime.now(timezone.utc) - parse_timestamp(observed_at)).total_seconds()
        if not 0 <= age <= 30:
            raise ValueError("execution_observation_stale")
        if any(not isinstance(value, str) or len(value) != 64
               or any(letter not in "0123456789abcdef" for letter in value)
               for value in source_hashes.values()):
            raise ValueError("execution_observation_source_hash_invalid")
        verified, errors = manager._verified_events(events)
        if errors:
            raise ValueError("execution_observation_contract_mismatch")
        found = {order["id"] for order, event in verified.values()}
        if any(order["status"] in ACTIVE - {"INTENT"} and order["id"] not in found
               for order in manager.state["orders"].values()):
            raise ValueError("execution_observation_remote_order_missing")
        required = {"positions", "sellable", "broker_reserved_ids", "remote_reserved_sell", "position_costs"}
        if not required <= inventory.keys():
            raise ValueError("execution_observation_inventory_incomplete")
        for symbol, quantity in inventory["positions"].items():
            available = inventory["sellable"].get(symbol)
            if type(quantity) is not int or type(available) is not int or not 0 <= available <= quantity:
                raise ValueError("execution_observation_inventory_invalid")
            if quantity - available != inventory["remote_reserved_sell"].get(symbol, 0):
                raise ValueError("execution_observation_reservation_mismatch")
        for old, event in verified.values():
            manager.update(old["id"], **{key: event[key] for key in
                           ("event_id", "filled", "notional", "status")}, persist=False, update_account=False)
        expected = dict(manager.state.get("risk_ledger", {}).get("baseline", {}).get("positions", {}))
        for order in manager.state["orders"].values():
            symbol = order["symbol"]
            expected[symbol] = expected.get(symbol, 0) + order["filled"] * (1 if order["side"] == "BUY" else -1)
        expected = {symbol: quantity for symbol, quantity in expected.items() if quantity}
        actual = {symbol: quantity for symbol, quantity in inventory["positions"].items() if quantity}
        if expected != actual or any(quantity < 0 for quantity in expected.values()):
            raise ValueError("execution_observation_position_mismatch")
        manager.state["execution_observation"] = {
            "account_fingerprint": manager.state["broker_identity"], "mode": manager.state["mode"],
            "as_of": observed_at, "inventory": copy.deepcopy(inventory), "source_hashes": dict(source_hashes),
            "order_contracts": {order["id"]: {key: order.get(key) for key in
                ("broker_id", "symbol", "side", "quantity", "price", "filled", "status")}
                for order in manager.state["orders"].values()},
        }
        manager.verify_cancellations(events, complete=True)
        manager._save()
        manager._execution_observation_valid = True
    except Exception:
        manager.state = before
        manager._cancel_verified = {}
        raise


def validate_reduction(manager, order):
    """새 매수 승인 없이도 가능한 매도인지 검사한다. 차입·다른 계좌·불명 주문은 거절한다."""
    if manager.state["mode"] != "kis_demo" or manager.state.get("replay_only") or manager.state.get("restore_gate"):
        raise ValueError("reduction_mode_or_restore_gate")
    if order["side"] != "SELL":
        raise ValueError("reduction_sell_only")
    if getattr(manager, "_execution_observation_valid", False) is not True:
        raise ValueError("reduction_requires_current_process_observation")
    observation = manager.state.get("execution_observation", {})
    if (observation.get("mode") != "kis_demo"
            or observation.get("account_fingerprint") != manager.state.get("broker_identity")):
        raise ValueError("reduction_account_not_observed")
    now = datetime.now(timezone.utc)
    for stamp in [observation["as_of"], order["quote_at"]]:
        if not 0 <= (now - parse_timestamp(stamp)).total_seconds() <= 30:
            raise ValueError("reduction_snapshot_or_quote_stale")
    inventory = observation["inventory"]
    remote_ids = set(inventory["broker_reserved_ids"])
    from trading.order_contract import broker_key
    others = [item for item in manager.state["orders"].values() if item["id"] != order["id"] and item["status"] in ACTIVE]
    if any(item["status"] in {"UNKNOWN", "SENDING"} for item in others):
        raise ValueError("reduction_unknown_order_requires_reconcile")
    # 관측 이후 원주문/체결을 바꾼 상태는 매도 근거가 될 수 없다.
    for identifier, contract in observation["order_contracts"].items():
        current = manager.state["orders"].get(identifier, {})
        if identifier != order["id"] and any(current.get(key) != value for key, value in contract.items()):
            raise ValueError("reduction_observed_order_changed")
    unsent_reserved = sum(item["quantity"] - item["filled"] for item in others
        if item["side"] == "SELL" and item["symbol"] == order["symbol"]
        and (not item.get("broker_id") or broker_key(item["broker_id"]) not in remote_ids))
    remaining = order["quantity"] - order.get("filled", 0)
    if remaining <= 0 or remaining + unsent_reserved > inventory["sellable"].get(order["symbol"], 0):
        raise ValueError("reduction_exceeds_verified_sellable")
    if money(order["price"]) <= 0:
        raise ValueError("reduction_limit_price_invalid")
