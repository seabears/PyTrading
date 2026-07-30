"""다중 종목 포트폴리오 백테스트 테스트."""
from __future__ import annotations

from datetime import date, timedelta
import unittest

from pytrading.backtest import PortfolioBacktestConfig, PortfolioBacktestEngine
from pytrading.stocks.models import StockCandle


def price_series(start_price: float, daily_change: float, count: int = 40):
    start_day = date(2025, 1, 1)
    candles = []
    for index in range(count):
        price = start_price + daily_change * index
        candles.append(
            StockCandle(
                time=(start_day + timedelta(days=index)).strftime("%Y%m%d"),
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1_000_000,
            )
        )
    return candles


class PortfolioBacktestEngineTest(unittest.TestCase):
    def setUp(self):
        self.config = PortfolioBacktestConfig(
            initial_cash=1_000_000,
            commission_rate=0,
            slippage_rate=0,
            maximum_positions=2,
            minimum_cash_rate=0,
            rebalance_interval=5,
            trend_window=5,
            momentum_window=3,
            volume_window=3,
            volatility_window=3,
            exit_moving_average_window=2,
            maximum_annualized_volatility=10,
            stop_loss_rate=0.50,
            trailing_stop_rate=0.50,
            target_cagr_rate=10,
        )

    def test_selects_rising_stocks_and_trades_on_next_open(self):
        histories = {
            "FAST": price_series(100, 2),
            "SLOW": price_series(100, 1),
            "DOWN": price_series(150, -1),
        }

        result = PortfolioBacktestEngine(self.config).run(histories)

        self.assertEqual({trade.symbol for trade in result.trades}, {"FAST", "SLOW"})
        # 5번째 종가로 대상을 고르고 6번째 거래일 시가에 매수한다.
        self.assertTrue(all(trade.entry_time == "20250106" for trade in result.trades))
        self.assertGreater(result.final_equity, result.initial_cash)
        self.assertGreater(result.cagr_rate, 0)
        self.assertEqual(result.trade_count, 2)
        self.assertIn(2025, result.annual_returns)

    def test_rejects_history_shorter_than_indicator_window(self):
        histories = {
            "ONE": price_series(100, 1, count=4),
            "TWO": price_series(100, 2, count=4),
        }

        with self.assertRaisesRegex(ValueError, "최소 5거래일"):
            PortfolioBacktestEngine(self.config).run(histories)

    def test_default_long_term_windows_can_complete(self):
        histories = {
            "FAST": price_series(100, 0.30, count=260),
            "SLOW": price_series(100, 0.15, count=260),
            "DOWN": price_series(200, -0.10, count=260),
        }
        config = PortfolioBacktestConfig(
            maximum_positions=2,
            minimum_average_trading_value=0,
        )

        result = PortfolioBacktestEngine(config).run(histories)

        self.assertGreaterEqual(result.trade_count, 2)
        self.assertGreater(result.final_equity, result.initial_cash)
        self.assertTrue(result.validation_start_time)


if __name__ == "__main__":
    unittest.main()
