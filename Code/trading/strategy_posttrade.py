"""전략 모의계좌의 확정 정산을 기존 위험 계산에 연결한다.

조회된 누적 주문으로 개별 체결이나 최종 비용을 발명하지 않는다. 기존 정규화
공급기가 제공한 현금·체결·비용·자금 사건을 같은 계약으로 검사한다. 공급기가
없으면 비용 대기를 유지한다. 이 모듈은 HTTP·주문·설정 변경을 수행하지 않는다.
금액은 risk_ledger.amount의 USD 6자리 HALF_EVEN 규칙을 사용한다.
"""
import copy
from datetime import datetime, timezone
from decimal import Decimal

from strategy.engine import parse_timestamp
from trading.risk_ledger import RiskLedger, amount, digest, TOLERANCE
from trading.order_contract import broker_key


def order_contract_hash(manager):
    """전송 전 새 INTENT는 제외하고 증권사 연결 주문의 누적 상태를 봉인한다."""
    return digest({key: row for key, row in manager.state['orders'].items()
                   if row.get('broker_id') or row.get('filled')})


def settlement_status(manager):
    """재시작 후에도 보존되는 진행 상태다. 조회 결과가 주문 승인이라는 뜻은 아니다."""
    settlement = manager.state.get('strategy_settlement', {})
    pending = [order['id'] for order in manager.state['orders'].values()
               if order.get('filled') and manager.state.get('demo_settlement', {}).get('orders', {})
               .get(order.get('broker_id'), {}).get('final_costs_usd') is None]
    return {'phase': 'COSTS_PENDING' if pending else settlement.get('phase', 'NO_SETTLEMENT_SOURCE'),
            'pending_cost_order_count': len(pending),
            'as_of': settlement.get('as_of'), 'source_kind': settlement.get('source_kind'),
            'reason': settlement.get('reason', 'normalized_final_cost_and_cash_source_required'),
            'new_orders_allowed': False}


def owned_position_basis(manager, owner, symbol, inventory, reserve_ratio):
    """재진입 원가에 과거에 청산한 매수를 섞지 않는다. 확정 비용과 보수적 예약을 구분한다."""
    orders = manager.state['orders']
    own = [row for row in orders.values() if row.get('strategy_owner') == owner and row['symbol'] == symbol]
    remaining = sum(row['filled'] * (1 if row['side'] == 'BUY' else -1) for row in own)
    if remaining <= 0:
        raise ValueError('strategy_owned_positive_position_required')
    settled = manager.state.get('strategy_settlement', {})
    fills = list(settled.get('fills', {}).values())
    covered = all(sum(fill['quantity'] for fill in fills if fill['order_id'] == row['id']) == row['filled']
                  and sum((amount(fill['notional']) for fill in fills if fill['order_id'] == row['id']), Decimal(0))
                  == amount(row['notional']) for row in own if row['filled'])
    if settled and covered:
        quantity, cost, entry_at = 0, Decimal(0), None
        for fill in sorted(fills, key=lambda row: (parse_timestamp(row['at']), row['id'])):
            order = orders.get(fill['order_id'], {})
            if order.get('strategy_owner') != owner or fill['symbol'] != symbol:
                continue
            if fill['side'] == 'BUY':
                if not quantity: entry_at = fill['at']
                quantity += fill['quantity']
                cost += amount(fill['notional']) + amount(fill['fees'])
            else:
                if not 0 < fill['quantity'] <= quantity:
                    raise ValueError('strategy_owned_lot_sequence_invalid')
                allocated = cost if fill['quantity'] == quantity else amount(cost * fill['quantity'] / quantity)
                quantity -= fill['quantity']; cost -= allocated
        if quantity != remaining:
            raise ValueError('strategy_owned_settlement_quantity_mismatch')
        return {'quantity': quantity, 'cost': str(cost), 'costs_final': True, 'entry_at': entry_at}
    # 비용 대기 중이라도 관측된 보유의 매도 판단은 계속한다. 원격의 현재 남은 원가를 쓴다.
    if inventory['positions'].get(symbol) != remaining:
        raise ValueError('strategy_shared_symbol_cost_allocation_requires_evidence')
    cost = amount(inventory['position_costs'][symbol]) * (Decimal(1) + Decimal(str(reserve_ratio)))
    return {'quantity': remaining, 'cost': str(cost), 'costs_final': False, 'entry_at': None}


