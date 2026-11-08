"""API 주문 한도와 장부 현금 분리. 임시 계좌·합성 응답, 실제 HTTP 없음."""
import copy,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from trading.buying_power import assess_buying_power,bind_api_buying_power,validate_api_buying_power
from trading.orders import OrderManager
from trading.risk_ledger import RiskLedger,digest
from Test.trading.risk_fixtures import seed_risk,snapshot

class BuyingPowerTests(unittest.TestCase):
    def order(self,identifier='remote',status='ACCEPTED',broker_id='20261101:1',quantity=10,filled=0):
        return {'id':identifier,'side':'BUY','status':status,'broker_id':broker_id,'quantity':quantity,'filled':filled,'price':'100'}
    def account(self,power='9000'):
        return {'buying_power_usd':power,'broker_reserved_ids':['20261101:1'],'remote_reservations_included':True}
    def test_broker_reserved_buy_is_not_subtracted_twice(self):
        value=assess_buying_power(self.account(),[self.order()],order_cost='8500')
        self.assertEqual(value['local_not_yet_reflected_reserve_usd'],'0')
        self.assertTrue(value['within_buying_power'])
    def test_unsent_local_buy_still_reserves_money(self):
        orders=[self.order(),self.order('local','INTENT',None,2)]
        value=assess_buying_power(self.account(),orders,order_cost='8900')
        self.assertEqual(value['local_not_yet_reflected_reserve_usd'],'200.600000000')
        self.assertFalse(value['within_buying_power'])
    def test_partial_cancel_pending_and_zero_padded_broker_id(self):
        order=self.order(status='CANCEL_PENDING',broker_id='20261101:0001',filled=3)
        value=assess_buying_power(self.account(),[order],order_cost='9000')
        self.assertTrue(value['within_buying_power']);self.assertEqual(value['broker_reserved_orders_not_deducted_again'],['remote'])
    def test_cash_nav_ledger_is_not_required_for_budget(self):
        account=self.account('700');account['modeled_cash_usd']='100000'
        value=assess_buying_power(account,[],order_cost='701')
        self.assertFalse(value['within_buying_power'])
        self.assertFalse(value['cash_or_nav_verification_required_for_this_calculation'])
    def test_own_current_order_is_not_reserved_twice(self):
        order=self.order('own','INTENT',None)
        self.assertTrue(assess_buying_power(self.account(),[order],current_id='own',order_cost='9000')['within_buying_power'])
    def test_unknown_orders_and_unproven_remote_reservations_block(self):
        with self.assertRaises(ValueError):assess_buying_power(self.account(),[self.order(status='UNKNOWN')])
        account=self.account();account['remote_reservations_included']=False
        with self.assertRaises(ValueError):assess_buying_power(account,[])
    def test_negative_nan_and_conflicting_alias_are_invalid(self):
        for power in ['-1','NaN']:
            with self.assertRaises((ValueError,ArithmeticError)):assess_buying_power(self.account(power),[])
        account=self.account();account.update(cash='100000',cash_is_available_order_capacity=True)
        with self.assertRaises(ValueError):assess_buying_power(account,[])

class BuyingPowerBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.manager=OrderManager(Path(self.temp.name)/'orders.sqlite','kis_demo');self.addCleanup(self.manager.close)
        self.manager.state['broker_identity']='synthetic-account'
        self.proof=seed_risk(self.manager,source_kind='kis_vps')
        self.payload={'rt_cd':'0','output':{'tr_crcy_cd':'USD','ovrs_ord_psbl_amt':'9000'}}
        self.record={'environment':'vps','operation':'overseas_stock.inquire_psamount','method':'GET',
            'account_fingerprint':'synthetic-account','at':datetime.now(timezone.utc).isoformat(),
            'payload':self.payload,'sha256':digest(self.payload),'request_context':{'ITEM_CD':'AAPL'}}
        self.inventory={'broker_reserved_ids':[],'remote_reservations_included':True}
    def bound_snapshot(self):
        evidence=bind_api_buying_power(self.manager,self.record,self.inventory)
        account=snapshot(self.proof)
        account.update(buying_power_usd=evidence['buying_power_usd'],buying_power_evidence=evidence,
                       cash='9000',broker_reserved_ids=[],remote_reservations_included=True)
        return account
    def test_updated_api_capacity_does_not_require_replacing_pnl_cash(self):
        account=self.bound_snapshot()
        self.assertEqual(self.proof.buying_power,'10000.000000')
        RiskLedger(self.manager).validate_snapshot(account)
        self.assertEqual(self.manager.state['risk_ledger']['last_evaluation']['cash_balance'],'10000.000000')
    def test_snapshot_tampering_and_runtime_binding_loss_fail(self):
        account=self.bound_snapshot();bad=copy.deepcopy(account);bad['buying_power_usd']='100000'
        with self.assertRaises(ValueError):RiskLedger(self.manager).validate_snapshot(bad)
        self.manager._buying_power_binding=None
        with self.assertRaises(ValueError):RiskLedger(self.manager).validate_snapshot(account)
    def test_wrong_account_environment_stale_or_hash_never_binds(self):
        for key,value in [('environment','prod'),('account_fingerprint','other'),('sha256','0'*64),
                          ('at',(datetime.now(timezone.utc)-timedelta(seconds=31)).isoformat())]:
            record={**self.record,key:value}
            with self.subTest(key=key),self.assertRaises(ValueError):bind_api_buying_power(self.manager,record,self.inventory)
    def test_loss_limit_and_product_rules_remain_separate(self):
        account=self.bound_snapshot();account['daily_loss_ratio']='.99'
        with self.assertRaises(ValueError):RiskLedger(self.manager).validate_snapshot(account)
