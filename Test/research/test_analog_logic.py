"""유사 상황 실험의 미래 차단·정규화·현금 대기를 검증한다."""
import copy
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
from analog_logic import STATE_FIELDS, choose_strategy, market_states, mature_cases, nearest_cases
from analog_experiment import close_month, compound_months, full_months
from broker.sessions import calendar_for
from research.algorithm_study import make_features


POLICY = {"minimum_history": 2, "neighbors": 2, "minimum_neighbors": 2,
          "maximum_distance": 1.5, "drawdown_penalty": 1, "minimum_positive_fraction": .5}


def state(value):
    return {field: value for field in STATE_FIELDS}


def case(anchor, ending, value=0, profit=.05, drawdown=.01, stress=.04):
    return {"anchor_date": anchor, "outcome_start": anchor, "outcome_end": ending, "state": state(value),
        "outcomes": {"trend": {"base": {"net_return": profit, "max_drawdown": drawdown},
                                "double_cost": {"net_return": stress, "max_drawdown": drawdown}}}}


class AnalogSelectionTests(unittest.TestCase):
    def setUp(self):
        self.cases = [case("2020-01-31", "2020-02-28", -1), case("2020-02-28", "2020-03-31", 1)]

    def select(self, cases=None, policy=None, current=None, control=None):
        return choose_strategy(current or state(0), cases if cases is not None else self.cases,
                               "2020-04-30", ["trend"], policy or POLICY, control)

    def test_future_outcome_is_not_available(self):
        unfinished = case("2020-03-31", "2020-05-31", profit=100)
        self.assertNotIn(unfinished, mature_cases(self.cases + [unfinished], "2020-04-30"))

    def test_current_anchor_is_not_a_historical_case(self):
        current = case("2020-04-30", "2020-04-30")
        self.assertNotIn(current, mature_cases([current], "2020-04-30"))

    def test_completed_today_is_available_at_close(self):
        current = case("2020-03-31", "2020-04-30")
        self.assertEqual(mature_cases([current], "2020-04-30"), [current])

    def test_future_state_and_outcome_cannot_change_choice(self):
        future = case("2021-01-31", "2021-02-28", value=1000000, profit=10000)
        self.assertEqual(self.select(), self.select(self.cases + [future]))

    def test_neighbor_rank_uses_state_not_outcome(self):
        before = [item["case"]["anchor_date"] for item in nearest_cases(state(0), self.cases, 2, 2)]
        modified = copy.deepcopy(self.cases)
        modified[0]["outcomes"]["trend"]["base"]["net_return"] = -100
        after = [item["case"]["anchor_date"] for item in nearest_cases(state(0), modified, 2, 2)]
        self.assertEqual(before, after)

    def test_scaling_is_invariant_to_feature_units(self):
        expected = [item["distance"] for item in nearest_cases(state(0), self.cases, 2, 2)]
        changed = copy.deepcopy(self.cases)
        for item in changed:
            item["state"]["return5"] *= 100
        actual = [item["distance"] for item in nearest_cases(state(0), changed, 2, 2)]
        self.assertEqual(expected, actual)

    def test_enough_positive_evidence_selects(self):
        self.assertEqual(self.select()["selected"], "trend")

    def test_insufficient_history_is_cash(self):
        self.assertEqual(self.select(self.cases[:1])["reason"], "insufficient_history")

    def test_dissimilar_market_is_cash(self):
        self.assertEqual(self.select(current=state(100))["reason"], "insufficient_similar_cases")

    def test_cost_stress_can_veto_positive_base(self):
        changed = copy.deepcopy(self.cases)
        for item in changed:
            item["outcomes"]["trend"]["double_cost"]["net_return"] = -.01
        self.assertEqual(self.select(changed)["selected"], "cash")

    def test_large_drawdown_can_veto_positive_return(self):
        changed = copy.deepcopy(self.cases)
        for item in changed:
            item["outcomes"]["trend"]["base"]["max_drawdown"] = .1
        self.assertEqual(self.select(changed)["selected"], "cash")

    def test_negative_returns_are_cash(self):
        changed = copy.deepcopy(self.cases)
        for item in changed:
            item["outcomes"]["trend"]["base"]["net_return"] = -.01
        self.assertEqual(self.select(changed)["selected"], "cash")

    def test_controls_do_not_use_similarity_cutoff(self):
        self.assertEqual(self.select(current=state(100), control="all_history")["selected"], "trend")
        self.assertEqual(self.select(current=state(100), control="recent")["selected"], "trend")

    def test_inputs_are_not_modified(self):
        original = copy.deepcopy(self.cases)
        self.select()
        self.assertEqual(original, self.cases)


