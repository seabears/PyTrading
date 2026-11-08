"""사업군 비교가 기간·설정·실시간 대상과 섞이지 않는지 합성 입력으로 확인한다."""
import json
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from paths import PROJECT_ROOT, CONFIG_ROOT
from tools.research_peers import load_companies, peer_period, split_reference, select_historical_companies


class PeerResearchTest(unittest.TestCase):
    def test_recent_ipo_is_excluded_without_mutating_company_list(self):
        companies = [{"symbol": "US:SPCX", "name": "SpaceX", "source": "official", "listed_on": "2026-06-12"},
                     {"symbol": "US:META", "name": "메타"}]
        available, skipped = select_historical_companies(companies, "2025-11-06")
        self.assertEqual([item["symbol"] for item in available], ["US:META"])
        self.assertEqual(skipped[0]["symbol"], "US:SPCX")
        self.assertEqual(len(companies), 2)

    def test_company_list_includes_references_and_requested_tickers(self):
        companies = load_companies()
        self.assertEqual(len(companies), 17)
        self.assertEqual(len({company["symbol"] for company in companies}), 17)
        self.assertTrue({"US:ARM", "US:NVDA", "US:GOOG", "US:GOOGL", "US:AMZN"} <= {company["symbol"] for company in companies})
        self.assertTrue({"US:META", "US:MSFT", "US:TSLA", "US:SPCX"} <= {company["symbol"] for company in companies})
        # peers.json은 이전 연구의 고정 종목군이다. 새 실행 목록과 독립적으로 보존한다.

    def test_current_watchlist_has_all_requested_kis_symbols(self):
        live = json.loads((CONFIG_ROOT / "settings.json").read_text(encoding="utf-8"))
        exchanges = json.loads((CONFIG_ROOT / "kis.json").read_text(encoding="utf-8"))["us_exchanges"]
        expected = "T AVGO GOOGL COIN O SPCX TSLA AMZN IONQ NVDA QCOM IBM JNJ MSFT INTC VZ CVX AMD ARM ASML JOBY MU PLTR LLY META RBLX AAPL ISRG SNDK TEM".split()
        self.assertEqual(live["symbols"], ["US:" + symbol for symbol in expected])
        self.assertEqual(len(set(live["symbols"])), 30)
        self.assertTrue(all(exchanges[symbol] in {"NAS", "NYS", "AMS"} for symbol in expected))
        self.assertFalse(live["collect_news"])

    def test_duplicate_company_is_rejected(self):
        companies = load_companies()
        with patch("pathlib.Path.read_text", return_value=json.dumps({"companies": companies + [companies[0]]})):
            with self.assertRaises(ValueError):
                load_companies()

    def test_common_date_window_excludes_future_and_warmup_pnl(self):
        start = date(2024, 1, 1)
        bars = [{"date": (start + timedelta(days=index)).isoformat()} for index in range(400)]
        warmup, testing = peer_period(bars, bars[200]["date"], bars[350]["date"])
        self.assertEqual(len(warmup), 200)
        self.assertEqual(len(testing), 151)
        self.assertEqual(testing[-1], bars[350])

    def test_short_coverage_rejected(self):
        with self.assertRaises(ValueError):
            peer_period([], "2025-11-06", "2026-06-12")

    def test_incomplete_edge_rejected(self):
        start = date(2024, 1, 1)
        bars = [{"date": (start + timedelta(days=index)).isoformat()} for index in range(400)]
        with self.assertRaises(ValueError):
            peer_period(bars, bars[200]["date"], "2025-03-01")

    def test_reference_split_is_chronological(self):
        bars = list(range(700))
        training, validation, testing = split_reference(bars, {"training_fraction": .6, "validation_fraction": .2})
        self.assertEqual(training, bars[:420])
        self.assertEqual(validation, bars[420:560])
        self.assertEqual(testing, bars[560:])
