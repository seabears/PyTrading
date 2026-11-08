"""다양한 알고리즘 연구에서 미래 참조·현금 재사용·갭 손실·선정 누수를 검증한다."""
import copy
import unittest
from datetime import date, timedelta

from research.algorithm_study import FAMILIES, benchmark, make_features, replay, signal
from tools.run_algorithm_study import choose_candidate
from research.algorithm_analysis import analyze


def example_bars(count=250):
    first = date(2019, 1, 1)
    return [{"date": (first + timedelta(days=index)).isoformat(),
             "open": 100 + index * .1 + (.03 if index % 2 else -.03),
             "close": 100 + index * .1 + (.04 if index % 2 else -.04),
             "high": 101 + index * .1, "low": 99 + index * .1, "volume": 1000}
            for index in range(count)]


class AlgorithmStudyTests(unittest.TestCase):
    def setUp(self):
        self.bars = example_bars()
        self.costs = {"starting_cash": {"US": 10000, "KR": 10000000}, "allocation_fraction": .1,
                      "max_positions_per_market": 5, "buy_cost_ratio": .001,
                      "sell_cost_ratio": .002, "slippage_ratio": .001}
        self.settings = {"spread_ratio": .001, "maximum_entry_gap": .03, "risk_per_trade": .0025,
                         "stop_atr": 2.5, "trailing_atr": 3, "cooldown_days": 3}

    def run_replay(self, bars=None, end=None, **overrides):
        bars = self.bars if bars is None else bars
        features = make_features(bars)
        options = {"series": {"US:AAPL": bars}, "features": {"US:AAPL": features},
                   "proxy_features": {row["date"]: row for row in features},
                   "family": "ma_trend", "market_filter": False, "costs": self.costs,
                   "settings": self.settings, "start": bars[210]["date"], "end": end or bars[-1]["date"]}
        options.update(overrides)
        return replay(**options)

    def test_features_do_not_use_future_prices(self):
        changed = copy.deepcopy(self.bars)
        for bar in changed[220:]:
            for name in ("open", "high", "low", "close"):
                bar[name] *= 5
        self.assertEqual(make_features(self.bars)[:220], make_features(changed)[:220])

    def test_all_families_reject_insufficient_history(self):
        feature = make_features(self.bars)[100]
        for family in FAMILIES:
            self.assertFalse(signal(feature, family)["enter"])

    def test_family_conditions_are_distinct_and_explicit(self):
        feature = {**make_features(self.bars)[220], "close": 110, "ma50": 108, "ma200": 100,
                   "ma10": 112, "ma20": 114, "momentum63": .1, "momentum126": .2,
                   "rsi2": 5, "zscore": -2.5, "prior_high55": 109, "prior_low20": 105}
        self.assertTrue(all(signal(feature, family)["enter"] for family in FAMILIES))
        changed = {**feature, "rsi2": 50, "zscore": 0, "prior_high55": 115}
        for family in ("trend_pullback", "bollinger_reversion", "donchian"):
            self.assertFalse(signal(changed, family)["enter"])

    def test_orders_use_next_day_and_period_end_does_not_force_exit(self):
        result = self.run_replay()
        position = result["positions"]["US:AAPL"]
        self.assertEqual(position["signal_date"], self.bars[210]["date"])
        self.assertEqual(position["entry_date"], self.bars[211]["date"])
        self.assertEqual(result["trades"], [])
        self.assertGreater(result["curve"][-1]["equity"], result["curve"][-1]["cash"])

    def test_extending_period_does_not_change_previous_curve_or_trades(self):
        earlier = self.run_replay(end=self.bars[230]["date"])
        later = self.run_replay()
        self.assertEqual(earlier["curve"], later["curve"][:len(earlier["curve"])])
        self.assertEqual(earlier["trades"], [trade for trade in later["trades"] if trade["exit_date"] <= self.bars[230]["date"]])

    def test_cash_and_position_limit_are_shared(self):
        values = make_features(self.bars)
        result = self.run_replay(series={f"US:S{i}": self.bars for i in range(8)},
            features={f"US:S{i}": values for i in range(8)}, costs={**self.costs, "max_positions_per_market": 2})
        self.assertEqual(result["summary"]["maximum_positions"], 2)
        self.assertGreaterEqual(result["summary"]["minimum_cash"], 0)

    def test_gap_through_stop_uses_low_open_instead_of_promised_stop(self):
        bars = copy.deepcopy(self.bars)
        bars[212].update(open=60, high=61, low=59, close=60)
        result = self.run_replay(bars=bars)
        trade = result["trades"][0]
        self.assertEqual(trade["reason"], "gap_stop")
        self.assertLess(trade["exit_price"], 60)
        self.assertLess(trade["pnl"], -100)

    def test_today_high_does_not_raise_today_stop(self):
        bars = copy.deepcopy(self.bars)
        bars[211]["high"] = 200
        # 진입 당시 손절선은 약 116, 이후 고가 200으로 올린 손절선은 다음 날부터다.
        bars[211]["low"] = 119
        result = self.run_replay(bars=bars, end=bars[211]["date"])
        self.assertEqual(result["summary"]["open_positions"], 1)
        self.assertEqual(result["trades"], [])

    def test_missing_held_bar_is_marked_and_never_invented(self):
        values = make_features(self.bars)
        series = self.bars[:215] + self.bars[216:]
        result = self.run_replay(series={"US:AAPL": series},
                                 features={"US:AAPL": make_features(series)})
        self.assertEqual(result["diagnostics"]["held_missing_daily_bar"], 1)
        self.assertEqual(result["curve"][5]["equity"], result["curve"][4]["equity"])

    def test_selection_ignores_evaluation_winner(self):
        summary = {"net_return": .1, "max_drawdown": .03, "trades": 40, "profit_factor": 1.5,
                   "year_returns": {"2023": .05, "2024": .05}}
        stages = {"development": {"base": {"summary": summary}},
                  "validation": {"base": {"summary": summary}, "double_cost": {"summary": summary}}}
        results = {"first": copy.deepcopy(stages), "second": copy.deepcopy(stages)}
        settings = {"selection": {"minimum_validation_trades": 30, "maximum_validation_drawdown": .08,
                                    "minimum_validation_profit_factor": 1.1, "minimum_positive_validation_years": 2}}
        original = choose_candidate(results, settings)
        results["second"]["evaluation"] = {"net_return": 10000}
        self.assertEqual(original, choose_candidate(results, settings))

    def test_no_eligible_candidate_selects_cash(self):
        summary = {"net_return": -.1, "max_drawdown": .03, "trades": 40, "profit_factor": .5,
                   "year_returns": {"2023": -.05, "2024": -.05}}
        stages = {"development": {"base": {"summary": summary}},
                  "validation": {"base": {"summary": summary}, "double_cost": {"summary": summary}}}
        settings = {"selection": {"minimum_validation_trades": 30, "maximum_validation_drawdown": .08,
                                    "minimum_validation_profit_factor": 1.1, "minimum_positive_validation_years": 2}}
        self.assertIsNone(choose_candidate({"bad": stages}, settings)["selected"])

    def test_benchmark_includes_spread_fees_and_only_half_initial_capital(self):
        result = benchmark(self.bars, self.costs, self.settings, self.bars[210]["date"], self.bars[-1]["date"])
        self.assertGreater(result["curve"][0]["cash"], 5000)
        self.assertLess(result["curve"][0]["equity"], 10000)

    def test_unknown_algorithm_is_rejected(self):
        with self.assertRaises(ValueError):
            self.run_replay(family="unknown")

    def test_analysis_reconciles_closed_costs_and_open_stock_contributions(self):
        bars = copy.deepcopy(self.bars)
        bars[212].update(open=60, high=61, low=59, close=60)
        result = self.run_replay(bars=bars)
        analysis = analyze(result, {"US:AAPL": bars}, self.costs, self.settings["spread_ratio"])
        self.assertTrue(all(analysis["checks"].values()))
        self.assertGreater(analysis["closed_fees"], 0)
        self.assertGreater(analysis["closed_slippage_cost"], 0)

    def test_analysis_also_reconciles_unclosed_position(self):
        result = self.run_replay()
        analysis = analyze(result, {"US:AAPL": self.bars}, self.costs, self.settings["spread_ratio"])
        self.assertTrue(analysis["checks"]["stock_contributions_reconcile"])
        self.assertGreater(analysis["by_symbol"]["US:AAPL"]["open_pnl"], 0)

    def test_intraday_stop_cash_is_not_reused_at_already_passed_open(self):
        falling = copy.deepcopy(self.bars)
        falling[211]["low"] = 100
        series = {"US:A": falling, "US:B": self.bars, "US:C": self.bars}
        result = self.run_replay(series=series, features={name: make_features(bars) for name, bars in series.items()},
                                 costs={**self.costs, "allocation_fraction": .5, "max_positions_per_market": 3},
                                 settings={**self.settings, "risk_per_trade": .5}, end=self.bars[211]["date"])
        self.assertEqual(set(result["positions"]), {"US:B"})
        self.assertEqual(result["trades"][0]["symbol"], "US:A")
        self.assertGreater(result["curve"][-1]["cash"], 4000)

    def test_experiment_registry_appends_without_overwriting_previous_events(self):
        import json
        import tempfile
        from pathlib import Path
        from tools.run_algorithm_study import record_event
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.jsonl"
            record_event(path, {"status": "started", "algorithm": "example"})
            original = path.read_bytes()
            record_event(path, {"status": "failed", "error_type": "ValueError"})
            self.assertTrue(path.read_bytes().startswith(original))
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["status"] for row in events], ["started", "failed"])
