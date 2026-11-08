"""토스 공식 Open API의 읽기 전용 시세 연결.

실행: python main.py / 개별 연결 확인: python main.py --test broker-live
지속 실행과 설정은 app/runner.py, ../Config/settings.json에서 관리한다.
인증: ../Config/settings.json의 env_file이 가리키는 KEY=VALUE 파일을 사용한다.

계좌·주문 API는 호출하지 않는다. 결과는 관찰용이며 위험 예산은 항상 False다.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from strategy.engine import parse_timestamp, require_number

from broker.rate_limits import GroupRateLimiter, PATH_GROUPS, retry_after_seconds

CALENDAR_CACHE_SECONDS = 30.0

API_BASE = "https://openapi.tossinvest.com"
# 호출할 수 있는 API를 명시적으로 제한한다. 주문·계좌 경로는 목록에 없다.
READ_PATHS = {
    "/api/v1/market-indicators/KOSPI/candles",
    "/api/v1/market-indicators/KR_BOND_3Y/candles",
    "/api/v1/orderbook", "/api/v1/candles",
    "/api/v1/market-calendar/KR", "/api/v1/market-calendar/US",
}


class TossApiError(RuntimeError):
    """응답 본문이나 비밀키가 포함되지 않는 사용자 안내용 오류."""


class TossRateLimitError(TossApiError):
    """429는 일반 입력 오류와 구분해 제한된 재시도에만 사용한다."""


def read_credentials_file(env_file: Path) -> tuple[str, str]:
    """지정한 env 파일에서 두 인증값을 읽는다. 내용을 실행하거나 출력하지 않는다.

    지원: KEY=VALUE, 빈 줄, #으로 시작하는 주석, 값 전체를 감싼 작은/큰따옴표.
    UTF-8 파일과 Windows 메모장의 UTF-8 BOM을 모두 읽는다.
    환경변수 치환·명령 실행·백슬래시 이스케이프 변환은 수행하지 않는다.
    파일 지정 시 그 파일만 사용하며 누락값을 환경변수로 채우지 않는다.
    """
    try:
        contents = env_file.expanduser().read_text(encoding="utf-8-sig")
    except OSError:
        raise TossApiError("env 파일을 읽을 수 없습니다. 경로와 읽기 권한을 확인하세요.") from None
    except UnicodeError:
        raise TossApiError("env 파일을 UTF-8 형식으로 저장하세요.") from None

    required_names = {"TOSS_CLIENT_ID", "TOSS_CLIENT_SECRET"}
    credentials: dict[str, str] = {}
    for line_number, original_line in enumerate(contents.splitlines(), start=1):
        line = original_line.strip()
        if not line or line.startswith("#"):
            continue
        # 값에 =가 들어가도 첫 번째 =에서만 나누므로 원래 값이 유지된다.
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise TossApiError(f"env 파일 {line_number}행은 KEY=VALUE 형식이어야 합니다.")
        if name not in required_names:
            continue
        if name in credentials:
            raise TossApiError(f"env 파일에서 {name}이 중복됐습니다.")
        value = value.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise TossApiError(f"env 파일 {line_number}행의 따옴표가 닫히지 않았습니다.")
            value = value[1:-1]
        if not value.strip():
            raise TossApiError(f"env 파일의 {name} 값이 비어 있습니다.")
        credentials[name] = value

    if required_names - credentials.keys():
        raise TossApiError("env 파일에 TOSS_CLIENT_ID와 TOSS_CLIENT_SECRET이 모두 필요합니다.")
    return credentials["TOSS_CLIENT_ID"], credentials["TOSS_CLIENT_SECRET"]


def read_credentials(prompt_if_missing: bool, env_file: Path | None = None) -> tuple[str, str]:
    """지정한 env 파일, 환경변수, 요청된 비공개 입력 순서로 인증값을 읽는다.

    입력값은 Python 메모리에만 둔다. CMD의 set 명령이나 임시 파일로 전달하지 않는다.
    입력 숨김이 불가능한 터미널에서는 표시되는 입력으로 대체하지 않고 중단한다.
    """
    if env_file is not None:
        return read_credentials_file(env_file)

    client_id = os.environ.get("TOSS_CLIENT_ID", "").strip()
    client_secret = os.environ.get("TOSS_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        return client_id, client_secret
    if not prompt_if_missing or not sys.stdin.isatty():
        raise TossApiError("인증 정보가 없습니다. ../Config/settings.json의 env_file과 인증 파일을 확인하세요.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            if not client_id:
                client_id = getpass.getpass("Toss client_id (hidden): ").strip()
            if not client_secret:
                client_secret = getpass.getpass("Toss client_secret (hidden): ").strip()
    except (getpass.GetPassWarning, EOFError):
        raise TossApiError("비공개 입력이 불가능합니다. 별도의 CMD 터미널에서 실행하세요.") from None

    if not client_id or not client_secret:
        raise TossApiError("client_id와 client_secret을 모두 입력해야 합니다.")
    return client_id, client_secret


class TossMarketClient:
    """토큰은 메모리에만 저장하고 같은 프로세스에서 만료 직전까지 재사용한다."""

    def __init__(self, client_id: str | None = None, client_secret: str | None = None) -> None:
        # 직접 생성하는 코드와 기존 환경변수 방식도 계속 지원한다.
        self.client_id = (client_id if client_id is not None else os.environ.get("TOSS_CLIENT_ID", "")).strip()
        self.client_secret = (client_secret if client_secret is not None else os.environ.get("TOSS_CLIENT_SECRET", "")).strip()
        if not self.client_id or not self.client_secret:
            raise TossApiError("인증 정보가 없습니다. ../Config/settings.json의 env_file과 인증 파일을 확인하세요.")
        self.access_token = ""
        self.token_valid_until = 0.0
        self.rate_limiter = GroupRateLimiter()
        self.calendar_cache = {}

    def _request(self, request: urllib.request.Request) -> dict[str, Any]:
        """모든 요청의 그룹 한도를 관리한다. 오류 본문·인증값은 출력하지 않는다."""
        request_path = urllib.parse.urlsplit(request.full_url).path
        self.rate_limiter.acquire(request_path)
        stage = "토큰 발급" if request_path == "/oauth2/token" else "시세 조회"
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                self.rate_limiter.observe(request_path, getattr(response, "headers", {}))
                payload = json.load(response)
                if not isinstance(payload, dict):
                    raise ValueError("JSON 객체 응답이 아닙니다.")
                return payload
        except urllib.error.HTTPError as error:
            try:
                if error.code == 429:
                    delay = self.rate_limiter.observe(request_path, error.headers or {}, limited=True)
                    group = PATH_GROUPS[request_path]
                    raise TossRateLimitError(
                        f"HTTP 429 [{stage}/{group}]: 호출 한도 초과. 다음 요청 전 {delay:.2f}초 대기합니다."
                    ) from None
                if error.code == 403 and request_path == "/oauth2/token":
                    raise TossApiError(
                        "HTTP 403 [토큰 발급]: 호출 IP가 허용되지 않았습니다. "
                        "토스증권 WTS 설정 > Open API > 허용 IP 관리에서 "
                        "이 PC의 현재 공인 IP를 등록하세요. VPN·프록시·핫스팟 사용 여부도 확인하세요."
                    ) from None
                guidance = {
                    400: "요청 형식 또는 입력 종목을 확인하세요.",
                    401: "인증 정보·토큰 만료·다른 프로그램의 토큰 재발급을 확인하세요.",
                    403: "토스 Open API 권한과 허용 IP 설정을 확인하세요.",
                    404: "요청 종목 또는 API 경로를 확인하세요.",
                }
                if error.code == 401 and request_path == "/oauth2/token":
                    message = "client_id·client_secret 또는 클라이언트 활성 상태를 확인하세요."
                else:
                    message = guidance.get(error.code, "토스 API 상태를 확인하세요.")
                raise TossApiError(f"HTTP {error.code} [{stage}]: {message}") from None
            finally:
                error.close()
        except (urllib.error.URLError, TimeoutError, OSError):
            raise TossApiError("토스 API 연결 실패: 인터넷·DNS·방화벽을 확인하세요.") from None
        except (ValueError, UnicodeError):
            raise TossApiError("토스 API 응답을 JSON 객체로 읽을 수 없습니다.") from None

    def authenticate(self) -> None:
        """공식 OAuth2 Client Credentials 방식. 재발급은 기존 토큰을 무효화할 수 있다."""
        form = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }).encode("utf-8")
        request = urllib.request.Request(
            API_BASE + "/oauth2/token", data=form, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = self._request(request)
        token = response.get("access_token")
        lifetime = response.get("expires_in")
        if not isinstance(token, str) or not token:
            raise TossApiError("토큰 발급 응답에 access_token이 없습니다.")
        token_type = response.get("token_type")
        if not isinstance(token_type, str) or token_type.lower() != "bearer":
            raise TossApiError("토큰 발급 응답의 token_type이 Bearer가 아닙니다.")
        if type(lifetime) is not int or lifetime <= 0:
            raise TossApiError("토큰 발급 응답의 유효 시간이 잘못됐습니다.")
        self.access_token = token
        # 스펙은 양의 정수 유효 시간이다. 60초 이하의 정상 토큰도 허용한다.
        margin = min(60.0, lifetime * 0.1)
        self.token_valid_until = time.monotonic() + lifetime - margin

    def get(self, path: str, parameters: dict[str, Any] | None = None) -> Any:
        """허용된 시세 GET만 호출하고 공통 envelope의 result를 반환한다."""
        if path not in READ_PATHS:
            raise TossApiError("허용되지 않은 API 경로입니다.")
        # 같은 시장의 장 시간을 종목마다 다시 요청하지 않는다. 호가·봉은 캐시하지 않는다.
        cache_key = path if path.startswith("/api/v1/market-calendar/") and not parameters else None
        cached = self.calendar_cache.get(cache_key) if cache_key else None
        if cached and time.monotonic() < cached[0]:
            return cached[1]
        query = urllib.parse.urlencode(parameters or {})
        url = API_BASE + path + ("?" + query if query else "")
        # 대기 중 토큰이 만료될 수 있으므로 대기를 끝낸 뒤 헤더를 다시 만든다.
        # 읽기 전용 GET만 한 번 재시도한다. 두 번째 429는 호출자에게 전달한다.
        for attempt in range(2):
            self.rate_limiter.wait(path)
            if time.monotonic() >= self.token_valid_until:
                self.authenticate()
            request = urllib.request.Request(url, headers={
                "Authorization": "Bearer " + self.access_token,
                "Accept": "application/json",
            })
            try:
                response = self._request(request)
                break
            except TossRateLimitError as error:
                if attempt == 1:
                    raise
                print(f"{error} / 시세 요청을 한 번 재시도합니다.", flush=True)
        if "result" not in response:
            raise TossApiError("API 응답에 result가 없습니다.")
        if cache_key:
            self.calendar_cache[cache_key] = (time.monotonic() + CALENDAR_CACHE_SECONDS, response["result"])
        return response["result"]


def find_regular_session(calendar: dict, market: str, now: datetime) -> dict | None:
    """API의 장 시간을 사용한다. 미국 서머타임이나 한국 자정 경계를 직접 추측하지 않는다."""
    for name in ("today", "previousBusinessDay", "nextBusinessDay"):
        day = calendar.get(name)
        if not day:
            continue
        hours = day.get("integrated") if market == "KR" else day
        session = hours.get("regularMarket") if hours else None
        if not session:
            continue
        start = parse_timestamp(session["startTime"])
        end = parse_timestamp(session["endTime"])
        # 국내 종가 단일가 구간은 초기 전략의 관찰 시간에서 제외한다.
        auction_start = session.get("singlePriceAuctionStartTime")
        if auction_start:
            end = min(end, parse_timestamp(auction_start))
        if start <= now < end:
            return {"start": start, "end": end, "id": market + ":" + day["date"]}
    return None


def aggregate_five_minute_bars(candles: list[dict], session: dict, received_at: datetime) -> list[dict]:
    """토스 1분봉 5개를 합친다. timestamp는 공식 스키마상 봉 종료 시각이다.

    누락·중복 1분봉이 있거나 아직 끝나지 않은 묶음은 건너뛴다.
    세션 시작을 기준으로 묶으므로 프리·애프터마켓 체결이 섞이지 않는다.
    """
    minute = timedelta(minutes=1)
    five_minutes = timedelta(minutes=5)
    groups: dict[int, list[tuple[datetime, dict]]] = defaultdict(list)
    for candle in candles:
        end = parse_timestamp(candle["timestamp"])
        start = end - minute
        if start < session["start"] or end > session["end"] or end > received_at:
            continue
        elapsed_seconds = (start - session["start"]).total_seconds()
        if elapsed_seconds % 60 != 0:
            raise ValueError("1분봉 시각이 분 경계와 일치하지 않습니다.")
        group_number = int(elapsed_seconds // 300)
        groups[group_number].append((end, candle))

    bars = []
    for group_number, members in sorted(groups.items()):
        group_start = session["start"] + group_number * five_minutes
        group_end = group_start + five_minutes
        members.sort(key=lambda pair: pair[0])
        expected_ends = [group_start + (index + 1) * minute for index in range(5)]
        if [end for end, _ in members] != expected_ends:
            continue
        currencies = {candle["currency"] for _, candle in members}
        if len(currencies) != 1:
            raise ValueError("봉의 통화가 서로 다릅니다.")
        highs, lows, volumes = [], [], []
        for _, candle in members:
            high = require_number(candle["highPrice"])
            low = require_number(candle["lowPrice"])
            close = require_number(candle["closePrice"])
            opening = require_number(candle["openPrice"])
            if not low <= close <= high or not low <= opening <= high:
                raise ValueError("1분봉 가격 범위가 잘못됐습니다.")
            highs.append(high)
            lows.append(low)
            volumes.append(require_number(candle["volume"], allow_zero=True))
        bars.append({
            "start": group_start.isoformat(), "end": group_end.isoformat(),
            "available_at": received_at.isoformat(), "complete": True,
            "session_id": session["id"], "high": max(highs), "low": min(lows),
            "close": float(members[-1][1]["closePrice"]), "volume": sum(volumes),
        })
    return bars


def collect_snapshot(client: TossMarketClient, market: str, symbol: str) -> dict:
    """한 종목을 수집한다. 현재 단계는 실제 계좌를 모르므로 진입 예산을 허용하지 않는다."""
    calendar = client.get("/api/v1/market-calendar/" + market)
    now = datetime.now(timezone.utc)
    session = find_regular_session(calendar, market, now)
    snapshot = {
        "market": market, "symbol": symbol, "now": now.isoformat(),
        "regular_session_open": session is not None,
        "risk_budget_available": False, "pending_order": False,
        "position": None, "news_events": [], "bars": [],
    }
    if session is None:
        return snapshot

    # 과거 봉을 먼저 수집하고 현재 호가는 마지막에 읽어 지연을 줄인다.
    page = client.get("/api/v1/candles", {
        "symbol": symbol, "interval": "1m", "count": 200, "adjusted": "false",
    })
    candles_received_at = datetime.now(timezone.utc)
    bars = aggregate_five_minute_bars(page["candles"], session, candles_received_at)
    orderbook = client.get("/api/v1/orderbook", {"symbol": symbol})
    snapshot["now"] = datetime.now(timezone.utc).isoformat()
    snapshot["session_id"] = session["id"]
    snapshot["bars"] = bars
    expected_currency = "KRW" if market == "KR" else "USD"
    if orderbook.get("currency") != expected_currency:
        raise ValueError("입력 시장과 호가 통화가 다릅니다.")
    if not orderbook.get("timestamp") or not orderbook.get("asks") or not orderbook.get("bids"):
        # timestamp=null과 빈 호가는 스펙에서 허용하는 '미제공' 응답이다.
        # 수신 시각을 대신 넣으면 오래된 호가로 매매하므로 명시적으로 대기한다.
        snapshot["quote"] = None
        return snapshot
    # 응답 정렬을 믿는 대신 양수 잔량 중 최선 가격을 선택한다.
    asks = [require_number(row["price"]) for row in orderbook["asks"] if require_number(row["volume"], allow_zero=True) > 0]
    bids = [require_number(row["price"]) for row in orderbook["bids"] if require_number(row["volume"], allow_zero=True) > 0]
    if not asks or not bids:
        snapshot["quote"] = None
        return snapshot
    snapshot["quote"] = {
        # 수신 시간이 아니라 원본 데이터 시각으로 신선도를 검사한다.
        "available_at": orderbook["timestamp"], "bid": max(bids), "ask": min(asks),
    }
    return snapshot


def parse_symbol(value: str) -> tuple[str, str]:
    """예: KR:005930, US:AAPL. 임의 URL이나 계좌 API 입력을 허용하지 않는다."""
    match = re.fullmatch(r"(KR|US):([A-Za-z0-9.\-]+)", value.upper())
    if not match:
        raise argparse.ArgumentTypeError("종목은 KR:005930 또는 US:AAPL 형식입니다.")
    market, symbol = match.groups()
    if market == "KR" and not re.fullmatch(r"[A-Z0-9]{6}", symbol):
        raise argparse.ArgumentTypeError("국내 종목 코드는 영문·숫자 조합의 6자리입니다.")
    return market, symbol
