"""미국주식 모의계좌 잔고를 조회해 SQLite 관측 원장에 연결한다. 실제 주문 경로 없음.

CMD: python Code/kis_demo_balance.py
기본 인증 파일은 프로젝트의 Credentials/kis_demo.env다. --env-file로 변경할 수 있다.
장외에도 읽기 전용 잔고 조회는 가능하다. 장외 실행으로 매매 권한을 만들지 않는다.
"""
import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from broker.kis import BASE_URLS, TOKEN_PATH, KisMarketClient
from broker.kis_readonly import ReadOnlyKisApi, redact_payload
from broker.managed_kis import ManagedKisAdapter
from broker.kis_setup import load_kis_settings
from kis_preflight import read_demo_identity
from paths import CONFIG_ROOT, DATA_ROOT
from trading.demo_balance import connect_balance_observation
from trading.orders import OrderManager

BALANCE_PATHS = {
    "/uapi/overseas-stock/v1/trading/inquire-balance",
    "/uapi/overseas-stock/v1/trading/inquire-present-balance",
    "/uapi/overseas-stock/v1/trading/inquire-psamount",
    "/uapi/overseas-stock/v1/trading/inquire-ccnl",
}


def validate_readonly_http(request):
    """실제 HTTP 경계에서 vps 인증과 네 종류의 조회만 허용한다."""
    url = urllib.parse.urlsplit(request.full_url)
    host = urllib.parse.urlsplit(BASE_URLS["vps"])
    method = request.get_method()
    if url.scheme != "https" or url.netloc != host.netloc:
        raise ValueError("balance_demo_host_required")
    if not ((method == "GET" and url.path in BALANCE_PATHS)
            or (method == "POST" and url.path == TOKEN_PATH)):
        raise ValueError("balance_readonly_http_blocked")
    return method, url.path


def cash_history_start(value):
    """등록 시각은 UTC 문자열 날짜가 아니라 미국 현지 거래일로 조회한다."""
    if len(value) == 10:
        return value.replace("-", "")
    return datetime.fromisoformat(value).astimezone(ZoneInfo("America/New_York")).strftime("%Y%m%d")


def collect_and_connect(manager, adapter, api, symbol="AAPL", probe_price="500", cash_basis=None):
    """수집 전체가 성공한 경우에만 원장에 기록한다. 여력용 가격은 주문 의도가 아니다."""
    manager.ready = False
    start = len(api.records)
    if cash_basis is not None:
        from trading.reconciliation import normalize_orders
        from trading.order_contract import context
        baseline = manager.state.get("user_cash_account", {}).get("baseline", {})
        history_start = baseline.get("enrolled_at", cash_basis["authorized_on"])
        history_start = cash_history_start(history_start)
        history_end = datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d")
        order_context = {**context(manager.state), "limit_only": False}
        first = normalize_orders(adapter.query_history(history_start, history_end), order_context)
    adapter.query_balances()
    adapter.query_present_balance()
    adapter.query_buying_power(symbol, probe_price)
    if cash_basis is not None:
        second = normalize_orders(adapter.query_history(history_start, history_end), order_context)
        if sorted(row["event_id"] for row in first) != sorted(row["event_id"] for row in second):
            raise ValueError("user_cash_history_changed_during_snapshot")
    result = connect_balance_observation(manager, api.records[start:])
    if cash_basis is not None:
        from trading.user_cash import update_user_cash
        result["user_cash_account"] = update_user_cash(manager, result, second, cash_basis)
    from trading.buying_power import bind_api_buying_power, assess_buying_power
    remote_ids = [row["broker_id"] for row in second if row["status"] in {"ACCEPTED", "PARTIAL"}] if cash_basis is not None else []
    inventory = {"broker_reserved_ids": remote_ids, "remote_reservations_included": cash_basis is not None}
    captured = [row for row in api.records[start:] if row["operation"] == "overseas_stock.inquire_psamount"]
    budget_account = bind_api_buying_power(manager, captured[0], inventory)
    result["purchase_budget"] = assess_buying_power(budget_account, manager.state["orders"].values())
    if cash_basis is not None:
        from trading.demo_cash_review import review_cash
        result["cash_risk_review"] = review_cash(manager, result, second, budget_account,
            api.records[start:], {"start": datetime.strptime(history_start, "%Y%m%d").date().isoformat(),
                                  "end": datetime.strptime(history_end, "%Y%m%d").date().isoformat()})
        from trading.risk_ledger import RiskLedger
        result["risk_assessment"] = RiskLedger(manager).assess_observation(result["cash_risk_review"])
        from trading.demo_readiness import resolve_available_sources,ingest_available_sources
        from trading.reconciliation import normalize_inventory
        inventory_full = normalize_inventory([position for row in api.records[start:] if row["operation"]=="overseas_stock.inquire_balance" for position in row["payload"]["output1"]],second)
        normalized={"inventory":inventory_full,"history_window":result["cash_risk_review"]["history_window"],
                    "query_started_at":api.records[start]["at"]}
        resolution=resolve_available_sources(manager,api,normalized,{})
        result["source_resolution"]={key:value for key,value in resolution.items() if key!="sources"}
        if resolution["sources"] is not None:
            proof=ingest_available_sources(manager,normalized,resolution["sources"])
            result["trial_risk_ingested"] = True
            result["trial_basis_eligible"] = proof.eligible
            result["trial_basis_scope"] = "user_designated_forward_empty_account_demo"
        from trading.demo_accounting_cycle import readonly_plan
        result["order_accounting_plan"] = readonly_plan(manager,result["cash_risk_review"],result["risk_assessment"])
    return result


