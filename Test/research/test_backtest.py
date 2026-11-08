"""수익률을 조작하지 않도록 시각·체결 비용·선택 경계를 합성 입력으로 검증한다."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

from research.backtest import compare_rules, execution_price, simulate, split_sessions, validate_costs
from research.history import collect_history, load_research_settings, market_timezone


class BacktestTests(unittest.TestCase):
    def setUp(self):
        self.costs = {"starting_cash": {"KR": 10000, "US": 10000}, "allocation_fraction": 0.1,
                      "buy_cost_ratio": 0, "sell_cost_ratio": 0, "slippage_ratio": 0}
        self.rule = {"family": "breakout", "lookback": 2, "volume_ratio": 1,
                     "stop_loss": 0.01, "trailing_stop": 0.02, "deviation": 0.01, "max_chase": 0.1}
        start = datetime(2026, 9, 1, 13, 30, tzinfo=timezone.utc)
        prices = [(10, 10, 9.8, 9.9), (10, 10, 9.8, 9.9), (10, 10.6, 10, 10.5), (10.8, 10.8, 10.8, 10.8)]
        bars = [{"start": (start + timedelta(minutes=5 * index)).isoformat(),
                 "end": (start + timedelta(minutes=5 * (index + 1))).isoformat(),
                 "open": price[0], "high": price[1], "low": price[2], "close": price[3], "volume": 100}
                for index, price in enumerate(prices)]
        self.session = {"market": "US", "symbol": "TEST", "date": "2026-09-01", "bars": bars}

    def test_signal_executes_next_bar_not_signal_close(self):
        result = simulate([self.session], self.rule, self.costs, 0)
        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["trades"][0]["entry_price"], 10.8)
        self.assertEqual(result["summary"]["net_return"], 0)

    def test_round_trip_costs_reduce_equity_and_match_cash_flows(self):
        costs = {**self.costs, "buy_cost_ratio": 0.01, "sell_cost_ratio": 0.01, "slippage_ratio": 0.001}
        result = simulate([self.session], self.rule, costs, 0.001)
        trade = result["trades"][0]
        expected = trade["quantity"] * (trade["exit_price"] * 0.99 - trade["entry_price"] * 1.01)
        self.assertAlmostEqual(result["summary"]["net_pnl"], expected)
        self.assertLess(result["summary"]["net_return"], 0)

    def test_stop_gap_fills_at_worse_open_not_stop_price(self):
        session = copy.deepcopy(self.session)
        session["bars"].append({**session["bars"][-1], "start": "2026-09-01T13:50:00Z",
                                "end": "2026-09-01T13:55:00Z", "open": 8, "high": 9, "low": 7, "close": 8})
        result = simulate([session], self.rule, self.costs, 0)
        self.assertEqual(result["trades"][0]["exit_price"], 8)
        self.assertEqual(result["trades"][0]["reason"], "stop_or_trailing_gap_adjusted")

    def test_fees_and_spread_are_adverse_in_both_directions(self):
        costs = {**self.costs, "slippage_ratio": 0.001}
        self.assertGreater(execution_price(100, "BUY", costs, 0.001), 100)
        self.assertLess(execution_price(100, "SELL", costs, 0.001), 100)

    def test_split_keeps_chronological_separate_sessions(self):
        sessions = [{"date": str(index)} for index in range(20)]
        parts = split_sessions(sessions)
        self.assertEqual([len(part) for part in parts.values()], [12, 4, 4])
        self.assertEqual(parts["training"][-1]["date"], "11")
        self.assertEqual(parts["test"][0]["date"], "16")

    def test_final_test_prices_do_not_select_candidate(self):
        sessions = [{**copy.deepcopy(self.session), "date": f"2026-09-{index + 1:02d}"} for index in range(20)]
        settings = {"training_fraction": 0.6, "validation_fraction": 0.2, "assumed_spread_ratio": 0.001,
                    "minimum_sessions_per_symbol": 60, "minimum_test_trades_per_market": 30, "maximum_test_drawdown": 0.05}
        before = compare_rules(sessions, self.costs, settings)
        for session in sessions[16:]:
            for bar in session["bars"]:
                bar.update(open=1000, high=1000, low=1000, close=1000)
        after = compare_rules(sessions, self.costs, settings)
        self.assertEqual(before["selected_rule"], after["selected_rule"])
        self.assertEqual(before["verdict"], "rejected")

    def test_history_boundary_duplicates_are_removed(self):
        client = Mock()
        candle = {"timestamp": "2026-09-01T13:31:00Z", "currency": "USD"}
        client.get.side_effect = [{"candles": [candle], "nextBefore": candle["timestamp"]},
                                 {"candles": [candle], "nextBefore": candle["timestamp"]}]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            record = collect_history(client, "US", "TEST", Path(folder) / "history.json",
                                     {"history_days": 120, "max_pages_per_symbol": 3, "request_interval_seconds": 0},
                                     datetime(2026, 9, 2, tzinfo=timezone.utc))
        self.assertEqual(len(record["candles"]), 1)
        self.assertEqual(record["stop_reason"], "repeated_page")
        self.assertEqual(client.get.call_args.args[1]["before"], candle["timestamp"])

    def test_us_dst_and_korean_offsets(self):
        self.assertEqual(market_timezone("US", datetime(2026, 7, 1, tzinfo=timezone.utc)).utcoffset(None), timedelta(hours=-4))
        self.assertEqual(market_timezone("US", datetime(2026, 12, 1, tzinfo=timezone.utc)).utcoffset(None), timedelta(hours=-5))
        self.assertEqual(market_timezone("KR", datetime(2026, 7, 1, tzinfo=timezone.utc)).utcoffset(None), timedelta(hours=9))

    def test_invalid_costs_cannot_create_artificial_profit(self):
        for changes in ({"buy_cost_ratio": -0.01}, {"allocation_fraction": 2}, {"slippage_ratio": float("nan")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_costs({**self.costs, **changes})

    def test_configuration_must_leave_unused_test_period(self):
        from paths import PROJECT_ROOT, CONFIG_ROOT
        settings = load_research_settings(CONFIG_ROOT / "research.json")
        settings.update(training_fraction=0.8, validation_fraction=0.2)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps(settings), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_research_settings(path)

    def test_overnight_position_carries_and_gap_loss_is_counted(self):
        following = copy.deepcopy(self.session)
        following["date"] = "2026-09-02"
        for bar in following["bars"]:
            bar["start"] = bar["start"].replace("09-01", "09-02")
            bar["end"] = bar["end"].replace("09-01", "09-02")
            bar.update(open=8, high=9, low=7, close=8)
        result = simulate([self.session, following], {**self.rule, "hold_overnight": True}, self.costs, 0)
        self.assertEqual(result["trades"][0]["exit_price"], 8)
        self.assertIn("09-02", result["trades"][0]["exit_at"])
        self.assertLess(result["summary"]["net_return"], 0)
