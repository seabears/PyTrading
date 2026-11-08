"""합성 시세로 매수 제한과 가격 매도 유지·상태 보존을 검사한다."""
import copy
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from trading.paper import PaperAccount
from trading.safety import local_day
from strategy.engine import parse_timestamp
from Test.sample_data import sample


def fresh(seconds=0, symbol=None, bid=None):
    row = sample()
    offset = timedelta(seconds=seconds)
    row["now"] = (parse_timestamp(row["now"]) + offset).isoformat()
    row["quote"]["available_at"] = row["now"]
    for bar in row["bars"]:
        for field in ("start", "end", "available_at"):
            bar[field] = (parse_timestamp(bar[field]) + offset).isoformat()
    for event in row["news_events"]:
        event["available_at"] = (parse_timestamp(event["available_at"]) + offset).isoformat()
    if symbol:
        row["symbol"] = symbol
        row["news_events"][0]["symbol"] = symbol
    if bid is not None:
        row["quote"].update(bid=bid, ask=bid + .1)
    return row


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "account.json"
        self.account = PaperAccount(self.path)

    def test_manual_pause_blocks_new_buy_but_keeps_stop_loss(self):
        self.account.evaluate_snapshot(fresh())
        (self.path.parent / "PAUSE_BUYS").touch()
        result = self.account.evaluate_snapshot(fresh(60, "OTHER"))
        self.assertEqual(result["reason"], "safety_manual_buy_pause")
        result = self.account.evaluate_snapshot(fresh(60, bid=95))
        self.assertEqual(result["reason"], "stop_loss")
        self.assertIn("paper_fill", result)

    def test_daily_loss_halt_survives_restart_and_resets_next_local_day(self):
        self.account.evaluate_snapshot(fresh())
        self.account.evaluate_snapshot(fresh(60, bid=75))
        restored = PaperAccount(self.path)
        result = restored.evaluate_snapshot(fresh(2000))
        self.assertEqual(result["reason"], "safety_daily_loss_halt")
        next_day = restored.evaluate_snapshot(fresh(86400))
        self.assertEqual(next_day["action"], "BUY")

    def test_daily_loss_latch_does_not_clear_on_price_recovery(self):
        account = self.account
        account.evaluate_snapshot(fresh())
        account.safety_policy["daily_loss_limit"] = .0001
        account.evaluate_snapshot(fresh(60, bid=100.9))
        self.assertTrue(account.state["safety_days"]["US"]["loss_halted"])
        account.evaluate_snapshot(fresh(120, bid=105))
        result = account.evaluate_snapshot(fresh(120, "OTHER"))
        self.assertEqual(result["reason"], "safety_daily_loss_halt")

    def test_daily_buy_count_is_market_local_and_persistent(self):
        account = PaperAccount(self.path, safety_policy={"maximum_buys_per_day": 1})
        account.evaluate_snapshot(fresh())
        restored = PaperAccount(self.path, safety_policy={"maximum_buys_per_day": 1})
        self.assertEqual(restored.evaluate_snapshot(fresh(60, "OTHER"))["reason"], "safety_daily_buy_limit")

    def test_three_losses_pause_buys_then_resume_after_cooldown(self):
        for seconds in (0, 1920, 3840):
            self.assertEqual(self.account.evaluate_snapshot(fresh(seconds))["action"], "BUY")
            self.account.evaluate_snapshot(fresh(seconds + 60, bid=95))
        result = self.account.evaluate_snapshot(fresh(5760))
        self.assertEqual(result["reason"], "safety_consecutive_loss_pause")
        self.assertEqual(self.account.evaluate_snapshot(fresh(7561))["action"], "BUY")

    def test_trade_risk_sizes_down_a_wider_stop(self):
        result = self.account.evaluate_snapshot(fresh(), {"stop_loss": .2})
        trade = result["paper_fill"]
        metrics = result["metrics"]["safety"]
        self.assertLess(trade["quantity"], 9)
        self.assertLessEqual(trade["quantity"] * metrics["risk_per_share_at_stop"], 50)

    def test_total_exposure_cap_blocks_more_buys(self):
        account = PaperAccount(self.path, safety_policy={"maximum_exposure_fraction": .1})
        account.evaluate_snapshot(fresh())
        account.evaluate_snapshot(fresh(60, "SECOND"))
        result = account.evaluate_snapshot(fresh(60, "THIRD"))
        self.assertEqual(result["reason"], "safety_risk_or_exposure_limit")
        committed = sum(position["cost_basis"] for position in account.state["positions"].values())
        self.assertLessEqual(committed, 1000)

    def test_stale_other_position_blocks_buy_without_blocking_sell(self):
        self.account.evaluate_snapshot(fresh())
        result = self.account.evaluate_snapshot(fresh(240, "OTHER"))
        self.assertEqual(result["reason"], "safety_portfolio_quote_unavailable")
        self.assertEqual(self.account.evaluate_snapshot(fresh(241, bid=95))["action"], "SELL")

    def test_unavailable_legacy_quote_timestamp_is_not_assumed_fresh(self):
        self.account.evaluate_snapshot(fresh())
        self.account.state.pop("quote_times")
        self.account.save()
        restored = PaperAccount(self.path)
        self.assertEqual(restored.evaluate_snapshot(fresh(60, "OTHER"))["reason"], "safety_portfolio_quote_unavailable")

    def test_missing_legacy_mark_blocks_buy_without_blocking_price_stop(self):
        self.account.evaluate_snapshot(fresh())
        self.account.state.pop("last_prices")
        self.account.state.pop("safety_days")
        self.account.save()
        restored = PaperAccount(self.path)
        self.assertEqual(restored.evaluate_snapshot(fresh(60, bid=95))["action"], "SELL")
        self.assertEqual(restored.evaluate_snapshot(fresh(120, "OTHER"))["reason"], "safety_valuation_unavailable")

    def test_quote_jump_blocks_entry_for_one_observation(self):
        first = fresh()
        first["risk_budget_available"] = False
        # 가격 관측만 기록하고 신규 매수는 만들지 않는다.
        first["bars"] = []
        self.account.evaluate_snapshot(first)
        row = fresh(60, bid=120)
        row["bars"][-1].update(close=120, high=121)
        for bar in row["bars"][:-1]:
            bar.update(low=117, high=119, close=118)
        result = self.account.evaluate_snapshot(row)
        self.assertEqual(result["reason"], "safety_abrupt_quote_change")

    def test_outside_session_quote_does_not_raise_peak(self):
        self.account.evaluate_snapshot(fresh())
        row = fresh(60, bid=200)
        row["regular_session_open"] = False
        before = self.account.state["positions"]["US:DEMO_US"]["peak_bid_since_entry"]
        self.account.evaluate_snapshot(row)
        self.assertEqual(self.account.state["positions"]["US:DEMO_US"]["peak_bid_since_entry"], before)

    def test_invalid_quote_does_not_change_account(self):
        before = copy.deepcopy(self.account.state)
        row = fresh()
        row["quote"]["bid"] = "NaN"
        self.assertEqual(self.account.evaluate_snapshot(row)["reason"], "invalid_quote")
        self.assertEqual(self.account.state, before)

    def test_save_failure_rolls_back_memory_and_does_not_fake_fill(self):
        before = copy.deepcopy(self.account.state)
        with patch.object(self.account, "save", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                self.account.evaluate_snapshot(fresh())
        self.assertEqual(self.account.state, before)
        self.assertFalse(self.path.exists())

    def test_failed_sell_save_can_retry_once_without_double_cash_flow(self):
        self.account.evaluate_snapshot(fresh())
        before = copy.deepcopy(self.account.state)
        disk_before = self.path.read_bytes()
        with patch.object(self.account, "save", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                self.account.evaluate_snapshot(fresh(60, bid=95))
        self.assertEqual(self.account.state, before)
        self.assertEqual(self.path.read_bytes(), disk_before)
        self.assertEqual(self.account.evaluate_snapshot(fresh(60, bid=95))["action"], "SELL")
        self.assertEqual(len(self.account.state["trades"]), 2)

    def test_corrupt_cash_ledger_is_not_silently_reset(self):
        self.account.evaluate_snapshot(fresh())
        state = json.loads(self.path.read_text(encoding="utf-8"))
        state["cash"]["US"] += 100
        original = json.dumps(state)
        self.path.write_text(original, encoding="utf-8")
        with self.assertRaises(ValueError):
            PaperAccount(self.path)
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_us_local_day_does_not_reset_at_korean_midnight(self):
        before = parse_timestamp("2026-10-09T23:50:00+09:00")
        after = parse_timestamp("2026-10-10T00:10:00+09:00")
        self.assertEqual(local_day("US", before), local_day("US", after))

    def test_existing_account_financial_settings_are_compatible(self):
        self.account.evaluate_snapshot(fresh())
        previous_cash = self.account.state["cash"]["US"]
        restored = PaperAccount(self.path, safety_policy={"maximum_buys_per_day": 2})
        self.assertEqual(restored.state["cash"]["US"], previous_cash)
        self.assertEqual(len(restored.state["trades"]), 1)

    def test_removed_watchlist_position_still_gets_stop_check_after_other_quote_failure(self):
        import contextlib
        import io
        from app.runtime import load_run_settings
        from app import runner
        self.account.evaluate_snapshot(fresh())
        strategy = self.path.parent / "price-only.json"
        strategy.write_text(json.dumps({"news_enabled": False, "earnings_enabled": False}), encoding="utf-8")
        settings = load_run_settings()
        settings.update(output_dir=self.path.parent, watch=False, collect_news=False,
                        symbols=[("US", "AAPL")], strategy_config=strategy)
        def collect(client, market, symbol, options):
            if symbol == "AAPL":
                raise ValueError("malformed quote")
            return fresh(60, bid=95)
        with patch("app.runner.load_run_settings", return_value=settings), \
             patch("app.runner.create_kis_client"), \
             patch("app.runner.collect_kis_snapshot", side_effect=collect) as quotes, \
             contextlib.redirect_stdout(io.StringIO()):
            runner.main(argv=[])
        self.assertEqual(quotes.call_count, 2)
        restored = PaperAccount(self.path)
        self.assertEqual(restored.state["positions"], {})
        self.assertEqual(restored.state["trades"][-1]["reason"], "stop_loss")
