"""
한국투자증권(KIS) REST API 구현.

이 파일의 전체 실행 흐름은 다음과 같다.

1. D:\\00_env\\.env에서 APP_KEY, APP_SECRET, ACC_NO를 읽는다.
2. token\\token.dat에 저장된 토큰이 아직 유효한지 확인한다.
3. 유효한 토큰이 없으면 KIS OAuth API에서 새 토큰을 발급받아 저장한다.
4. 토큰과 앱 키를 HTTP 헤더에 넣어 현재가 또는 일봉 API를 호출한다.
5. KIS의 JSON 응답을 공통 모델인 StockQuote/StockHistory로 변환한다.

requests나 mojito 같은 외부 패키지는 사용하지 않는다. HTTP 통신에는
Python 표준 라이브러리인 urllib만 사용한다.
"""
from __future__ import annotations

import json
import os
import pickle
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pytrading.config.settings import KIS_ENV_PATH, KIS_TOKEN_PATH
from pytrading.stocks.models import Market, StockCandle, StockHistory, StockProvider, StockQuote, Timeframe
from pytrading.stocks.utils import to_float, to_int


# 한국투자증권 실전투자 REST API 주소.
# 모의투자를 사용하려면 별도의 모의투자 주소와 키가 필요하다.
KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"

# 만료 시각에 정확히 맞춰 요청하면 통신 중 토큰이 만료될 수 있으므로,
# 실제 만료 60초 전부터는 만료된 토큰으로 취급하고 새로 발급한다.
TOKEN_REFRESH_MARGIN_SECONDS = 60

# 사용자가 입력하는 시장 이름을 KIS API의 거래소 코드로 변환한다.
# 예: 사용자가 NASDAQ을 선택하면 KIS 요청에는 EXCD=NAS를 전송한다.
KIS_MARKETS = {
    "NASDAQ": "NAS",
    "NAS": "NAS",
    "NYSE": "NYS",
    "NYS": "NYS",
    "AMEX": "AMS",
    "AMS": "AMS",
}


@dataclass
class KisAccount:
    """KIS API 호출에 필요한 사용자 인증 정보."""

    api_key: str
    api_secret: str
    # 현재가 조회에는 계좌번호가 필요 없지만, 향후 잔고/주문 기능에서 사용한다.
    acc_no: str = ""


