"""현재 보유 목록 CSV 로더 테스트."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pytrading.data import load_holdings_csv


class HoldingsLoaderTest(unittest.TestCase):
    def test_loads_holdings_and_total(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "holdings.csv"
            path.write_text(
                "티커,종목,시장,수량,평균단가_USD,매입금액_USD,비중_pct,"
                "투자유형,목표비중_pct,최대비중_pct\n"
                "MSFT,마이크로소프트,NASDAQ,2,100.125,200.25,80.10,"
                "CORE,15,25\n"
                "BTQ,BTQ 테크놀로지스,NASDAQ,5,10,50.00,19.90,"
                "TACTICAL,1,3\n"
                "합계,,,,,250.25,100.00,,,\n",
                encoding="utf-8",
            )

            portfolio = load_holdings_csv(path)

        self.assertEqual(portfolio.symbols, ["MSFT", "BTQ"])
        self.assertEqual(portfolio.holdings[0].quantity, 2)
        self.assertEqual(portfolio.holdings[0].investment_style.value, "CORE")
        self.assertEqual(portfolio.holdings[1].maximum_weight_percent, 3)
        self.assertEqual(portfolio.total_purchase_amount_usd, 250.25)

    def test_rejects_amount_that_does_not_match_quantity_and_price(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.csv"
            path.write_text(
                "티커,종목,시장,수량,평균단가_USD,매입금액_USD,비중_pct\n"
                "MSFT,마이크로소프트,NASDAQ,2,100,250,100\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "수량 x 평균단가"):
                load_holdings_csv(path)


if __name__ == "__main__":
    unittest.main()
