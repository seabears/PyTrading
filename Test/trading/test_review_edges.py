"""주문 계약·예약·취소·관측 원장의 추가 경계 검사. 모든 입력은 합성이다."""

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from trading.orders import OrderManager
from trading.reconciliation import normalize_orders, normalize_snapshot, synchronize
from trading.observation_journal import ObservationJournal
from broker.kis_api.client import KisPreflightError, KisOrderRejected, KisOrderStateUnknown
from Test.trading.test_review_regressions import account, event
from trading.paper import PaperAccount


class ReconciliationEdges(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.manager = OrderManager(Path(self.temporary.name) / "orders.sqlite")
        self.addCleanup(lambda: self.manager.close())
        self.manager.reconcile(account(), [], complete=True)
        self.manager.create("local", "AAPL", "BUY", 2, 100, 97, account()["as_of"])
        self.manager.dispatch("local", Mock(submit=Mock(return_value="20261027:123")))

    def proof(self, filled=0):
        proof = event(self.manager, filled=filled)
        self.manager.verify_cancellations([proof], complete=True)
        return proof

    def test_all_immutable_fields_and_missing_field_are_checked(self):
        for key, value in [
            ("mode", "live"),
            ("account_fingerprint", "other"),
            ("order_day", "20261026"),
            ("order_number", "124"),
            ("symbol", "MSFT"),
            ("side", "SELL"),
            ("quantity", 99),
            ("order_type", "MARKET"),
            ("price", "200"),
            ("original_broker_id", "20261027:99"),
        ]:
            with self.subTest(key=key):
                bad = event(self.manager)
                bad[key] = value
                with self.assertRaises(ValueError):
                    self.manager.reconcile(account(), [bad], complete=True)
                self.assertFalse(self.manager.ready)
        missing = event(self.manager)
        missing.pop("order_type")
        with self.assertRaises(ValueError):
            self.manager.reconcile(account(), [missing], complete=True)

    def test_numeric_expressions_are_equivalent(self):
        proof = event(self.manager)
        proof.update(price="100.0000", broker_id="20261027:000123", order_number="000123")
        self.manager.reconcile(account(), [proof], complete=True)
        self.assertTrue(self.manager.ready)

    def test_batch_failure_does_not_apply_first_fill(self):
        self.manager.create("second", "MSFT", "BUY", 1, 200, 195, account()["as_of"])
        self.manager.dispatch("second", Mock(submit=Mock(return_value="20261027:456")))
        first = event(self.manager, filled=1)
        second = {
            **event(self.manager, "MSFT", "BUY", 1, "200"),
            "broker_id": "20261027:456",
            "order_number": "456",
            "notional": "NaN",
        }
        before = copy.deepcopy(self.manager.state)
        with self.assertRaises(Exception):
            self.manager.reconcile(account(), [first, second], complete=True)
        self.assertEqual(before["orders"], self.manager.state["orders"])
        self.assertEqual(before["account"], self.manager.state["account"])

    def test_duplicate_identifier_and_page_overlap_block(self):
        proof = event(self.manager)
        duplicate = {**proof, "broker_id": "20261027:000123"}
        with self.assertRaises(ValueError):
            self.manager.reconcile(account(), [proof, duplicate], complete=True)
        self.assertFalse(self.manager.can_cancel("local"))

    def test_manual_order_blocks_new_but_known_cancel_remains_safe(self):
        own = event(self.manager)
        manual = {**own, "broker_id": "20261027:999", "order_number": "999"}
        with self.assertRaises(ValueError):
            self.manager.reconcile(account(), [own, manual], complete=True)
        self.assertFalse(self.manager.ready)
        self.assertTrue(self.manager.can_cancel("local"))
        self.manager.cancel("local", Mock())

    def test_account_mismatch_never_authorizes_cancel(self):
        proof = event(self.manager)
        proof["account_fingerprint"] = "wrong"
        with self.assertRaises(ValueError):
            self.manager.reconcile(account(), [proof], complete=True)
        self.assertFalse(self.manager.can_cancel("local"))

    def test_missing_page_clears_previous_cancel_proof(self):
        self.proof()
        with self.assertRaises(ValueError):
            self.manager.reconcile(account(), [], complete=False)
        self.assertFalse(self.manager.can_cancel("local"))

    def test_cancel_preflight_rejection_never_leaves_pending(self):
        self.proof()
        adapter = Mock(prepare_cancel=Mock(side_effect=KisPreflightError("not sent")))
        with self.assertRaises(KisPreflightError):
            self.manager.cancel("local", adapter)
        adapter.cancel.assert_not_called()
        self.assertEqual(self.manager.state["orders"]["local"]["status"], "ACCEPTED")
        self.assertEqual(self.manager.state["orders"]["local"]["cancel_status"], "NOT_SENT")

    def test_cancel_explicit_rejection_differs_from_response_loss(self):
        self.proof()
        with self.assertRaises(KisOrderRejected):
            self.manager.cancel(
                "local", Mock(cancel=Mock(side_effect=KisOrderRejected("rejected")))
            )
        self.assertEqual(self.manager.state["orders"]["local"]["cancel_status"], "REJECTED")
        self.proof()
        with self.assertRaises(KisOrderStateUnknown):
            self.manager.cancel(
                "local", Mock(cancel=Mock(side_effect=KisOrderStateUnknown("lost")))
            )
        self.assertEqual(self.manager.state["orders"]["local"]["cancel_status"], "UNKNOWN")
        with self.assertRaises(ValueError):
            self.manager.cancel("local", Mock())

    def test_partial_cancel_uses_remote_remaining_and_restart_requires_recheck(self):
        self.proof(filled=1)
        adapter = Mock()
        self.manager.cancel("local", adapter)
        self.assertEqual(adapter.cancel.call_args.args[0]["cancel_quantity"], 1)
        self.manager.close()
        self.manager = OrderManager(Path(self.temporary.name) / "orders.sqlite")
        self.assertFalse(self.manager.can_cancel("local"))

    def test_known_cancel_child_rejection_recovers_open_status(self):
        self.proof()
        self.manager.cancel("local", Mock(cancel=Mock(return_value="20261027:456")))
        proof = event(self.manager)
        proof["linked_cancellations"] = [{"broker_id": "20261027:456", "status": "REJECTED"}]
        self.manager.reconcile(account(), [proof], complete=True)
        self.assertEqual(self.manager.state["orders"]["local"]["cancel_status"], "REJECTED")
        self.assertEqual(self.manager.state["orders"]["local"]["status"], "ACCEPTED")

    def test_cancel_save_failure_never_calls_adapter(self):
        self.proof()
        adapter = Mock()
        self.manager.connection.execute("PRAGMA query_only=ON")
        with self.assertRaises(Exception):
            self.manager.cancel("local", adapter)
        adapter.cancel.assert_not_called()
        self.assertEqual(self.manager.state["orders"]["local"]["status"], "ACCEPTED")
        self.assertEqual(self.manager.state["orders"]["local"]["cancel_status"], "NOT_SENT")

    def test_auth_preflight_after_persisted_sending_restores_not_sent(self):
        self.proof()
        adapter = Mock(cancel=Mock(side_effect=KisPreflightError("auth failed before HTTP")))
        with self.assertRaises(KisPreflightError):
            self.manager.cancel("local", adapter)
        self.assertEqual(self.manager.state["orders"]["local"]["status"], "ACCEPTED")
        self.assertEqual(self.manager.state["orders"]["local"]["cancel_status"], "NOT_SENT")

    def test_changed_history_never_unlocks_or_authorizes(self):
        from trading.order_contract import context

        row = {
            "ft_ord_qty": "2",
            "ft_ccld_qty": "0",
            "nccs_qty": "2",
            "ft_ccld_amt3": "0",
            "tr_crcy_cd": "USD",
            "prcs_stat_name": "접수",
            "rjct_rson": "",
            "sll_buy_dvsn_cd": "02",
            "ord_dt": "20261027",
            "odno": "123",
            "pdno": "AAPL",
            "ft_ord_unpr3": "100",
            "orgn_odno": "",
            "ord_dvsn": "00",
        }
        changed = {**row, "ft_ccld_qty": "1", "nccs_qty": "1", "ft_ccld_amt3": "100"}
        queries = Mock(
            query_history=Mock(side_effect=[[row], [changed]]),
            query_balances=Mock(return_value=[]),
            query_buying_power=Mock(return_value={}),
        )
        with self.assertRaises(ValueError):
            synchronize(self.manager, queries, {}, "20261027", "20261027", "AAPL", 100)
        self.assertFalse(self.manager.ready)
        self.assertFalse(self.manager.can_cancel("local"))

    def test_remote_and_local_cash_reservations_are_not_counted_twice(self):
        snapshot = account()
        snapshot.update(
            cash="350", broker_reserved_ids=["20261027:123"], remote_reservations_included=True
        )
        self.manager.reconcile(snapshot, [event(self.manager)], complete=True)
        self.manager.create("new", "AAPL", "BUY", 3, 100, 97, account()["as_of"])
        with self.assertRaises(ValueError):
            self.manager.create("extra", "AAPL", "BUY", 1, 100, 97, account()["as_of"])


class LedgerEdges(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.account = PaperAccount(self.folder / "account.json")
        self.account.state["pending_daily"] = []
        self.monitor = Mock(state={"buy_halts": []})

    def test_corrupt_observation_database_is_preserved_and_handle_released(self):
        path = self.folder / "observation-ledger.sqlite"
        original = b"corrupt observation database"
        path.write_bytes(original)
        with self.assertRaises(Exception):
            ObservationJournal(self.folder)
        self.assertEqual(path.read_bytes(), original)
        path.rename(self.folder / "preserved-corrupt.sqlite")

    def snapshot(self, stamp="2026-10-27T14:00:00+00:00", regular=True, quote=True):
        return {
            "now": stamp,
            "market": "US",
            "symbol": "AAPL",
            "regular_session_open": regular,
            "data_mode": "live_observation",
            "quote": {"available_at": stamp, "bid": 100, "ask": 100.1} if quote else None,
        }

    def test_no_normal_observation_means_no_zero_loss_performance(self):
        with ObservationJournal(self.folder) as journal:
            journal.observe(
                self.snapshot(regular=False, quote=False),
                {"action": "WAIT", "reason": "outside_regular_session"},
                self.account,
                self.monitor,
            )
        row = json.loads((self.folder / "daily/US-2026-10-27.json").read_text(encoding="utf-8"))
        self.assertEqual(row["normal_quotes"], 0)
        self.assertIsNone(row["observed_mdd"])
        self.assertIsNone(row["last_valid_valuation"])

    def test_duplicate_observation_and_restart_do_not_double_count(self):
        for _ in range(2):
            with ObservationJournal(self.folder) as journal:
                journal.observe(
                    self.snapshot(),
                    {"action": "WAIT", "reason": "no_daily_plan"},
                    self.account,
                    self.monitor,
                )
        row = json.loads((self.folder / "daily/US-2026-10-27.json").read_text(encoding="utf-8"))
        self.assertEqual(row["normal_quotes"], 1)

    def test_error_and_halt_history_survive_text_log_rotation(self):
        with ObservationJournal(self.folder) as journal:
            journal.observe(
                self.snapshot(quote=False),
                {"action": "WAIT", "reason": "lookup_error"},
                self.account,
                self.monitor,
                lookup_error=True,
            )
            journal.record("control", {"action": "manual_pause"}, "2026-10-27T14:01:00+00:00")
        (self.folder / "decisions.jsonl").write_text("rotated")
        row = json.loads((self.folder / "daily/US-2026-10-27.json").read_text(encoding="utf-8"))
        self.assertEqual(row["lookup_errors"], 1)
        self.assertEqual(row["controls"][0]["action"], "manual_pause")

    def test_authoritative_fill_recovery_does_not_invent_quotes(self):
        self.account.state["trades"] = [
            {
                "at": "2026-10-27T14:00:00+00:00",
                "symbol": "AAPL",
                "action": "BUY",
                "data_mode": "live_observation",
            }
        ]
        with ObservationJournal(self.folder) as journal:
            journal.recover_fills(self.account)
        row = json.loads((self.folder / "daily/US-2026-10-27.json").read_text(encoding="utf-8"))
        self.assertEqual(len(row["fills"]), 1)
        self.assertEqual(row["normal_quotes"], 0)
        self.assertIsNone(row["observed_mdd"])
        self.assertEqual(row["process_events"], 0)

    def test_stale_data_is_not_normal_and_version_plan_evidence_is_kept(self):
        snapshot = self.snapshot()
        snapshot["quote"]["available_at"] = "2026-10-27T13:00:00+00:00"
        with ObservationJournal(self.folder) as journal:
            journal.record(
                "startup",
                {"versions": {"candidate": "fixed"}, "restored_plans": ["one"]},
                snapshot["now"],
            )
            journal.record(
                "plan",
                {
                    "signal_day": "2026-10-26",
                    "plans": [{"id": "one"}],
                    "source_hashes": {"AAPL": "hash"},
                },
                snapshot["now"],
            )
            journal.observe(
                snapshot, {"action": "WAIT", "reason": "stale_quote"}, self.account, self.monitor
            )
        row = json.loads((self.folder / "daily/US-2026-10-27.json").read_text(encoding="utf-8"))
        self.assertEqual(row["stale_quotes"], 1)
        self.assertEqual(row["versions"]["candidate"], "fixed")
        self.assertEqual(row["starts"][0]["restored_plans"], ["one"])
        self.assertIn("one", row["plans"])
