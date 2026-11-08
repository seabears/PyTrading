"""사용자가 지정한 모의 USD 현금을 실제 보유/누적 체결에 연결해 계산한다.

사용자 지정은 계산 기준으로 유효하다. API 잔액 검증 여부는 출처 기록이며
계산을 막지 않는다. 이 장부는 주문용 RiskProof를 발급하지 않는다.
"""
import copy
from datetime import datetime, timezone
from decimal import Decimal

from strategy.engine import parse_timestamp
from trading.risk_ledger import amount, digest


def update_user_cash(manager, balance_link, remote_orders, config):
    """기준 현금 + 매도대금 - 매수대금 - 확정 비용, 그리고 보유 평가액을 계산한다.

    누적 체결을 주문별로 대체하므로 같은 통보를 다시 받아도 현금이 중복 차감되지 않는다.
    비용이 미확정이면 비용 전 현금은 표시하고 비용 후 현금은 None으로 둔다.
    """
    manager.ready = False
    if manager.state['mode'] != 'kis_demo' or config.get('mode') != 'kis_demo':
        raise ValueError('user_cash_demo_only')
    if config.get('currency') != 'USD' or config.get('source') != 'user_designation':
        raise ValueError('user_cash_basis_source_invalid')
    initial = amount(config['cash_usd'])
    if initial <= 0:
        raise ValueError('user_cash_basis_positive_required')
    observation = balance_link['observation']
    identity = manager.state.get('broker_identity')
    if observation['account_fingerprint'] != identity or observation['mode'] != 'kis_demo':
        raise ValueError('user_cash_account_mismatch')
    if not 0 <= (datetime.now(timezone.utc) - parse_timestamp(observation['as_of'])).total_seconds() <= 30:
        raise ValueError('user_cash_observation_stale')
    snapshot = observation['balance_snapshot']
    before = copy.deepcopy(manager.state)
    previous = manager.state.get('user_cash_account')
    if previous is None:
        if snapshot['positions'] or remote_orders:
            raise ValueError('user_cash_initial_holdings_or_history_require_review')
        baseline = {'cash_usd': str(initial), 'currency': 'USD', 'source': 'user_designation',
                    'authorization_date': config['authorized_on'], 'enrolled_at': observation['as_of'],
                    'account_fingerprint': identity, 'config_hash': digest(config)}
    else:
        baseline = previous['baseline']
        if baseline['account_fingerprint'] != identity or baseline['config_hash'] != digest(config):
            raise ValueError('user_cash_basis_or_account_changed')
    orders = {}
    for order in remote_orders:
        key = order['broker_id']
        if key in orders or order['account_fingerprint'] != identity or order['mode'] != 'kis_demo':
            raise ValueError('user_cash_order_identity_invalid')
        if order['side'] not in {'BUY','SELL'} or type(order['filled']) is not int or order['filled'] < 0:
            raise ValueError('user_cash_order_quantity_or_side_invalid')
        orders[key] = {field: order[field] for field in ['broker_id','symbol','side','filled','notional']}
        amount(order['notional'])
        old = (previous or {}).get('orders', {}).get(key)
        if old and (old['symbol'] != order['symbol'] or old['side'] != order['side']
                    or order['filled'] < old['filled'] or amount(order['notional']) < amount(old['notional'])):
            raise ValueError('user_cash_cumulative_history_changed')
    if set((previous or {}).get('orders', {})) - set(orders):
        raise ValueError('user_cash_history_missing')
    cash_before_costs = initial
    # 현재 공급기가 검산한 전방 자금 사건만 반영한다. API 여력을 입금으로 취급하지 않는다.
    settlement=manager.state.get('strategy_settlement',{})
    # 이미 검산·저장한 과거 사건은 재시작/현재 공급기 부재로 지우지 않는다.
    # 이를 최신 범위의 완전성이나 주문 승인으로 사용하지는 않는다.
    events=copy.deepcopy((previous or {}).get('cash_events',{}))
    if settlement and getattr(manager,'_strategy_settlement_binding',None)==digest(settlement):
        if settlement['account_fingerprint']!=identity:
            raise ValueError('user_cash_settlement_account_mismatch')
        for identifier,old in events.items():
            if settlement['cash_events'].get(identifier)!=old:
                raise ValueError('user_cash_verified_event_revision_or_missing')
        events=copy.deepcopy(settlement['cash_events'])
    for event in events.values():
        cash_before_costs+=amount(event['amount'],signed=True)
    expected_positions = {}
    fees = Decimal(0)
    missing_fees = []
    for key, order in orders.items():
        signed_quantity = order['filled'] if order['side'] == 'BUY' else -order['filled']
        expected_positions[order['symbol']] = expected_positions.get(order['symbol'], 0) + signed_quantity
        value = amount(order['notional'])
        cash_before_costs += -value if order['side'] == 'BUY' else value
        if order['filled']:
            cost = manager.state.get('demo_settlement', {}).get('orders', {}).get(key, {}).get('final_costs_usd')
            if cost is None:
                missing_fees.append(key)
            else:
                fees += amount(cost)
    expected_positions = {key: value for key, value in expected_positions.items() if value}
    actual_positions = {row['symbol']: row['quantity'] for row in snapshot['positions']}
    if expected_positions != actual_positions or any(value < 0 for value in expected_positions.values()):
        raise ValueError('user_cash_inventory_history_mismatch')
    if cash_before_costs < 0:
        raise ValueError('user_cash_negative_balance')
    cash = None if missing_fees else cash_before_costs - fees
    if cash is not None and cash < 0:
        raise ValueError('user_cash_fees_exceed_balance')
    marked = amount(snapshot['reported_holdings_value_usd'])
    value = {'mode': 'kis_demo', 'baseline': baseline, 'orders': orders,
             'as_of': observation['as_of'], 'observation_id': balance_link['observation_id'],
             'cash_basis_source': 'user_designation', 'cash_before_unconfirmed_costs_usd': str(cash_before_costs),
             'cash_usd': str(cash) if cash is not None else None,
             'modeled_nav_before_unconfirmed_costs_usd': str(cash_before_costs + marked),
             'modeled_nav_usd': str(cash + marked) if cash is not None else None,
             'confirmed_fees_usd': str(fees), 'orders_with_costs_pending': missing_fees,
             'cash_events':copy.deepcopy(events),
             'unprovided_cash_events': 'verified_forward_sources_only' if events else 'not_included_in_model',
             'broker_cash_verified': False, 'risk_approved': False, 'new_orders_allowed': False}
    manager.state['user_cash_account'] = value
    try:
        manager._save()
    except Exception:
        manager.state = before
        manager.ready = False
        raise
    return copy.deepcopy(value)
