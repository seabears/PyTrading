"""이동평균 교차 전략 테스트."""
from __future__ import annotations

import unittest

from pytrading.stocks.models import StockCandle
from pytrading.strategies import MovingAverageCrossStrategy, Signal


def candles(prices: list[float]) -> list[StockCandle]:
    return [
        StockCandle(str(index), price, price, price, price)
        for index, price in enumerate(prices, start=1)
    ]


class MovingAverageCrossStrategyTest(unittest.TestCase):
    def test_buy_signal_on_upward_cross(self):
        strategy = MovingAverageCrossStrategy(short_window=2, long_window=3)
        data = candles([10, 10, 9, 12])

        self.assertEqual(strategy.generate_signal(data), Signal.BUY)

    def test_requires_enough_candles(self):
        strategy = MovingAverageCrossStrategy(short_window=2, long_window=3)

        self.assertEqual(strategy.generate_signal(candles([10, 11, 12])), Signal.HOLD)


if __name__ == "__main__":
    unittest.main()
