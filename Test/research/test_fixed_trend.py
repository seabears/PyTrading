"""고정 후보 검토 기준과 실제 모의 관측 집계를 검증한다."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.fixed_trend_study import audit_forward, review_gate


class FixedTrendTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"minimum_forward_sessions": 20, "minimum_closed_trades_for_review": 30,
                       "maximum_review_drawdown": .08}

    def test_three_positive_days_do_not_pass(self):
        result = review_gate({"trades": 30, "net_return": .01, "max_drawdown": .01}, 3, self.policy)
        self.assertFalse(result["review_eligible"])

    def test_no_closed_trades_do_not_pass(self):
        result = review_gate({"trades": 0, "net_return": .01, "max_drawdown": 0}, 20, self.policy)
        self.assertFalse(result["review_eligible"])

    def test_eligible_does_not_approve_live_trading(self):
        result = review_gate({"trades": 30, "net_return": .01, "max_drawdown": .08}, 20, self.policy)
        self.assertTrue(result["review_eligible"])
        self.assertFalse(result["live_approved"])

    def test_loss_or_excess_drawdown_fails(self):
        for returns, drawdown in ((-.01, .01), (.1, .09)):
            result = review_gate({"trades": 40, "net_return": returns, "max_drawdown": drawdown}, 30, self.policy)
            self.assertFalse(result["review_eligible"])

    def test_no_record_is_not_evidence_of_performance(self):
        with TemporaryDirectory() as directory:
            result = audit_forward(Path(directory))
            self.assertEqual(result["observations"], 0)
            self.assertFalse(result["continuous_running_proven"])
            self.assertTrue(result["no_records_is_not_zero_loss_proof"])

    def test_malformed_record_is_counted_and_valid_record_kept(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            row = {"snapshot": {"now": "2026-10-25T14:00:00+00:00", "regular_session_open": False},
                   "decision": {"action": "WAIT", "reason": "outside_regular_session"}}
            (folder / "decisions.jsonl").write_text(json.dumps(row) + "\nbroken\n", encoding="utf-8")
            result = audit_forward(folder)
            self.assertEqual(result["observations"], 1)
            self.assertEqual(result["invalid_rows"], 1)
            self.assertEqual(result["regular_session_observations"], 0)
            self.assertEqual(result["fills"], 0)
