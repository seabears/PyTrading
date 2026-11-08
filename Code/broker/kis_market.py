"""KIS 국내·미국 분봉과 호가를 기존 판단 엔진의 공통 스냅샷으로 변환한다.

국내 KRX(J)와 미국 정규장만 관찰한다. NXT·주간·프리·애프터마켓은 제외한다.
분봉의 체결 분 시각을 구간 시작으로 보고 1분을 더해 공통 종료 시각으로 바꾼다.
진행 중인 마지막 분은 제외하며, 누락 분을 임의로 채우지 않는다.
"""
from datetime import datetime, timedelta, timezone
import time
from zoneinfo import ZoneInfo

from broker.kis import KisApiError
from broker.sessions import regular_session
from broker.toss import aggregate_five_minute_bars
from strategy.engine import require_number

KR_MINUTES = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
US_MINUTES = "/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice"
KR_QUOTE = "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn"
US_QUOTE = "/uapi/overseas-price/v1/quotations/inquire-asking-price"


def market_zone(market):
    return ZoneInfo("Asia/Seoul" if market == "KR" else "America/New_York")


def local_timestamp(day, hour, market):
    """날짜와 시각을 원본 시장 시간대로 결합한다. 잘못된 시각은 추측하지 않는다."""
    return datetime.strptime(str(day) + str(hour).zfill(6), "%Y%m%d%H%M%S").replace(tzinfo=market_zone(market))


def normalize_minute(row, market, session):
    """누적 거래량 대신 해당 분 체결량을 사용한다."""
    if market == "KR":
        day = row.get("stck_bsop_date") or session["start"].astimezone(market_zone(market)).strftime("%Y%m%d")
        start = local_timestamp(day, row["stck_cntg_hour"], market)
        opening, high, low, close, volume = (row[name] for name in ("stck_oprc", "stck_hgpr", "stck_lwpr", "stck_prpr", "cntg_vol"))
    else:
        start = local_timestamp(row["xymd"], row["xhms"], market)
        opening, high, low, close, volume = (row[name] for name in ("open", "high", "low", "last", "evol"))
    if start.second or start.microsecond:
        raise ValueError("KIS 분봉 시각이 분 경계와 일치하지 않습니다.")
    end = start + timedelta(minutes=1)
    return {"timestamp": end.isoformat(), "openPrice": opening, "highPrice": high,
            "lowPrice": low, "closePrice": close, "volume": volume, "currency": "KRW" if market == "KR" else "USD"}


def collect_minutes(client, market, symbol, exchange, session, now, maximum_pages):
    """국내 30개·미국 120개 응답을 제한된 페이지로 수집한다. 같은 분은 중복 제거한다."""
    candles = {}
    before = now.astimezone(market_zone(market))
    for page_number in range(maximum_pages):
        if market == "KR":
            response = client.get(KR_MINUTES, {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol,
                "FID_INPUT_HOUR_1": before.strftime("%H%M%S"), "FID_PW_DATA_INCU_YN": "Y", "FID_ETC_CLS_CODE": ""})
        else:
            response = client.get(US_MINUTES, {"AUTH": "", "EXCD": exchange, "SYMB": symbol,
                "NMIN": "1", "PINC": "0" if page_number == 0 else "1", "NEXT": "" if page_number == 0 else "1",
                "NREC": "120", "FILL": "", "KEYB": "" if page_number == 0 else before.strftime("%Y%m%d%H%M%S")})
        rows = response.get("output2")
        if not isinstance(rows, list):
            raise ValueError("KIS 분봉 output2가 목록이 아닙니다.")
        if not rows:
            break
        oldest = None
        previous_count = len(candles)
        for row in rows:
            candle = normalize_minute(row, market, session)
            end = datetime.fromisoformat(candle["timestamp"])
            start = end - timedelta(minutes=1)
            oldest = start if oldest is None else min(oldest, start)
            if start < session["start"] or end > now or end > session["end"]:
                continue
            key = end.astimezone(timezone.utc).isoformat()
            if key in candles and candles[key] != candle:
                raise ValueError("KIS의 동일한 완성 분봉 값이 서로 다릅니다.")
            candles[key] = candle
        # 120개면 21개 5분봉을 만들 여유가 있다. 정규장 시작까지 도달해도 중단한다.
        if len(candles) >= 120 or oldest <= session["start"] or len(candles) == previous_count:
            break
        next_before = oldest - timedelta(minutes=1)
        if next_before >= before:
            raise ValueError("KIS 분봉 페이지 시각이 이전으로 이동하지 않습니다.")
        before = next_before
    return list(candles.values())


