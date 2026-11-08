"""한정 시험의 합성 한도/권한 검사. 실제 인증·증권사 호출은 없다."""
import unittest
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from trading.demo_session import LimitedDemoSession
from trading.orders import OrderManager


class DemoLimitTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 29, 14, tzinfo=timezone.utc)
        # 이 클래스는 세션 한도 단위 검사다. 실제 사전 원장은 별도 통합 검사에서 확인한다.
        accounting = patch('trading.demo_session.prepare_pretrade', return_value={"phase":"PREPARED"})
        accounting.start();self.addCleanup(accounting.stop)
        self.manager = Mock(spec=OrderManager)
        self.manager.state = {"mode": "kis_demo", "orders": {}, "account": {},
                              "risk_ledger": {"last_evaluation": {"source_kind": "kis_vps"}}}
        from Test.trading.cash_policy_fixtures import confirm_cash_only
        confirm_cash_only(self.manager)
        self.manager.ready = True
        self.adapter = SimpleNamespace(api=SimpleNamespace(market_client=SimpleNamespace(environment="vps"), allow_trading=False), enabled=False)
        self.session = LimitedDemoSession(self.manager, self.adapter, 'synthetic-session', 'AAPL')
        self.recovery = {"regular_recovery_verified": True, "input_kind": "live_observation",
                         "checked_at": self.now.isoformat(), "diagnostics": [],
                         "per_symbol": {"AAPL": {"continuous": True}}}
        def create(identifier, symbol, side, quantity, price, stop, quote_at):
            order = {"id": identifier, "symbol": symbol, "side": side, "quantity": quantity,
                     "price": str(price), "order_type": "LIMIT", "filled": 0, "status": "INTENT"}
            self.manager.state['orders'][identifier] = order
            return order
        self.manager.create.side_effect = create

    def arm(self):
        with patch('trading.demo_session.RiskLedger') as ledger:
            ledger.return_value.context.return_value = SimpleNamespace(eligible=True, checkpoint_hash='synthetic-proof')
            if self.manager.state['risk_ledger']['last_evaluation']['source_kind']=='kis_vps':
                with patch('trading.demo_user_basis.require_execution_basis',return_value=ledger.return_value.context.return_value):
                    self.session.arm(self.recovery, now=self.now)
            else:
                self.session.arm(self.recovery,now=self.now)

    def clock(self):
        clock = patch('trading.demo_session.datetime', wraps=datetime)
        mock = clock.start();mock.now.return_value = self.now
        self.addCleanup(clock.stop)

    def create(self, identifier, side='BUY', price='100'):
        return self.session.create(identifier, side, 1, price, '90', self.now.isoformat())

    def test_default_is_disarmed(self):
        self.clock()
        with self.assertRaises(ValueError):self.create('a')
        self.manager.create.assert_not_called()
        self.assertFalse(self.adapter.enabled)
        self.assertFalse(self.adapter.api.allow_trading)

    def test_prod_and_replay_are_always_blocked(self):
        self.adapter.api.market_client.environment='prod'
        with self.assertRaises(ValueError):LimitedDemoSession(self.manager,self.adapter,'a','AAPL')
        self.adapter.api.market_client.environment='vps';self.manager.state['replay_only']=True
        with self.assertRaises(ValueError):LimitedDemoSession(self.manager,self.adapter,'a','AAPL')

    def test_missing_regular_recovery_blocks_before_risk(self):
        self.recovery['regular_recovery_verified']=False
        with patch('trading.demo_session.RiskLedger') as ledger:
            with self.assertRaises(ValueError):self.session.arm(self.recovery,now=self.now)
            ledger.assert_not_called()

    def test_missing_risk_proof_cannot_enable_orders(self):
        with patch('trading.demo_session.RiskLedger') as ledger:
            ledger.return_value.validate_snapshot.side_effect=ValueError('risk_evaluation_unavailable')
            with self.assertRaises(ValueError):self.session.arm(self.recovery,now=self.now)
        self.assertFalse(self.session.armed);self.assertFalse(self.adapter.api.allow_trading)

    def test_synthetic_risk_does_not_authorize_demo(self):
        self.manager.state['risk_ledger']['last_evaluation']['source_kind']='synthetic'
        with self.assertRaises(ValueError):self.arm()
        self.assertFalse(self.session.armed)

    def test_one_share_and_concurrent_share_limit(self):
        self.arm();self.clock()
        with self.assertRaises(ValueError):self.session.create('too-many','BUY',2,'100','90',self.now.isoformat())
        self.create('first')
        with self.assertRaises(ValueError):self.create('second')

    def test_gross_budget_includes_cancelled_intents(self):
        self.arm();self.clock();order=self.create('a',price='300');order['status']='CANCELLED'
        with self.assertRaises(ValueError):self.create('b',price='250')

    def test_existing_cost_reserve_is_inside_500_budget(self):
        self.arm();self.clock()
        with self.assertRaises(ValueError):self.create('a',price='500')
        self.manager.create.assert_not_called()

    def test_cannot_sell_original_account_holdings(self):
        self.arm();self.clock()
        self.manager.state['account']['positions']={'AAPL':100}
        with self.assertRaises(ValueError):self.create('sell-existing',side='SELL')

    def test_only_own_actual_filled_share_can_be_sold_once(self):
        self.arm();self.clock();order=self.create('buy');order.update(status='FILLED',filled=1)
        self.create('sell',side='SELL')
        with self.assertRaises(ValueError):self.create('sell-twice',side='SELL')

    def test_unknown_response_disarms_and_never_resends(self):
        self.arm();self.clock();self.create('a')
        self.manager.dispatch.side_effect=RuntimeError('synthetic_response_lost')
        with self.assertRaises(RuntimeError):self.session.submit('a')
        with self.assertRaises(ValueError):self.session.submit('a')
        self.manager.dispatch.assert_called_once();self.assertFalse(self.adapter.api.allow_trading)

    def test_attempt_limit_and_expiry(self):
        self.arm();self.clock();self.create('a');self.session.state['buy_attempts']=2
        with self.assertRaises(ValueError):self.session.submit('a')
        self.manager.dispatch.assert_not_called()
        self.session.expires_at=self.now-timedelta(seconds=1)
        with self.assertRaises(ValueError):self.create('b')
        self.assertFalse(self.session.armed)

    def test_contract_change_is_blocked_before_transmission(self):
        self.arm();self.clock();order=self.create('a');order['quantity']=99
        with self.assertRaises(ValueError):self.session.submit('a')
        self.manager.dispatch.assert_not_called();self.assertFalse(self.session.armed)

    def test_restart_never_rearms(self):
        self.arm()
        other=LimitedDemoSession(self.manager,self.adapter,'synthetic-session','AAPL')
        self.assertFalse(other.armed);self.assertFalse(self.adapter.enabled)

    def test_reconciliation_state_replacement_does_not_lose_attempts(self):
        import copy
        self.manager.state=copy.deepcopy(self.manager.state)
        self.session.state['buy_attempts']=2
        self.assertEqual(self.manager.state['limited_demo_session']['buy_attempts'],2)

    def test_cancel_remains_available_after_new_buy_disarm(self):
        self.arm();self.clock();order=self.create('a');order['status']='ACCEPTED'
        self.session.disarm();self.manager.can_cancel.return_value=True
        self.session.cancel('a')
        self.manager.cancel.assert_called_once();self.assertFalse(self.adapter.api.allow_trading)

    def test_rearm_does_not_extend_first_deadline(self):
        self.arm();deadline=self.session.expires_at
        self.now+=timedelta(minutes=1);self.recovery['checked_at']=self.now.isoformat()
        self.arm();self.assertEqual(self.session.expires_at,deadline)

    def test_cancel_only_own_verified_order_and_no_repeat(self):
        self.arm();self.clock();order=self.create('a');order['status']='ACCEPTED'
        self.manager.can_cancel.return_value=False
        with self.assertRaises(ValueError):self.session.cancel('a')
        self.manager.cancel.assert_not_called()
        self.manager.can_cancel.return_value=True;self.session.cancel('a')
        with self.assertRaises(ValueError):self.session.cancel('a')
        self.manager.cancel.assert_called_once()

    def test_intent_storage_failure_disarms_before_dispatch(self):
        self.arm();self.clock();self.manager._save.side_effect=RuntimeError('synthetic_disk_failure')
        with self.assertRaises(RuntimeError):self.create('a')
        self.assertFalse(self.session.armed);self.assertFalse(self.adapter.api.allow_trading)
        self.manager.dispatch.assert_not_called()

    def test_cancel_storage_failure_disarms_before_http(self):
        self.arm();self.clock();order=self.create('a');order['status']='ACCEPTED'
        self.manager.can_cancel.return_value=True;self.manager._save.side_effect=RuntimeError('synthetic_disk_failure')
        with self.assertRaises(RuntimeError):self.session.cancel('a')
        self.assertFalse(self.session.armed);self.assertFalse(self.adapter.api.allow_trading)
        self.manager.cancel.assert_not_called()

    def test_profile_budget_applies_to_session_create(self):
        import json,tempfile
        from pathlib import Path
        from paths import CONFIG_ROOT
        profile=json.loads((CONFIG_ROOT/'kis-demo-session.json').read_text(encoding='utf-8'))
        profile['maximum_gross_buy_commitments_usd']='50'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';path.write_text(json.dumps(profile),encoding='utf-8')
            self.manager.state.pop('limited_demo_session')
            self.session=LimitedDemoSession(self.manager,self.adapter,'strict','AAPL',profile=path)
            self.arm();self.clock()
            with self.assertRaisesRegex(ValueError,'500_usd_limit'):self.create('too-large',price='100')
            self.manager.create.assert_not_called()

    def test_symbol_disagreement_is_blocked(self):
        with self.assertRaisesRegex(ValueError,'profile_symbol_mismatch'):
            LimitedDemoSession(self.manager,self.adapter,'wrong','MSFT')

    def test_reduction_activation_cannot_create_new_buy(self):
        self.arm();self.clock();order=self.create('own-buy');order.update(status='FILLED',filled=1)
        self.session.prepare_reduction()
        with self.assertRaisesRegex(ValueError,'reduction_never_authorizes_buy'):self.create('another-buy')
        self.assertEqual(self.manager.create.call_count,1)
