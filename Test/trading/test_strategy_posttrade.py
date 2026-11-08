"""체결→정산→다음 진입의 합성 계약 검사. 실제 KIS 조회·주문은 전혀 사용하지 않는다."""
import copy
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from types import SimpleNamespace

from trading.risk_ledger import digest, RiskLedger
from trading.strategy_posttrade import connect_sources, current_settlement, refresh_from_provider, settlement_status
from trading.strategy_model_basis import build_sources, ingest, context
from trading.demo_balance import connect_balance_observation
from trading.user_cash import update_user_cash
from trading.demo_user_basis import normalize_owned_history


class StrategyPosttradeTests(unittest.TestCase):
    def setUp(self):
        from Test.trading.test_strategy_model_basis import StrategyModelBasisTests
        fixture = StrategyModelBasisTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.manager, self.api, self.normalized = fixture.manager, fixture.api, fixture.normalized
        fixture.ready()
        self.now = datetime.now(timezone.utc)
        baseline = self.now - timedelta(seconds=20)
        self.manager.state['user_cash_account']['baseline']['enrolled_at'] = baseline.isoformat()
        day = self.now.strftime('%Y%m%d')
        for identifier, side, price, number in [('buy', 'BUY', '100', '111'), ('sell', 'SELL', '110', '112')]:
            self.manager.state['orders'][identifier] = {
                'id': identifier, 'symbol': 'AAPL', 'side': side, 'quantity': 1, 'filled': 1,
                'notional': price, 'price': price, 'order_type': 'LIMIT', 'status': 'FILLED',
                'broker_id': day + ':' + number, 'strategy_owner': 'strategy-test',
                'created_at': baseline.isoformat(), 'quote_at': baseline.isoformat()}
        self.fills = [self.fill('b', 'buy', 'BUY', '100', 10), self.fill('s', 'sell', 'SELL', '110', 5)]
        h = digest({'synthetic_contract': 'not_actual_KIS'})
        start = baseline.isoformat()
        at = self.now.isoformat()
        self.sources = {'account_fingerprint': self.manager.state['broker_identity'], 'mode': 'kis_demo',
            'cash': '100008', 'nav': '100008', 'as_of': at, 'window_start': start,
            'source_times': {key: at for key in ('cash', 'balances', 'fills', 'cash_events', 'quotes')},
            'source_hashes': {'fixture': h}, 'fills': self.fills, 'cash_events': [], 'quotes': {},
            'source_kind': 'kis_vps',
            'coverage': {key: {'from': start, 'through': at, 'complete': True}
                         for key in ('cash', 'balances', 'fills', 'cash_events', 'quotes')},
            'provenance': {key: {'origin': 'mock_official_provider_not_actual', 'sha256': h,
                               'currency': 'USD', 'basis': basis}
                           for key, basis in {'cash': 'execution_cash', 'nav': 'usd_net_assets',
                                              'fills': 'executions', 'cash_events': 'movements'}.items()}}
        self.normalized['observed_inputs'] = {'buying_power_usd': '100008'}
        self.manager._execution_observation_valid = True
        self.manager.state['execution_observation'] = {'as_of': at,
            'account_fingerprint': self.manager.state['broker_identity'], 'inventory': {'positions': {}}}

    def fill(self, identifier, order_id, side, notional, seconds):
        return {'id': identifier, 'order_id': order_id, 'symbol': 'AAPL', 'side': side,
                'quantity': 1, 'notional': notional, 'fees': '1', 'fees_final': True,
                'at': (self.now - timedelta(seconds=seconds)).isoformat()}

    def bind(self, sources=None):
        value = sources or self.sources
        # 실제 API가 아니라 시험용 공급기 경계를 재현한다.
        self.manager._captured_execution_cash_sources = {'cash': value['cash'], 'nav': value['nav'],
            'source_hashes': value['source_hashes'], 'normalized_sources_hash': digest(value)}

    def connect(self):
        self.bind()
        return connect_sources(self.manager, self.normalized, self.sources, self.now)

    def fresh_history(self):
        rows = []
        for order in self.manager.state['orders'].values():
            rows.append({'ord_dt': order['broker_id'].split(':')[0], 'odno': order['broker_id'].split(':')[1],
                'orgn_odno': '0000', 'ft_ord_qty': '1', 'ft_ccld_qty': '1', 'nccs_qty': '0',
                'tr_crcy_cd': 'USD', 'prcs_stat_name': '체결', 'rjct_rson': '0',
                'sll_buy_dvsn_cd': '02' if order['side'] == 'BUY' else '01', 'pdno': 'AAPL',
                'ft_ord_unpr3': order['price'], 'ft_ccld_amt3': order['notional'], 'ord_dvsn': '00'})
        for index in [0, -1]:
            record = self.api.records[index]
            record['payload']['output'] = copy.deepcopy(rows)
            record['sha256'] = digest(record['payload'])
        capacity = self.api.records[-2]
        capacity['payload']['output']['ovrs_ord_psbl_amt'] = self.sources['cash']
        capacity['sha256'] = digest(capacity['payload'])
        link = connect_balance_observation(self.manager, self.api.records)
        remote = normalize_owned_history(self.manager, rows)
        config = {'mode': 'kis_demo', 'currency': 'USD', 'cash_usd': '100000',
                  'source': 'user_designation', 'authorized_on': '2026-11-02'}
        update_user_cash(self.manager, link, remote, config)

    def test_round_trip_final_costs_cash_realized_and_next_entry_proof(self):
        result = self.connect()
        self.assertEqual(result['calculation']['realized_pnl_after_cost'], '8.000000')
        self.assertEqual(result['calculation']['fees'], '2.000000')
        self.fresh_history()
        proof = ingest(self.manager, build_sources(self.manager, self.api, self.normalized))
        self.assertTrue(proof.eligible)
        self.assertEqual(proof.positions, {})
        from trading.buying_power import bind_api_buying_power
        from trading.reconciliation import normalize_snapshot
        remote=normalize_owned_history(self.manager,self.api.records[-1]['payload']['output'])
        power=bind_api_buying_power(self.manager,self.api.records[-2],self.normalized['inventory'])
        snapshot=normalize_snapshot([],self.api.records[-2]['payload'],proof,remote,
            buying_power_service='unknown',buying_power_evidence=power)
        self.manager.reconcile(snapshot,remote,complete=True)
        # 신규 의도를 만든 것만으로 확정 정산 봉인이 깨지지 않는다.
        self.manager.create('next-entry', 'AAPL', 'BUY', 1, '100', '97', self.now.isoformat())
        self.assertTrue(context(self.manager).eligible)
        self.assertFalse(self.manager.state['risk_ledger']['last_evaluation']['broker_cash_verified'])

    def test_final_fee_does_not_need_preexisting_risk_approval(self):
        self.manager.ready = False
        self.assertEqual(self.connect()['phase'], 'RECONCILED')

    def test_duplicate_refresh_does_not_double_fees_or_pnl(self):
        first = self.connect()
        second = self.connect()
        self.assertEqual(first['calculation'], second['calculation'])
        self.assertEqual(len(self.manager.state['strategy_settlement']['fills']), 2)

    def test_missing_provider_is_explicit_and_does_not_enable_orders(self):
        self.manager._strategy_settlement_binding = 'old'
        result = refresh_from_provider(self.manager, SimpleNamespace(), self.normalized)
        self.assertFalse(result['connected'])
        self.assertIsNone(self.manager._strategy_settlement_binding)

    def test_json_claim_without_full_runtime_source_capture_is_rejected(self):
        self.bind()
        self.manager._captured_execution_cash_sources.pop('normalized_sources_hash')
        with self.assertRaisesRegex(ValueError, 'full_source_capture'):
            connect_sources(self.manager, self.normalized, self.sources)

    def test_missing_fee_is_not_zero(self):
        self.sources['fills'][0]['fees_final'] = False
        self.bind()
        with self.assertRaises(ValueError): connect_sources(self.manager, self.normalized, self.sources)

    def test_missing_or_duplicate_execution_is_rejected(self):
        for fills in [[self.fills[0]], [self.fills[0], self.fills[0], self.fills[1]]]:
            value = copy.deepcopy(self.sources); value['fills'] = fills; self.bind(value)
            with self.subTest(count=len(fills)), self.assertRaises(ValueError):
                connect_sources(self.manager, self.normalized, value)

    def test_unexplained_cash_difference_rejected(self):
        self.sources['cash'] = self.sources['nav'] = '101008'
        with self.assertRaisesRegex(ValueError, 'cash_inventory_or_cost'): self.connect()

    def test_deposit_not_counted_as_profit(self):
        self.sources['cash'] = self.sources['nav'] = '101008'
        self.sources['cash_events'] = [{'id': 'deposit', 'at': (self.now-timedelta(seconds=2)).isoformat(),
                                      'kind': 'DEPOSIT', 'amount': '1000'}]
        result = self.connect()['calculation']
        self.assertEqual(result['external_flow'], '1000.000000')
        self.assertEqual(result['realized_pnl_after_cost'], '8.000000')
        self.assertEqual(result['daily_loss_ratio'], '0')

    def test_user_cash_includes_verified_deposit_once(self):
        self.sources['cash'] = self.sources['nav'] = '101008'
        self.sources['cash_events'] = [{'id': 'deposit', 'at': (self.now-timedelta(seconds=2)).isoformat(),
                                      'kind': 'DEPOSIT', 'amount': '1000'}]
        self.connect(); self.fresh_history(); self.fresh_history()
        self.assertEqual(self.manager.state['user_cash_account']['cash_usd'], '101008.000000')

    def test_manual_trade_and_wrong_account_block(self):
        self.manager.state['orders']['buy'].pop('strategy_owner')
        with self.assertRaises(ValueError): self.connect()

    def test_stale_original_time_and_coverage_gap_block(self):
        for change in ['time', 'coverage']:
            value = copy.deepcopy(self.sources)
            if change == 'time': value['source_times']['cash'] = (self.now-timedelta(seconds=31)).isoformat()
            else: value['coverage']['cash_events']['complete'] = False
            self.bind(value)
            with self.subTest(change=change), self.assertRaises(ValueError):
                connect_sources(self.manager, self.normalized, value)

    def test_restart_cannot_reuse_persisted_eligible_boolean(self):
        self.connect(); self.manager._strategy_settlement_binding = None
        with self.assertRaises(ValueError): current_settlement(self.manager)

    def test_changed_or_missing_historical_fill_requires_review(self):
        self.connect()
        self.sources['fills'][0]['fees'] = '0.9'
        with self.assertRaisesRegex(ValueError, 'revision_or_missing'): self.connect()

    def test_partial_fill_cost_notional_mismatch_blocks(self):
        self.sources['fills'][0]['quantity'] = 2
        with self.assertRaisesRegex(ValueError, 'cumulative_fill'): self.connect()

    def test_storage_failure_rolls_back_costs_and_clears_runtime_proof(self):
        before = copy.deepcopy(self.manager.state)
        self.bind()
        with patch.object(self.manager, '_save', side_effect=OSError('synthetic_full_disk')):
            with self.assertRaises(OSError): connect_sources(self.manager, self.normalized, self.sources)
        self.assertEqual(before, self.manager.state)
        self.assertIsNone(self.manager._strategy_settlement_binding)
        self.assertFalse(self.manager.ready)

    def test_restore_gate_and_mode_change_block(self):
        self.manager.state['restore_gate'] = {'pending': True}
        with self.assertRaises(ValueError): self.connect()

    def test_synthetic_settlement_never_arms_operating_context(self):
        self.sources['source_kind'] = 'synthetic'
        self.manager.state['replay_only'] = True
        result = self.connect()
        self.assertEqual(result['source_kind'], 'synthetic')
        with self.assertRaises(ValueError): current_settlement(self.manager)

    def test_no_network_or_financial_transport_called(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('must_not_send')) as network:
            self.connect()
        self.assertEqual(network.call_count, 0)

    def test_loss_episode_and_cooldown_survive_recalculation(self):
        sell=self.manager.state['orders']['sell']; sell.update(price='90',notional='90')
        self.sources['fills'][1]['notional']='90'
        self.sources['cash']=self.sources['nav']='99988'
        self.normalized['observed_inputs']['buying_power_usd']='99988'
        self.manager.policy['consecutive_losses']=1
        result=self.connect()['calculation']
        self.assertEqual(result['realized_pnl_after_cost'],'-12.000000')
        self.assertEqual(result['consecutive_losses'],1)
        self.assertTrue(result['consecutive_loss_cooldown']); self.assertFalse(result['eligible'])
        self.assertEqual(self.connect()['calculation']['consecutive_losses'],1)

    def test_existing_daily_halt_is_not_erased(self):
        from trading.risk_ledger import local_day
        day=local_day(self.now.isoformat())
        self.manager.state['risk_ledger']['days'][day]={'halted':True,'baseline_equity':'100000',
            'baseline_flow':'0','baseline_at':(self.now-timedelta(seconds=20)).isoformat()}
        result=self.connect()['calculation']
        self.assertTrue(result['day_halted']); self.assertFalse(result['eligible'])

    def test_cash_event_reversal_not_silently_overwritten(self):
        self.sources['cash']=self.sources['nav']='100018'
        self.sources['cash_events']=[{'id':'dividend','at':(self.now-timedelta(seconds=1)).isoformat(),
                                     'kind':'DIVIDEND','amount':'10'}]
        self.connect()
        self.sources['cash_events'][0]['amount']='11'
        with self.assertRaisesRegex(ValueError,'revision_or_missing'): self.connect()

    def test_reentry_uses_current_remaining_cost_not_old_buy_average(self):
        from trading.strategy_posttrade import owned_position_basis
        self.connect()
        order=copy.deepcopy(self.manager.state['orders']['buy'])
        order.update(id='reentry',price='200',notional='200',broker_id=self.now.strftime('%Y%m%d')+':113')
        self.manager.state['orders']['reentry']=order
        # 새 체결은 기존 정산에 없으므로 원격 현재 원가와 비용 예약을 쓴다.
        basis=owned_position_basis(self.manager,'strategy-test','AAPL',
            {'positions':{'AAPL':1},'position_costs':{'AAPL':'200'}},'0.003')
        self.assertEqual(basis['cost'],'200.600000000'); self.assertFalse(basis['costs_final'])

    def test_partial_sale_keeps_remaining_final_cost_basis(self):
        from trading.strategy_posttrade import owned_position_basis
        buy=self.manager.state['orders']['buy']; buy.update(quantity=2,filled=2,notional='200')
        self.sources['fills'][0].update(quantity=2,notional='200')
        self.sources['cash']='99908'; self.sources['nav']='100018'
        self.sources['quotes']={'AAPL':{'at':self.now.isoformat(),'price':'110'}}
        self.normalized['inventory']['positions']={'AAPL':1}
        self.normalized['inventory']['position_costs']={'AAPL':'100.5'}
        self.normalized['observed_inputs']['buying_power_usd']='99908'
        self.manager.state['execution_observation']['inventory']['positions']={'AAPL':1}
        self.connect()
        basis=owned_position_basis(self.manager,'strategy-test','AAPL',self.normalized['inventory'],'0.003')
        self.assertEqual(basis['cost'],'100.500000'); self.assertTrue(basis['costs_final'])

    def test_local_status_is_read_only_and_redacts_identity(self):
        from execution_status import read_status
        self.connect(); self.manager._save()
        before=self.fixture.path.read_bytes() if hasattr(self.fixture,'path') else None
        path=self.manager.connection.execute('PRAGMA database_list').fetchone()[2]
        value=read_status(path,'kis_demo')
        self.assertFalse(value['new_orders_allowed'])
        self.assertEqual(value['filled_order_count'],2)
        self.assertNotIn(self.manager.state['broker_identity'],str(value))

    def test_absent_status_does_not_create_a_ledger(self):
        from pathlib import Path
        from execution_status import read_status
        absent=Path(self.fixture.temp.name)/'absent.sqlite' if hasattr(self.fixture,'temp') else Path(self.fixture.manager.connection.execute('PRAGMA database_list').fetchone()[2]).with_name('absent.sqlite')
        value=read_status(absent,'kis_demo')
        self.assertFalse(value['ledger_present']); self.assertFalse(absent.exists())

    def test_provider_callback_connects_without_enabling_http(self):
        def provider(manager, normalized):
            self.bind()
            return self.sources
        value=refresh_from_provider(self.manager,SimpleNamespace(settlement_source_provider=provider),self.normalized)
        self.assertTrue(value['connected']); self.assertFalse(self.manager.ready)
        self.assertFalse(self.api.allow_trading)

    def test_synthetic_label_cannot_be_reused_after_replay_flag_removed(self):
        self.sources['source_kind']='synthetic'; self.manager.state['replay_only']=True
        self.connect(); self.manager.state['replay_only']=False
        with self.assertRaises(ValueError): current_settlement(self.manager)

    def test_model_snapshot_is_not_nested_inside_next_settlement(self):
        self.manager.state['risk_ledger']['strategy_sources']={'large_previous_snapshot':{'risk_candidate':{'old':'nested'}}}
        candidate=self.connect()['risk_candidate']
        self.assertNotIn('strategy_sources',candidate)

    def test_drawdown_is_observed_and_excludes_deposit(self):
        self.sources['cash']=self.sources['nav']='101008'
        self.sources['cash_events']=[{'id':'deposit','at':(self.now-timedelta(seconds=1)).isoformat(),
                                    'kind':'DEPOSIT','amount':'1000'}]
        result=self.connect()['calculation']
        self.assertEqual(result['observed_max_drawdown_ratio'],'0')
        self.assertEqual(result['observed_peak_adjusted_equity'],'100008.000000')

    def test_verified_round_trip_allows_next_mock_vps_dispatch(self):
        from unittest.mock import Mock
        from trading.buying_power import bind_api_buying_power
        from trading.reconciliation import normalize_snapshot
        self.connect(); self.fresh_history()
        proof=ingest(self.manager,build_sources(self.manager,self.api,self.normalized))
        remote=normalize_owned_history(self.manager,self.api.records[-1]['payload']['output'])
        power=bind_api_buying_power(self.manager,self.api.records[-2],self.normalized['inventory'])
        snapshot=normalize_snapshot([],self.api.records[-2]['payload'],proof,remote,
            buying_power_service='unknown',buying_power_evidence=power)
        self.manager.reconcile(snapshot,remote,complete=True)
        order=self.manager.create('next','AAPL','BUY',1,'100','97',self.now.isoformat())
        order['strategy_owner']='strategy-test'; self.manager._save()
        response=Mock(); response.status=200; response.headers={}
        response.read.return_value=b'{"rt_cd":"0","output":{"ODNO":"113"}}'
        response.__enter__=Mock(return_value=response); response.__exit__=Mock(return_value=False)
        self.fixture.adapter.enabled=True; self.api.allow_trading=True
        with patch('broker.sessions.regular_session',return_value={'id':'US:synthetic'}),patch('urllib.request.urlopen',return_value=response) as network:
            self.manager.dispatch('next',self.fixture.adapter)
        self.assertEqual(network.call_count,1)
        self.assertEqual(order['status'],'ACCEPTED'); self.assertEqual(order['filled'],0)

    def test_failed_new_settlement_invalidates_previous_runtime_proof(self):
        self.connect()
        self.sources['cash']='99999'
        with self.assertRaises(ValueError): self.connect()
        with self.assertRaises(ValueError): current_settlement(self.manager)

    def test_previously_verified_cash_events_survive_restart_display(self):
        self.sources['cash']=self.sources['nav']='101008'
        self.sources['cash_events']=[{'id':'deposit','at':(self.now-timedelta(seconds=1)).isoformat(),
                                     'kind':'DEPOSIT','amount':'1000'}]
        self.connect(); self.fresh_history()
        self.manager._strategy_settlement_binding=None
        self.fresh_history()
        self.assertEqual(self.manager.state['user_cash_account']['cash_usd'],'101008.000000')
        with self.assertRaises(ValueError): current_settlement(self.manager)

    def test_broker_gross_cost_and_verified_fee_basis_are_kept_separate(self):
        buy=self.manager.state['orders']['buy']; buy.update(quantity=2,filled=2,notional='200')
        self.sources['fills'][0].update(quantity=2,notional='200')
        self.sources['cash']='99908'; self.sources['nav']='100018'
        self.sources['quotes']={'AAPL':{'at':self.now.isoformat(),'price':'110'}}
        self.normalized['inventory']['positions']={'AAPL':1}
        self.normalized['inventory']['position_costs']={'AAPL':'100'}
        self.normalized['observed_inputs']['buying_power_usd']='99908'
        self.manager.state['execution_observation']['inventory']['positions']={'AAPL':1}
        value=self.connect()
        self.assertEqual(value['reported_position_costs'],{'AAPL':'100'})
        self.assertEqual(value['calculation']['position_costs'],{'AAPL':'100.500000'})
        self.assertFalse(value['reported_cost_semantics_certified'])
