"""CSV 데이터 검증 테스트."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pytrading.data import load_candles_from_csv


class CsvLoaderTest(unittest.TestCase):
    def test_loads_case_insensitive_headers_and_sorts_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prices.csv"
            path.write_text(
                "Date,Open,High,Low,Close,Volume\n"
                "2026-01-02,101,103,100,102,200\n"
                "2026-01-01,100,102,99,101,100\n",
                encoding="utf-8",
            )

            candles = load_candles_from_csv(path)

        self.assertEqual([item.time for item in candles], ["2026-01-01", "2026-01-02"])
        self.assertEqual(candles[1].volume, 200)

    def test_rejects_invalid_high_price(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.csv"
            path.write_text(
                "date,open,high,low,close\n2026-01-01,100,90,80,95\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "고가/저가"):
                load_candles_from_csv(path)


if __name__ == "__main__":
    unittest.main()
