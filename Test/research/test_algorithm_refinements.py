"""소폭 변경의 격리, 기본값 보존, 미래 정보 차단, 후보 선정 경계를 검증한다."""
import copy
import unittest

from research.algorithm_study import FAMILIES, make_features, replay, resolve_strategy, signal
from research.algorithm_refinements import build_variants, feature_periods, select_variant
from Test.research.test_algorithm_study import example_bars


class RefinementTests(unittest.TestCase):
    def setUp(self):
        self.settings = {"stop_atr": 2.5, "trailing_atr": 3, "spread_ratio": .001,
                         "maximum_entry_gap": .03, "risk_per_trade": .0025, "cooldown_days": 3}
        self.plan = {"families": {"donchian": {"breakout_days": [40, 70], "stop_atr": [2, 3], "market_filter": [False]}},
                     "minimum_family_stress_positive_fraction": .75,
                     "selection": {"minimum_validation_trades": 30, "maximum_validation_drawdown": .08,
                                   "minimum_validation_profit_factor": 1.1, "minimum_positive_validation_years": 2}}
        self.costs = {"starting_cash": {"US": 10000, "KR": 10000000}, "allocation_fraction": .1,
                      "max_positions_per_market": 5, "buy_cost_ratio": .001, "sell_cost_ratio": .002, "slippage_ratio": .001}

    def test_each_child_changes_exactly_one_effective_parameter(self):
        variants = build_variants(self.plan, self.settings)
        parent = variants[0]
        def effective(variant):
            return {**variant["strategy"], **variant["risk"], "market_filter": variant["market_filter"]}
        original = effective(parent)
        for variant in variants[1:]:
            self.assertEqual(variant["parent"], parent["name"])
            changed = effective(variant)
            self.assertEqual(sum(changed[key] != value for key, value in original.items()), 1)

    def test_original_settings_and_plan_are_not_mutated(self):
        before = copy.deepcopy((self.plan, self.settings))
        build_variants(self.plan, self.settings)
        self.assertEqual(before, (self.plan, self.settings))

    def test_unknown_duplicate_and_no_change_axes_rejected(self):
        for axes in ({"unknown": [3]}, {"stop_atr": [2, 2]}, {"stop_atr": [2.5]}, {"market_filter": [0]}):
            with self.assertRaises(ValueError):
                build_variants({**self.plan, "families": {"donchian": axes}}, self.settings)

    def test_invalid_strategy_periods_and_rotation_rejected(self):
        for overrides in ({"fast_ma": 250}, {"slow_ma": True}, {"holding_days": -1}, {"rotation_days": 10}):
            with self.assertRaises(ValueError):
                resolve_strategy("ma_trend", overrides)

    def test_custom_high_excludes_current_day(self):
        bars = example_bars(280)
        bars[-1]["high"] = 9999
        features = make_features(bars, {"ma": [250], "high": [40, 70], "low": [15, 25]})
        self.assertEqual(features[-1]["prior_high40"], max(bar["high"] for bar in bars[-41:-1]))
        self.assertEqual(features[-1]["prior_low15"], min(bar["low"] for bar in bars[-16:-1]))

    def test_custom_features_cannot_see_future(self):
        bars = example_bars(280)
        changed = copy.deepcopy(bars)
        for bar in changed[260:]:
            for key in ("open", "high", "low", "close"):
                bar[key] *= 10
        extras = {"ma": [40, 60, 150, 250], "high": [40, 70], "low": [15, 25]}
        self.assertEqual(make_features(bars, extras)[:260], make_features(changed, extras)[:260])

    def test_parameter_changes_signal_and_exit(self):
        feature = {**make_features(example_bars(280), {"ma": [60], "high": [40]})[-1],
                   "close": 110, "ma50": 112, "ma60": 108, "ma200": 100, "momentum63": .1,
                   "prior_high40": 109, "prior_high55": 112}
        self.assertFalse(signal(feature, "ma_trend")["enter"])
        self.assertTrue(signal(feature, "ma_trend")["exit"])
        changed = signal(feature, "ma_trend", {"fast_ma": 60})
        self.assertTrue(changed["enter"])
        self.assertFalse(changed["exit"])
        self.assertFalse(signal(feature, "donchian")["enter"])
        self.assertTrue(signal(feature, "donchian", {"breakout_days": 40})["enter"])

    def replay(self, family="ma_trend", strategy=None):
        bars = example_bars(280)
        features = make_features(bars, {"ma": [250]})
        return replay({"US:AAPL": bars}, {"US:AAPL": features}, {row["date"]: row for row in features},
                      family, False, self.costs, self.settings, bars[210]["date"], bars[-1]["date"], strategy)

    def test_explicit_defaults_preserve_previous_replay_behavior_for_all_families(self):
        for family in FAMILIES:
            self.assertEqual(self.replay(family), self.replay(family, resolve_strategy(family)))

    def test_holding_limit_exits_at_following_open(self):
        result = self.replay(strategy={"holding_days": 2})
        bars = example_bars(280)
        first = result["trades"][0]
        self.assertEqual(first["entry_date"], bars[211]["date"])
        self.assertEqual(first["exit_date"], bars[213]["date"])
        self.assertEqual(first["reason"], "holding_limit")

    def test_long_average_waits_until_enough_completed_history(self):
        result = self.replay(strategy={"slow_ma": 250})
        position = result["positions"]["US:AAPL"]
        self.assertEqual(position["entry_date"], example_bars(280)[251]["date"])

    def test_rotation_change_affects_only_planning_cadence(self):
        baseline = self.replay("momentum_rotation")
        slower = self.replay("momentum_rotation", {"rotation_days": 10})
        self.assertEqual(len(baseline["decisions"]), 14)
        self.assertEqual(len(slower["decisions"]), 7)

    def test_selection_does_not_read_evaluation_results(self):
        variants = build_variants({**self.plan, "families": {"donchian": {"stop_atr": [2]}}}, self.settings)
        summary = {"net_return": .1, "max_drawdown": .02, "trades": 50, "profit_factor": 2,
                   "year_returns": {"2023": .05, "2024": .05}}
        stages = {stage: {scenario: {"summary": copy.deepcopy(summary)} for scenario in ("base", "double_cost")}
                  for stage in ("development", "validation")}
        results = {variant["name"]: copy.deepcopy(stages) for variant in variants}
        before = select_variant(results, variants, self.plan)
        results[variants[-1]["name"]]["evaluation"] = {"best_future_return": 100000}
        self.assertEqual(before, select_variant(results, variants, self.plan))
        results[variants[-1]["name"]]["validation"]["double_cost"]["summary"]["net_return"] = -.1
        self.assertIsNone(select_variant(results, variants, self.plan)["selected"])

    def test_feature_periods_include_every_declared_lookback(self):
        periods = feature_periods(build_variants(self.plan, self.settings))
        self.assertEqual(periods["high"], [40, 55, 70])
