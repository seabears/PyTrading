"""실제 주문 스택을 합성 HTTP로 검사. 외부 주문·실제 인증을 사용하지 않는다."""
import copy,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import Mock,patch

from broker.managed_kis import ManagedKisAdapter
from broker.demo_trial import TrialKisApi
from trading.orders import OrderManager
from trading.demo_session import LimitedDemoSession
from trading.demo_account import observe_settlement
from trading.risk_ledger import RiskLedger
from trading.demo_accounting_cycle import prepare_pretrade,validate_pretrade,apply_verified_costs,observe_posttrade,readonly_plan
from Test.broker.test_kis_api import market_client
from Test.trading.risk_fixtures import seed_risk,snapshot,evidence,execution
from Test.trading.test_review_regressions import event


class AccountingCycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'orders.sqlite'
        self.manager=OrderManager(self.path,'kis_demo');self.addCleanup(lambda:self.manager.close())
        self.api=TrialKisApi(market_client('vps'),'00000000')
        self.adapter=ManagedKisAdapter(self.api,self.manager,'00000000','01',{'AAPL':'NASD'},enabled=False)
        self.proof=seed_risk(self.manager,source_kind='kis_vps')
        self.manager.state['account']=snapshot(self.proof);self.manager.ready=True
        self.session=LimitedDemoSession(self.manager,self.adapter,'synthetic-accounting','AAPL')
        self.api.trial_session=self.session;self.addCleanup(self.session.disarm)
        self.now=datetime.now(timezone.utc);self.stamp=self.now.isoformat()
        regular=patch('trading.demo_session.regular_session',return_value={'end':self.now+timedelta(hours=1)})
        regular.start();self.addCleanup(regular.stop)
        recovery={'regular_recovery_verified':True,'input_kind':'live_observation','checked_at':self.stamp,
                  'diagnostics':[],'per_symbol':{'AAPL':{'continuous':True}}}
        self.session.arm(recovery)
        self.order=self.session.create('trial:buy','BUY',1,'100','98',self.stamp)

    def prepare(self):return prepare_pretrade(self.manager,'trial:buy',self.session.limits)

    def response(self):
        response=Mock();response.status=200;response.headers={}
        response.read.return_value=b'{"rt_cd":"0","output":{"ODNO":"123"}}'
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        return response

    def fill(self,filled=1,quantity=1):
        order=self.manager.state['orders']['trial:buy']
        if not order.get('broker_id'):
            order.update(status='ACCEPTED',broker_id='20261101:123')
        row=event(self.manager,quantity=quantity,filled=filled)
        day,number=order['broker_id'].split(':')
        row.update(broker_id=order['broker_id'],order_day=day,order_number=number,
                   status='FILLED' if filled==quantity else 'PARTIAL',remaining=quantity-filled,
                   event_id=order['broker_id']+':'+str(filled))
        inventory={'positions':{'AAPL':filled} if filled else {},'sellable':{'AAPL':filled} if filled else {},
                   'remote_reserved_sell':{},'broker_reserved_ids':[],
                   'position_costs':{'AAPL':str(filled*100)} if filled else {},'exposure':str(filled*100)}
        observe_settlement(self.manager,[row],inventory,observed_at=self.stamp,source_hashes={'synthetic':'a'*64})
        return row,inventory

    def test_first_buy_saves_baseline_before_mock_http_without_future_fee(self):
        with patch('urllib.request.urlopen',return_value=self.response()) as network:
            self.session.submit('trial:buy')
        self.assertEqual(network.call_count,1)
        self.assertIn('openapivts.koreainvestment.com',network.call_args.args[0].full_url)
        value=self.manager.state['demo_accounting_cycle']['pretrade']['trial:buy']
        self.assertFalse(value['future_order_final_costs_required_before_submit'])
        self.assertIsNone(value['future_order_final_costs_usd'])
        self.assertEqual(value['cash_before_usd'],'10000.000000')
        self.assertEqual(self.order['status'],'ACCEPTED')

    def test_missing_pretrade_snapshot_is_rejected_without_network(self):
        with patch('urllib.request.urlopen') as network:
            with self.assertRaises(ValueError):validate_pretrade(self.manager,'trial:buy')
            network.assert_not_called()

    def test_stale_contract_account_and_risk_changes_fail(self):
        self.prepare()
        with self.assertRaises(ValueError):validate_pretrade(self.manager,'trial:buy',self.now+timedelta(minutes=1))
        self.order['price']='101'
        with self.assertRaises(ValueError):validate_pretrade(self.manager,'trial:buy')
        self.order['price']='100';self.manager.state['broker_identity']='other'
        with self.assertRaises(ValueError):validate_pretrade(self.manager,'trial:buy')

    def test_storage_failure_prevents_any_http(self):
        with patch.object(self.manager,'_save',side_effect=OSError('synthetic')),patch('urllib.request.urlopen') as network:
            with self.assertRaises(OSError):self.session.submit('trial:buy')
            network.assert_not_called()
        self.assertNotIn('demo_accounting_cycle',self.manager.state)

    def test_restart_retains_baseline_but_never_rearms_or_resends(self):
        self.prepare();self.manager.close();self.manager=OrderManager(self.path,'kis_demo','research')
        self.assertIn('trial:buy',self.manager.state['demo_accounting_cycle']['pretrade'])
        self.assertFalse(self.manager.ready)
        with self.assertRaises(ValueError):prepare_pretrade(self.manager,'trial:buy',self.session.limits)

    def test_existing_pending_filled_costs_block_next_buy(self):
        self.manager.state['demo_settlement']={'orders':{'prior':{'final_costs_usd':None}}}
        with self.assertRaisesRegex(ValueError,'existing_filled_costs_pending'):self.prepare()

    def test_first_cost_record_is_pending_and_duplicate_does_not_reset_confirmed_cost(self):
        self.prepare();row,inventory=self.fill()
        value=observe_posttrade(self.manager,[row],inventory,self.stamp,{'synthetic':'a'*64})
        self.assertEqual(value['phase'],'SETTLEMENT_PENDING');self.assertTrue(value['new_buy_blocked'])
        settled=self.manager.state['demo_settlement']['orders'][row['broker_id']]
        settled.update(final_costs_usd='0.5',cost_state='CONFIRMED',cost_source={'synthetic':'not_actual'})
        observe_settlement(self.manager,[row],inventory,observed_at=self.stamp,source_hashes={'synthetic':'a'*64})
        self.assertEqual(self.manager.state['demo_settlement']['orders'][row['broker_id']]['final_costs_usd'],'0.5')

    def test_additional_partial_fill_invalidates_prior_final_costs(self):
        self.order['quantity']=2;self.session.state['contracts']['trial:buy']['quantity']=2
        row,inventory=self.fill(1,2)
        settled=self.manager.state['demo_settlement']['orders'][row['broker_id']]
        settled.update(final_costs_usd='0.5',cost_state='CONFIRMED')
        row,inventory=self.fill(2,2)
        self.assertIsNone(self.manager.state['demo_settlement']['orders'][row['broker_id']]['final_costs_usd'])

    def test_verified_final_costs_are_imported_from_existing_risk_ledger(self):
        self.prepare();row,inventory=self.fill()
        now=datetime.now(timezone.utc)
        fill=execution('synthetic-fill','trial:buy',now,1,100,fees='0.5')
        proof=RiskLedger(self.manager).ingest(evidence(self.manager,now,source_kind='kis_vps',cash='9899.5',buying_power='9899.5',
            net_asset_value='10000.5',positions={'AAPL':1},position_costs={'AAPL':'100.5'},fills=[fill],
            quotes={'AAPL':{'at':now.isoformat(),'price':'101'}}),now=now)
        self.assertTrue(proof.eligible)
        self.assertEqual(apply_verified_costs(self.manager)['applied_orders'],1)
        settled=self.manager.state['demo_settlement']['orders'][row['broker_id']]
        self.assertEqual(settled['final_costs_usd'],'0.500000')
        self.assertEqual(settled['cost_source']['fill_ids'],['synthetic-fill'])
        self.assertEqual(observe_posttrade(self.manager,[row],inventory,self.stamp,{'synthetic':'a'*64})['phase'],'HOLDING')

    def test_unverified_or_quantity_mismatched_costs_are_not_imported(self):
        row,_=self.fill()
        self.assertEqual(apply_verified_costs(self.manager)['applied_orders'],0)
        self.assertIsNone(self.manager.state['demo_settlement']['orders'][row['broker_id']]['final_costs_usd'])

    def test_mock_round_trip_matches_final_costs_and_cash_delta(self):
        self.prepare();buy,inventory=self.fill()
        self.session.prepare_reduction()
        sell=self.session.create('trial:sell','SELL',1,'101','0',self.stamp)
        response=self.response();response.read.return_value=b'{"rt_cd":"0","output":{"ODNO":"124"}}'
        with patch('urllib.request.urlopen',return_value=response) as network:
            self.session.submit('trial:sell')
            self.assertEqual(network.call_count,1)
        day,number=sell['broker_id'].split(':')
        sold=event(self.manager,side='SELL',quantity=1,price='101',filled=1)
        sold.update(broker_id=sell['broker_id'],order_day=day,order_number=number,status='FILLED',remaining=0,
                    notional='105',event_id=sell['broker_id']+':1')
        flat={'positions':{},'sellable':{},'remote_reserved_sell':{},'broker_reserved_ids':[],'position_costs':{},'exposure':'0'}
        observe_settlement(self.manager,[buy,sold],flat,observed_at=self.stamp,source_hashes={'synthetic':'a'*64})
        now=datetime.now(timezone.utc)
        fills=[execution('synthetic-buy','trial:buy',now-timedelta(seconds=1),1,100,fees='0.5'),
               execution('synthetic-sell','trial:sell',now,1,105,fees='0.5',side='SELL')]
        RiskLedger(self.manager).ingest(evidence(self.manager,now,source_kind='kis_vps',cash='10004',buying_power='10004',
            net_asset_value='10004',positions={},position_costs={},fills=fills,quotes={}),now=now)
        self.assertEqual(apply_verified_costs(self.manager)['applied_orders'],2)
        result=observe_posttrade(self.manager,[buy,sold],flat,self.stamp,{'synthetic':'a'*64})
        self.assertEqual(result['phase'],'RECONCILED')
        self.assertEqual(result['actual_cash_delta_usd'],'4.000000')
        self.assertEqual(result['expected_cash_delta_usd'],'4.000000')
        self.assertTrue(result['cash_delta_matches'])
        self.assertEqual(result['remaining_shares'],0)

    def test_cash_delta_mismatch_is_not_reported_as_reconciled(self):
        self.prepare();row,inventory=self.fill()
        record=self.manager.state['demo_accounting_cycle']['pretrade']['trial:buy']
        record['cash_before_usd']='9999'
        now=datetime.now(timezone.utc)
        fill=execution('synthetic-fill','trial:buy',now,1,100,fees='0.5')
        RiskLedger(self.manager).ingest(evidence(self.manager,now,source_kind='kis_vps',cash='9899.5',buying_power='9899.5',
            net_asset_value='10000.5',positions={'AAPL':1},position_costs={'AAPL':'100.5'},fills=[fill],
            quotes={'AAPL':{'at':now.isoformat(),'price':'101'}}),now=now)
        apply_verified_costs(self.manager)
        value=observe_posttrade(self.manager,[row],inventory,self.stamp,{'synthetic':'a'*64})
        self.assertEqual(value['phase'],'REVIEW')
        self.assertFalse(value['cash_delta_matches'])
        self.assertIn('posttrade_cash_delta_mismatch',value['issues'])

    def test_missing_remote_order_and_duplicate_identity_require_review(self):
        row,inventory=self.fill()
        self.assertEqual(observe_posttrade(self.manager,[],inventory,self.stamp,{'synthetic':'a'*64})['phase'],'REVIEW')
        with self.assertRaises(ValueError):observe_posttrade(self.manager,[row,row],inventory,self.stamp,{'synthetic':'a'*64})

    def test_unknown_future_fee_is_posttrade_requirement_not_pretrade_gate(self):
        review={'historical_cost_status':'not_applicable_no_fills','as_of':self.stamp}
        assessment={'failed_controls':[],'unknown_controls':[]}
        plan=readonly_plan(self.manager,review,assessment)
        self.assertEqual(plan['pretrade_blockers'],[])
        self.assertFalse(plan['future_final_cost_is_pretrade_requirement'])

    def test_unexplained_cash_flow_is_not_waived_by_stage_split(self):
        self.manager.ready=False
        with patch('urllib.request.urlopen') as network:
            with self.assertRaises(ValueError):self.prepare()
            network.assert_not_called()
