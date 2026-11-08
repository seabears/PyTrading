"""체결 모드 선택·전략 수량 보존·가상/실제 체결 분리. 외부 요청은 사용하지 않는다."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from types import SimpleNamespace
from trading.execution import load_execution,strategy_path,configure_account,ExecutionAccount
from execution_mode import select_mode
from paths import DATA_ROOT


class SignalAccount:
    def __init__(self,path):
        self.path=path;self.settings={'buy_cost_ratio':0.001}
        self.state={'cash':{'US':10000},'positions':{},'trades':[],'last_processed_at':{},'quote_times':{},'last_prices':{}}
        self.action='BUY';self.fail_save=False
    def save(self):
        if self.fail_save:raise OSError('synthetic save failure')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(json.dumps(self.state),encoding='utf-8')
    def evaluate_snapshot(self,snapshot,strategy=None):
        if self.action=='HOLD':return {'action':'HOLD','reason':'original_strategy_holding'}
        trade={'action':self.action,'quantity':17,'reason':'original_strategy','price':100,'fees':7}
        self.state['cash']['US']=8300;self.state['positions']['US:NVDA']={'quantity':17};self.state['trades'].append(trade)
        self.save();return {'action':self.action,'reason':'original_strategy','paper_fill':trade}
    def observe_quote(self,snapshot):return self.evaluate_snapshot(snapshot)


class ExecutionModeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name);self.config=self.folder/'execution.json'
        self.values={'internal_paper':{'enabled':False},'kis_demo':{'enabled':True,'credentials_file':'../Credentials/demo.env'},'live':{'enabled':False,'credentials_file':'../Credentials/live.env'}}
        self.write();self.selection=load_execution(self.config)
        self.data_patch=patch('trading.execution.DATA_ROOT',self.folder);self.data_patch.start();self.addCleanup(self.data_patch.stop)
        self.account=SignalAccount(self.folder/'account.json')
        self.port=Mock();self.port.sync.return_value={'observation_valid':True}
        self.port.submit.return_value={'status':'ACCEPTED','reason':'broker_acceptance_is_not_fill'}
        self.snapshot={'market':'US','symbol':'NVDA','now':'2026-11-02T15:00:00+00:00','source':'kis','data_mode':'live_observation',
                       'regular_session_open':True,'quote':{'available_at':'2026-11-02T15:00:00+00:00','ask':100,'bid':99.99},'bars':[{'end':'2026-11-02T14:55:00+00:00'}]}
    def write(self):self.config.write_text(json.dumps(self.values),encoding='utf-8')
    def wrapped(self):return configure_account(self.account,self.selection,port=self.port)
    def test_only_one_mode_can_be_enabled(self):
        self.values['internal_paper']['enabled']=True;self.write()
        with self.assertRaisesRegex(ValueError,'only_one'):load_execution(self.config)
    def test_bool_required_not_number_or_string(self):
        for value in [1,0,'true',None]:
            self.values['kis_demo']['enabled']=value;self.write()
            with self.assertRaises(ValueError):load_execution(self.config)
    def test_missing_or_unknown_keys_rejected(self):
        self.values['unexpected']={};self.write()
        with self.assertRaises(ValueError):load_execution(self.config)
    def test_all_disabled_means_no_fill_and_no_transport(self):
        self.values['kis_demo']['enabled']=False;self.write();self.selection=load_execution(self.config)
        before=copy.deepcopy(self.account.state);wrapped=self.wrapped();result=wrapped.evaluate_snapshot(self.snapshot)
        self.assertEqual(result['reason'],'execution_disabled');self.port.submit.assert_not_called();self.port.sync.assert_not_called()
        for key in ['cash','positions','trades']:self.assertEqual(self.account.state[key],before[key])
    def test_internal_mode_returns_existing_account_unchanged(self):
        self.values['kis_demo']['enabled']=False;self.values['internal_paper']['enabled']=True;self.write()
        self.assertIs(configure_account(self.account,load_execution(self.config)),self.account)
    def test_strategy_quantity_and_symbol_are_not_replaced_by_trial_limits(self):
        result=self.wrapped().evaluate_snapshot(self.snapshot)
        intent=self.port.submit.call_args.args[0]
        self.assertEqual((intent['symbol'],intent['quantity'],intent['price']),('NVDA',17,'100'))
        self.assertGreater(intent['quantity']*float(intent['price']),500)
        self.assertEqual(result['strategy_quantity'],17)
    def test_acceptance_is_not_paper_fill_or_financial_update(self):
        before=copy.deepcopy(self.account.state);result=self.wrapped().evaluate_snapshot(self.snapshot)
        self.assertNotIn('paper_fill',result);self.assertEqual(result['broker_status'],'ACCEPTED')
        for key in ['cash','positions','trades']:self.assertEqual(self.account.state[key],before[key])
    def test_duplicate_signal_survives_account_restart_without_resending(self):
        self.wrapped().evaluate_snapshot(self.snapshot)
        other=SignalAccount(self.account.path);other.state=json.loads(self.account.path.read_text())
        result=configure_account(other,self.selection,port=self.port).evaluate_snapshot(self.snapshot)
        self.assertEqual(result['reason'],'broker_signal_already_recorded');self.assertEqual(self.port.submit.call_count,1)
    def test_unknown_response_never_automatically_resends(self):
        self.port.submit.side_effect=OSError('synthetic response loss')
        wrapped=self.wrapped();result=wrapped.evaluate_snapshot(self.snapshot)
        self.assertEqual(result['broker_status'],'UNKNOWN')
        wrapped.evaluate_snapshot(self.snapshot);self.assertEqual(self.port.submit.call_count,1)
    def test_save_failure_before_submit_sends_nothing(self):
        wrapped=self.wrapped();self.account.fail_save=True
        with self.assertRaises(OSError):wrapped.evaluate_snapshot(self.snapshot)
        self.port.submit.assert_not_called()
    def test_synthetic_replay_cannot_send_even_with_demo_enabled(self):
        self.snapshot['data_mode']='historical_replay';result=self.wrapped().evaluate_snapshot(self.snapshot)
        self.assertEqual(result['reason'],'broker_requires_actual_kis_observation');self.port.sync.assert_not_called();self.port.submit.assert_not_called()
    def test_outside_session_does_not_initialize_or_call_broker(self):
        self.snapshot['regular_session_open']=False
        result=self.wrapped().evaluate_snapshot(self.snapshot)
        self.assertEqual(result['reason'],'outside_regular_session');self.port.sync.assert_not_called()
    def test_stale_quote_does_not_submit(self):
        self.snapshot['quote']['available_at']='2026-11-02T14:00:00+00:00'
        result=self.wrapped().evaluate_snapshot(self.snapshot)
        self.assertEqual(result['reason'],'broker_quote_or_session_invalid');self.port.submit.assert_not_called()
    def test_original_hold_does_not_force_sell_after_buy(self):
        wrapped=self.wrapped();wrapped.evaluate_snapshot(self.snapshot);self.account.action='HOLD'
        result=wrapped.evaluate_snapshot(self.snapshot)
        self.assertEqual(result['action'],'HOLD');self.assertEqual(self.port.submit.call_count,1)
    def test_original_sell_is_routed_without_new_buy_or_cancel_probe(self):
        self.account.action='SELL';self.wrapped().observe_quote(self.snapshot)
        self.assertEqual(self.port.submit.call_args.args[0]['side'],'SELL');self.assertEqual(self.port.submit.call_count,1)
    def test_config_change_requires_restart_before_more_requests(self):
        wrapped=self.wrapped();self.values['kis_demo']['enabled']=False;self.write()
        with self.assertRaisesRegex(ValueError,'restart_required'):wrapped.evaluate_snapshot(self.snapshot)
        self.port.submit.assert_not_called()
    def test_live_mode_is_explicitly_locked_before_credentials_or_transport(self):
        self.values['kis_demo']['enabled']=False;self.values['live']['enabled']=True;self.write()
        with self.assertRaisesRegex(ValueError,'live_strategy_transmission_locked'):
            configure_account(self.account,load_execution(self.config),port=self.port)
        self.port.sync.assert_not_called();self.port.submit.assert_not_called()
    def test_selector_changes_only_mode_and_does_not_start_execution(self):
        self.assertEqual(select_mode('disabled',self.config),'disabled')
        self.assertEqual(load_execution(self.config)['mode'],'disabled');self.port.submit.assert_not_called()
    def test_paths_keep_internal_and_separate_broker_modes(self):
        internal={'mode':'internal_paper'};original=self.folder/'research/account.json'
        self.assertEqual(strategy_path(original,internal),original)
        demo=strategy_path(original,{'mode':'kis_demo'});live=strategy_path(original,{'mode':'live'})
        self.assertNotEqual(demo,live);self.assertIn('kis_demo',demo.parts)
    def test_reconciliation_failure_blocks_strategy_and_submission(self):
        self.port.sync.return_value={'observation_valid':False,'reason':'broker_readonly_or_reconciliation_failed'}
        result=self.wrapped().evaluate_snapshot(self.snapshot)
        self.assertEqual(result['action'],'WAIT');self.port.submit.assert_not_called()
    def test_managed_strategy_api_rejects_unmanaged_post_before_http(self):
        from broker.strategy_execution import ManagedStrategyApi
        market=SimpleNamespace(environment='vps',app_key='synthetic-app',app_secret='synthetic-secret',request_interval=0.2)
        api=ManagedStrategyApi(market,'synthetic-account')
        with patch('urllib.request.urlopen') as transport:
            with self.assertRaises(Exception):api.execute(SimpleNamespace(method='POST',name='overseas_stock.order'))
        transport.assert_not_called()
    def test_missing_risk_evidence_blocks_before_dispatch(self):
        from broker.strategy_execution import StrategyDemoPort
        port=StrategyDemoPort.__new__(StrategyDemoPort);port.manager=Mock();port.manager.state={'orders':{}};port.adapter=Mock();port.api=Mock()
        port.refresh=Mock(return_value={'new_orders_allowed':False,'resolution':{'reason':'official_cash_source_missing'}})
        result=port.submit({'symbol':'NVDA','side':'BUY'},self.snapshot)
        self.assertEqual(result['status'],'BLOCKED');port.manager.dispatch.assert_not_called()
    def test_close_releases_only_owned_port(self):
        self.wrapped().close();self.port.close.assert_called_once()

    def test_disable_during_account_query_stops_before_intent_or_submit(self):
        def change_mode(*args):
            self.values['kis_demo']['enabled']=False;self.write()
            return {'observation_valid':True}
        self.port.sync.side_effect=change_mode
        with self.assertRaisesRegex(ValueError,'restart_required'):self.wrapped().evaluate_snapshot(self.snapshot)
        self.port.submit.assert_not_called();self.assertEqual(self.account.state['broker_signals'],{})

    def test_http_boundary_rechecks_disabled_flag(self):
        from broker.strategy_execution import ManagedStrategyApi
        market=SimpleNamespace(environment='vps',app_key='synthetic-app',app_secret='synthetic-secret',request_interval=0.2)
        api=ManagedStrategyApi(market,'synthetic-account');api._managed_permission=True;api.allow_trading=True
        api._execution_selection=self.selection
        self.values['kis_demo']['enabled']=False;self.write()
        with patch('urllib.request.urlopen') as network:
            with self.assertRaisesRegex(Exception,'mode_changed_before_http'):
                api._http('/uapi/overseas-stock/v1/trading/order',{},'POST')
        network.assert_not_called()

    def test_broker_projection_restart_does_not_require_fake_paper_cash_flows(self):
        from trading.paper import PaperAccount
        path=self.folder/'execution-accounts/kis_demo/restart/account.json'
        account=PaperAccount(path);account.state['execution_mode']='kis_demo';account.state['cash']['US']=100000;account.save()
        restored=PaperAccount(path)
        self.assertEqual(restored.state['cash']['US'],100000);self.assertEqual(restored.state['trades'],[])

    def test_broker_projection_cannot_be_loaded_from_internal_account_path(self):
        from trading.execution import validate_projection
        state={'execution_mode':'kis_demo','trades':[],'cash':{'US':100000,'KR':0},'positions':{}}
        with self.assertRaisesRegex(ValueError,'path_or_mode'):validate_projection(self.folder/'account.json',state,{})

    def test_paper_fills_cannot_be_promoted_by_broker_mode_label(self):
        from trading.execution import validate_projection
        state={'execution_mode':'kis_demo','trades':[{'action':'BUY'}],'cash':{'US':100000,'KR':0},'positions':{}}
        with self.assertRaisesRegex(ValueError,'paper_trades'):validate_projection(self.folder/'execution-accounts/kis_demo/account.json',state,{})

    def test_broker_observation_does_not_report_fake_paper_valuation_or_fills(self):
        from trading.observation_journal import ObservationJournal
        from app.operations import OperationMonitor
        folder=self.folder/'observed';folder.mkdir()
        wrapped=self.wrapped();self.account.state['pending_daily']=[]
        self.account.state['broker_confirmed_fills']=[{'id':'confirmed','symbol':'NVDA','side':'BUY','filled':17,'notional':'1700','status':'FILLED'}]
        self.account.state['broker_readiness']={'as_of':self.snapshot['now']}
        with ObservationJournal(folder) as journal:
            journal.observe(self.snapshot,{'action':'HOLD','reason':'original_strategy_holding'},wrapped,OperationMonitor(folder))
        row=json.loads((folder/'daily/US-2026-11-02.json').read_text(encoding='utf-8'))
        self.assertEqual(row['execution_mode'],'kis_demo');self.assertIsNone(row['cash'])
        self.assertFalse(row['latest_valuation_available']);self.assertEqual(len(row['fills']),0)
        self.assertEqual(row['broker_confirmed_orders']['confirmed']['filled'],17)

    def test_cancel_only_known_own_unfilled_entries_and_never_resend(self):
        from broker.strategy_execution import StrategyDemoPort
        port=StrategyDemoPort.__new__(StrategyDemoPort);port.manager=Mock();port.adapter=Mock();port.api=Mock()
        port.manager.state={'orders':{
            'own':{'id':'own','strategy_owner':'owner','symbol':'NVDA','side':'BUY','status':'PARTIAL'},
            'other':{'id':'other','strategy_owner':'other','symbol':'NVDA','side':'BUY','status':'ACCEPTED'}}}
        port.manager.can_cancel.return_value=True
        def accepted(identifier,adapter):
            port.manager.state['orders'][identifier].update(status='CANCEL_PENDING',cancel_status='ACCEPTED')
        port.manager.cancel.side_effect=accepted
        outcome=port.cancel_entries('owner','NVDA')
        self.assertEqual(len(outcome),1);self.assertEqual(outcome[0]['status'],'CANCEL_REQUESTED_NOT_FINAL')
        port.manager.cancel.assert_called_once_with('own',port.adapter)
        port.cancel_entries('owner','NVDA');self.assertEqual(port.manager.cancel.call_count,1)
        self.assertFalse(port.api.allow_trading);self.assertFalse(port.adapter.enabled)

    def test_unknown_cancel_identity_is_not_transmitted(self):
        from broker.strategy_execution import StrategyDemoPort
        port=StrategyDemoPort.__new__(StrategyDemoPort);port.manager=Mock();port.adapter=Mock();port.api=Mock()
        port.manager.state={'orders':{'own':{'id':'own','strategy_owner':'owner','symbol':'NVDA','side':'BUY','status':'UNKNOWN'}}}
        port.manager.can_cancel.return_value=False
        self.assertEqual(port.cancel_entries('owner','NVDA')[0]['status'],'CANCEL_IDENTITY_UNVERIFIED')
        port.manager.cancel.assert_not_called()

    def test_original_missed_entry_window_requests_verified_cancel(self):
        from broker.strategy_execution import StrategyDemoPort
        port=StrategyDemoPort.__new__(StrategyDemoPort);port.cancel_entries=Mock(return_value=[])
        with patch('broker.strategy_execution.DATA_ROOT',self.folder):
            port.cancel_invalid_entry(self.account,self.snapshot,{'action':'WAIT','reason':'missed_open_window'})
        port.cancel_entries.assert_called_once_with('account.json','NVDA')

    def test_original_hold_does_not_cancel_pending_buy_for_arbitrary_timeout(self):
        from broker.strategy_execution import StrategyDemoPort
        port=StrategyDemoPort.__new__(StrategyDemoPort);port.cancel_entries=Mock()
        port.cancel_invalid_entry(self.account,self.snapshot,{'action':'HOLD','reason':'daily_holding'})
        port.cancel_entries.assert_not_called()
