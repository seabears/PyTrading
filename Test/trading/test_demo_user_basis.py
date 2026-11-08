"""명시 허용된 빈 모의계좌 전방 기준. 합성 캡처·임시 원장·Mock HTTP만 사용."""
import copy,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch,Mock

from broker.demo_trial import TrialKisApi
from broker.managed_kis import ManagedKisAdapter
from trading.orders import OrderManager
from trading.demo_session import LimitedDemoSession
from trading.demo_profile import load_demo_profile
from trading.demo_user_basis import build_sources,trial_context,require_execution_basis,KIND
from trading.demo_readiness import resolve_available_sources,ingest_available_sources
from trading.demo_balance import connect_balance_observation,BALANCE,CAPACITY,PRESENT
from trading.user_cash import update_user_cash
from trading.buying_power import bind_api_buying_power
from trading.reconciliation import normalize_inventory,normalize_snapshot
from trading.risk_ledger import RiskLedger,digest
from Test.broker.test_kis_api import market_client


class UserTrialBasisTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'orders.sqlite'
        self.manager=OrderManager(self.path,'kis_demo');self.addCleanup(lambda:self.manager.close())
        self.api=TrialKisApi(market_client('vps'),'00000000')
        self.adapter=ManagedKisAdapter(self.api,self.manager,'00000000','01',{'AAPL':'NASD'},enabled=False)
        self.session=LimitedDemoSession(self.manager,self.adapter,'synthetic-user-basis','AAPL')
        self.api.trial_session=self.session;self.addCleanup(self.session.disarm)
        self.profile=load_demo_profile();self.now=datetime.now(timezone.utc)
        def record(operation,payload,context=None):
            return {'operation':operation,'method':'GET','environment':'vps','at':self.now.isoformat(),
                'account_fingerprint':self.manager.state['broker_identity'],'payload':payload,'sha256':digest(payload),
                'continuation':'','request_context':context or {}}
        history='overseas_stock.inquire_ccnl';period={'ORD_STRT_DT':(self.now-timedelta(days=2)).astimezone(ZoneInfo('America/New_York')).strftime('%Y%m%d'),'ORD_END_DT':self.now.astimezone(ZoneInfo('America/New_York')).strftime('%Y%m%d')}
        self.api.records=[record(history,{'rt_cd':'0','output':[]},period)]
        for exchange in ['NASD','NYSE','AMEX']:
            self.api.records.append(record(BALANCE,{'rt_cd':'0','output1':[]},{'OVRS_EXCG_CD':exchange,'TR_CRCY_CD':'USD'}))
        self.api.records.append(record(PRESENT,{'rt_cd':'0','output3':{'tot_loan_amt':'0'}}))
        self.api.records.append(record(CAPACITY,{'rt_cd':'0','output':{'tr_crcy_cd':'USD','ovrs_ord_psbl_amt':'100000','sll_ruse_psbl_amt':'0'}}))
        self.api.records.append(record(history,{'rt_cd':'0','output':[]},period))
        link=connect_balance_observation(self.manager,self.api.records)
        update_user_cash(self.manager,link,[],{'mode':'kis_demo','currency':'USD','cash_usd':'100000','source':'user_designation','authorized_on':'2026-11-02'})
        self.inventory=normalize_inventory([])
        self.normalized={'inventory':self.inventory,'query_started_at':self.now.isoformat(),
                         'history_window':{'start':(self.now-timedelta(days=2)).date().isoformat(),'end':self.now.date().isoformat()}}

    def resolve(self):return resolve_available_sources(self.manager,self.api,self.normalized,{},self.profile)

    def ready(self):
        resolution=self.resolve();self.assertIsNotNone(resolution['sources'])
        proof=ingest_available_sources(self.manager,self.normalized,resolution['sources'])
        power=bind_api_buying_power(self.manager,self.api.records[-2],self.inventory)
        snapshot=normalize_snapshot([],self.api.records[-2]['payload'],proof,[],buying_power_service='unknown',buying_power_evidence=power)
        self.manager.reconcile(snapshot,[],complete=True)
        return proof

    def test_real_shape_resolves_and_ingests_without_fake_official_flags(self):
        proof=self.ready();self.assertTrue(proof.eligible)
        value=self.manager.state['risk_ledger']['last_evaluation']
        self.assertEqual(value['source_kind'],KIND)
        self.assertFalse(value['broker_cash_verified']);self.assertFalse(value['past_cash_movements_verified'])
        self.assertFalse(self.adapter.api.allow_trading)

    def test_first_buy_full_stack_with_user_basis_uses_mock_vps_only(self):
        self.ready();stamp=datetime.now(timezone.utc).isoformat()
        recovery={'regular_recovery_verified':True,'input_kind':'live_observation','checked_at':stamp,
                  'diagnostics':[],'per_symbol':{'AAPL':{'continuous':True}}}
        response=Mock();response.status=200;response.headers={};response.read.return_value=b'{"rt_cd":"0","output":{"ODNO":"123"}}'
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with patch('trading.demo_session.regular_session',return_value={'end':datetime.now(timezone.utc)+timedelta(hours=1)}),patch('urllib.request.urlopen',return_value=response) as network:
            self.session.arm(recovery)
            self.session.create('test-buy','BUY',1,'100','98',stamp)
            self.session.submit('test-buy')
        self.assertEqual(network.call_count,1)
        self.assertIn('openapivts.koreainvestment.com',network.call_args.args[0].full_url)
        self.assertEqual(self.manager.state['orders']['test-buy']['status'],'ACCEPTED')
        self.assertEqual(self.session.state['buy_attempts'],1)

    def test_source_cannot_be_rebound_or_json_forged(self):
        sources=build_sources(self.manager,self.api,self.normalized,self.profile)
        self.manager._user_trial_binding=None
        with self.assertRaises(ValueError):ingest_available_sources(self.manager,self.normalized,sources)

    def test_owned_limit_type_can_be_recovered_but_manual_type_is_not_inferred(self):
        from trading.demo_user_basis import normalize_owned_history
        order={'id':'own','broker_id':'20261102:000123','symbol':'AAPL','side':'BUY','quantity':1,'price':'100','order_type':'LIMIT','filled':0,'status':'CANCELLED'}
        self.manager.state['orders']['own']=order;self.session.state['order_ids']=['own']
        row={'ord_dt':'20261102','odno':'123','orgn_odno':'0000','ft_ord_qty':'1','ft_ccld_qty':'0','nccs_qty':'0',
             'tr_crcy_cd':'USD','prcs_stat_name':'취소완료','rjct_rson':'0','sll_buy_dvsn_cd':'02','pdno':'AAPL','ft_ord_unpr3':'100','ft_ccld_amt3':'0'}
        result=normalize_owned_history(self.manager,[row]);self.assertEqual(result[0]['order_type'],'LIMIT')
        for index in [0,-1]:
            self.api.records[index]['payload']['output']=[row]
            self.api.records[index]['sha256']=digest(self.api.records[index]['payload'])
        self.assertIsNotNone(self.resolve()['sources'])
        row['ft_ord_unpr3']='101'
        with self.assertRaises(ValueError):normalize_owned_history(self.manager,[row])
        self.session.state['order_ids']=[]
        self.assertEqual(normalize_owned_history(self.manager,[row])[0]['order_type'],'UNKNOWN')

    def test_immutable_trial_budget_is_enforced_outside_mutable_session_limits(self):
        self.ready()
        order={'id':'oversize','symbol':'AAPL','side':'BUY','quantity':1,'price':'500','filled':0}
        with self.assertRaises(ValueError):require_execution_basis(self.manager,order=order)

    def test_persisted_source_does_not_survive_restart_without_capture(self):
        self.ready();self.manager.close();self.manager=OrderManager(self.path,'kis_demo')
        with self.assertRaises(ValueError):RiskLedger(self.manager).context()

    def test_wrong_account_stale_capture_hash_and_page_gaps_fail(self):
        original=copy.deepcopy(self.api.records)
        for key,value in [('account_fingerprint','other'),('sha256','f'*64),('continuation','M'),
                           ('at',(self.now-timedelta(seconds=31)).isoformat())]:
            self.api.records=copy.deepcopy(original);self.api.records[-1][key]=value
            with self.subTest(key=key):self.assertIsNone(self.resolve()['sources'])

    def test_existing_holdings_fill_cost_or_active_order_blocks(self):
        self.normalized['inventory']['positions']={'AAPL':1}
        self.assertIsNone(self.resolve()['sources']);self.normalized['inventory']['positions']={}
        self.manager.state['user_cash_account']['orders']={'known':{'filled':1}}
        self.assertIsNone(self.resolve()['sources']);self.manager.state['user_cash_account']['orders']={}
        self.manager.state['orders']['unknown']={'status':'UNKNOWN'}
        self.assertIsNone(self.resolve()['sources'])

    def test_loan_or_sell_reuse_missing_or_nonzero_blocks(self):
        record=self.api.records[-2]
        for value in ['1',None]:
            if value is None:record['payload']['output'].pop('sll_ruse_psbl_amt')
            else:record['payload']['output']['sll_ruse_psbl_amt']=value
            record['sha256']=digest(record['payload'])
            self.assertIsNone(self.resolve()['sources'])

    def test_halt_restore_or_replay_never_waived(self):
        for key in ['restore_gate','replay_only']:
            self.manager.state[key]=True;self.assertIsNone(self.resolve()['sources']);self.manager.state.pop(key)
        self.manager.state['risk_ledger']={'days':{'day':{'halted':True}}}
        self.assertIsNone(self.resolve()['sources'])

    def test_user_basis_cannot_be_used_outside_limited_session(self):
        self.ready();self.manager.state['limited_demo_session']['id']='other'
        with self.assertRaises(ValueError):require_execution_basis(self.manager)

    def test_evaluation_tampering_and_policy_change_rejected(self):
        self.ready();self.manager.state['risk_ledger']['last_evaluation']['cash_balance']='999999'
        with self.assertRaises(ValueError):trial_context(self.manager)

    def test_profile_cannot_expand_or_use_prod(self):
        from trading.demo_profile import validate_trial_basis
        for change in [{'maximum_gross_buy_commitments_usd':'501'},{'quantity':2},{'environment':'prod'},
                       {'risk_basis_authorized_on':None}]:
            with self.assertRaises(ValueError):validate_trial_basis({**self.profile,**change})

    def test_first_fill_prevents_second_buy_and_does_not_reset_basis(self):
        self.ready();baseline=copy.deepcopy(self.manager.state['risk_ledger']['baseline'])
        self.manager.state['user_cash_account']['orders']={'fill':{'filled':1}}
        self.assertIsNone(self.resolve()['sources'])
        self.assertEqual(baseline,self.manager.state['risk_ledger']['baseline'])
        with self.assertRaises(ValueError):trial_context(self.manager)

    def test_save_failure_cannot_leave_an_usable_proof(self):
        sources=self.resolve()['sources']
        with patch.object(self.manager,'_save',side_effect=OSError('synthetic-storage')):
            with self.assertRaises(OSError):ingest_available_sources(self.manager,self.normalized,sources)
        self.assertFalse(self.manager.ready)
        with self.assertRaises((ValueError,KeyError)):trial_context(self.manager)
