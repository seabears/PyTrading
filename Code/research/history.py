"""공식 토스 과거 분봉 수집·검사·5분봉 변환. 인증값은 저장하지 않는다."""
import calendar
import json
import time
from datetime import datetime, timedelta, timezone

from broker.toss import aggregate_five_minute_bars
from strategy.engine import parse_timestamp, require_number


def load_research_settings(path):
    """잘못 수정한 설정이 무한 요청·검증 기간 겹침으로 이어지지 않게 검사한다."""
    settings = json.loads(path.read_text(encoding="utf-8"))
    required = {"history_days", "max_pages_per_symbol", "request_interval_seconds", "training_fraction",
                "validation_fraction", "minimum_sessions_per_symbol", "minimum_test_trades_per_market",
                "maximum_test_drawdown", "assumed_spread_ratio"}
    if not isinstance(settings, dict) or set(settings) != required:
        raise ValueError("research.json의 필수 설정 이름을 확인하세요.")
    for name in ("history_days", "max_pages_per_symbol", "minimum_sessions_per_symbol", "minimum_test_trades_per_market"):
        if type(settings[name]) is not int or settings[name] < 1:
            raise ValueError("연구 기간·페이지·표본 수는 양의 정수여야 합니다.")
    if settings["history_days"] > 3650 or settings["max_pages_per_symbol"] > 2000:
        raise ValueError("연구 수집 범위는 3650일·2000페이지 이하여야 합니다.")
    for name in ("training_fraction", "validation_fraction", "maximum_test_drawdown", "assumed_spread_ratio"):
        if isinstance(settings[name], bool) or not isinstance(settings[name], (int, float)):
            raise ValueError("연구 비율은 숫자로 적으세요.")
        value = require_number(settings[name])
        if value >= 1:
            raise ValueError("연구 비율은 0 초과 1 미만이어야 합니다.")
    if settings["training_fraction"] + settings["validation_fraction"] >= 1:
        raise ValueError("미사용 최종 시험 기간을 남겨야 합니다.")
    if isinstance(settings["request_interval_seconds"], bool) or not isinstance(settings["request_interval_seconds"], (int, float)):
        raise ValueError("과거 시세 요청 간격은 숫자로 적으세요.")
    if require_number(settings["request_interval_seconds"]) < 0.05:
        raise ValueError("과거 시세 요청 간격은 최소 0.05초여야 합니다.")
    return settings


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    # Windows 인덱서·백신의 순간적인 파일 잠금만 짧게 재시도한다. 계속 실패하면 숨기지 않는다.
    for attempt in range(10):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.1)


def collect_history(client, market, symbol, path, settings, now=None, interval="1m", adjusted=False):
    """페이지 수·기간을 제한한다. 중복 경계는 제거하고 응답이 반복되면 중단한다.

    매 페이지 저장하므로 중단 시 받은 자료를 잃지 않는다. 캐시는 연구 실행에서 재사용한다.
    API의 nextBefore는 inclusive이므로 시각 중복 자체는 오류가 아니다.
    """
    if interval not in {"1m", "1d"}:
        raise ValueError("과거 시세 단위는 1m 또는 1d여야 합니다.")
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=settings["history_days"])
    by_time = {}
    before = now.isoformat()
    offset = 0
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("adjusted", False) != adjusted:
            raise ValueError("기존 자료와 요청한 수정주가 설정이 다릅니다.")
        if saved.get("collection_complete") and (saved.get("stop_reason") != "page_limit" or saved["pages"] >= settings["max_pages_per_symbol"]):
            return saved
        if saved.get("interval", "1m") != interval:
            raise ValueError("기존 과거 시세와 요청 봉 단위가 다릅니다.")
        now = parse_timestamp(saved.get("requested_end", saved["retrieved_at"]))
        cutoff = parse_timestamp(saved["requested_start"])
        by_time = {parse_timestamp(row["timestamp"]).astimezone(timezone.utc).isoformat(): row for row in saved["candles"]}
        offset = saved["pages"]
        before = saved.get("next_before") or min(parse_timestamp(row["timestamp"]) for row in saved["candles"]).isoformat()
    stop_reason = "page_limit"
    remaining_pages = settings["max_pages_per_symbol"] - offset
    if remaining_pages <= 0:
        return saved
    for page_number in range(remaining_pages):
        page = client.get("/api/v1/candles", {
            "symbol": symbol, "interval": interval, "count": 200,
            "adjusted": "true" if adjusted else "false", "before": before,
        })
        candles = page.get("candles", [])
        previous_count = len(by_time)
        for candle in candles:
            end = parse_timestamp(candle["timestamp"])
            if cutoff <= end <= now:
                key = end.astimezone(timezone.utc).isoformat()
                if key in by_time and by_time[key] != candle:
                    raise ValueError("같은 분봉 시각에 서로 다른 값이 있습니다.")
                by_time[key] = candle
        if not candles:
            stop_reason = "empty_page"
        elif min(parse_timestamp(row["timestamp"]) for row in candles) < cutoff:
            stop_reason = "requested_period_reached"
        elif not page.get("nextBefore"):
            stop_reason = "last_page"
        elif len(by_time) == previous_count:
            stop_reason = "repeated_page"
        record = {"origin": "toss_actual_historical_candles", "market": market, "symbol": symbol,
                  "retrieved_at": datetime.now(timezone.utc).isoformat(), "requested_start": cutoff.isoformat(),
                  "requested_end": now.isoformat(), "interval": interval,
                  "pages": offset + page_number + 1, "stop_reason": stop_reason,
                  "next_before": page.get("nextBefore"),
                  "collection_complete": stop_reason != "page_limit" or page_number == remaining_pages - 1,
                  "adjusted": adjusted, "candles": sorted(by_time.values(), key=lambda row: parse_timestamp(row["timestamp"]))}
        write_json(path, record)
        if page_number == 0 or (page_number + 1) % 25 == 0:
            print(f"{market}:{symbol}: 과거 시세 {offset + page_number + 1}페이지 / {len(by_time)}봉 ({interval})", flush=True)
        if stop_reason != "page_limit":
            break
        next_before = parse_timestamp(page["nextBefore"])
        if next_before > parse_timestamp(before):
            raise ValueError("과거 시세 페이지가 미래 방향으로 이동했습니다.")
        before = page["nextBefore"]
        time.sleep(settings["request_interval_seconds"])
    return record


