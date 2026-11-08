"""차단 집계·조건 단일 변경·시험 제외 선택·기업행동 경고를 합성 입력으로 확인한다."""
import copy
import unittest

from research.daily import signal_details, simulate_daily
from tools.analyze_conditions import aggregate_development, choose_candidate, load_condition_settings, price_discontinuities, variant_rule


class DiagnosticTest(unittest.TestCase):
    def setUp(self):
        self.rule = {"family": "breakout", "lookback": 2, "volume_ratio": 1, "trend_filter": False,
                     "trend_days": 100, "stop_loss": .03, "trailing_stop": .08, "holding_days": 20,
                     "cooldown_days": 3, "max_chase": .1}
        self.bars = [{"date": f"2025-01-{index + 1:02d}", "open": opening, "high": high, "low": low, "close": closing, "volume": 100}
                     for index, (opening, high, low, closing) in enumerate([(10, 10, 9.8, 9.9), (10, 10, 9.8, 9.9), (10, 10.6, 10, 10.5), (10.8, 10.8, 10.8, 10.8)])]
        self.costs = {"starting_cash": {"US": 10000}, "allocation_fraction": .1, "buy_cost_ratio": 0, "sell_cost_ratio": 0, "slippage_ratio": 0}

    def test_eligible_days_reconcile_with_first_blocks_and_plans(self):
        result = simulate_daily(self.bars, "US", self.rule, self.costs, 0)
        diagnostic = result["diagnostics"]
        self.assertEqual(diagnostic["eligible_days"], sum(diagnostic["first_blocks"].values()) + diagnostic["orders_planned"])
        self.assertEqual(diagnostic["orders_planned"], diagnostic["entries"] + diagnostic["gap_cancellations"] + diagnostic["cash_cancellations"])
        self.assertEqual(sum(diagnostic[name] for name in ("eligible_days", "position_days", "cooldown_days", "last_day")), len(self.bars))

    def test_cash_and_gap_cancellations_are_separate(self):
        tiny_costs = {**self.costs, "starting_cash": {"US": 1}}
        result = simulate_daily(self.bars, "US", self.rule, tiny_costs, 0)
        self.assertEqual(result["diagnostics"]["cash_cancellations"], 1)
        self.assertEqual(result["diagnostics"]["gap_cancellations"], 0)
        bars = copy.deepcopy(self.bars)
        bars[-1].update(open=20, high=20, low=20, close=20)
        self.assertEqual(simulate_daily(bars, "US", self.rule, self.costs, 0)["diagnostics"]["gap_cancellations"], 1)

    def test_independent_failures_can_overlap(self):
        bars = copy.deepcopy(self.bars[:3])
        bars[-1].update(volume=1, close=15, high=15)
        detail = signal_details(bars, self.rule)
        self.assertFalse(detail["conditions"]["volume"])
        self.assertFalse(detail["conditions"]["chase"])
        self.assertTrue(detail["conditions"]["price_signal"])

    def test_single_condition_change_preserves_original(self):
        before = dict(self.rule)
        rule = variant_rule(self.rule, "no_volume", load_condition_settings())
        self.assertFalse(rule["volume_filter"])
        self.assertEqual(self.rule, before)
        self.assertEqual(rule["stop_loss"], before["stop_loss"])

    def test_candidate_selection_does_not_read_test_result(self):
        item = {"training_mean": .01, "validation_mean": .02, "validation_mean_drawdown": .01,
                "validation_stress_mean": .01, "validation_positive_fraction": .6, "validation_excess_mean": .01}
        aggregates = {"good": item, "bad": {**item, "training_mean": -.01, "test_return": 999}}
        self.assertEqual(choose_candidate(aggregates, load_condition_settings()), "good")

    def test_no_eligible_candidate_remains_none(self):
        aggregates = {"bad": {"training_mean": -1}}
        self.assertIsNone(choose_candidate(aggregates, load_condition_settings()))

    def test_positive_profit_below_buy_and_hold_is_rejected(self):
        item = {"training_mean": .01, "validation_mean": .02, "validation_mean_drawdown": .01,
                "validation_stress_mean": .01, "validation_positive_fraction": .8, "validation_excess_mean": -.01}
        self.assertIsNone(choose_candidate({"looks_profitable": item}, load_condition_settings()))

    def test_trend_follow_requires_long_history_and_keeps_original_rule(self):
        before = dict(self.rule)
        rule = variant_rule(self.rule, "trend_follow", load_condition_settings())
        self.assertEqual(rule["trend_days"], 200)
        self.assertEqual(rule["family"], "trend_follow")
        self.assertFalse(signal_details(self.bars, rule)["passed"])
        self.assertEqual(self.rule, before)

    def test_split_like_discontinuity_is_flagged_without_mutation(self):
        bars = [{"date": "2024-06-07", "close": 1000, "open": 1000}, {"date": "2024-06-10", "close": 100, "open": 100}]
        self.assertEqual(price_discontinuities(bars)[0]["open_vs_previous_close"], .1)
        self.assertEqual(bars[0]["close"], 1000)

    def test_same_company_share_class_and_quality_warning_are_excluded(self):
        summary = {"net_return": .01, "max_drawdown": .01, "trades": 2}
        comparison = {"training": {"summary": summary}, "validation": {"summary": summary}, "validation_stress": summary}
        results = {key: {"comparisons": {"baseline": comparison}, "validation_benchmark": 0, "price_warnings": ([{}] if key == "US:NVDA" else [])}
                   for key in ("US:AAPL", "US:NVDA", "US:GOOG", "US:GOOGL")}
        companies = [{"symbol": key} for key in results]
        result = aggregate_development(results, companies, ["baseline"], exclude_price_warnings=True)
        self.assertEqual(result["baseline"]["company_count"], 2)
        self.assertEqual(result["baseline"]["validation_trades"], 4)
