"""전체 공식 요청 계약과 HTTP·실시간 전송 경계를 인터넷 없이 검증한다."""
import base64
import importlib
import io
import json
import unittest
import urllib.error
from dataclasses import replace
from unittest.mock import Mock, patch

from broker.kis import KisApiError, KisRateLimitError
from broker.kis_api import ApiRequest, ApiResponse, KisApiClient
from broker.kis_api.client import KisOrderStateUnknown, load_catalog
from broker.kis_api.websocket import KisStreamSession, decrypt_notice
from broker.kis_api import overseas_stock_ws
from paths import FIXTURES_ROOT, CONFIG_ROOT


def market_client(environment="prod"):
    return Mock(environment=environment, app_key="fake-key", app_secret="fake-secret", access_token="fake-token",
                request_interval=0.2, next_request_at=0.0)


def sample_request(method="GET", environment="real"):
    values = json.loads((FIXTURES_ROOT / "kis-api-vectors.json").read_text(encoding="utf-8"))["vectors"]
    vector = next(row for row in values if row["name"].startswith("overseas_stock.") and row["expected"].get("method") == method and row["environment"] == environment)
    module, name = vector["name"].rsplit(".", 1)
    request = getattr(importlib.import_module("broker.kis_api." + module), name)(**vector["arguments"])
    for key in ("PDNO", "SYMB"):
        if key in request.parameters:request.parameters[key] = "AAPL"
    return request


class OfficialApiContractTests(unittest.TestCase):
    def test_all_functions_and_tr_variants_match_pinned_official_contract(self):
        fixture = json.loads((FIXTURES_ROOT / "kis-api-vectors.json").read_text(encoding="utf-8"))
        catalog = load_catalog()
        self.assertEqual(len(catalog), 323)
        self.assertEqual(fixture["missing"], [])
        self.assertEqual(fixture["uncovered"], [])
        seen = set()
        for vector in fixture["vectors"]:
            with self.subTest(api=vector["name"], environment=vector["environment"]):
                module, name = vector["name"].rsplit(".", 1)
                result = getattr(importlib.import_module("broker.kis_api." + module), name)(**vector["arguments"])
                for key, expected in vector["expected"].items():
                    actual = getattr(result, key)
                    self.assertEqual(list(actual) if key == "columns" else actual, expected)
                self.assertEqual(result.environment, vector["environment"])
                seen.add(vector["name"])
        self.assertEqual(seen, set(catalog))

    def test_current_portal_inventory_has_no_missing_routes(self):
        catalog = json.loads((CONFIG_ROOT / "kis-api-catalog.json").read_text(encoding="utf-8"))
        operations = catalog["operations"]
        rest = {path for row in operations for path in row["paths"]}
        streams = {identifier for row in operations if row["kind"] == "websocket" for identifier in row["transaction_ids"]}
        auth = {"/oauth2/tokenP", "/oauth2/Approval", "/oauth2/revokeP"}
        self.assertEqual(len(catalog["portal_inventory_paths"]), 323)
        for path in catalog["portal_inventory_paths"]:
            with self.subTest(path=path):
                if path.startswith("/tryitout/"):
                    self.assertIn(path.split("/")[-1], streams)
                else:
                    self.assertIn(path, rest | auth)

    def test_portal_only_rest_and_websocket_functions_validate_inputs(self):
        from broker.kis_api import overseas_stock, etfetn, domestic_futureoption, domestic_stock_ws
        request = overseas_stock.multprice([("NAS", "AAPL"), ("NYS", "T")])
        self.assertEqual(request.parameters["NREC"], "2")
        self.assertEqual(request.parameters["SYMB_02"], "T")
        for symbols in ([], [("NASD", "AAPL")], [("NAS", "AAPL")] * 11):
            with self.subTest(symbols=symbols), self.assertRaises(ValueError):overseas_stock.multprice(symbols)
        self.assertEqual(etfetn.inquire_asking_price("069500").transaction_id, "FHPST02400200")
        with self.assertRaises(ValueError):etfetn.inquire_asking_price("invalid")
        self.assertEqual(domestic_futureoption.margin_rate("20261022").transaction_id, "TTTO6032R")
        with self.assertRaises(ValueError):domestic_futureoption.margin_rate("20260230")
        self.assertEqual(domestic_stock_ws.vi_integrated("1", "005930").transaction_id, "H0UNVIC0")

    def test_portal_current_rest_transactions_replace_stale_examples(self):
        catalog = load_catalog()
        self.assertIn("STTN1103U", catalog["domestic_futureoption.order_rvsecncl"]["transaction_ids"])
        self.assertNotIn("TTTN1103U", catalog["domestic_futureoption.order_rvsecncl"]["transaction_ids"])
        self.assertEqual(catalog["overseas_futureoption.inquire_time_optchartprice"]["transaction_ids"], ["HHDFO55020400"])

    def test_actual_us_quote_schema_uses_portal_71_fields(self):
        subscription = overseas_stock_ws.asking_price("1", "DNASAAPL")
        self.assertEqual(len(subscription.columns), 71)
        self.assertEqual(subscription.columns[:2], ("RSYM", "SYMB"))
        self.assertEqual(subscription.columns[-1], "DASK10")

    def test_american_demo_sell_uses_documented_transaction_id(self):
        from broker.kis_api.overseas_stock import order
        request = order(cano="12345678", acnt_prdt_cd="01", ovrs_excg_cd="NASD", pdno="AAPL", ord_qty="1",
                        ovrs_ord_unpr="1", ord_dv="sell", ctac_tlno="", mgco_aptm_odno="", ord_svr_dvsn_cd="0", ord_dvsn="00", env_dv="demo")
        self.assertEqual(request.transaction_id, "VTTT1001U")


