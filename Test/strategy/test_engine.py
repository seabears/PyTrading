import copy
import unittest
from datetime import datetime, timedelta, timezone

from strategy.engine import evaluate


from Test.sample_data import sample


class RulesTest(unittest.TestCase):
    def test_both_markets(self):
        for market in ("KR", "US"):
            self.assertEqual(evaluate(sample(market))["action"], "BUY")

    def test_news_not_sufficient(self):
        s = sample()
        s["bars"][-1]["volume"] = 100
        self.assertEqual(evaluate(s)["action"], "WAIT")

    def test_unverified_news(self):
        s = sample()
        s["news_events"][0]["source_verified"] = False
        self.assertEqual(evaluate(s)["action"], "WAIT")

    def test_duplicate_and_corrected_news(self):
        s = sample()
        s["news_events"].append(copy.deepcopy(s["news_events"][0]))
        self.assertEqual(len(evaluate(s)["metrics"]["positive_event_ids"]), 1)
        s["news_events"][-1].update(kind="material_contract_cancelled", available_at=s["now"])
        self.assertEqual(evaluate(s)["reason"], "negative_event_blocks_entry")

    def test_no_lookahead_news(self):
        s = sample()
        s["news_events"][0]["available_at"] = "2026-10-10T16:00:00+00:00"
        self.assertEqual(evaluate(s)["action"], "WAIT")

    def test_future_or_unfinished_bar(self):
        for field, value in (("complete", False), ("available_at", "2026-10-10T16:00:00Z")):
            s = sample()
            s["bars"][-1][field] = value
            self.assertEqual(evaluate(s)["reason"], "invalid_or_unfinished_bar")

    def test_stale_quote(self):
        s = sample()
        s["quote"]["available_at"] = "2026-10-09T15:59:00Z"
        self.assertEqual(evaluate(s)["reason"], "stale_or_future_quote")

    def test_stop_does_not_require_bars(self):
        s = sample()
        s["position"] = {"quantity": 1, "average_cost": 110, "peak_bid_since_entry": 110}
        s["bars"] = []
        self.assertEqual(evaluate(s)["reason"], "stop_loss")

    def test_pending_order_prevents_duplicate(self):
        s = sample()
        s["pending_order"] = True
        self.assertEqual(evaluate(s)["action"], "WAIT")

    def test_same_bar_and_cooldown(self):
        s = sample()
        s["last_entry_signal_bar"] = s["bars"][-1]["end"]
        self.assertEqual(evaluate(s)["reason"], "entry_already_signalled_for_bar")
        del s["last_entry_signal_bar"]
        s["last_exit_at"] = s["now"]
        self.assertEqual(evaluate(s)["reason"], "reentry_cooldown")

    def test_invalid_price(self):
        s = sample()
        s["quote"]["bid"] = float("nan")
        self.assertEqual(evaluate(s)["action"], "WAIT")

    def test_closed_session(self):
        s = sample()
        s["regular_session_open"] = False
        self.assertEqual(evaluate(s)["reason"], "outside_regular_session")

    def test_no_risk_budget(self):
        s = sample()
        s["risk_budget_available"] = False
        self.assertEqual(evaluate(s)["action"], "WAIT")

    def test_stop_with_broken_news(self):
        s = sample()
        s["position"] = {"quantity": 1, "average_cost": 110}
        s["news_events"] = [{}]
        self.assertEqual(evaluate(s)["reason"], "stop_loss")

    def test_held_position_exit_and_hold(self):
        s = sample()
        s["position"] = {"quantity": 1, "average_cost": 100, "peak_bid_since_entry": 102}
        self.assertEqual(evaluate(s)["action"], "HOLD")
        s["news_events"][0]["kind"] = "earnings_guidance_cut"
        self.assertEqual(evaluate(s)["reason"], "confirmed_negative_event")
        s["news_events"] = []
        s["position"]["peak_bid_since_entry"] = 110
        self.assertEqual(evaluate(s)["reason"], "trailing_stop")
        self.assertEqual(evaluate(s, {"breakeven_trigger": 0, "profit_lock_trigger": 0})["reason"], "trailing_stop")
        s["position"]["peak_bid_since_entry"] = 102
        s["bars"][-1]["close"] = 99
        self.assertEqual(evaluate(s)["reason"], "close_below_prior_average")

    def test_missing_clock(self):
        s = sample()
        del s["now"]
        self.assertEqual(evaluate(s)["action"], "WAIT")


    def test_disabled_news_allows_price_entry_without_positive_news(self):
        snapshot = sample()
        snapshot["news_events"] = []
        decision = evaluate(snapshot, {"news_enabled": False})
        self.assertEqual(decision["action"], "BUY")
        self.assertEqual(decision["reason"], "price_breakout_with_volume")
        self.assertFalse(decision["metrics"]["news_enabled"])
        self.assertNotIn("confirmed_positive_event", {item["rule"] for item in decision["checks"]})
        self.assertEqual(evaluate(snapshot)["action"], "WAIT")

    def test_disabled_news_ignores_invalid_and_negative_events(self):
        for events in ([{}], None, [{"kind": "earnings_guidance_cut"}]):
            snapshot = sample()
            snapshot["news_events"] = events
            self.assertEqual(evaluate(snapshot, {"news_enabled": False})["action"], "BUY")
        snapshot = sample()
        snapshot["position"] = {"quantity": 1, "average_cost": 100, "peak_bid_since_entry": 102}
        snapshot["news_events"][0]["kind"] = "earnings_guidance_cut"
        self.assertEqual(evaluate(snapshot, {"news_enabled": False})["action"], "HOLD")
        self.assertEqual(evaluate(snapshot)["reason"], "confirmed_negative_event")

    def test_disabling_news_keeps_volume_budget_and_price_stops(self):
        snapshot = sample()
        snapshot["news_events"] = []
        snapshot["bars"][-1]["volume"] = 100
        self.assertEqual(evaluate(snapshot, {"news_enabled": False})["action"], "WAIT")
        snapshot = sample()
        snapshot["risk_budget_available"] = False
        self.assertEqual(evaluate(snapshot, {"news_enabled": False})["action"], "WAIT")
        snapshot["position"] = {"quantity": 1, "average_cost": 110}
        snapshot["news_events"] = [{}]
        self.assertEqual(evaluate(snapshot, {"news_enabled": False})["reason"], "stop_loss")

    def test_news_flag_rejects_strings_and_numbers(self):
        for value in ("false", 0, 1, None):
            self.assertTrue(evaluate(sample(), {"news_enabled": value})["reason"].startswith("invalid_input"))

if __name__ == "__main__":
    unittest.main()
