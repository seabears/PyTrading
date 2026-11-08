"""KIS 모의 잔고 캡처를 검산해 같은 SQLite의 미확정 관측 원장에 연결한다.

판단 순서: 계좌/모드/원본 해시/시각 → 전체 페이지 → 중복 보유 → 금액 파싱 → 저장.
주문가능액은 현금이 아니며 output3 집계는 통화 기준 미확정 상태로 보존한다.
이 연결은 RiskProof 또는 신규 주문 권한을 만들지 않는다.
"""
from datetime import datetime, timezone
from decimal import Decimal

from strategy.engine import parse_timestamp
from trading.risk_ledger import RiskLedger, amount, digest

BALANCE = "overseas_stock.inquire_balance"
CAPACITY = "overseas_stock.inquire_psamount"
PRESENT = "overseas_stock.inquire_present_balance"
EXCHANGES = {"NASD", "NYSE", "AMEX"}
AGGREGATE_FIELDS = {
    "frcr_evlu_tota": "외화평가총액",
    "tot_asst_amt": "총자산금액",
    "tot_frcr_cblc_smtl": "총외화잔고합계",
    "tot_loan_amt": "총대출금액",
}


def checked_records(manager, records, now):
    """현재 조회 캡처만 연결한다. 과거 재생은 실제 관측으로 재시간화하지 않는다."""
    if manager.state["mode"] != "kis_demo" or not manager.state.get("broker_identity"):
        raise ValueError("balance_bound_demo_account_required")
    selected = [record for record in records if record.get("operation") in {BALANCE, CAPACITY, PRESENT}]
    if not selected:
        raise ValueError("balance_capture_missing")
    for record in selected:
        if (record.get("environment") != "vps"
                or record.get("account_fingerprint") != manager.state["broker_identity"]
                or record.get("method") != "GET"):
            raise ValueError("balance_capture_account_mode_or_method_mismatch")
        if not 0 <= (now - parse_timestamp(record["at"])).total_seconds() <= 30:
            raise ValueError("balance_capture_stale")
        if digest(record["payload"]) != record.get("sha256"):
            raise ValueError("balance_capture_hash_mismatch")
        if record["payload"].get("rt_cd") != "0":
            raise ValueError("balance_capture_business_error")
    return selected


def holdings_from_pages(records):
    """미국 3거래소 전체 페이지를 확인한다. 동일 보유는 중복 합산하지 않는다."""
    final_pages = {}
    seen_pages = set()
    positions = {}
    duplicates = 0
    for record in records:
        if record["operation"] != BALANCE:
            continue
        context = record["request_context"]
        exchange = context.get("OVRS_EXCG_CD")
        if exchange not in EXCHANGES or context.get("TR_CRCY_CD") != "USD":
            raise ValueError("balance_exchange_or_currency_invalid")
        page_key = (exchange, record["sha256"])
        if page_key in seen_pages or final_pages.get(exchange) is True:
            raise ValueError("balance_page_repeated_or_after_final")
        seen_pages.add(page_key)
        continuation = record.get("continuation")
        if continuation not in {"", "D", "E", "M", "F"}:
            raise ValueError("balance_continuation_unknown")
        final_pages[exchange] = continuation not in {"M", "F"}
        rows = record["payload"]["output1"]
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("balance_rows_invalid")
        for row in rows:
            quantity = Decimal(str(row["ovrs_cblc_qty"]))
            sellable = Decimal(str(row["ord_psbl_qty"]))
            if (not quantity.is_finite() or not sellable.is_finite()
                    or quantity < 0 or sellable < 0 or sellable > quantity
                    or quantity != int(quantity) or sellable != int(sellable)):
                raise ValueError("balance_quantity_invalid")
            if not quantity:
                continue
            if row.get("tr_crcy_cd") != "USD":
                raise ValueError("balance_position_currency_invalid")
            symbol = row["ovrs_pdno"]
            if not isinstance(symbol, str) or not symbol:
                raise ValueError("balance_symbol_missing")
            # 대출 코드 의미를 추측하지 않고 다른 잔고 구분을 합쳐 버리지 않는다.
            key = (symbol, row.get("ovrs_excg_cd"), row.get("loan_type_cd"), row.get("loan_dt"))
            value = {"symbol": symbol, "quantity": int(quantity), "sellable": int(sellable),
                     "currency": "USD", "cost_basis_usd": str(amount(row["frcr_pchs_amt1"])),
                     "reported_market_value_usd": str(amount(row["ovrs_stck_evlu_amt"])),
                     "reported_unrealized_pnl_usd": str(amount(row["frcr_evlu_pfls_amt"], signed=True))}
            if key in positions:
                if positions[key] != value:
                    raise ValueError("balance_duplicate_position_conflict")
                duplicates += 1
            else:
                positions[key] = value
    if set(final_pages) != EXCHANGES or not all(final_pages.values()):
        raise ValueError("balance_pages_incomplete")
    # 같은 종목의 다른 잔고 구분은 자동 합산하지 않고 원가/수량을 별도로 확인한다.
    symbols = [row["symbol"] for row in positions.values()]
    if len(symbols) != len(set(symbols)):
        raise ValueError("balance_multiple_position_types_require_review")
    return list(positions.values()), duplicates


