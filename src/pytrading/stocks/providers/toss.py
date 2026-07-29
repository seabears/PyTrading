r"""
Toss Securities Open API stock provider.

The OpenAPI spec used for this module is stored at:
D:\01_GIT\PyTrading\docs\새 텍스트 문서.txt
"""
from __future__ import annotations

import json
import os
import pickle
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from pytrading.config.settings import TOSS_ENV_PATH, TOSS_TOKEN_PATH
from pytrading.stocks.models import Market, StockCandle, StockHistory, StockProvider, StockQuote, Timeframe
from pytrading.stocks.utils import change_rate, to_float, to_int


TOSS_BASE_URL = "https://openapi.tossinvest.com"
TOKEN_REFRESH_MARGIN_SECONDS = 60


class TossStockClient:
    """Common stock client backed by Toss Securities Open API."""

    provider = StockProvider.TOSS

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str = TOSS_BASE_URL,
        token_path: str | Path = TOSS_TOKEN_PATH,
        env_path: str | Path = TOSS_ENV_PATH,
        timeout: float = 10.0,
    ):
        env = _load_env(Path(env_path))
        self.client_id = client_id or os.getenv("TOSS_CLIENT_ID") or env.get("TOSS_CLIENT_ID") or env.get("TOSS_APP_KEY")
        self.client_secret = (
            client_secret
            or os.getenv("TOSS_CLIENT_SECRET")
            or env.get("TOSS_CLIENT_SECRET")
            or env.get("TOSS_APP_SECRET")
        )
        self.base_url = base_url.rstrip("/")
        self.token_path = Path(token_path)
        self.timeout = timeout

    def quote(self, symbol: str, market: str = Market.US.value) -> StockQuote:
        quotes = self.quotes([symbol], market=market)
        if not quotes:
            raise RuntimeError(f"Toss quote not found for symbol: {symbol}")
        return quotes[0]

    def quotes(self, symbols: list[str], market: str = Market.US.value) -> list[StockQuote]:
        symbols = [symbol.upper() for symbol in symbols]
        payload = self._get_json("/api/v1/prices", {"symbols": ",".join(symbols)})
        rows = payload.get("result") or []
        if not isinstance(rows, list):
            raise RuntimeError(f"Unexpected Toss prices response: {payload}")
        return [self._to_quote(row, market) for row in rows]

    def history(
        self,
        symbol: str,
        market: str = Market.US.value,
        timeframe: str = Timeframe.DAY.value,
        count: int = 100,
        before: str = "",
        adjusted: bool = True,
    ) -> StockHistory:
        if timeframe not in (Timeframe.MINUTE_1.value, Timeframe.DAY.value):
            raise ValueError("Toss candles support only 1m and 1d")
        if count < 1 or count > 200:
            raise ValueError("Toss candle count must be between 1 and 200")

        params = {
            "symbol": symbol.upper(),
            "interval": timeframe,
            "count": str(count),
            "adjusted": "true" if adjusted else "false",
        }
        if before:
            params["before"] = before
        payload = self._get_json("/api/v1/candles", params)
        result = payload.get("result") or {}
        rows = result.get("candles") or []
        return StockHistory(
            symbol=symbol.upper(),
            provider=self.provider,
            market=market.upper(),
            timeframe=timeframe,
            candles=[self._to_candle(row) for row in reversed(rows)],
            raw=payload,
        )

    def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.base_url}{path}?{query}",
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _access_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "Toss credentials not found. Set TOSS_CLIENT_ID and TOSS_CLIENT_SECRET "
                "in environment variables or D:\\00_env\\toss.env."
            )

        token = _read_token(self.token_path)
        if token and _is_token_valid(token, self.client_id, self.client_secret):
            return str(token["access_token"])

        token = self._issue_token()
        _save_token(self.token_path, token)
        return str(token["access_token"])

    def _issue_token(self) -> dict[str, Any]:
        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/oauth2/token",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            token = json.loads(response.read().decode("utf-8"))
        token["timestamp"] = int(time.time()) + int(token.get("expires_in") or 0)
        token["client_id"] = self.client_id
        token["client_secret"] = self.client_secret
        return token

    def _to_quote(self, row: dict[str, Any], market: str) -> StockQuote:
        price = to_float(row.get("lastPrice"))
        previous_close = to_float(row.get("basePrice") or row.get("previousClosePrice"))
        rate = to_float(row.get("changeRate")) or change_rate(price, previous_close)
        change = None if price is None or previous_close is None else price - previous_close
        return StockQuote(
            symbol=str(row.get("symbol") or ""),
            provider=self.provider,
            market=str(row.get("market") or market).upper(),
            price=price,
            currency=str(row.get("currency") or ""),
            timestamp=str(row.get("timestamp") or ""),
            previous_close=previous_close,
            change=change,
            change_rate=rate,
            volume=to_int(row.get("volume")),
            trade_amount=to_float(row.get("tradeAmount")),
            raw=row,
        )

    def _to_candle(self, row: dict[str, Any]) -> StockCandle:
        return StockCandle(
            time=str(row.get("timestamp") or ""),
            open=to_float(row.get("openPrice")) or 0.0,
            high=to_float(row.get("highPrice")) or 0.0,
            low=to_float(row.get("lowPrice")) or 0.0,
            close=to_float(row.get("closePrice")) or 0.0,
            volume=to_int(row.get("volume")) or 0,
            currency=str(row.get("currency") or ""),
        )


def _load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    with path.open("r", encoding="utf-8-sig") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _read_token(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("rb") as f:
            token = pickle.load(f)
        return token if isinstance(token, dict) else None
    except Exception:
        return None


def _save_token(path: Path, token: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(token, f)


def _is_token_valid(token: dict[str, Any], client_id: str, client_secret: str) -> bool:
    expire_epoch = int(token.get("timestamp") or 0)
    return (
        bool(token.get("access_token"))
        and int(time.time()) + TOKEN_REFRESH_MARGIN_SECONDS < expire_epoch
        and token.get("client_id") == client_id
        and token.get("client_secret") == client_secret
    )
