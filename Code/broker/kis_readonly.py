"""모의 계좌 조회 전용 API. 생성·전송·낮은 HTTP 경로에서 계좌 변경 요청을 거절한다."""

import copy
import hashlib
import json
from datetime import datetime, timezone

from broker.kis_api.client import KisApiClient, KisApiError

ALLOWED_OPERATIONS = {
    "overseas_stock.inquire_ccnl",
    "overseas_stock.inquire_balance",
    "overseas_stock.inquire_psamount",
    "overseas_stock.inquire_present_balance",
}
ALLOWED_PATHS = {
    "/uapi/overseas-stock/v1/trading/inquire-ccnl",
    "/uapi/overseas-stock/v1/trading/inquire-balance",
    "/uapi/overseas-stock/v1/trading/inquire-psamount",
    "/uapi/overseas-stock/v1/trading/inquire-present-balance",
}


def redact_payload(value, secrets):
    """인증·계좌 원문과 자유문 오류 메시지는 보존하지 않는다. 응답 구조는 유지한다."""
    if isinstance(value, dict):
        return {
            key: redact_payload(item, secrets)
            for key, item in value.items()
            if key.lower()
            not in {
                "cano",
                "acnt_prdt_cd",
                "account",
                "account_number",
                "appkey",
                "appsecret",
                "access_token",
                "authorization",
                "msg1",
                "rjct_rson_name",
                "cust_name",
                "acnt_name",
            }
        }
    if isinstance(value, list):
        return [redact_payload(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret and len(secret) >= 8:
                value = value.replace(secret, "[REDACTED]")
    return value


class ReadOnlyKisApi(KisApiClient):
    def __init__(self, market_client, account_number):
        if market_client.environment != "vps":
            raise ValueError("preflight_requires_vps")
        super().__init__(market_client, allow_trading=False)
        self.records = []
        self.secrets = (account_number, market_client.app_key, market_client.app_secret)

    def execute(self, specification):
        if specification.method != "GET" or specification.name not in ALLOWED_OPERATIONS:
            raise KisApiError("readonly_operation_blocked")
        response = super().execute(specification)
        safe = redact_payload(copy.deepcopy(response.payload), self.secrets)
        self.records.append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "environment": self.market_client.environment,
                "account_fingerprint": hashlib.sha256((self.market_client.environment + "\0" +
                    str(self.market_client.app_key) + "\0" + str(specification.parameters.get("CANO")) +
                    "\0" + str(specification.parameters.get("ACNT_PRDT_CD"))).encode()).hexdigest(),
                "request_context": {key: value for key, value in specification.parameters.items()
                                    if key in {"OVRS_EXCG_CD", "TR_CRCY_CD", "ORD_STRT_DT", "ORD_END_DT",
                                               "WCRC_FRCR_DVSN_CD", "NATN_CD", "TR_MKET_CD", "INQR_DVSN_CD",
                                               "OVRS_ORD_UNPR", "ITEM_CD", "PDNO"}},
                "method": "GET",
                "operation": specification.name,
                "tr_id": specification.transaction_id,
                "continuation": response.continuation,
                "payload": safe,
                "sha256": hashlib.sha256(json.dumps(safe, sort_keys=True).encode()).hexdigest(),
            }
        )
        return response

    def _http(self, path, parameters, method, headers=None, *, order=False):
        if method != "GET" or order or path not in ALLOWED_PATHS:
            raise KisApiError("readonly_http_blocked")
        return super()._http(path, parameters, method, headers, order=False)

    def execute_managed(self, *arguments, **keywords):
        raise KisApiError("readonly_orders_blocked")


