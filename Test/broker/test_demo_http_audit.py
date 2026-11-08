"""실패 GET과 제한된 재시도 근거에 비밀값이 남지 않는 합성 검사."""
import io
import json
import unittest
import urllib.error
from unittest.mock import Mock, patch
from broker.kis_api.client import KisApiClient
from broker.kis import KisApiError
from Test.broker.test_kis_api import market_client, sample_request


class HttpAuditTests(unittest.TestCase):
    def response(self):
        value=Mock();value.status=200;value.headers={}
        value.__enter__=Mock(return_value=value);value.__exit__=Mock(return_value=False)
        value.read.return_value=b'{"rt_cd":"0","output":{}}'
        return value

    def test_http_rate_limit_and_recovery_are_both_logged_safely(self):
        api=KisApiClient(market_client())
        error=urllib.error.HTTPError('https://secret?CANO=private-account',500,'private-secret',{},
            io.BytesIO(b'{"msg_cd":"EGW00201","msg1":"private-account fake-token"}'))
        with patch('urllib.request.urlopen',side_effect=[error,self.response()]):api.execute(sample_request())
        rows=api.http_audit
        self.assertEqual([r['http_status'] for r in rows],[500,200])
        self.assertEqual([r['attempt'] for r in rows],[1,2])
        self.assertTrue(rows[0]['retry_scheduled']);self.assertEqual(rows[0]['provider_code'],'EGW00201')
        self.assertEqual(rows[1]['outcome'],'success')
        serialized=json.dumps(rows)
        for value in ['fake-secret','fake-key','fake-token','private-account','msg1','authorization','CANO=']:
            self.assertNotIn(value,serialized)

    def test_unknown_provider_text_is_not_saved(self):
        api=KisApiClient(market_client())
        error=urllib.error.HTTPError('https://hidden',403,'secret',{},io.BytesIO(b'{"msg_cd":"private-account","msg1":"fake-secret"}'))
        with patch('urllib.request.urlopen',side_effect=error),self.assertRaises(KisApiError):api.execute(sample_request())
        self.assertEqual(api.http_audit[0]['http_status'],403)
        self.assertIsNone(api.http_audit[0]['provider_code'])
        self.assertNotIn('private-account',json.dumps(api.http_audit))
