"""사용자 지정 모의 현금의 계산·보존 검사. 합성 체결과 임시 SQLite만 사용."""
import copy,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
from trading.orders import OrderManager
from trading.user_cash import update_user_cash
from trading.risk_ledger import RiskLedger

class UserCashTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'orders.sqlite'
        self.manager=OrderManager(self.path,'kis_demo');self.addCleanup(lambda:self.manager.close())
        self.manager.state['broker_identity']='test-account'
        self.config={'mode':'kis_demo','currency':'USD','cash_usd':'100000','source':'user_designation','authorized_on':'2026-11-01'}
        self.link={'observation_id':'test','observation':{'account_fingerprint':'test-account','mode':'kis_demo',
          'as_of':datetime.now(timezone.utc).isoformat(),'balance_snapshot':{'positions':[],'reported_holdings_value_usd':'0'}}}
    def update(self,orders=None):return update_user_cash(self.manager,self.link,orders or [],self.config)
    def order(self,side='BUY',filled=1,notional='100',key='buy'):
        return {'broker_id':key,'mode':'kis_demo','account_fingerprint':'test-account','symbol':'AAPL','side':side,'filled':filled,'notional':notional}
    def position(self,quantity,value):
        self.link['observation']['balance_snapshot']={'positions':([{'symbol':'AAPL','quantity':quantity}] if quantity else []),'reported_holdings_value_usd':str(value)}
    def test_user_cash_is_used_for_cash_and_modeled_nav_without_api_verification(self):
        value=self.update();self.assertEqual(value['cash_usd'],'100000.000000');self.assertEqual(value['modeled_nav_usd'],'100000.000000')
        self.assertFalse(value['broker_cash_verified']);self.assertFalse(value['new_orders_allowed'])
        with self.assertRaises(ValueError):RiskLedger(self.manager).context()
    def test_buy_and_pending_costs_compute_cash_before_costs(self):
        self.update();self.position(1,101);value=self.update([self.order()])
        self.assertEqual(value['cash_before_unconfirmed_costs_usd'],'99900.000000');self.assertIsNone(value['cash_usd'])
        self.assertEqual(value['modeled_nav_before_unconfirmed_costs_usd'],'100001.000000')
    def test_final_fees_sell_and_duplicate_notice_do_not_double_count(self):
        self.update();self.manager.state['demo_settlement']={'orders':{'buy':{'final_costs_usd':'1'},'sell':{'final_costs_usd':'1'}}}
        self.position(1,101);orders=[self.order()];self.assertEqual(self.update(orders)['cash_usd'],'99899.000000')
        self.assertEqual(self.update(orders)['cash_usd'],'99899.000000')
        self.position(0,0);orders.append(self.order('SELL',1,'105','sell'))
        self.assertEqual(self.update(orders)['cash_usd'],'100003.000000')
    def test_restart_preserves_user_basis_and_account_binding(self):
        self.update();self.manager.close();self.manager=OrderManager(self.path,'kis_demo')
        self.assertEqual(self.update()['cash_usd'],'100000.000000')
        self.manager.state['broker_identity']='other'
        with self.assertRaises(ValueError):self.update()
    def test_missing_history_changed_basis_and_inventory_mismatch_fail(self):
        self.update();self.position(1,101);self.update([self.order()])
        with self.assertRaises(ValueError):self.update([])
        self.config['cash_usd']='200000'
        with self.assertRaises(ValueError):self.update([self.order()])
    def test_existing_holdings_cannot_be_silently_rebased(self):
        self.position(1,101)
        with self.assertRaises(ValueError):self.update()
    def test_partial_cumulative_fills_and_storage_failure(self):
        self.update();self.position(1,100);self.update([self.order()])
        self.position(2,200);value=self.update([self.order(filled=2,notional='200')])
        self.assertEqual(value['cash_before_unconfirmed_costs_usd'],'99800.000000')
        previous=copy.deepcopy(self.manager.state)
        with patch.object(self.manager,'_save',side_effect=OSError('test')):
            with self.assertRaises(OSError):self.update([self.order(filled=2,notional='200')])
        self.assertEqual(previous,self.manager.state)


class CashHistoryDateTests(unittest.TestCase):
    def test_utc_registration_uses_new_york_date(self):
        from kis_demo_balance import cash_history_start
        self.assertEqual(cash_history_start('2026-11-02T01:00:00+00:00'), '20261101')
        self.assertEqual(cash_history_start('2026-11-01'), '20261101')
