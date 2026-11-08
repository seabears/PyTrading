"""상태 기계의 합성 시나리오. 실제 API·인증·실제 체결 검증이 아니다."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from datetime import datetime, timezone
from trading.demo_runner import LimitedDemoRunner


class SyntheticSession:
    def __init__(self):
        self.session_id='synthetic';self.armed=False
        self.manager=SimpleNamespace(state={'orders':{}},_save=Mock(),can_cancel=lambda identifier:True)
        self.limits={'quantity':1,'maximum_concurrent_shares':1,'maximum_gross_buy_commitments_usd':'500',
                     'maximum_buy_attempts':2,'maximum_poll_count':24,'poll_seconds':5}
        self.sent=[];self.cancelled=[]
    def arm(self,recovery):self.armed=True
    def prepare_reduction(self):self.armed=True
    def disarm(self):self.armed=False
    def create(self,identifier,side,quantity,price,stop,at):
        self.manager.state['orders'][identifier]={'id':identifier,'side':side,'symbol':'AAPL','quantity':quantity,
            'filled':0,'status':'INTENT','price':price,'notional':'0','broker_id':None}
    def submit(self,identifier):
        self.sent.append(identifier);self.manager.state['orders'][identifier].update(status='ACCEPTED',broker_id=identifier)
    def cancel(self,identifier):
        self.cancelled.append(identifier);self.manager.state['orders'][identifier].update(status='CANCEL_PENDING',session_cancel_attempted=True)
    def _own_orders(self):return list(self.manager.state['orders'].values())
    def summary(self):return {'local_active_orders':sum(order['status'] in {'ACCEPTED','CANCEL_PENDING','INTENT','UNKNOWN'} for order in self._own_orders()),
        'local_net_filled_shares':sum(order['filled']*(1 if order['side']=='BUY' else -1) for order in self._own_orders())}


class SyntheticPort:
    def __init__(self,session,*,probe_fills=False,pending_costs=False):
        self.session=session;self.probe_fills=probe_fills;self.pending_costs=pending_costs;self.calls=0
    def refresh(self):
        self.calls+=1
        for order in self.session._own_orders():
            if order['id'].endswith(':probe'):
                if self.probe_fills:order.update(status='FILLED',filled=1)
                elif order['status']=='CANCEL_PENDING':order.update(status='CANCELLED')
            elif order['status']=='ACCEPTED':order.update(status='FILLED',filled=1)
        return {'new_orders_allowed':True,'settlement_complete':not self.pending_costs,
                'posttrade':{'phase':'SETTLEMENT_PENDING' if self.pending_costs else 'RECONCILED',
                             'actual_cash_delta_usd':None if self.pending_costs else '0','cash_delta_matches':not self.pending_costs}}
    def quote(self):return {'at':datetime.now(timezone.utc).isoformat(),'bid':'100','ask':'101'}
    def recovery(self):return {'kind':'synthetic_only'}
    def wait(self,seconds):pass


class DemoWorkflowTests(unittest.TestCase):
    def test_cancel_then_buy_and_sell_all_finish(self):
        session=SyntheticSession();result=LimitedDemoRunner(session,SyntheticPort(session)).run()
        self.assertTrue(result['completed']);self.assertEqual(result['phase'],'DONE')
        self.assertEqual(len(session.sent),3);self.assertEqual(len(session.cancelled),1)
        self.assertEqual(result['remaining_shares'],0);self.assertFalse(session.armed)

    def test_probe_fill_skips_additional_buy_and_sells_only_once(self):
        session=SyntheticSession();result=LimitedDemoRunner(session,SyntheticPort(session,probe_fills=True)).run()
        self.assertTrue(result['completed']);self.assertEqual(session.sent,['synthetic:probe','synthetic:exit'])
        self.assertEqual(session.cancelled,[])

    def test_flat_with_pending_final_cost_is_not_complete(self):
        session=SyntheticSession();result=LimitedDemoRunner(session,SyntheticPort(session,pending_costs=True)).run()
        self.assertFalse(result['completed']);self.assertEqual(result['phase'],'REVIEW');self.assertEqual(result['remaining_shares'],0)

    def test_risk_failure_never_sends(self):
        session=SyntheticSession();port=SyntheticPort(session);port.refresh=lambda:{'new_orders_allowed':False}
        result=LimitedDemoRunner(session,port).run();self.assertFalse(result['completed']);self.assertEqual(session.sent,[])

    def test_persisted_unknown_is_queried_without_resending(self):
        session=SyntheticSession();port=SyntheticPort(session);runner=LimitedDemoRunner(session,port)
        session.create('synthetic:entry','BUY',1,'100','98','');session.manager.state['orders']['synthetic:entry']['status']='UNKNOWN'
        runner.state['phase']='ENTRY_PENDING';result=runner.run()
        self.assertEqual(session.sent,[]);self.assertFalse(result['completed']);self.assertGreaterEqual(port.calls,1)

    def test_crash_between_phase_and_intent_does_not_recreate_order(self):
        session=SyntheticSession();port=SyntheticPort(session);runner=LimitedDemoRunner(session,port)
        runner.state['phase']='ENTRY_PENDING';result=runner.run()
        self.assertEqual(session.sent,[]);self.assertFalse(result['completed'])

    def test_existing_probe_on_new_state_requires_review(self):
        session=SyntheticSession();port=SyntheticPort(session);runner=LimitedDemoRunner(session,port)
        session.create('synthetic:probe','BUY',1,'98','95','')
        self.assertFalse(runner.step());self.assertEqual(session.sent,[])

    def test_unknown_response_disables_and_finally_queries(self):
        session=SyntheticSession();port=SyntheticPort(session)
        def lost(identifier):
            session.manager.state['orders'][identifier]['status']='UNKNOWN';raise TimeoutError('synthetic')
        session.submit=lost
        result=LimitedDemoRunner(session,port).run()
        self.assertFalse(result['completed']);self.assertFalse(session.armed);self.assertGreaterEqual(port.calls,2)

    def test_budget_too_small_for_two_buys_skips_cancel_probe(self):
        session=SyntheticSession();session.limits['maximum_gross_buy_commitments_usd']='150'
        result=LimitedDemoRunner(session,SyntheticPort(session)).run()
        self.assertTrue(result['completed']);self.assertEqual(session.sent,['synthetic:entry','synthetic:exit'])

    def test_poll_count_is_bounded_and_shutdown_queries_final_state(self):
        session=SyntheticSession();port=SyntheticPort(session);runner=LimitedDemoRunner(session,port,stop_requested=lambda:True)
        result=runner.run();self.assertEqual(session.sent,[]);self.assertFalse(result['completed']);self.assertTrue(result['final_remote_verified'])

    def test_fill_during_cancel_skips_second_buy(self):
        session=SyntheticSession();port=SyntheticPort(session)
        original=port.refresh
        def refresh():
            for order in session._own_orders():
                if order['id'].endswith(':probe') and order['status']=='CANCEL_PENDING':
                    order.update(status='FILLED',filled=1)
            return original()
        port.refresh=refresh
        result=LimitedDemoRunner(session,port).run()
        self.assertTrue(result['completed']);self.assertEqual(session.sent,['synthetic:probe','synthetic:exit'])
        self.assertEqual(len(session.cancelled),1)

    def test_missing_final_query_is_not_success(self):
        session=SyntheticSession();port=SyntheticPort(session);runner=LimitedDemoRunner(session,port)
        runner.state['phase']='DONE';runner.state['completed']=True
        port.refresh=Mock(side_effect=TimeoutError('synthetic'))
        result=runner.run();self.assertFalse(result['completed']);self.assertFalse(result['final_remote_verified'])


    def test_final_costs_without_verified_cash_reconciliation_is_not_complete(self):
        session=SyntheticSession();port=SyntheticPort(session);original=port.refresh
        def refresh():
            result=original();result['posttrade']={'phase':'CASH_RECONCILIATION_PENDING','actual_cash_delta_usd':None}
            return result
        port.refresh=refresh
        result=LimitedDemoRunner(session,port).run()
        self.assertFalse(result['completed']);self.assertEqual(result['phase'],'REVIEW')