class AnalogAccountTests(unittest.TestCase):
    def test_future_bars_do_not_change_earlier_market_states(self):
        bars = [{"date": str(index).zfill(4), "open": 100 + index, "close": 100 + index,
                 "high": 101 + index, "low": 99 + index, "volume": 100 + index % 5} for index in range(250)]
        full_features = {str(stock): make_features(bars) for stock in range(12)}
        prefix_features = {str(stock): make_features(bars[:230]) for stock in range(12)}
        full = market_states(bars, full_features)
        prefix = market_states(bars[:230], prefix_features)
        self.assertTrue(prefix)
        self.assertEqual({day: value for day, value in full.items() if day < "0230"}, prefix)

    def test_month_end_does_not_charge_already_marked_exit_twice(self):
        costs = {"starting_cash": {"US": 10000}, "buy_cost_ratio": .001,
                 "sell_cost_ratio": .002, "slippage_ratio": .001}
        purchase_cost = 100 * 1.0005 * 1.001 * 1.001
        final_equity = 10000 - purchase_cost + 110 * .9995 * .999 * .998
        result = {"positions": {"TEST": {"quantity": 1, "cost": purchase_cost,
            "price": purchase_cost / 1.001, "signal_date": "2026-01-01", "entry_date": "2026-01-02"}},
            "curve": [{"date": "2026-01-02", "equity": final_equity,
                       "cash": 10000 - purchase_cost, "positions": 1, "exposure": .01}], "trades": []}
        actual = close_month(result, {"TEST": [{"date": "2026-01-02", "close": 110}]}, costs, {"spread_ratio": .001}, "2026-01-02")
        self.assertAlmostEqual(actual["curve"][-1]["cash"], final_equity)
        self.assertAlmostEqual(actual["trades"][0]["pnl"], final_equity - 10000)
        self.assertEqual(len(actual["trades"]), 1)
        self.assertFalse(actual["positions"])
        self.assertTrue(result["positions"])

    def test_monthly_returns_compound_and_losses_scale(self):
        results = {}
        months = []
        for month, final in (("2026-01", 11000), ("2026-02", 9000)):
            day = month + "-28"
            months.append({"month": month, "days": [day]})
            results[(month, "trend", "base")] = {
                "curve": [{"date": day, "equity": final, "cash": final, "positions": 0, "exposure": 0}],
                "trades": [{"quantity": 1, "entry_cost": 100, "pnl": final - 10000, "reason": "experiment_month_end"}]}
        account = compound_months(months, [{"selected": "trend"}] * 2, results, "base", 10000)
        self.assertAlmostEqual(account["summary"]["net_return"], -.01)
        self.assertAlmostEqual(account["trades"][1]["pnl"], -1100)
        self.assertAlmostEqual(account["curve"][-1]["equity"], 9900)

    def test_incomplete_month_is_not_an_evaluation_outcome(self):
        schedule = calendar_for("US", 2026).schedule
        dates = [label.date().isoformat() for label in schedule.index if label.strftime("%Y-%m") == "2026-01"]
        self.assertEqual(full_months([{"date": day} for day in dates])[0]["end"], dates[-1])
        self.assertEqual(full_months([{"date": day} for day in dates[:-1]]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
