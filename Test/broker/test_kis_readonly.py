"""실제 전송 함수 앞에서 읽기 전용 경계를 검사한다. 모든 API 본문은 합성이다."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from broker.kis_api import overseas_stock, ApiResponse
from broker.kis_api.client import KisApiError
from broker.kis_readonly import ReadOnlyKisApi, inspect_remote, redact_payload
from broker.managed_kis import ManagedKisAdapter
from trading.orders import OrderManager


class ReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.manager = OrderManager(Path(self.temporary.name) / "readonly.sqlite", "kis_demo")
        self.addCleanup(self.manager.close)
        self.market = Mock(
            environment="vps",
            app_key="fake-key-123",
            app_secret="fake-secret-123",
            request_interval=0.6,
            next_request_at=0,
            access_token="fake",
        )
        self.api = ReadOnlyKisApi(self.market, "00000000")
        self.adapter = ManagedKisAdapter(
            self.api, self.manager, "00000000", "01", {"AAPL": "NASD"}, enabled=False
        )

    def order(self):
        return overseas_stock.order(
            "00000000", "01", "NASD", "AAPL", "1", "100", "buy", "", "", "0", "00", env_dv="demo"
        )

    def test_orders_cancel_and_low_level_posts_blocked_before_http(self):
        cancel = overseas_stock.order_rvsecncl(
            "00000000", "01", "NASD", "AAPL", "1", "02", "1", "0", "", "0", env_dv="demo"
        )
        with patch("urllib.request.urlopen") as connection:
            for request in (self.order(), cancel):
                with self.assertRaises(KisApiError):
                    self.api.execute(request)
            with self.assertRaises(KisApiError):
                self.api.execute_managed(self.order(), self.manager, "one")
            self.api._managed_permission = True
            self.api.allow_trading = True
            with self.assertRaises(KisApiError):
                self.api._http(self.order().path, {}, "POST", order=True)
            connection.assert_not_called()

    def test_enabled_false_can_query_without_trading_permission(self):
        with patch.object(
            self.api, "_http", return_value=ApiResponse({"rt_cd": "0", "output": []})
        ) as http:
            self.assertEqual(self.adapter.query_history("20261001", "20261028"), [])
        self.assertFalse(self.api.allow_trading)
        self.assertEqual(http.call_args.args[2], "GET")
        with self.assertRaises(ValueError):
            self.adapter.submit({"symbol": "AAPL"})

    def test_three_reads_and_double_history_use_get_only(self):
        def response(path, parameters, method, *args, **kwargs):
            self.assertEqual(method, "GET")
            self.assertNotIn("/order", path)
            if path.endswith("inquire-ccnl"):
                return ApiResponse({"rt_cd": "0", "output": []})
            if path.endswith("inquire-balance"):
                return ApiResponse({"rt_cd": "0", "output1": []})
            if path.endswith("inquire-psamount"):
                return ApiResponse(
                    {
                        "rt_cd": "0",
                        "output": {
                            "tr_crcy_cd": "USD",
                            "ord_psbl_frcr_amt": "10000",
                            "ovrs_ord_psbl_amt": "10000",
                        },
                    }
                )
            return ApiResponse(
                {
                    "rt_cd": "0",
                    "output1": [],
                    "output2": [{"crcy_cd": "USD", "frcr_dncl_amt_2": "10000"}],
                    "output3": [],
                }
            )

        with patch.object(self.api, "_http", side_effect=response) as http:
            result = inspect_remote(
                self.manager, self.adapter, "20261001", "20261028", "AAPL", "100"
            )
        self.assertEqual(http.call_count, 7)
        self.assertFalse(result["new_orders_allowed"])
        self.assertFalse(self.manager.ready)
        self.assertEqual(result["reported_usd_deposit_settlement_basis"], "10000")
        self.assertIn("execution_fee_and_cash_movement_history_not_proven", result["issues"])

    def test_changed_snapshot_and_present_page_repeat_fail_closed(self):
        adapter = Mock(
            query_history=Mock(side_effect=[[], [{"unexpected": "row"}]]),
            query_balances=Mock(return_value=[]),
            query_buying_power=Mock(return_value={}),
            query_present_balance=Mock(return_value={}),
        )
        with self.assertRaises(Exception):
            inspect_remote(self.manager, adapter, "20261001", "20261028", "AAPL", "100")
        response = ApiResponse({"rt_cd": "0", "output1": [], "output2": [], "output3": []}, "M")
        with patch.object(self.api, "execute", return_value=response):
            with self.assertRaisesRegex(ValueError, "page_repeated"):
                self.adapter.query_present_balance()

    def test_redaction_removes_identity_tokens_and_free_text(self):
        value = {
            "cano": "00000000",
            "appkey": "fake-key-123",
            "msg1": "00000000 secret",
            "output": {"note": "fake-key-123 00000000", "quantity": "2"},
        }
        safe = redact_payload(value, ("00000000", "fake-key-123"))
        encoded = json.dumps(safe)
        self.assertNotIn("00000000", encoded)
        self.assertNotIn("fake-key-123", encoded)
        self.assertNotIn("msg1", safe)

    def test_replay_store_cannot_send_even_when_adapter_enabled(self):
        self.manager.state["replay_only"] = True
        self.adapter.enabled = True
        with patch("urllib.request.urlopen") as connection:
            with self.assertRaisesRegex(ValueError, "replay_store_never_sends_orders"):
                self.adapter.submit({"symbol": "AAPL"})
            connection.assert_not_called()

    def test_prod_environment_rejected(self):
        with self.assertRaises(ValueError):
            ReadOnlyKisApi(Mock(environment="prod"), "00000000")


class DemoCredentialFormatTests(unittest.TestCase):
    def parse(self, text):
        from kis_preflight import read_demo_identity
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'demo.env'
            path.write_text('KIS_APP_KEY=fake-key\nKIS_APP_SECRET=fake-secret\n'+text, encoding='utf-8')
            return read_demo_identity(path)

    def test_combined_acc_no_uses_explicit_demo_tool_default(self):
        self.assertEqual(self.parse('ACC_NO=00000000-01\n')[2:], ('00000000','01'))

    def test_separate_fields_remain_supported(self):
        self.assertEqual(self.parse('KIS_ENVIRONMENT=vps\nKIS_ACCOUNT_NUMBER=00000000\nKIS_ACCOUNT_PRODUCT_CODE=01\n')[2:], ('00000000','01'))

    def test_duplicate_format_conflict_and_wrong_environment_rejected(self):
        for text in ('ACC_NO=00000000-01\nKIS_ACCOUNT_NUMBER=11111111\n',
                     'ACC_NO=00000000-01\nKIS_ENVIRONMENT=prod\n',
                     'ACC_NO=00000000-01\nACC_NO=11111111-01\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.parse(text)

    def test_account_format_and_unclosed_quote_rejected(self):
        for value in ('00000000', '00000000-1', '00000000-01-extra', '"00000000-01'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.parse('ACC_NO='+value+'\n')
