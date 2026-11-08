"""검토에서 재현된 진단 주문 경로·미전송 취소·새 일봉 계획 소실. 실제 통신 없음."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
from unittest.mock import Mock,patch

from broker.strategy_execution import StrategyDemoPort
from trading.orders import OrderManager


class ExecutionReviewThreeTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.folder=Path(temporary.name)
        self.selection=self.folder/'execution.json'
        self.selection.write_text(json.dumps({'internal_paper':{'enabled':False},
            'kis_demo':{'enabled':True,'credentials_file':'unused-demo.env'},
            'live':{'enabled':False,'credentials_file':'unused-live.env'}}),encoding='utf-8')

    def test_runner_diagnostic_configures_internal_even_when_global_mode_is_demo(self):
        from tools import run_once
        from app.runtime import load_run_settings
        class ConfigurationObserved(Exception):pass
        modes=[]
        def capture(account,selection):
            modes.append(selection['mode']);raise ConfigurationObserved()
        defaults=load_run_settings()
        with patch.dict('os.environ',{'PYTRADING_EXECUTION_CONFIG':str(self.selection)}), \
             patch('tools.run_once.RESULTS_ROOT',self.folder/'results'), \
             patch('trading.execution.DATA_ROOT',self.folder), \
             patch('app.runner.load_run_settings',return_value=defaults), \
             patch('app.runner.PaperAccount'), \
             patch('trading.execution.configure_account',side_effect=capture), \
             patch('urllib.request.urlopen') as network, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ConfigurationObserved):run_once.main()
        self.assertEqual(modes,['internal_paper'])
        network.assert_not_called()

    def manager_port(self):
        manager=OrderManager(self.folder/'orders.sqlite','kis_demo','strategies');self.addCleanup(manager.close)
        manager.state['broker_identity']='synthetic-review-identity'
        manager.state['orders']['entry']={'id':'entry','broker_id':'20261027:123','symbol':'AAPL',
            'side':'BUY','quantity':2,'filled':0,'notional':'0','price':'100','order_type':'LIMIT',
            'status':'ACCEPTED','strategy_owner':'owner'}
        from Test.trading.test_review_regressions import event
        remote=event(manager)
        manager.verify_cancellations([remote],complete=True)
        manager._save()
        port=StrategyDemoPort.__new__(StrategyDemoPort);port.manager=manager
        port.api=SimpleNamespace(allow_trading=False)
        port.adapter=SimpleNamespace(enabled=False,prepare_cancel=Mock(),cancel=Mock(return_value='20261027:456'))
        return manager,port,remote

    def test_not_sent_cancel_can_retry_after_fresh_verified_remaining_quantity(self):
        manager,port,remote=self.manager_port()
        port.adapter.prepare_cancel.side_effect=[ValueError('synthetic_preflight_failure'),None]
        port.cancel_entries('owner','AAPL')
        self.assertEqual(manager.state['orders']['entry']['cancel_status'],'NOT_SENT')
        self.assertEqual(port.adapter.cancel.call_count,0)
        manager.verify_cancellations([remote],complete=True)
        second=port.cancel_entries('owner','AAPL')
        self.assertEqual(len(second),1)
        self.assertEqual(port.adapter.cancel.call_count,1)
        self.assertEqual(manager.state['orders']['entry']['cancel_status'],'ACCEPTED')
        self.assertFalse(port.adapter.enabled);self.assertFalse(port.api.allow_trading)

    def sync_fixture(self):
        owner=str(Path('daily')/'account.json');at=datetime.now(timezone.utc).isoformat()
        plan={'id':'2026-11-02:BUY:US:AAPL','symbol':'US:AAPL','side':'BUY',
            'signal_day':'2026-11-02','execution_day':'2026-11-03'}
        orders={}
        for side in ['BUY','SELL']:
            identifier='past-'+side
            orders[identifier]={'id':identifier,'strategy_owner':owner,'symbol':'AAPL','side':side,
                'filled':1,'quantity':1,'notional':'100','status':'FILLED','quote_at':at,
                'strategy_signal_at':'2026-10-20:'+side+':US:AAPL'}
        account=SimpleNamespace(path=self.folder/owner,settings={'buy_cost_ratio':0.003},save=Mock(),
            state={'positions':{},'pending_daily':[copy.deepcopy(plan)],'last_exit_at':{},
                   'last_entry_signal_bar':{},'cash':{'US':100000}})
        observed={'observed_at':at,'user_cash_account':{'cash_usd':'100000','orders_with_costs_pending':[]},
            'new_orders_allowed':False,'resolution':{'reason':'not_risk_approved'},'settlement_complete':True}
        port=StrategyDemoPort.__new__(StrategyDemoPort);port.manager=Mock()
        port.manager.state={'orders':orders};port.manager._execution_observation_valid=True
        port.refresh=Mock(return_value=observed)
        return port,account,plan,owner

    def test_past_round_trip_does_not_remove_new_daily_buy_plan(self):
        port,account,plan,_=self.sync_fixture()
        with patch('broker.strategy_execution.DATA_ROOT',self.folder):
            outcome=port.sync(account,{})
        self.assertTrue(outcome['observation_valid'])
        self.assertEqual(account.state['pending_daily'],[plan])
        account.save.assert_called_once()

    def test_diagnostic_buy_signal_stays_internal_and_has_zero_broker_transport(self):
        from app.runtime import load_run_settings
        from tools import run_once
        from Test.sample_data import sample
        strategy=self.folder/'strategy.json'
        strategy.write_text(json.dumps({'news_enabled':False,'earnings_enabled':False}),encoding='utf-8')
        defaults=load_run_settings()
        defaults.update(strategy_config=strategy,broker='kis',symbols=[('US','AAPL')],collect_news=False)
        before=self.selection.read_bytes()
        with patch.dict('os.environ',{'PYTRADING_EXECUTION_CONFIG':str(self.selection)}), \
             patch('tools.run_once.RESULTS_ROOT',self.folder/'results'), \
             patch('trading.execution.DATA_ROOT',self.folder), \
             patch('app.runner.load_run_settings',return_value=defaults), \
             patch('app.runner.create_kis_client'), \
             patch('app.runner.collect_kis_snapshot',return_value=sample()), \
             patch('broker.strategy_execution.StrategyDemoPort') as broker_port, \
             patch('urllib.request.urlopen') as network, contextlib.redirect_stdout(io.StringIO()):
            run_once.main()
        paths=list((self.folder/'results').glob('once-*/account.json'))
        self.assertEqual(len(paths),1)
        state=json.loads(paths[0].read_text(encoding='utf-8'))
        self.assertEqual(state['trades'][0]['action'],'BUY')
        broker_port.assert_not_called();network.assert_not_called()
        self.assertEqual(before,self.selection.read_bytes())

    def test_diagnostic_scope_covers_feature_dispatch_and_resets_after_error(self):
        from broker.diagnostic import diagnostic_active
        from tools.test_features import run_feature
        active=[]
        def diagnostic():
            active.append(diagnostic_active());raise ValueError('synthetic_failure')
        with patch('tools.run_once.main',side_effect=diagnostic):
            with self.assertRaises(ValueError):run_feature('runner')
        self.assertEqual(active,[True]);self.assertFalse(diagnostic_active())

    def test_direct_operations_probe_enters_diagnostic_scope(self):
        from broker.diagnostic import diagnostic_active
        from tools import measure_operations
        active=[]
        def observed(*args,**kwargs):active.append(diagnostic_active())
        with patch('tools.measure_operations.run',side_effect=observed),contextlib.redirect_stdout(io.StringIO()):
            measure_operations.main()
        self.assertEqual(active,[True]);self.assertFalse(diagnostic_active())

    def test_nested_diagnostic_scope_does_not_change_persisted_mode(self):
        from broker.diagnostic import diagnostic_scope,diagnostic_active
        from trading.execution import load_execution
        with diagnostic_scope():
            self.assertEqual(load_execution(self.selection)['mode'],'internal_paper')
            with diagnostic_scope():self.assertTrue(diagnostic_active())
            self.assertTrue(diagnostic_active())
        self.assertFalse(diagnostic_active())
        self.assertEqual(load_execution(self.selection)['mode'],'kis_demo')

    def test_diagnostic_configure_rejects_explicit_broker_mode(self):
        from broker.diagnostic import diagnostic_scope
        from trading.execution import configure_account,load_execution
        selected=load_execution(self.selection)
        with diagnostic_scope(),self.assertRaisesRegex(ValueError,'diagnostic_broker_account'):
            configure_account(Mock(),selected)

    def test_diagnostic_order_and_low_level_post_block_before_auth_or_transport(self):
        from broker.diagnostic import diagnostic_scope
        from broker.kis_api.client import KisApiClient,KisPreflightError
        from Test.broker.test_kis_api import market_client,sample_request
        client=KisApiClient(market_client('vps'),allow_trading=True)
        client._managed_permission=True
        with diagnostic_scope(),patch('urllib.request.urlopen') as network:
            with self.assertRaisesRegex(KisPreflightError,'diagnostic_broker_order'):
                client.execute(sample_request('POST','demo'))
            for path in ['/uapi/overseas-stock/v1/trading/order','/uapi/overseas-stock/v1/trading/order-rvsecncl']:
                with self.subTest(path=path),self.assertRaises(KisPreflightError):client._http(path,{},'POST',order=True)
        network.assert_not_called();client.market_client.authenticate.assert_not_called()

    def test_diagnostic_keeps_readonly_get_available(self):
        from broker.diagnostic import diagnostic_scope
        from broker.kis_api.client import KisApiClient,ApiResponse
        from Test.broker.test_kis_api import market_client,sample_request
        client=KisApiClient(market_client('prod'))
        with diagnostic_scope(),patch.object(client,'_http',return_value=ApiResponse({'rt_cd':'0','output':[]})) as http:
            client.execute(sample_request())
        self.assertEqual(http.call_count,1);self.assertEqual(http.call_args.args[2],'GET')

    def test_unknown_or_accepted_cancel_never_resends_after_new_remaining_proof(self):
        from broker.kis_api.client import KisOrderStateUnknown
        manager,port,remote=self.manager_port()
        port.adapter.cancel.side_effect=KisOrderStateUnknown('synthetic_response_lost')
        port.cancel_entries('owner','AAPL')
        self.assertEqual(manager.state['orders']['entry']['cancel_status'],'UNKNOWN')
        manager.verify_cancellations([remote],complete=True)
        self.assertEqual(port.cancel_entries('owner','AAPL'),[])
        self.assertEqual(port.adapter.cancel.call_count,1)

    def test_explicit_cancel_rejection_does_not_automatically_repeat(self):
        from broker.kis_api.client import KisOrderRejected
        manager,port,remote=self.manager_port()
        port.adapter.cancel.side_effect=KisOrderRejected('synthetic_rejected')
        port.cancel_entries('owner','AAPL')
        manager.verify_cancellations([remote],complete=True)
        self.assertEqual(port.cancel_entries('owner','AAPL'),[])
        self.assertEqual(port.adapter.cancel.call_count,1)

    def test_late_preflight_failure_is_retryable_after_reconciliation(self):
        from broker.kis_api.client import KisPreflightError
        manager,port,remote=self.manager_port()
        port.adapter.cancel.side_effect=[KisPreflightError('synthetic_not_sent'),'20261027:456']
        port.cancel_entries('owner','AAPL')
        self.assertEqual(manager.state['orders']['entry']['cancel_status'],'NOT_SENT')
        manager.verify_cancellations([remote],complete=True)
        self.assertEqual(len(port.cancel_entries('owner','AAPL')),1)
        self.assertEqual(port.adapter.cancel.call_count,2)

    def test_stale_cancel_proof_never_retries_not_sent(self):
        from datetime import timedelta
        manager,port,_=self.manager_port()
        manager.state['orders']['entry'].update(strategy_cancel_requested=True,cancel_status='NOT_SENT')
        manager._cancel_verified['entry']['at']=(datetime.now(timezone.utc)-timedelta(seconds=31)).isoformat()
        result=port.cancel_entries('owner','AAPL')
        self.assertEqual(result[0]['status'],'CANCEL_IDENTITY_UNVERIFIED')
        port.adapter.cancel.assert_not_called()

    def test_not_sent_cancel_recovery_survives_restart(self):
        from Test.trading.test_review_regressions import event
        manager,port,remote=self.manager_port()
        manager.state['orders']['entry'].update(strategy_cancel_requested=True,cancel_status='NOT_SENT')
        manager._save();manager.close()
        # 이미 닫은 연결의 cleanup은 멱등적이다. 새 연결은 별도 잠금을 소유한다.
        restored=OrderManager(self.folder/'orders.sqlite','kis_demo','strategies');self.addCleanup(restored.close)
        port.manager=restored
        restored.verify_cancellations([event(restored)],complete=True)
        self.assertEqual(len(port.cancel_entries('owner','AAPL')),1)
        self.assertEqual(port.adapter.cancel.call_count,1)

    def test_acknowledged_cancel_never_resends_even_if_strategy_flag_absent(self):
        manager,port,remote=self.manager_port()
        port.cancel_entries('owner','AAPL')
        manager.verify_cancellations([remote],complete=True)
        self.assertEqual(port.cancel_entries('owner','AAPL'),[])
        self.assertEqual(port.adapter.cancel.call_count,1)

    def linked_order(self,plan,owner,side=None,filled=1,explicit=True):
        from trading.execution import strategy_signal_id
        side=side or plan['side'];symbol=plan['symbol'].split(':',1)[1]
        order={'id':strategy_signal_id(owner,symbol,side,plan['id']),'strategy_owner':owner,
            'symbol':symbol,'side':side,'filled':filled,'strategy_signal_at':plan['id']}
        if explicit:order['strategy_daily_plan_id']=plan['id']
        return order

    def test_exact_plan_link_requires_actual_fill_and_immutable_signal_identity(self):
        from trading.execution import fills_daily_plan
        _,_,plan,owner=self.sync_fixture()
        linked=self.linked_order(plan,owner)
        self.assertTrue(fills_daily_plan(linked,plan,owner))
        for changes in [{'filled':0},{'strategy_owner':'another'},{'id':'wrong'},
                        {'strategy_signal_at':'old'},{'strategy_daily_plan_id':'old'},
                        {'symbol':'MSFT'},{'side':'SELL'}]:
            with self.subTest(changes=changes):self.assertFalse(fills_daily_plan(dict(linked,**changes),plan,owner))

    def test_legacy_plan_signal_is_supported_only_with_matching_order_hash(self):
        from trading.execution import fills_daily_plan
        _,_,plan,owner=self.sync_fixture()
        linked=self.linked_order(plan,owner,explicit=False)
        self.assertTrue(fills_daily_plan(linked,plan,owner))
        linked['id']='unidentified-old-order'
        self.assertFalse(fills_daily_plan(linked,plan,owner))

    def test_same_symbol_new_date_or_other_strategy_plan_is_not_consumed(self):
        from trading.execution import fills_daily_plan
        _,_,plan,owner=self.sync_fixture()
        linked=self.linked_order(plan,owner)
        newer=dict(plan,id='2026-11-03:BUY:US:AAPL',signal_day='2026-11-03',execution_day='2026-11-04')
        self.assertFalse(fills_daily_plan(linked,newer,owner))
        self.assertFalse(fills_daily_plan(linked,plan,'other-owner'))

    def test_sync_keeps_exact_new_order_plan_until_first_actual_fill(self):
        port,account,plan,owner=self.sync_fixture()
        linked=self.linked_order(plan,owner,filled=0)
        linked.update(quantity=1,notional='0',status='ACCEPTED',quote_at=datetime.now(timezone.utc).isoformat())
        port.manager.state['orders'][linked['id']]=linked
        with patch('broker.strategy_execution.DATA_ROOT',self.folder):
            self.assertTrue(port.sync(account,{})['observation_valid'])
        self.assertEqual(account.state['pending_daily'],[plan])

    def test_sync_removes_only_exact_executed_plan_and_preserves_future_plan(self):
        port,account,plan,owner=self.sync_fixture()
        linked=self.linked_order(plan,owner)
        linked.update(quantity=1,notional='100',status='FILLED',quote_at=datetime.now(timezone.utc).isoformat())
        port.manager.state['orders'][linked['id']]=linked
        sold=dict(linked,id='later-close',side='SELL',strategy_signal_at='later-exit',strategy_daily_plan_id=None)
        port.manager.state['orders'][sold['id']]=sold
        future=dict(plan,id='2026-11-03:BUY:US:AAPL',signal_day='2026-11-03',execution_day='2026-11-04')
        account.state['pending_daily'].append(future)
        with patch('broker.strategy_execution.DATA_ROOT',self.folder):
            self.assertTrue(port.sync(account,{})['observation_valid'])
        self.assertEqual(account.state['pending_daily'],[future])

    def test_daily_plan_id_is_persisted_in_strategy_signal_intent(self):
        from Test.trading.test_execution_modes import SignalAccount
        from trading.execution import configure_account,load_execution,strategy_signal_id
        account=SignalAccount(self.folder/'account.json')
        plan={'id':'2026-11-02:BUY:US:NVDA','symbol':'US:NVDA','side':'BUY'}
        account.state['pending_daily']=[plan]
        port=Mock();port.sync.return_value={'observation_valid':True}
        port.submit.return_value={'status':'ACCEPTED','reason':'not_a_fill'}
        at=datetime.now(timezone.utc).isoformat()
        snapshot={'market':'US','symbol':'NVDA','now':at,'source':'kis','data_mode':'live_observation',
            'regular_session_open':True,'quote':{'available_at':at,'ask':100,'bid':99.99}}
        with patch('trading.execution.DATA_ROOT',self.folder):
            configure_account(account,load_execution(self.selection),port=port).evaluate_snapshot(snapshot)
        intent=port.submit.call_args.args[0]
        self.assertEqual(intent['daily_plan_id'],plan['id'])
        self.assertEqual(intent['id'],strategy_signal_id('account.json','NVDA','BUY',plan['id']))

    def test_strategy_supplied_plan_id_wins_over_same_symbol_future_plan(self):
        from Test.trading.test_execution_modes import SignalAccount
        from trading.execution import configure_account,load_execution
        class TaggedAccount(SignalAccount):
            def evaluate_snapshot(self,snapshot,strategy=None):
                result=super().evaluate_snapshot(snapshot,strategy)
                result['daily_plan_id']='current-plan'
                return result
        account=TaggedAccount(self.folder/'account.json')
        account.state['pending_daily']=[{'id':value,'symbol':'US:NVDA','side':'BUY'} for value in ['future-plan','current-plan']]
        port=Mock();port.sync.return_value={'observation_valid':True};port.submit.return_value={'status':'ACCEPTED'}
        at=datetime.now(timezone.utc).isoformat()
        snapshot={'market':'US','symbol':'NVDA','now':at,'source':'kis','data_mode':'live_observation',
            'regular_session_open':True,'quote':{'available_at':at,'ask':100,'bid':99.99}}
        with patch('trading.execution.DATA_ROOT',self.folder):
            configure_account(account,load_execution(self.selection),port=port).evaluate_snapshot(snapshot)
        self.assertEqual(port.submit.call_args.args[0]['daily_plan_id'],'current-plan')

    def test_partial_fill_during_not_sent_cancel_changes_retry_quantity(self):
        manager,port,remote=self.manager_port()
        port.adapter.prepare_cancel.side_effect=[ValueError('synthetic_not_sent'),None]
        port.cancel_entries('owner','AAPL')
        newer=dict(remote,event_id='partial-new',filled=1,notional='100',status='PARTIAL')
        manager.update('entry',event_id='partial-new',filled=1,notional='100',status='PARTIAL',update_account=False)
        manager.verify_cancellations([newer],complete=True)
        port.cancel_entries('owner','AAPL')
        self.assertEqual(port.adapter.cancel.call_args.args[0]['cancel_quantity'],1)
