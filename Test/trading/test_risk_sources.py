"""공식 지원과 미확인 근거를 구분하는 합성 검사. 인증·외부 호출 없음."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace

from paths import CONFIG_ROOT
from trading.demo_profile import load_demo_profile
from trading.demo_readiness import (assess_readonly_inputs, assemble_risk_evidence,
    ingest_available_sources, resolve_available_sources, support)
from trading.orders import OrderManager
from Test.trading.risk_fixtures import evidence


class RiskSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.profile = json.loads((CONFIG_ROOT/'kis-demo-session.json').read_text(encoding='utf-8'))
        self.now = datetime.now(timezone.utc)

    def profile_file(self, **changes):
        p=self.folder/'profile.json';p.write_text(json.dumps({**self.profile, **changes}),encoding='utf-8');return p

    def test_profile_reads_tighter_limits_and_hashes_change(self):
        default=load_demo_profile()
        altered=load_demo_profile(self.profile_file(maximum_gross_buy_commitments_usd='200', maximum_buy_attempts=1))
        self.assertEqual(altered['maximum_buy_attempts'],1)
        self.assertNotEqual(default['limits_hash'],altered['limits_hash'])

    def test_profile_rejects_looser_wrong_mode_and_non_numeric_limits(self):
        for change in [{'maximum_buy_attempts':3},{'maximum_active_minutes':11},{'maximum_concurrent_shares':2},
                       {'maximum_gross_buy_commitments_usd':'NaN'},{'maximum_gross_buy_commitments_usd':'501'},
                       {'maximum_gross_buy_commitments_usd':'bad'},{'quantity':True}, {'environment':'prod'},
                       {'order_type':'MARKET'},{'new_orders_allowed':True}]:
            with self.subTest(change=change), self.assertRaises(ValueError):load_demo_profile(self.profile_file(**change))

    def test_explicit_official_unsupported_is_required(self):
        self.assertEqual(support({}), '미확인')
        self.assertEqual(support({'virtualTrId':'모의투자 미지원'}),'공식적으로 미지원')
        self.assertEqual(support({'virtualTrId':'VTTS3012R'}),'확인됨')

    def test_empty_history_cost_not_applicable_does_not_authorize_cash(self):
        result=assess_readonly_inputs({'history_complete':True,'history_stable':True,'filled_quantity':0,'buying_power':'100000'},[])
        self.assertTrue(result['historical_costs_not_applicable'])
        self.assertNotIn('final_fee_source_unproven',result['issues'])
        self.assertIsNone(result['observed_inputs']['execution_cash_usd'])
        self.assertFalse(result['new_orders_allowed'])
        self.assertFalse(result['pretrade_cost_policy']['final_fee_assumed'])

    def test_incomplete_history_and_existing_fill_do_not_remove_cost_requirement(self):
        for change in [{'history_complete':False,'filled_quantity':0},{'history_complete':True,'filled_quantity':1}]:
            result=assess_readonly_inputs({**change,'history_stable':True},[])
            self.assertIn('final_fee_source_unproven',result['issues'])

    def test_unsupported_output2_zero_is_not_cash(self):
        result=assess_readonly_inputs({'reported_usd_deposit_settlement_basis':'0','buying_power':'100000'},[],
            {'inquire-present-balance':{'apiSummary':'모의 output3만 정상 출력'}})
        self.assertEqual(result['statuses']['reported_deposit']['status'],'공식적으로 미지원')
        self.assertIsNone(result['observed_inputs']['initial_nav_usd'])

    def test_payload_mutation_and_old_evidence_are_detected(self):
        record={'operation':'query','at':(self.now-timedelta(minutes=1)).isoformat(),'payload':{'safe':'changed'},'sha256':'a'*64}
        result=assess_readonly_inputs({},[record],now=self.now)
        self.assertIn('source_payload_hash_mismatch',result['issues'])
        self.assertIn('source_observations_not_current',result['issues'])

    def manager_and_sources(self):
        manager=OrderManager(self.folder/'orders.sqlite','kis_demo');self.addCleanup(manager.close)
        manager.state['broker_identity']='synthetic-identity';manager.state['replay_only']=True
        e=evidence(manager,self.now)
        h=e['source_hashes']['fixture']
        source={'account_fingerprint':manager.state['broker_identity'],'mode':'kis_demo','cash':e['cash'],'nav':e['net_asset_value'],'as_of':e['as_of'],'window_start':e['window_start'],
                'source_times':e['source_times'],'source_hashes':e['source_hashes'],'fills':[],'cash_events':[], 'quotes':{},
                'source_kind':'synthetic','coverage':{key:{'from':e['window_start'],'through':e['as_of'],'complete':True} for key in e['complete']},
                'provenance':{key:{'origin':'synthetic_fixture','sha256':h,'currency':'USD','basis':basis} for key,basis in
                  {'cash':'execution_cash','nav':'usd_net_assets','fills':'executions','cash_events':'movements'}.items()}}
        normalized={'inventory':{'positions':{},'position_costs':{}},'observed_inputs':{'buying_power_usd':'9000'}}
        return manager,normalized,source

    def test_adapter_ingests_synthetic_evidence_into_replay_only_ledger(self):
        manager,normalized,source=self.manager_and_sources()
        proof=ingest_available_sources(manager,normalized,source)
        self.assertTrue(proof.eligible)
        result=manager.state['risk_ledger']['last_evaluation']
        self.assertEqual(result['initial'],'10000.000000')
        self.assertEqual(result['buying_power'],'9000.000000')
        self.assertTrue(manager.state['replay_only'])

    def test_source_coverage_gap_currency_and_hash_mismatch_block(self):
        manager,n,s=self.manager_and_sources()
        for kind in ['coverage','currency','hash','capacity','pending_fee']:
            value=copy.deepcopy(s)
            if kind=='coverage':value['coverage']['cash']['complete']=False
            if kind=='currency':value['provenance']['cash']['currency']='KRW'
            if kind=='hash':value['provenance']['cash']['sha256']='f'*64
            if kind=='capacity':value['provenance']['cash']['origin']='buying_power'
            if kind=='pending_fee':value['fills']=[{'fees_final':False}]
            with self.subTest(kind=kind),self.assertRaises(ValueError):assemble_risk_evidence(manager,n,value)

    def test_json_claim_cannot_masquerade_as_actual_account_capture(self):
        manager,n,s=self.manager_and_sources();s['source_kind']='kis_vps'
        with self.assertRaisesRegex(ValueError,'live_cash_source_capture_required'):assemble_risk_evidence(manager,n,s)

    def test_missing_source_does_not_create_risk_baseline(self):
        manager,n,s=self.manager_and_sources()
        with self.assertRaises(ValueError):ingest_available_sources(manager,n,None)
        self.assertFalse(manager.ready)
        self.assertNotIn('last_evaluation',manager.state.get('risk_ledger',{}))

    def test_unsupported_cash_path_never_fetches_or_approves(self):
        api=SimpleNamespace(records=[])
        result=resolve_available_sources(None,api,{}, {'foreign-margin':{'virtualTrId':'모의투자 미지원'}})
        self.assertIsNone(result['sources']);self.assertEqual(result['status'],'공식적으로 미지원')

    def test_new_support_label_alone_does_not_generate_cash(self):
        result=resolve_available_sources(None,SimpleNamespace(records=[]),{}, {'foreign-margin':{'virtualTrId':'VTEST'}})
        self.assertIsNone(result['sources']);self.assertEqual(result['reason'],'execution_cash_definition_not_in_contract')

    def test_evidence_from_another_account_or_mode_cannot_be_rebound(self):
        manager,n,s=self.manager_and_sources()
        for change in [{'account_fingerprint':'another-account'},{'mode':'live'}]:
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'account_or_mode'):
                assemble_risk_evidence(manager,n,{**s,**change})
