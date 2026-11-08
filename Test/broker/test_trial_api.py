"""한정 전송 경계의 합성 검사. 네트워크·인증 파일 사용 안 함."""
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from broker.demo_trial import TrialKisApi
from broker.kis_api.client import KisApiError
from Test.broker.test_kis_api import market_client, sample_request


class TrialApiTests(unittest.TestCase):
    def test_default_post_and_low_level_post_never_reach_http(self):
        api=TrialKisApi(market_client('vps'),'00000000')
        with patch('urllib.request.urlopen') as network:
            with self.assertRaises(KisApiError):api.execute(sample_request('POST','demo'))
            with self.assertRaises(KisApiError):api._http('/uapi/overseas-stock/v1/trading/order',{},'POST',order=True)
            network.assert_not_called()

    def test_prod_instance_is_rejected(self):
        with self.assertRaises(ValueError):TrialKisApi(market_client('prod'),'00000000')

    def test_managed_permission_does_not_replace_trial_scope(self):
        api=TrialKisApi(market_client('vps'),'00000000');api.allow_trading=True
        with patch('urllib.request.urlopen') as network:
            with self.assertRaisesRegex(KisApiError,'session_scope'):
                api.execute_managed(sample_request('POST','demo'),Mock(),'not-owned')
            network.assert_not_called()

    def test_changed_trial_scope_is_rejected(self):
        api=TrialKisApi(market_client('vps'),'00000000');manager=Mock()
        api.trial_session=SimpleNamespace(manager=manager,state={'order_ids':['own']})
        with self.assertRaisesRegex(KisApiError,'session_scope'):
            api.execute_managed(sample_request('POST','demo'),manager,'other')

    def test_deadline_and_operator_stop_block_before_http(self):
        import time
        api=TrialKisApi(market_client('vps'),'00000000')
        api.execution_deadline=time.monotonic()-1
        with patch('urllib.request.urlopen') as network:
            with self.assertRaisesRegex(KisApiError,'deadline_or_stop'):api.execute(sample_request())
            network.assert_not_called()
        api.execution_deadline=time.monotonic()+100;api.execution_stop_requested=lambda:True
        with self.assertRaisesRegex(KisApiError,'deadline_or_stop'):api.execute(sample_request())