def market_timezone(market, moment):
    """2007년 이후 미국 DST 규칙으로 현지 날짜·시각을 구한다.

    Windows의 별도 tzdata 의존성을 피한다. 과거 거래소 조기 종료·휴장은 분봉 존재로만
    추정하므로 공식 역사 거래 달력 검증은 별도로 필요하며 보고서에 이 한계를 남긴다.
    """
    if market == "KR":
        return timezone(timedelta(hours=9))
    year = moment.year
    if year < 2007:
        raise ValueError("연구 시각 변환은 2007년 이후 데이터만 지원합니다.")
    march_first = datetime(year, 3, 1, tzinfo=timezone.utc)
    november_first = datetime(year, 11, 1, tzinfo=timezone.utc)
    second_sunday = 1 + (calendar.SUNDAY - march_first.weekday()) % 7 + 7
    first_sunday = 1 + (calendar.SUNDAY - november_first.weekday()) % 7
    start = datetime(year, 3, second_sunday, 7, tzinfo=timezone.utc)
    end = datetime(year, 11, first_sunday, 6, tzinfo=timezone.utc)
    return timezone(timedelta(hours=-4 if start <= moment < end else -5))


def prepare_sessions(record):
    """정규장 시각만 사용한다. 누락된 분봉으로 만든 5분봉과 부분 세션은 제외한다."""
    market = record["market"]
    expected_currency = "KRW" if market == "KR" else "USD"
    groups = {}
    for candle in record["candles"]:
        moment = parse_timestamp(candle["timestamp"])
        if candle.get("currency") != expected_currency:
            raise ValueError("과거 시세 통화와 시장이 다릅니다.")
        local = moment.astimezone(market_timezone(market, moment))
        if local.weekday() >= 5:
            continue
        day = local.date().isoformat()
        groups.setdefault(day, []).append(candle)
    sessions = []
    for day, candles in sorted(groups.items()):
        local = parse_timestamp(candles[0]["timestamp"]).astimezone(market_timezone(market, parse_timestamp(candles[0]["timestamp"])))
        start = local.replace(hour=9, minute=0 if market == "KR" else 30, second=0, microsecond=0)
        end = start.replace(hour=15 if market == "KR" else 16, minute=20 if market == "KR" else 0)
        session = {"start": start, "end": end, "id": market + ":" + day}
        bars = aggregate_five_minute_bars(candles, session, end)
        # 일반 정규장 봉이 모두 있는 세션만 비교한다. 조기 종료일도 보수적으로 제외된다.
        expected_count = int((end - start).total_seconds() / 300)
        if len(bars) != expected_count:
            continue
        by_end = {parse_timestamp(candle["timestamp"]): candle for candle in candles}
        for bar in bars:
            first_end = parse_timestamp(bar["start"]) + timedelta(minutes=1)
            bar["open"] = require_number(by_end[first_end]["openPrice"])
        sessions.append({"market": market, "symbol": record["symbol"], "date": day, "bars": bars})
    return sessions
