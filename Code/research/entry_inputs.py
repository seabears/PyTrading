"""저장된 실제 일봉·분봉에서 인과적인 공통 돌파 사건을 만든다."""
from datetime import timedelta
from zoneinfo import ZoneInfo

from research.algorithm_study import make_features
from research.daily import prepare_daily_bars
from research.engine_backtest import prepare_record
from strategy.engine import parse_timestamp


def daily_inputs(records, periods):
    series = {symbol: prepare_daily_bars(record) for symbol, record in records.items()}
    features = {symbol: make_features(bars) for symbol, bars in series.items()}
    proxy = {row["date"]: row for row in features["SPY"]}
    dates = [bar["date"] for bar in series["SPY"]]
    for symbol, observed in series.items():
        if symbol == "SPY":
            continue
        lookup = {bar["date"]: bar for bar in observed}
        rows = {row["date"]: row for row in features[symbol]}
        # 누락 일봉을 이웃 날짜로 대체하지 않는다. SPY 거래일에 빈칸을 둔다.
        bars = [lookup.get(day) for day in dates]
        anchors = []
        for i, day in enumerate(dates):
            feature, market = rows.get(day), proxy[day]
            stage = next((name for name, period in periods.items() if period["start"] <= day <= period["end"]), None)
            if stage is None or feature is None or feature["count"] < 201:
                continue
            if market.get("ma200") is None or market["close"] <= market["ma200"]:
                continue
            if i < 55 or any(bar is None for bar in bars[i - 55:i + 1]):
                continue
            previous = bars[i - 55:i]
            level = max(bar["high"] for bar in previous)
            if bars[i]["close"] <= level:
                continue
            volume = sum(bar["volume"] for bar in previous[-20:]) / 20
            anchors.append({"index": i, "symbol": symbol, "date": day, "stage": stage,
                "period_end": periods[stage]["end"], "time_bucket": "daily",
                "level": level, "atr": feature["atr"],
                "volume_ratio": bars[i]["volume"] / volume if volume else 0,
                "event_id": "daily:" + symbol + ":" + day})
        yield symbol, bars, anchors, {"first": observed[0]["date"], "last": observed[-1]["date"], "bars": len(observed)}


def intraday_inputs(symbol, record):
    zone = ZoneInfo("America/New_York")
    for session in prepare_record(record):
        minute_lookup = {ending: candle for ending, candle in session["minutes"]}
        bars = []
        for n in range(1, session["expected_minutes"] + 1):
            ending = session["start"] + timedelta(minutes=n)
            candle = minute_lookup.get(ending)
            bars.append(None if candle is None else {"date": session["day"], **{
                name: float(candle[field]) for name, field in (("open", "openPrice"),
                    ("high", "highPrice"), ("low", "lowPrice"), ("close", "closePrice"), ("volume", "volume"))}})
        anchors = []
        completed = session["bars"]
        for j in range(20, len(completed)):
            window = completed[j - 20:j + 1]
            ends = [parse_timestamp(bar["end"]) for bar in window]
            if any(later - earlier != timedelta(minutes=5) for earlier, later in zip(ends, ends[1:])):
                continue
            latest, previous = window[-1], window[:-1]
            level = max(bar["high"] for bar in previous)
            volume = sum(bar["volume"] for bar in previous) / 20
            if latest["close"] <= level or volume <= 0 or latest["volume"] < volume * 2:
                continue
            ranges = [max(window[k]["high"] - window[k]["low"],
                          abs(window[k]["high"] - window[k - 1]["close"]),
                          abs(window[k]["low"] - window[k - 1]["close"])) for k in range(7, 21)]
            ending = ends[-1]
            i = int((ending - session["start"]).total_seconds() / 60) - 1
            local = ending.astimezone(zone)
            anchors.append({"index": i, "symbol": symbol, "date": session["day"],
                "stage": "intraday_exploratory", "period_end": session["day"],
                "time_bucket": f"{local.hour:02d}:00-{local.hour + 1:02d}:00 NY",
                "level": level, "atr": sum(ranges) / 14,
                "volume_ratio": latest["volume"] / volume,
                "signal_time": ending.isoformat(),
                "event_id": "intraday:" + symbol + ":" + ending.isoformat()})
        yield symbol, bars, anchors, {"date": session["day"], "observed_minutes": len(minute_lookup), "expected_minutes": len(bars)}
