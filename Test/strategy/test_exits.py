"""원가 보호 활성화·순이익 계산·보조 데이터 오류·기존 손절 우선순위를 검사한다."""
import unittest
from strategy.engine import evaluate
from strategy.exits import PROFIT_EXIT_DEFAULTS, profit_exit_floor
from Test.sample_data import sample


class ProfitExitsTest(unittest.TestCase):
    def test_not_active_before_net_profit_trigger(self):
        self.assertIsNone(profit_exit_floor(100, 103, .997, PROFIT_EXIT_DEFAULTS))

    def test_breakeven_floor_pays_sell_costs_and_leaves_buffer(self):
        price, reason = profit_exit_floor(100, 104, .997, PROFIT_EXIT_DEFAULTS)
        self.assertEqual(reason, "breakeven_protection")
        self.assertAlmostEqual(price * .997, 100.2)

    def test_lock_keeps_half_of_net_peak_profit(self):
        price, reason = profit_exit_floor(100, 110, .997, PROFIT_EXIT_DEFAULTS)
        self.assertEqual(reason, "profit_lock")
        self.assertAlmostEqual(price * .997 - 100, (110 * .997 - 100) * .5)

    def test_price_protection_precedes_broken_news_and_bars(self):
        for peak, bid, reason in ((104, 100.4, "breakeven_protection"), (106, 102, "profit_lock")):
            snapshot = sample()
            snapshot.update(position={"quantity": 1, "average_cost": 100, "peak_bid_since_entry": peak},
                            news_events=[{}], bars=[])
            snapshot["quote"].update(bid=bid, ask=bid + .1)
            self.assertEqual(evaluate(snapshot)["reason"], reason)

    def test_cost_assumption_from_account_changes_floor(self):
        snapshot = sample()
        snapshot["position"] = {"quantity": 1, "average_cost": 100, "peak_bid_since_entry": 104,
                                "sell_proceeds_ratio": .99}
        snapshot["quote"].update(bid=100.8, ask=100.9)
        self.assertEqual(evaluate(snapshot)["action"], "HOLD")  # 순고점 수익 2.96%: 미활성.
        snapshot["position"]["peak_bid_since_entry"] = 105
        self.assertEqual(evaluate(snapshot)["reason"], "breakeven_protection")

    def test_stale_quote_cannot_trigger_exit(self):
        snapshot = sample()
        snapshot["position"] = {"quantity": 1, "average_cost": 100, "peak_bid_since_entry": 110}
        snapshot["quote"]["available_at"] = "2026-10-09T15:59:00Z"
        self.assertEqual(evaluate(snapshot)["reason"], "stale_or_future_quote")

    def test_invalid_and_disabled_policy(self):
        for invalid in (float("nan"), True, -.1, 1):
            with self.assertRaises(ValueError):
                profit_exit_floor(100, 110, .997, {**PROFIT_EXIT_DEFAULTS, "profit_keep_ratio": invalid})
        self.assertIsNone(profit_exit_floor(100, 110, .997, {**PROFIT_EXIT_DEFAULTS,
                                                         "breakeven_trigger": 0, "profit_lock_trigger": 0}))

    def test_gap_loss_is_still_possible(self):
        snapshot = sample()
        snapshot["position"] = {"quantity": 1, "average_cost": 100, "peak_bid_since_entry": 110}
        snapshot["quote"].update(bid=95, ask=95.1)
        decision = evaluate(snapshot)
        self.assertEqual(decision["reason"], "stop_loss")
        self.assertLess(decision["metrics"]["return_at_bid"], 0)