def _matching_fills(manager, evidence):
    """누적 주문과 개별 정산의 수량·금액을 전량 대조한다. 누락/수동 체결은 거절한다."""
    received = {}
    totals = {}
    for fill in evidence['fills']:
        identifier = fill['id']
        if not isinstance(identifier, str) or not identifier or identifier in received:
            raise ValueError('strategy_duplicate_settlement_fill')
        received[identifier] = copy.deepcopy(fill)
        order = manager.state['orders'].get(fill['order_id'])
        if (not order or not order.get('strategy_owner') or not order.get('broker_id')
                or (order['symbol'], order['side']) != (fill['symbol'], fill['side'])
                or type(fill['quantity']) is not int or fill['quantity'] <= 0
                or fill['fees_final'] is not True):
            raise ValueError('strategy_settlement_order_or_cost_invalid')
        if not (parse_timestamp(evidence['window_start']) <= parse_timestamp(fill['at'])
                <= parse_timestamp(evidence['as_of'])):
            raise ValueError('strategy_settlement_fill_outside_window')
        if amount(fill['notional']) <= 0:
            raise ValueError('strategy_settlement_notional_invalid')
        amount(fill['fees'])
        total = totals.setdefault(order['id'], {'quantity': 0, 'notional': Decimal(0)})
        total['quantity'] += fill['quantity']
        total['notional'] += amount(fill['notional'])
    for order in manager.state['orders'].values():
        if not order.get('filled'):
            continue
        total = totals.get(order['id'], {})
        if (total.get('quantity') != order['filled']
                or total.get('notional') != amount(order['notional'])):
            raise ValueError('strategy_settlement_cumulative_fill_mismatch')
    return received


def _remaining_costs(fills, include_fees):
    """확인된 체결 순서로 남은 원가를 계산한다. 증권사 원가의 비용 포함 여부는 추정하지 않는다."""
    lots = {}
    for fill in sorted(fills.values(), key=lambda row: (parse_timestamp(row['at']), row['id'])):
        lot = lots.setdefault(fill['symbol'], {'quantity': 0, 'cost': Decimal(0)})
        if fill['side'] == 'BUY':
            lot['quantity'] += fill['quantity']
            lot['cost'] += amount(fill['notional']) + (amount(fill['fees']) if include_fees else Decimal(0))
        else:
            if not 0 < fill['quantity'] <= lot['quantity']:
                raise ValueError('strategy_settlement_sell_without_cost_basis')
            allocated = lot['cost'] if lot['quantity'] == fill['quantity'] else amount(lot['cost'] * fill['quantity'] / lot['quantity'])
            lot['quantity'] -= fill['quantity']; lot['cost'] -= allocated
    return {symbol: str(lot['cost']) for symbol, lot in lots.items() if lot['quantity']}


