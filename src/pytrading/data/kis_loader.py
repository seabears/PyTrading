"""KIS API를 백테스트용 데이터 입력으로 연결한다."""
from __future__ import annotations

from pytrading.stocks.models import StockCandle
from pytrading.stocks.providers.kis import KisStockClient


def load_candles_from_kis(
    symbol: str,
    market: str,
    start: str,
    end: str,
    client: KisStockClient | None = None,
) -> list[StockCandle]:
    """
    KIS에서 지정한 기간의 일봉을 가져온다.

    클라이언트를 인자로 받을 수 있게 하여 실제 통신과 백테스트 로직을
    분리하고, 테스트에서는 가짜 KIS 클라이언트를 사용할 수 있게 한다.
    """

    kis_client = client or KisStockClient()
    history = kis_client.history(
        symbol=symbol,
        market=market,
        timeframe="1d",
        start=start,
        end=end,
    )
    if len(history.candles) < 2:
        raise ValueError(
            f"KIS 과거 데이터가 부족합니다: {symbol} {market} "
            f"{start}~{end} ({len(history.candles)}건)"
        )
    return history.candles
