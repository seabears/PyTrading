"""합성 원본 근거로 자금·부분 체결·현지 날짜·중복·재시작을 검사한다. 외부 호출 없음."""

import copy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from trading.orders import OrderManager
from trading.risk_ledger import RiskLedger, amount, local_day
from Test.trading.risk_fixtures import evidence, managed_order, execution, snapshot


class RiskLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "orders.sqlite"
        self.manager = OrderManager(self.path, "kis_demo")
        self.addCleanup(lambda: self.manager.close())
        self.manager.state["broker_identity"] = "test-identity"
        self.now = datetime.now(timezone.utc) - timedelta(seconds=10)
        self.ledger = RiskLedger(self.manager)
        self.ledger.ingest(evidence(self.manager, self.now), now=self.now)

    def advance(self, seconds=2, **changes):
        stamp = self.now + timedelta(seconds=seconds)
        return self.ledger.ingest(
            evidence(self.manager, stamp, window_start=self.now.isoformat(), **changes), now=stamp
        )

    def evaluation(self):
        return self.manager.state["risk_ledger"]["last_evaluation"]

    def test_initial_cash_capacity_and_nav_are_distinct(self):
        proof = self.advance(buying_power="9000")
        value = self.evaluation()
        self.assertEqual(amount(value["initial"]), 10000)
        self.assertEqual(amount(value["cash_balance"]), 10000)
        self.assertEqual(amount(value["buying_power"]), 9000)
        self.assertEqual(amount(value["net_asset_value"]), 10000)
        self.assertTrue(proof.eligible)

    def test_deposit_withdrawal_dividend_fee_are_not_trade_profit(self):
        stamp = self.now + timedelta(seconds=1)
        events = [
            {"id": str(index), "at": stamp.isoformat(), "kind": kind, "amount": value}
            for index, (kind, value) in enumerate(
                [("DEPOSIT", "1000"), ("WITHDRAWAL", "-200"), ("DIVIDEND", "10"), ("FEE", "-1")]
            )
        ]
        self.advance(
            cash="10809", buying_power="10809", net_asset_value="10809", cash_events=events
        )
        value = self.evaluation()
        self.assertEqual(amount(value["external_flow"], signed=True), 800)
        self.assertEqual(amount(value["realized_pnl_after_cost"], signed=True), 0)
        self.assertEqual(amount(value["dividend_income"], signed=True), 10)
        self.assertEqual(
            amount(
                self.manager.state["risk_ledger"]["days"][local_day(stamp.isoformat())][
                    "adjusted_pnl"
                ],
                signed=True,
            ),
            9,
        )

    def test_partial_sell_is_one_round_trip_only_on_flat(self):
        managed_order(self.manager, "buy")
        managed_order(self.manager, "sell", side="SELL")
        first = execution("b", "buy", self.now + timedelta(seconds=1), 2, "200", "2")
        second = execution("s1", "sell", self.now + timedelta(seconds=2), 1, "90", "1", side="SELL")
        stamp = self.now + timedelta(seconds=3)
        self.advance(
            3,
            cash="9887",
            buying_power="9887",
            net_asset_value="9987",
            positions={"AAPL": 1},
            position_costs={"AAPL": "101"},
            quotes={"AAPL": {"at": stamp.isoformat(), "price": "100"}},
            fills=[first, second],
        )
        self.assertEqual(self.evaluation()["closed_trades"], [])
        self.assertEqual(amount(self.evaluation()["realized_pnl_after_cost"], signed=True), -12)
        last = execution("s2", "sell", self.now + timedelta(seconds=4), 1, "95", "1", side="SELL")
        self.advance(
            5, cash="9981", buying_power="9981", net_asset_value="9981", fills=[first, second, last]
        )
        self.assertEqual(len(self.evaluation()["closed_trades"]), 1)
        self.assertEqual(amount(self.evaluation()["closed_trades"][0]["pnl"], signed=True), -19)
        self.assertEqual(self.evaluation()["consecutive_losses"], 1)

    def test_duplicate_replay_after_restart_does_not_add_profit(self):
        managed_order(self.manager, "buy", quantity=1)
        managed_order(self.manager, "sell", side="SELL", quantity=1)
        fills = [
            execution("b", "buy", self.now + timedelta(seconds=1), 1, "100"),
            execution("s", "sell", self.now + timedelta(seconds=2), 1, "99", side="SELL"),
        ]
        self.advance(3, cash="9999", buying_power="9999", net_asset_value="9999", fills=fills)
        self.manager.close()
        self.manager = OrderManager(self.path, "kis_demo")
        self.ledger = RiskLedger(self.manager)
        self.advance(4, cash="9999", buying_power="9999", net_asset_value="9999", fills=fills)
        self.assertEqual(self.evaluation()["consecutive_losses"], 1)
        self.assertEqual(len(self.manager.state["risk_ledger"]["fills"]), 2)

    def test_cash_change_without_event_blocks(self):
        proof = self.advance(cash="11000", buying_power="11000", net_asset_value="11000")
        self.assertFalse(proof.eligible)
        self.assertIn("unexplained_cash_movement", self.evaluation()["issues"])

    def test_manual_fill_rejected(self):
        fill = execution("manual", "not-managed", self.now + timedelta(seconds=1), 1, "100")
        with self.assertRaisesRegex(ValueError, "manual_or_unmatched"):
            self.advance(fills=[fill])
        self.assertFalse(self.manager.ready)
        with self.assertRaises(ValueError):
            self.ledger.context(now=self.now)

    def test_unknown_fee_prevents_qualification(self):
        managed_order(self.manager, "buy", quantity=1)
        fill = execution("b", "buy", self.now + timedelta(seconds=1), 1, "100")
        fill["fees_final"] = False
        with self.assertRaisesRegex(ValueError, "execution_cost_unknown"):
            self.advance(fills=[fill])

    def test_initial_holdings_are_not_invented_basis(self):
        other = OrderManager(Path(self.temporary.name) / "legacy.sqlite", "kis_demo")
        try:
            other.state["broker_identity"] = "legacy"
            proof = RiskLedger(other).ingest(
                evidence(
                    other,
                    self.now,
                    positions={"AAPL": 5},
                    position_costs={"AAPL": "500"},
                    net_asset_value="10500",
                    quotes={"AAPL": {"at": self.now.isoformat(), "price": "100"}},
                ),
                now=self.now,
            )
            self.assertFalse(proof.eligible)
            self.assertIn(
                "initial_history_or_holdings_require_review",
                other.state["risk_ledger"]["last_evaluation"]["issues"],
            )
        finally:
            other.close()

    def test_missing_complete_scope_stale_and_wrong_account_block(self):
        original = evidence(self.manager, self.now)
        for change in (
            {"account_fingerprint": "other"},
            {"complete": {}},
            {"source_hashes": {}},
            {"as_of": (self.now - timedelta(minutes=5)).isoformat()},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.ledger.ingest({**original, **change}, now=self.now)

    def test_stale_position_price_is_not_current_valuation(self):
        managed_order(self.manager, "buy", quantity=1)
        fill = execution("b", "buy", self.now + timedelta(seconds=1), 1, "100")
        with self.assertRaisesRegex(ValueError, "risk_valuation_stale"):
            self.advance(
                cash="9900",
                buying_power="9900",
                net_asset_value="10000",
                positions={"AAPL": 1},
                position_costs={"AAPL": "100"},
                fills=[fill],
                quotes={
                    "AAPL": {"at": (self.now - timedelta(minutes=2)).isoformat(), "price": "100"}
                },
            )

    def test_event_revision_and_missing_history_block(self):
        event = {
            "id": "deposit",
            "at": (self.now + timedelta(seconds=1)).isoformat(),
            "kind": "DEPOSIT",
            "amount": "100",
        }
        self.advance(
            cash="10100", buying_power="10100", net_asset_value="10100", cash_events=[event]
        )
        with self.assertRaisesRegex(ValueError, "risk_event_revision"):
            self.advance(3, cash_events=[{**event, "amount": "200"}])
        with self.assertRaisesRegex(ValueError, "risk_history_event_missing"):
            self.advance(4)

    def test_daily_halt_survives_recovery_and_restart(self):
        managed_order(self.manager, "buy", quantity=1)
        fill = execution("b", "buy", self.now + timedelta(seconds=1), 1, "100")
        # 배당이 아니라 독립 비용 손실. 회복 입금은 손익 회복으로 계산하지 않는다.
        events = [
            {
                "id": "fee",
                "kind": "FEE",
                "amount": "-300",
                "at": (self.now + timedelta(seconds=1)).isoformat(),
            }
        ]
        self.advance(
            cash="9600",
            buying_power="9600",
            net_asset_value="9700",
            positions={"AAPL": 1},
            position_costs={"AAPL": "100"},
            fills=[fill],
            cash_events=events,
            quotes={"AAPL": {"at": (self.now + timedelta(seconds=2)).isoformat(), "price": "100"}},
        )
        self.assertTrue(self.evaluation()["day_halted"])
        self.manager.close()
        self.manager = OrderManager(self.path, "kis_demo")
        self.ledger = RiskLedger(self.manager)
        self.assertFalse(self.ledger.context(now=self.now + timedelta(seconds=3)).eligible)

    def test_local_day_transition_uses_new_york_not_utc(self):
        self.assertEqual(local_day("2026-10-28T03:59:00+00:00"), "2026-10-27")
        self.assertEqual(local_day("2026-10-28T04:01:00+00:00"), "2026-10-28")
        self.assertEqual(local_day("2026-11-02T04:30:00+00:00"), "2026-11-01")

    def test_context_cannot_authorize_changed_snapshot_or_expired_data(self):
        proof = self.advance()
        value = snapshot(proof)
        value["cash"] = "999999"
        with self.assertRaises(ValueError):
            self.ledger.validate_snapshot(value)
        with self.assertRaises(ValueError):
            self.ledger.context(now=self.now + timedelta(minutes=1))

    def test_decimal_precision_rejects_float_nan(self):
        self.assertEqual(str(amount("0.1234565")), "0.123456")
        for value in (0.1, "NaN", "Infinity"):
            with self.assertRaises(ValueError):
                amount(value)

    def test_manual_verified_dict_is_not_proof(self):
        from trading.reconciliation import normalize_snapshot

        with self.assertRaises(ValueError):
            normalize_snapshot([], {}, {"verified": True, "initial": "10000"})
