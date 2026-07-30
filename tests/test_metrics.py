"""포트폴리오 핵심 성과 지표 계산 테스트."""
from __future__ import annotations

from datetime import date, timedelta
import unittest

from pytrading.backtest.metrics import (
    calculate_annual_returns,
    calculate_cagr,
    calculate_max_drawdown,
)
from pytrading.backtest.models import EquityPoint


class BacktestMetricsTest(unittest.TestCase):
    def test_cagr_is_approximately_ten_percent(self):
        result = calculate_cagr(
            1_000,
            1_100,
            date(2025, 1, 1),
            date(2025, 1, 1) + timedelta(days=365),
        )

        self.assertAlmostEqual(result, 10.0, delta=0.02)

    def test_maximum_drawdown_uses_previous_peak(self):
        curve = [
            EquityPoint("2025-01-01", 100),
            EquityPoint("2025-01-02", 120),
            EquityPoint("2025-01-03", 90),
            EquityPoint("2025-01-04", 110),
        ]

        self.assertAlmostEqual(calculate_max_drawdown(curve), -25.0)

    def test_annual_returns_chain_from_previous_year_end(self):
        curve = [
            EquityPoint("2025-12-31", 110),
            EquityPoint("2026-12-31", 121),
        ]

        returns = calculate_annual_returns(curve, 100)
        self.assertAlmostEqual(returns[2025], 10.0)
        self.assertAlmostEqual(returns[2026], 10.0)


if __name__ == "__main__":
    unittest.main()
