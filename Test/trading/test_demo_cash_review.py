"""현금·예약·비용 읽기 전용 검산. 실제 API·인증 없이 임시 원장 사용."""
import copy
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from trading.orders import OrderManager
from trading.user_cash import update_user_cash
from trading.demo_cash_review import review_cash
from trading.buying_power import bind_api_buying_power
from trading.risk_ledger import digest, RiskLedger


class CashReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.manager=OrderManager(Path(self.temp.name)/'orders.sqlite','kis_demo')
        self.addCleanup(lambda:self.manager.close())
        self.manager.state['broker_identity']='synthetic-account'
        now=datetime.now(timezone.utc)
        self.link={'observation_id':'balance-test','observation':{'account_fingerprint':'synthetic-account',
             'mode':'kis_demo','as_of':now.isoformat(),
             'balance_snapshot':{'positions':[],'reported_holdings_value_usd':'0'}}}
        self.config={'mode':'kis_demo','currency':'USD','cash_usd':'100000','source':'user_designation','authorized_on':'2026-11-01'}
        update_user_cash(self.manager,self.link,[],self.config)
        payload={'rt_cd':'0','output':{'tr_crcy_cd':'USD','ovrs_ord_psbl_amt':'99900'}}
        self.record={'operation':'overseas_stock.inquire_psamount','environment':'vps','method':'GET',
             'account_fingerprint':'synthetic-account','at':now.isoformat(),'payload':payload,'sha256':digest(payload)}
        self.inventory={'broker_reserved_ids':[],'remote_reservations_included':True}
        self.remote=[]
        self.window={'start':now.astimezone(ZoneInfo('America/New_York')).date().isoformat(),
                     'end':now.astimezone(ZoneInfo('America/New_York')).date().isoformat()}

    def review(self):
        budget=bind_api_buying_power(self.manager,self.record,self.inventory)
        with patch('urllib.request.urlopen') as transport:
            result=review_cash(self.manager,self.link,self.remote,budget,[self.record],self.window)
            transport.assert_not_called()
        return result

    def order(self,identifier='remote',side='BUY',quantity=2,filled=0,price='100',notional='0',status='ACCEPTED'):
        number={'remote':'123','local':'124','unresolved':'125'}[identifier]
        return {'id':identifier,'broker_id':'20261101:'+number,'account_fingerprint':'synthetic-account',
                'mode':'kis_demo','symbol':'AAPL','side':side,'quantity':quantity,'filled':filled,
                'price':price,'notional':notional,'status':status}

    def update(self):
        update_user_cash(self.manager,self.link,self.remote,self.config)

    def test_empty_account_distinguishes_not_applicable_from_future_costs(self):
        result=self.review()
        self.assertEqual(result['historical_cost_status'],'not_applicable_no_fills')
        self.assertEqual(result['model_cash_usd'],'100000.000000')
        self.assertEqual(result['estimated_available_after_all_reserves_usd'],'99900.000000')
        self.assertFalse(result['new_orders_allowed'])
        self.assertEqual(result['blockers'],['cash_movement_coverage_not_established','current_approved_risk_checkpoint_missing'])
        self.assertNotIn('non_integrated_account_status_unproven',str(result))

    def test_remote_and_local_reservations_each_count_once(self):
        self.remote=[self.order()];self.update()
        self.inventory['broker_reserved_ids']=[self.remote[0]['broker_id']]
        local=self.order('local',quantity=1,status='INTENT');local['broker_id']=None
        self.manager.state['orders']={'remote':self.remote[0],'local':local}
        value=self.review()
        self.assertEqual(value['remote_reserved_buy_usd'],'200.600000000')
        self.assertEqual(value['local_reserved_buy_usd'],'100.300000000')
        self.assertEqual(value['api_budget']['local_not_yet_reflected_reserve_usd'],'100.300000000')

    def test_partial_fill_pending_costs_estimate_not_final(self):
        self.remote=[self.order(filled=1,notional='100',status='PARTIAL')]
        self.link['observation']['balance_snapshot']={'positions':[{'symbol':'AAPL','quantity':1}],'reported_holdings_value_usd':'101'}
        self.update();value=self.review()
        self.assertIsNone(value['model_cash_usd'])
        self.assertEqual(value['pending_execution_cost_estimate_usd'],'0.300000000')
        self.assertEqual(value['remote_reserved_buy_usd'],'100.300000000')
        self.assertIn('filled_execution_final_costs_pending',value['blockers'])
        self.assertFalse(value['cost_estimate_is_final'])

    def test_final_cost_replaces_estimate_and_duplicate_is_idempotent(self):
        self.remote=[self.order(quantity=1,filled=1,notional='100',status='FILLED')]
        self.link['observation']['balance_snapshot']={'positions':[{'symbol':'AAPL','quantity':1}],'reported_holdings_value_usd':'101'}
        self.manager.state['demo_settlement']={'orders':{self.remote[0]['broker_id']:{'final_costs_usd':'1'}}}
        self.update();first=self.review();second=self.review()
        self.assertEqual(first['model_cash_usd'],'99899.000000')
        self.assertEqual(first['pending_execution_cost_estimate_usd'],'0')
        self.assertEqual(first['observation_id'],second['observation_id'])
        with self.assertRaises(ValueError):RiskLedger(self.manager).context()

    def test_manual_order_is_explicit_blocker(self):
        self.remote=[self.order()];self.update()
        self.assertIn('remote_orders_not_matched_to_local_ledger',self.review()['blockers'])

    def test_wrong_account_corrupt_capture_and_stale_records_fail(self):
        for key,value in [('account_fingerprint','other'),('sha256','0'*64),
                           ('at',(datetime.now(timezone.utc)-timedelta(seconds=31)).isoformat())]:
            original=copy.deepcopy(self.record);self.record[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.review()
            self.record=original

    def test_incomplete_history_cannot_be_current_cash(self):
        self.window['start']='2099-01-01'
        with self.assertRaises(ValueError):self.review()

    def test_storage_failure_remains_order_blocked(self):
        with patch.object(self.manager,'_save',side_effect=OSError('test')):
            with self.assertRaises(OSError):self.review()
        self.assertFalse(self.manager.ready)

    def test_restart_preserves_observation_without_order_permission(self):
        value=self.review();path=Path(self.temp.name)/'orders.sqlite'
        self.manager.close();self.manager=OrderManager(path,'kis_demo')
        self.assertIn(value['observation_id'],self.manager.state['risk_observations'])
        self.assertFalse(self.manager.ready)

    def test_unknown_transmission_blocks_budget_without_hiding_other_findings(self):
        order=self.order('unresolved',status='UNKNOWN');order['broker_id']=None
        self.manager.state['orders']={'unresolved':order}
        value=self.review()
        self.assertIsNone(value['estimated_available_after_all_reserves_usd'])
        self.assertIn('local_order_state_unresolved',value['blockers'])
