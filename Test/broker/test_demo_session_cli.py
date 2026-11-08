"""조회 진입점의 실제 HTTP 허용 경계와 선행 복구 차단을 합성 검사한다."""
import json
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
from broker.kis import BASE_URLS,TOKEN_PATH
from kis_demo_session import validate_demo_readonly_request,run


class DemoCliTests(unittest.TestCase):
    def test_only_demo_auth_and_readonly_get_are_allowed(self):
        request=urllib.request.Request(BASE_URLS['vps']+TOKEN_PATH,data=b'{}',method='POST')
        self.assertEqual(validate_demo_readonly_request(request),('POST',TOKEN_PATH))
        request=urllib.request.Request(BASE_URLS['vps']+'/uapi/overseas-stock/v1/trading/inquire-balance?CANO=synthetic',method='GET')
        self.assertEqual(validate_demo_readonly_request(request)[0],'GET')

    def test_actual_order_cancel_and_prod_are_blocked_at_http_boundary(self):
        for path in ['/uapi/overseas-stock/v1/trading/order','/uapi/overseas-stock/v1/trading/order-rvsecncl']:
            with self.assertRaises(ValueError):validate_demo_readonly_request(urllib.request.Request(BASE_URLS['vps']+path,data=b'{}',method='POST'))
        with self.assertRaises(ValueError):validate_demo_readonly_request(urllib.request.Request(BASE_URLS['prod']+TOKEN_PATH,data=b'{}',method='POST'))

    def test_no_recovery_means_no_credential_read_or_network(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name);source=folder/'recovery.json';source.write_text(json.dumps({'regular_recovery_verified':False}),encoding='utf-8')
            with patch('kis_demo_session.read_demo_identity') as credentials,patch('kis_demo_session.urllib.request.urlopen') as network:
                with self.assertRaises(ValueError):run(source,folder/'never.env',folder/'output')
                credentials.assert_not_called();network.assert_not_called()
