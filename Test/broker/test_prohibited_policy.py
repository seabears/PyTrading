"""금지 정책의 합성 회귀 검사. 실제 인증·네트워크·운영 원장을 사용하지 않는다."""
import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from broker.kis import KisApiError, KisMarketClient
from broker.kis_api import KisApiClient, overseas_stock, overseas_stock_ws
from broker.kis_api.websocket import KisStreamSession
from broker.product_policy import load_product_rules, validate_symbol
from paths import CONFIG_ROOT
from trading.cash_service_policy import require_cash_only, require_usd_funding
from trading.demo_account import select_buying_power
from trading.demo_profile import load_demo_profile
from trading.orders import OrderManager
from trading.risk_ledger import RiskLedger
from Test.trading.cash_policy_fixtures import confirm_cash_only
from Test.trading.risk_fixtures import evidence, seed_risk, snapshot


class ProhibitedPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'orders.sqlite'
        self.manager = OrderManager(self.path, 'kis_demo')
        self.addCleanup(lambda: self.manager.close())
        self.manager.state['broker_identity'] = 'synthetic-account'
        self.market = Mock(environment='vps', app_key='synthetic', app_secret='synthetic',
                           access_token='synthetic', request_interval=.2, next_request_at=0)
        self.api = KisApiClient(self.market, allow_trading=True)

    def blocked(self, action, error=(ValueError, KisApiError)):
        """전송 함수를 계수한다. 누락된 예외·전송 발생은 실제 검사 실패로 남긴다."""
        with patch('urllib.request.urlopen') as transport:
            with self.assertRaises(error):
                action()
            self.assertEqual(transport.call_count, 0)
        target = os.environ.get('PYTRADING_POLICY_CASE_LOG')
        if target:
            with open(target, 'a', encoding='utf-8') as output:
                output.write(json.dumps({'test': self.id(), 'kind': 'synthetic',
                                         'transport_calls': transport.call_count}) + '\n')

    def test_integrated_profile_rejected(self):
        profile = json.loads((CONFIG_ROOT / 'kis-demo-session.json').read_text(encoding='utf-8'))
        profile['buying_power_service'] = 'integrated'
        path = Path(self.temp.name) / 'profile.json'
        path.write_text(json.dumps(profile), encoding='utf-8')
        self.blocked(lambda: load_demo_profile(path))

    def test_unknown_and_cash_setting_do_not_require_enrollment_status(self):
        for service in ('unknown', 'cash_only'):
            self.manager.state['requested_cash_service'] = service
            self.assertFalse(require_cash_only(self.manager)['account_enrollment_status_required'])
        self.manager.state['requested_cash_service'] = 'integrated'
        self.blocked(lambda: require_cash_only(self.manager))

    def test_capacity_ignores_integrated_amount_and_does_not_certify_cash(self):
        payload = {'output': {'tr_crcy_cd': 'USD', 'ovrs_ord_psbl_amt': '100',
                              'frcr_ord_psbl_amt1': '999999'}}
        for service in ('unknown', 'cash_only'):
            selected = select_buying_power(payload, service)
            self.assertEqual(selected['amount'], '100.000000')
            self.assertEqual(selected['field'], 'ovrs_ord_psbl_amt')
            self.assertFalse(selected['account_enrollment_status_checked'])
        self.blocked(lambda: select_buying_power(payload, 'integrated'))

    def test_historical_status_flags_do_not_block_usd_policy(self):
        for state in ('integrated', 'unknown', 'cash_only'):
            self.manager.state['cash_service_evidence'] = {'status':state}
            self.assertFalse(require_cash_only(self.manager)['account_enrollment_status_required'])

    def test_no_capture_or_enrollment_proof_is_created(self):
        require_cash_only(self.manager)
        self.assertNotIn('cash_service_evidence', self.manager.state)

    def test_unknown_status_does_not_prevent_otherwise_valid_risk_ingest(self):
        proof = RiskLedger(self.manager).ingest(evidence(self.manager, source_kind='kis_vps'))
        self.assertTrue(proof.eligible)

    def test_restart_does_not_require_enrollment_recapture(self):
        self.manager.close()
        self.manager = OrderManager(self.path, 'kis_demo')
        self.assertFalse(require_cash_only(self.manager)['account_enrollment_status_required'])

    def test_unknown_setting_allows_valid_usd_cash_bounded_intent(self):
        proof = seed_risk(self.manager, source_kind='kis_vps')
        self.manager.state['account'] = snapshot(proof)
        self.manager.ready = True
        self.manager.state['requested_cash_service'] = 'unknown'
        with patch('urllib.request.urlopen') as transport:
            self.manager.create('new', 'AAPL', 'BUY', 1, '100', '98', datetime.now(timezone.utc).isoformat())
            self.assertEqual(transport.call_count, 0)
        self.assertEqual(self.manager.state['orders']['new']['status'], 'INTENT')

    def test_usd_cash_cap_independent_of_larger_api_budget(self):
        self.manager.state['risk_ledger'] = {'last_evaluation': {'cash_balance': '100'}}
        order = {'id':'new','side':'BUY','quantity':1,'filled':0,'price':'100'}
        with patch.object(RiskLedger,'validate_snapshot'):
            self.blocked(lambda: require_usd_funding(self.manager, order))
            result = require_usd_funding(self.manager, {**order,'price':'90'})
        self.assertEqual(result['required_usd'], '90.270000000')

    def test_remote_reserve_counts_once_in_cash_cap_not_api_budget(self):
        self.manager.state['risk_ledger'] = {'last_evaluation': {'cash_balance': '200'}}
        reserved = {'id':'remote','side':'BUY','quantity':1,'filled':0,'price':'100',
                    'status':'ACCEPTED','broker_id':'20261101:123'}
        self.manager.state['orders'] = {'remote':reserved}
        order = {**reserved,'id':'new','price':'100'}
        with patch.object(RiskLedger,'validate_snapshot'):
            self.blocked(lambda: require_usd_funding(self.manager, order))
            result = require_usd_funding(self.manager, {**order,'price':'90'})
        self.assertEqual(result['reserved_usd'], '100.300000000')

    def test_unverified_or_stale_cash_still_blocks(self):
        order = {'id':'new','side':'BUY','quantity':1,'filled':0,'price':'1'}
        self.blocked(lambda: require_usd_funding(self.manager, order))

    def test_raw_managed_permission_cannot_bypass_transport_policy(self):
        self.api._managed_permission = True
        self.blocked(lambda: self.api._http('/uapi/overseas-stock/v1/trading/order',
                                            {'PDNO': 'AAPL'}, 'POST'))
        self.market._wait.assert_not_called()

    def test_managed_adapter_unknown_account_blocks_before_http_and_auth(self):
        from broker.managed_kis import ManagedKisAdapter
        self.manager.state.pop('broker_identity')
        adapter = ManagedKisAdapter(self.api, self.manager, '00000000', '01', {'AAPL': 'NASD'}, enabled=True)
        self.manager.ready = True
        order = {'id': 'new', 'symbol': 'AAPL', 'side': 'BUY', 'quantity': 1,
                 'price': '100', 'status': 'SENDING', 'order_type': 'LIMIT'}
        self.manager.state['orders']['new'] = order
        for service in ('unknown', 'cash_only', 'integrated'):
            with self.subTest(service=service):
                self.manager.state['requested_cash_service'] = service
                self.blocked(lambda: adapter.submit(order))
        self.market.authenticate.assert_not_called()

    def test_expiry_during_rate_wait_blocks_immediate_transport(self):
        # 전송 바로 전 검사까지 실제 실행한다. 다른 위험 계약은 별도 회귀에서 검사한다.
        confirm_cash_only(self.manager)
        self.api._managed_permission = True
        def validate(path, parameters):
            require_cash_only(self.manager)
        def change_status():
            self.manager.state['requested_cash_service'] = 'integrated'
        self.market._wait.side_effect = change_status
        with patch.object(self.api, '_enforce_managed_policy', side_effect=validate) as guard:
            self.blocked(lambda: self.api._http('/uapi/overseas-stock/v1/trading/order',
                                                {'PDNO': 'AAPL'}, 'POST'))
        self.assertEqual(guard.call_count, 2)

    def rules_for(self, item):
        rules = copy.deepcopy(load_product_rules())
        rules['verified_instruments']['SYNTHETIC'] = item
        return rules

    def test_futures_and_unknown_etf_block_all_transport_paths(self):
        self.market.environment = 'prod'
        for item in ({'asset_type': 'etf', 'futures_based': True},
                     {'asset_type': 'etf', 'futures_based': True, 'leverage': 2},
                     {'asset_type': 'etf', 'futures_based': True, 'inverse': True},
                     {'asset_type': 'etf'}, {'asset_type': 'etf', 'futures_based': False}):
            with self.subTest(item=item), patch('broker.product_policy.load_product_rules',
                                                 return_value=self.rules_for(item)):
                self.blocked(lambda: self.api.execute(overseas_stock.price('', 'NAS', 'SYNTHETIC')))
                self.blocked(lambda: self.api._http('/uapi/overseas-price/v1/quotations/price',
                                                    {'SYMB': 'SYNTHETIC'}, 'GET'))
                legacy = KisMarketClient('synthetic', 'synthetic')
                self.blocked(lambda: legacy.get('/uapi/overseas-price/v1/quotations/inquire-asking-price',
                                                {'SYMB': 'SYNTHETIC'}))
                socket = Mock()
                session = KisStreamSession(self.api, socket, 'synthetic')
                self.blocked(lambda: session.send(overseas_stock_ws.asking_price('1', 'DNASSYNTHETIC')))
                socket.send.assert_not_called()
        self.market.authenticate.assert_not_called()

    def test_registered_etf_reviews_and_unchanged_stock_bond_policy(self):
        rules = load_product_rules()
        validate_symbol('AAPL', rules)
        validate_symbol('SPY', rules)
        validate_symbol('069500', rules)
        rules['verified_instruments']['SYNTHETIC'] = {'asset_type': 'bond'}
        validate_symbol('SYNTHETIC', rules)

    def test_false_flag_without_bound_official_review_is_insufficient(self):
        item = copy.deepcopy(load_product_rules()['verified_instruments']['SPY'])
        variants = [copy.deepcopy(item) for _ in range(3)]
        variants[0]['futures_review']['symbol'] = 'SYNTHETIC'
        variants[0]['futures_review']['source']['sha256'] = ''
        variants[1]['futures_review']['checked_on'] = '9999-12-31'
        variants[2]['futures_review']['source']['kind'] = 'guess_by_name'
        for value in variants:
            self.blocked(lambda: validate_symbol('SYNTHETIC', self.rules_for(value)))

    def test_allowed_read_only_query_has_no_account_permission_requirement(self):
        from broker.kis_api.models import ApiResponse
        self.api.allow_trading = False
        self.market.environment = 'prod'
        with patch.object(self.api, '_http', return_value=ApiResponse({'rt_cd': '0', 'output': {}})) as http:
            self.api.execute(overseas_stock.price('', 'NAS', 'AAPL'))
        http.assert_called_once()
        self.assertEqual(http.call_args.args[2], 'GET')