def connect_balance_observation(manager, records, now=None):
    """검산한 조회를 관측 원장에 저장한다. 현금/NAV나 확정 비용을 만들지 않는다."""
    manager.ready = False
    now = now or datetime.now(timezone.utc)
    records = checked_records(manager, records, now)
    positions, duplicates = holdings_from_pages(records)
    capacities = [record for record in records if record["operation"] == CAPACITY]
    presents = [record for record in records if record["operation"] == PRESENT]
    if len(capacities) != 1 or len(presents) != 1:
        raise ValueError("balance_capacity_or_summary_missing_or_duplicated")
    capacity = capacities[0]["payload"]["output"]
    if capacity.get("tr_crcy_cd") != "USD":
        raise ValueError("balance_capacity_currency_invalid")
    if presents[0].get("continuation") in {"M", "F"}:
        raise ValueError("balance_present_pages_incomplete")
    summary = presents[0]["payload"]["output3"]
    if not isinstance(summary, dict):
        raise ValueError("balance_summary_invalid")
    aggregate = {
        key: {"name": name, "value": str(amount(summary[key])), "currency": None,
              "basis": "reported_aggregate_currency_unconfirmed"}
        for key, name in AGGREGATE_FIELDS.items() if key in summary
    }
    observation = {
        "account_fingerprint": manager.state["broker_identity"], "mode": "kis_demo",
        "source_kind": "kis_vps_observation", "as_of": max((record["at"] for record in records), key=parse_timestamp),
        "source_hashes": {str(index): record["sha256"] for index, record in enumerate(records)},
        "source_times": {str(index): record["at"] for index, record in enumerate(records)},
        "inventory": {"positions": {row["symbol"]: row["quantity"] for row in positions},
                      "position_costs": {row["symbol"]: row["cost_basis_usd"] for row in positions}},
        "balance_snapshot": {"positions": positions, "duplicate_rows_ignored": duplicates,
            "holdings_cost_basis_usd": str(sum((amount(row["cost_basis_usd"]) for row in positions), Decimal(0))),
            "reported_holdings_value_usd": str(sum((amount(row["reported_market_value_usd"]) for row in positions), Decimal(0))),
            "reported_buying_power_usd": str(amount(capacity["ovrs_ord_psbl_amt"])),
            "reported_aggregate_fields": aggregate, "complete_balance_pages": True},
        "missing_evidence": ["execution_cash_basis_unproven", "usd_nav_basis_unproven",
            "final_costs_and_cash_movements_unproven"],
        "new_orders_allowed": False,
    }
    # RiskLedger의 기존 미확정 관측 경로는 실제 현금/NAV/손익을 None으로 강제한다.
    identifier = RiskLedger(manager).record_unsettled_observation(observation)
    return {"observation_id": identifier, "observation": manager.state["risk_observations"][identifier],
            "ledger_connected": True, "risk_approved": False, "new_orders_allowed": False}
