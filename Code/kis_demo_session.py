"""정규장 복구 후 KIS 모의계좌를 별도 원장에서 조회·검산한다.

기본 CLI는 조회 전용이다. 별도 kis_demo_execute.py에서만 명시 실행을 요청한다.
완전한 위험 검산 전 신규 매수는 차단하며, 실제 계좌 관측은 미확정 기록으로 보존한다.
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from broker.kis import BASE_URLS, TOKEN_PATH, KisMarketClient
from broker.kis_setup import load_kis_settings
from broker.kis_readonly import ReadOnlyKisApi, ALLOWED_PATHS, inspect_remote
from broker.managed_kis import ManagedKisAdapter
from kis_preflight import read_demo_identity
from paths import CONFIG_ROOT, DATA_ROOT
from trading.orders import OrderManager
from trading.demo_session import LimitedDemoSession
from trading.demo_readiness import assess_readonly_inputs, ingest_available_sources, resolve_available_sources
from trading.demo_profile import load_demo_profile
from trading.demo_account import record_initial_reference
from trading.demo_port import DemoExecutionPort
from trading.demo_runner import LimitedDemoRunner
from trading.demo_store import session_store
from broker.demo_trial import TrialKisApi, ORDER_PATHS
from strategy.engine import parse_timestamp
from broker.sessions import regular_session


def validate_demo_readonly_request(request):
    """실제 HTTP 경계에서도 vps 인증POST와 허용 조회GET 이외에는 전송하지 않는다."""
    url = urllib.parse.urlsplit(request.full_url)
    expected = urllib.parse.urlsplit(BASE_URLS["vps"])
    if url.scheme != expected.scheme or url.netloc != expected.netloc:
        raise ValueError("demo_readonly_host_mismatch")
    path, method = url.path, request.get_method()
    if (method == "POST" and path == TOKEN_PATH) or (method == "GET" and path in ALLOWED_PATHS):
        return method, path
    raise ValueError("demo_readonly_order_http_blocked")


def run(recovery_file, credentials_file, output, profile_file=None, contracts_folder=None, execute_requested=False):
    profile = load_demo_profile(profile_file)
    symbol = profile["symbol"]
    now = datetime.now(timezone.utc)
    snapshot = json.loads(recovery_file.read_text(encoding="utf-8"))
    recovery = snapshot.get("recovery", snapshot)
    if (recovery.get("regular_recovery_verified") is not True or not regular_session("US", now)
            or recovery.get("input_kind") != "live_observation"
            or not 0 <= (now - parse_timestamp(recovery["checked_at"])).total_seconds() <= 30):
        raise ValueError("actual_regular_recovery_required")
    if snapshot.get("service", {}).get("ActiveState") not in {None, "active"}:
        raise ValueError("observation_service_not_active")
    output = output.resolve()
    if not output.is_relative_to(DATA_ROOT.resolve()):
        raise ValueError("session_output_must_be_inside_data")
    stamp = now.strftime("%Y%m%d-%H%M%S-%f")
    target = output / ("actual-vps-" + stamp)
    target.mkdir(parents=True)
    key, secret, account, product = read_demo_identity(credentials_file)
    market = KisMarketClient(key, secret, "vps")
    market.token_cache = DATA_ROOT / "cache/kis/vps" / ("readonly-" + market.identity[:16] + ".json")
    api = (TrialKisApi if execute_requested else ReadOnlyKisApi)(market, account)
    audit = []
    original_urlopen = urllib.request.urlopen

    def guarded_urlopen(request, *args, **kwargs):
        url = urllib.parse.urlsplit(request.full_url)
        method, path = request.get_method(), url.path
        demo_host = urllib.parse.urlsplit(BASE_URLS["vps"]).netloc
        quote_host = urllib.parse.urlsplit(BASE_URLS["prod"]).netloc
        if (execute_requested and url.scheme == "https" and url.netloc == demo_host
                and method == "POST" and path in ORDER_PATHS
                and api._managed_permission and api.allow_trading and session is not None
                and (session.armed or path.endswith("order-rvsecncl"))):
            pass  # 실제 전송 전의 원장·위험·수량 검사는 execute_managed에서 수행한다.
        elif (execute_requested and url.scheme == "https" and url.netloc == quote_host
                and ((method == "GET" and path == "/uapi/overseas-price/v1/quotations/inquire-asking-price")
                     or (method == "POST" and path == TOKEN_PATH))):
            pass  # 분리된 실전 시세 인증/호가 조회만 허용한다. 실전 주문은 계속 금지다.
        else:
            method, path = validate_demo_readonly_request(request)
        row = {"at": datetime.now(timezone.utc).isoformat(), "method": method,
               "path": path, "environment": "vps" if url.netloc == demo_host else "prod_quotes",
               "kind": "authentication" if path == TOKEN_PATH else "account_read"}
        audit.append(row)
        try:
            response = original_urlopen(request, *args, **kwargs)
            row["http_status"] = response.status
            return response
        except Exception:
            row["outcome"] = "request_failed"
            raise

    manager = None
    adapter = None
    session = None
    result = {"environment": "vps", "regular_recovery_verified": True,
              "new_orders_allowed": False, "risk_ingested": False,
              "buy_requests": 0, "sell_requests": 0, "cancel_requests": 0,
              "phase": "readonly_query", "result_directory": str(target)}
    urllib.request.urlopen = guarded_urlopen
    try:
        market.authenticate()
        api.secrets = (*api.secrets, market.access_token)
        store, alias, session_id = session_store(profile, stamp)
        manager = OrderManager(store, "kis_demo", alias)
        options = load_kis_settings(CONFIG_ROOT / "kis.json")
        exchanges = {symbol: {"NAS": "NASD", "NYS": "NYSE", "AMS": "AMEX"}.get(value, value)
                     for symbol, value in options["us_exchanges"].items()}
        adapter = ManagedKisAdapter(api, manager, account, product, exchanges, enabled=False)
        session = LimitedDemoSession(manager, adapter, session_id, symbol, profile=profile_file)
        if execute_requested:
            api.trial_session = session
        if profile.get("initial_reference"):
            result["initial_capital_reference"] = record_initial_reference(manager, profile["initial_reference"])
        contracts = {}
        if contracts_folder:
            for path in contracts_folder.glob("*.json"):
                contracts[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        port = DemoExecutionPort(manager, adapter, profile, contracts, recovery_file)
        observation = port.refresh()
        result.update(phase="risk_sources_blocked", query_success=True,
            account_binding_verified=True, execute_requested=execute_requested,
            risk_ingested=observation["risk_ingested"], risk_observation_id=observation["risk_observation_id"], risk_inputs=observation["risk_inputs"],
            remote_readonly=observation["report"], source_resolution=observation["resolution"],
            risk_gate="risk_sources_unproven" if not observation["new_orders_allowed"] else None,
            profile_limits_hash=profile["limits_hash"], profile_symbol=symbol,
            local_session=session.summary(), store=str(store),
            final_remote_account_snapshot_verified=True)
        if execute_requested and (observation["new_orders_allowed"] or session.state["order_ids"]):
            # 증권 계좌 인증(vps)과 시세 인증(prod)은 별도 파일·토큰을 사용한다.
            from app.runtime import load_run_settings
            from broker.kis_setup import create_kis_client
            runtime = load_run_settings()
            quote_client = create_kis_client(runtime["env_file"], options)
            if quote_client.environment != "prod":
                raise ValueError("separate_prod_quote_connection_required")
            port.quote_client = quote_client
            # 전송이 가능한 시점부터는 운영체제 종료 요청도 유한 루프의 종료 조건으로 받는다.
            import signal
            stop = {"requested": False}
            prior_handlers = {}
            def request_stop(*_):
                stop["requested"] = True
            try:
                for signum in (signal.SIGINT, signal.SIGTERM):
                    prior_handlers[signum] = signal.signal(signum, request_stop)
                workflow = LimitedDemoRunner(session, port, stop_requested=lambda: stop["requested"])
                result["workflow"] = workflow.run()
            finally:
                for signum, handler in prior_handlers.items():
                    signal.signal(signum, handler)
            result["phase"] = "completed" if result["workflow"]["completed"] else "review_required"
            result["final_remote_account_snapshot_verified"] = result["workflow"].get("final_remote_verified", False)
        elif not execute_requested:
            result["phase"] = "readonly_complete_risk_blocked" if not observation["new_orders_allowed"] else "readonly_complete"
        result["local_session"] = session.summary()
        result["settlement"] = manager.state.get("demo_settlement")
        # 최종 프로필·활성화 상태는 파일에 켜 두지 않는다.
        result.update(buy_requests=session.state["buy_attempts"], sell_requests=session.state["sell_attempts"],
                      cancel_requests=session.state["cancel_attempts"])

    finally:
        if session:
            result.update(buy_requests=session.state["buy_attempts"], sell_requests=session.state["sell_attempts"],
                          cancel_requests=session.state["cancel_attempts"])
            result["local_session"] = session.summary()
            session.disarm()
        if adapter:
            adapter.enabled = False
        api.allow_trading = False
        result["final_order_activation"] = False
        result["http_audit"] = [row for row in audit if row["kind"] == "authentication"] + api.http_audit
        urllib.request.urlopen = original_urlopen
        if manager:
            manager.ready = False
            manager.close()
        # 모든 값은 기존 redactor를 거친 뒤에만 보존한다. 원문 계좌/키/토큰 유출을 재검사한다.
        serialized = json.dumps({"result": result, "records": api.records}, ensure_ascii=False, indent=2)
        if any(value in serialized for value in (key, secret, account, market.access_token) if len(value) >= 8):
            raise ValueError("redaction_validation_failed")
        (target / "responses-redacted.json").write_text(json.dumps(api.records, ensure_ascii=False, indent=2), encoding="utf-8")
        (target / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recovery-file", type=Path)
    parser.add_argument("--env-file", type=Path, default=CONFIG_ROOT.parent / "Credentials/kis_demo.env")
    parser.add_argument("--output", type=Path, default=DATA_ROOT / "reports/kis-demo-session")
    parser.add_argument("--profile", type=Path, default=CONFIG_ROOT / "kis-demo-session.json")
    parser.add_argument("--contracts-folder", type=Path, help="공식 포털에서 고정한 지원/필드 계약")
    parser.add_argument("--execute", action="store_true", help="정규장 사전 관측 후10분 한정 vps 시험. 실계좌 금지")
    arguments = parser.parse_args()
    try:
        if arguments.recovery_file is None:
            from trading.demo_day_gate import today_session, QuoteWatchProcess
            schedule=today_session()
            if not schedule["regular_now"]:
                from zoneinfo import ZoneInfo
                opening=(datetime.fromisoformat(schedule["opening"]).astimezone(ZoneInfo("Asia/Seoul")).isoformat()
                         if schedule["opening"] else "오늘 휴장")
                print(json.dumps({"phase":"outside_regular_session","opening_kst":opening,"order_requests_sent":0},ensure_ascii=False))
                return 2
            folder=DATA_ROOT/"reports/demo-today-quotes"/datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            with QuoteWatchProcess(folder) as recovery_file:
                result=run(recovery_file,arguments.env_file,arguments.output,arguments.profile,
                           arguments.contracts_folder,execute_requested=arguments.execute)
        else:
            result=run(arguments.recovery_file,arguments.env_file,arguments.output,arguments.profile,
                       arguments.contracts_folder,execute_requested=arguments.execute)
        print(json.dumps({"phase": result["phase"], "result_directory": result["result_directory"],
                          "new_orders_allowed": False, "order_requests_sent": sum(result.get(name,0) for name in ("buy_requests","sell_requests","cancel_requests"))}, ensure_ascii=False))
        return 0 if result["phase"]=="completed" else 3
    except (ValueError, OSError, RuntimeError, KeyError):
        print("모의 시험이 중단됐습니다. 결과 원장의 주문·잔고 상태를 확인하세요. 상태 확인 전 같은 시험을 다시 실행하지 마세요.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
