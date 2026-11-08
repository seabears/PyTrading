"""예상치의 기간·수신 시각·회계 기준 불명·데모 한계를 검증한다."""
import copy
import unittest

from news.consensus import alpha_calendar, alpha_observations, numeric


class ConsensusTests(unittest.TestCase):
    def setUp(self):
        self.stamp = "2026-10-25T12:00:00+00:00"
        self.payload = {"symbol": "IBM", "estimates": [
            {"date": "2026-12-31", "horizon": "fiscal quarter", "eps_estimate_average": "2.5",
             "revenue_estimate_average": "10000000", "eps_estimate_average_7_days_ago": "2.4"}]}

    def test_two_metrics_are_observations_and_never_auto_approved(self):
        rows = alpha_observations(self.payload, self.stamp)["observations"]
        self.assertEqual({row["metric"] for row in rows}, {"eps", "revenue"})
        self.assertTrue(all(row["status"] == "observation_only" and row["trading_eligible"] is False for row in rows))

    def test_period_end_is_not_release_or_received_time(self):
        row = alpha_observations(self.payload, self.stamp)["observations"][0]
        self.assertEqual(row["period_end"], "2026-12-31")
        self.assertEqual(row["observed_at"], self.stamp)
        self.assertIsNone(row["report_at"])
        self.assertIsNone(row["period_start"])

    def test_gaap_currency_units_are_not_guessed(self):
        row = alpha_observations(self.payload, self.stamp)["observations"][0]
        self.assertIsNone(row["basis"])
        self.assertIsNone(row["currency"])
        self.assertIsNone(row["unit"])

    def test_revision_values_do_not_create_fake_historical_snapshots(self):
        rows = alpha_observations(self.payload, self.stamp)["observations"]
        self.assertTrue(all(row["observed_at"] == self.stamp for row in rows))
        self.assertEqual(len(rows), 2)

    def test_annual_horizon_is_not_quarterly(self):
        self.payload["estimates"][0]["horizon"] = "fiscal year"
        self.assertFalse(alpha_observations(self.payload, self.stamp)["observations"])

    def test_past_period_observation_is_not_claimed_pre_release(self):
        self.payload["estimates"][0]["date"] = "2026-06-30"
        row = alpha_observations(self.payload, self.stamp)["observations"][0]
        self.assertFalse(row["future_period_candidate"])

    def test_personal_key_access_does_not_imply_validation(self):
        row = alpha_observations(self.payload, self.stamp, demo=False)["observations"][0]
        self.assertFalse(row["trading_eligible"])

    def test_error_object_is_not_empty_success(self):
        with self.assertRaises(ValueError):
            alpha_observations({"Information": "request limit"}, self.stamp)

    def test_wrong_symbol_is_rejected(self):
        self.payload["symbol"] = "AAPL"
        with self.assertRaises(ValueError):
            alpha_observations(self.payload, self.stamp)

    def test_received_time_requires_timezone(self):
        with self.assertRaises(ValueError):
            alpha_observations(self.payload, "2026-10-25T12:00:00")

    def test_missing_eps_is_not_zero_and_negative_eps_is_valid(self):
        self.payload["estimates"][0]["eps_estimate_average"] = None
        report = alpha_observations(self.payload, self.stamp)
        self.assertEqual([row["metric"] for row in report["observations"]], ["revenue"])
        self.payload["estimates"][0]["eps_estimate_average"] = "-1.5"
        self.assertEqual(alpha_observations(self.payload, self.stamp)["observations"][0]["value"], -1.5)

    def test_invalid_numbers_are_rejected(self):
        for value in (True, float("inf"), "NaN", None):
            with self.assertRaises(ValueError):
                numeric(value)

    def test_duplicate_period_is_rejected(self):
        self.payload["estimates"].append(copy.deepcopy(self.payload["estimates"][0]))
        with self.assertRaises(ValueError):
            alpha_observations(self.payload, self.stamp)

    def test_empty_calendar_and_error_json_are_different(self):
        report = alpha_calendar(b"symbol,name,reportDate,fiscalDateEnding,estimate,currency\r\n")
        self.assertEqual(report["status"], "valid_header_but_no_rows")
        with self.assertRaises(ValueError):
            alpha_calendar(b'{"Information":"API key required"}')
