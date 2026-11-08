"""운영 장애·영속 저장·일봉 재시작·주문 응답 유실을 외부 호출 없이 검증한다."""
import copy
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from app.operations import OperationMonitor
from app.stateio import atomic_json, rotate_log, restore_paper
from app.runtime import load_run_settings, acquire_run_lock
from broker.sessions import regular_session
from paths import CONFIG_ROOT
from trading.paper import PaperAccount
from trading.daily_account import DailyAccount, session_after, last_closed_day
from trading.orders import OrderManager, limit_price
from Test.sample_data import sample, later


class StorageOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def test_failed_atomic_replace_preserves_original(self):
        path = self.folder / "state.json"
        atomic_json(path, {"cash": 10})
        with patch("app.stateio.os.replace", side_effect=OSError("full")):
            with self.assertRaises(OSError):
                atomic_json(path, {"cash": 0})
        self.assertEqual(json.loads(path.read_text())["cash"], 10)

    def test_log_rotation_is_bounded(self):
        path = self.folder / "decisions.jsonl"
        for index in range(8):
            path.write_text(str(index) * 100)
            rotate_log(path, 10, 2)
        self.assertTrue(path.with_name(path.name + ".2").exists())
        self.assertFalse(path.with_name(path.name + ".3").exists())

    def test_corruption_is_not_reset_and_restore_keeps_quarantine(self):
        path = self.folder / "account.json"
        account = PaperAccount(path)
        account.save()
        account.save()
        path.write_text("broken")
        with self.assertRaises(ValueError):
            PaperAccount(path)
        restore_paper(path)
        self.assertEqual(PaperAccount(path).state["cash"]["US"], 10000)
        self.assertTrue(list(self.folder.glob("*.quarantined-*")))
        self.assertTrue((self.folder / "PAUSE_BUYS").exists())

    def test_restore_refuses_active_lock(self):
        with acquire_run_lock(self.folder / "run.lock"):
            with self.assertRaises(OSError):
                restore_paper(self.folder / "account.json")

    def test_repeated_error_latches_across_restart(self):
        monitor = OperationMonitor(self.folder)
        for _ in range(3):
            monitor.error("US:AAPL", "timeout")
        restored = OperationMonitor(self.folder)
        self.assertIn("repeated_collection_errors", restored.state["buy_halts"])

    def test_low_disk_halts_only_buys_and_measures_cycle(self):
        monitor = OperationMonitor(self.folder, minimum_free_bytes=100)
        with patch("app.operations.shutil.disk_usage", return_value=Mock(free=50)):
            monitor.begin_cycle()
        snapshot = sample()
        monitor.observe(snapshot, 1.5)
        self.assertTrue(snapshot["operational_buy_block"])
        account = PaperAccount(self.folder / "account.json")
        decision = account.evaluate_snapshot(snapshot)
        self.assertEqual(decision["reason"], "operations_buy_halt")
        snapshot.pop("operational_buy_block")
        snapshot = later(snapshot)
        account.evaluate_snapshot(snapshot)
        sell = later(snapshot, bid=90)
        sell["operational_buy_block"] = True
        self.assertEqual(account.evaluate_snapshot(sell)["action"], "SELL")
        monitor.end_cycle(account, 60)
        self.assertGreater(monitor.state["expected_next_cycle_seconds"], 60)

    def test_linux_settings_preserve_windows_file(self):
        before = (CONFIG_ROOT / "settings.json").read_bytes()
        with patch.dict(os.environ, {"PYTRADING_SETTINGS": str(CONFIG_ROOT / "settings-linux.json")}):
            settings = load_run_settings()
        self.assertEqual(settings["env_file"], (CONFIG_ROOT.parent / "Credentials/kis-market.env").resolve())
        self.assertEqual(before, (CONFIG_ROOT / "settings.json").read_bytes())


class DailyExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "account.json"
        self.candidate = json.loads((CONFIG_ROOT / "fixed-trend-study.json").read_text(encoding="utf-8"))["candidate"]
        self.costs = json.loads((CONFIG_ROOT / "paper.json").read_text(encoding="utf-8"))
        self.account = DailyAccount(self.path, self.costs, self.candidate)
        self.plan = {"id": "2026-10-20:BUY:US:AAPL", "symbol": "US:AAPL", "side": "BUY", "execution_day": "2026-10-21", "signal_day": "2026-10-20", "close": 100, "atr": 1, "score": 1}
        self.account.state["pending_daily"] = [self.plan]
        self.account.save()

    def snapshot(self, stamp="2026-10-21T13:30:05+00:00", bid=99.9, ask=100):
        return {"market": "US", "symbol": "AAPL", "now": stamp, "quote": {"available_at": stamp, "bid": bid, "ask": ask}}

    def test_restart_restores_pending_and_exactly_one_fill(self):
        restored = DailyAccount(self.path, self.costs, self.candidate)
        self.assertEqual(restored.observe_quote(self.snapshot())["action"], "BUY")
        again = DailyAccount(self.path, self.costs, self.candidate)
        self.assertEqual(again.observe_quote(self.snapshot())["reason"], "duplicate_observation")
        self.assertEqual(len(again.state["trades"]), 1)

    def test_early_start_misses_open_window_without_historical_fill(self):
        self.account.process_started_at = datetime.fromisoformat("2026-10-21T13:20:00+00:00")
        result = self.account.observe_quote(self.snapshot("2026-10-21T13:36:00+00:00"))
        self.assertEqual(result["reason"], "missed_open_window")
        self.assertEqual(self.account.state["trades"], [])

    def test_stop_still_sells_when_operational_buys_halted(self):
        self.account.observe_quote(self.snapshot())
        snapshot = self.snapshot("2026-10-21T13:31:00+00:00", 95, 95.1)
        snapshot["operational_buy_block"] = True
        self.assertEqual(self.account.observe_quote(snapshot)["action"], "SELL")

    def test_save_failure_rolls_back_fill(self):
        before = copy.deepcopy(self.account.state)
        with patch.object(self.account, "save", side_effect=OSError("full")):
            with self.assertRaises(OSError):
                self.account.observe_quote(self.snapshot())
        self.assertEqual(self.account.state, before)

    def test_stale_quote_and_holiday_never_fill(self):
        stale = self.snapshot()
        stale["quote"]["available_at"] = "2026-10-21T13:29:00+00:00"
        self.assertEqual(self.account.observe_quote(stale)["reason"], "stale_quote")
        self.assertEqual(self.account.observe_quote(self.snapshot("2026-11-26T15:00:00+00:00"))["reason"], "outside_regular_session")

    def test_closed_signal_is_persisted_once_for_next_session(self):
        now = datetime(2026, 10, 20, 20, 3, tzinfo=timezone.utc)
        feature = {"ma200": 90, "close": 100, "atr": 1}
        with patch("trading.daily_account.make_features", return_value=[feature]), patch("trading.daily_account.signal", return_value={"enter": True, "exit": False, "score": 1}):
            self.assertTrue(self.account.plan_closed({"US:AAPL": [{"date": "2026-10-20", "high": 100, "close": 100}]}, [{"date": "2026-10-20"}], now))
            self.assertFalse(self.account.plan_closed({}, [], now))
        restored = DailyAccount(self.path, self.costs, self.candidate)
        self.assertEqual(restored.state["pending_daily"][0]["execution_day"], "2026-10-21")

    def test_future_daily_bar_does_not_plan(self):
        with self.assertRaises(ValueError):
            self.account.plan_closed({"US:AAPL": [{"date": "2026-10-21"}]}, [{"date": "2026-10-21"}], datetime(2026, 10, 21, 15, tzinfo=timezone.utc))

    def test_holiday_next_session_and_dst(self):
        self.assertEqual(session_after("2026-11-25"), "2026-11-27")
        self.assertIsNotNone(regular_session("US", datetime(2026, 11, 27, 17, tzinfo=timezone.utc)))
        self.assertIsNone(regular_session("US", datetime(2026, 11, 27, 18, tzinfo=timezone.utc)))

    def test_corporate_action_suspicion_blocks_entry_without_adjusting_quantity(self):
        result = self.account.observe_quote(self.snapshot(bid=49.9, ask=50))
        self.assertEqual(result['reason'], 'corporate_action_or_price_mismatch')
        self.assertEqual(self.account.state['positions'], {})
        self.assertEqual(self.account.state['trades'], [])
        restored = DailyAccount(self.path, self.costs, self.candidate)
        self.assertFalse(restored.state['corporate_action_suspicions']['US:AAPL']['quantity_adjusted'])
        self.assertEqual(restored.state['pending_daily'], [])

    def test_candidate_change_refused(self):
        changed = copy.deepcopy(self.candidate)
        changed["risk"]["trailing_atr"] = 3
        with self.assertRaises(ValueError):
            DailyAccount(self.path, self.costs, changed)


class OrderJournalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "orders.sqlite"
        self.manager = OrderManager(self.path)
        self.addCleanup(lambda: self.manager.close())
        self.snapshot = {"cash": "10000", "positions": {"AAPL": 5}, "position_costs": {"AAPL": "500"}, "initial": "10000", "exposure": "500", "as_of": datetime.now(timezone.utc).isoformat(), "daily_loss_ratio": 0, "consecutive_losses": 0, "last_loss_at": None}
        self.manager.reconcile(copy.deepcopy(self.snapshot), [], complete=True)

    def create(self, identifier="one", side="BUY", quantity=2):
        return self.manager.create(identifier, "AAPL", side, quantity, "100.009", "97", datetime.now(timezone.utc).isoformat())

    def verify_cancel(self):
        order=self.manager.state["orders"]["one"]
        proof={**order,"broker_id":order["broker_id"],"event_id":"verified-query",
            "order_type":"LIMIT","original_broker_id":None,"order_day":"","order_number":order["broker_id"],
            "mode":"internal","account_fingerprint":"internal:research"}
        self.manager.verify_cancellations([proof],complete=True)

    def test_response_loss_blocks_retry_and_restart_requires_reconcile(self):
        self.create()
        adapter = Mock()
        adapter.submit.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            self.manager.dispatch("one", adapter)
        self.assertEqual(self.manager.state["orders"]["one"]["status"], "UNKNOWN")
        with self.assertRaises(ValueError):
            self.manager.dispatch("one", adapter)
        self.assertEqual(adapter.submit.call_count, 1)
        self.manager.close()
        self.manager = OrderManager(self.path)
        self.assertFalse(self.manager.ready)
        with self.assertRaises(ValueError):
            self.manager.reconcile(copy.deepcopy(self.snapshot), [], complete=True)

    def test_crash_between_save_and_http_becomes_unknown(self):
        self.create()
        self.manager.state["orders"]["one"]["status"] = "SENDING"
        self.manager._save()
        self.manager.close()
        self.manager = OrderManager(self.path)
        self.assertEqual(self.manager.state["orders"]["one"]["status"], "UNKNOWN")

    def test_duplicate_signal_is_idempotent(self):
        quote_at = datetime.now(timezone.utc).isoformat()
        first = self.manager.create("same", "AAPL", "BUY", 2, 100, 97, quote_at)
        second = self.manager.create("same", "AAPL", "BUY", 2, 100, 97, quote_at)
        self.assertEqual(first, second)
        self.assertEqual(len(self.manager.state["orders"]), 1)

    def test_partial_duplicate_out_of_order_and_cancel_race(self):
        self.create()
        self.manager.dispatch("one", Mock(submit=Mock(return_value="B1")))
        self.manager.update("one", "a", 1, "100", "PARTIAL")
        cash = self.manager.state["account"]["cash"]
        self.manager.update("one", "a", 1, "100", "PARTIAL")
        self.manager.update("one", "older", 0, "0", "ACCEPTED")
        self.assertEqual(cash, self.manager.state["account"]["cash"])
        self.verify_cancel()
        self.manager.cancel("one", Mock())
        self.manager.update("one", "cancel", 1, "100", "CANCELLED")
        self.manager.update("one", "late-fill", 2, "200", "FILLED")
        self.assertEqual(self.manager.state["orders"]["one"]["status"], "FILLED")
        self.assertEqual(self.manager.state["account"]["positions"]["AAPL"], 7)

    def test_cancel_pending_survives_nonterminal_history(self):
        self.create()
        adapter = Mock(submit=Mock(return_value="B1"))
        self.manager.dispatch("one", adapter)
        self.verify_cancel()
        self.manager.cancel("one", adapter)
        self.manager.update("one", "still-open", 0, "0", "ACCEPTED")
        self.assertEqual(self.manager.state["orders"]["one"]["status"], "CANCEL_PENDING")
        with self.assertRaises(ValueError):
            self.manager.cancel("one", adapter)
        self.assertEqual(adapter.cancel.call_count, 1)

    def test_reserved_sells_cannot_exceed_holding(self):
        self.create("sell1", "SELL", 4)
        with self.assertRaises(ValueError):
            self.create("sell2", "SELL", 2)

    def test_reserved_buys_cannot_exceed_cash(self):
        self.manager.state["account"]["cash"] = "300"
        self.create()
        with self.assertRaises(ValueError):
            self.create("second")

    def test_loss_halt_does_not_block_valid_sell(self):
        self.manager.state["account"]["daily_loss_ratio"] = .03
        with self.assertRaises(ValueError):
            self.create()
        self.assertEqual(self.create("sell", "SELL")["status"], "INTENT")

    def test_incomplete_snapshot_never_unlocks_orders(self):
        with self.assertRaises(ValueError):
            self.manager.reconcile(self.snapshot, [], complete=False)
        with self.assertRaises(ValueError):
            self.create()

    def test_account_and_mode_are_isolated(self):
        self.manager.close()
        with self.assertRaises(ValueError):
            other = OrderManager(self.path, mode="kis_demo")
            other.close()
        self.manager = OrderManager(self.path)

    def test_unknown_product_etn_and_fractional_shares_blocked(self):
        for symbol, quantity in (("UNKNOWN", 1), ("Q123456", 1), ("AAPL", .5)):
            with self.assertRaises((ValueError, RuntimeError)):
                self.manager.create("bad", symbol, "BUY", quantity, 100, 97, datetime.now(timezone.utc).isoformat())

    def test_rounding_and_unsupported_subdollar(self):
        self.assertEqual(str(limit_price("100.009", "BUY")), "100.00")
        self.assertEqual(str(limit_price("100.001", "SELL")), "100.01")
        with self.assertRaises(ValueError):
            limit_price(".99", "BUY")

    def test_explicit_rejection_is_not_response_loss(self):
        from broker.kis_api.client import KisOrderRejected
        self.create()
        adapter = Mock(submit=Mock(side_effect=KisOrderRejected("rejected")))
        with self.assertRaises(KisOrderRejected):
            self.manager.dispatch("one", adapter)
        self.assertEqual(self.manager.state["orders"]["one"]["status"], "REJECTED")

    def test_second_process_cannot_open_same_order_journal(self):
        with self.assertRaises(OSError):
            OrderManager(self.path)

    def test_live_mode_never_transmits(self):
        path = Path(self.temporary.name) / "live.sqlite"
        manager = OrderManager(path, "live")
        try:
            manager.reconcile(copy.deepcopy(self.snapshot), [], complete=True)
            manager.create("live", "AAPL", "BUY", 1, 100, 97, datetime.now(timezone.utc).isoformat())
            adapter = Mock()
            with self.assertRaises(ValueError):
                manager.dispatch("live", adapter)
            adapter.submit.assert_not_called()
        finally:
            manager.close()


