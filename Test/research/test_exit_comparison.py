"""손절선의 적용 시점·갭·공동 자금·비용 검산. 실제 주문은 사용하지 않는다."""
import copy
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Code"))
sys.path.insert(0, str(Path(__file__).parent))
from exit_comparison_core import VARIANTS, execution, initial_stop, next_stop, replay
from exit_comparison_experiment import choose_candidate


VARIANT = {row["name"]: row for row in VARIANTS}
COSTS = {"starting_cash": {"US": 10000}, "allocation_fraction": .1, "max_positions_per_market": 5,
         "buy_cost_ratio": 0, "sell_cost_ratio": 0, "slippage_ratio": 0}
POLICY = {"spread_ratio": 0, "risk_budget": .0025, "maximum_entry_gap": .03, "holding_sessions": 20}


def inputs(count=25, symbols=("TEST",)):
    days = [f"2026-01-{index + 1:02d}" for index in range(count)]
    series = {symbol: [{"date": day, "open": 100, "high": 101, "low": 99, "close": 100, "volume": 100}
                       for day in days] for symbol in symbols}
    features = {symbol: [{"date": day, "atr": 2} for day in days] for symbol in symbols}
    opportunities = {days[0]: [{"symbol": symbol, "date": days[0], "level": 99, "close": 100,
                               "atr": 2, "score": 1} for symbol in symbols]}
    return series, features, days, opportunities


def run_case(variant="hold20", changed=None, costs=None, policy=None):
    series, features, days, opportunities = changed or inputs()
    return replay(series, features, days, opportunities, VARIANT[variant], costs or COSTS,
                  policy or POLICY, days[0], days[-1])


