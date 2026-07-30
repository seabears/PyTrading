"""실제 HTTP 통신 없이 KIS 기간 조회와 응답 변환을 검증한다."""
from __future__ import annotations

import unittest

from pytrading.stocks.providers.kis import KisStockClient


def overseas_row(date: str, close: str) -> dict[str, str]:
    return {
        "xymd": date,
        "open": close,
        "high": close,
        "low": close,
        "clos": close,
        "tvol": "100",
    }


class _FakeOverseasClient(KisStockClient):
    def __init__(self):
        self.request_interval = 0
        self.requests: list[dict[str, str]] = []
        self.responses = [
            {"output2": [overseas_row("20240105", "105"), overseas_row("20240104", "104")]},
            {
                "output2": [
                    overseas_row("20240103", "103"),
                    overseas_row("20240102", "102"),
                    overseas_row("20240101", "101"),
                ]
            },
        ]

    def _get_json(self, path, tr_id, params):
        self.requests.append(params)
        return self.responses.pop(0)


class _FakeDomesticClient(KisStockClient):
    def __init__(self):
        self.request_interval = 0
        self.requests: list[tuple[str, dict[str, str]]] = []

    def _get_json(self, path, tr_id, params):
        self.requests.append((path, params))
        date = params["FID_INPUT_DATE_2"]
        return {
            "output2": [
                {
                    "stck_bsop_date": date,
                    "stck_oprc": "70000",
                    "stck_hgpr": "71000",
                    "stck_lwpr": "69000",
                    "stck_clpr": "70500",
                    "acml_vol": "123456",
                }
            ]
        }


class KisHistoryTest(unittest.TestCase):
    def test_overseas_history_fetches_older_pages_and_sorts(self):
        client = _FakeOverseasClient()

        history = client.history("aapl", "NASDAQ", start="20240101", end="20240105")

        self.assertEqual(len(client.requests), 2)
        self.assertEqual(client.requests[0]["BYMD"], "20240105")
        self.assertEqual(client.requests[1]["BYMD"], "20240103")
        self.assertEqual(
            [candle.time for candle in history.candles],
            ["20240101", "20240102", "20240103", "20240104", "20240105"],
        )

    def test_domestic_history_splits_long_period_and_parses_krw(self):
        client = _FakeDomesticClient()

        history = client.history("005930", "KOREA", start="20240101", end="20240430")

        self.assertEqual(len(client.requests), 2)
        self.assertTrue(
            all(
                path.endswith("inquire-daily-itemchartprice")
                and params["FID_ORG_ADJ_PRC"] == "0"
                for path, params in client.requests
            )
        )
        self.assertEqual(history.market, "KOREA")
        self.assertEqual(history.candles[-1].currency, "KRW")
        self.assertEqual(history.candles[-1].close, 70500)

    def test_history_rejects_invalid_date_range(self):
        client = _FakeOverseasClient()
        with self.assertRaisesRegex(ValueError, "시작일"):
            client.history("AAPL", "NASDAQ", start="20240201", end="20240101")


if __name__ == "__main__":
    unittest.main()
