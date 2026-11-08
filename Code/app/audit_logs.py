"""인증 이벤트 최근100건과 거래일·종목별 판단 로그. 비밀값은 입력받지 않는다.

토큰 재사용은 갱신이 아니므로 이력을 추가하지 않는다. 일별 판단은 별도 삭제
제한 없이 보존하며, SQLite 관측 원장과 기존 회전 로그도 계속 사용한다.
"""
import hashlib
import json
import math
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.runtime import acquire_run_lock, AlreadyRunningError
from app.stateio import atomic_json
from paths import DATA_ROOT

TOKEN_EVENT_LIMIT = 100  # 성공·실패 합계100건. 101번째부터 가장 오래된 한 건씩 제거한다.
SAFE_CODES = {"EGW00103", "EGW00121", "EGW00123", "EGW00201", "EGW00133"}
SAFE_CATEGORIES = {"api_error", "http_error", "connection_error", "rate_limit",
                   "authentication_expired", "authentication_cooldown", "storage_error",
                   "processing_error", "response_contract_error"}


def safe_code(value, fallback="unclassified"):
    """서버 자유문·경로·인증 문자열을 사유 코드로 저장하지 않는다."""
    return value if isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", value) else fallback


def safe_number(value):
    return value if type(value) in {int, float} and math.isfinite(value) else None


def safe_timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value)
        return moment.isoformat() if moment.tzinfo is not None else None
    except ValueError:
        return None


def safe_error(value):
    """허용된 진단 필드만 남긴다. 예외 문자열·응답 본문은 받지 않는다."""
    value = value if isinstance(value, dict) else {}
    return {
        "stage": safe_code(value.get("stage")),
        "category": value.get("category") if value.get("category") in SAFE_CATEGORIES else "api_error",
        "http_status": value.get("http_status") if type(value.get("http_status")) is int and 100 <= value["http_status"] <= 599 else None,
        "provider_code": value.get("provider_code") if value.get("provider_code") in SAFE_CODES else None,
    }


def token_event_path(cache_path):
    """운영 캐시는 프로젝트 공통100건, 외부/시험 캐시는 그 폴더 안에 격리한다."""
    if cache_path is None:
        return None  # 영속 캐시가 없는 메모리 전용 시험 클라이언트는 기록하지 않는다.
    cache_path = Path(cache_path).resolve()
    if cache_path.is_relative_to(DATA_ROOT.resolve()):
        return DATA_ROOT / "logs" / "token-refresh.json"
    return cache_path.parent / "token-refresh.json"


