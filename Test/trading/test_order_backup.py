"""실제 SQLite WAL·파일 교체 실패를 격리 폴더에서 검사한다. 증권사 호출은 없다."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch, Mock

from trading.orders import OrderManager
from trading.order_backup import backup_orders, restore_orders, inspect_database
from Test.trading.risk_fixtures import seed_risk, snapshot


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.source = self.folder / "source.sqlite"
        self.bundle = self.folder / "backup"
        self.manager = OrderManager(self.source, "kis_demo", "demo")
        self.addCleanup(self.manager.close)
        proof = seed_risk(self.manager, source_kind="kis_vps")
        self.manager.reconcile(snapshot(proof), [], complete=True)

    def restore(self, **changes):
        arguments = {
            "bundle": self.bundle,
            "destination": self.folder / "restored.sqlite",
            "mode": "kis_demo",
            "alias": "demo",
            "fingerprint": self.manager.state["broker_identity"],
        }
        arguments.update(changes)
        return restore_orders(**arguments)

    def test_online_wal_backup_contains_same_risk_checkpoint(self):
        self.manager.state["note"] = "latest-committed"
        self.manager._save()
        manifest = backup_orders(self.source, self.bundle)
        saved = inspect_database(self.bundle / "orders.sqlite")
        self.assertEqual(saved["note"], "latest-committed")
        self.assertEqual(
            manifest["risk_checkpoint"], saved["risk_ledger"]["last_evaluation"]["checkpoint_hash"]
        )
        self.assertEqual(saved["risk_ledger"], self.manager.state["risk_ledger"])

    def test_partial_creation_failure_is_not_registered(self):
        with patch("trading.order_backup.os.replace", side_effect=OSError("storage fault")):
            with self.assertRaises(OSError):
                backup_orders(self.source, self.bundle)
        self.assertFalse(self.bundle.exists())
        self.assertTrue(list(self.folder.glob(".partial-*")))
        self.assertEqual(inspect_database(self.source)["mode"], "kis_demo")

    def test_restore_requires_new_path_and_preserves_original(self):
        backup_orders(self.source, self.bundle)
        before = self.source.read_bytes()
        with self.assertRaises(ValueError):
            self.restore(destination=self.source)
        self.assertEqual(before, self.source.read_bytes())

    def test_other_account_alias_mode_and_corrupt_hash_rejected(self):
        backup_orders(self.source, self.bundle)
        for fields in ({"fingerprint": "other"}, {"alias": "other"}, {"mode": "live"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.restore(**fields)
        path = self.bundle / "orders.sqlite"
        path.write_bytes(path.read_bytes() + b"corrupt")
        with self.assertRaises(ValueError):
            self.restore()

    def test_intent_response_loss_and_cancel_pending_are_quarantined(self):
        self.manager.create(
            "intent", "AAPL", "BUY", 1, "100", "97", self.manager.state["account"]["as_of"]
        )
        self.manager.state["orders"]["sending"] = {
            **self.manager.state["orders"]["intent"],
            "id": "sending",
            "status": "SENDING",
        }
        self.manager.state["orders"]["partial"] = {
            **self.manager.state["orders"]["intent"],
            "id": "partial",
            "status": "CANCEL_PENDING",
            "filled": 0,
            "cancel_status": "SENDING",
            "broker_id": "20261028:1",
        }
        self.manager._save()
        backup_orders(self.source, self.bundle)
        gate = self.restore()
        restored = OrderManager(self.folder / "restored.sqlite", "kis_demo", "demo")
        try:
            self.assertFalse(restored.ready)
            self.assertEqual(restored.state["orders"]["intent"]["status"], "UNKNOWN")
            self.assertEqual(restored.state["orders"]["sending"]["status"], "UNKNOWN")
            self.assertEqual(restored.state["orders"]["partial"]["cancel_status"], "UNKNOWN")
            adapter = Mock()
            with self.assertRaises(ValueError):
                restored.dispatch("intent", adapter)
            adapter.submit.assert_not_called()
            self.assertEqual(gate["status"], "remote_reconciliation_required")
        finally:
            restored.close()

    def test_restore_interruption_never_replaces_original_or_publishes_destination(self):
        backup_orders(self.source, self.bundle)
        with patch("trading.order_backup.os.replace", side_effect=OSError("process exit")):
            with self.assertRaises(OSError):
                self.restore()
        self.assertFalse((self.folder / "restored.sqlite").exists())
        self.assertTrue(list(self.folder.glob(".restore-partial-*")))
        self.assertTrue(self.source.exists())

    def test_old_backup_gate_not_cleared_by_snapshot_boolean(self):
        backup_orders(self.source, self.bundle)
        self.restore()
        restored = OrderManager(self.folder / "restored.sqlite", "kis_demo", "demo")
        try:
            old = self.manager.state["account"]
            with self.assertRaises(ValueError):
                restored.reconcile(old, [], complete=True)
            self.assertFalse(restored.ready)
            self.assertIn("restore_gate", restored.state)
        finally:
            restored.close()
