"""운용 코드와의 일치·미래 정보 차단·공동 자금·비용 정합성을 검증한다."""
import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from research.engine_backtest import prepare_record, replay, snapshots
from strategy.engine import load_config
from trading.paper import PAPER_DEFAULTS, PaperAccount


def example_record():
    opening = datetime(2026, 10, 20, 13, 30, tzinfo=timezone.utc)
    candles = []
    for index in range(150):
        price = 100 if index < 100 else (101.2 if index < 110 else 97)
        close = 101 if 100 <= index < 105 else price
        candles.append({"timestamp": (opening + timedelta(minutes=index + 1)).isoformat(),
                        "openPrice": price, "highPrice": max(price, close) + .1,
                        "lowPrice": min(price, close) - .1, "closePrice": close,
                        "volume": 400 if 100 <= index < 105 else 100, "currency": "USD"})
    return {"market": "US", "symbol": "AAPL", "candles": candles}


class EngineBacktestTests(unittest.TestCase):
    def setUp(self):
        self.record = example_record()
        self.sessions = prepare_record(self.record)
        self.strategy = {"news_enabled": False}
        self.settings = copy.deepcopy(PAPER_DEFAULTS)
        self.prepared = {"US:AAPL": self.sessions}

    def run_replay(self, **overrides):
        options = {"prepared": self.prepared, "symbols": [("US", "AAPL")],
                   "strategy_overrides": self.strategy, "paper_settings": self.settings,
                   "spread_ratio": .001, "start": "2026-10-20", "end": "2026-10-20",
                   "capture_decisions": True}
        options.update(overrides)
        return replay(**options)

    def test_matches_real_paper_account_for_every_decision_and_final_state(self):
        result = self.run_replay()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paper.json"
            account = PaperAccount(path, self.settings)
            decisions = [account.evaluate_snapshot(snapshot, self.strategy) for _, snapshot in snapshots(
                self.sessions, "US", "AAPL", .001, load_config(self.strategy), "2026-10-20", "2026-10-20")]
            self.assertEqual(decisions, result["decisions"])
            self.assertEqual(account.state, result["state"])
            self.assertEqual(PaperAccount(path, self.settings).state, result["state"])
        self.assertEqual(len(result["closed_trades"]), 1)
        self.assertEqual(result["closed_trades"][0]["exit"]["reason"], "stop_loss")

    def test_future_and_current_unfinished_ohlcv_do_not_change_prefix(self):
        changed = copy.deepcopy(self.record)
        # 11:15 시가 호가만 알려진 시각에 현재 분의 나머지 정보는 미완성이다.
        for index, candle in enumerate(changed["candles"]):
            if index >= 105:
                candle.update(highPrice=10000, lowPrice=1, closePrice=9000, volume=999999)
            if index > 105:
                candle["openPrice"] = 5000
        original = self.run_replay()
        other = self.run_replay(prepared={"US:AAPL": prepare_record(changed)})
        self.assertEqual(original["decisions"][:106], other["decisions"][:106])
        self.assertEqual(original["decisions"][105]["action"], "BUY")

    def test_shared_position_limit_and_configured_symbol_priority(self):
        settings = {**self.settings, "max_positions_per_market": 1}
        prepared = {"US:AAPL": self.sessions, "US:MSFT": self.sessions}
        for symbols in [[("US", "AAPL"), ("US", "MSFT")], [("US", "MSFT"), ("US", "AAPL")]]:
            result = self.run_replay(prepared=prepared, symbols=symbols, paper_settings=settings)
            self.assertEqual(result["summary"]["maximum_positions"], 1)
            self.assertEqual(result["state"]["trades"][0]["symbol"], symbols[0][1])
            self.assertGreater(result["failed_checks"].get("risk_budget_available", 0), 0)
            self.assertGreaterEqual(result["state"]["cash"]["US"], 0)

    def test_cost_attribution_and_cash_reconcile(self):
        result = self.run_replay()
        for trade in result["closed_trades"]:
            self.assertAlmostEqual(trade["gross_mid_pnl"] - trade["spread_cost"]
                                   - trade["slippage_cost"] - trade["fees"], trade["net_pnl"], places=9)
        initial = self.settings["starting_cash"]["US"]
        self.assertAlmostEqual(initial + sum(t["cash_flow"] for t in result["state"]["trades"]),
                               result["state"]["cash"]["US"])
        self.assertAlmostEqual(result["summary"]["realized_pnl"], result["summary"]["final_equity"] - initial)

    def test_open_positions_are_not_forcibly_closed_and_exit_costs_are_reserved(self):
        record = copy.deepcopy(self.record)
        record["candles"] = record["candles"][:108]
        result = self.run_replay(prepared={"US:AAPL": prepare_record(record)})
        self.assertEqual(result["summary"]["open_positions"], 1)
        self.assertEqual(result["summary"]["closed_trades"], 0)
        self.assertEqual([t["action"] for t in result["state"]["trades"]], ["BUY"])
        self.assertLess(result["curve"][-1]["net_liquidation_equity"], result["curve"][-1]["equity"])

    def test_missing_minute_does_not_get_filled(self):
        record = copy.deepcopy(self.record)
        del record["candles"][60]
        result = self.run_replay(prepared={"US:AAPL": prepare_record(record)})
        self.assertIn("non_contiguous_bars", result["reasons"])
        self.assertEqual(result["summary"]["closed_trades"], 0)
        self.assertEqual(result["summary"]["processed_snapshots"], 149)

    def test_duplicate_minute_is_rejected(self):
        self.record["candles"].append(self.record["candles"][0])
        with self.assertRaisesRegex(ValueError, "중복"):
            prepare_record(self.record)

    def test_news_enabled_strategy_is_explicitly_rejected(self):
        with self.assertRaisesRegex(ValueError, "뉴스"):
            self.run_replay(strategy_overrides={"news_enabled": True})

    def test_paper_settings_are_validated_by_original_constructor(self):
        with self.assertRaises(ValueError):
            self.run_replay(paper_settings={**self.settings, "slippage_ratio": 2})

    def test_inputs_are_not_mutated(self):
        before = copy.deepcopy((self.prepared, self.settings, self.strategy))
        self.run_replay()
        self.assertEqual(before, (self.prepared, self.settings, self.strategy))

    def test_calendar_excludes_holiday_and_extended_hours(self):
        record = example_record()
        holiday = copy.deepcopy(record["candles"][0])
        holiday["timestamp"] = "2026-12-25T14:31:00+00:00"
        extended = copy.deepcopy(holiday)
        extended["timestamp"] = "2026-10-20T12:31:00+00:00"
        record["candles"].extend([holiday, extended])
        sessions = prepare_record(record)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(sessions[0]["minutes"]), 150)

    def test_overnight_gap_stop_runs_before_new_day_bar_warmup(self):
        record = copy.deepcopy(self.record)
        record["candles"] = record["candles"][:108]
        gap = copy.deepcopy(record["candles"][0])
        gap.update(timestamp="2026-10-21T13:31:00+00:00", openPrice=80,
                   highPrice=80.1, lowPrice=79.9, closePrice=80)
        record["candles"].append(gap)
        result = self.run_replay(prepared={"US:AAPL": prepare_record(record)}, end="2026-10-21")
        trade = result["closed_trades"][0]
        self.assertEqual(trade["exit"]["reason"], "stop_loss")
        self.assertLess(trade["exit"]["price"], 80)
        self.assertEqual(result["decisions"][-1]["action"], "SELL")

    def test_exchange_early_close_excludes_later_minutes(self):
        record = example_record()
        template = record["candles"][0]
        opening = datetime(2026, 11, 27, 14, 30, tzinfo=timezone.utc)
        record["candles"] = [{**template, "timestamp": (opening + timedelta(minutes=i + 1)).isoformat()}
                             for i in range(390)]
        sessions = prepare_record(record)
        self.assertEqual(sessions[0]["expected_minutes"], 210)
        self.assertEqual(len(sessions[0]["minutes"]), 210)


if __name__ == "__main__":
    unittest.main()