class ApiTransportTests(unittest.TestCase):
    def setUp(self):
        self.market = market_client()
        self.client = KisApiClient(self.market)

    def test_order_blocked_before_authentication(self):
        with patch.object(self.client, "_http") as http, self.assertRaises(KisApiError):
            self.client.execute(sample_request("POST"))
        http.assert_not_called()
        self.market.authenticate.assert_not_called()

    def test_forged_path_tr_or_method_blocked_before_authentication(self):
        request = sample_request()
        for changed in (replace(request, path="/uapi/private"), replace(request, transaction_id="EVIL"), replace(request, method="POST")):
            with self.subTest(request=changed), self.assertRaises(KisApiError):
                self.client.execute(changed)
        self.market.authenticate.assert_not_called()

    def test_environment_mismatch_blocked(self):
        with self.assertRaises(KisApiError):
            self.client.execute(replace(sample_request(), environment="demo"))
        self.market.authenticate.assert_not_called()

    def test_read_only_rate_limit_retries_once_and_preserves_continuation(self):
        response = ApiResponse({"rt_cd": "0", "output": [{"value": "1"}]}, "M")
        with patch.object(self.client, "_http", side_effect=[KisRateLimitError("limit"), response]) as http:
            result = self.client.execute(replace(sample_request(), continuation="N"))
        self.assertEqual(http.call_count, 2)
        self.assertEqual(http.call_args.args[3]["tr_cont"], "N")
        self.assertTrue(result.has_more)
        self.assertGreater(self.market.next_request_at, 0)

    def test_order_permission_flag_without_account_context_is_blocked(self):
        client = KisApiClient(self.market, allow_trading=True)
        client.market_client.environment = "vps"
        client._managed_permission = True
        with patch.object(client, "_http") as http, self.assertRaises(KisApiError):
            client.execute(sample_request("POST", "demo"))
        http.assert_not_called()

    def test_missing_managed_context_never_queries_order_response(self):
        client = KisApiClient(self.market, allow_trading=True)
        client.market_client.environment = "vps"
        client._managed_permission = True
        with patch.object(client, "_http", return_value=ApiResponse({})) as http, self.assertRaises(KisApiError):
            client.execute(sample_request("POST", "demo"))
        http.assert_not_called()

    def test_raw_permission_flag_never_transmits_or_retries(self):
        client = KisApiClient(self.market, allow_trading=True)
        client.market_client.environment = "vps"
        client._managed_permission = True
        with patch("broker.kis_api.client.urllib.request.urlopen") as opener:
            with self.assertRaises(KisApiError):client.execute(sample_request("POST", "demo"))
        opener.assert_not_called()
        # 정식 원장/어댑터의 응답 유실 무재전송은 test_trial_integration에서 유지한다.

    def test_http_error_body_array_is_not_exposed(self):
        error = urllib.error.HTTPError("url", 403, "secret", {}, io.BytesIO(b'["private-account"]'))
        with patch("broker.kis_api.client.urllib.request.urlopen", side_effect=error), self.assertRaises(KisApiError) as raised:
            self.client.execute(sample_request())
        self.assertNotIn("private-account", str(raised.exception))

    def test_real_http_request_has_auth_headers_and_get_query(self):
        context = Mock()
        context.__enter__ = Mock(return_value=io.StringIO('{"rt_cd":"0","output":[]}'))
        context.__exit__ = Mock(return_value=False)
        context.__enter__.return_value.headers = {"tr_cont": "F"}
        with patch("broker.kis_api.client.urllib.request.urlopen", return_value=context) as opener:
            response = self.client.execute(sample_request())
        request = opener.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Authorization"), "Bearer fake-token")
        self.assertEqual(request.get_header("Appkey"), "fake-key")
        self.assertNotIn("fake-secret", request.full_url)
        self.assertTrue(response.has_more)

    def test_approval_and_hash_use_correct_endpoints_and_fields(self):
        with patch.object(self.client, "_http", side_effect=[ApiResponse({"approval_key": "approval"}), ApiResponse({"HASH": "hash"})]) as http:
            self.assertEqual(self.client.approval_key(), "approval")
            self.assertEqual(self.client.hash_key({"ORD_QTY": "1"}), "hash")
        self.assertEqual(http.call_args_list[0].args[0], "/oauth2/Approval")
        self.assertEqual(http.call_args_list[0].args[1]["secretkey"], "fake-secret")
        self.assertEqual(http.call_args_list[1].args[0], "/uapi/hashkey")

    def test_revoke_blocked_and_authentication_reuses_existing_client(self):
        with self.assertRaises(KisApiError):self.client.revoke_token()
        self.market.authenticate.assert_not_called()
        self.client.authenticate()
        self.market.authenticate.assert_called_once()

    def test_response_rows_and_private_representations(self):
        response = ApiResponse({"output": {"account": "private-account"}})
        self.assertEqual(response.rows(), [{"account": "private-account"}])
        self.assertNotIn("private-account", repr(response))
        with self.assertRaises(ValueError):response.rows("missing")
        request = replace(sample_request(), parameters={"CANO": "private-account"})
        self.assertNotIn("private-account", repr(request))


