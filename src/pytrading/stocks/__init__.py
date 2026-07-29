"""Provider-neutral stock API."""
from __future__ import annotations

from .models import Market, StockCandle, StockHistory, StockProvider, StockQuote, Timeframe
from .providers.toss import TossStockClient
from .providers.kis import KisStockClient

def create_stock_client(provider: str):
    key = provider.strip().lower()

    if key == StockProvider.KIS.value:
        return KisStockClient()
    
    if key == StockProvider.TOSS.value:
        return TossStockClient()

    raise ValueError(f"Unsupported stock provider: {provider}")

# 모듈 안에서 찾지 못한 이름을 요청받았을 때, 자동으로 호출하는 특수 함수
def __getattr__(name: str):
    if name == "KisStockClient":
        from .providers.kis import KisStockClient

        return KisStockClient
    raise AttributeError(name)


__all__ = [
    "KisStockClient",
    "Market",
    "StockCandle",
    "StockHistory",
    "StockProvider",
    "StockQuote",
    "Timeframe",
    "TossStockClient",
    "create_stock_client",
]