class KisStockClient:
    """
    KIS 시세 API 클라이언트.

    CLI는 이 클래스를 직접 알 필요 없이 create_stock_client("kis")를 통해
    인스턴스를 만든다. quote()는 현재가, history()는 일봉을 반환한다.
    """

    provider = StockProvider.KIS

    def __init__(
        self,
        account: KisAccount | None = None,
        env_path: str | Path = KIS_ENV_PATH,
        token_path: str | Path = KIS_TOKEN_PATH,
        base_url: str = KIS_BASE_URL,
        timeout: float = 10.0,
    ):
        # account를 직접 전달하지 않으면 기본 환경 파일에서 키를 읽는다.
        self.account = account or load_kis_account(Path(env_path))

        # 토큰 저장 경로와 API 주소를 인스턴스에 보관한다.
        # 테스트할 때는 이 값을 가짜 서버 주소나 임시 파일로 바꿀 수 있다.
        self.token_path = Path(token_path)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def quote(self, symbol: str, market: str = Market.NASDAQ.value) -> StockQuote:
        """해외주식 한 종목의 현재가를 조회한다."""

        # 종목 코드는 KIS 요청 형식에 맞게 대문자로 통일한다.
        symbol = symbol.upper()
        market_code = self._market_code(market)

        # 해외주식 현재체결가 API 호출.
        # HHDFS00000300은 KIS가 이 API에 지정한 거래 ID(TR ID)이다.
        payload = self._get_json(
            "/uapi/overseas-price/v1/quotations/price",
            "HHDFS00000300",
            {"AUTH": "", "EXCD": market_code, "SYMB": symbol},
        )

        # KIS 응답은 실제 시세 데이터를 output 안에 넣어 반환한다.
        output = payload.get("output") or {}

        # 공급자별 필드 이름(last, base, diff 등)을 프로젝트 공통 형식으로 바꾼다.
        return StockQuote(
            symbol=symbol,
            provider=self.provider,
            market=market.upper(),
            price=to_float(output.get("last")),
            currency="USD",
            previous_close=to_float(output.get("base")),
            change=to_float(output.get("diff")),
            change_rate=to_float(output.get("rate")),
            volume=to_int(output.get("tvol")),
            trade_amount=to_float(output.get("tamt")),
            raw=payload,
        )

    def quotes(self, symbols: list[str], market: str = Market.NASDAQ.value) -> list[StockQuote]:
        """
        여러 종목의 현재가를 순서대로 조회한다.

        KIS 현재가 API는 한 요청에 한 종목을 받으므로 quote()를 반복 호출한다.
        """
        return [self.quote(symbol, market) for symbol in symbols]

    def history(
        self,
        symbol: str,
        market: str = Market.NASDAQ.value,
        timeframe: str = Timeframe.DAY.value,
        start: str = "",
        end: str = "",
    ) -> StockHistory:
        """해외주식의 일봉 데이터를 조회한다."""

        # 현재 구현은 KIS 기간별시세 API의 일봉만 지원한다.
        if timeframe != Timeframe.DAY.value:
            raise ValueError("KIS REST history currently supports only the 1d timeframe.")

        symbol = symbol.upper()

        # 해외주식 기간별시세 API 호출.
        # GUBN=0은 일봉, BYMD는 조회 기준 종료일, MODP=1은 수정주가 반영이다.
        payload = self._get_json(
            "/uapi/overseas-price/v1/quotations/dailyprice",
            "HHDFS76240000",
            {
                "AUTH": "",
                "EXCD": self._market_code(market),
                "SYMB": symbol,
                "GUBN": "0",
                "BYMD": end,
                "MODP": "1",
            },
        )

        # output2에는 최신 날짜부터 과거 날짜 순서로 봉 데이터가 들어온다.
        rows = payload.get("output2") or []

        # 화면과 차트에서 오래된 날짜부터 보이도록 reversed()로 순서를 뒤집는다.
        # start/end가 입력됐다면 해당 날짜 범위만 남긴다.
        candles = [
            parse_overseas_candle(row)
            for row in reversed(rows)
            if isinstance(row, dict) and _date_in_range(str(row.get("xymd") or ""), start, end)
        ]
        return StockHistory(
            symbol=symbol,
            provider=self.provider,
            market=market.upper(),
            timeframe=timeframe,
            candles=candles,
            raw=payload,
        )

    def _get_json(self, path: str, tr_id: str, params: dict[str, str]) -> dict[str, Any]:
        """
        인증이 필요한 KIS GET API를 호출하고 JSON 객체를 반환한다.

        quote()와 history()에서 공통으로 필요한 URL 조립, 인증 헤더,
        응답 오류 검사를 한곳에서 처리한다.
        """

        # 딕셔너리를 AUTH=&EXCD=NAS&SYMB=AAPL 형태의 쿼리 문자열로 바꾼다.
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.base_url}{path}?{query}",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                # 먼저 저장된 토큰을 검사하고, 필요할 때만 새 토큰을 발급한다.
                "Authorization": f"Bearer {self._access_token()}",
                "appkey": self.account.api_key,
                "appsecret": self.account.api_secret,
                "tr_id": tr_id,
                "custtype": "P",
            },
        )
        payload = self._open_json(request)

        # KIS는 HTTP 요청이 성공해도 업무 오류를 rt_cd로 알려줄 수 있다.
        # rt_cd가 "0"이 아니면 정상 시세 응답이 아니다.
        if str(payload.get("rt_cd", "0")) != "0":
            message = payload.get("msg1") or payload.get("msg_cd") or "Unknown KIS API error"
            raise RuntimeError(f"KIS API error: {message}")
        return payload

    def _access_token(self) -> str:
        """저장된 토큰을 재사용하거나, 만료된 경우 새로 발급한다."""

        token = read_token(self.token_path)

        # 토큰 값, 만료 시각, 발급에 사용한 앱 키가 모두 일치해야 재사용한다.
        if token and is_token_valid(token, self.account.api_key, self.account.api_secret):
            return str(token["access_token"])

        # 파일이 없거나 토큰이 만료됐으면 KIS에 새 토큰을 요청한다.
        token = self._issue_token()
        save_token(self.token_path, token)
        return str(token["access_token"])

    def _issue_token(self) -> dict[str, Any]:
        """KIS OAuth 서버에서 client_credentials 방식으로 토큰을 발급한다."""

        # KIS 토큰 API는 앱 키와 앱 시크릿을 JSON 본문으로 받는다.
        body = json.dumps(
            {
                "grant_type": "client_credentials",
                "appkey": self.account.api_key,
                "appsecret": self.account.api_secret,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/oauth2/tokenP",
            data=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
            method="POST",
        )
        token = self._open_json(request)

        # 응답에 access_token이 없다면 발급 실패로 처리한다.
        if not token.get("access_token"):
            message = token.get("error_description") or token.get("msg1") or "Token was not returned"
            raise RuntimeError(f"KIS token issue failed: {message}")
        # KIS 응답에 로컬 캐시 검사용 정보를 추가한다.
        # timestamp는 발급 시각, expires_at은 실제 만료 시각(Unix timestamp)이다.
        token["timestamp"] = int(time.time())
        token["expires_at"] = int(time.time()) + int(token.get("expires_in") or 86400)

        # 다른 앱 키로 발급한 토큰을 잘못 재사용하지 않도록 발급 키도 기록한다.
        token["api_key"] = self.account.api_key
        token["api_secret"] = self.account.api_secret
        return token

    def _open_json(self, request: urllib.request.Request) -> dict[str, Any]:
        """HTTP 요청을 실행하고 응답 본문을 JSON 딕셔너리로 변환한다."""

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # 400/401/500 같은 HTTP 오류도 본문에 KIS 오류 설명이 들어올 수 있다.
            body = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(body)
                message = payload.get("msg1") or payload.get("error_description") or body
            except json.JSONDecodeError:
                message = body
            raise RuntimeError(f"KIS HTTP {exc.code}: {message}") from exc
        except urllib.error.URLError as exc:
            # DNS, 인터넷 연결, 타임아웃 같은 네트워크 오류를 읽기 쉽게 바꾼다.
            raise RuntimeError(f"KIS connection failed: {exc.reason}") from exc

    @staticmethod
    def _market_code(market: str) -> str:
        """NASDAQ 같은 사용자 입력을 NAS 같은 KIS 거래소 코드로 바꾼다."""

        market_code = KIS_MARKETS.get(market.upper())
        if not market_code:
            raise ValueError(f"Unsupported KIS market: {market}. Use NASDAQ, NYSE, or AMEX.")
        return market_code


def load_kis_account(env_path: Path = KIS_ENV_PATH) -> KisAccount:
    """
    환경 변수 또는 D:\\00_env\\.env에서 KIS 인증 정보를 읽는다.

    우선순위는 운영체제 환경 변수 -> env 파일 -> 기존 토큰 파일 순서다.
    토큰 파일 fallback은 예전에 저장한 키가 있는 경우를 위한 호환 처리다.
    """

    env = load_env(env_path)
    api_key = os.getenv("APP_KEY") or env.get("APP_KEY")
    api_secret = os.getenv("APP_SECRET") or env.get("APP_SECRET")
    acc_no = os.getenv("ACC_NO") or env.get("ACC_NO") or ""

    # env 파일에 키가 없다면 기존 token.dat에 저장된 키를 마지막으로 확인한다.
    cached = read_token(KIS_TOKEN_PATH)
    api_key = api_key or (str(cached.get("api_key")) if cached else "")
    api_secret = api_secret or (str(cached.get("api_secret")) if cached else "")

    if not api_key or not api_secret:
        raise RuntimeError(f"KIS credentials not found in {env_path} or {KIS_TOKEN_PATH}")
    return KisAccount(api_key=api_key, api_secret=api_secret, acc_no=acc_no)


def parse_overseas_candle(row: dict[str, Any]) -> StockCandle:
    """KIS 일봉 한 행을 프로젝트 공통 StockCandle 객체로 변환한다."""

    close = to_float(row.get("clos") or row.get("last")) or 0.0
    return StockCandle(
        time=str(row.get("xymd") or ""),
        open=to_float(row.get("open")) or close,
        high=to_float(row.get("high")) or close,
        low=to_float(row.get("low")) or close,
        close=close,
        volume=to_int(row.get("tvol") or row.get("evol")) or 0,
        currency="USD",
    )


def load_env(path: Path) -> dict[str, str]:
    """KEY=VALUE 형식의 단순 env 파일을 딕셔너리로 읽는다."""

    env: dict[str, str] = {}
    if not path.exists():
        return env
    with path.open("r", encoding="utf-8-sig") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def read_token(path: Path) -> dict[str, Any] | None:
    """pickle 형식의 토큰 파일을 읽는다. 파일이 없거나 깨졌으면 None을 반환한다."""

    try:
        with path.open("rb") as file:
            token = pickle.load(file)
        return token if isinstance(token, dict) else None
    except Exception:
        return None


def save_token(path: Path, token: dict[str, Any]) -> None:
    """토큰 딕셔너리를 token.dat에 저장한다."""

    # token 폴더가 없으면 먼저 만든다.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as file:
        pickle.dump(token, file)


def is_token_valid(token: dict[str, Any], api_key: str, api_secret: str) -> bool:
    """저장된 토큰을 현재 앱 키로 계속 사용할 수 있는지 검사한다."""

    # 새 코드에서 저장하는 expires_at을 가장 먼저 사용한다.
    expires_at = int(token.get("expires_at") or 0)

    # 과거 토큰 파일에는 만료 시각이 문자열로 저장됐을 수 있어 호환한다.
    if not expires_at and token.get("access_token_token_expired"):
        try:
            expires_at = int(
                datetime.strptime(str(token["access_token_token_expired"]), "%Y-%m-%d %H:%M:%S").timestamp()
            )
        except ValueError:
            expires_at = 0
    # timestamp + expires_in 형식으로 저장된 과거 토큰도 읽을 수 있게 한다.
    if not expires_at:
        expires_at = int(token.get("timestamp") or 0) + int(token.get("expires_in") or 0)

    # access_token이 있고, 60초 이상 남았고, 앱 키가 같을 때만 유효하다.
    return (
        bool(token.get("access_token"))
        and int(time.time()) + TOKEN_REFRESH_MARGIN_SECONDS < expires_at
        and token.get("api_key") == api_key
        and token.get("api_secret") == api_secret
    )


def _date_in_range(value: str, start: str, end: str) -> bool:
    """YYYYMMDD 문자열이 사용자가 요청한 시작일/종료일 범위 안인지 확인한다."""

    return (not start or value >= start) and (not end or value <= end)