class LateStartEntryTests(unittest.TestCase):
    """사용자가 요청한 늦은 실행 예외. 모든 호가·계획은 외부 호출 없는 합성 자료다."""

    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "account.json"
        self.costs = json.loads((CONFIG_ROOT / "paper.json").read_text(encoding="utf-8"))
        self.candidate = json.loads((CONFIG_ROOT / "fixed-trend-study.json").read_text(encoding="utf-8"))["candidate"]

    def account(self, start="2026-10-21T13:36:00+00:00", execution_day="2026-10-21"):
        account = DailyAccount(self.path, self.costs, self.candidate,
                               process_started_at=datetime.fromisoformat(start))
        account.state["pending_daily"] = [{"id": "2026-10-20:BUY:US:AAPL", "symbol": "US:AAPL",
            "side": "BUY", "execution_day": execution_day, "signal_day": "2026-10-20",
            "close": 100, "atr": 1, "score": 1}]
        return account

    def snapshot(self, at="2026-10-21T15:00:00+00:00", bid=99.9, ask=100):
        return {"market": "US", "symbol": "AAPL", "now": at,
                "quote": {"available_at": at, "bid": bid, "ask": ask}}

    def test_late_start_buys_at_current_price_with_audit(self):
        account = self.account()
        result = account.observe_quote(self.snapshot(bid=100.9, ask=101))
        self.assertEqual(result["action"], "BUY")
        self.assertEqual(result["paper_fill"]["reference_price"], 101)
        self.assertTrue(result["entry_timing"]["late_start_exception"])
        self.assertEqual(result["paper_fill"]["entry_timing"]["process_started_at"], account.process_started_at.isoformat())

    def test_preopen_start_does_not_gain_exception_after_slow_history(self):
        account = self.account("2026-10-21T13:20:00+00:00")
        self.assertEqual(account.observe_quote(self.snapshot())["reason"], "missed_open_window")
        self.assertEqual(account.state["trades"], [])

    def test_start_during_first_five_minutes_keeps_original_window(self):
        account = self.account("2026-10-21T13:34:00+00:00")
        self.assertEqual(account.observe_quote(self.snapshot())["reason"], "missed_open_window")

    def test_exact_five_minute_start_is_not_late(self):
        account = self.account("2026-10-21T13:35:00+00:00")
        self.assertEqual(account.observe_quote(self.snapshot())["reason"], "missed_open_window")

    def test_just_after_five_minute_start_qualifies(self):
        account = self.account("2026-10-21T13:35:00.000001+00:00")
        self.assertEqual(account.observe_quote(self.snapshot())["action"], "BUY")

    def test_original_entry_at_exact_five_minutes_is_preserved(self):
        account = self.account("2026-10-21T13:20:00+00:00")
        self.assertEqual(account.observe_quote(self.snapshot("2026-10-21T13:35:00+00:00"))["action"], "BUY")

    def test_prior_session_start_does_not_extend_next_day(self):
        account = self.account("2026-10-20T15:00:00+00:00")
        self.assertEqual(account.observe_quote(self.snapshot())["reason"], "missed_open_window")

    def test_old_plan_is_expired_even_for_late_start(self):
        account = self.account(execution_day="2026-10-20")
        self.assertEqual(account.observe_quote(self.snapshot())["reason"], "missed_open_window")

    def test_future_start_does_not_qualify(self):
        account = self.account("2026-10-21T16:00:00+00:00")
        self.assertEqual(account.observe_quote(self.snapshot())["reason"], "missed_open_window")

    def test_late_start_does_not_bypass_gap_or_operational_halt(self):
        account = self.account()
        quote = self.snapshot()
        quote["operational_buy_block"] = True
        self.assertEqual(account.observe_quote(quote)["reason"], "operations_buy_halt")
        self.assertEqual(len(account.state["pending_daily"]), 1)
        self.assertEqual(account.observe_quote(self.snapshot("2026-10-21T15:01:00+00:00", 104, 104.1))["reason"], "entry_gap_cancelled")
        self.assertEqual(account.state["trades"], [])

    def test_late_start_still_requires_fresh_quote_and_plan(self):
        account = self.account()
        stale = self.snapshot()
        stale["quote"]["available_at"] = "2026-10-21T14:58:00+00:00"
        self.assertEqual(account.observe_quote(stale)["reason"], "stale_quote")
        account.state["pending_daily"] = []
        self.assertEqual(account.observe_quote(self.snapshot())["reason"], "no_daily_plan")

    def test_restart_uses_new_start_and_restores_only_unconsumed_plans(self):
        account = self.account("2026-10-21T13:20:00+00:00")
        account.save()
        restored = DailyAccount(self.path, self.costs, self.candidate,
                                process_started_at=datetime.fromisoformat("2026-10-21T14:00:00+00:00"))
        self.assertEqual(len(restored.state["pending_daily"]), 1)
        self.assertEqual(restored.observe_quote(self.snapshot())["action"], "BUY")
        again = DailyAccount(self.path, self.costs, self.candidate,
                             process_started_at=datetime.fromisoformat("2026-10-21T15:01:00+00:00"))
        self.assertEqual(again.state["pending_daily"], [])
        self.assertEqual(again.observe_quote(self.snapshot("2026-10-21T15:02:00+00:00"))["action"], "HOLD")
        self.assertEqual(len(again.state["trades"]), 1)

    def test_restart_does_not_revive_expired_plan(self):
        account = self.account("2026-10-21T13:20:00+00:00")
        self.assertEqual(account.observe_quote(self.snapshot())["reason"], "missed_open_window")
        restored = DailyAccount(self.path, self.costs, self.candidate,
                                process_started_at=datetime.fromisoformat("2026-10-21T15:01:00+00:00"))
        self.assertEqual(restored.observe_quote(self.snapshot("2026-10-21T15:02:00+00:00"))["reason"], "no_daily_plan")

    def test_early_close_and_dst_follow_exchange_session(self):
        account = self.account("2026-11-27T14:36:00+00:00", execution_day="2026-11-27")
        self.assertTrue(account.entry_timing(datetime.fromisoformat("2026-11-27T17:59:00+00:00"))["entry_window_open"])
        self.assertFalse(account.entry_timing(datetime.fromisoformat("2026-11-27T18:00:00+00:00"))["entry_window_open"])
        self.assertEqual(account.observe_quote(self.snapshot("2026-11-27T18:00:00+00:00"))["reason"], "outside_regular_session")

    def test_naive_start_is_rejected(self):
        with self.assertRaises(ValueError):
            self.account("2026-10-21T13:36:00")

    def test_service_captures_start_before_initialization_and_audits_it(self):
        """실제 서비스 진입점이 초기화 완료 시각 대신 최초 진입 시각을 전달한다."""
        from contextlib import ExitStack
        from app import daily_service
        from unittest.mock import MagicMock
        late = datetime.fromisoformat("2026-10-21T15:00:00+00:00")
        for stamp, expected in (("2026-10-21T13:20:00+00:00", False),
                                ("2026-10-21T13:36:00+00:00", True)):
            with self.subTest(start=stamp), ExitStack() as stack:
                start = datetime.fromisoformat(stamp)
                directory = Path(self.temporary.name) / ("late" if expected else "early")
                clock = stack.enter_context(patch.object(daily_service, "datetime", wraps=datetime))
                clock.now.side_effect = [start, late, late]
                runtime = {"broker": "kis", "symbols": [("US", "AAPL")], "interval": 60,
                           "paper_settings": CONFIG_ROOT / "paper.json", "broker_config": "unused",
                           "env_file": "unused"}
                stack.enter_context(patch.object(daily_service, "load_run_settings", return_value=runtime))
                stack.enter_context(patch.object(daily_service, "DATA_ROOT", Path(self.temporary.name)))
                stack.enter_context(patch.dict(os.environ, {"PYTRADING_DAILY_DIR": str(directory)}))
                stack.enter_context(patch("trading.execution.load_execution", return_value={"mode": "internal_paper"}))
                monitor = stack.enter_context(patch.object(daily_service, "OperationMonitor")).return_value
                monitor.state = {"errors": {}}
                journal = MagicMock()
                stack.enter_context(patch.object(daily_service, "ObservationJournal")).return_value.__enter__.return_value = journal
                stack.enter_context(patch.object(daily_service, "last_closed_day", return_value="2026-10-20"))
                stack.enter_context(patch.object(daily_service, "load_kis_settings", return_value={}))
                client_factory = stack.enter_context(patch.object(daily_service, "create_kis_client"))
                stack.enter_context(patch.object(daily_service, "collect_us_history", return_value=({"collection_complete": False}, {})))
                stack.enter_context(patch.object(daily_service, "observe_symbol"))
                stack.enter_context(patch.object(daily_service.signal, "signal"))
                daily_service.run(watch=False)
                # 인증·시세 요청을 하는 클라이언트 메서드는 어느 것도 호출하지 않는다.
                client_factory.return_value.get.assert_not_called()
                startup = next(call.args[1] for call in journal.record.call_args_list if call.args[0] == "startup")
                self.assertEqual(startup["entry_timing"]["process_started_at"], stamp)
                self.assertEqual(startup["entry_timing"]["late_start_exception"], expected)

    def test_late_start_still_manages_sell_when_buys_halted(self):
        account = self.account()
        self.assertEqual(account.observe_quote(self.snapshot())["action"], "BUY")
        snapshot = self.snapshot("2026-10-21T15:01:00+00:00", 95, 95.1)
        snapshot["operational_buy_block"] = True
        self.assertEqual(account.observe_quote(snapshot)["action"], "SELL")

    def test_late_start_does_not_bypass_portfolio_risk_limits(self):
        account = self.account()
        with patch("trading.daily_account.entry_limits", return_value=("daily_loss_limit", 0, None)):
            self.assertEqual(account.observe_quote(self.snapshot())["reason"], "safety_daily_loss_limit")
        self.assertEqual(account.state["trades"], [])
        self.assertEqual(len(account.state["pending_daily"]), 1)
