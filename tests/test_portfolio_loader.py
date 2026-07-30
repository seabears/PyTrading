"""KIS 다중 종목 캐시 수집 테스트."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from pytrading.data import load_portfolio_from_kis
from pytrading.stocks.models import StockCandle, StockHistory, StockProvider


class _FakeKisClient:
    def __init__(self):
        self.calls: list[str] = []

    def history(self, symbol, market, timeframe, start, end):
        self.calls.append(symbol)
        start_day = date(2025, 1, 1)
        candles = [
            StockCandle(
                time=(start_day + timedelta(days=index)).strftime("%Y%m%d"),
                open=100 + index,
                high=101 + index,
                low=99 + index,
                close=100 + index,
                volume=1_000,
            )
            for index in range(3)
        ]
        return StockHistory(
            symbol=symbol,
            provider=StockProvider.KIS,
            market=market,
            timeframe=timeframe,
            candles=candles,
        )


class PortfolioLoaderTest(unittest.TestCase):
    def test_downloads_then_reuses_symbol_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            client = _FakeKisClient()
            first = load_portfolio_from_kis(
                ["AAA", "BBB"],
                "NASDAQ",
                "20250101",
                "20250103",
                cache_dir=Path(directory),
                client=client,
            )
            second = load_portfolio_from_kis(
                ["AAA", "BBB"],
                "NASDAQ",
                "20250101",
                "20250103",
                cache_dir=Path(directory),
            )

        self.assertEqual(first.downloaded, ["AAA", "BBB"])
        self.assertEqual(client.calls, ["AAA", "BBB"])
        self.assertEqual(second.cache_hits, ["AAA", "BBB"])

    def test_requires_two_unique_symbols(self):
        with self.assertRaisesRegex(ValueError, "최소 2개"):
            load_portfolio_from_kis(
                ["AAA", "AAA"],
                "NASDAQ",
                "20250101",
                "20250103",
                client=_FakeKisClient(),
            )


if __name__ == "__main__":
    unittest.main()
