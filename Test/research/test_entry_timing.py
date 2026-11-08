"""매수 시점 연구의 정보 시점·비용·미체결·자료 경계를 검증한다."""
import copy
import unittest
from datetime import date, datetime, timedelta, timezone

from research.entry_timing import entry_decision, measure_event, net_return, study_series, summarize
from research.entry_inputs import daily_inputs, intraday_inputs


ZERO = {"buy_cost_ratio": 0, "sell_cost_ratio": 0, "slippage_ratio": 0}
MODES = [{"name": "base", "kind": "immediate"}, {"name": "wait", "kind": "delay", "wait": 2}]


def sample():
    bars = [{"date": "2026-01-01", "open": 101, "high": 104, "low": 100, "close": 102, "volume": 100} for _ in range(40)]
    anchor = {"index": 0, "level": 100, "atr": 4, "volume_ratio": 2,
        "symbol": "TEST", "date": "2026-01-01", "stage": "test", "period_end": "2026-12-31",
        "time_bucket": "daily", "event_id": "a"}
    return bars, anchor


class EntryTimingTests(unittest.TestCase):
    def test_signal_close_cannot_fill_same_bar(self):
        bars, anchor = sample()
        self.assertEqual(entry_decision(bars, anchor, MODES[0], 1, 10, .03), (1, "filled"))

    def test_entry_bar_future_fields_are_invisible(self):
        bars, anchor = sample()
        expected = entry_decision(bars, anchor, MODES[0], 1, 10, .03)
        bars[1].update(high=10000, low=1, close=1, volume=100000)
        self.assertEqual(entry_decision(bars, anchor, MODES[0], 1, 10, .03), expected)

    def test_confirmation_buys_following_open(self):
        bars, anchor = sample()
        mode = {"name": "confirm", "kind": "confirm", "wait": 1}
        self.assertEqual(entry_decision(bars, anchor, mode, 1, 10, .03), (2, "filled"))
        bars[1]["close"] = 101
        self.assertEqual(entry_decision(bars, anchor, mode, 1, 10, .03)[1], "confirmation_failed")

    def test_invalidation_cancels_even_if_later_recovers(self):
        bars, anchor = sample()
        bars[1]["close"] = 99
        self.assertEqual(entry_decision(bars, anchor, MODES[1], 1, 10, .03)[1], "breakout_invalidated")

    def test_retest_waits_for_completed_block(self):
        bars, anchor = sample()
        bars[1]["low"] = 100
        mode = {"name": "retest", "kind": "retest", "wait": 15}
        self.assertEqual(entry_decision(bars, anchor, mode, 5, 15, .03), (6, "filled"))

    def test_retest_expires(self):
        bars, anchor = sample()
        for bar in bars:
            bar["low"] = 102
        mode = {"name": "retest", "kind": "retest", "wait": 5}
        self.assertEqual(entry_decision(bars, anchor, mode, 1, 10, .03)[1], "retest_not_seen")

    def test_gap_and_volume_cancellations(self):
        bars, anchor = sample()
        bars[1]["open"] = 110
        self.assertEqual(entry_decision(bars, anchor, MODES[0], 1, 10, .03)[1], "gap_limit")
        mode = {"name": "volume", "kind": "volume", "minimum": 3}
        self.assertEqual(entry_decision(bars, anchor, mode, 1, 10, .03)[1], "volume_filter")

    def test_costs_match_cash_flows(self):
        costs = {"buy_cost_ratio": .001, "sell_cost_ratio": .002, "slippage_ratio": .001}
        expected = 110 * .9995 * .999 * .998 / (100 * 1.0005 * 1.001 * 1.001) - 1
        self.assertAlmostEqual(net_return(100, 110, costs, .001), expected)
        self.assertLess(net_return(100, 110, costs, .001, 2), expected)

    def test_common_exit_does_not_move_with_entry(self):
        bars, anchor = sample()
        bars[5]["close"], bars[7]["close"] = 105, 115
        rows = measure_event(bars, anchor, MODES, [5], 1, 10, .03, ZERO, 0)
        self.assertEqual({row["common_exit_index"] for row in rows}, {5})
        self.assertAlmostEqual(rows[1]["common_net"], 105 / 101 - 1)
        self.assertAlmostEqual(rows[1]["holding_net"], 115 / 101 - 1)

    def test_late_entry_is_cash_at_short_common_exit(self):
        bars, anchor = sample()
        rows = measure_event(bars, anchor, MODES, [1], 1, 10, .03, ZERO, 0)
        self.assertIsNone(rows[1]["common_net"])
        self.assertEqual(rows[1]["reason"], "after_common_exit")
        self.assertIsNotNone(rows[1]["holding_net"])

    def test_cancellations_remain_in_opportunity_mean(self):
        bars, anchor = sample()
        modes = [MODES[0], {"name": "blocked", "kind": "volume", "minimum": 3}]
        rows = measure_event(bars, anchor, modes, [5], 1, 10, .03, ZERO, 0)
        summary = {row["mode"]: row for row in summarize(rows, "base")}
        self.assertEqual(summary["blocked"]["events"], 1)
        self.assertEqual(summary["blocked"]["mean_all"], 0)
        self.assertAlmostEqual(summary["blocked"]["opportunity_delta"], -summary["base"]["mean_all"])

    def test_censor_gap_and_period_boundary(self):
        bars, anchor = sample()
        args = dict(modes=MODES, horizons=[5], step=1, max_wait=10, gap_limit=.03, costs=ZERO, spread=0)
        rows, audit = study_series(bars[:10], [anchor], **args)
        self.assertEqual(audit[0]["status"], "right_censored")
        self.assertFalse(rows)
        bars[4] = None
        self.assertEqual(study_series(bars, [anchor], **args)[1][0]["status"], "data_gap")
        bars, anchor = sample()
        bars[15]["date"] = "2027-01-01"
        self.assertEqual(study_series(bars, [anchor], **args)[1][0]["status"], "period_boundary")

    def test_spacing_does_not_rescue_later_signal_after_missing_data(self):
        bars, anchor = sample()
        second = {**anchor, "index": 2, "event_id": "b"}
        bars[1] = None
        rows, audit = study_series(bars, [anchor, second], MODES, [5], 1, 10, .03, ZERO, 0)
        self.assertEqual([row["status"] for row in audit], ["data_gap", "overlap_skipped"])


