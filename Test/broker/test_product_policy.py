"""공용 API에서도 ETN·미확인 상품을 차단하고 주식·채권·ETF만 허용한다."""
import copy
import json
import unittest
from unittest.mock import Mock, patch

from broker.kis import KisMarketClient, KisApiError
from broker.kis_api import KisApiClient, overseas_stock, overseas_stock_ws, etfetn
from broker.kis_api.websocket import KisStreamSession
from broker.product_policy import load_product_rules, validate_product_request, validate_symbol
from paths import CONFIG_ROOT


class StockBondEtfPolicyTests(unittest.TestCase):
    def setUp(self):
        self.market = Mock(environment="prod", app_key="fake", app_secret="fake", access_token="fake", request_interval=0.2, next_request_at=0.0)
        self.client = KisApiClient(self.market, allow_trading=True)

    def test_allowed_types_and_current_watchlist(self):
        rules = load_product_rules()
        self.assertEqual(set(rules["allowed_asset_types"]), {"stock", "bond", "etf"})
        settings = json.loads((CONFIG_ROOT / "settings.json").read_text(encoding="utf-8"))
        for instrument in settings["symbols"]:
            validate_symbol(instrument.split(":", 1)[1], rules)

    def test_etn_and_unknown_names_fail_before_authentication(self):
        for symbol in ("Q500001", "500001", "VXX", "NOT_VERIFIED"):
            request = overseas_stock.price("", "NAS", symbol)
            with self.subTest(symbol=symbol), patch.object(self.client, "_http") as http, self.assertRaises(KisApiError):
                self.client.execute(request)
            http.assert_not_called()
        self.market.authenticate.assert_not_called()

    def test_shared_etf_endpoint_keeps_etf_and_blocks_etn(self):
        from broker.kis_api.client import validate_operation
        allowed = etfetn.inquire_price(fid_cond_mrkt_div_code="J", fid_input_iscd="069500")
        # 사용자 명시 예외는 069500에만 적용하며 다른 ETF 차단은 유지한다.
        validate_operation(allowed, "rest", "prod")
        validate_operation(overseas_stock.price("", "AMS", "SPY"), "rest", "prod")
        denied = etfetn.inquire_price(fid_cond_mrkt_div_code="J", fid_input_iscd="Q500001")
        with self.assertRaisesRegex(KisApiError, "ETN"):self.client.execute(denied)
        self.market.authenticate.assert_not_called()

    def test_shared_stock_order_cannot_send_etn(self):
        request = overseas_stock.order(cano="12345678", acnt_prdt_cd="01", ovrs_excg_cd="NASD", pdno="VXX", ord_qty="1", ovrs_ord_unpr="1", ord_dv="buy", ctac_tlno="", mgco_aptm_odno="", ord_svr_dvsn_cd="0", ord_dvsn="00")
        with patch.object(self.client, "_http") as http, self.assertRaises(KisApiError):self.client.execute(request)
        self.market.authenticate.assert_not_called();http.assert_not_called()

    def test_websocket_etn_blocked_and_stock_still_allowed(self):
        socket = Mock();session = KisStreamSession(self.client, socket, "fake")
        with self.assertRaises(KisApiError):session.send(overseas_stock_ws.asking_price("1", "DNASVXX"))
        socket.send.assert_not_called()
        session.send(overseas_stock_ws.asking_price("1", "DNASAAPL"))
        socket.send.assert_called_once()

    def test_confirmed_etn_is_denied_even_without_q_prefix(self):
        rules = copy.deepcopy(load_product_rules())
        rules["verified_instruments"]["EXAMPLE"] = {"asset_type": "etn"}
        with self.assertRaisesRegex(KisApiError, "사용 불허"):validate_symbol("EXAMPLE", rules)

    def test_confirmed_bond_and_etf_types_allowed_other_types_denied(self):
        rules = copy.deepcopy(load_product_rules())
        for asset_type in ("stock", "bond", "etf", "etn", "elw", "future", "option", "other"):
            rules["verified_instruments"]["EXAMPLE"] = {"asset_type": asset_type}
            with self.subTest(asset_type=asset_type):
                if asset_type in {"stock", "bond"}:validate_symbol("EXAMPLE", rules)
                else:
                    with self.assertRaises(KisApiError):validate_symbol("EXAMPLE", rules)

    def test_low_level_and_legacy_requests_do_not_bypass_policy(self):
        with patch("broker.kis_api.client.urllib.request.urlopen") as network, self.assertRaises(KisApiError):
            self.client._http("/uapi/overseas-price/v1/quotations/price", {"SYMB": "VXX"}, "GET")
        network.assert_not_called()
        legacy = KisMarketClient("fake", "fake")
        with patch.object(legacy, "authenticate") as auth, self.assertRaises(KisApiError):
            legacy.get("/uapi/overseas-price/v1/quotations/inquire-asking-price", {"SYMB": "VXX"})
        auth.assert_not_called()

    def test_multiple_symbol_requests_cannot_hide_etn(self):
        request = overseas_stock.multprice([("NAS", "AAPL"), ("NAS", "VXX")])
        with self.assertRaises(KisApiError):self.client.execute(request)
        self.market.authenticate.assert_not_called()

    def test_derivative_paths_stay_denied(self):
        for path in ("/uapi/domestic-futureoption/v1/quotations/inquire-price", "/uapi/overseas-futureoption/v1/quotations/inquire-price", "/uapi/elw/v1/quotations/indicator"):
            with self.subTest(path=path), self.assertRaises(KisApiError):validate_product_request(path, {})

    def test_market_and_account_queries_without_instrument_stay_available(self):
        for path, parameters in (("/uapi/domestic-stock/v1/trading/inquire-balance", {"CANO": "12345678"}),
                                 ("/uapi/domestic-stock/v1/quotations/inquire-index-price", {"FID_INPUT_ISCD": "0001"})):
            validate_product_request(path, parameters)
