"""지표·시간 누수·비용·갭·ATR 손절·시장 지연·일별 평가 지표를 합성 자료로 검증한다."""
import copy
import json
import math
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from research.technical import performance, position_size, replay
from strategy.technical import MarketRegime, average_true_range, classify_regime, session_vwap, signal_details
from tools.research_technical import load_record, load_settings


class ConstantRegime:
    def at(self, day):
        return "up"


def bar(index, opening=100, high=102, low=99, close=101, volume=10):
    day = (date(2024, 1, 1) + timedelta(days=index)).isoformat()
    return {"date": day, "time": day, "open": opening, "high": high, "low": low, "close": close, "volume": volume}


def always_enter(history, family, settings, regime, require_up):
    return {"enter": True, "exit": False, "conditions": {}, "values": {"atr": 1.0}}


class TechnicalIndicatorsTest(unittest.TestCase):
    def test_vwap_weights_volume_and_zero_volume_is_unavailable(self):
        rows = [bar(0, high=10, low=10, close=10, volume=1), bar(1, high=20, low=20, close=20, volume=3)]
        self.assertEqual(session_vwap(rows), 17.5)
        for row in rows:
            row["volume"] = 0
        self.assertIsNone(session_vwap(rows))

    def test_atr_includes_gap_from_previous_close(self):
        rows = [bar(0, high=101, low=99, close=100), bar(1, high=112, low=110, close=111), bar(2, high=114, low=110, close=112)]
        self.assertEqual(average_true_range(rows, 2), 8)
        self.assertIsNone(average_true_range(rows[:2], 2))

    def test_vwap_cross_requires_volume_and_optional_market_filter(self):
        rows = [bar(0, high=101, low=99, close=100), bar(1, high=101, low=99, close=100), bar(2, high=104, low=100, close=103, volume=30)]
        settings = {"volume_period": 2, "volume_ratio": 1.5, "atr_period": 2, "maximum_holding_bars": 12}
        self.assertTrue(signal_details(rows, "vwap_volume", settings)["enter"])
        self.assertFalse(signal_details(rows, "vwap_volume", settings, "down", True)["enter"])
        rows[-1]["volume"] = 10
        self.assertFalse(signal_details(rows, "vwap_volume", settings)["enter"])

    def test_ma_momentum_uses_only_supplied_completed_history(self):
        rows = [bar(index, high=101 + index, low=99 + index, close=100 + index) for index in range(10)]
        settings = {"fast": 2, "slow": 4, "momentum_period": 3, "minimum_momentum": 0, "atr_period": 2, "maximum_holding_bars": 60}
        original = copy.deepcopy(rows)
        before = signal_details(rows[:7], "ma_momentum", settings)
        rows[-1]["close"] = 1
        self.assertEqual(signal_details(rows[:7], "ma_momentum", settings), before)
        self.assertTrue(before["enter"])
        self.assertEqual(original[:7], rows[:7])

    def test_regime_up_down_sideways_unknown(self):
        self.assertEqual(classify_regime(list(range(1, 11)), 2, 4, 2), "up")
        self.assertEqual(classify_regime(list(range(11, 1, -1)), 2, 4, 2), "down")
        self.assertEqual(classify_regime([10] * 10, 2, 4, 2), "sideways")
        self.assertEqual(classify_regime([10], 2, 4, 2), "unknown")

    def test_market_regime_excludes_same_day_future_and_stale_values(self):
        rows = [bar(index, close=100 + index) for index in range(10)]
        settings = {"fast": 2, "slow": 4, "slope_period": 2, "lag_calendar_days": 2, "maximum_age_days": 7}
        provider = MarketRegime(rows, settings)
        self.assertEqual(provider.at("2024-01-10"), "up")
        rows[-1]["close"] = 1
        rows[-2]["close"] = 1
        self.assertEqual(provider.at("2024-01-10"), "up")
        self.assertEqual(provider.at("2024-01-20"), "unknown")


