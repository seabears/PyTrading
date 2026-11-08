"""초기금·여력·미확정 비용과 축소 매도. 임시 SQLite/합성 응답, 외부 호출 없음."""
import copy
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from trading.orders import OrderManager
from trading.demo_account import select_buying_power, record_initial_reference, observe_settlement
from trading.execution_observation import observe_execution, validate_reduction
from Test.trading.test_review_regressions import event


class DemoAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.manager=OrderManager(Path(self.temp.name)/'orders.sqlite','kis_demo');self.addCleanup(self.manager.close)
        self.manager.state['broker_identity']='synthetic-account'
        self.now=datetime.now(timezone.utc).isoformat()
        self.hashes={'synthetic_source':'a'*64}
        self.manager.state['orders']['buy']={
            'id':'buy','symbol':'AAPL','side':'BUY','quantity':1,'price':'100','order_type':'LIMIT',
            'status':'ACCEPTED','filled':0,'notional':'0','broker_id':'20261027:123',
            'created_at':self.now,'quote_at':self.now,'stop_price':'98'}
        self.row=event(self.manager,quantity=1,filled=1);self.row.update(status='FILLED',remaining=0)
        self.inventory={'positions':{'AAPL':1},'sellable':{'AAPL':1},'remote_reserved_sell':{},
                        'broker_reserved_ids':[],'position_costs':{'AAPL':'100'},'exposure':'100'}

    def observe(self, rows=None, inventory=None):
        return observe_settlement(self.manager,rows if rows is not None else [self.row],inventory or self.inventory,
                                  observed_at=self.now,source_hashes=self.hashes)

    def test_integrated_denied_usd_selection_needs_no_enrollment_status(self):
        value={'output':{'tr_crcy_cd':'USD','ovrs_ord_psbl_amt':'100','frcr_ord_psbl_amt1':'250'}}
        with self.assertRaisesRegex(ValueError,'integrated_margin_prohibited'):
            select_buying_power(value,'integrated')
        self.assertEqual(select_buying_power(value,'cash_only')['amount'],'100.000000')
        self.assertEqual(select_buying_power(value,'unknown')['amount'],'100.000000')
        from Test.trading.cash_policy_fixtures import confirm_cash_only
        confirm_cash_only(self.manager)
        self.assertEqual(select_buying_power(value,'cash_only',manager=self.manager)['amount'],'100.000000')

    def test_invalid_currency_missing_selected_field_and_nan_are_rejected(self):
        for value,service in [({'tr_crcy_cd':'KRW','ovrs_ord_psbl_amt':'100'},'cash_only'),
                ({'tr_crcy_cd':'USD'},'integrated'),({'tr_crcy_cd':'USD','ovrs_ord_psbl_amt':'NaN'},'cash_only')]:
            with self.subTest(value=value),self.assertRaises(ValueError):select_buying_power({'output':value},service)

    def test_user_initial_cash_is_recorded_without_risk_approval(self):
        reference={'currency':'USD','amount':'100000','source':'user_confirmation','confirmed_on':'2026-10-30'}
        saved=record_initial_reference(self.manager,reference)
        self.assertEqual(saved['amount'],'100000.000000');self.assertFalse(self.manager.ready)
        self.assertNotIn('baseline',self.manager.state.get('risk_ledger',{}))
        self.assertEqual(saved,record_initial_reference(self.manager,reference))
        with self.assertRaises(ValueError):record_initial_reference(self.manager,{**reference,'amount':'200000'})
        self.manager.state['broker_identity']='other'
        with self.assertRaises(ValueError):record_initial_reference(self.manager,reference)

    def test_filled_order_is_observed_without_inventing_costs_or_cash(self):
        account=copy.deepcopy(self.manager.state['account']);result=self.observe()
        self.assertEqual(self.manager.state['orders']['buy']['filled'],1)
        self.assertEqual(self.manager.state['account'],account);self.assertFalse(self.manager.ready)
        value=result['orders']['20261027:123']
        self.assertIsNone(value['final_costs_usd']);self.assertIsNone(value['execution_at'])
        self.assertIsNone(result['net_realized_pnl_usd']);self.assertFalse(result['final_costs_complete'])

    def test_duplicate_observation_does_not_duplicate_fills(self):
        self.observe();self.observe()
        self.assertEqual(len(self.manager.state['demo_settlement']['orders']),1)
        self.assertEqual(self.manager.state['orders']['buy']['filled'],1)

    def test_missing_or_other_order_does_not_partly_apply_valid_fill(self):
        before=copy.deepcopy(self.manager.state['orders'])
        wrong={**self.row,'broker_id':'20261027:999','order_number':'999','event_id':'other'}
        with self.assertRaises(ValueError):self.observe([self.row,wrong])
        self.assertEqual(before,self.manager.state['orders'])
        self.assertNotIn('execution_observation',self.manager.state)

    def test_inventory_difference_rolls_back_fill_observation(self):
        before=copy.deepcopy(self.manager.state['orders'])
        with self.assertRaisesRegex(ValueError,'position_mismatch'):
            self.observe(inventory={**self.inventory,'positions':{'AAPL':2},'sellable':{'AAPL':2}})
        self.assertEqual(before,self.manager.state['orders'])

    def test_cost_pending_stops_buy_but_allows_verified_sell(self):
        self.observe()
        with self.assertRaises(ValueError):self.manager.create('another','AAPL','BUY',1,'100','98',self.now)
        order=self.manager.create('sell','AAPL','SELL',1,'101','0',self.now)
        self.manager.dispatch('sell',Mock(submit=Mock(return_value='20261027:124')))
        self.assertEqual(self.manager.state['orders']['sell']['status'],'ACCEPTED')
        self.assertFalse(self.manager.ready)

    def test_sell_cannot_exceed_verified_inventory_or_unsent_reservation(self):
        self.observe();self.manager.create('first-sell','AAPL','SELL',1,'100','0',self.now)
        with self.assertRaises(ValueError):self.manager.create('excess','AAPL','SELL',1,'100','0',self.now)

    def test_stale_quote_account_restore_replay_and_other_account_block_reduction(self):
        self.observe()
        order={'id':'sell','side':'SELL','symbol':'AAPL','quantity':1,'filled':0,'price':'100','quote_at':self.now}
        with self.assertRaises(ValueError):validate_reduction(self.manager,{**order,'quote_at':(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()})
        for key,value in [('restore_gate',True),('replay_only',True),('broker_identity','other')]:
            previous=self.manager.state.get(key)
            self.manager.state[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_reduction(self.manager,order)
            if previous is None:self.manager.state.pop(key,None)
            else:self.manager.state[key]=previous

    def test_changed_fill_or_price_invalidates_reduction_observation(self):
        self.observe();self.manager.state['orders']['buy']['price']='99'
        with self.assertRaisesRegex(ValueError,'observed_order_changed'):
            self.manager.create('sell','AAPL','SELL',1,'100','0',self.now)

    def test_missing_remote_order_and_storage_failure_fail_closed(self):
        with self.assertRaises(ValueError):self.observe([])
        original=copy.deepcopy(self.manager.state['orders'])
        with patch.object(self.manager,'_save',side_effect=OSError('synthetic_disk_failure')):
            with self.assertRaises(OSError):self.observe()
        self.assertEqual(original,self.manager.state['orders']);self.assertFalse(self.manager.ready)

    def test_restart_requires_new_full_observation_before_reduction(self):
        self.observe();self.manager.close()
        reopened=OrderManager(Path(self.temp.name)/'orders.sqlite','kis_demo')
        try:
            with self.assertRaisesRegex(ValueError,'current_process_observation'):
                reopened.create('sell','AAPL','SELL',1,'100','0',self.now)
        finally:reopened.close()

    def test_unsettled_risk_record_never_becomes_risk_proof(self):
        from trading.risk_ledger import RiskLedger
        value={'account_fingerprint':self.manager.state['broker_identity'],'mode':'kis_demo',
               'as_of':self.now,'source_hashes':self.hashes,'inventory':self.inventory}
        ledger=RiskLedger(self.manager)
        first=ledger.record_unsettled_observation(value);second=ledger.record_unsettled_observation(value)
        self.assertEqual(first,second);self.assertEqual(len(self.manager.state['risk_observations']),1)
        record=self.manager.state['risk_observations'][first]
        self.assertIsNone(record['execution_cash_usd']);self.assertFalse(record['risk_approved'])
        with self.assertRaises(ValueError):ledger.context()
        with self.assertRaises(ValueError):ledger.record_unsettled_observation({**value,'account_fingerprint':'other'})

    def test_trial_resume_requires_explicit_path_and_preserves_scope(self):
        import json,sqlite3
        from trading.demo_store import session_store
        root=Path(self.temp.name)
        with patch('trading.demo_store.DATA_ROOT',root):
            store,alias,identifier=session_store({},'synthetic-session')
            self.assertEqual(identifier,'synthetic-session')
            store.parent.mkdir(parents=True,exist_ok=True)
            connection=sqlite3.connect(store)
            connection.execute('CREATE TABLE journal (id INTEGER PRIMARY KEY, body TEXT)')
            state={'mode':'kis_demo','alias':alias,'limited_demo_session':{'id':identifier}}
            connection.execute('INSERT INTO journal VALUES(1,?)',(json.dumps(state),));connection.commit();connection.close()
            self.assertEqual(session_store({'resume_store':str(store)},'new'),(store,alias,identifier))
            with self.assertRaises(ValueError):session_store({'resume_store':str(root/'other.sqlite')},'new')

    def test_resume_rejects_other_mode_or_malformed_database(self):
        import json,sqlite3
        from trading.demo_store import session_store
        root=Path(self.temp.name)
        with patch('trading.demo_store.DATA_ROOT',root):
            store,alias,identifier=session_store({},'synthetic-session');store.parent.mkdir(parents=True,exist_ok=True)
            connection=sqlite3.connect(store);connection.execute('CREATE TABLE journal (id INTEGER PRIMARY KEY, body TEXT)')
            connection.execute('INSERT INTO journal VALUES(1,?)',(json.dumps({'mode':'live','alias':alias,'limited_demo_session':{'id':identifier}}),));connection.commit();connection.close()
            with self.assertRaises(ValueError):session_store({'resume_store':str(store)},'new')