def connect_sources(manager, normalized, sources, now=None):
    """검산된 공급기 자료를 연결한다. 승인 전 비용 확정을 요구하는 순환 의존을 없앤다.

    sources는 기존 assemble_risk_evidence 계약이다. 실제 자료는 그 함수의 현재
    프로세스 캡처 연결을 요구하고, 합성 자료는 replay_only 원장에서만 허용한다.
    실제 KIS 응답에 없는 필드를 보완하거나 임의 파일을 공식 자료로 승격하지 않는다.
    """
    from trading.demo_readiness import assemble_risk_evidence
    from trading.strategy_model_basis import KIND, selected_mode
    now = now or datetime.now(timezone.utc)
    manager.ready = False
    manager._strategy_settlement_binding = None
    manager._strategy_sources_binding = None
    manager._strategy_evaluation_binding = None
    if manager.state['mode'] != 'kis_demo' or manager.state['alias'] != 'strategies' or manager.state.get('restore_gate'):
        raise ValueError('strategy_settlement_account_scope_invalid')
    selected = selected_mode(manager)
    evidence = assemble_risk_evidence(manager, normalized, sources)
    if evidence['source_kind'] == 'kis_vps':
        captured = getattr(manager, '_captured_execution_cash_sources', {})
        if captured.get('normalized_sources_hash') != digest(sources):
            raise ValueError('strategy_settlement_full_source_capture_required')
    if evidence['source_kind'] == 'synthetic' and not manager.state.get('replay_only'):
        raise ValueError('strategy_synthetic_settlement_requires_replay')
    cash_model = manager.state.get('user_cash_account')
    if not cash_model or cash_model['baseline']['account_fingerprint'] != manager.state['broker_identity']:
        raise ValueError('strategy_settlement_baseline_missing')
    baseline_at = cash_model['baseline']['enrolled_at']
    if parse_timestamp(evidence['window_start']) > parse_timestamp(baseline_at):
        raise ValueError('strategy_settlement_history_gap')
    if not 0 <= (now - parse_timestamp(evidence['as_of'])).total_seconds() <= 30:
        raise ValueError('strategy_settlement_stale')
    for field in ('cash', 'balances', 'fills', 'cash_events', 'quotes'):
        stamp = parse_timestamp(evidence['source_times'][field])
        if not 0 <= (now - stamp).total_seconds() <= 30 or stamp > parse_timestamp(evidence['as_of']):
            raise ValueError('strategy_settlement_source_stale')
    observation = manager.state.get('execution_observation', {})
    if (not getattr(manager, '_execution_observation_valid', False)
            or observation.get('account_fingerprint') != manager.state['broker_identity']
            or observation.get('inventory', {}).get('positions') != evidence['positions']
            or not 0 <= (now - parse_timestamp(observation['as_of'])).total_seconds() <= 30):
        raise ValueError('strategy_settlement_current_order_observation_required')
    fills = _matching_fills(manager, evidence)
    gross_costs, net_costs = _remaining_costs(fills, False), _remaining_costs(fills, True)
    reported_costs = copy.deepcopy(evidence['position_costs'])
    if set(reported_costs) != set(net_costs):
        raise ValueError('strategy_reported_position_costs_missing')
    basis_matches = {}
    for symbol, value in reported_costs.items():
        matches = [basis for basis, costs in [('gross', gross_costs), ('including_verified_fees', net_costs)]
                   if abs(amount(value) - amount(costs[symbol])) <= TOLERANCE]
        if not matches:
            raise ValueError('strategy_reported_position_costs_unexplained')
        basis_matches[symbol] = matches
    # 원격 원문은 별도 보존한다. 내부 위험 계산 원가만 검증된 체결+확정 비용으로 조립한다.
    evidence['position_costs'] = net_costs
    events = {}
    for event in evidence['cash_events']:
        identifier = event['id']
        if not identifier or identifier in events:
            raise ValueError('strategy_duplicate_cash_event')
        if not parse_timestamp(baseline_at) < parse_timestamp(event['at']) <= parse_timestamp(evidence['as_of']):
            raise ValueError('strategy_cash_event_outside_model_scope')
        events[identifier] = copy.deepcopy(event)
    prior = manager.state.get('strategy_settlement', {})
    if prior.get('as_of') and parse_timestamp(evidence['as_of']) < parse_timestamp(prior['as_of']):
        raise ValueError('strategy_settlement_out_of_order')
    for field, current in [('fills', fills), ('cash_events', events)]:
        for identifier, old in prior.get(field, {}).items():
            if current.get(identifier) != old:
                raise ValueError('strategy_settlement_history_revision_or_missing')
    saved_risk = manager.state.get('risk_ledger', {})
    if saved_risk.get('last_evaluation', {}).get('source_kind') not in {None, KIND}:
        raise ValueError('strategy_settlement_basis_migration_required')
    # 과거 strategy_sources/risk_candidate를 자기 안으로 다시 복사하지 않는다.
    # 계산에 필요한 사건·일별 기준만 복사해 반복 조회 시 중첩 상태가 커지는 것을 막는다.
    risk = {key: copy.deepcopy(saved_risk[key]) for key in ('days', 'last_evaluation') if key in saved_risk}
    initial = cash_model['baseline']['cash_usd']
    risk.update(baseline={'cash': initial, 'net_asset_value': initial, 'as_of': baseline_at,
                          'positions': {}, 'basis': 'user_designation_not_broker_verified'},
                fills=fills, cash_events=events, issues=[])
    risk.setdefault('days', {})
    calculation = RiskLedger(manager)._calculate(risk, evidence, now)
    if calculation['issues']:
        raise ValueError('strategy_settlement_cash_inventory_or_cost_mismatch')
    # 입출금으로 관측 최고점과 낙폭을 부풀리지 않는다. 미관측 중간 가격의 MDD는 알 수 없다.
    flow_adjusted = amount(calculation['net_asset_value']) - amount(calculation['external_flow'], signed=True)
    previous = risk.get('last_evaluation', {})
    peak = max(amount(initial), amount(previous.get('observed_peak_adjusted_equity', initial)), flow_adjusted)
    drawdown = max(Decimal(0), (peak - flow_adjusted) / peak) if peak else Decimal(0)
    calculation.update(observed_peak_adjusted_equity=str(peak), observed_drawdown_ratio=str(drawdown),
        observed_max_drawdown_ratio=str(max(Decimal(previous.get('observed_max_drawdown_ratio', '0')), drawdown)),
        drawdown_scope='verified_snapshots_only_not_unobserved_prices')
    # 주문마다 최종 정산 근거를 저장한다. 재수신은 덮어쓰기이므로 비용을 더하지 않는다.
    before = copy.deepcopy(manager.state)
    settlement = copy.deepcopy(manager.state.get('demo_settlement', {'orders': {}}))
    for order in manager.state['orders'].values():
        if not order.get('filled'):
            continue
        own = [fill for fill in fills.values() if fill['order_id'] == order['id']]
        key = order['broker_id']
        previous = settlement['orders'].get(key, {})
        settlement['orders'][key] = {**previous, 'quantity': order['filled'],
            'notional_usd': str(amount(order['notional'])), 'symbol': order['symbol'], 'side': order['side'],
            'observed_at': evidence['as_of'], 'final_costs_usd': str(sum((amount(fill['fees']) for fill in own), Decimal(0))),
            'individual_execution_ids': sorted(fill['id'] for fill in own),
            'execution_times': {fill['id']: fill['at'] for fill in own},
            'cost_state': 'CONFIRMED', 'cost_source': {'checkpoint_hash': digest(evidence),
                'source_kind': evidence['source_kind'], 'fill_ids': sorted(fill['id'] for fill in own),
                'source_hashes': evidence['source_hashes']}}
    settlement.update(final_costs_complete=True, reconciliation_required=False,
                      net_realized_pnl_usd=calculation['realized_pnl_after_cost'])
    value = {'phase': 'RECONCILED', 'as_of': evidence['as_of'], 'source_kind': evidence['source_kind'],
        'reason': 'final_costs_cash_and_inventory_reconciled', 'account_fingerprint': manager.state['broker_identity'],
        'evidence': evidence, 'reported_position_costs': reported_costs,
        'reported_cost_numeric_matches': basis_matches,
        'reported_cost_semantics_certified': False,
        'fills': fills, 'cash_events': events, 'calculation': calculation,
        'risk_candidate': risk, 'execution_fingerprint': selected['fingerprint'],
        'policy_hash': digest(manager.policy), 'order_hash': order_contract_hash(manager)}
    manager.state['demo_settlement'] = settlement
    manager.state['strategy_settlement'] = value
    manager._strategy_settlement_binding = digest(value)
    try:
        manager._save()
    except BaseException:
        manager.state = before
        manager._strategy_settlement_binding = None
        raise
    return copy.deepcopy(value)


