"""기존 전략 수량의 최초 모의진입: 합성 원본/Mock 전송과 실제 API를 구분한다."""
import copy,json,unittest
from unittest.mock import Mock,patch
from pathlib import Path
from datetime import datetime,timezone
def fixture_factory():
    from Test.trading.test_demo_user_basis import UserTrialBasisTests
    return UserTrialBasisTests()
from Test.broker.test_kis_api import market_client
from broker.strategy_execution import ManagedStrategyApi
from broker.managed_kis import ManagedKisAdapter
from trading.execution import load_execution
from trading.strategy_model_basis import build_sources,ingest,context,KIND
from trading.demo_readiness import resolve_available_sources,ingest_available_sources
from trading.risk_ledger import RiskLedger,digest
from trading.buying_power import bind_api_buying_power
from trading.reconciliation import normalize_snapshot


class StrategyModelBasisTests(unittest.TestCase):
    def setUp(self):
        # 기존 캡처 생성기를 재사용하며 원장과 cleanup은 각 사례마다 격리한다.
        fixture=fixture_factory();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.manager=fixture.manager;self.normalized=fixture.normalized;self.inventory=fixture.inventory
        saved=self.manager.state.pop('limited_demo_session')
        self.addCleanup(lambda:self.manager.state.setdefault('limited_demo_session',saved))
        self.manager.state['alias']='strategies'
        path=Path(fixture.temp.name)/'execution.json'
        path.write_text(json.dumps({'internal_paper':{'enabled':False},'kis_demo':{'enabled':True,'credentials_file':'demo.env'},'live':{'enabled':False,'credentials_file':'live.env'}}))
        selected=load_execution(path);self.manager._strategy_execution_selection=selected
        self.api=ManagedStrategyApi(market_client('vps'),'00000000');self.api.records=copy.deepcopy(fixture.api.records)
        self.api._execution_selection=selected
        self.adapter=ManagedKisAdapter(self.api,self.manager,'00000000','01',{'AAPL':'NASD'})
        self.profile={'risk_basis':KIND}
    def resolve(self):return resolve_available_sources(self.manager,self.api,self.normalized,{},self.profile)
    def ready(self):
        source=self.resolve()['sources'];self.assertIsNotNone(source)
        proof=ingest_available_sources(self.manager,self.normalized,source)
        power=bind_api_buying_power(self.manager,self.api.records[-2],self.inventory)
        snapshot=normalize_snapshot([],self.api.records[-2]['payload'],proof,[],buying_power_service='unknown',buying_power_evidence=power)
        self.manager.reconcile(snapshot,[],complete=True);return proof
    def test_current_empty_capture_builds_model_not_official_cash_proof(self):
        self.assertTrue(self.ready().eligible)
        evaluation=self.manager.state['risk_ledger']['last_evaluation']
        self.assertEqual(evaluation['source_kind'],KIND)
        self.assertFalse(evaluation['broker_cash_verified']);self.assertFalse(evaluation['past_cash_movements_verified'])
    def test_original_quantity_over_trial_cap_uses_mock_vps_and_not_paper_fill(self):
        self.ready();at=datetime.now(timezone.utc).isoformat()
        order=self.manager.create('strategy-entry','AAPL','BUY',17,'100','97',at)
        order['strategy_owner']='strategy-test';self.manager._save()
        response=Mock();response.status=200;response.headers={};response.read.return_value=b'{"rt_cd":"0","output":{"ODNO":"123"}}'
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        self.adapter.enabled=True;self.api.allow_trading=True
        with patch('broker.sessions.regular_session',return_value={'id':'US:2026-11-02'}),patch('urllib.request.urlopen',return_value=response) as network:
            self.manager.dispatch(order['id'],self.adapter)
        self.assertEqual(network.call_count,1);self.assertIn('openapivts',network.call_args.args[0].full_url)
        self.assertEqual(order['quantity'],17);self.assertEqual(order['status'],'ACCEPTED');self.assertEqual(order['filled'],0)
    def test_no_runtime_binding_no_source(self):
        self.manager._strategy_execution_selection=None;self.assertIsNone(self.resolve()['sources'])
    def test_persisted_context_does_not_rearm_after_restart(self):
        self.ready();self.manager._strategy_evaluation_binding=None
        with self.assertRaises(ValueError):RiskLedger(self.manager).context()
    def test_payload_hash_account_or_age_tampering_blocks(self):
        self.api.records[-1]['account_fingerprint']='wrong';self.assertIsNone(self.resolve()['sources'])
    def test_actual_holdings_require_separate_posttrade_evidence(self):
        self.normalized['inventory']['positions']={'AAPL':1};self.assertIsNone(self.resolve()['sources'])
    def test_missing_or_nonzero_sell_reuse_blocks(self):
        for value in [None,'100']:
            output=self.api.records[-2]['payload']['output']
            if value is None:output.pop('sll_ruse_psbl_amt',None)
            else:output['sll_ruse_psbl_amt']=value
            self.api.records[-2]['sha256']=digest(self.api.records[-2]['payload'])
            self.assertIsNone(self.resolve()['sources'])
    def test_loan_nonzero_blocks(self):
        row=self.api.records[-3];row['payload']['output3']['tot_loan_amt']='1';row['sha256']=digest(row['payload'])
        self.assertIsNone(self.resolve()['sources'])
    def test_pending_costs_do_not_become_zero(self):
        self.manager.state['user_cash_account']['orders_with_costs_pending']=['fill']
        self.assertIsNone(self.resolve()['sources'])
    def test_first_fill_blocks_new_buy_context_without_final_costs(self):
        self.ready();self.manager.state['orders']['filled']={'filled':1}
        with self.assertRaisesRegex(ValueError,'posttrade'):context(self.manager)
    def test_existing_halt_not_cleared(self):
        self.manager.state['risk_ledger']={'days':{'2026-11-02':{'halted':True}}}
        self.assertIsNone(self.resolve()['sources']);self.assertTrue(self.manager.state['risk_ledger']['days']['2026-11-02']['halted'])
    def test_restore_gate_not_waived(self):
        self.manager.state['restore_gate']={'pending':True};self.assertIsNone(self.resolve()['sources'])
    def test_source_cannot_be_forged_from_json(self):
        source=build_sources(self.manager,self.api,self.normalized);self.manager._strategy_sources_binding=None
        with self.assertRaises(ValueError):ingest(self.manager,source)
    def test_configuration_disable_invalidates_proof(self):
        self.ready();path=self.manager._strategy_execution_selection['path'];values=json.loads(path.read_text());values['kis_demo']['enabled']=False;path.write_text(json.dumps(values))
        with self.assertRaises(ValueError):context(self.manager)

    def test_unknown_cash_change_cannot_be_hidden_by_designated_initial_amount(self):
        row=self.api.records[-2];row['payload']['output']['ovrs_ord_psbl_amt']='120000';row['sha256']=digest(row['payload'])
        self.assertIsNone(self.resolve()['sources'])
