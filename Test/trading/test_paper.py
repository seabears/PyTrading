"""모의 자금 보존·비용·복구·중복 방지를 가상 입력으로 검증한다."""
import copy
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from strategy.engine import parse_timestamp
from trading.paper import PAPER_DEFAULTS, PaperAccount
from Test.sample_data import sample


from Test.sample_data import later


class PaperTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix=".test-", dir=Path(__file__).parent)
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "account.json"
        self.account = PaperAccount(self.path)

    def test_buy_budget_and_costs(self):
        decision = self.account.evaluate_snapshot(sample())
        trade = decision["paper_fill"]
        expected_price = 101 * 1.001
        expected_cost = 9 * expected_price * 1.001
        self.assertEqual(trade["quantity"], 9)
        self.assertAlmostEqual(trade["price"], expected_price)
        self.assertAlmostEqual(trade["fees"], 9 * expected_price * 0.001)
        self.assertAlmostEqual(self.account.state["cash"]["US"], 10000 - expected_cost)
        self.assertLessEqual(expected_cost, 1000)

    def test_stop_loss_cash_conservation_and_restart(self):
        snapshot = sample()
        buy = self.account.evaluate_snapshot(snapshot)["paper_fill"]
        restored = PaperAccount(self.path)
        sell = restored.evaluate_snapshot(later(snapshot, bid=95))["paper_fill"]
        self.assertEqual(sell["reason"], "stop_loss")
        self.assertAlmostEqual(sell["realized_pnl"], buy["cash_flow"] + sell["cash_flow"])
        self.assertAlmostEqual(restored.state["cash"]["US"], 10000 + sell["realized_pnl"])
        self.assertEqual(restored.state["positions"], {})
        self.assertAlmostEqual(restored.summary()["US"]["pnl_at_last_quote"], sell["realized_pnl"])

    def test_same_input_and_restart_do_not_trade_twice(self):
        snapshot = sample()
        self.account.evaluate_snapshot(snapshot)
        restored = PaperAccount(self.path)
        self.assertEqual(restored.evaluate_snapshot(snapshot)["reason"], "already_processed_snapshot")
        self.assertEqual(len(restored.state["trades"]), 1)

    def test_older_input_does_not_change_state(self):
        snapshot = sample()
        self.account.evaluate_snapshot(snapshot)
        before = copy.deepcopy(self.account.state)
        self.assertEqual(self.account.evaluate_snapshot(later(snapshot, seconds=-60))["action"], "WAIT")
        self.assertEqual(before, self.account.state)

    def test_markets_have_separate_cash(self):
        self.account.evaluate_snapshot(sample("KR"))
        self.assertEqual(self.account.state["cash"]["US"], 10000)
        self.account.evaluate_snapshot(sample("US"))
        self.assertEqual(set(self.account.state["positions"]), {"KR:DEMO_KR", "US:DEMO_US"})

    def test_position_limit_blocks_other_symbol(self):
        self.account = PaperAccount(self.path, {"max_positions_per_market": 1})
        self.account.evaluate_snapshot(sample())
        second = sample()
        second["symbol"] = "OTHER"
        second["news_events"][0]["symbol"] = "OTHER"
        self.assertEqual(self.account.evaluate_snapshot(second)["action"], "WAIT")
        self.assertEqual(len(self.account.state["trades"]), 1)

    def test_fresh_peak_and_stale_peak(self):
        snapshot = sample()
        self.account.evaluate_snapshot(snapshot)
        self.account.evaluate_snapshot(later(snapshot, bid=105))
        self.assertEqual(self.account.state["positions"]["US:DEMO_US"]["peak_bid_since_entry"], 105)
        stale = later(snapshot, seconds=120, bid=200)
        stale["quote"]["available_at"] = snapshot["now"]
        self.assertEqual(self.account.evaluate_snapshot(stale)["reason"], "stale_or_future_quote")
        self.assertEqual(self.account.state["positions"]["US:DEMO_US"]["peak_bid_since_entry"], 105)

    def test_broken_news_does_not_block_price_stop(self):
        snapshot = sample()
        self.account.evaluate_snapshot(snapshot)
        changed = later(snapshot, bid=95)
        changed["news_events"] = [{}]
        self.assertEqual(self.account.evaluate_snapshot(changed)["reason"], "stop_loss")

    def test_no_news_cannot_buy(self):
        snapshot = sample()
        snapshot["news_events"] = []
        self.assertEqual(self.account.evaluate_snapshot(snapshot)["action"], "WAIT")
        self.assertEqual(self.account.state["trades"], [])

    def test_breakeven_protection_survives_restart_and_pays_costs(self):
        snapshot = sample()
        buy = self.account.evaluate_snapshot(snapshot)["paper_fill"]
        self.assertEqual(self.account.evaluate_snapshot(later(snapshot, bid=105))["action"], "HOLD")
        restored = PaperAccount(self.path)
        falling = later(snapshot, seconds=120, bid=101.65)
        falling["news_events"] = [{}]
        falling["bars"] = []
        sell = restored.evaluate_snapshot(falling)["paper_fill"]
        self.assertEqual(sell["reason"], "breakeven_protection")
        self.assertGreater(sell["realized_pnl"], 0)
        self.assertAlmostEqual(sell["realized_pnl"], sell["cash_flow"] + buy["cash_flow"])

    def test_changed_settings_require_separate_account(self):
        self.account.evaluate_snapshot(sample())
        with self.assertRaises(ValueError):
            PaperAccount(self.path, {"slippage_ratio": 0.01})

    def test_insufficient_budget(self):
        account = PaperAccount(self.path, {"starting_cash": {"KR": 1000, "US": 100}})
        self.assertEqual(account.evaluate_snapshot(sample())["reason"], "paper_budget_below_one_share")
        self.assertEqual(account.state["trades"], [])

    def test_corrupted_file_is_not_reset(self):
        self.path.write_text("broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            PaperAccount(self.path)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "broken")


if __name__ == "__main__":
    unittest.main()
