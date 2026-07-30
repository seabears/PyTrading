"""투자 대상 선택과 독립 매수·매도 함수 테스트."""
from __future__ import annotations

import unittest

from pytrading.stocks.models import StockCandle
from pytrading.strategies import (
    create_buy_signal,
    create_sell_signal,
    select_investment_targets,
)


def make_candles(prices: list[float], volume: int = 1_000) -> list[StockCandle]:
    return [
        StockCandle(
            time=str(index),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=volume,
        )
        for index, price in enumerate(prices, start=1)
    ]


class InvestmentTargetSelectionTest(unittest.TestCase):
    def test_selects_uptrend_targets_in_momentum_order(self):
        histories = {
            "SLOW": make_candles([10, 10, 11]),
            "FAST": make_candles([10, 11, 13]),
            "DOWN": make_candles([13, 12, 10]),
        }

        targets = select_investment_targets(
            histories,
            long_window=2,
            momentum_window=2,
            volume_window=2,
            maximum_targets=2,
        )

        self.assertEqual(targets, ["FAST", "SLOW"])

    def test_excludes_target_below_minimum_volume(self):
        histories = {"LOW_VOLUME": make_candles([10, 11, 12], volume=10)}

        targets = select_investment_targets(
            histories,
            long_window=2,
            momentum_window=2,
            volume_window=2,
            minimum_average_volume=100,
        )

        self.assertEqual(targets, [])


class BuySellSignalTest(unittest.TestCase):
    def test_creates_buy_signal_on_upward_cross(self):
        self.assertTrue(
            create_buy_signal(
                make_candles([10, 10, 9, 12]),
                short_window=2,
                long_window=3,
            )
        )

    def test_creates_sell_signal_on_downward_cross(self):
        self.assertTrue(
            create_sell_signal(
                make_candles([10, 10, 11, 8]),
                short_window=2,
                long_window=3,
            )
        )

    def test_creates_sell_signal_at_stop_loss(self):
        self.assertTrue(
            create_sell_signal(
                make_candles([94]),
                short_window=2,
                long_window=3,
                entry_price=100,
                stop_loss_rate=0.05,
            )
        )

    def test_creates_sell_signal_at_trailing_stop(self):
        self.assertTrue(
            create_sell_signal(
                make_candles([92]),
                short_window=2,
                long_window=3,
                highest_price=100,
                trailing_stop_rate=0.07,
            )
        )


if __name__ == "__main__":
    unittest.main()
