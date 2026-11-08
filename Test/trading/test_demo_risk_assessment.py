"""실행 가능한 위험 평가와 영속 중지. 실제 API 없이 임시 원장으로 검사한다."""
import copy
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from trading.orders import OrderManager
from trading.risk_ledger import RiskLedger, digest
from trading.demo_risk_assessment import assess_observation, latest_assessment


class RiskAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'orders.sqlite'
        self.manager=OrderManager(self.path,'kis_demo');self.addCleanup(lambda:self.manager.close())
        self.manager.state['broker_identity']='synthetic-account'
        self.now=datetime.now(timezone.utc)
        self.manager.state['user_cash_account']={'baseline':{'cash_usd':'10000','account_fingerprint':'synthetic-account',
             'enrolled_at':self.now.isoformat()},'observation_id':'balance', 'as_of':self.now.isoformat(),
             'cash_usd':'10000','modeled_nav_usd':'10000','confirmed_fees_usd':'0','orders_with_costs_pending':[], 'orders':{}}
        self.manager.state['risk_observations']={'balance':{'balance_snapshot':{'positions':[], 'holdings_cost_basis_usd':'0'}}}
        self.review={'observation_id':'review','as_of':self.now.isoformat(),'mode':'kis_demo','account_fingerprint':'synthetic-account',
             'balance_observation_id':'balance','estimated_cash_after_cost_reserve_usd':'10000','remote_reserved_buy_usd':'0',
             'local_reserved_buy_usd':'0','api_budget':{'available_for_new_order_usd':'10000'},'unmatched_remote_orders':[],
             'unresolved_local_orders':[],'historical_cost_status':'not_applicable_no_fills','future_cost_channel_status':'not_established_for_vps'}
        self.store_review()

    def store_review(self):
        self.manager.state['risk_observations']['review']={k:copy.deepcopy(v) for k,v in self.review.items() if k!='observation_id'}

    def assess(self):
        self.store_review()
        with patch('urllib.request.urlopen') as network:
            value=assess_observation(self.manager,self.review,self.now)
            network.assert_not_called()
        return value

    def test_partial_evidence_still_runs_all_computable_controls(self):
        value=self.assess()
        self.assertTrue(value['evaluation_complete']);self.assertFalse(value['evidence_complete'])
        self.assertEqual(value['unknown_controls'],['cash_movement_coverage'])
        self.assertTrue(value['known_controls_passed']);self.assertFalse(value['new_orders_allowed'])
        self.assertNotIn('current_approved_risk_checkpoint_missing',value['unknown_controls'])
        self.assertEqual(value['model_daily_loss_ratio'],'0')

    def test_risk_state_is_not_broker_proof(self):
        self.assess()
        with self.assertRaises(ValueError):RiskLedger(self.manager).context()
        self.assertFalse(self.manager.ready)

    def test_existing_complete_proof_is_reused_without_enabling_orders(self):
        # 실제 연결이 아닌 기존 합성 RiskLedger fixture로 향후 근거 연결 경로를 검사한다.
        from Test.trading.risk_fixtures import seed_risk
        seed_risk(self.manager,source_kind='kis_vps')
        self.now=datetime.now(timezone.utc)  # 근거 생성 완료 이후를 검사 시각으로 사용한다.
        value=self.assess()
        self.assertEqual(value['controls']['cash_movement_coverage']['status'],'pass')
        self.assertTrue(value['risk_approved']);self.assertFalse(value['new_orders_allowed'])
        self.assertEqual(value['decision'],'risk_checks_approved')

    def test_proof_for_different_cash_is_not_reused(self):
        from Test.trading.risk_fixtures import seed_risk
        seed_risk(self.manager,source_kind='kis_vps')
        self.now=datetime.now(timezone.utc)
        self.manager.state['user_cash_account']['cash_usd']='9000'
        self.assertEqual(self.assess()['controls']['cash_movement_coverage']['status'],'unknown')

    def test_loss_halt_survives_recovery_restart_and_duplicate(self):
        self.manager.state['user_cash_account']['modeled_nav_usd']='9000'
        first=self.assess();self.assertEqual(first['controls']['daily_loss_limit']['status'],'fail')
        self.assertEqual(first['assessment_id'],self.assess()['assessment_id'])
        self.manager.close();self.manager=OrderManager(self.path,'kis_demo')
        self.manager.state['user_cash_account']['modeled_nav_usd']='10000'
        second=self.assess();self.assertTrue(second['controls']['daily_loss_limit']['latched'])
        self.assertEqual(second['controls']['daily_loss_limit']['status'],'fail')

    def test_next_local_day_has_new_day_state_keeps_prior_halt(self):
        self.manager.state['user_cash_account']['modeled_nav_usd']='9000';first=self.assess()
        self.now+=timedelta(days=1);stamp=self.now.isoformat();self.review['as_of']=stamp
        self.manager.state['user_cash_account'].update(as_of=stamp,modeled_nav_usd='9000')
        second=self.assess()
        self.assertNotEqual(first['local_day'],second['local_day'])
        self.assertFalse(second['controls']['daily_loss_limit']['latched'])
        self.assertTrue(self.manager.state['risk_assessment_ledger']['days'][first['local_day']]['halted'])

    def test_cost_pending_does_not_invent_daily_pnl_or_drawdown(self):
        model=self.manager.state['user_cash_account'];model.update(cash_usd=None,modeled_nav_usd=None,orders_with_costs_pending=['buy'])
        model['orders']={'buy':{'filled':1}}
        value=self.assess()
        self.assertIsNone(value['model_daily_loss_ratio']);self.assertIsNone(value['maximum_observed_model_drawdown'])
        self.assertEqual(value['controls']['execution_costs']['status'],'unknown')
        self.assertEqual(value['controls']['consecutive_loss_cooldown']['status'],'unknown')

    def test_exposure_and_cash_reserves_use_existing_policy(self):
        self.review['remote_reserved_buy_usd']='11000'
        value=self.assess()
        self.assertIn('total_investment_limit',value['failed_controls'])
        self.assertIn('usd_cash_and_reservations',value['failed_controls'])

    def test_manual_and_unknown_orders_report_failure(self):
        self.review['unmatched_remote_orders']=['test-order']
        self.review['unresolved_local_orders']=['unknown']
        self.assertIn('order_reconciliation',self.assess()['failed_controls'])

    def test_operator_pause_and_restore_do_not_clear(self):
        pause=self.path.parent/'PAUSE_BUYS';pause.touch()
        self.assertIn('operator_and_restore_gate',self.assess()['failed_controls'])
        self.assertTrue(pause.exists());pause.unlink()
        self.manager.state['restore_gate']=True
        self.assertIn('operator_and_restore_gate',self.assess()['failed_controls'])
        self.assertTrue(self.manager.state['restore_gate'])

    def test_policy_or_order_mutation_invalidates_cached_assessment(self):
        self.assess();original=copy.deepcopy(self.manager.policy)
        self.manager.policy['daily_loss_limit']=.01
        with self.assertRaises(ValueError):latest_assessment(self.manager,self.now)
        self.manager.policy=original;self.manager.state['orders']['new']={'status':'INTENT'}
        with self.assertRaises(ValueError):latest_assessment(self.manager,self.now)

    def test_stale_wrong_account_or_unsaved_review_rejected(self):
        with self.assertRaises(ValueError):assess_observation(self.manager,self.review,self.now+timedelta(seconds=31))
        self.review['estimated_cash_after_cost_reserve_usd']='99999'
        with self.assertRaises(ValueError):assess_observation(self.manager,self.review,self.now)
        self.store_review();self.manager.state['broker_identity']='other'
        with self.assertRaises(ValueError):assess_observation(self.manager,self.review,self.now)

    def test_save_failure_rolls_back_assessment_ledger(self):
        before=copy.deepcopy(self.manager.state)
        with patch.object(self.manager,'_save',side_effect=OSError('synthetic-storage')):
            with self.assertRaises(OSError):self.assess()
        self.assertEqual(before,self.manager.state);self.assertFalse(self.manager.ready)

    def test_restart_does_not_refresh_old_observation_time(self):
        value=self.assess();self.manager.close();self.manager=OrderManager(self.path,'kis_demo')
        self.assertEqual(latest_assessment(self.manager,self.now)['as_of'],value['as_of'])
        with self.assertRaises(ValueError):latest_assessment(self.manager,self.now+timedelta(seconds=31))

    def test_drawdown_is_based_on_observed_model_values(self):
        self.assess();self.manager.state['user_cash_account']['modeled_nav_usd']='9500'
        value=self.assess();self.assertEqual(value['maximum_observed_model_drawdown'],'0.05')
        self.assertFalse(value['external_cash_flows_verified']);self.assertFalse(value['full_day_coverage_verified'])
