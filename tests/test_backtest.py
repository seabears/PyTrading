"""백테스트 엔진의 체결 시점과 손익 계산 테스트."""
from __future__ import annotations

import unittest

from pytrading.backtest import BacktestConfig, BacktestEngine
from pytrading.stocks.models import StockCandle
from pytrading.strategies import Signal


def candle(day: int, price: float) -> StockCandle:
    return StockCandle(
        time=f"2026-01-{day:02d}",
        open=price,
        high=price,
        low=price,
        close=price,
        volume=100,
    )


class _KnownSignalStrategy:
    """첫날 매수, 둘째 날 매도 신호를 내는 테스트용 전략."""

    name = "테스트 전략"

    def generate_signal(self, candles):
        if len(candles) == 1:
            return Signal.BUY
        if len(candles) == 2:
            return Signal.SELL
        return Signal.HOLD


class BacktestEngineTest(unittest.TestCase):
    def test_signal_is_executed_at_next_open(self):
        candles = [candle(1, 100), candle(2, 110), candle(3, 120)]
        config = BacktestConfig(initial_cash=1_000, commission_rate=0, slippage_rate=0)

        result = BacktestEngine(config).run(candles, _KnownSignalStrategy())

        self.assertEqual(result.trade_count, 1)
        self.assertEqual(result.trades[0].entry_time, "2026-01-02")
        self.assertEqual(result.trades[0].exit_time, "2026-01-03")
        self.assertEqual(result.trades[0].quantity, 9)
        self.assertAlmostEqual(result.final_equity, 1_090)
        self.assertAlmostEqual(result.total_return_rate, 9)

    def test_trading_costs_reduce_profit(self):
        candles = [candle(1, 100), candle(2, 100), candle(3, 110)]
        free_result = BacktestEngine(
            BacktestConfig(initial_cash=1_000, commission_rate=0, slippage_rate=0)
        ).run(candles, _KnownSignalStrategy())
        cost_result = BacktestEngine(
            BacktestConfig(initial_cash=1_000, commission_rate=0.001, slippage_rate=0.001)
        ).run(candles, _KnownSignalStrategy())

        self.assertLess(cost_result.final_equity, free_result.final_equity)
        self.assertGreater(cost_result.total_fees, 0)


if __name__ == "__main__":
    unittest.main()
