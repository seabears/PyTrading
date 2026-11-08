"""모의 잔고 원장 연결. 합성 응답·임시 SQLite만 사용하며 실제 인증은 없다."""
import copy
import json
import tempfile
import unittest
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from trading.orders import OrderManager
from trading.risk_ledger import RiskLedger, digest
from trading.demo_balance import connect_balance_observation, BALANCE, CAPACITY, PRESENT
from kis_demo_balance import validate_readonly_http, collect_and_connect


class DemoBalanceLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'orders.sqlite'
        self.manager = OrderManager(self.path, 'kis_demo', 'demo-balance-observation')
        self.addCleanup(lambda: self.manager.close())
        self.manager.state['broker_identity'] = 'synthetic-account'
        self.now = datetime.now(timezone.utc)
        self.records = []
        for exchange in ['NASD', 'NYSE', 'AMEX']:
            self.records.append(self.record(BALANCE, {'rt_cd': '0', 'output1': []},
                                            {'OVRS_EXCG_CD': exchange, 'TR_CRCY_CD': 'USD'}))
        self.records.append(self.record(PRESENT, {'rt_cd': '0', 'output3': {
            'tot_asst_amt': '338727500', 'frcr_evlu_tota': '338727500', 'tot_loan_amt': '0'}}))
        self.records.append(self.record(CAPACITY, {'rt_cd': '0', 'output': {
            'tr_crcy_cd': 'USD', 'ovrs_ord_psbl_amt': '100000', 'frcr_ord_psbl_amt1': '99000'}}))

    def record(self, operation, payload, context=None):
        return {'operation': operation, 'method': 'GET', 'environment': 'vps',
                'account_fingerprint': 'synthetic-account', 'at': self.now.isoformat(),
                'payload': payload, 'sha256': digest(payload), 'continuation': '',
                'request_context': context or {}}

    def connect(self):
        with patch('urllib.request.urlopen') as network:
            value = connect_balance_observation(self.manager, self.records, self.now)
            network.assert_not_called()
        return value

    def test_actual_shape_connects_capacity_without_inventing_usd_cash_or_nav(self):
        result = self.connect()
        self.assertTrue(result['ledger_connected'])
        value = result['observation']
        self.assertEqual(value['balance_snapshot']['reported_buying_power_usd'], '100000.000000')
        self.assertIsNone(value['execution_cash_usd'])
        self.assertIsNone(value['net_asset_value_usd'])
        self.assertIsNone(value['final_costs_usd'])
        self.assertFalse(value['risk_approved'])
        self.assertIsNone(value['balance_snapshot']['reported_aggregate_fields']['tot_asst_amt']['currency'])
        self.assertFalse(self.manager.ready)
        with self.assertRaises(ValueError):RiskLedger(self.manager).context()

    def test_identical_capture_is_idempotent_and_restart_preserves_evidence(self):
        first = self.connect();self.assertEqual(first['observation_id'], self.connect()['observation_id'])
        self.assertEqual(len(self.manager.state['risk_observations']), 1)
        self.manager.close()
        self.manager = OrderManager(self.path, 'kis_demo', 'demo-balance-observation')
        self.assertIn(first['observation_id'], self.manager.state['risk_observations'])
        self.assertFalse(self.manager.ready)

    def test_wrong_account_mode_hash_method_and_future_capture_fail_before_storage(self):
        for key, value in [('account_fingerprint', 'other'), ('environment', 'prod'),
                           ('sha256', '0' * 64), ('method', 'POST'),
                           ('at', (self.now + timedelta(seconds=1)).isoformat())]:
            records = copy.deepcopy(self.records);records[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                connect_balance_observation(self.manager, records, self.now)
        self.assertNotIn('risk_observations', self.manager.state)

    def test_old_real_capture_cannot_become_current_by_reading_it_again(self):
        with self.assertRaisesRegex(ValueError, 'stale'):
            connect_balance_observation(self.manager, self.records, self.now + timedelta(seconds=31))
        self.assertEqual(self.records[0]['at'], self.now.isoformat())

    def test_missing_exchange_unfinished_page_or_repeated_page_is_incomplete(self):
        for kind in ['missing', 'unfinished', 'repeat']:
            records = copy.deepcopy(self.records)
            if kind == 'missing':records.pop(0)
            elif kind == 'unfinished':records[0]['continuation'] = 'M'
            else:records.insert(0, copy.deepcopy(records[0]))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                connect_balance_observation(self.manager, records, self.now)

    def position(self):
        return {'ovrs_pdno': 'AAPL', 'ovrs_excg_cd': 'NASD', 'tr_crcy_cd': 'USD',
                'loan_type_cd': '10', 'loan_dt': '', 'ovrs_cblc_qty': '1', 'ord_psbl_qty': '1',
                'frcr_pchs_amt1': '100', 'ovrs_stck_evlu_amt': '101', 'frcr_evlu_pfls_amt': '1'}

    def with_positions(self, conflict=False):
        for index in [0, 1]:
            row = self.position()
            if conflict and index == 1:row['ovrs_cblc_qty'] = '2'
            self.records[index]['payload']['output1'] = [row]
            self.records[index]['sha256'] = digest(self.records[index]['payload'])

    def test_same_holding_returned_twice_is_not_two_shares(self):
        self.with_positions()
        value = self.connect()['observation']['balance_snapshot']
        self.assertEqual(value['duplicate_rows_ignored'], 1)
        self.assertEqual(value['positions'][0]['quantity'], 1)
        self.assertEqual(value['reported_holdings_value_usd'], '101.000000')

    def test_conflicting_duplicate_holding_never_partly_updates_ledger(self):
        self.with_positions(conflict=True)
        with self.assertRaisesRegex(ValueError, 'conflict'):self.connect()
        self.assertNotIn('risk_observations', self.manager.state)

    def test_unsupported_output2_never_supplies_cash(self):
        self.records[3]['payload']['output2'] = [{'crcy_cd': 'USD', 'frcr_dncl_amt_2': '999999'}]
        self.records[3]['sha256'] = digest(self.records[3]['payload'])
        self.assertIsNone(self.connect()['observation']['execution_cash_usd'])

    def test_nan_currency_and_missing_summary_are_rejected(self):
        for kind in ['nan', 'currency', 'missing']:
            records = copy.deepcopy(self.records)
            if kind == 'nan':records[-1]['payload']['output']['ovrs_ord_psbl_amt'] = 'NaN'
            elif kind == 'currency':records[-1]['payload']['output']['tr_crcy_cd'] = 'KRW'
            else:records.pop(3)
            for row in records:row['sha256'] = digest(row['payload'])
            with self.subTest(kind=kind), self.assertRaises((ValueError, ArithmeticError)):
                connect_balance_observation(self.manager, records, self.now)

    def test_storage_failure_keeps_orders_disabled(self):
        with patch.object(self.manager, '_save', side_effect=OSError('synthetic-disk')):
            with self.assertRaises(OSError):self.connect()
        self.assertFalse(self.manager.ready)
        self.assertIsNone(self.manager.state.get('account'))

    def test_http_guard_denies_orders_prod_and_unknown_requests(self):
        for url in ['https://openapivts.koreainvestment.com:29443/uapi/overseas-stock/v1/trading/order',
                    'https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance']:
            with patch('urllib.request.urlopen') as network:
                with self.assertRaises(ValueError):validate_readonly_http(urllib.request.Request(url, method='POST'))
                network.assert_not_called()
        request = urllib.request.Request('https://openapivts.koreainvestment.com:29443/uapi/overseas-stock/v1/trading/inquire-balance')
        self.assertEqual(validate_readonly_http(request)[0], 'GET')

    def test_collection_failure_does_not_store_partial_balance(self):
        adapter = Mock();adapter.query_present_balance.side_effect = ValueError('synthetic-response')
        api = Mock(records=[])
        with self.assertRaises(ValueError):collect_and_connect(self.manager, adapter, api)
        self.assertNotIn('risk_observations', self.manager.state)

    def test_entrypoint_passes_configured_exchange_to_adapter(self):
        from types import SimpleNamespace
        import kis_demo_balance as entry
        market = SimpleNamespace(identity='synthetic-identity', access_token='synthetic-token', authenticate=Mock())
        api = SimpleNamespace(secrets=('fake-account','fake-key'), records=[], allow_trading=False)
        folder = Path(self.temp.name)
        with patch.object(entry, 'DATA_ROOT', folder), \
             patch.object(entry, 'read_demo_identity', return_value=('fake-key','fake-secret','00000000','01')), \
             patch.object(entry, 'KisMarketClient', return_value=market), \
             patch.object(entry, 'ReadOnlyKisApi', return_value=api), \
             patch.object(entry, 'OrderManager', return_value=Mock()), \
             patch.object(entry, 'load_kis_settings', return_value={'us_exchanges':{'AAPL':'NAS'}}), \
             patch.object(entry, 'ManagedKisAdapter') as adapter, \
             patch.object(entry, 'collect_and_connect', return_value={'ledger_connected':True}):
            result = entry.run(folder/'unused.env',folder/'new.sqlite',folder/'output')
        self.assertEqual(adapter.call_args.args[4]['AAPL'], 'NASD')
        self.assertFalse(adapter.call_args.kwargs['enabled'])
        self.assertTrue(result['ledger_connected'])
