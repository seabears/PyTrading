"""선물·옵션·ELW는 구현 보존, REST·실시간 전송은 불허하는지 검사한다."""
import importlib
import json
import unittest
from unittest.mock import Mock, patch

from broker.kis import KisApiError
from broker.kis_api import KisApiClient
from broker.kis_api.client import load_catalog, validate_operation
from broker.kis_api.websocket import KisStreamSession
from paths import CONFIG_ROOT, FIXTURES_ROOT


class DisallowedProductTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()
        vectors = json.loads((FIXTURES_ROOT / "kis-api-vectors.json").read_text(encoding="utf-8"))["vectors"]
        self.vectors = {}
        for vector in vectors:self.vectors.setdefault(vector["name"], vector)
        self.market = Mock(environment="prod", app_key="fake", app_secret="fake", access_token="fake", request_interval=0.2, next_request_at=0)

    def build(self, name):
        module, function = name.rsplit(".", 1)
        return getattr(importlib.import_module("broker.kis_api." + module), function)(**self.vectors[name]["arguments"])

    def test_implementations_preserved_and_status_counts_explicit(self):
        self.assertEqual(len(self.catalog), 323)
        disabled = [row for row in self.catalog.values() if not row["enabled"]]
        self.assertEqual(len(disabled), 104)
        self.assertEqual(sum(row["enabled"] for row in self.catalog.values()), 219)
        for row in disabled:
            with self.subTest(api=row["name"]):
                self.assertTrue(row["disabled_reason"])
                self.assertIsNotNone(self.build(row["name"]))

    def test_all_disallowed_rest_calls_block_before_auth_and_network(self):
        client = KisApiClient(self.market, allow_trading=True)
        with patch.object(client, "_http") as http:
            for row in self.catalog.values():
                if row["enabled"] or row["kind"] != "rest":continue
                with self.subTest(api=row["name"]), self.assertRaisesRegex(KisApiError, "사용 불허"):
                    client.execute(self.build(row["name"]))
        self.market.authenticate.assert_not_called()
        http.assert_not_called()

    def test_all_disallowed_websocket_subscriptions_block_before_send(self):
        client, socket = KisApiClient(self.market), Mock()
        session = KisStreamSession(client, socket, "fake-approval")
        # 실행 중인 클라이언트가 과거 허용 상태를 캐시한 경우도 최신 설정으로 차단한다.
        for cached in client.catalog.values():cached["enabled"] = True
        for row in self.catalog.values():
            if row["enabled"] or row["kind"] != "websocket":continue
            with self.subTest(api=row["name"]), self.assertRaisesRegex(KisApiError, "사용 불허"):
                session.send(self.build(row["name"]))
        socket.send.assert_not_called()

    def test_low_level_transport_cannot_bypass_disallowed_paths(self):
        client = KisApiClient(self.market, allow_trading=True)
        paths = {path for row in self.catalog.values() if not row["enabled"] for path in row["paths"]}
        with patch("broker.kis_api.client.urllib.request.urlopen") as network:
            for path in paths:
                with self.subTest(path=path), self.assertRaisesRegex(KisApiError, "사용 불허"):
                    client._http(path, {}, "GET")
        network.assert_not_called()

    def test_elw_reference_in_stock_module_also_disallowed(self):
        row = self.catalog["domestic_stock.inquire_elw_price"]
        self.assertFalse(row["enabled"])

    def test_stocks_bonds_etfs_stay_allowed(self):
        for name in ("domestic_stock.inquire_price", "overseas_stock.price", "domestic_bond.inquire_price", "etfetn.inquire_price"):
            with self.subTest(api=name):
                request = self.build(name)
                # 종목 분류는 별도 정책 테스트에서 검사한다. 여기서는 상품별 API 허용 상태를 검사한다.
                for key in ("FID_INPUT_ISCD", "PDNO", "SYMB"):
                    if key in request.parameters:request.parameters[key] = "AAPL"
                environment = "prod" if request.environment == "real" else "vps"
                self.assertTrue(validate_operation(request, "rest", environment, self.catalog)["enabled"])

    def test_stock_websocket_still_sends(self):
        from broker.kis_api import overseas_stock_ws
        socket = Mock()
        session = KisStreamSession(KisApiClient(self.market), socket, "fake")
        session.send(overseas_stock_ws.asking_price("1", "DNASAAPL"))
        socket.send.assert_called_once()
