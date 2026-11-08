"""토스 REST의 클라이언트 × API 그룹별 속도 조절.

초기 한도는 공식 가이드의 기본값이다. 서버 응답의 현재 한도가 항상 우선한다.
클라이언트 한 개를 단일 실행 흐름에서 사용한다. 다른 프로세스의 요청은 알 수 없다.
"""
import math
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

DEFAULT_GROUP_LIMITS = {
    "AUTH": 5, "MARKET_INFO": 3, "MARKET_DATA": 15,
    "MARKET_DATA_CHART": 20, "MARKET_INDICATOR_CHART": 5,
}
PATH_GROUPS = {
    "/oauth2/token": "AUTH",
    "/api/v1/market-calendar/KR": "MARKET_INFO",
    "/api/v1/market-calendar/US": "MARKET_INFO",
    "/api/v1/orderbook": "MARKET_DATA",
    "/api/v1/candles": "MARKET_DATA_CHART",
    "/api/v1/market-indicators/KOSPI/candles": "MARKET_INDICATOR_CHART",
    "/api/v1/market-indicators/KR_BOND_3Y/candles": "MARKET_INDICATOR_CHART",
}
# 시계·통신 타이밍 차이를 고려해 한도보다 10% 느리게 요청한다.
PACE_MARGIN = 1.1
MAX_BACKOFF_SECONDS = 32.0


def nonnegative_seconds(value):
    """누락·음수·비유한 값은 None. 0은 정상 헤더 값으로 받아들인다."""
    try:
        seconds = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return seconds if math.isfinite(seconds) and seconds >= 0 else None


def retry_after_seconds(value):
    """초 또는 HTTP 날짜. 잘못된 헤더는 None을 반환해 기본 백오프를 사용한다."""
    seconds = nonnegative_seconds(value)
    if seconds is not None:
        return seconds
    if value is None:
        return None
    try:
        moment = parsedate_to_datetime(value)
        if moment.tzinfo is None:
            return None
        return max(0.0, (moment - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return None


class GroupRateLimiter:
    """그룹별 다음 요청 시각·현재 한도·연속 429 횟수를 관리한다."""

    def __init__(self):
        self.groups = {
            name: {"limit": limit, "next_at": 0.0, "consecutive_429": 0,
                   "remaining": None, "reset_seconds": None}
            for name, limit in DEFAULT_GROUP_LIMITS.items()
        }

    def wait(self, path):
        group = PATH_GROUPS[path]
        delay = self.groups[group]["next_at"] - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    def acquire(self, path):
        """같은 그룹의 요청 시작을 분산한다. 다른 그룹은 독립적으로 관리한다."""
        self.wait(path)
        state = self.groups[PATH_GROUPS[path]]
        state["next_at"] = time.monotonic() + PACE_MARGIN / state["limit"]

    def observe(self, path, headers, *, limited=False):
        """정상·429 응답 모두 헤더를 읽는다. 원문과 인증 헤더는 저장하지 않는다."""
        group = PATH_GROUPS[path]
        state = self.groups[group]
        # urllib의 HTTPMessage처럼 테스트용 사전도 헤더 이름의 대소문자를 구분하지 않는다.
        headers = {str(name).lower(): value for name, value in headers.items()}
        limit = nonnegative_seconds(headers.get("x-ratelimit-limit"))
        if limit is not None and limit >= 1 and limit.is_integer():
            state["limit"] = int(limit)
        remaining = nonnegative_seconds(headers.get("x-ratelimit-remaining"))
        reset = nonnegative_seconds(headers.get("x-ratelimit-reset"))
        state.update(remaining=remaining, reset_seconds=reset)
        now = time.monotonic()
        # 서버가 한도를 낮추면 다음 요청부터 바로 반영한다.
        state["next_at"] = max(state["next_at"], now + PACE_MARGIN / state["limit"])
        if remaining is not None and remaining <= 1 and reset is not None:
            state["next_at"] = max(state["next_at"], now + reset)
        if not limited:
            state["consecutive_429"] = 0
            return None
        state["consecutive_429"] += 1
        backoff = min(MAX_BACKOFF_SECONDS, 2.0 ** min(state["consecutive_429"] - 1, 5))
        advised = retry_after_seconds(headers.get("retry-after"))
        # 서버 지정 시간보다 먼저 재시도하지 않는다. 지수 백오프에 작은 무작위 지연을 더한다.
        delay = max(backoff, advised or 0.0, reset or 0.0) + random.uniform(0.0, 0.25)
        state["next_at"] = max(state["next_at"], now + delay)
        return delay
