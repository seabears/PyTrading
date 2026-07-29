"""
Provider-neutral stock data models.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class StockProvider(str, Enum):
    KIS = "kis"
    TOSS = "toss"


class Market(str, Enum):
    KOREA = "KOREA"
    NASDAQ = "NASDAQ"
    NYSE = "NYSE"
    AMEX = "AMEX"
    US = "US"
    KR = "KR"


class Timeframe(str, Enum):
    MINUTE_1 = "1m"
    DAY = "1d"


@dataclass
class StockQuote:
    symbol: str
    provider: StockProvider
    market: str
    price: Optional[float] = None
    currency: str = ""
    timestamp: str = ""
    name: str = ""
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_rate: Optional[float] = None
    volume: Optional[int] = None
    trade_amount: Optional[float] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class StockCandle:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    currency: str = ""


@dataclass
class StockHistory:
    symbol: str
    provider: StockProvider
    market: str
    timeframe: str
    candles: list[StockCandle] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)