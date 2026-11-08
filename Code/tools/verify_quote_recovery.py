"""운영 원장을 읽어 실제 미국 정규장 복구를 판정한다.

시세/인증/주문 요청과 계좌 변경은 하지 않는다. 자료가 부족하면 false를 반환한다.
각 종목의 연속성, 실제 전체 순회와 프로세스 이력을 함께 검사한다.
"""

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MAXIMUM_GAP_SECONDS = 180
MINIMUM_SPAN_SECONDS = 600
MINIMUM_COMPLETE_CYCLES = 3


def parse_time(value):
    """시각은 시간대가 명시된 자료만 인정한다. 로컬 시간으로 추측하지 않는다."""
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        raise ValueError("timezone_missing")
    return moment.astimezone(timezone.utc)


def session_bounds(now):
    """현지 거래일의 개장·종료 시각. 휴장·조기 종료·서머타임은 기존 달력을 쓴다."""
    from broker.sessions import calendar_for

    day = now.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    schedule = calendar_for("US", now.year).schedule.loc[day:day]
    if schedule.empty:
        return day, None, None
    row = schedule.iloc[0]
    return day, row["open"].to_pydatetime(), row["close"].to_pydatetime()


def observation_quality(payload, at):
    """저장된 age만 믿지 않고 원본 호가 시각으로 신선도를 다시 계산한다."""
    if payload.get("lookup_error"):
        return "lookup_error", None
    quote = payload.get("quote")
    if not isinstance(quote, dict) or not quote.get("available_at"):
        return "missing", None
    age = (at - parse_time(quote["available_at"])).total_seconds()
    if not 0 <= age <= 30:
        return "stale", age
    recorded_age = payload.get("quote_age_seconds")
    if recorded_age is None or abs(recorded_age - age) > 0.001:
        return "age_mismatch", age
    return "normal", age


