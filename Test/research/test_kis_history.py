"""과거 수집의 인과성·페이지 진행·원본 검사를 합성 응답으로 확인한다."""
import unittest
from unittest.mock import patch
from datetime import date
from research.kis_history import collect_us_history, read_history_page
from broker.kis import KisApiError


def daily(day, close="12"):
    return {"xymd": day, "open": "10", "high": "13", "low": "9", "clos": close, "tvol": "100"}


class Client:
    def __init__(self, pages):
        self.pages, self.parameters = iter(pages), []

    def get(self, path, parameters):
        self.parameters.append(parameters)
        return {"output2": next(self.pages)}


class KisHistoryTests(unittest.TestCase):
    def test_transient_network_error_retries_same_page(self):
        client = Client([])
        client.get = unittest.mock.Mock(side_effect=[KisApiError("KIS 연결 실패"), {"output2": []}])
        with patch("research.kis_history.time.sleep") as sleep:
            self.assertEqual(read_history_page(client, "/path", {"SYMB": "AAPL"}), {"output2": []})
        self.assertEqual(client.get.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_permission_error_does_not_retry(self):
        client = Client([])
        client.get = unittest.mock.Mock(side_effect=KisApiError("KIS 시세 조회 거절"))
        with patch("research.kis_history.time.sleep") as sleep, self.assertRaises(KisApiError):
            read_history_page(client, "/path", {})
        self.assertEqual(client.get.call_count, 1)
        sleep.assert_not_called()

    def test_daily_pages_move_back_and_exclude_future(self):
        client = Client([[daily("20261022"), daily("20261021")], [daily("20261020"), daily("20261019")]])
        result, raw = collect_us_history(client, "AAPL", "NAS", "1d", date(2026, 10, 20), date(2026, 10, 21))
        self.assertEqual([row["timestamp"][:10] for row in result["candles"]], ["2026-10-20", "2026-10-21"])
        self.assertEqual(client.parameters[1]["BYMD"], "20261020")
        self.assertEqual(client.parameters[0]["MODP"], "1")
        self.assertTrue(result["requested_period_reached"])
        self.assertEqual(len(raw), 2)

    def test_repeated_page_is_incomplete(self):
        result, raw = collect_us_history(Client([[daily("20261021")], [daily("20261021")]]), "AAPL", "NAS", "1d", date(2018, 1, 1), date(2026, 10, 21))
        self.assertEqual(result["stop_reason"], "api_no_progress")
        self.assertFalse(result["collection_complete"])

    def test_bad_range_is_quarantined_and_raw_preserved(self):
        result, raw = collect_us_history(Client([[daily("20261021", "20")], []]), "AAPL", "NAS", "1d", date(2018, 1, 1), date(2026, 10, 21))
        self.assertEqual(result["candles"], [])
        self.assertEqual(len(result["rejected"]), 1)
        self.assertEqual(raw[0]["rows"][0]["clos"], "20")

    def test_conflicting_duplicate_fails(self):
        with self.assertRaises(ValueError):
            collect_us_history(Client([[daily("20261021"), daily("20261021", "11")]]), "AAPL", "NAS", "1d", date(2018, 1, 1), date(2026, 10, 21))

    def test_minute_today_excluded_without_stopping_pagination(self):
        def minute(day):
            return {"xymd": day, "xhms": "100000", "open": "10", "high": "13", "low": "9", "last": "12", "evol": "100"}
        client = Client([[minute("20261022")], [minute("20261021")], []])
        result, raw = collect_us_history(client, "AAPL", "NAS", "1m", date(2018, 1, 1), date(2026, 10, 21))
        self.assertEqual(len(result["candles"]), 1)
        self.assertEqual(result["candles"][0]["timestamp"], "2026-10-21T10:01:00-04:00")
        self.assertEqual(client.parameters[1]["KEYB"], "20261022095900")
        self.assertEqual(result["stop_reason"], "api_empty_page")

    def test_page_cap_is_incomplete(self):
        result, raw = collect_us_history(Client([[daily("20261021")]]), "AAPL", "NAS", "1d", date(2018, 1, 1), date(2026, 10, 21), 1)
        self.assertFalse(result["collection_complete"])
        self.assertEqual(result["stop_reason"], "page_limit")

    def test_date_label_uses_correct_dst(self):
        result, raw = collect_us_history(Client([[daily("20260102")], []]), "AAPL", "NAS", "1d", date(2018, 1, 1), date(2026, 1, 2))
        self.assertTrue(result["candles"][0]["timestamp"].endswith("-05:00"))