def current_settlement(manager, now=None):
    """저장한 참/거짓 대신 현재 원본·계좌·주문·설정을 다시 대조한다."""
    from trading.strategy_model_basis import selected_mode
    now = now or datetime.now(timezone.utc)
    selected = selected_mode(manager)
    value = manager.state.get('strategy_settlement', {})
    if (not value or getattr(manager, '_strategy_settlement_binding', None) != digest(value)
            or value['account_fingerprint'] != manager.state['broker_identity']
            or value['execution_fingerprint'] != selected['fingerprint']
            or value['policy_hash'] != digest(manager.policy)
            or value['order_hash'] != order_contract_hash(manager)
            or value['source_kind'] != 'kis_vps'
            or manager.state.get('restore_gate') or manager.state.get('replay_only')):
        raise ValueError('strategy_posttrade_current_verified_sources_required')
    if not 0 <= (now - parse_timestamp(value['as_of'])).total_seconds() <= 30:
        raise ValueError('strategy_posttrade_sources_stale')
    return copy.deepcopy(value)


def refresh_from_provider(manager, api, normalized):
    """기존 자료 공급기만 호출한다. 미지원 API 추측·자동 대체·검증 플래그 입력은 없다."""
    manager._strategy_settlement_binding = None
    provider = getattr(api, 'settlement_source_provider', None)
    if provider is None:
        return {'connected': False, 'reason': 'normalized_final_cost_and_cash_provider_unavailable'}
    sources = provider(manager, normalized)
    if sources is None:
        return {'connected': False, 'reason': 'settlement_source_not_available_yet'}
    value = connect_sources(manager, normalized, sources)
    return {'connected': True, 'as_of': value['as_of'], 'source_kind': value['source_kind']}