def evaluate(folder, *, now=None, expected_symbols=None):
    """600초·전체 3회·종목별 180초 이내 간격을 요구한다. 주문 허가와는 무관하다.

    now/expected_symbols는 합성 검사 주입용이다. CLI는 실제 시각·운영 설정을 쓴다.
    과거 다른 프로세스 오류는 day_history에 남겨 재시작으로 숨겨지지 않게 한다.
    """
    clock_was_supplied = now is not None
    now = now or datetime.now(timezone.utc)
    day, opening, closing = session_bounds(now)
    state = json.loads((folder / "operations.json").read_text(encoding="utf-8"))
    since = parse_time(state["process_started_at"])
    if expected_symbols is None:
        from app.runtime import load_run_settings

        expected_symbols = {
            symbol for market, symbol in load_run_settings()["symbols"] if market == "US"
        }
    expected = sorted(set(expected_symbols))
    path = (folder / "observation-ledger.sqlite").resolve()
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        # 이벤트와 일별 진단이 동일한 SQLite 읽기 스냅샷에 속한다.
        connection.execute("BEGIN")
        events = connection.execute(
            "SELECT id,kind,at,body FROM events WHERE day=? ORDER BY at,id", (day,)
        ).fetchall()
    finally:
        connection.close()
    # 검사 시작 이후·SQLite 스냅샷 획득 이전에 기록된 행은 실제 동시 관측이다.
    # 원장 읽기 완료 시각을 상한으로 사용하며 원본 행이나 오류 이력은 수정하지 않는다.
    if not clock_was_supplied:
        now = datetime.now(timezone.utc)

    samples = []
    histories = {"regular_attempts": 0, "non_normal": 0, "starts": [], "controls": []}
    diagnostics = []
    unknown_symbols = set()
    for identifier, kind, at_text, body in events:
        at = parse_time(at_text)
        payload = json.loads(body)
        if kind == "startup":
            histories["starts"].append(at_text)
        elif kind == "control":
            # 자유문이나 계좌 정보를 포함할 수 있는 나머지 payload는 내보내지 않는다.
            action = payload.get("action", "")
            allowed = {"process_stopped", "regular_quote_outage", "regular_quote_recovered",
                       "repeated_collection_errors", "daily_plan_unavailable",
                       "observation_postprocessing_failed", "observation_storage_or_account_error"}
            histories["controls"].append({"at": at_text, "action": action if action in allowed else "other_control"})
        if kind != "observation" or payload.get("input_kind") != "live_observation":
            continue
        if not payload.get("regular_session_open") or not opening or not opening <= at < closing:
            continue
        if at > now:
            diagnostics.append("future_observation")
            continue
        quality, age = observation_quality(payload, at)
        histories["regular_attempts"] += 1
        histories["non_normal"] += quality != "normal"
        if at < since:
            continue
        symbol = payload["symbol"]
        if symbol not in expected:
            unknown_symbols.add(symbol)
        samples.append({"at": at, "symbol": symbol, "quality": quality, "age": age})

    reference = max(opening, since) if opening else since
    per_symbol = {}
    for symbol in expected:
        rows = [sample for sample in samples if sample["symbol"] == symbol]
        normal = [sample for sample in rows if sample["quality"] == "normal"]
        times = [sample["at"] for sample in normal]
        intervals = [(right - left).total_seconds() for left, right in zip(times, times[1:])]
        span = (times[-1] - times[0]).total_seconds() if times else None
        latest_age = (now - times[-1]).total_seconds() if times else None
        leading_gap = (times[0] - reference).total_seconds() if times else None
        per_symbol[symbol] = {
            "attempts": len(rows), "normal_quotes": len(normal),
            "lookup_errors": sum(row["quality"] == "lookup_error" for row in rows),
            "missing_quotes": sum(row["quality"] == "missing" for row in rows),
            "stale_quotes": sum(row["quality"] == "stale" for row in rows),
            "age_mismatches": sum(row["quality"] == "age_mismatch" for row in rows),
            "first_normal_at": times[0].isoformat() if times else None,
            "last_normal_at": times[-1].isoformat() if times else None,
            "span_seconds": span, "maximum_interval_seconds": max(intervals, default=None),
            "latest_observation_age_seconds": latest_age,
            "leading_gap_seconds": leading_gap,
            "maximum_quote_age_seconds": max((row["age"] for row in normal), default=None),
            "continuous": bool(times) and span >= MINIMUM_SPAN_SECONDS
                and len(times) >= MINIMUM_COMPLETE_CYCLES
                and max(intervals, default=0) <= MAXIMUM_GAP_SECONDS
                and 0 <= latest_age <= MAXIMUM_GAP_SECONDS
                and 0 <= leading_gap <= MAXIMUM_GAP_SECONDS
                and len(rows) == len(normal),
        }

    cycles = []
    excluded_cycles = 0
    metrics_path = folder / "cycle-metrics.jsonl"
    # 회전 전 파일도 읽되 동일 종료 시각은 중복 집계하지 않는다.
    seen = set()
    for metric_file in sorted(folder.glob("cycle-metrics.jsonl*")):
        for line in metric_file.read_text(encoding="utf-8").splitlines():
            metric = json.loads(line)
            end = parse_time(metric["at"])
            if end < since or end > now or metric["at"] in seen:
                continue
            seen.add(metric["at"])
            duration = metric["cycle_seconds"]
            if not isinstance(duration, (float, int)) or not 0 <= duration <= 86400:
                diagnostics.append("invalid_cycle_duration")
                continue
            start = end - timedelta(seconds=duration)
            if not opening or not opening <= start <= end < closing:
                excluded_cycles += 1
                continue
            # 기존 metrics에는 UTC 시작 시각이 없다. 저장 오버헤드 허용 1초를 명시한다.
            window_start = max(opening, start - timedelta(seconds=1))
            covered = [sample for sample in samples if window_start <= sample["at"] <= end]
            good = {sample["symbol"] for sample in covered if sample["quality"] == "normal"}
            complete = bool(expected) and set(expected) <= good and all(sample["quality"] == "normal" for sample in covered)
            cycles.append({"end": end.isoformat(), "inferred_start": start.isoformat(),
                           "seconds": duration, "symbols_observed": len(good & set(expected)),
                           "complete": complete})
    cycles.sort(key=lambda row: row["end"])
    for index, cycle in enumerate(cycles):
        cycle["start_interval_seconds"] = (
            (parse_time(cycle["inferred_start"]) - parse_time(cycles[index - 1]["inferred_start"])).total_seconds()
            if index else None
        )
    complete_cycles = sum(cycle["complete"] for cycle in cycles)
    regular_now = bool(opening and opening <= now < closing)
    if not regular_now:
        diagnostics.append("outside_regular_session")
    if not expected or not all(row["continuous"] for row in per_symbol.values()):
        diagnostics.append("per_symbol_continuity_incomplete")
    if complete_cycles < MINIMUM_COMPLETE_CYCLES:
        diagnostics.append("complete_regular_cycles_insufficient")
    if unknown_symbols:
        diagnostics.append("unexpected_symbols")
    # 최신 프로세스만 통과해도 당일 이전 프로세스의 실패/저장 장애를 숨기지 않는다.
    if histories["non_normal"]:
        diagnostics.append("day_contains_non_normal_observations")
    if any(row["action"] == "observation_postprocessing_failed" for row in histories["controls"]):
        diagnostics.append("day_contains_postprocessing_failure")

    return {
        "checked_at": now.isoformat(), "trading_day": day, "since": since.isoformat(),
        "input_kind": "live_observation", "regular_session_open": regular_now,
        "session_start": opening.isoformat() if opening else None,
        "session_end": closing.isoformat() if closing else None,
        "source": {"database": path.name, "events_for_day": len(events),
                   "events_sha256": hashlib.sha256(json.dumps(events, ensure_ascii=False).encode()).hexdigest(),
                   "cycle_start_precision": "inferred_from_end_minus_duration_with_1s_storage_tolerance"},
        "normal_quotes": sum(row["quality"] == "normal" for row in samples),
        "quote_errors_or_missing": sum(row["quality"] != "normal" for row in samples),
        "per_symbol": per_symbol, "regular_cycles": cycles,
        "complete_regular_cycles": complete_cycles,
        "excluded_nonregular_cycles": excluded_cycles,
        "day_history": histories, "diagnostics": sorted(set(diagnostics)),
        "buy_halts": state["buy_halts"], "quote_health": state.get("quote_health"),
        "regular_recovery_verified": not diagnostics,
        "new_orders_allowed": False, "order_execution_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        print(json.dumps(evaluate(arguments.folder.resolve()), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        parser.exit(1, "관측 자료의 누락·형식·저장 상태를 확인하세요. 복구는 미확인입니다.\n")


if __name__ == "__main__":
    main()
