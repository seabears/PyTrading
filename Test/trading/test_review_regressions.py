"""검토에서 발견된 두 사례. 실제 인증·주문 없이 임시 SQLite에서 재현한다."""

import copy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from trading.orders import OrderManager
from trading.reconciliation import synchronize
from broker.managed_kis import ManagedKisAdapter
from broker.kis_api.client import KisApiClient, ApiResponse


def account():
    return {
        "cash": "10000",
        "positions": {"AAPL": 5},
        "position_costs": {"AAPL": "500"},
        "initial": "10000",
        "exposure": "500",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "daily_loss_ratio": 0,
        "consecutive_losses": 0,
        "last_loss_at": None,
    }


def event(manager, symbol="AAPL", side="BUY", quantity=2, price="100", filled=0):
    return {
        "broker_id": "20261027:123",
        "event_id": "event",
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "filled": filled,
        "notional": str(filled * 100),
        "status": "PARTIAL" if filled else "ACCEPTED",
        "order_type": "LIMIT",
        "original_broker_id": None,
        "order_day": "20261027",
        "order_number": "123",
        "account_fingerprint": manager.state.get("broker_identity", "internal:research"),
        "mode": manager.state["mode"],
    }


class ReviewRegressions(unittest.TestCase):
    def test_same_number_other_order_rejected_without_partial_changes(self):
        with TemporaryDirectory() as temporary:
            manager = OrderManager(Path(temporary) / "journal.sqlite")
            try:
                manager.reconcile(account(), [], complete=True)
                manager.create("local", "AAPL", "BUY", 2, 100, 97, account()["as_of"])
                manager.dispatch("local", Mock(submit=Mock(return_value="20261027:123")))
                before = copy.deepcopy(manager.state)
                with self.assertRaises(ValueError):
                    manager.reconcile(
                        account(), [event(manager, "MSFT", "SELL", 99, "200")], complete=True
                    )
                self.assertFalse(manager.ready)
                self.assertEqual(before["orders"], manager.state["orders"])
                self.assertEqual(before["account"], manager.state["account"])
            finally:
                manager.close()

    def test_known_reserved_sell_reconciles_and_can_cancel(self):
        with TemporaryDirectory() as temporary:
            manager = OrderManager(Path(temporary) / "journal.sqlite", "kis_demo")
            try:
                manager.reconcile(account(), [], complete=True)
                api = KisApiClient(
                    Mock(
                        environment="vps",
                        app_key="fake",
                        app_secret="fake",
                        access_token="fake",
                        request_interval=0.6,
                        next_request_at=0,
                    ),
                    allow_trading=True,
                )
                adapter = ManagedKisAdapter(
                    api, manager, "00000000", "01", {"AAPL": "NASD"}, enabled=True
                )
                manager.create("local", "AAPL", "SELL", 2, 100, 97, account()["as_of"])
                manager.dispatch("local", Mock(submit=Mock(return_value="20261027:123")))
                from Test.trading.risk_fixtures import seed_risk
                risk = seed_risk(manager, {'AAPL': 5})
                balance = [
                    {
                        "ovrs_pdno": "AAPL",
                        "ovrs_cblc_qty": "5",
                        "ord_psbl_qty": "3",
                        "tr_crcy_cd": "USD",
                        "frcr_pchs_amt1": "500",
                    }
                ]
                capacity = {
                    "output": {
                        "tr_crcy_cd": "USD",
                        "ord_psbl_frcr_amt": "10000",
                        "ovrs_ord_psbl_amt": "10000",
                    }
                }
                row = {
                    "ft_ord_qty": "2",
                    "ft_ccld_qty": "0",
                    "nccs_qty": "2",
                    "ft_ccld_amt3": "0",
                    "tr_crcy_cd": "USD",
                    "prcs_stat_name": "",
                    "rjct_rson": "",
                    "sll_buy_dvsn_cd": "01",
                    "ord_dt": "20261027",
                    "odno": "000123",
                    "pdno": "AAPL",
                    "ft_ord_unpr3": "100.0000",
                    "orgn_odno": "",
                    "ord_dvsn": "00",
                }
                queries = Mock(
                    query_history=Mock(return_value=[row]),
                    query_balances=Mock(return_value=balance),
                    query_buying_power=Mock(return_value=capacity),
                )
                synchronize(manager, queries, risk, "20261027", "20261027", "AAPL", 100)
                manager.create("local-unsent", "AAPL", "SELL", 3, 100, 97, account()["as_of"])
                with self.assertRaises(ValueError):
                    manager.create("excess", "AAPL", "SELL", 1, 100, 97, account()["as_of"])
                with patch.object(
                    api,
                    "_http",
                    return_value=ApiResponse({"rt_cd": "0", "output": {"ODNO": "456"}}),
                ) as http:
                    manager.cancel("local", adapter)
                    self.assertEqual(http.call_count, 1)
                self.assertEqual(manager.state["orders"]["local"]["status"], "CANCEL_PENDING")
            finally:
                manager.close()