class ApiWebsocketTests(unittest.TestCase):
    def setUp(self):
        self.api = KisApiClient(market_client())
        self.socket = Mock()
        self.session = KisStreamSession(self.api, self.socket, "private-approval")
        self.subscription = overseas_stock_ws.asking_price("1", "DNASAAPL")
        self.session.send(self.subscription)

    def test_subscription_message_and_unsubscribe(self):
        message = json.loads(self.socket.send.call_args.args[0])
        self.assertEqual(message["body"]["input"]["tr_id"], "HDFSASP0")
        self.assertEqual(message["header"]["approval_key"], "private-approval")
        self.session.send(overseas_stock_ws.asking_price("2", "DNASAAPL"))
        self.assertEqual(json.loads(self.socket.send.call_args.args[0])["header"]["tr_type"], "2")

    def test_ping_responds_with_pong(self):
        raw = '{"header":{"tr_id":"PINGPONG"}}'
        self.assertEqual(self.session.parse(raw).kind, "ping")
        self.socket.pong.assert_called_once_with(raw.encode())

    def test_multiple_rows_parse_without_losing_fields(self):
        width = len(self.subscription.columns)
        values = "^".join(str(index) for index in range(width * 2))
        event = self.session.parse(f"0|HDFSASP0|002|{values}")
        self.assertEqual(len(event.rows), 2)
        self.assertEqual(event.rows[1][self.subscription.columns[0]], str(width))
        self.assertNotIn("private-approval", repr(event))

    def test_invalid_width_and_unknown_tr_fail(self):
        for message in ("0|HDFSASP0|001|1^2", "0|UNKNOWN|001|1", "2|HDFSASP0|001|1"):
            with self.subTest(message=message), self.assertRaises(KisApiError):self.session.parse(message)

    def test_real_aes_cbc_encrypted_notice_round_trip(self):
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.padding import PKCS7
        key, initialization_vector = "1" * 32, "2" * 16
        values = "^".join("value" for _ in self.subscription.columns)
        padder = PKCS7(128).padder()
        padded = padder.update(values.encode()) + padder.finalize()
        encoder = Cipher(algorithms.AES(key.encode()), modes.CBC(initialization_vector.encode())).encryptor()
        encrypted = base64.b64encode(encoder.update(padded) + encoder.finalize()).decode()
        ack = {"header": {"tr_id": "HDFSASP0", "tr_key": "DNASAAPL"},
               "body": {"rt_cd": "0", "output": {"key": key, "iv": initialization_vector}}}
        self.assertEqual(self.session.parse(json.dumps(ack)).kind, "subscribed")
        event = self.session.parse("1|HDFSASP0|001|" + encrypted)
        self.assertEqual(len(event.rows), 1)
        self.assertEqual(set(event.rows[0].values()), {"value"})
        with self.assertRaises(KisApiError):decrypt_notice(encrypted, "bad", initialization_vector)

    def test_rejected_ack_and_missing_key_fail(self):
        with self.assertRaises(KisApiError):self.session.parse('{"header":{"tr_id":"HDFSASP0"},"body":{"rt_cd":"1"}}')
        with self.assertRaises(KisApiError):self.session.parse('1|HDFSASP0|001|encrypted')

    def test_timeout_ends_and_message_bound_is_enforced(self):
        self.socket.recv.side_effect = TimeoutError()
        self.assertEqual(list(self.session.events(2, 0.1)), [])
        with self.assertRaises(ValueError):list(self.session.events(0))
