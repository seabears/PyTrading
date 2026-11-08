"""KIS 미국 과거 시세 수집. 일봉과 분봉의 실제 제공 범위·중단 이유를 보존한다.

일봉은 MODP=1(수정주가 요청), 분봉은 원본 가격이다. 배당 재투자 수익률이 아니다.
페이지가 반복되거나 잘못된 값이 나오면 완료로 위장하지 않는다.
"""
from datetime import date, datetime, timedelta, timezone
import time
from zoneinfo import ZoneInfo

from broker.kis import KisApiError
from broker.kis_market import normalize_minute
from strategy.engine import require_number

DAILY_PATH = "/uapi/overseas-price/v1/quotations/dailyprice"
MINUTE_PATH = "/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice"


def read_history_page(client, path, parameters):
    """일시적인 연결 실패만 같은 페이지를 최대 3회 재시도한다. 권한 오류는 즉시 중단한다."""
    for attempt in range(3):
        try:
            return client.get(path, parameters)
        except KisApiError as error:
            if "연결 실패" not in str(error) or attempt == 2:
                raise
            print(f"  일시적 KIS 연결 실패 — {attempt + 1}초 대기 후 같은 페이지 재시도", flush=True)
            time.sleep(attempt + 1)


def validate_candle(candle):
    """0원·음수·NaN·가격 범위 오류를 저장 전에 차단한다."""
    values = {name: require_number(candle[name], allow_zero=name == "volume")
              for name in ("openPrice", "highPrice", "lowPrice", "closePrice", "volume")}
    if not (values["lowPrice"] <= values["openPrice"] <= values["highPrice"]
            and values["lowPrice"] <= values["closePrice"] <= values["highPrice"]):
        raise ValueError("KIS 과거 시세 OHLC 범위 오류")
    return candle


def collect_us_history(client, symbol, exchange, interval, start, end, maximum_pages=200):
    """과거 방향으로만 조회한다. 시작일 도달과 API 제공 끝을 구별해 기록한다.

    end는 현지 날짜다. 분봉도 해당 날짜 다음 날 00시 이전의 완성 봉만 저장한다.
    반환이 끝났다는 뜻과 요청한 전체 기간을 확보했다는 뜻은 서로 다르다.
    """
    if interval not in {"1d", "1m"} or start > end or not 1 <= maximum_pages <= 500:
        raise ValueError("수집 단위·날짜·최대 페이지 설정 오류")
    candles, raw_pages, rejected = {}, [], []
    before = end.strftime("%Y%m%d") if interval == "1d" else ""
    stop_reason = "page_limit"
    pages = 0
    for page in range(maximum_pages):
        parameters = {"AUTH": "", "EXCD": exchange, "SYMB": symbol}
        if interval == "1d":
            parameters.update(GUBN="0", BYMD=before, MODP="1")
        else:
            parameters.update(NMIN="1", PINC="1", NEXT="" if page == 0 else "1",
                              NREC="120", FILL="", KEYB=before)
        response = read_history_page(client, DAILY_PATH if interval == "1d" else MINUTE_PATH, parameters)
        rows = response.get("output2")
        if not isinstance(rows, list):
            raise ValueError("KIS 과거 시세 output2 목록 누락")
        # 인증 헤더·키·토큰은 담지 않는다. 재현을 위해 시세 본문만 저장한다.
        raw_pages.append({"parameters": parameters, "rows": rows})
        pages += 1
        if not rows:
            stop_reason = "api_empty_page"
            break
        oldest = None
        previous_count = len(candles)
        for row in rows:
            if interval == "1d":
                day = datetime.strptime(row["xymd"], "%Y%m%d").date()
                candle = {"timestamp": day.isoformat() + "T00:00:00-04:00",
                          "currency": "USD", "openPrice": row["open"], "highPrice": row["high"],
                          "lowPrice": row["low"], "closePrice": row["clos"], "volume": row["tvol"]}
                # 일봉은 날짜 라벨이다. 실제 체결 시각으로 해석하지 않는다.
                candle["timestamp"] = datetime.combine(day, datetime.min.time(), ZoneInfo("America/New_York")).isoformat()
                cursor = datetime.combine(day, datetime.min.time())
            else:
                candle = normalize_minute(row, "US", None)
                cursor = datetime.strptime(row["xymd"] + row["xhms"].zfill(6), "%Y%m%d%H%M%S")
                day = cursor.date()
            oldest = cursor if oldest is None else min(oldest, cursor)
            if not start <= day <= end:
                continue
            try:
                validate_candle(candle)
            except ValueError as error:
                # 원본 응답은 raw_pages에 남긴다. 오류 가격을 정상 봉처럼 고치지 않는다.
                rejected.append({"candle": candle, "reason": str(error)})
                continue
            key = candle["timestamp"]
            if key in candles and candles[key] != candle:
                raise ValueError("동일 시각의 KIS 과거 시세 값이 다름")
            candles[key] = candle
        if oldest.date() <= start:
            stop_reason = "requested_start_reached"
            break
        next_cursor = oldest - (timedelta(days=1) if interval == "1d" else timedelta(minutes=1))
        next_before = next_cursor.strftime("%Y%m%d" if interval == "1d" else "%Y%m%d%H%M%S")
        if before and next_before >= before:
            stop_reason = "api_no_progress"
            break
        before = next_before
        if (page + 1) % 25 == 0:
            print(f"  {symbol} {interval}: {page + 1}페이지 / {len(candles)}봉 수집 중", flush=True)
    record = {"origin": "kis_actual_historical_candles", "market": "US", "symbol": symbol,
              "exchange": exchange, "interval": interval, "adjusted": interval == "1d",
              "retrieved_at": datetime.now(timezone.utc).isoformat(),
              "requested_start": start.isoformat(), "requested_end": end.isoformat(),
              "pages": pages, "stop_reason": stop_reason,
              "collection_complete": stop_reason not in {"page_limit", "api_no_progress"},
              "requested_period_reached": stop_reason == "requested_start_reached",
              "rejected": rejected,
              "candles": sorted(candles.values(), key=lambda item: item["timestamp"])}
    return record, raw_pages