class ExitComparisonTests(unittest.TestCase):
    def test_fixed_and_atr_initial_stops(self):
        self.assertEqual(initial_stop(100, 2, VARIANT["fixed3"]), 97)
        self.assertEqual(initial_stop(100, 2, VARIANT["atr25"]), 95)
        self.assertIsNone(initial_stop(100, 2, VARIANT["hold20"]))

    def test_trailing_stop_never_moves_down(self):
        self.assertEqual(next_stop(98, 101, 10, VARIANT["atr25_trail3"]), 98)

    def test_signal_enters_next_open_and_expires_on_twentieth_session(self):
        result = run_case()
        self.assertEqual(result["entries"][0]["entry_date"], "2026-01-02")
        self.assertEqual(result["trades"][0]["exit_date"], "2026-01-21")
        self.assertEqual(result["trades"][0]["reason"], "holding20_close")

    def test_current_high_cannot_raise_stop_and_sell_same_day(self):
        data = inputs()
        data[0]["TEST"][1].update(high=120, low=99, close=110)
        data[0]["TEST"][2].update(open=115, high=116, low=114, close=115)
        result = run_case("fixed3_trail4", data)
        self.assertEqual(result["trades"][0]["exit_date"], "2026-01-03")
        self.assertEqual(result["trades"][0]["exit"]["reference"], 115)
        self.assertEqual(result["trades"][0]["reason"], "gap_stop")

    def test_gap_stop_uses_worse_open_not_threshold(self):
        data = inputs()
        data[0]["TEST"][2].update(open=90, high=92, low=89, close=91)
        result = run_case("fixed3", data)
        self.assertEqual(result["trades"][0]["exit"]["reference"], 90)

    def test_entry_day_initial_stop_can_trigger(self):
        data = inputs()
        data[0]["TEST"][1]["low"] = 96
        result = run_case("fixed3", data)
        self.assertEqual(result["trades"][0]["exit_date"], "2026-01-02")
        self.assertEqual(result["trades"][0]["exit"]["reference"], 97)

    def test_holding_only_ignores_stop_candidate(self):
        data = inputs()
        data[0]["TEST"][2].update(open=50, high=101, low=49, close=100)
        self.assertEqual(run_case("hold20", data)["trades"][0]["reason"], "holding20_close")

    def test_quantity_formula_is_identical_across_exit_variants(self):
        quantities = [run_case(row["name"])["entries"][0]["quantity"] for row in VARIANTS]
        self.assertEqual(len(set(quantities)), 1)

    def test_joint_cash_and_five_position_limit(self):
        result = run_case(changed=inputs(symbols=tuple("ABCDEFGH")))
        self.assertEqual(result["summary"]["maximum_positions"], 5)
        self.assertGreaterEqual(result["summary"]["minimum_cash"], 0)

    def test_open_position_is_not_fabricated_as_closed_trade(self):
        result = run_case(changed=inputs(count=5))
        self.assertEqual(result["summary"]["trades"], 0)
        self.assertEqual(result["summary"]["open_positions"], 1)

    def test_cost_bridge_matches_cash_and_equity(self):
        costs = {**COSTS, "buy_cost_ratio": .001, "sell_cost_ratio": .002, "slippage_ratio": .001}
        result = run_case(costs=costs, policy={**POLICY, "spread_ratio": .001})
        trade = result["trades"][0]
        self.assertAlmostEqual(trade["pnl"], trade["gross_pnl"] - trade["spread_cost"] - trade["slippage_cost"] - trade["fees"])
        self.assertAlmostEqual(result["summary"]["final_equity"], 10000 + trade["pnl"])
        self.assertLess(trade["pnl"], 0)

    def test_buy_and_sell_fee_cash_flows(self):
        costs = {**COSTS, "buy_cost_ratio": .001, "sell_cost_ratio": .002, "slippage_ratio": .001}
        buy = execution(100, "BUY", 2, costs, .001)
        sell = execution(110, "SELL", 2, costs, .001)
        self.assertAlmostEqual(buy["price"] * 2 + buy["fee"], 200 * 1.0005 * 1.001 * 1.001)
        self.assertAlmostEqual(sell["price"] * 2 - sell["fee"], 220 * .9995 * .999 * .998)

    def test_future_changes_do_not_modify_prior_entries_or_curve(self):
        original = inputs()
        changed = copy.deepcopy(original)
        changed[0]["TEST"][10].update(open=50, low=49, high=51, close=50)
        before, after = run_case("fixed3", original), run_case("fixed3", changed)
        self.assertEqual(before["entries"], after["entries"])
        self.assertEqual(before["curve"][:10], after["curve"][:10])

    def test_missing_bar_keeps_position_and_valuation(self):
        data = inputs()
        del data[0]["TEST"][3]
        result = run_case("fixed3", data)
        self.assertEqual(result["diagnostics"]["held_missing_bar"], 1)
        self.assertEqual(result["curve"][3]["equity"], result["curve"][2]["equity"])

    def test_breakout_below_level_cancels_entry(self):
        data = inputs()
        data[0]["TEST"][1]["open"] = 98
        self.assertFalse(run_case(changed=data)["entries"])

    def test_end_of_day_sale_cash_is_not_used_at_previous_open(self):
        data = inputs(symbols=("A", "B"))
        first = data[3][data[2][0]][0]
        data[3][data[2][0]] = [first]
        data[3][data[2][1]] = [{**first, "symbol": "B", "date": data[2][1]}]
        result = run_case(changed=data, costs={**COSTS, "max_positions_per_market": 1},
                          policy={**POLICY, "holding_sessions": 2})
        self.assertEqual([entry["symbol"] for entry in result["entries"]], ["A"])


class CandidateSelectionTests(unittest.TestCase):
    def samples(self):
        summaries = {}
        for variant in VARIANTS:
            row = {"net_return": .08, "max_drawdown": .02, "worst_month": -.01, "trades": 40}
            summaries[variant["name"]] = {stage: {scenario: copy.deepcopy(row) for scenario in ("base", "double_cost")}
                                          for stage in ("development", "validation", "evaluation")}
        summaries["hold20"]["validation"]["base"].update(net_return=.1, max_drawdown=.04)
        return summaries

    def test_evaluation_cannot_change_selection(self):
        original = self.samples()
        changed = copy.deepcopy(original)
        changed["fixed5"]["evaluation"]["base"]["net_return"] = 1000
        self.assertEqual(choose_candidate(original), choose_candidate(changed))

    def test_validation_drawdown_must_improve_not_only_overall_return(self):
        summaries = self.samples()
        for variant in VARIANTS[1:]:
            summaries[variant["name"]]["validation"]["base"]["max_drawdown"] = .04
        self.assertIsNone(choose_candidate(summaries)["selected"])

    def test_cost_stress_can_veto_positive_profit(self):
        summaries = self.samples()
        for variant in VARIANTS[1:]:
            summaries[variant["name"]]["validation"]["double_cost"]["net_return"] = -.01
        self.assertIsNone(choose_candidate(summaries)["selected"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
