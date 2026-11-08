"""실전 차단과 공식 응답 정상화·통신 복구 경계를 합성 응답으로 검증한다."""
import copy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest
from unittest.mock import Mock, patch

from broker.kis import KisApiError, KisAuthenticationExpired, KisMarketClient
from broker.kis_api import overseas_stock, ApiResponse, KisApiClient
from broker.managed_kis import ManagedKisAdapter
from trading.reconciliation import normalize_orders, normalize_snapshot
from trading.orders import OrderManager


class GuardTests(unittest.TestCase):
    def request(self, environment="real"):
        return overseas_stock.order("fake-account", "01", "NASD", "AAPL", "1", "100.00", "buy", "", "", "0", "00", env_dv=environment)

    def test_cancel_request_failure_is_not_a_transmission(self):
        from broker.kis_api.client import KisPreflightError
        adapter = object.__new__(ManagedKisAdapter)
        adapter.api = Mock()
        with patch.object(adapter, '_cancel_request', side_effect=ValueError('binding changed')):
            with self.assertRaises(KisPreflightError):
                adapter.cancel({'id': 'one'})
        adapter.api.execute_managed.assert_not_called()

    def test_history_repeated_or_missing_cursor_never_returns_complete(self):
        adapter = object.__new__(ManagedKisAdapter)
        adapter.account_number, adapter.product_code = 'synthetic', '01'
        adapter.api = Mock()
        with patch.object(adapter, '_guard'):
            for payload in ({'ctx_area_nk200': ''}, {'ctx_area_fk200': 'same', 'ctx_area_nk200': 'same'}):
                response = Mock(has_more=True, payload=payload)
                response.rows.return_value = []
                adapter.api.execute.return_value = response
                with self.assertRaises(ValueError):
                    adapter.query_history('20261026', '20261027')

    def test_same_alias_cannot_bind_different_broker_account(self):
        with TemporaryDirectory() as directory:
            manager = OrderManager(Path(directory) / "demo.sqlite", "kis_demo")
            try:
                api = Mock(market_client=Mock(environment="vps", app_key="fake"))
                ManagedKisAdapter(api, manager, "00000000", "01", {})
                with self.assertRaises(ValueError):
                    ManagedKisAdapter(api, manager, "00000001", "01", {})
            finally:
                manager.close()

    def test_wrong_account_managed_request_is_rejected_before_http(self):
        market = Mock(environment="vps", app_key="fake", request_interval=.6)
        api = KisApiClient(market, allow_trading=True)
        manager = Mock(ready=True)
        manager.state = {"mode": "kis_demo", "broker_identity": "wrong-account-hash", "orders": {"one": {"status": "SENDING", "id": "one", "symbol": "AAPL", "quantity": 1}}}
        with patch.object(api, "_http") as http:
            with self.assertRaises(KisApiError):
                api.execute_managed(self.request("demo"), manager, "one")
            http.assert_not_called()

    def test_bad_legacy_token_shape_does_not_prevent_new_authentication(self):
        from broker.kis_setup import create_kis_client
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "cache/kis/token.json"
            path.parent.mkdir(parents=True)
            path.write_text("[]")
            with patch("broker.kis_setup.DATA_ROOT", folder), patch("broker.kis_setup.read_credentials_file", return_value=("fake", "secret")):
                client = create_kis_client(folder / "fake.env", {"environment": "prod"})
            self.assertEqual(client.access_token, "")
            self.assertEqual(path.read_text(), "[]")

    def test_prod_flag_does_not_authorize_order(self):
        market = Mock(environment="prod", request_interval=.2)
        api = KisApiClient(market, allow_trading=True)
        with self.assertRaises(KisApiError):
            api.execute(self.request())
        market.authenticate.assert_not_called()

    def test_low_level_trading_post_cannot_bypass_gate(self):
        market = Mock(environment="prod", request_interval=.2)
        api = KisApiClient(market, allow_trading=True)
        with patch("urllib.request.urlopen") as connection:
            with self.assertRaises(KisApiError):
                api._http("/uapi/overseas-stock/v1/trading/order", {}, "POST", order=False)
            connection.assert_not_called()

    def test_vps_direct_order_is_also_blocked(self):
        api = KisApiClient(Mock(environment="vps", request_interval=.6), allow_trading=True)
        with self.assertRaises(KisApiError):
            api.execute(self.request("demo"))

    def test_token_expired_get_retries_only_once(self):
        client = KisMarketClient("fake", "fake-secret")
        with patch.object(client, "authenticate") as auth, patch.object(client, "_request", side_effect=[KisAuthenticationExpired("expired"), {"rt_cd": "0"}]) as request:
            self.assertEqual(client.get("/uapi/overseas-price/v1/quotations/dailyprice", {"SYMB": "AAPL"}), {"rt_cd": "0"})
        self.assertEqual(auth.call_count, 2)
        self.assertEqual(request.call_count, 2)

    def test_managed_demo_submits_only_persisted_matching_intent(self):
        with TemporaryDirectory() as directory:
            manager = OrderManager(Path(directory) / "demo.sqlite", "kis_demo")
            try:
                manager.reconcile({"cash": "10000", "positions": {}, "position_costs": {}, "initial": "10000", "exposure": "0", "as_of": datetime.now(timezone.utc).isoformat(), "daily_loss_ratio": 0, "consecutive_losses": 0, "last_loss_at": None}, [], complete=True)
                market = Mock(environment="vps", request_interval=.6, next_request_at=0, access_token="fake", app_key="fake", app_secret="fake")
                api = KisApiClient(market, allow_trading=True)
                adapter = ManagedKisAdapter(api, manager, "fake-account", "01", {"AAPL": "NASD"}, enabled=True)
                from Test.trading.risk_fixtures import seed_risk, snapshot
                proof = seed_risk(manager, source_kind='kis_vps')  # 합성 fixture: 실제 API 증거가 아님
                manager.reconcile(snapshot(proof), [], complete=True)
                manager.create("one", "AAPL", "BUY", 1, "100.00", 97, datetime.now(timezone.utc).isoformat())
                with patch.object(api, "_http", return_value=ApiResponse({"rt_cd": "0", "output": {"ODNO": "001"}})) as http:
                    manager.dispatch("one", adapter)
                self.assertTrue(manager.state["orders"]["one"]["broker_id"].endswith("001"))
                self.assertEqual(http.call_args.args[3]["tr_id"], "VTTT1002U")
                self.assertFalse(api._managed_permission)
            finally:
                manager.close()


