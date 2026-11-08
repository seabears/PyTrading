"""정규장 판정 합성 검사. 모든 원장은 임시 폴더에 만들며 외부 호출은 없다."""
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tools import verify_quote_recovery as verifier


class RegularVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.opening = datetime(2026, 10, 29, 13, 30, tzinfo=timezone.utc)
        self.now = self.opening + timedelta(seconds=730)
        self.events = []
        self.metrics = []
        self.state = {"process_started_at": "2026-10-29T12:26:50+00:00",
                      "buy_halts": ["repeated_collection_errors"], "quote_health": "fresh"}

    def populate(self, *, sparse_second=False):
        for index in range(7):
            at = self.opening + timedelta(seconds=5 + 120 * index)
            for symbol in ("AAPL", "MSFT"):
                if sparse_second and symbol == "MSFT" and index not in {0, 3, 6}:
                    continue
                payload = {"symbol": symbol, "input_kind": "live_observation",
                           "regular_session_open": True, "lookup_error": False,
                           "quote_age_seconds": 1,
                           "quote": {"available_at": (at - timedelta(seconds=1)).isoformat()}}
                self.events.append((str(len(self.events)), "2026-10-29", "observation", at.isoformat(), json.dumps(payload)))
            self.metrics.append({"at": (at + timedelta(seconds=1)).isoformat(), "cycle_seconds": 2})

    def evaluate(self):
        (self.folder / "operations.json").write_text(json.dumps(self.state), encoding="utf-8")
        (self.folder / "cycle-metrics.jsonl").write_text("\n".join(json.dumps(row) for row in self.metrics), encoding="utf-8")
        database = self.folder / "observation-ledger.sqlite"
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,day TEXT,kind TEXT,at TEXT,body TEXT)")
            connection.execute("DELETE FROM events")
            connection.executemany("INSERT INTO events VALUES(?,?,?,?,?)", self.events)
        connection.close()
        with patch.object(verifier, "datetime", wraps=datetime) as clock, patch("app.runtime.load_run_settings", return_value={"symbols": [("US", "AAPL"), ("US", "MSFT")]}):
            clock.now.return_value = self.now
            if getattr(self, "read_completed_at", None):
                clock.now.side_effect = [self.now, self.read_completed_at]
            return verifier.evaluate(self.folder)

    def test_all_symbols_and_cycles_pass_but_orders_remain_blocked(self):
        self.populate()
        result = self.evaluate()
        self.assertTrue(result["regular_recovery_verified"])
        self.assertFalse(result["new_orders_allowed"])
        self.assertEqual(result["complete_regular_cycles"], 7)
        self.assertEqual(result["buy_halts"], ["repeated_collection_errors"])

    def test_three_sparse_samples_cannot_hide_one_symbols_gap(self):
        self.populate(sparse_second=True)
        result = self.evaluate()
        self.assertFalse(result["regular_recovery_verified"])
        self.assertEqual(result["per_symbol"]["MSFT"]["maximum_interval_seconds"], 360)

    def test_off_hours_cycles_do_not_count(self):
        self.populate()
        self.metrics.insert(0, {"at": "2026-10-29T13:00:00+00:00", "cycle_seconds": 1700})
        result = self.evaluate()
        self.assertEqual(len(result["regular_cycles"]), 7)
        self.assertEqual(result["excluded_nonregular_cycles"], 1)
        self.assertEqual(result["regular_cycles"][1]["start_interval_seconds"], 120)

    def test_restarting_cannot_erase_same_day_failure(self):
        self.populate()
        self.state["process_started_at"] = "2026-10-29T13:30:01+00:00"
        error = {"symbol": "AAPL", "input_kind": "live_observation", "regular_session_open": True, "lookup_error": True}
        self.events.insert(0, ("older-error", "2026-10-29", "observation", "2026-10-29T13:30:00+00:00", json.dumps(error)))
        result = self.evaluate()
        self.assertFalse(result["regular_recovery_verified"])
        self.assertIn("day_contains_non_normal_observations", result["diagnostics"])

    def test_missing_cycle_evidence_does_not_invent_full_passes(self):
        self.populate()
        self.metrics = []
        self.assertFalse(self.evaluate()["regular_recovery_verified"])

    def test_ten_minutes_global_span_is_not_each_symbols_span(self):
        self.populate()
        self.events = [row for row in self.events if json.loads(row[4])["symbol"] == "AAPL" or parse(row[3]) >= self.opening + timedelta(seconds=365)]
        self.assertFalse(self.evaluate()["regular_recovery_verified"])

    def test_off_hours_and_forged_age_cannot_pass(self):
        self.populate()
        first = list(self.events[0]);payload = json.loads(first[4]);payload["quote"]["available_at"] = (self.opening - timedelta(seconds=120)).isoformat();first[4] = json.dumps(payload);self.events[0] = tuple(first)
        result = self.evaluate()
        self.assertFalse(result["regular_recovery_verified"])
        self.assertEqual(result["per_symbol"]["AAPL"]["stale_quotes"], 1)
        self.now = self.opening - timedelta(minutes=10)
        self.assertFalse(self.evaluate()["regular_recovery_verified"])



    def test_row_committed_during_snapshot_read_is_not_a_future_clock_error(self):
        self.populate()
        at=self.now+timedelta(milliseconds=10)
        payload={"symbol":"AAPL","input_kind":"live_observation","regular_session_open":True,
                 "lookup_error":False,"quote_age_seconds":1,
                 "quote":{"available_at":(at-timedelta(seconds=1)).isoformat()}}
        self.events.append(("concurrent-row","2026-10-29","observation",at.isoformat(),json.dumps(payload)))
        self.read_completed_at=self.now+timedelta(milliseconds=50)
        result=self.evaluate()
        self.assertNotIn("future_observation",result["diagnostics"])
        self.assertTrue(result["regular_recovery_verified"])


def parse(value):
    return datetime.fromisoformat(value)
