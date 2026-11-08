"""반복 연구의 체결·비용·미래 정보·날짜 중복 방지를 합성 입력으로 확인한다."""
import copy
import unittest

from research.daily import benchmark_daily, develop_rules, prepare_daily_bars, rules_for_round, simulate_daily
from tools.research_cycles import overlaps_previous_test


class DailyResearchTests(unittest.TestCase):
    def setUp(self):
        self.costs = {"starting_cash": {"KR": 10000, "US": 10000}, "allocation_fraction": 0.1,
                      "buy_cost_ratio": 0, "sell_cost_ratio": 0, "slippage_ratio": 0}
        self.rule = {"family": "breakout", "lookback": 2, "volume_ratio": 1, "trend_filter": False,
                     "trend_days": 100, "stop_loss": 0.03, "trailing_stop": 0.08, "holding_days": 20,
                     "cooldown_days": 3, "max_chase": 0.1}
        prices = [(10, 10, 9.8, 9.9), (10, 10, 9.8, 9.9), (10, 10.6, 10, 10.5), (10.8, 10.8, 10.8, 10.8)]
        self.bars = [{"date": f"2025-01-{index + 1:02d}", "open": row[0], "high": row[1],
                      "low": row[2], "close": row[3], "volume": 100} for index, row in enumerate(prices)]

    def test_next_day_fill_and_period_end_liquidation(self):
        result = simulate_daily(self.bars, "US", self.rule, self.costs, 0)
        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["trades"][0]["entry_price"], 10.8)
        self.assertEqual(result["trades"][0]["entry_date"], "2025-01-04")
        self.assertAlmostEqual(result["summary"]["net_return"], 0)

    def test_costs_match_cash_conservation(self):
        costs = {**self.costs, "buy_cost_ratio": 0.001, "sell_cost_ratio": 0.002, "slippage_ratio": 0.001}
        result = simulate_daily(self.bars, "US", self.rule, costs, 0.001)
        trade = result["trades"][0]
        pnl = trade["quantity"] * (trade["exit_price"] * 0.998 - trade["entry_price"] * 1.001)
        self.assertAlmostEqual(result["summary"]["net_pnl"], pnl)
        self.assertLess(result["summary"]["net_return"], 0)

    def test_gap_stop_never_gets_better_fictitious_stop_fill(self):
        bars = copy.deepcopy(self.bars)
        bars.append({**bars[-1], "date": "2025-01-05", "open": 8, "high": 9, "low": 7, "close": 8})
        result = simulate_daily(bars, "US", self.rule, self.costs, 0)
        self.assertEqual(result["trades"][0]["exit_price"], 8)

    def test_chasing_gap_cancels_entry(self):
        bars = copy.deepcopy(self.bars)
        bars[-1].update(open=20, high=20, low=20, close=20)
        self.assertEqual(simulate_daily(bars, "US", self.rule, self.costs, 0)["summary"]["trades"], 0)

    def test_external_filter_blocks_new_entry(self):
        result = simulate_daily(self.bars, "US", self.rule, self.costs, 0, entry_filter=lambda day: False)
        self.assertEqual(result["summary"]["trades"], 0)
        self.assertEqual(result["entry_filter_blocks"], 1)

    def test_external_filter_does_not_block_stop_exit(self):
        bars = copy.deepcopy(self.bars)
        bars.append({**bars[-1], "date": "2025-01-05", "open": 8, "high": 9, "low": 7, "close": 8})
        result = simulate_daily(bars, "US", self.rule, self.costs, 0, entry_filter=lambda day: day == "2025-01-03")
        self.assertEqual(result["trades"][0]["exit_price"], 8)
        self.assertEqual(result["trades"][0]["reason"], "gap_adjusted_stop")

    def test_warmup_prices_do_not_create_account_pnl_or_trades(self):
        warmup = [{**self.bars[0], "date": "2024-12-01", "open": 1000, "close": 1000, "high": 1000, "low": 1000}] * 120
        result = simulate_daily([self.bars[0]], "US", self.rule, self.costs, 0, warmup)
        self.assertEqual(result["summary"]["trades"], 0)
        self.assertAlmostEqual(result["summary"]["net_return"], 0)

    def test_rounds_are_bounded_and_each_has_eight_candidates(self):
        for stage in ("breakout", "trend_filter", "pullback"):
            self.assertEqual(len(rules_for_round(stage)), 8)
        with self.assertRaises(ValueError):
            rules_for_round("unknown")

    def test_development_does_not_need_test_prices(self):
        settings = {"rounds": ["breakout", "trend_filter", "pullback"], "assumed_spread_ratio": 0.001,
                    "minimum_training_trades": 10, "minimum_validation_trades": 5}
        result = develop_rules(self.bars * 30, self.bars * 10, "US", self.costs, settings)
        self.assertEqual(len(result["rounds"]), 3)
        self.assertNotIn("test", result)

    def test_overlapping_dates_detected_across_different_sources(self):
        periods = [{"key": "US:AAPL", "start": "2026-09-17", "end": "2026-10-09", "fingerprint": "old"}]
        self.assertTrue(overlaps_previous_test("US:AAPL", "2026-09-01", "2026-09-20", "new", periods))
        self.assertFalse(overlaps_previous_test("US:AAPL", "2026-03-01", "2026-06-12", "new", periods))
        self.assertFalse(overlaps_previous_test("US:AAPL", "2026-09-17", "2026-10-09", "old", periods))

    def test_daily_price_validation_and_same_budget_benchmark(self):
        record = {"market": "US", "interval": "1d", "candles": [
            {"timestamp": "2025-01-01T00:00:00+09:00", "currency": "USD", "openPrice": "100", "highPrice": "110",
             "lowPrice": "90", "closePrice": "110", "volume": "100"}]}
        bars = prepare_daily_bars(record)
        self.assertEqual(bars[0]["date"], "2025-01-01")
        self.assertAlmostEqual(benchmark_daily(bars, "US", self.costs, 0), 0.01)
        record["candles"][0]["closePrice"] = "200"
        with self.assertRaises(ValueError):
            prepare_daily_bars(record)
