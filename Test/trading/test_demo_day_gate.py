"""오늘 모의 시험의 정규장/시세 전용 HTTP 경계. 외부 호출이나 실제 관측을 만들지 않는다."""
import tempfile,unittest,urllib.request
from pathlib import Path
from unittest.mock import Mock,patch
from broker.kis import BASE_URLS,TOKEN_PATH
from broker.kis_market import US_QUOTE
from tools.demo_quote_watch import validate_quote_request
from trading.demo_day_gate import QuoteWatchProcess


class DemoDayGateTests(unittest.TestCase):
    def test_only_prod_quote_and_auth_requests_are_allowed(self):
        for method,path in [('GET',US_QUOTE),('POST',TOKEN_PATH)]:
            request=urllib.request.Request(BASE_URLS['prod']+path,method=method)
            validate_quote_request(request)

    def test_order_account_demo_host_and_unknown_methods_block(self):
        for host,path,method in [(BASE_URLS['prod'],'/uapi/overseas-stock/v1/trading/order','POST'),
             (BASE_URLS['vps'],US_QUOTE,'GET'),(BASE_URLS['prod'],'/uapi/overseas-stock/v1/trading/inquire-balance','GET'),
             (BASE_URLS['prod'],US_QUOTE,'POST')]:
            with self.subTest(path=path),patch('urllib.request.urlopen') as network:
                with self.assertRaises(ValueError):validate_quote_request(urllib.request.Request(host+path,method=method))
                network.assert_not_called()

    def test_outside_session_does_not_start_child_or_read_credentials(self):
        with tempfile.TemporaryDirectory() as temporary,patch('trading.demo_day_gate.today_session',return_value={'regular_now':False}),patch('subprocess.Popen') as child:
            with self.assertRaises(ValueError):
                with QuoteWatchProcess(Path(temporary)/'quotes'):pass
            child.assert_not_called()

    def test_child_is_stopped_on_context_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);process=Mock();process.poll.return_value=1
            with patch('trading.demo_day_gate.DATA_ROOT',root),patch('trading.demo_day_gate.today_session',return_value={'regular_now':True}),patch('subprocess.Popen',return_value=process):
                watcher=QuoteWatchProcess(root/'quotes')
                with self.assertRaises(ValueError):watcher.__enter__()
                self.assertTrue(watcher.log.closed)

    def test_close_targets_only_owned_child(self):
        watcher=QuoteWatchProcess(Path('unused'));watcher.process=Mock()
        watcher.process.poll.return_value=None
        watcher.close()
        watcher.process.terminate.assert_called_once()
        watcher.process.wait.assert_called_once_with(timeout=20)
