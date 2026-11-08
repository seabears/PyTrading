"""KIS 수량과 주문 계약을 엄격히 대조한다. 예약된 수량·금액은 이중 차감하지 않는다."""

import hashlib
import json
from datetime import datetime, timezone
from trading.orders import money
from trading.order_contract import broker_key, context


def whole(value):
    number = money(value)
    if number != number.to_integral_value():
        raise ValueError("fractional_quantity_unsupported")
    return int(number)


def normalize_orders(rows, identity_context=None):
    identity_context = identity_context or {
        "mode": None,
        "account_fingerprint": None,
        "limit_only": False,
    }
    orders = []
    children = []
    seen = set()
    for row in rows:
        identifier = broker_key(row["ord_dt"] + ":" + row["odno"])
        if identifier in seen:
            raise ValueError("duplicate_order_identifier")
        seen.add(identifier)
        original = row["orgn_odno"].strip()
        if original and set(original) != {"0"}:
            children.append((identifier, broker_key(row["ord_dt"] + ":" + original), row))
            continue
        quantity, filled, remaining = (
            whole(row[field]) for field in ("ft_ord_qty", "ft_ccld_qty", "nccs_qty")
        )
        if (
            quantity < 1
            or filled > quantity
            or filled + remaining > quantity
            or row["tr_crcy_cd"] != "USD"
        ):
            raise ValueError("remote_quantity_or_currency_mismatch")
        if filled == quantity:
            status = "FILLED"
        elif (
            row["prcs_stat_name"] in {"취소", "취소완료", "전량취소"}
            and row["rjct_rson"] in {"", "0", "00000"}
            and remaining == 0
        ):
            status = "CANCELLED"
        elif row["rjct_rson"] not in {"", "0", "00000"} and remaining == 0:
            status = "REJECTED"
        elif filled + remaining == quantity and remaining:
            status = "PARTIAL" if filled else "ACCEPTED"
        else:
            raise ValueError("remote_final_status_unknown")
        side = {"01": "SELL", "02": "BUY"}.get(row["sll_buy_dvsn_cd"])
        if side is None:
            raise ValueError("remote_side_unknown")
        raw_type = row.get("ord_dvsn")
        order_type = (
            "LIMIT"
            if raw_type == "00" or (raw_type is None and identity_context.get("limit_only") is True)
            else "UNKNOWN"
        )
        event = {
            **{key: identity_context[key] for key in ("mode", "account_fingerprint")},
            "broker_id": identifier,
            "order_day": row["ord_dt"],
            "order_number": row["odno"],
            "original_broker_id": None,
            "order_type": order_type,
            "symbol": row["pdno"],
            "side": side,
            "quantity": quantity,
            "price": str(money(row["ft_ord_unpr3"])),
            "filled": filled,
            "notional": str(money(row["ft_ccld_amt3"])),
            "status": status,
            "remaining": remaining,
            "linked_cancellations": [],
        }
        orders.append(event)
    by_id = {row["broker_id"]: row for row in orders}
    for identifier, parent, row in children:
        if parent not in by_id:
            number = parent.split(":")[1]
            matches = [
                key
                for key, base in by_id.items()
                if key.split(":")[1] == number
                and key.split(":")[0] <= row["ord_dt"]
                and base["symbol"] == row["pdno"]
            ]
            if len(matches) != 1:
                raise ValueError("original_order_missing_or_ambiguous")
            parent = matches[0]
        base = by_id[parent]
        if row.get("rvse_cncl_dvsn") != "02":
            raise ValueError("unmanaged_amendment_requires_review")
        if (
            row["pdno"] != base["symbol"]
            or {"01": "SELL", "02": "BUY"}.get(row["sll_buy_dvsn_cd"]) != base["side"]
        ):
            raise ValueError("cancel_child_identity_mismatch")
        quantity = whole(row["ft_ord_qty"])
        if not 0 < quantity <= base["quantity"] or money(row["ft_ord_unpr3"]) != 0:
            raise ValueError("cancel_child_contract_mismatch")
        base["linked_cancellations"].append(
            {
                "broker_id": identifier,
                "requested_quantity": quantity,
                "status": "REJECTED" if row["rjct_rson"] not in {"", "0", "00000"} else "ACCEPTED",
            }
        )
        # 취소 자식 행의 접수만으로 원주문을 CANCELLED로 바꾸지 않는다.
    for event in orders:
        event["event_id"] = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
    return orders