def minute_record(day="2026-09-21", count=390):
    opening = datetime.fromisoformat(day + "T13:30:00+00:00")
    candles = []
    for n in range(1, count + 1):
        signal = 101 <= n <= 105
        candles.append({"timestamp": (opening + timedelta(minutes=n)).isoformat(), "currency": "USD",
            "openPrice": 100, "highPrice": 103 if signal else 101, "lowPrice": 99,
            "closePrice": 102 if signal else 100, "volume": 1000 if signal else 100})
    return {"market": "US", "symbol": "TEST", "interval": "1m", "candles": candles}


class EntryInputTests(unittest.TestCase):
    def test_api_numeric_strings_are_normalized_before_decisions(self):
        record = minute_record()
        for candle in record["candles"]:
            for key in ("openPrice", "highPrice", "lowPrice", "closePrice", "volume"):
                candle[key] = str(candle[key])
        _, bars, anchors, _ = next(intraday_inputs("TEST", record))
        self.assertIsInstance(bars[105]["open"], float)
        entry_decision(bars, anchors[0], MODES[0], 5, 15, .003)

    def test_intraday_first_signal_requires_105_completed_minutes(self):
        symbol, bars, anchors, coverage = next(intraday_inputs("TEST", minute_record()))
        self.assertEqual(anchors[0]["index"], 104)
        self.assertEqual(anchors[0]["signal_time"], "2026-09-21T15:15:00+00:00")
        self.assertEqual(anchors[0]["time_bucket"], "11:00-12:00 NY")
        self.assertEqual(coverage["expected_minutes"], 390)

    def test_missing_minute_blocks_signal_without_filling(self):
        record = minute_record()
        del record["candles"][20]
        _, bars, anchors, _ = next(intraday_inputs("TEST", record))
        self.assertIsNone(bars[20])
        self.assertFalse(anchors)

    def test_daily_anchor_does_not_depend_on_future(self):
        candles = []
        day = date(2024, 1, 1)
        while len(candles) < 260:
            if day.weekday() < 5:
                price = 100 + len(candles)
                candles.append({"timestamp": day.isoformat() + "T00:00:00-05:00", "currency": "USD",
                    "openPrice": price, "highPrice": price + .1, "lowPrice": price - .1,
                    "closePrice": price, "volume": 100})
            day += timedelta(days=1)
        def records(length):
            return {symbol: {"market": "US", "interval": "1d", "candles": copy.deepcopy(candles[:length])} for symbol in ("TEST", "SPY")}
        periods = {"test": {"start": "2024-01-01", "end": "2025-12-31"}}
        full = next(daily_inputs(records(260), periods))[2]
        prefix = next(daily_inputs(records(230), periods))[2]
        self.assertTrue(prefix)
        self.assertEqual([row for row in full if row["index"] < 230], prefix)
        self.assertGreaterEqual(prefix[0]["index"], 200)
