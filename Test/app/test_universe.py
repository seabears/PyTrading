"""일별 자동 추가/제외의 합성 검사. 실제 인증·시세·주문은 사용하지 않는다."""
import copy
import io
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from app.universe import load_policy, evaluate_daily, publish_selection, selection_view, spread_result
from app.universe_service import UniverseService
from broker.universe_data import parse_master, save_stock_evidence, verified_stocks
from broker.sessions import calendar_for
from paths import CONFIG_ROOT


class UniverseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.policy = load_policy()
        self.now = datetime(2026,11,4,16,tzinfo=timezone.utc)
        self.required = '2026-11-03'
        dates = calendar_for('US',2026).schedule.loc[:self.required].index[-80:]
        self.bars = [{'date':day.date().isoformat(),'open':100.,'high':101.,'low':99.,'close':100.,'volume':1e6} for day in dates]
        self.detail = {'curr':'USD','shar':'100000000','last':'100','base':'100','e_ordyn':'매매 가능'}
        self.samples = []
        for index in range(20):
            at = self.now-timedelta(minutes=20-index)
            self.samples.append({'at':at.isoformat(),'quote_at':at.isoformat(),'bid':99.99,'ask':100.01})

    def publish(self, rows, now=None):
        return publish_selection(self.folder,rows,self.required,now or self.now,self.policy,scope={'synthetic':True})

    def row(self,symbol='ABC',passed=True,reason='eligible'):
        return {'symbol':symbol,'exchange':'NAS','passed':passed,'reason':reason,'turnover20_usd_approx':1e8}

    def view(self,state=None,now=None,orders=()):
        return selection_view([('US','AAPL')],state or {},now or self.now,folder=self.folder,policy=self.policy,broker_orders=orders)

    def test_daily_thresholds_pass(self):
        result=evaluate_daily(self.bars,self.detail,self.required,self.policy)
        self.assertTrue(result['passed']);self.assertEqual(result['valid_sessions60'],60)

    def test_price_failure(self):
        bars=[dict(row,open=4.,high=4.01,low=3.99,close=4.) for row in self.bars]
        self.assertEqual(evaluate_daily(bars,self.detail,self.required,self.policy)['reason'],'price_below_minimum')

    def test_liquidity_failure(self):
        bars=[dict(row,volume=1.) for row in self.bars]
        self.assertEqual(evaluate_daily(bars,self.detail,self.required,self.policy)['reason'],'median_turnover_below_minimum')

    def test_recent_dry_day_fails_even_with_high_median(self):
        bars=copy.deepcopy(self.bars);bars[-1]['volume']=0
        self.assertEqual(evaluate_daily(bars,self.detail,self.required,self.policy)['reason'],'recent_turnover_below_minimum')

    def test_extreme_atr_fails(self):
        bars=[dict(row,high=120.,low=80.) for row in self.bars]
        self.assertEqual(evaluate_daily(bars,self.detail,self.required,self.policy)['reason'],'atr_above_maximum')

    def test_small_cap_fails(self):
        result=evaluate_daily(self.bars,dict(self.detail,shar='100'),self.required,self.policy)
        self.assertEqual(result['reason'],'market_cap_below_minimum')

    def test_currency_or_trade_permission_unknown_fails(self):
        for detail in (dict(self.detail,curr='KRW'),dict(self.detail,e_ordyn='')):
            self.assertFalse(evaluate_daily(self.bars,detail,self.required,self.policy)['passed'])

    def test_latest_missing_fails(self):
        self.assertEqual(evaluate_daily(self.bars[:-1],self.detail,self.required,self.policy)['reason'],'latest_completed_daily_missing')

    def test_two_missing_sessions_fail(self):
        bars=self.bars[:-4]+self.bars[-2:]
        self.assertEqual(evaluate_daily(bars,self.detail,self.required,self.policy)['reason'],'daily_coverage_below_59_of_60')

    def test_duplicate_daily_fails(self):
        self.assertFalse(evaluate_daily(self.bars+[self.bars[-1]],self.detail,self.required,self.policy)['passed'])

    def test_corporate_action_suspicion_fails(self):
        self.assertEqual(evaluate_daily(self.bars,dict(self.detail,base='10'),self.required,self.policy)['reason'],'corporate_action_or_price_mismatch')

    def test_real_session_spread_requires_twenty_unique_samples(self):
        self.assertTrue(spread_result(self.samples,self.required,self.now,self.policy)['passed'])
        self.assertFalse(spread_result(self.samples[:19],self.required,self.now,self.policy)['passed'])

    def test_repeated_quote_timestamp_does_not_create_twenty_samples(self):
        samples=[dict(row,quote_at=self.samples[-1]['quote_at']) for row in self.samples]
        self.assertFalse(spread_result(samples,self.required,self.now,self.policy)['passed'])

    def test_wide_spread_fails(self):
        samples=[dict(row,bid=99.,ask=101.) for row in self.samples]
        self.assertFalse(spread_result(samples,self.required,self.now,self.policy)['passed'])

    def test_off_hours_or_stale_samples_do_not_pass(self):
        samples=[dict(row,quote_at=(datetime.fromisoformat(row['at'])-timedelta(seconds=31)).isoformat()) for row in self.samples]
        self.assertFalse(spread_result(samples,self.required,self.now,self.policy)['passed'])
        samples=[dict(row,at='2026-11-04T10:00:00+00:00',quote_at='2026-11-04T10:00:00+00:00') for row in self.samples]
        self.assertFalse(spread_result(samples,self.required,self.now,self.policy)['passed'])

    def test_new_auto_added_and_deduplicated_against_user(self):
        self.publish([self.row(),self.row('AAPL')])
        self.assertEqual(self.view()['entry_symbols'],[('US','AAPL'),('US','ABC')])

    def test_failed_auto_removed_with_reason_and_history(self):
        self.publish([self.row()]);result=self.publish([self.row(passed=False,reason='atr_above_maximum')],self.now+timedelta(seconds=1))
        self.assertEqual(result['removed'],[{'symbol':'ABC','reason':'atr_above_maximum'}])
        self.assertNotIn(('US','ABC'),self.view(now=self.now+timedelta(seconds=1))['entry_symbols'])
        self.assertEqual(len(list((self.folder/'history'/self.required).glob('*.json'))),2)

    def test_not_in_shortlist_is_removed_not_retained_forever(self):
        self.publish([self.row()]);result=self.publish([],self.now+timedelta(seconds=1))
        self.assertEqual(result['removed'][0]['reason'],'not_in_daily_search_scope')

    def test_user_never_automatically_removed(self):
        self.publish([self.row('AAPL',False,'price_below_minimum')])
        self.assertIn(('US','AAPL'),self.view()['entry_symbols'])

    def test_excluded_holding_and_active_order_are_management_only(self):
        state={'positions':{'US:ABC':{'quantity':1}},'pending_daily':[]}
        orders=[{'symbol':'DEF','status':'ACCEPTED'}]
        view=self.view(state,orders=orders)
        self.assertEqual(view['management_only'],[('US','ABC'),('US','DEF')])
        self.assertNotIn(('US','ABC'),view['entry_symbols'])

    def test_stale_selection_does_not_supply_new_entries(self):
        self.publish([self.row()]);view=self.view(now=self.now+timedelta(days=1))
        self.assertFalse(view['automatic']);self.assertEqual(view['entry_symbols'],[('US','AAPL')])

    def test_corrupt_selection_preserves_user_and_management(self):
        (self.folder/'selection.json').write_text('broken')
        view=self.view({'positions':{'US:ABC':{}}})
        self.assertEqual(view['entry_symbols'],[('US','AAPL')]);self.assertIn(('US','ABC'),view['observed_symbols'])

    def test_restart_restores_selection_without_duplicate_entries(self):
        self.publish([self.row()]);self.assertEqual(self.view(),self.view())

    def test_policy_change_expires_auto_only(self):
        self.publish([self.row()]);self.policy['minimum_price_usd']=10
        self.assertFalse(self.view()['automatic']);self.assertIn(('US','AAPL'),self.view()['entry_symbols'])

    def master(self,kind='2',category='   '):
        fields=['']*24;fields[4]='ABC';fields[7]='SYNTHETIC COMPANY';fields[8]=kind;fields[9]='USD';fields[22]=category
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:archive.writestr('NASMST.COD','\t'.join(fields))
        return stream.getvalue()

    def test_official_master_uppercase_and_padded_category(self):
        found=parse_master(self.master(),'NAS',self.now)
        self.assertEqual(found['ABC']['security_type'],'2')
        save_stock_evidence(self.folder,found)
        self.assertEqual(verified_stocks(self.folder/'verified-stocks.json')['ABC']['asset_type'],'stock')

    def test_etf_or_etn_never_registered_by_discovery(self):
        for kind,category in [('3','001'),('3','002'),('2','002')]:
            with self.assertRaises(ValueError):parse_master(self.master(kind,category),'NAS',self.now)

    def test_failed_scan_removes_auto_and_keeps_user(self):
        service=UniverseService({'symbols':[('US','AAPL')]},{},folder=self.folder,provider=Mock(),clock=lambda:self.now)
        self.publish([self.row()]);service._error(ValueError('secret-do-not-log'),'scan')
        self.assertFalse(self.view()['automatic'])
        self.assertNotIn('secret-do-not-log',(self.folder/'status.json').read_text())

    def test_first_day_collects_samples_and_second_day_removes_failed_candidate(self):
        clock=[self.now]
        provider=Mock()
        provider.masters.return_value={'ABC':{}}
        provider.shortlist.return_value=({'ABC':{'exchange':'NAS'}},{'NAS':{'synthetic':True}})
        provider.daily.return_value=(self.bars,self.detail)
        provider.quote.side_effect=lambda symbol,exchange,now:{'at':now.isoformat(),'quote_at':now.isoformat(),'bid':99.99,'ask':100.01}
        service=UniverseService({'symbols':[('US','AAPL')]},{},folder=self.folder,provider=provider,clock=lambda:clock[0])
        for _ in range(20):
            service.refresh();clock[0]+=timedelta(seconds=60)
        self.assertIn('ABC',json.loads((self.folder/'selection.json').read_text())['selected'])
        self.assertEqual(provider.daily.call_count,1)
        clock[0]=self.now+timedelta(days=1)
        # 제공 일봉은 전일 그대로이므로 새 완료 일봉 누락으로 자동 제외되어야 한다.
        service.refresh()
        self.assertFalse(json.loads((self.folder/'selection.json').read_text())['selected'])
        self.assertEqual(provider.daily.call_count,2)

    def test_disabled_does_not_start_network_worker(self):
        provider=Mock();service=UniverseService({'symbols':[]},{},folder=self.folder,provider=provider)
        service.policy['enabled']=False;service.start();service.close()
        provider.assert_not_called();provider.masters.assert_not_called()

    def test_excluded_buy_never_reaches_fill(self):
        from trading.daily_account import DailyAccount
        candidate=json.loads((CONFIG_ROOT/'fixed-trend-study.json').read_text())['candidate']
        settings=json.loads((CONFIG_ROOT/'paper.json').read_text())
        account=DailyAccount(self.folder/'account.json',settings,candidate)
        account.state['pending_daily']=[{'id':'plan','symbol':'US:ABC','side':'BUY','execution_day':'2026-11-04'}]
        snapshot={'market':'US','symbol':'ABC','now':self.now.isoformat(),'universe_entry_allowed':False,
                  'quote':{'available_at':self.now.isoformat(),'bid':99.99,'ask':100.01}}
        with patch.object(account,'_fill') as fill:
            result=account.observe_quote(snapshot)
        self.assertEqual(result['reason'],'universe_no_longer_eligible');fill.assert_not_called()
        self.assertFalse(account.state['pending_daily'])

    def test_excluded_holding_still_sells_at_stop(self):
        from trading.daily_account import DailyAccount
        candidate=json.loads((CONFIG_ROOT/'fixed-trend-study.json').read_text())['candidate']
        settings=json.loads((CONFIG_ROOT/'paper.json').read_text())
        account=DailyAccount(self.folder/'account.json',settings,candidate)
        account.state['positions']['US:ABC']={'market':'US','symbol':'ABC','quantity':1,'average_cost':100,
            'cost_basis':100,'daily_stop':99,'daily_peak':100,'entry_day':'2026-11-03','entry_at':self.now.isoformat()}
        snapshot={'market':'US','symbol':'ABC','now':self.now.isoformat(),'universe_entry_allowed':False,
                  'quote':{'available_at':self.now.isoformat(),'bid':98.,'ask':98.01}}
        result=account.observe_quote(snapshot)
        self.assertEqual(result['action'],'SELL');self.assertFalse(account.state['positions'])

    def test_excluded_entry_cancels_only_own_pending_buy_path(self):
        from broker.strategy_execution import StrategyDemoPort
        port=StrategyDemoPort.__new__(StrategyDemoPort);port.cancel_entries=Mock(return_value=[])
        account=Mock();account.path=Path('daily/account.json')
        with patch('broker.strategy_execution.DATA_ROOT',Path('.')):
            port.cancel_invalid_entry(account,{'symbol':'ABC'},{'action':'WAIT','reason':'universe_no_longer_eligible'})
        port.cancel_entries.assert_called_once_with('daily\\account.json' if __import__('os').name=='nt' else 'daily/account.json','ABC')

    def test_excluded_strategy_buy_is_blocked_at_http_boundary(self):
        from broker.kis_api.client import KisApiClient, KisPreflightError
        from broker.kis_api.models import ApiRequest
        market=Mock(environment='vps',request_interval=.2)
        api=KisApiClient(market,allow_trading=True)
        manager=Mock(ready=True)
        manager.state={'mode':'kis_demo','orders':{'order':{'status':'SENDING','side':'BUY','symbol':'AAPL','strategy_owner':'owner'}}}
        spec=ApiRequest('overseas_stock.order','/uapi/overseas-stock/v1/trading/order','VTTT1002U',
                        {'PDNO':'AAPL'},'POST','demo')
        with patch('app.universe.current_entry_allowed',return_value=False),patch.object(api,'_http') as http:
            with self.assertRaises(KisPreflightError):api.execute_managed(spec,manager,'order')
        http.assert_not_called();market.authenticate.assert_not_called()

    def test_selection_cap_has_explicit_removal_reason(self):
        self.policy['maximum_auto_symbols']=1
        self.publish([self.row('ZZZ')])
        result=self.publish([self.row('AAA'),self.row('ZZZ')],self.now+timedelta(seconds=1))
        self.assertEqual(result['removed'],[{'symbol':'ZZZ','reason':'below_selection_limit'}])

    def test_invalid_discovery_does_not_override_existing_disallowed_product(self):
        from broker.product_policy import load_product_rules,validate_symbol
        from broker.kis import KisApiError
        row={'asset_type':'stock'}
        # 기존 ETF/ETN 판정이 있으면 발견 자료로 덮어쓰지 않는다.
        with patch('broker.universe_data.verified_stocks',return_value={'069500':row}):
            rules=load_product_rules()
        self.assertEqual(rules['verified_instruments']['069500']['asset_type'],'etf')
        with self.assertRaises(KisApiError):validate_symbol('Q123456',rules)

    def test_publish_failure_does_not_replace_previous_selection(self):
        self.publish([self.row()]);original=(self.folder/'selection.json').read_bytes()
        with patch('app.universe.atomic_json',side_effect=OSError('synthetic_disk_full')):
            with self.assertRaises(OSError):self.publish([])
        self.assertEqual((self.folder/'selection.json').read_bytes(),original)

    def test_preopen_auto_addition_does_not_recreate_consumed_plan(self):
        from trading.daily_account import DailyAccount
        candidate=json.loads((CONFIG_ROOT/'fixed-trend-study.json').read_text())['candidate']
        settings=json.loads((CONFIG_ROOT/'paper.json').read_text())
        account=DailyAccount(self.folder/'account.json',settings,candidate)
        account.state['last_signal_day']=self.required
        account.state['daily_reference_closes']={'US:AAPL':100}
        feature={'ma200':90,'close':100,'atr':2}
        preopen=self.now.replace(hour=12)
        with patch('trading.daily_account.make_features',return_value=[feature]),patch('trading.daily_account.signal',return_value={'enter':True,'score':1}):
            added=account.plan_additional_closed({'US:ABC':self.bars},self.bars,preopen)
            self.assertEqual(added,[self.required+':BUY:US:ABC'])
            account.state['pending_daily']=[]  # 집행·취소된 기존 계획은 다시 만들면 안 된다.
            self.assertEqual(account.plan_additional_closed({'US:ABC':self.bars},self.bars,preopen),[])
        self.assertFalse(account.state['pending_daily'])

    def test_intraday_first_selection_does_not_reopen_entry_window(self):
        from trading.daily_account import DailyAccount
        candidate=json.loads((CONFIG_ROOT/'fixed-trend-study.json').read_text())['candidate']
        settings=json.loads((CONFIG_ROOT/'paper.json').read_text())
        account=DailyAccount(self.folder/'account.json',settings,candidate)
        account.state['last_signal_day']=self.required
        self.assertEqual(account.plan_additional_closed({'US:ABC':self.bars},self.bars,self.now),[])
        self.assertFalse(account.state['pending_daily'])

    def test_actual_ranking_missing_cursor_limits_scope_without_inventing_key(self):
        from broker.universe_data import UniverseData
        from broker.kis_api.models import ApiResponse
        provider=UniverseData.__new__(UniverseData)
        provider.policy=self.policy;provider.folder=self.folder;provider.api=Mock()
        stocks={}
        responses=[]
        for exchange,symbol in [('NAS','AAA'),('NYS','BBB'),('AMS','CCC')]:
            stocks[symbol]={'exchange':exchange}
            responses.append(ApiResponse({'output1':{'nrec':'100'},'output2':[{'symb':symbol}]},'F'))
        provider.api.execute.side_effect=responses
        selected,scope=provider.shortlist(stocks,set(),__import__('threading').Event())
        self.assertEqual(set(selected),{'AAA','BBB','CCC'})
        self.assertEqual(provider.api.execute.call_count,3)
        self.assertTrue(all(row['stop_reason']=='next_cursor_not_provided' and not row['all_pages_reached'] for row in scope.values()))

    def test_running_broker_adapter_learns_only_verified_new_exchange(self):
        from broker.strategy_execution import StrategyDemoPort
        from types import SimpleNamespace
        port=StrategyDemoPort.__new__(StrategyDemoPort)
        port.adapter=SimpleNamespace(exchanges={'AAPL':'NASD'})
        port.manager=Mock();port.latest=None;port.refreshed=0
        with patch('broker.universe_data.verified_stocks',return_value={'ABC':{'exchange':'NYS'}}), \
             patch('trading.demo_port.DemoExecutionPort') as execution:
            execution.return_value.refresh.return_value={'observed':'synthetic'}
            port.refresh({'symbol':'ABC','quote':{'ask':100}})
        self.assertEqual(port.adapter.exchanges['ABC'],'NYSE')
        self.assertEqual(port.adapter.exchanges['AAPL'],'NASD')

    def test_second_collector_waits_without_invalidating_healthy_shared_selection(self):
        from app.runtime import AlreadyRunningError
        self.publish([self.row()])
        service=UniverseService({'symbols':[]},{},folder=self.folder,provider=Mock(),clock=lambda:self.now)
        service.stop_event=Mock()
        service.stop_event.is_set.side_effect=[False,True]
        with patch('app.universe_service.acquire_run_lock',side_effect=AlreadyRunningError('busy')):
            service._loop()
        self.assertIn('ABC',self.view()['automatic'])
        service.stop_event.wait.assert_called_once_with(self.policy['spread_sample_seconds'])

    def test_excluded_partial_holding_cancels_remaining_buy_without_forced_sell(self):
        from broker.strategy_execution import StrategyDemoPort
        port=StrategyDemoPort.__new__(StrategyDemoPort);port.cancel_entries=Mock(return_value=['checked'])
        account=Mock();account.path=self.folder/'account.json'
        snapshot={'symbol':'ABC','universe_entry_allowed':False}
        decision={'action':'HOLD','reason':'daily_holding'}
        with patch('broker.strategy_execution.DATA_ROOT',self.folder):
            result=port.cancel_invalid_entry(account,snapshot,decision)
        port.cancel_entries.assert_called_once_with('account.json','ABC')
        self.assertEqual(result,['checked']);self.assertEqual(decision['action'],'HOLD')