def normalize_inventory(balance_rows, remote_orders=()):
    """위험 승인과 분리해 전체 보유·매도가능·원격 예약의 수지를 검사한다."""
    remote_sell = {}
    remote_ids = []
    for order in remote_orders:
        if order["status"] in {"ACCEPTED", "PARTIAL"}:
            remote_ids.append(broker_key(order["broker_id"]))
            if order["side"] == "SELL":
                remote_sell[order["symbol"]] = (
                    remote_sell.get(order["symbol"], 0) + order["quantity"] - order["filled"]
                )
    positions = {}
    costs = {}
    sellable = {}
    from broker.product_policy import validate_symbol, load_product_rules

    for row in balance_rows:
        symbol = row["ovrs_pdno"]
        validate_symbol(symbol, load_product_rules())
        quantity = whole(row["ovrs_cblc_qty"])
        allowed = whole(row["ord_psbl_qty"])
        if row["tr_crcy_cd"] != "USD" or allowed > quantity:
            raise ValueError("position_quantity_or_currency_mismatch")
        cost = str(money(row["frcr_pchs_amt1"]))
        if symbol in positions and (positions[symbol], sellable[symbol], costs[symbol]) != (
            quantity,
            allowed,
            cost,
        ):
            raise ValueError("duplicate_position_conflict")
        if quantity - allowed != remote_sell.get(symbol, 0):
            raise ValueError("unexplained_sell_reservation")
        positions[symbol] = quantity
        sellable[symbol] = allowed
        costs[symbol] = cost
    if any(symbol not in positions and count for symbol, count in remote_sell.items()):
        raise ValueError("remote_sell_without_position")
    return {
        "positions": positions,
        "sellable": sellable,
        "remote_reserved_sell": remote_sell,
        "broker_reserved_ids": remote_ids,
        "remote_reservations_included": True,
        "position_costs": costs,
        "exposure": str(sum(money(value) for value in costs.values())),
    }


def normalize_snapshot(balance_rows, capacity, risk_context, remote_orders=(), *, buying_power_service=None, buying_power_evidence=None):
    from trading.risk_ledger import RiskProof

    if not isinstance(risk_context, RiskProof) or not risk_context.eligible:
        raise ValueError("risk_context_unverified")
    output = capacity["output"]
    if output["tr_crcy_cd"] != "USD":
        raise ValueError("unsupported_currency")
    from trading.cash_service_policy import validate_service_setting
    if buying_power_service is not None:
        validate_service_setting(buying_power_service)
    # 가입 상태는 검사하지 않는다. USD 현금 상한·위험 한도는 주문 경계에서 검사한다.
    available = money(output["ovrs_ord_psbl_amt"])
    inventory = normalize_inventory(balance_rows, remote_orders)
    if inventory["positions"] != risk_context.positions:
        raise ValueError("risk_and_broker_snapshot_mismatch")
    extra = {}
    if buying_power_evidence is not None:
        if available != money(buying_power_evidence["buying_power_usd"]):
            raise ValueError("buying_power_capture_value_mismatch")
        extra = {"buying_power_usd": str(available), "buying_power_evidence": buying_power_evidence}
    elif available != money(risk_context.buying_power):
        raise ValueError("risk_and_broker_snapshot_mismatch")
    return {**extra,
        **inventory,
        **risk_context.values(),
        "broker_position_costs": inventory["position_costs"],
        "position_costs": risk_context.position_costs,
        "exposure": risk_context.exposure,
        "cash": str(available),
        "cash_is_available_order_capacity": True,
        "risk_checkpoint_hash": risk_context.checkpoint_hash,
        "risk_account_fingerprint": risk_context.account_fingerprint,
        "as_of": risk_context.as_of,
    }


def synchronize(manager, adapter, risk_context, start, end, symbol, price):
    manager.ready = False
    manager._cancel_verified = {}
    try:
        proof_context = context(manager.state)
        first = normalize_orders(adapter.query_history(start, end), proof_context)
        balances = adapter.query_balances()
        capacity = adapter.query_buying_power(symbol, price)
        second = normalize_orders(adapter.query_history(start, end), proof_context)
        if sorted(row["event_id"] for row in first) != sorted(row["event_id"] for row in second):
            raise ValueError("history_changed_during_snapshot")
        manager.verify_cancellations(second, complete=True)
        snapshot = normalize_snapshot(balances, capacity, risk_context, second)
        snapshot["remote_history_start"] = start
        manager.reconcile(snapshot, second, complete=True)
    except Exception as error:
        manager.record_reconcile_failure(str(error))
        raise