class NormalizationTests(unittest.TestCase):
    def row(self):
        return {"orgn_odno": "", "ord_dvsn": "00", "ft_ord_qty": "2", "ft_ccld_qty": "1", "nccs_qty": "1", "ft_ccld_amt3": "100", "tr_crcy_cd": "USD",
            "prcs_stat_name": "접수", "rjct_rson": "", "sll_buy_dvsn_cd": "02", "ord_dt": "20261027", "odno": "001", "pdno": "AAPL", "ft_ord_unpr3": "100"}

    def test_partial_state_and_date_scoped_id(self):
        event = normalize_orders([self.row()])[0]
        self.assertEqual(event["status"], "PARTIAL")
        self.assertEqual(event["broker_id"], "20261027:1")

    def test_unknown_closed_status_is_not_invented(self):
        row = self.row()
        row["nccs_qty"] = "0"
        with self.assertRaises(ValueError):
            normalize_orders([row])

    def test_cancel_child_is_linked_without_inventing_final_cancel(self):
        parent=self.row();parent.update(ft_ccld_qty='0',nccs_qty='2',ft_ccld_amt3='0')
        child={**parent,'odno':'002','orgn_odno':'001','rvse_cncl_dvsn':'02','ft_ord_qty':'1','ft_ord_unpr3':'0'}
        events=normalize_orders([child,parent])
        self.assertEqual(len(events),1);self.assertEqual(events[0]['status'],'ACCEPTED')
        self.assertEqual(events[0]['linked_cancellations'][0]['requested_quantity'],1)
        with self.assertRaises(ValueError):normalize_orders([child])
        child['rvse_cncl_dvsn']='01'
        with self.assertRaises(ValueError):normalize_orders([parent,child])

    def test_missing_fields_do_not_mean_zero(self):
        row = self.row()
        row.pop("ft_ccld_amt3")
        with self.assertRaises(KeyError):
            normalize_orders([row])

    def test_risk_context_must_be_verified(self):
        with self.assertRaises(ValueError):
            normalize_snapshot([], {}, {})

    def test_order_state_save_failure_prevents_any_send(self):
        with TemporaryDirectory() as directory:
            manager = OrderManager(Path(directory) / "orders.sqlite")
            try:
                manager.reconcile({"cash": "10000", "positions": {}, "position_costs": {}, "initial": "10000", "exposure": "0", "as_of": datetime.now(timezone.utc).isoformat(), "daily_loss_ratio": 0, "consecutive_losses": 0, "last_loss_at": None}, [], complete=True)
                manager.connection.execute("PRAGMA query_only=ON")
                with self.assertRaises(sqlite3.OperationalError):
                    manager.create("one", "AAPL", "BUY", 1, 100, 97, datetime.now(timezone.utc).isoformat())
                adapter = Mock()
                with self.assertRaises(ValueError):
                    manager.dispatch("one", adapter)
                adapter.submit.assert_not_called()
            finally:
                manager.close()
