"""조회 금액의 의미 차이를 임의 기준 자금으로 바꾸지 않는 합성 검사."""
import unittest
from trading.demo_readiness import assess_readonly_inputs


class DemoReadinessTests(unittest.TestCase):
    def test_capacity_is_not_initial_capital(self):
        report={'buying_power':'100000.00','reported_usd_deposit_settlement_basis':'0.000000','issues':[]}
        result=assess_readonly_inputs(report,[])
        self.assertEqual(result['buying_power_minus_reported_deposit'],'100000.000000')
        self.assertIsNone(result['observed_inputs']['initial_nav_usd'])
        self.assertIsNone(result['observed_inputs']['execution_cash_usd'])
        self.assertFalse(result['new_orders_allowed'])
        self.assertIn('final_fee_source_unproven',result['issues'])

    def test_equal_cash_fields_do_not_prove_history_or_costs(self):
        result=assess_readonly_inputs({'buying_power':'100','reported_usd_deposit_settlement_basis':'100','issues':[]},[])
        self.assertFalse(result['risk_ingested']);self.assertFalse(result['initial_basis_established'])
        self.assertIn('cash_movement_source_unproven',result['issues'])

    def test_sources_and_existing_blockers_remain(self):
        result=assess_readonly_inputs({'issues':['untracked_remote_order']},[{'operation':'query','at':'2026-10-29T14:00:00+00:00'}])
        self.assertEqual(result['pages_by_operation'],{'query':1})
        self.assertIn('untracked_remote_order',result['issues'])