def one_object(value):
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value if isinstance(value, dict) else {}


def normalize_quote(response, market, session):
    """원본 호가 시각만 사용한다. 시각 누락·빈 호가는 매매 대기로 돌린다."""
    metadata = one_object(response.get("output1"))
    if market == "KR":
        hour = metadata.get("aspr_acpt_hour")
        if not hour:
            return None
        day = session["start"].astimezone(market_zone(market)).strftime("%Y%m%d")
        stamp = local_timestamp(day, hour, market)
        levels = metadata
        bid_name, ask_name, bid_volume, ask_volume = "bidp1", "askp1", "bidp_rsqn1", "askp_rsqn1"
    else:
        if not metadata.get("dymd") or not metadata.get("dhms"):
            return None
        # 미국 분봉 xymd/xhms는 현지 시각이지만 호가 dymd/dhms는 한국 시각이다.
        # 실제 응답의 분봉 khms와 호가 dhms를 대조해 확인했다.
        stamp = local_timestamp(metadata["dymd"], metadata["dhms"], "KR")
        levels = {}
        for name in ("output2", "output3", "output1"):
            item = one_object(response.get(name))
            if "pbid1" in item and "pask1" in item:
                levels = item
                break
        bid_name, ask_name, bid_volume, ask_volume = "pbid1", "pask1", "vbid1", "vask1"
        if metadata.get("curr") and metadata["curr"] != "USD":
            raise ValueError("미국 호가 통화가 USD가 아닙니다.")
    if not levels or not levels.get(bid_name) or not levels.get(ask_name):
        return None
    if require_number(levels.get(bid_volume, 0), allow_zero=True) == 0 or require_number(levels.get(ask_volume, 0), allow_zero=True) == 0:
        return None
    bid = require_number(levels[bid_name], allow_zero=True)
    ask = require_number(levels[ask_name], allow_zero=True)
    if bid == 0 or ask == 0:
        return None
    if bid > ask:
        raise ValueError("KIS 매수 호가가 매도 호가보다 높습니다.")
    return {"available_at": stamp.isoformat(), "bid": bid, "ask": ask}


def wait_for_quote_time(quote, now):
    """서버 시계가 최대 2초 앞선 경우 실제 시간이 따라잡을 때까지 기다린다.

    판단 시각을 임의로 미래로 바꾸지 않는다. 더 먼 미래·오래된 호가는 엔진이 차단한다.
    """
    if quote:
        lead = (datetime.fromisoformat(quote["available_at"]) - now).total_seconds()
        if 0 < lead <= 2:
            time.sleep(lead + 0.05)
            return datetime.now(timezone.utc)
    return now


def collect_snapshot(client, market, symbol, options):
    now = datetime.now(timezone.utc)
    session = regular_session(market, now)
    snapshot = {"market": market, "symbol": symbol, "now": now.isoformat(), "source": "kis",
        "regular_session_open": session is not None, "risk_budget_available": False,
        "pending_order": False, "position": None, "news_events": [], "bars": [], "quote": None}
    if session is None:
        return snapshot
    exchange = options["us_exchanges"].get(symbol) if market == "US" else "KRX"
    if not exchange:
        raise KisApiError(f"US:{symbol}의 KIS 거래소가 미설정입니다. 상장·지원 여부를 확인한 뒤 Config/kis.json에 추가하세요.")
    snapshot["session_id"] = session["id"]
    candles = collect_minutes(client, market, symbol, exchange, session, now, options["maximum_minute_pages"])
    received = datetime.now(timezone.utc)
    snapshot["bars"] = aggregate_five_minute_bars(candles, session, received)
    if market == "KR":
        response = client.get(KR_QUOTE, {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol})
    else:
        response = client.get(US_QUOTE, {"AUTH": "", "EXCD": exchange, "SYMB": symbol})
    snapshot["quote"] = normalize_quote(response, market, session)
    current = wait_for_quote_time(snapshot["quote"], datetime.now(timezone.utc))
    snapshot["now"] = current.isoformat()
    # 수집 중 장이 끝났으면 이미 받은 호가로 신규 거래를 판단하지 않는다.
    snapshot["regular_session_open"] = session["start"] <= current < session["end"]
    return snapshot
