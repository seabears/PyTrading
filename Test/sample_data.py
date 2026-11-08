"""모든 기능 테스트가 공유하는 합성 시세 입력. 실제 시장 데이터가 아니다."""
import copy
from datetime import datetime, timedelta, timezone
from strategy.engine import parse_timestamp


def sample(market="US"):
    now = datetime(2026, 10, 9, 16, 0, tzinfo=timezone.utc)
    bars = []
    for i in range(21):
        end = now - timedelta(minutes=(20 - i) * 5)
        bars.append({"start": (end - timedelta(minutes=5)).isoformat(), "end": end.isoformat(),
                     "available_at": end.isoformat(), "complete": True, "session_id": "demo",
                     "low": 99, "high": 102 if i == 20 else 100,
                     "close": 101 if i == 20 else 99.5, "volume": 250 if i == 20 else 100})
    symbol = "DEMO_US" if market == "US" else "DEMO_KR"
    return {"now": now.isoformat(), "market": market, "symbol": symbol, "session_id": "demo",
            "regular_session_open": True, "risk_budget_available": True, "pending_order": False,
            "quote": {"available_at": now.isoformat(), "bid": 100.9, "ask": 101}, "bars": bars,
            "news_events": [{"market": market, "symbol": symbol, "event_id": "demo-event",
                             "available_at": (now - timedelta(minutes=10)).isoformat(),
                             "kind": "earnings_guidance_raised", "confirmed": True,
                             "source_verified": True}]}


def later(snapshot, seconds=60, bid=None):
    changed = copy.deepcopy(snapshot)
    now = parse_timestamp(snapshot["now"]) + timedelta(seconds=seconds)
    changed["now"] = now.isoformat()
    changed["quote"]["available_at"] = now.isoformat()
    if bid is not None:
        changed["quote"].update(bid=bid, ask=bid + 0.1)
    return changed