def inspect_remote(manager, adapter, start, end, symbol, price):
    """양끝 전체 주문 조회가 같아야 잔고·예약 검사를 진행한다. 주문 자격은 부여하지 않는다."""
    from trading.order_contract import context
    from trading.reconciliation import normalize_orders, normalize_inventory

    manager.ready = False
    proof_context = {**context(manager.state), "limit_only": False}
    first = normalize_orders(adapter.query_history(start, end), proof_context)
    balances = adapter.query_balances()
    capacity = adapter.query_buying_power(symbol, price)
    present = adapter.query_present_balance()
    second = normalize_orders(adapter.query_history(start, end), proof_context)
    if sorted(row["event_id"] for row in first) != sorted(row["event_id"] for row in second):
        raise ValueError("history_changed_during_snapshot")
    inventory = normalize_inventory(balances, second)
    known, errors = manager._verified_events(second)
    if any(row["order_type"] == "UNKNOWN" for row in second):
        errors.append("order_type_not_returned_by_contract")
    if any(
        order["status"] in {"UNKNOWN", "SENDING", "ACCEPTED", "PARTIAL", "CANCEL_PENDING"}
        and not any(order["id"] == local["id"] for local, event in known.values())
        for order in manager.state["orders"].values()
    ):
        errors.append("local_order_missing_from_history")
    local_reservations = {"sell": {}, "buy_notional_before_cost_buffer": "0"}
    from decimal import Decimal

    reserved_buy = Decimal(0)
    for order in manager.state["orders"].values():
        if order["status"] not in {
            "INTENT",
            "UNKNOWN",
            "SENDING",
            "ACCEPTED",
            "PARTIAL",
            "CANCEL_PENDING",
        }:
            continue
        if order.get("broker_id") in inventory["broker_reserved_ids"]:
            continue
        remaining = order["quantity"] - order["filled"]
        if order["side"] == "SELL":
            local_reservations["sell"][order["symbol"]] = (
                local_reservations["sell"].get(order["symbol"], 0) + remaining
            )
        else:
            reserved_buy += remaining * Decimal(order["price"])
    local_reservations["buy_notional_before_cost_buffer"] = str(reserved_buy)
    for ticker, quantity in local_reservations["sell"].items():
        if quantity > inventory["sellable"].get(ticker, 0):
            errors.append("local_sell_reservation_exceeds_available")
    money_fields = capacity["output"]
    if money_fields["tr_crcy_cd"] != "USD":
        raise ValueError("unsupported_currency")
    # 읽기 전용 외화 주문 여력 진단값이다. 실제 USD 현금이나 계좌 미가입 증거가 아니다.
    buying_power = Decimal(money_fields["ovrs_ord_psbl_amt"])
    if not buying_power.is_finite() or buying_power < 0:
        raise ValueError("capacity_invalid")
    # 공개 응답의 외화예수금은 결제 기준이다. 별도 거래·수수료 수지 없이
    # 체결 기준 현금/순자산·일일 손익으로 변환하지 않는다.
    currencies = [row for row in present["output2"] if row.get("crcy_cd") == "USD"]
    errors += ["execution_fee_and_cash_movement_history_not_proven"]
    if len(currencies) != 1:
        errors.append("usd_cash_record_missing_or_duplicated")
    try:
        from trading.risk_ledger import RiskLedger

        proof = RiskLedger(manager).context()
        risk = {"checkpoint_hash": proof.checkpoint_hash, "eligible": proof.eligible}
        if proof.positions != inventory["positions"] or proof.buying_power != str(buying_power):
            # 소수 문자열 표기 차이는 Decimal로 다시 비교한다.
            if (
                proof.positions != inventory["positions"]
                or Decimal(proof.buying_power) != buying_power
            ):
                errors.append("remote_risk_snapshot_mismatch")
    except ValueError:
        risk = {"eligible": False}
        errors.append("risk_evidence_unavailable_or_stale")
    return {
        "kind": "kis_demo_readonly",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "account_fingerprint": manager.state["broker_identity"],
        "inventory": inventory,
        "local_unsent_or_unconfirmed_reservations": local_reservations,
        "buying_power": str(buying_power),
        "reported_usd_deposit_settlement_basis": (
            currencies[0].get("frcr_dncl_amt_2") if len(currencies) == 1 else None
        ),
        "risk": risk,
        "issues": sorted(set(errors)),
        "new_orders_allowed": False,
        "history_stable": True,
        "order_rows": len(second),
        "order_requests_sent": 0,
    }
