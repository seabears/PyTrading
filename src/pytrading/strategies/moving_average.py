"""단기·장기 단순 이동평균 교차 전략."""
from __future__ import annotations

from typing import Sequence

from pytrading.stocks.models import StockCandle
from pytrading.strategies.base import Signal
from pytrading.strategies.buy import create_buy_signal
from pytrading.strategies.sell import create_sell_signal


class MovingAverageCrossStrategy:
    """
    단기 이동평균이 장기 이동평균을 상향 돌파하면 매수하고,
    하향 돌파하면 매도한다.

    신호 계산에는 현재 봉의 종가까지만 사용한다. 실제 체결은 백테스트
    엔진이 다음 봉 시가에 처리하므로 미래 정보를 미리 보는 문제가 없다.
    """

    def __init__(self, short_window: int = 5, long_window: int = 20):
        if short_window < 1:
            raise ValueError("단기 이동평균 기간은 1 이상이어야 합니다.")
        if long_window <= short_window:
            raise ValueError("장기 이동평균 기간은 단기 기간보다 커야 합니다.")
        self.short_window = short_window
        self.long_window = long_window

    @property
    def name(self) -> str:
        return f"SMA 교차({self.short_window}/{self.long_window})"

    def generate_signal(self, candles: Sequence[StockCandle]) -> Signal:
        if create_buy_signal(
            candles,
            short_window=self.short_window,
            long_window=self.long_window,
        ):
            return Signal.BUY
        if create_sell_signal(
            candles,
            short_window=self.short_window,
            long_window=self.long_window,
        ):
            return Signal.SELL
        return Signal.HOLD
