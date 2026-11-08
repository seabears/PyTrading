"""수동 모의 체결1주의 관리 편입·복구·보호 매도를 합성 자료로 검사한다."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

from paths import CONFIG_ROOT
from trading.daily_account import DailyAccount
from trading.strategy_adoption import adopt_manual_fill,restore_adopted_exit_plans
from broker.strategy_execution import StrategyDemoPort


class StrategyAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for module in ['trading.strategy_adoption','broker.strategy_execution','trading.execution','trading.adoption_requests']:
            current=patch(module+'.DATA_ROOT',self.root);current.start();self.addCleanup(current.stop)
        self.now=datetime(2026,11,4,15,0,tzinfo=timezone.utc)
        self.candidate=json.loads((CONFIG_ROOT/'fixed-trend-study.json').read_text(encoding='utf-8'))['candidate']
        self.costs=json.loads((CONFIG_ROOT/'paper.json').read_text(encoding='utf-8'))
        self.account=self.new_account()
        self.order={'id':'manual-buy','broker_id':'20261103:123','symbol':'T','side':'BUY','quantity':1,
            'filled':1,'notional':'21.19500','price':'21.20','stop_price':'20.56','order_type':'LIMIT',
            'status':'FILLED','strategy_owner':'user_requested_single_demo:original',
            'created_at':'2026-11-03T15:18:30+00:00','quote_at':'2026-11-03T15:18:29+00:00',
            'strategy_signal_at':'2026-11-03T15:18:29+00:00','strategy_position':{}}
        inventory={'positions':{'T':1},'sellable':{'T':1},'position_costs':{'T':'21.195'},
                   'remote_reserved_sell':{},'broker_reserved_ids':[]}
        self.manager=SimpleNamespace(state={'mode':'kis_demo','broker_identity':'synthetic-account-fingerprint',
            'orders':{'manual-buy':self.order},'execution_observation':{
                'mode':'kis_demo','account_fingerprint':'synthetic-account-fingerprint',
                'as_of':self.now.isoformat(),'source_hashes':{'mock':'a'*64},'inventory':inventory,
                'order_contracts':{'manual-buy':{key:self.order[key] for key in ['broker_id','symbol','side','quantity','price','filled','status']}}},
            'demo_settlement':{'orders':{'20261103:123':{'final_costs_usd':None,
                'quantity':1,'notional_usd':'21.19500','symbol':'T','side':'BUY',
                'observed_at':self.now.isoformat(),'source_hashes':{'mock':'a'*64}}},'final_costs_complete':False}},
            _execution_observation_valid=True,ready=False,_save=Mock(),_strategy_settlement_binding=None)
        self.snapshot={'market':'US','symbol':'T','now':self.now.isoformat(),'source':'kis',
            'data_mode':'live_observation','regular_session_open':True,
            'quote':{'bid':21.3,'ask':21.31,'available_at':self.now.isoformat()}}
        end=datetime(2026,11,3,tzinfo=timezone.utc)
        candles=[]
        for index in range(211):
            close=21+index*.001
            candles.append({'timestamp':(end-timedelta(days=210-index)).isoformat(),'currency':'USD',
                'openPrice':close,'closePrice':close,'highPrice':close+.2,'lowPrice':close-.2,'volume':1000})
        self.record={'market':'US','interval':'1d','collection_complete':True,'candles':candles}

    def new_account(self):
        account=DailyAccount(self.root/'execution-accounts/kis_demo/daily/account.json',self.costs,self.candidate)
        account.state['execution_mode']='kis_demo';account.save=Mock()
        return account

    def adopt(self):
        return adopt_manual_fill(self.manager,self.account,'manual-buy',self.snapshot,self.record,now=self.now)

    def restore_observation(self):
        self.manager._execution_observation_valid=True

    def port(self):
        port=StrategyDemoPort.__new__(StrategyDemoPort);port.manager=self.manager
        observed={'report':{'inventory':self.manager.state['execution_observation']['inventory']},
            'observed_at':self.now.isoformat(),'user_cash_account':{'cash_usd':None,'orders_with_costs_pending':['20261103:123']},
            'cash_risk_review':{'estimated_cash_after_cost_reserve_usd':'99978.7'},'new_orders_allowed':False,
            'resolution':{'status':'미확인','reason':'strategy_designated_cash_unavailable'},
            'settlement_complete':False,'settlement_source':{'connected':False},
            'strategy_posttrade':{'phase':'COSTS_PENDING','pending_cost_order_count':1}}
        def refresh(snapshot,**_):
            self.restore_observation();return observed
        port.refresh=Mock(side_effect=refresh)
        return port

    def test_adoption_preserves_financial_contract_and_original_owner_receipt(self):
        before=copy.deepcopy(self.order)
        with patch('urllib.request.urlopen',side_effect=AssertionError('no network')) as network:
            receipt=self.adopt()
        for key in ['id','broker_id','quantity','filled','notional','price','stop_price','created_at','quote_at','status','strategy_signal_at']:
            self.assertEqual(self.order[key],before[key])
        self.assertEqual(receipt['original_order'],before)
        self.assertEqual(receipt['original_owner'],before['strategy_owner'])
        self.assertEqual(self.order['strategy_owner'],str(self.account.path.relative_to(self.root)))
        self.assertEqual(network.call_count,0)
        self.assertFalse(self.manager.ready)
        self.assertFalse(receipt['costs_finalized_by_adoption'])
        self.assertEqual(self.manager.state['demo_settlement']['orders']['20261103:123']['final_costs_usd'],None)

    def test_original_stop_is_not_lowered_and_unobserved_peak_not_fabricated(self):
        receipt=self.adopt();details=receipt['management_position']
        self.assertEqual(details['daily_stop'],20.56)
        self.assertEqual(details['daily_peak'],21.3)
        self.assertEqual(details['management_entry_price'],'21.19500')
        self.assertEqual(details['entry_day'],'2026-11-03')
        self.assertFalse(details['individual_execution_time_known'])

    def test_stale_quote_blocks_without_changing_owner(self):
        self.snapshot['quote']['available_at']=(self.now-timedelta(seconds=31)).isoformat()
        before=copy.deepcopy(self.manager.state)
        with self.assertRaises(ValueError):self.adopt()
        self.assertEqual(self.manager.state,before)

    def test_old_or_wrong_account_observation_blocks(self):
        for field,value in [('as_of',(self.now-timedelta(seconds=31)).isoformat()),('account_fingerprint','other')]:
            original=self.manager.state['execution_observation'][field]
            self.manager.state['execution_observation'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.adopt()
            self.manager.state['execution_observation'][field]=original

    def test_no_runtime_observation_flag_blocks(self):
        self.manager._execution_observation_valid=False
        with self.assertRaises(ValueError):self.adopt()

    def test_live_mode_and_restore_gate_block(self):
        self.manager.state['mode']='live'
        with self.assertRaises(ValueError):self.adopt()
        self.manager.state['mode']='kis_demo';self.manager.state['restore_gate']={'pending':True}
        with self.assertRaises(ValueError):self.adopt()

    def test_foreign_or_nonmanual_source_is_not_adopted(self):
        self.order['strategy_owner']='some_other_strategy'
        with self.assertRaises(ValueError):self.adopt()

    def test_partial_or_unfilled_order_does_not_become_one_share(self):
        self.order.update(status='PARTIAL',quantity=2)
        with self.assertRaises(ValueError):self.adopt()

    def test_changed_order_since_remote_snapshot_blocks(self):
        self.order['price']='22.00'
        with self.assertRaises(ValueError):self.adopt()

    def test_reserved_or_mismatched_holding_blocks(self):
        inventory=self.manager.state['execution_observation']['inventory']
        inventory['sellable']['T']=0;inventory['remote_reserved_sell']['T']=1
        with self.assertRaises(ValueError):self.adopt()
        inventory['sellable']['T']=1;inventory['remote_reserved_sell']['T']=0;inventory['positions']['T']=2
        with self.assertRaises(ValueError):self.adopt()

    def test_other_lots_are_not_silently_allocated(self):
        self.manager.state['orders']['other']={**self.order,'id':'other','strategy_owner':'foreign'}
        with self.assertRaises(ValueError):self.adopt()

    def test_missing_or_unfinished_daily_source_blocks(self):
        self.record['collection_complete']=False
        with self.assertRaises(ValueError):self.adopt()
        self.record['collection_complete']=True;self.record['candles']=self.record['candles'][:-1]
        with self.assertRaises(ValueError):self.adopt()

    def test_insufficient_atr_history_and_price_dislocation_block(self):
        full=self.record['candles'];self.record['candles']=full[-100:]
        with self.assertRaises(ValueError):self.adopt()
        self.record['candles']=full;self.snapshot['quote'].update(bid=10,ask=10.01)
        with self.assertRaises(ValueError):self.adopt()

    def test_storage_failure_rolls_back_owner_and_receipt(self):
        before=copy.deepcopy(self.manager.state)
        self.manager._save.side_effect=OSError('full')
        with self.assertRaises(OSError):self.adopt()
        self.assertEqual(self.manager.state,before)
        self.assertFalse(self.manager.ready)

    def test_repeat_is_idempotent_and_never_adds_fake_buy(self):
        first=self.adopt();self.restore_observation()
        second=self.adopt()
        self.assertEqual(first,second)
        self.assertEqual(len(self.manager.state['orders']),1)
        self.assertEqual(self.account.state['trades'],[])
        self.assertEqual(self.account.state['pending_daily'],[])

    def test_new_strategy_projection_recovers_from_authoritative_receipt(self):
        receipt=self.adopt()
        account=self.new_account();port=self.port()
        result=port.sync(account,self.snapshot)
        self.assertTrue(result['observation_valid'])
        self.assertEqual(account.state['positions']['US:T']['quantity'],1)
        self.assertEqual(account.state['positions']['US:T']['daily_stop'],receipt['management_position']['daily_stop'])
        self.assertFalse(account.state['broker_readiness']['new_orders_allowed'])
        self.assertFalse(account.state['positions']['US:T']['actual_costs_final'])

    def test_existing_confirmed_exit_signal_is_restored_as_sell_only(self):
        with patch('trading.strategy_adoption.signal',return_value={'enter':False,'exit':True,'score':0}):
            receipt=self.adopt()
        account=self.new_account();self.assertTrue(self.port().sync(account,self.snapshot)['observation_valid'])
        self.assertEqual(account.state['pending_daily'],[receipt['pending_exit_plan']])
        self.port().sync(account,self.snapshot)
        self.assertEqual(len(account.state['pending_daily']),1)
        self.assertEqual(account.state['pending_daily'][0]['side'],'SELL')

    def test_sold_holding_cannot_be_resurrected_by_repeat(self):
        self.adopt();self.restore_observation()
        self.manager.state['execution_observation']['inventory']['positions']={}
        self.manager.state['execution_observation']['inventory']['sellable']={}
        with self.assertRaises(ValueError):self.adopt()

    def test_existing_stop_management_still_sells_while_buys_blocked(self):
        self.adopt();port=self.port()
        self.assertTrue(port.sync(self.account,self.snapshot)['observation_valid'])
        quote=copy.deepcopy(self.snapshot)
        quote['now']=(self.now+timedelta(minutes=1)).isoformat()
        quote['quote'].update(bid=20.4,ask=20.41,available_at=quote['now'])
        quote['operational_buy_block']=True
        before=copy.deepcopy(self.account.state)
        # 판단 복사본만 검사한다. 실제 주문·운영 계좌 저장은 하지 않는다.
        preview=copy.copy(self.account);preview.state=copy.deepcopy(self.account.state)
        decision=preview.observe_quote(quote)
        self.assertEqual(decision['action'],'SELL')
        self.assertEqual(decision['paper_fill']['quantity'],1)
        self.assertEqual(self.account.state,before)

    def test_raised_trailing_stop_is_not_replaced_by_initial_metadata(self):
        self.adopt();port=self.port();port.sync(self.account,self.snapshot)
        self.account.state['positions']['US:T']['daily_stop']=21.0
        port.sync(self.account,self.snapshot)
        self.assertEqual(self.account.state['positions']['US:T']['daily_stop'],21.0)

    def test_changed_notional_cannot_seed_wrong_entry_price(self):
        self.order['notional']='21.50'
        with self.assertRaises(ValueError):self.adopt()

    def test_tampered_management_metadata_is_not_silently_restored(self):
        self.adopt();self.restore_observation()
        self.order['strategy_position']['daily_stop']=1.0
        with self.assertRaises(ValueError):self.adopt()
        account=self.new_account();account.state['positions']['US:T']={'quantity':1}
        with self.assertRaises(ValueError):restore_adopted_exit_plans(self.manager,account)

    def test_existing_loss_halt_and_pending_costs_are_preserved(self):
        self.manager.state['risk_ledger']={'days':{'2026-11-04':{'halted':True}}}
        self.manager.state['user_cash_account']={'cash_usd':None,'orders_with_costs_pending':['20261103:123']}
        before=copy.deepcopy(self.manager.state)
        self.adopt()
        self.assertEqual(self.manager.state['risk_ledger'],before['risk_ledger'])
        self.assertEqual(self.manager.state['user_cash_account'],before['user_cash_account'])

    def test_zero_padded_official_order_number_matches_same_canonical_id(self):
        orders=self.manager.state['demo_settlement']['orders']
        value=orders.pop('20261103:123')
        orders['20261103:0000000123']=value
        self.assertEqual(self.adopt()['broker_id'],'20261103:123')

    def test_duplicate_canonical_fill_keys_block_adoption(self):
        orders=self.manager.state['demo_settlement']['orders']
        orders['20261103:0000000123']=copy.deepcopy(orders['20261103:123'])
        with self.assertRaises(ValueError):self.adopt()

    def test_multiple_shares_adopts_verified_whole_source_lot(self):
        self.order.update(quantity=2,filled=2,notional='42.39000')
        observation=self.manager.state['execution_observation']
        observation['order_contracts']['manual-buy'].update(quantity=2,filled=2)
        observation['inventory']['positions']['T']=2;observation['inventory']['sellable']['T']=2
        self.manager.state['demo_settlement']['orders']['20261103:123'].update(quantity=2,notional_usd='42.39000')
        receipt=self.adopt()
        self.assertEqual(receipt['quantity'],2)
        self.assertEqual(receipt['management_position']['management_entry_price'],'21.19500')

    def test_closed_historical_other_owner_lot_does_not_block_new_manual_lot(self):
        self.manager.state['orders']['past-buy']={**self.order,'id':'past-buy','strategy_owner':'past','side':'BUY'}
        self.manager.state['orders']['past-sell']={**self.order,'id':'past-sell','strategy_owner':'past','side':'SELL'}
        self.assertEqual(self.adopt()['quantity'],1)

    def test_same_day_manual_fill_uses_previous_completed_atr_without_backdated_exit(self):
        self.order['broker_id']='20261104:123'
        self.manager.state['execution_observation']['order_contracts']['manual-buy']['broker_id']=self.order['broker_id']
        settlement=self.manager.state['demo_settlement']['orders'].pop('20261103:123')
        self.manager.state['demo_settlement']['orders']['20261104:123']=settlement
        with patch('trading.strategy_adoption.signal',return_value={'enter':False,'exit':True,'score':0}):
            receipt=self.adopt()
        self.assertEqual(receipt['management_position']['entry_day'],'2026-11-04')
        self.assertIsNone(receipt['pending_exit_plan'])

    def test_explicit_operator_metadata_is_validated(self):
        with self.assertRaises(ValueError):
            adopt_manual_fill(self.manager,self.account,'manual-buy',self.snapshot,self.record,now=self.now,
                authorization={'request_id':'not-valid','confirmed_at':self.now.isoformat(),'source':'local_operator_confirmation'})