def append_token_event(path, event):
    """프로세스 간 잠금+원자 교체. 실패 시 기존 정상 이력을 그대로 둔다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = None
    for attempt in range(20):
        try:
            lock = acquire_run_lock(path.with_suffix(".lock"))
            break
        except AlreadyRunningError:
            if attempt == 19:
                raise
            time.sleep(0.01)
    try:
        history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        if not isinstance(history, list) or any(not isinstance(row, dict) or not row.get("event_id") for row in history):
            raise ValueError("token_history_invalid")
        # 저장 후 같은 보류 이벤트가 다시 전달돼도 중복 기록하지 않는다.
        if any(row["event_id"] == event["event_id"] for row in history):
            return
        atomic_json(path, [*history[-(TOKEN_EVENT_LIMIT - 1):], event])
    finally:
        if lock:
            lock.close()


def token_event(environment, issued_at=None, expires_at=None, error=None):
    """이 함수에는 키·토큰·계좌번호 인자가 없다. 발급 시각과 오류 코드만 만든다."""
    now = datetime.now(timezone.utc)
    return {
        "event_id": uuid.uuid4().hex,
        "at": now.isoformat(),
        "at_kst": now.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
        "environment": environment if environment in {"prod", "vps"} else "unknown",
        "event": "token_issue_failed" if error else "token_issued",
        "issued_at": datetime.fromtimestamp(issued_at, timezone.utc).isoformat() if issued_at is not None else None,
        "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat() if expires_at is not None else None,
        "error": safe_error(error) if error else None,
    }


def signal_context(account, folder, symbol):
    """저장된 확정 일봉만 동일 함수로 재계산하는 진단. 계획·주문은 만들지 않는다."""
    day = account.state.get("last_signal_day")
    if not day or not hasattr(account, "candidate"):
        return {"status": "unavailable", "reason": "closed_signal_source_unavailable"}
    cache_key = (day, account.state.get("daily_candidate_hash"))
    cached = getattr(account, "_decision_signal_context", None)
    if cached is None or cached[0] != cache_key:
        from research.daily import prepare_daily_bars
        from research.algorithm_study import make_features, signal
        contexts = {}
        source = Path(folder) / "sources" / day
        try:
            proxy_path = source / "SPY.json"
            proxy_bars = prepare_daily_bars(json.loads(proxy_path.read_text(encoding="utf-8")))
            if proxy_bars[-1]["date"] != day:
                raise ValueError("diagnostic_source_day_mismatch")
            proxy = make_features(proxy_bars)[-1]
            market_pass = proxy["ma200"] is not None and proxy["close"] > proxy["ma200"]
            candidate = account.candidate
            for path in sorted(source.glob("*.json")):
                if path.name == "SPY.json":
                    continue
                bars = prepare_daily_bars(json.loads(path.read_text(encoding="utf-8")))
                if bars[-1]["date"] != day:
                    raise ValueError("diagnostic_source_day_mismatch")
                feature = make_features(bars)[-1]
                detail = signal(feature, candidate["family"], candidate["strategy"])
                ready = feature["count"] >= max(201, candidate["strategy"]["slow_ma"] + 1)
                valid = bool(feature["atr"]) and bool(feature["volatility"])
                if not ready:
                    reason = "insufficient_indicator_history"
                elif not valid:
                    reason = "indicator_unavailable"
                elif not detail["enter"]:
                    reason = "entry_signal_not_met"
                elif candidate["market_filter"] and not market_pass:
                    reason = "market_filter_not_met"
                else:
                    reason = "entry_candidate"
                contexts[path.stem] = {
                    "status": "available", "source_kind": "stored_closed_daily_diagnostic_replay",
                    "diagnostic_calculated_at": datetime.now(timezone.utc).isoformat(),
                    "signal_day": day,
                    "original_plan_calculated_at": safe_timestamp(account.state.get("last_signal_observed_at")),
                    "bars": feature["count"], "required_bars": max(201, candidate["strategy"]["slow_ma"] + 1),
                    "close": feature["close"],
                    "prior_breakout_high": feature.get("prior_high" + str(candidate["strategy"]["breakout_days"])),
                    "breakout_sessions": candidate["strategy"]["breakout_days"],
                    "indicator_ready": ready and valid, "entry_signal": bool(detail["enter"]),
                    "market_filter_pass": market_pass, "market_filter_enabled": candidate["market_filter"],
                    "spy_close": proxy["close"], "spy_ma200": proxy["ma200"],
                    "reason": reason, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "proxy_source_sha256": hashlib.sha256(proxy_path.read_bytes()).hexdigest(),
                }
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            # 진단 원본이 없다고 매매 판단을 바꾸지 않는다. 자료 누락을 그대로 표시한다.
            contexts = {}
        cached = (cache_key, contexts)
        account._decision_signal_context = cached
    return cached[1].get(symbol, {"status": "unavailable", "reason": "closed_signal_source_unavailable"})


def record_symbol_decision(folder, snapshot, decision, account, monitor):
    """미국 현지 날짜/종목.jsonl. 허용된 수치·고정 코드로 판단을 설명한다."""
    market, symbol = snapshot.get("market"), snapshot.get("symbol")
    if market != "US" or not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,15}", symbol):
        raise ValueError("decision_log_symbol_invalid")
    stamp = safe_timestamp(snapshot.get("now"))
    if stamp is None:
        raise ValueError("decision_log_time_invalid")
    now = datetime.fromisoformat(stamp)
    day = now.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    path = Path(folder) / "logs" / "decisions" / ("US-" + day) / (symbol + ".jsonl")
    quote = snapshot.get("quote") or {}
    readiness = account.state.get("broker_readiness") or {}
    posttrade = readiness.get("posttrade") or {}
    position = account.state.get("positions", {}).get("US:" + symbol, {})
    row = {
        "at": stamp, "at_kst": now.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
        "trading_day": day, "symbol": symbol, "market": market,
        "action": decision.get("action") if decision.get("action") in {"BUY", "SELL", "WAIT", "HOLD"} else "WAIT",
        "reason": safe_code(decision.get("reason")),
        "mode": getattr(account, "execution_mode", "internal_paper"),
        "input_kind": snapshot.get("data_mode") if snapshot.get("data_mode") in {"live_observation", "historical_replay"} else "synthetic_or_unspecified",
        "regular_session_open": snapshot.get("regular_session_open") is True,
        "bid": safe_number(quote.get("bid")), "ask": safe_number(quote.get("ask")),
        "quote_at": safe_timestamp(quote.get("available_at")),
        "strategy_position_quantity": safe_number(position.get("quantity")),
        "buy_halts": [safe_code(reason) for reason in monitor.state.get("buy_halts", [])],
        "operational_buy_block": snapshot.get("operational_buy_block") is True,
        "broker_observed_at": safe_timestamp(readiness.get("as_of")),
        "new_orders_allowed": readiness.get("new_orders_allowed") if type(readiness.get("new_orders_allowed")) is bool else None,
        "risk_reason": safe_code((readiness.get("risk_resolution") or {}).get("reason")),
        "cost_phase": safe_code(posttrade.get("phase", "").lower()),
        "pending_cost_order_count": safe_number(posttrade.get("pending_cost_order_count")),
        "strategy_action": decision.get("strategy_action") if decision.get("strategy_action") in {"BUY", "SELL"} else None,
        "strategy_quantity": safe_number(decision.get("strategy_quantity")),
        "error": safe_error(snapshot["error"]) if snapshot.get("error") else None,
        "signal": signal_context(account, folder, symbol),
    }
    row["event_id"] = hashlib.sha256((stamp + ":" + symbol + ":" + row["reason"]).encode()).hexdigest()
    encoded = json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    # 기존 마지막 줄이 불완전하면 덮어쓰지 않고 저장 오류로 알린다. SQLite 원장은 남는다.
    if path.exists() and path.stat().st_size:
        with path.open("rb") as stream:
            stream.seek(-1, 2)
            if stream.read(1) != b"\n":
                raise OSError("decision_log_incomplete_tail")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(encoded)
    return path
