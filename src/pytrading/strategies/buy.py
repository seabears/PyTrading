"""과거 캔들로 매수 신호를 만드는 함수."""
from __future__ import annotations

from collections.abc import Sequence

from pytrading.stocks.models import StockCandle
from pytrading.strategies.indicators import moving_average_cross_values


def create_buy_signal(
    candles: Sequence[StockCandle],
    *,
    short_window: int = 5,
    long_window: int = 20,
) -> bool:
    """단기 이동평균이 장기 이동평균을 상향 돌파했는지 확인한다."""

    averages = moving_average_cross_values(candles, short_window, long_window)
    if averages is None:
        return False
    previous_short, current_short, previous_long, current_long = averages
    return previous_short <= previous_long and current_short > current_long