class TechnicalExecutionTest(unittest.TestCase):
    def setUp(self):
        self.costs = {"starting_cash": {"KR": 10000, "US": 10000}, "allocation_fraction": .1,
                      "buy_cost_ratio": 0, "sell_cost_ratio": 0, "slippage_ratio": 0}
        self.risk = {"risk_per_trade": .005, "stop_atr": 2, "trailing_atr": 3,
                     "daily_loss_limit": .01, "maximum_entry_gap": .5, "cooldown_bars": 0}
        self.settings = {"fast": 2, "slow": 4, "momentum_period": 3, "minimum_momentum": 0, "atr_period": 2, "maximum_holding_bars": 60}

    def run_replay(self, rows, risk=None):
        with patch("research.technical.signal_details", side_effect=always_enter):
            return replay(rows, "US", "ma_momentum", self.settings, risk or self.risk, self.costs, 0, ConstantRegime())

    def test_signal_fills_next_open_and_cash_reconciles(self):
        rows = [bar(0), bar(1, 110, 113, 109, 112), bar(2, 115, 117, 114, 116)]
        result = self.run_replay(rows)
        trade = result["trades"][0]
        self.assertEqual(trade["entry_price"], 110)
        self.assertEqual(trade["entry_bar_index"], trade["signal_bar_index"] + 1)
        self.assertEqual(result["summary"]["net_pnl"], sum(trade["pnl"] for trade in result["trades"]))
        self.assertGreaterEqual(min(row["equity"] for row in result["curve"]), 0)

    def test_gap_stop_uses_worse_open_price(self):
        rows = [bar(0), bar(1, 100, 101, 99, 100), bar(2, 90, 92, 89, 91)]
        result = self.run_replay(rows)
        self.assertEqual(result["trades"][0]["exit_price"], 90)
        self.assertEqual(result["trades"][0]["reason"], "gap_adjusted_atr_stop")

    def test_same_bar_high_cannot_raise_that_bars_stop(self):
        rows = [bar(0), bar(1, 100, 130, 99, 125), bar(2, 126, 129, 125, 127)]
        result = self.run_replay(rows)
        self.assertEqual(result["trades"][0]["exit_date"], rows[2]["date"])
        self.assertEqual(result["trades"][0]["exit_price"], 126)

    def test_rising_atr_does_not_lower_existing_trailing_stop(self):
        rows = [bar(0), bar(1, 100, 110, 100, 110), bar(2, 110, 111, 110, 111), bar(3, 108, 109, 107, 108)]
        risk = {**self.risk, "trailing_atr": 1}
        def expanding_atr(history, *args):
            return {**always_enter(history, *args), "values": {"atr": 30 if len(history) >= 3 else 1}}
        with patch("research.technical.signal_details", side_effect=expanding_atr):
            result = replay(rows, "US", "ma_momentum", self.settings, risk, self.costs, 0, ConstantRegime())
        self.assertEqual(result["trades"][0]["exit_price"], 108)
        self.assertEqual(result["trades"][0]["reason"], "gap_adjusted_atr_stop")

    def test_costs_reduce_identical_trade_profit(self):
        rows = [bar(0), bar(1, 100, 102, 99, 101), bar(2, 104, 105, 103, 104)]
        baseline = self.run_replay(rows)
        self.costs.update(buy_cost_ratio=.001, sell_cost_ratio=.002, slippage_ratio=.001)
        charged = self.run_replay(rows)
        self.assertLess(charged["summary"]["net_return"], baseline["summary"]["net_return"])

    def test_risk_and_capital_limits_both_constrain_quantity(self):
        quantity = position_size(10000, 10000, 100, 20, self.risk, self.costs, 0)
        self.assertEqual(quantity, 1)
        quantity = position_size(10000, 10000, 100, .01, self.risk, self.costs, 0)
        self.assertEqual(quantity, 10)

    def test_large_entry_gap_is_cancelled(self):
        rows = [bar(0, close=100), bar(1, 150, 151, 149, 150)]
        result = self.run_replay(rows, {**self.risk, "maximum_entry_gap": .02})
        self.assertEqual(result["trades"], [])
        self.assertEqual(result["diagnostics"]["entry_gap_cancelled"], 1)

    def test_daily_loss_limit_blocks_new_entries_until_next_session(self):
        rows = [bar(0, 100, 101, 99, 100), bar(1, 100, 101, 99, 100),
                bar(2, 90, 92, 89, 90), bar(3, 100, 101, 99, 100), bar(4, 100, 101, 99, 100)]
        for index, row in enumerate(rows):
            row["date"] = "2024-01-01"
            row["time"] = f"2024-01-01T09:{index * 5:02d}:00"
        with patch("research.technical.signal_details", side_effect=always_enter):
            result = replay(rows, "US", "vwap_volume", self.settings,
                            {**self.risk, "daily_loss_limit": .005}, self.costs, 0, ConstantRegime())
        self.assertEqual(len(result["trades"]), 1)
        self.assertGreater(result["diagnostics"]["daily_loss_halt"], 0)

    def test_intraday_flattens_and_resets_history_at_session_boundary(self):
        rows = [bar(index, 100, 102, 99, 101) for index in range(4)]
        rows[1]["date"] = rows[0]["date"]
        rows[3]["date"] = rows[2]["date"]
        lengths = []
        def remember(history, *args):
            lengths.append(len(history))
            return always_enter(history, *args)
        with patch("research.technical.signal_details", side_effect=remember):
            result = replay(rows, "US", "vwap_volume", self.settings, self.risk, self.costs, 0, ConstantRegime())
        self.assertEqual(lengths, [1, 2, 1, 2])
        self.assertTrue(all(trade["reason"] == "session_end" for trade in result["trades"]))


class TechnicalMetricsTest(unittest.TestCase):
    def test_sharpe_uses_daily_returns_not_intraday_bar_count(self):
        curve = [{"date": "2024-01-01", "equity": 100}, {"date": "2024-01-01", "equity": 101}]
        self.assertIsNone(performance(curve, [], 100)["sharpe"])
        curve.append({"date": "2024-01-02", "equity": 99.99})
        result = performance(curve, [{"pnl": 100}, {"pnl": -50}], 100)
        self.assertAlmostEqual(result["sharpe"], 0, places=9)
        self.assertEqual(result["sharpe_days"], 2)
        self.assertEqual(result["profit_factor"], 2)
        self.assertEqual(result["payoff_ratio"], 2)
        self.assertEqual(result["win_rate"], .5)

    def test_no_loss_profit_factor_is_not_infinity(self):
        result = performance([{"date": "2024-01-01", "equity": 110}], [{"pnl": 10}], 100)
        self.assertIsNone(result["profit_factor"])

    def test_bad_policy_is_rejected(self):
        settings = load_settings()
        settings["regime"]["lag_calendar_days"] = 0
        with patch.object(Path, "read_text", return_value=json.dumps(settings)), self.assertRaises(ValueError):
            load_settings()

    def test_non_actual_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"
            path.write_text(json.dumps({"origin": "synthetic", "market": "US", "symbol": "AAPL", "interval": "1d", "adjusted": True, "collection_complete": True}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_record(path, "US", "AAPL", {})

    def test_menu_runs_new_study_without_starting_live_trading(self):
        from tools import test_features
        with patch("tools.research_technical.main") as run, patch("app.runner.main", side_effect=AssertionError("live")):
            self.assertEqual(test_features.run_feature("strategies"), 0)
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