class Kodex200UserExceptionTests(unittest.TestCase):
    def test_user_exception_preserves_unknown_futures_evidence(self):
        rules = load_product_rules()
        item = rules['verified_instruments']['069500']
        self.assertIsNone(item['futures_based'])
        self.assertEqual(item['futures_review']['status'], 'unknown')
        self.assertEqual(item['policy_exception']['authority'], 'user_explicit_instruction')
        validate_symbol('069500', rules)

    def test_exception_cannot_be_copied_to_another_etf_or_etn(self):
        rules = copy.deepcopy(load_product_rules())
        item = copy.deepcopy(rules['verified_instruments']['069500'])
        rules['verified_instruments']['SYNTHETIC'] = item
        with self.assertRaises(KisApiError):validate_symbol('SYNTHETIC', rules)
        rules['verified_instruments']['069500']['asset_type'] = 'etn'
        with self.assertRaises(KisApiError):validate_symbol('069500', rules)

    def test_missing_authorization_or_confirmed_futures_stays_blocked(self):
        for change in ('remove_authority', 'confirmed_futures'):
            rules = copy.deepcopy(load_product_rules())
            item = rules['verified_instruments']['069500']
            if change == 'remove_authority':item['policy_exception'].pop('authority')
            else:item['futures_based'] = True
            with self.subTest(change=change), self.assertRaises(KisApiError):
                validate_symbol('069500', rules)
