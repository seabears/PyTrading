"""삭제한 재무 API의 함수·목록·캐시·직접 HTTP 우회를 검사한다. 실제 호출 없음."""
import json
import unittest
from unittest.mock import Mock, patch
from broker.kis import KisApiError
from broker.kis_api import domestic_stock, ApiRequest, KisApiClient
from broker.kis_api.client import load_catalog
from broker.kis_api.removed_finance import REMOVED_FINANCE_NAMES, REMOVED_FINANCE_PATHS
from paths import FIXTURES_ROOT


class RemovedFinanceTests(unittest.TestCase):
    def test_functions_catalog_and_contract_vectors_removed(self):
        catalog = load_catalog()
        vectors = json.loads((FIXTURES_ROOT/'kis-api-vectors.json').read_text(encoding='utf-8'))['vectors']
        self.assertEqual(len(REMOVED_FINANCE_NAMES), 7)
        self.assertEqual(len(catalog), 323)
        for name in REMOVED_FINANCE_NAMES:
            self.assertFalse(hasattr(domestic_stock, name.split('.')[1]))
            self.assertNotIn(name, catalog)
            self.assertFalse(any(row['name']==name for row in vectors))
        self.assertTrue(callable(domestic_stock.finance_ratio))
        self.assertTrue(catalog['domestic_stock.finance_ratio']['enabled'])

    def test_stale_cached_operation_blocked_before_authentication(self):
        market = Mock(environment='prod', request_interval=.2)
        api = KisApiClient(market)
        with patch.object(api, '_http') as network:
            for name in REMOVED_FINANCE_NAMES:
                path = '/uapi/domestic-stock/v1/finance/'+name.split('finance_',1)[1].replace('_','-')
                api.catalog[name] = {'name':name,'enabled':True}
                with self.assertRaises(KisApiError):
                    api.execute(ApiRequest(name,path,'REMOVED',{}))
        market.authenticate.assert_not_called()
        network.assert_not_called()

    def test_direct_transport_blocks_all_removed_paths(self):
        api = KisApiClient(Mock(environment='prod', request_interval=.2))
        with patch('broker.kis_api.client.urllib.request.urlopen') as network:
            for path in REMOVED_FINANCE_PATHS:
                for spelling in (path,path+'/',path.replace('balance-sheet','%62alance-sheet')):
                    with self.assertRaises(KisApiError):api._http(spelling,{},'GET')
        network.assert_not_called()
