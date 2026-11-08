"""대출 API 제거와 현금 주문 우회 차단을 합성 요청으로 검사한다. 실제 인증·주문 없음."""
import importlib
import inspect
import json
import unittest
from unittest.mock import Mock, patch

from broker.kis import KisApiError
from broker.kis_api import ApiRequest, KisApiClient, overseas_stock
from broker.kis_api.policy import REMOVED_OPERATIONS, REMOVED_PATHS
from paths import CONFIG_ROOT, FIXTURES_ROOT


class NoBorrowingTests(unittest.TestCase):
    def setUp(self):
        self.market = Mock(environment="prod", app_key="fake", app_secret="fake", access_token="fake", request_interval=0.2, next_request_at=0.0)

    def test_dedicated_functions_and_allowed_paths_are_removed(self):
        catalog = json.loads((CONFIG_ROOT / "kis-api-catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(len(REMOVED_OPERATIONS), 8)
        for name in REMOVED_OPERATIONS:
            module, function = name.rsplit(".", 1)
            self.assertFalse(hasattr(importlib.import_module("broker.kis_api." + module), function), name)
        self.assertFalse(REMOVED_OPERATIONS & {row["name"] for row in catalog["operations"]})
        self.assertFalse(REMOVED_PATHS & {path for row in catalog["operations"] for path in row["paths"]})
        self.assertEqual({row["name"] for row in catalog["excluded_by_user"]}, REMOVED_OPERATIONS)

    def test_removed_api_cannot_even_build_a_request(self):
        for path in REMOVED_PATHS:
            with self.subTest(path=path), self.assertRaises(KisApiError):
                ApiRequest("forged", path, "FAKE", {})

    def test_allow_trading_does_not_bypass_removed_path_or_old_catalog(self):
        client = KisApiClient(self.market, allow_trading=True)
        request = overseas_stock.price("", "NAS", "AAPL")
        path = "/uapi/domestic-stock/v1/trading/order-credit"
        # 예전 설정 복원과 외부에서 만든 변조 요청까지 전송 직전 검사에서 막는다.
        object.__setattr__(request, "path", path)
        client.catalog[request.name] = {"kind": "rest", "paths": [path], "methods": ["GET"], "transaction_ids": [request.transaction_id]}
        with patch.object(client, "_http") as http, self.assertRaises(KisApiError):
            client.execute(request)
        self.market.authenticate.assert_not_called()
        http.assert_not_called()

    def test_parameters_mutated_after_creation_are_blocked_before_auth(self):
        client = KisApiClient(self.market, allow_trading=True)
        for name, value in (("LOAN_DT", "20261023"), ("CRDT_TYPE", "21"), ("LDNG_DT", "20261023"), ("SLL_TYPE", "05")):
            request = overseas_stock.price("", "NAS", "AAPL")
            request.parameters[name] = value
            with self.subTest(field=name), self.assertRaises(KisApiError):client.execute(request)
        self.market.authenticate.assert_not_called()

    def test_low_level_transport_also_blocks_loan_endpoint(self):
        client = KisApiClient(self.market, allow_trading=True)
        with patch("broker.kis_api.client.urllib.request.urlopen") as network, self.assertRaises(KisApiError):
            client._http("/uapi/domestic-stock/v1/trading/order-credit", {}, "POST", order=True)
        network.assert_not_called()

    def test_reservation_signatures_remove_loan_arguments_and_cash_stays_available(self):
        from broker.kis_api import domestic_stock
        vectors = json.loads((FIXTURES_ROOT / "kis-api-vectors.json").read_text(encoding="utf-8"))["vectors"]
        for name in ("order_resv", "order_resv_rvsecncl"):
            function = getattr(domestic_stock, name)
            self.assertNotIn("loan_dt", inspect.signature(function).parameters)
            self.assertNotIn("ldng_dt", inspect.signature(function).parameters)
            arguments = next(row["arguments"] for row in vectors if row["name"] == "domestic_stock." + name)
            request = function(**arguments)
            self.assertEqual(request.parameters["ORD_OBJT_CBLC_DVSN_CD"], "10")
            self.assertNotIn("LOAN_DT", request.parameters)
            with self.assertRaises(ValueError):function(**{**arguments, "ord_objt_cblc_dvsn_cd": "12"})
            with self.assertRaises(TypeError):function(**{**arguments, "loan_dt": "20261023"})

    def test_reservation_raw_request_requires_cash_balance_code(self):
        path = "/uapi/domestic-stock/v1/trading/order-resv"
        for parameters in ({}, {"ORD_OBJT_CBLC_DVSN_CD": "12"}, {"ORD_OBJT_CBLC_DVSN_CD": "21"}):
            with self.subTest(parameters=parameters), self.assertRaises(KisApiError):
                ApiRequest("domestic_stock.order_resv", path, "FAKE", parameters, "POST")
        self.assertEqual(ApiRequest("cash", path, "FAKE", {"ORD_OBJT_CBLC_DVSN_CD": "10"}, "POST").parameters["ORD_OBJT_CBLC_DVSN_CD"], "10")

    def test_regular_cash_sell_remains_and_borrowed_sell_is_blocked(self):
        path = "/uapi/domestic-stock/v1/trading/order-cash"
        for value in ("", "01"):
            ApiRequest("cash", path, "FAKE", {"SLL_TYPE": value}, "POST")
        with self.assertRaises(KisApiError):ApiRequest("cash", path, "FAKE", {"SLL_TYPE": "05"}, "POST")

    def test_normal_history_has_no_public_loan_filter(self):
        self.assertNotIn("loan_dvsn_cd", inspect.signature(overseas_stock.inquire_period_trans).parameters)
        vectors = json.loads((FIXTURES_ROOT / "kis-api-vectors.json").read_text(encoding="utf-8"))["vectors"]
        arguments = next(row["arguments"] for row in vectors if row["name"] == "overseas_stock.inquire_period_trans")
        self.assertEqual(overseas_stock.inquire_period_trans(**arguments).parameters["LOAN_DVSN_CD"], "")