def run(credentials_file, store, output):
    """조회/원장/결과 경로를 분리하고 종료 때도 주문 차단을 유지한다."""
    if not store.resolve().is_relative_to(DATA_ROOT.resolve()) or not output.resolve().is_relative_to(DATA_ROOT.resolve()):
        raise ValueError("balance_store_output_must_be_inside_data")
    output.mkdir(parents=True, exist_ok=False)
    key, secret, account, product = read_demo_identity(credentials_file)
    market = KisMarketClient(key, secret, "vps")
    market.token_cache = DATA_ROOT / "cache/kis/vps" / ("readonly-" + market.identity[:16] + ".json")
    api = ReadOnlyKisApi(market, account)
    manager = None
    original = urllib.request.urlopen
    audit = []

    def guarded(request, *arguments, **keywords):
        method, path = validate_readonly_http(request)
        row = {"at": datetime.now(timezone.utc).isoformat(), "method": method, "path": path}
        audit.append(row)
        try:
            response = original(request, *arguments, **keywords)
            row["http_status"] = response.status
            return response
        except Exception as error:
            row["error_type"] = type(error).__name__
            if type(getattr(error, "code", None)) is int:
                row["http_status"] = error.code
            raise

    result = {"ledger_connected": False, "risk_approved": False, "new_orders_allowed": False,
              "buy_requests": 0, "sell_requests": 0, "cancel_requests": 0}
    urllib.request.urlopen = guarded
    try:
        market.authenticate()
        api.secrets = (*api.secrets, market.access_token)
        manager = OrderManager(store, "kis_demo", "demo-balance-observation")
        options = load_kis_settings(CONFIG_ROOT / "kis.json")
        exchanges = {
            symbol: {"NAS": "NASD", "NYS": "NYSE", "AMS": "AMEX"}.get(exchange, exchange)
            for symbol, exchange in options["us_exchanges"].items()
        }
        adapter = ManagedKisAdapter(api, manager, account, product, exchanges, enabled=False)
        cash_basis = json.loads((CONFIG_ROOT / "kis-demo-cash.json").read_text(encoding="utf-8"))
        result.update(collect_and_connect(manager, adapter, api, cash_basis=cash_basis))
    except Exception as error:
        # 자유문 예외에는 인증·계좌·응답 원문이 포함될 수 있어 타입만 기록한다.
        result["error_type"] = type(error).__name__
    finally:
        urllib.request.urlopen = original
        api.allow_trading = False
        if manager:
            manager.ready = False
            manager.close()
    result.update(store=str(store), recorded_at=datetime.now(timezone.utc).isoformat(), http_audit=audit)
    safe = redact_payload(result, (key, secret, account, market.access_token))
    serialized = json.dumps({"result": safe, "records": api.records}, ensure_ascii=False)
    if any(value in serialized for value in (key, secret, account, market.access_token) if value and len(value) >= 8):
        raise ValueError("balance_redaction_failed")
    (output / "results.json").write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "responses-redacted.json").write_text(json.dumps(api.records, ensure_ascii=False, indent=2), encoding="utf-8")
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_credentials = CONFIG_ROOT.parent / "Credentials/kis_demo.env"
    parser.add_argument("--env-file", type=Path, default=default_credentials)
    parser.add_argument("--store", type=Path, default=DATA_ROOT / "execution/kis-demo-balance/orders.sqlite")
    parser.add_argument("--output", type=Path, default=DATA_ROOT / "reports/kis-demo-balance" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
    arguments = parser.parse_args()
    result = run(arguments.env_file, arguments.store, arguments.output)
    print(json.dumps({"ledger_connected": result["ledger_connected"], "risk_approved": False,
                      "output": str(arguments.output), "error_type": result.get("error_type")}, ensure_ascii=False))
    return 0 if result["ledger_connected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
