"""기간·기준·단위·시각이 다른 수치를 검증 완료로 올리지 않는지 확인한다."""
import copy
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from news.earnings_validation import quarter_facts, validate_claim
from news.earnings_audit import extract_release
from news.earnings import load_policy, classify
from strategy.engine import evaluate
from Test.news.test_earnings import snapshot


class OfficialEarningsValidationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 25, tzinfo=timezone.utc)
        self.official = {"status": "found", "symbol": "AAPL", "period_start": "2026-03-29",
                         "period_end": "2026-06-27", "basis": "GAAP", "unit": "USD/shares", "val": 2.02,
                         "available_at": "2026-07-31T12:00:00+00:00"}
        self.claim = {"metric": "eps", "symbol": "AAPL", "period_start": "2026-03-29", "period_end": "2026-06-27",
                      "basis": "GAAP", "unit": "USD/shares", "actual": 2.02, "estimate": 1.9,
                      "released_at": "2026-07-30T20:30:00+00:00", "estimate_observed_at": "2026-07-30T12:00:00+00:00",
                      "verified_at": "2026-08-01T00:00:00+00:00", "official_url": "https://data.sec.gov/test",
                      "estimate_url": "https://www.reuters.com/test", "estimate_snapshot_sha256": "a" * 64}

    def test_same_basis_period_and_prior_estimate_can_pass(self):
        self.assertTrue(validate_claim(self.claim, self.official, self.now)["verified"])

    def test_gaap_and_non_gaap_cannot_mix(self):
        self.claim["basis"] = "non-GAAP"
        self.assertFalse(validate_claim(self.claim, self.official, self.now)["verified"])

    def test_ytd_or_other_quarter_is_rejected(self):
        self.claim["period_start"] = "2025-09-28"
        self.assertFalse(validate_claim(self.claim, self.official, self.now)["verified"])

    def test_currency_or_per_share_unit_mismatch_is_rejected(self):
        self.claim["unit"] = "EUR/shares"
        self.assertFalse(validate_claim(self.claim, self.official, self.now)["verified"])

    def test_retroactive_consensus_without_prior_snapshot_is_rejected(self):
        self.claim["estimate_observed_at"] = "2026-08-01T00:00:00+00:00"
        self.assertFalse(validate_claim(self.claim, self.official, self.now)["verified"])

    def test_missing_estimate_is_not_invented(self):
        del self.claim["estimate"]
        self.assertFalse(validate_claim(self.claim, self.official, self.now)["verified"])

    def test_untrusted_official_domain_is_rejected(self):
        self.claim["official_url"] = "https://data.sec.gov.evil.example/test"
        self.assertFalse(validate_claim(self.claim, self.official, self.now)["verified"])

    def test_untrusted_consensus_source_is_rejected(self):
        self.claim["estimate_url"] = "https://reuters.com.evil.example/test"
        self.assertFalse(validate_claim(self.claim, self.official, self.now)["verified"])

    def test_future_verification_is_rejected(self):
        self.claim["verified_at"] = "2026-10-26T00:00:00+00:00"
        self.assertFalse(validate_claim(self.claim, self.official, self.now)["verified"])

    def test_tolerance_cannot_be_overridden_to_hide_wrong_value(self):
        self.claim.update(actual=999, rounding_tolerance=1000)
        self.assertFalse(validate_claim(self.claim, self.official, self.now)["verified"])

    def test_annual_eps_is_not_quarter_eps(self):
        facts = {"facts": {"us-gaap": {"EarningsPerShareDiluted": {"units": {"USD/shares": [
            {"start": "2025-07-01", "end": "2026-06-30", "val": 17.95, "filed": "2026-07-29", "form": "10-K"}]}}}}}
        self.assertEqual(quarter_facts(facts, "EarningsPerShareDiluted", "USD/shares", "2026-06-30", "2026-10-25")["status"], "no_standalone_quarter_fact")

    def test_later_filing_does_not_replace_original_fact(self):
        facts = {"facts": {"us-gaap": {"EarningsPerShareDiluted": {"units": {"USD/shares": [
            {"start": "2026-04-01", "end": "2026-06-30", "val": 1, "filed": "2026-07-29", "form": "10-Q"},
            {"start": "2026-04-01", "end": "2026-06-30", "val": 2, "filed": "2026-08-29", "form": "10-Q"}]}}}}}
        result = quarter_facts(facts, "EarningsPerShareDiluted", "USD/shares", "2026-06-30", "2026-10-25")
        self.assertEqual(result["val"], 1)
        self.assertTrue(result["later_value_changed"])

    def test_unverified_headline_cannot_buy_or_force_news_sale(self):
        with patch("news.earnings_validation.eligible_event_ids", return_value={}):
            row = snapshot()
            result = evaluate(row, {"news_enabled": False, "earnings_enabled": True})
            self.assertEqual(result["reason"], "earnings_awaiting_verification")
            row = snapshot("Apple revenue misses estimates")
            row["position"] = {"quantity": 1, "average_cost": 100, "peak_bid_since_entry": 101}
            self.assertEqual(evaluate(row, {"news_enabled": False, "earnings_enabled": True})["action"], "HOLD")

    def test_gaap_phrase_does_not_fall_through_to_footnote_dollar_amount(self):
        raw = b'''<p>January 28, 2026 Microsoft Corp. today announced results for the quarter ended December 31, 2025.
        Revenue was $80.0 billion. Diluted earnings per share on a GAAP basis was $4.20 and increased 10%,
        and on a non-GAAP basis was $3.10. Later, earnings per share was $999.0 in a different footnote.</p>'''
        row = extract_release(raw, "MSFT")
        self.assertEqual(row["ir_eps_gaap"], 4.2)
        self.assertEqual(row["ir_eps_non_gaap"], 3.1)

    def test_missing_quarter_eps_is_not_replaced_with_distant_note(self):
        raw = ('<p>January 28, 2026 quarter ended December 31, 2025. Revenue was $80.0 billion. '
               + 'Unrelated text. ' * 200 + 'Earnings per share was $999.</p>').encode()
        with self.assertRaises(ValueError):
            extract_release(raw, "MSFT")

    def test_old_release_verification_cannot_approve_a_new_reused_headline(self):
        row = snapshot()
        policy = load_policy()
        from strategy.engine import parse_timestamp
        now = parse_timestamp(row["now"])
        event = classify(row["earnings_events"][0], policy, now)
        record = {event["event_id"]: {"symbol": "AAPL", "direction": "positive",
            "released_at": "2026-07-30T20:00:00+00:00", "verified_at": "2026-07-31T12:00:00+00:00"}}
        with patch("news.earnings_validation.eligible_event_ids", return_value=record):
            self.assertEqual(evaluate(row, {"news_enabled": False, "earnings_enabled": True})["reason"], "earnings_awaiting_verification")

    def test_fresh_verified_release_still_requires_normal_entry_rules(self):
        row = snapshot()
        from strategy.engine import parse_timestamp
        now = parse_timestamp(row["now"])
        event = classify(row["earnings_events"][0], load_policy(), now)
        record = {event["event_id"]: {"symbol": "AAPL", "direction": "positive",
            "released_at": "2026-10-09T15:00:00+00:00", "verified_at": "2026-10-09T15:59:00+00:00"}}
        with patch("news.earnings_validation.eligible_event_ids", return_value=record):
            self.assertEqual(evaluate(row, {"news_enabled": False, "earnings_enabled": True})["action"], "BUY")
            row["bars"][-1]["volume"] = 100
            self.assertEqual(evaluate(row, {"news_enabled": False, "earnings_enabled": True})["action"], "WAIT")
