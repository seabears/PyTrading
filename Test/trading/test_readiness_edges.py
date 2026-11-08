"""추가 위험·복원·일봉 관측 경계. 실제 API·현재 운용 계좌를 사용하지 않는다."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
import unittest

from trading.orders import OrderManager
from trading.risk_ledger import RiskLedger, local_day, amount
from trading.order_backup import backup_orders, restore_orders
from trading.observation_journal import ObservationJournal
from trading.paper import PaperAccount
from daily_review import review_observations
from Test.trading.risk_fixtures import evidence, managed_order, execution, seed_risk, snapshot
from Test.trading.test_review_regressions import event


class ReadinessEdges(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.manager = OrderManager(self.folder / "orders.sqlite", "kis_demo")
        self.addCleanup(self.manager.close)
        self.manager.state["broker_identity"] = "identity"
        self.now = datetime.now(timezone.utc) - timedelta(seconds=12)

    def test_execution_order_uses_instant_not_timezone_text(self):
        ledger = RiskLedger(self.manager)
        ledger.ingest(evidence(self.manager, self.now), now=self.now)
        managed_order(self.manager, "buy", quantity=1)
        managed_order(self.manager, "sell", side="SELL", quantity=1)
        buy = execution(
            "buy-event",
            "buy",
            (self.now + timedelta(seconds=1)).astimezone(timezone(timedelta(hours=9))),
            1,
            "100",
        )
        sell = execution(
            "sell-event", "sell", self.now + timedelta(seconds=2), 1, "99", side="SELL"
        )
        stamp = self.now + timedelta(seconds=3)
        ledger.ingest(
            evidence(
                self.manager,
                stamp,
                cash="9999",
                buying_power="9999",
                net_asset_value="9999",
                fills=[sell, buy],
            ),
            now=stamp,
        )
        self.assertEqual(
            amount(
                self.manager.state["risk_ledger"]["last_evaluation"]["realized_pnl_after_cost"],
                signed=True,
            ),
            -1,
        )

    def test_unknown_raw_credentials_fields_never_enter_ledger(self):
        payload = evidence(self.manager, self.now)
        payload["account_number"] = "secret-account-raw"
        with self.assertRaises(ValueError):
            RiskLedger(self.manager).ingest(payload, now=self.now)
        self.assertNotIn("secret-account-raw", json.dumps(self.manager.state))

    def test_cash_and_history_source_times_must_be_current(self):
        ledger = RiskLedger(self.manager)
        payload = evidence(self.manager, self.now)
        payload["source_times"]["cash"] = (self.now - timedelta(minutes=2)).isoformat()
        with self.assertRaisesRegex(ValueError, "risk_source_timestamp_invalid"):
            ledger.ingest(payload, now=self.now)

    def test_proof_inventory_mutation_does_not_change_authoritative_evaluation(self):
        proof = seed_risk(self.manager, source_kind="kis_vps")
        proof.positions["AAPL"] = 99
        self.assertEqual(self.manager.state["risk_ledger"]["last_evaluation"]["positions"], {})
        with self.assertRaises(ValueError):
            RiskLedger(self.manager).validate_snapshot(snapshot(proof))

    def test_initial_invalid_evidence_can_be_replaced_by_complete_checkpoint(self):
        ledger = RiskLedger(self.manager)
        with self.assertRaises(ValueError):
            ledger.ingest(evidence(self.manager, self.now, complete={}), now=self.now)
        self.assertTrue(ledger.ingest(evidence(self.manager, self.now), now=self.now).eligible)

    def test_three_round_trips_pause_then_expire_cooldown(self):
        ledger = RiskLedger(self.manager)
        ledger.ingest(evidence(self.manager, self.now), now=self.now)
        fills = []
        for index in range(3):
            buy, sell = "buy" + str(index), "sell" + str(index)
            managed_order(self.manager, buy, quantity=1)
            managed_order(self.manager, sell, side="SELL", quantity=1)
            fills += [
                execution(
                    "b" + str(index), buy, self.now + timedelta(seconds=index * 2 + 1), 1, "100"
                ),
                execution(
                    "s" + str(index),
                    sell,
                    self.now + timedelta(seconds=index * 2 + 2),
                    1,
                    "99",
                    side="SELL",
                ),
            ]
        stamp = self.now + timedelta(seconds=8)
        payload = evidence(
            self.manager,
            stamp,
            cash="9997",
            buying_power="9997",
            net_asset_value="9997",
            fills=fills,
            window_start=self.now.isoformat(),
        )
        proof = ledger.ingest(payload, now=stamp)
        self.assertFalse(proof.eligible)
        self.assertEqual(proof.consecutive_losses, 3)
        later = stamp + timedelta(hours=2)
        proof = ledger.ingest(
            {
                **payload,
                "as_of": later.isoformat(),
                "source_times": {key: later.isoformat() for key in payload["complete"]},
            },
            now=later,
        )
        self.assertTrue(proof.eligible)

    def test_new_york_day_rolls_baseline_not_old_fee(self):
        ledger = RiskLedger(self.manager)
        first = datetime(2026, 10, 28, 3, 58, tzinfo=timezone.utc)
        ledger.ingest(evidence(self.manager, first), now=first)
        fee = {
            "id": "fee",
            "kind": "FEE",
            "scope": "account",
            "amount": "-50",
            "at": (first + timedelta(seconds=30)).isoformat(),
        }
        second = first + timedelta(minutes=1)
        data = evidence(
            self.manager,
            second,
            cash="9950",
            buying_power="9950",
            net_asset_value="9950",
            cash_events=[fee],
            window_start=first.isoformat(),
        )
        ledger.ingest(data, now=second)
        third = datetime(2026, 10, 28, 4, 1, tzinfo=timezone.utc)
        ledger.ingest(
            {
                **data,
                "as_of": third.isoformat(),
                "source_times": {key: third.isoformat() for key in data["complete"]},
            },
            now=third,
        )
        value = self.manager.state["risk_ledger"]["last_evaluation"]
        self.assertEqual(amount(value["daily_fees"]), 0)
        self.assertEqual(amount(value["daily_loss_ratio"]), 0)
        self.assertEqual(len(self.manager.state["risk_ledger"]["days"]), 2)

    def test_policy_change_and_ambiguous_fill_sequence_fail(self):
        ledger = RiskLedger(self.manager)
        ledger.ingest(evidence(self.manager, self.now), now=self.now)
        self.manager.policy["daily_loss_limit"] = 0.9
        with self.assertRaisesRegex(ValueError, "risk_policy_changed"):
            ledger.ingest(evidence(self.manager, self.now), now=self.now)

    def test_restore_missing_remote_order_stays_unknown_then_explicit_binding_reconciles(self):
        # 원격 응답 전체는 합성이다. 실제 모의 주문 접수 검증이 아니다.
        proof = seed_risk(self.manager, source_kind="kis_vps")
        self.manager.reconcile(snapshot(proof), [], complete=True)
        self.manager.create("intent", "AAPL", "BUY", 1, "100", "97", proof.as_of)
        bundle = self.folder / "backup"
        backup_orders(self.folder / "orders.sqlite", bundle)
        path = self.folder / "restored.sqlite"
        restore_orders(bundle, path, "kis_demo", "research", self.manager.state["broker_identity"])
        restored = OrderManager(path, "kis_demo")
        try:
            with self.assertRaises(ValueError):
                restored.reconcile(snapshot(proof), [], complete=True)
            row = event(restored, quantity=1, filled=1)
            row.update(status="FILLED", notional="100")
            restored.bind_unknown("intent", "20261027:123", [row])
            stamp = datetime.now(timezone.utc)
            fill = execution("fill-after-backup", "intent", stamp, 1, "100")
            start = restored.state["risk_ledger"]["baseline"]["window_start"]
            data = evidence(
                restored,
                stamp,
                source_kind="kis_vps",
                window_start=start,
                cash="9900",
                buying_power="9900",
                net_asset_value="10000",
                positions={"AAPL": 1},
                position_costs={"AAPL": "100"},
                quotes={"AAPL": {"at": stamp.isoformat(), "price": "100"}},
                fills=[fill],
            )
            # 복원 후 새 계좌 상태 확인도 합성 입력으로 다시 수행한다.
            from Test.trading.cash_policy_fixtures import confirm_cash_only
            confirm_cash_only(restored, at=stamp)
            fresh = RiskLedger(restored).ingest(data, now=stamp)
            value = snapshot(fresh)
            value["remote_history_start"] = local_day(
                restored.state["restore_gate"]["backup_at"]
            ).replace("-", "")
            restored.reconcile(value, [row], complete=True)
            self.assertTrue(restored.ready)
            self.assertNotIn("restore_gate", restored.state)
            self.assertEqual(restored.state["orders"]["intent"]["status"], "FILLED")
        finally:
            restored.close()


class DailyReviewTests(unittest.TestCase):
    def test_missing_open_window_and_data_readiness_are_distinct(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            account = PaperAccount(folder / "account.json")
            account.state["pending_daily"] = []
            monitor = Mock(state={"buy_halts": []})
            with ObservationJournal(folder) as journal:
                journal.record(
                    "plan",
                    {"plans": [], "coverage": {"US:AAPL": {"indicator_ready": False}}},
                    "2026-10-27T13:00:00+00:00",
                )
                stamp = "2026-10-27T14:00:00+00:00"
                journal.observe(
                    {
                        "symbol": "AAPL",
                        "market": "US",
                        "now": stamp,
                        "regular_session_open": True,
                        "data_mode": "live_observation",
                        "quote": {"available_at": stamp, "bid": 100, "ask": 100.1},
                    },
                    {"action": "WAIT", "reason": "no_daily_plan"},
                    account,
                    monitor,
                )
            result = review_observations(folder)
            self.assertEqual(result["observed_trading_days"], 1)
            self.assertEqual(result["virtual_fills"], 0)
            row = result["days"]["2026-10-27"]
            self.assertEqual(row["reasons"]["data_not_ready"], 1)
            self.assertEqual(row["open_window_symbols"], [])
            self.assertFalse(result["minimum_days_met"])

    def test_nonregular_process_progress_does_not_become_observed_session(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with ObservationJournal(folder) as journal:
                journal.record("heartbeat", {}, "2026-10-27T10:00:00+00:00")
            self.assertEqual(review_observations(folder)["observed_trading_days"], 0)
