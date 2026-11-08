"""합성 지표로 시간 누수·누락 처리를 검증한다. 수익성 테스트와 분리한다."""
import json
import unittest
from datetime import date, timedelta

from paths import PROJECT_ROOT, CONFIG_ROOT
from research.indicators import available_values, make_entry_filter, prepare_series, validate_settings
from broker.toss import READ_PATHS


class IndicatorTest(unittest.TestCase):
    def setUp(self):
        self.settings = validate_settings(json.loads((CONFIG_ROOT / "indicators.json").read_text(encoding="utf-8")))

    def test_future_and_same_day_are_excluded(self):
        series = prepare_series([{"date": "2026-01-01", "value": 20}, {"date": "2026-01-02", "value": 99}, {"date": "2026-01-03", "value": 999}])
        self.assertEqual(available_values(series, "2026-01-03", self.settings), [20])

    def test_stale_and_missing_block_entry(self):
        for rows in ([], [{"date": "2026-01-01", "value": 20}]):
            check = make_entry_filter("vix", {"vix": prepare_series(rows)}, self.settings)
            self.assertFalse(check("2026-02-01"))

    def test_vix_limit(self):
        for value, expected in ((25, True), (26, False), (0, False)):
            check = make_entry_filter("vix", {"vix": prepare_series([{"date": "2026-01-01", "value": value}])}, self.settings)
            self.assertEqual(check("2026-01-03"), expected)

    def test_market_requires_history_and_uptrend(self):
        first = date(2026, 1, 1)
        rows = [{"date": (first + timedelta(days=index)).isoformat(), "value": 100 + index} for index in range(50)]
        self.assertTrue(make_entry_filter("market", {"market": prepare_series(rows)}, self.settings)("2026-02-21"))
        self.assertFalse(make_entry_filter("market", {"market": prepare_series(rows[:20])}, self.settings)("2026-01-22"))

    def test_bond_uses_percentage_points(self):
        first = date(2026, 1, 1)
        for increase, expected in ((0.20, True), (0.30, False)):
            rows = [{"date": (first + timedelta(days=index)).isoformat(), "value": 3 + (increase if index == 20 else 0)} for index in range(21)]
            self.assertEqual(make_entry_filter("bond", {"bond": prepare_series(rows)}, self.settings)("2026-01-23"), expected)

    def test_duplicate_and_nonfinite_rejected(self):
        for rows in ([{"date": "2026-01-01", "value": "nan"}], [{"date": "2026-01-01", "value": 1}] * 2):
            with self.assertRaises(ValueError):
                prepare_series(rows)

    def test_lag_and_boolean_settings_rejected(self):
        for changes in ({"lag_calendar_days": 1}, {"market_trend_days": True}, {"maximum_vix": float("inf")}):
            with self.assertRaises(ValueError):
                validate_settings({**self.settings, **changes})

    def test_baseline_and_unknown_mode(self):
        self.assertTrue(make_entry_filter("baseline", {}, self.settings)("2026-01-03"))
        with self.assertRaises(ValueError):
            make_entry_filter("unknown", {}, self.settings)

    def test_api_allowlist_stays_explicit(self):
        self.assertIn("/api/v1/market-indicators/KOSPI/candles", READ_PATHS)
        self.assertNotIn("/api/v1/accounts", READ_PATHS)
        self.assertNotIn("/api/v1/market-indicators/arbitrary/candles", READ_PATHS)
