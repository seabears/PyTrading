"""고정 일봉 전략과 공통 체결 선택을 연결한다. 기본 내부 가상체결, 실계좌 전송 잠금."""

import json
import signal
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone

from app.audit_logs import record_symbol_decision
from app.operations import OperationMonitor
from app.runtime import load_run_settings, acquire_run_lock
from app.stateio import atomic_json, rotate_log
from broker.kis_setup import create_kis_client, load_kis_settings
from broker.kis_market import US_QUOTE, normalize_quote, wait_for_quote_time
from broker.sessions import regular_session
from paths import CONFIG_ROOT, DATA_ROOT, CODE_ROOT
from research.kis_history import collect_us_history
from research.daily import prepare_daily_bars
from trading.daily_account import DailyAccount, last_closed_day
from trading.observation_journal import ObservationJournal


def observe_symbol(client, options, account, monitor, folder, symbol, journal=None, *, entry_allowed=True):
    started = time.monotonic()
    now = datetime.now(timezone.utc)
    session = regular_session("US", now)
    snapshot = {
        "market": "US",
        "symbol": symbol,
        "now": now.isoformat(),
        "regular_session_open": session is not None,
        "quote": None,
        "source": "kis",
        "data_mode": "live_observation",
        "universe_entry_allowed": entry_allowed,
    }
    affected = [
        item["id"] for item in account.state["pending_daily"] if item["symbol"] == "US:" + symbol
    ]
    stage = "quote_http"
    request_finished = started
    try:
        if session:
            response = client.get(
                US_QUOTE, {"AUTH": "", "EXCD": options["us_exchanges"][symbol], "SYMB": symbol}
            )
            request_finished = time.monotonic()
            stage = "normalization"
            snapshot["quote"] = normalize_quote(response, "US", session)
            snapshot["now"] = wait_for_quote_time(
                snapshot["quote"], datetime.now(timezone.utc)
            ).isoformat()
        snapshot["regular_session_open"] = (
            regular_session("US", datetime.fromisoformat(snapshot["now"])) is not None
        )
        snapshot["request_seconds"] = time.monotonic() - started
        timings = getattr(client, "last_timings", {})
        snapshot["timings"] = dict(timings) if isinstance(timings, dict) else {}
        stage = "monitor_storage"
        monitor.observe(snapshot, snapshot["request_seconds"])
        stage = "account_processing"
        decision = account.observe_quote(snapshot)
        stage = "journal_storage"
        if journal:
            journal.observe(snapshot, decision, account, monitor, affected)
        stage = "decision_storage"
        record_symbol_decision(folder, snapshot, decision, account, monitor)
        path = folder / "decisions.jsonl"
        rotate_log(path)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "snapshot": snapshot,
                        "decision": decision,
                        "account_summary": account.summary(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        print(symbol, decision["action"], decision["reason"], flush=True)
    except (ValueError, OSError, RuntimeError, KeyError, sqlite3.Error) as error:
        from broker.kis import KisApiError
        elapsed = time.monotonic() - started
        diagnostic = error.diagnostic() if isinstance(error, KisApiError) else {
            "stage": stage, "category": "storage_error" if "storage" in stage else "processing_error",
            "http_status": None, "provider_code": None}
        snapshot["error"] = diagnostic
        snapshot["now"] = datetime.now(timezone.utc).isoformat()
        snapshot["regular_session_open"] = regular_session("US", datetime.fromisoformat(snapshot["now"])) is not None
        snapshot["request_seconds"] = elapsed
        timings = getattr(client, "last_timings", {})
        snapshot["timings"] = dict(timings) if isinstance(timings, dict) else {}
        snapshot["timings"]["observation_seconds"] = elapsed
        snapshot["timings"]["postprocessing_seconds"] = max(0, time.monotonic() - request_finished) if stage != "quote_http" else 0
        # 기록 실패 시 원장 기록 자체가 실패해도 이번 프로세스의 신규 매수는 먼저 차단한다.
        if "storage" in stage or stage == "account_processing":
            reason = "observation_storage_or_account_error"
            if reason not in monitor.state["buy_halts"]:
                monitor.state["buy_halts"].append(reason)
        # 기록 오류가 원래 실패 진단을 덮지 않도록 각 저장 경로를 독립적으로 시도한다.
        try:
            monitor.error("US:" + symbol, "daily_observation_failed", diagnostic, elapsed)
        except (OSError, RuntimeError, ValueError, sqlite3.Error):
            print(json.dumps({"error": diagnostic, "secondary": "monitor_storage_failed"}), flush=True)
        if journal:
            try:
                if "storage" in stage or stage == "account_processing":
                    journal.record("control", {"action": "observation_postprocessing_failed", "error": diagnostic})
                    monitor.halt("observation_storage_or_account_error")
                else:
                    journal.observe(snapshot, {"action": "WAIT", "reason": "quote_collection_error"},
                                    account, monitor, affected, lookup_error=True)
            except (OSError, RuntimeError, ValueError, sqlite3.Error):
                print(json.dumps({"error": diagnostic, "secondary": "journal_storage_failed"}), flush=True)
        # 조회 실패도 종목의 일별 로그에 남긴다. 기록 실패로 원래 오류를 덮지 않는다.
        try:
            record_symbol_decision(folder, snapshot,
                {"action": "WAIT", "reason": "observation_storage_failed" if "storage" in stage else "observation_failed"},
                account, monitor)
        except (OSError, ValueError, KeyError, TypeError):
            print(json.dumps({"error": diagnostic, "secondary": "daily_decision_log_failed"}), flush=True)




def run(watch=True):
    # 설정·인증·일봉 수집에 걸린 시간으로 늦은 시작 예외를 만들지 않는다.
    process_started_at = datetime.now(timezone.utc)
    runtime = load_run_settings()
    if runtime["broker"] != "kis" or any(market != "US" for market, symbol in runtime["symbols"]):
        raise ValueError("고정 일봉 관측은 KIS 미국 주식 전용입니다.")
    import os
    from pathlib import Path

    folder = Path(
        os.environ.get("PYTRADING_DAILY_DIR", str(DATA_ROOT / "paper-daily-frozen"))
    ).resolve()
    if not folder.is_relative_to(DATA_ROOT.resolve()):
        raise ValueError("일봉 관측 폴더는 Data 내부여야 합니다.")
    from trading.execution import load_execution, strategy_path, configure_account
    selection = load_execution()
    if selection['mode']=='live':
        raise ValueError('live_strategy_transmission_locked')
    folder = strategy_path(folder / 'account.json', selection).parent
    print('고정 일봉 체결 방식: '+selection['mode'], flush=True)
    folder.mkdir(parents=True, exist_ok=True)
    restored = (folder / "account.json").exists()
    with acquire_run_lock(folder / "run.lock"), ObservationJournal(folder) as journal:
        candidate = json.loads(
            (CONFIG_ROOT / "fixed-trend-study.json").read_text(encoding="utf-8")
        )["candidate"]
        costs = json.loads(runtime["paper_settings"].read_text(encoding="utf-8"))
        from trading.daily_risk import load_daily_risk
        risk_policy = load_daily_risk(selection['mode'])
        account = configure_account(DailyAccount(
            folder / "account.json", costs, candidate, process_started_at=process_started_at,
            maximum_trade_risk=risk_policy["maximum_trade_risk"]
        ), selection)
        monitor = OperationMonitor(folder)
        import hashlib

        versions = {
            name: hashlib.sha256((CONFIG_ROOT / name).read_bytes()).hexdigest()
            for name in ("fixed-trend-study.json", "paper.json", "safety.json", "universe.json")
        }
        versions.update(
            {
                "code:" + name: hashlib.sha256((CODE_ROOT / name).read_bytes()).hexdigest()
                for name in (
                    "trading/daily_account.py",
                    "research/algorithm_study.py",
                    "app/daily_service.py",
                    "app/universe.py", "app/universe_service.py", "broker/universe_data.py",
                )
            }
        )
        settings_snapshot = {
            name: json.loads((CONFIG_ROOT / name).read_text(encoding="utf-8"))
            for name in ("fixed-trend-study.json", "paper.json", "safety.json", "universe.json")
        }
        journal.recover_fills(account)
        journal.record(
            "startup",
            {
                "versions": versions,
                "daily_risk_policy": risk_policy,
                "settings_snapshot": settings_snapshot,
                "entry_timing": account.entry_timing(datetime.now(timezone.utc)),
                "restored_plans": account.state["pending_daily"] if restored else [],
            },
        )
        options = load_kis_settings(runtime["broker_config"])
        client = create_kis_client(runtime["env_file"], options)
        from app.runner import stop_on_service_signal

        from app.universe import selection_view
        from app.universe_service import UniverseService
        universe_service = UniverseService(runtime, options).start() if watch else None
        previous = signal.signal(signal.SIGTERM, stop_on_service_signal)
        try:
            while True:
                monitor.begin_cycle()
                journal.record("heartbeat", {})
                now = datetime.now(timezone.utc)
                required = last_closed_day(now)
                port = getattr(account, 'port', None)
                orders = list(port.manager.state['orders'].values()) if port is not None else []
                view = selection_view(runtime['symbols'], account.state, now, broker_orders=orders)
                if view['automatic']:
                    options['us_exchanges'].update(view['automatic'])
                entry_symbols = set(view['entry_symbols'])
                # 장중 추가는 관찰만 시작한다. 확정 계획을 재생성해 진입 창을 되살리지 않는다.
                signature = (tuple(view['entry_symbols']), tuple(view['management_only']), view['reason'])
                if getattr(account, '_universe_signature', None) != signature:
                    journal.record('universe', {'user_symbols':view['users'], 'automatic':view['automatic'],
                        'management_only':view['management_only'], 'reason':view['reason']})
                    account._universe_signature = signature
                # 새로운 완료 거래일만 읽고 진행 중인 당일 일봉은 제외한다.
                if account.state["last_signal_day"] != required:
                    try:
                        series = {}
                        symbols = list(
                            dict.fromkeys(
                                [symbol for market, symbol in view["entry_symbols"] if market == "US"]
                                + [key.split(":")[1] for key in account.state["positions"]]
                                + ["SPY"]
                            )
                        )
                        for symbol in symbols:
                            record, raw = collect_us_history(
                                client,
                                symbol,
                                options["us_exchanges"].get(
                                    symbol, "AMS" if symbol == "SPY" else None
                                ),
                                "1d",
                                date.fromisoformat(required) - timedelta(days=450),
                                date.fromisoformat(required),
                                maximum_pages=5,
                            )
                            if not record["collection_complete"]:
                                raise ValueError("일봉 조회 미완료")
                            source = folder / "sources" / required
                            atomic_json(source / (symbol + ".json"), record)
                            series["US:" + symbol] = prepare_daily_bars(record)
                            monitor.save()
                            # 느린 일봉 수집 중에도 기존 보유 가격 손절을 계속 확인한다.
                            for key in list(account.state["positions"]):
                                observe_symbol(
                                    client,
                                    options,
                                    account,
                                    monitor,
                                    folder,
                                    key.split(":")[1],
                                    journal, entry_allowed=("US", key.split(":")[1]) in entry_symbols,
                                )
                        proxy = series.pop("US:SPY")
                        account.plan_closed(series, proxy, datetime.now(timezone.utc))
                        sources = {
                            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in (folder / "sources" / required).glob("*.json")
                        }
                        journal.record(
                            "plan",
                            {
                                "signal_day": required,
                                "plans": account.state["pending_daily"],
                                "source_hashes": sources,
                                "versions": versions,
                                "coverage": {
                                    key: {
                                        "bars": len(bars),
                                        "last": bars[-1]["date"] if bars else None,
                                        "indicator_ready": len(bars) >= 201,
                                    }
                                    for key, bars in series.items()
                                },
                            },
                        )
                        monitor.state["errors"]["daily_feed"] = 0
                        monitor.save()
                    except (ValueError, OSError, RuntimeError, KeyError, sqlite3.Error):
                        monitor.error("daily_feed", "closed_daily_data_unavailable")
                        # 당일 필요한 일봉이 없으면 신규 진입만 막는다. 보유 가격 손절은 계속 본다.
                        monitor.halt("daily_plan_unavailable")
                        journal.record("control", {"action": "daily_plan_unavailable"})
                # 사용자 종목 계획을 먼저 준비한 뒤 장전 자동 검색이 완료되는 경우를 연결한다.
                # 장중 새 선정은 기존 계획/진입 창을 재생성하지 않고 관찰만 시작한다.
                extra = [symbol for market,symbol in view['entry_symbols'] if market=='US'
                         and 'US:'+symbol not in account.state.get('daily_reference_closes',{})]
                if (extra and account.state['last_signal_day'] == required and regular_session('US',now) is None):
                    try:
                        extra_series = {}
                        for symbol in extra:
                            record, _ = collect_us_history(client,symbol,options['us_exchanges'][symbol],'1d',
                                date.fromisoformat(required)-timedelta(days=450),date.fromisoformat(required),maximum_pages=5)
                            if not record['collection_complete']:
                                raise ValueError('additional_daily_incomplete')
                            atomic_json(folder/'sources'/required/(symbol+'.json'),record)
                            extra_series['US:'+symbol] = prepare_daily_bars(record)
                            for key in list(account.state['positions']):
                                observe_symbol(client,options,account,monitor,folder,key.split(':')[1],journal,
                                               entry_allowed=tuple(key.split(':',1)) in entry_symbols)
                        proxy = prepare_daily_bars(json.loads((folder/'sources'/required/'SPY.json').read_text(encoding='utf-8')))
                        added = account.plan_additional_closed(extra_series,proxy,datetime.now(timezone.utc))
                        account._decision_signal_context = None
                        journal.record('plan_extension',{'signal_day':required,'symbols':sorted(extra_series),'added_plan_ids':added,
                            'source_hashes':{path.name:hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in (folder/'sources'/required).glob('*.json')},'versions':versions})
                    except (ValueError,OSError,RuntimeError,KeyError,sqlite3.Error):
                        journal.record('control',{'action':'additional_daily_unavailable','symbols':extra})
                        # 추가 자료 장애 때문에 기존 사용자 계획과 보유 관리까지 무효화하지 않는다.
                held = [key.split(":")[1] for key in account.state["positions"]]
                planned = [item["symbol"].split(":")[1] for item in account.state["pending_daily"]]
                symbols = list(
                    dict.fromkeys(held + [symbol for _, symbol in view["observed_symbols"]] + planned)
                )
                for symbol in symbols:
                    observe_symbol(client, options, account, monitor, folder, symbol, journal,
                                   entry_allowed=("US", symbol) in entry_symbols)
                monitor.end_cycle(account, runtime["interval"] if watch else 0)
                journal.record("heartbeat", {})
                if not watch:
                    break
                time.sleep(runtime["interval"])
        except KeyboardInterrupt:
            print("고정 일봉 모의 관측 정상 종료", flush=True)
        finally:
            if universe_service:
                universe_service.close()
            if hasattr(account, "close"):
                account.close()
            journal.record("control", {"action": "process_stopped"})
            signal.signal(signal.SIGTERM, previous)
