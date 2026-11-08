"""장외에도 읽기 전용 호가 API 지연을 진단한다. 장중 관측·체결 성능으로 해석하지 않는다."""
import json
import time
from datetime import datetime, timezone
from app.runtime import load_run_settings
from broker.kis_setup import load_kis_settings, create_kis_client
from broker.kis_market import US_QUOTE, normalize_quote
from broker.sessions import regular_session
from paths import DATA_ROOT
from app.stateio import atomic_json


def main():
    settings = load_run_settings()
    options = load_kis_settings(settings["broker_config"])
    client = create_kis_client(settings["env_file"], options)
    rows = []
    started = time.monotonic()
    for market, symbol in settings["symbols"]:
        before = time.monotonic()
        row = {"symbol": market + ":" + symbol}
        try:
            response = client.get(US_QUOTE, {"AUTH": "", "EXCD": options["us_exchanges"][symbol], "SYMB": symbol})
            quote = normalize_quote(response, "US", None)
            now = datetime.now(timezone.utc)
            row.update(session_open=regular_session("US", now) is not None, quote_at=quote["available_at"] if quote else None,
                quote_age_seconds=(now - datetime.fromisoformat(quote["available_at"])).total_seconds() if quote else None,
                received_at=now.isoformat(), success=True)
        except (RuntimeError, ValueError, KeyError, OSError) as error:
            row.update(success=False, error_type=type(error).__name__)
        row["request_seconds"] = time.monotonic() - before
        rows.append(row)
        print(row["symbol"], round(row["request_seconds"], 3), row["success"], flush=True)
    result = {"kind": "actual_read_only_http_diagnostic", "rows": rows, "total_seconds": time.monotonic() - started,
        "minute_candles_collected": False, "held_positions_measured": False, "orders_sent": 0}
    folder = DATA_ROOT / "reports/operations"
    atomic_json(folder / "quote-latency.json", result)
    print("호가 API 진단:", result["total_seconds"], "초", flush=True)
