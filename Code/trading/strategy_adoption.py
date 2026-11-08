"""사용자 요청으로 확인된 수동 모의 체결을 기존 일봉 전략의 보유 관리에 연결한다.

새 매수·가상 체결·비용 확정을 만들지 않는다. 원주문 계약은 그대로 두고 관리
소유자와 보호선만 이전하며 이전 소유자/원본·허용 근거를 같은 SQLite에 보존한다.
"""
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal

from paths import DATA_ROOT, CONFIG_ROOT
from strategy.engine import parse_timestamp
from trading.orders import ACTIVE, money
from trading.daily_account import last_closed_day, session_after
from research.daily import prepare_daily_bars
from research.algorithm_study import make_features, signal


def adopt_manual_fill(manager, account, order_id, snapshot, daily_record, *, now=None, authorization=None):
    """현재 전체 계좌 대조와 선택한 원주문의 전량 체결 보유를 요구한다. API·주문 함수는 호출하지 않는다.

    now는 합성 검사의 시계 주입용이며 운영에서는 현재UTC를 쓴다. 기존 손절을
    낮추지 않고, 관리 시작 전 미관측 고점을 추정하지 않는다. 비용은 미확정 유지다.
    """
    now = now or datetime.now(timezone.utc)
    if authorization is not None:
        if (set(authorization) != {'request_id','confirmed_at','source'}
                or authorization.get('source') != 'local_operator_confirmation'
                or not re.fullmatch(r'[0-9a-f]{32}', authorization.get('request_id',''))
                or not 0 <= (now-parse_timestamp(authorization['confirmed_at'])).total_seconds() <= 86400):
            raise ValueError('adoption_operator_request_invalid')
    if (manager.state.get('mode') != 'kis_demo' or manager.state.get('replay_only')
            or manager.state.get('restore_gate') or account.state.get('execution_mode') != 'kis_demo'):
        raise ValueError('adoption_demo_mode_and_reconciled_state_required')
    target = account.path.resolve()
    if not target.is_relative_to((DATA_ROOT/'execution-accounts/kis_demo').resolve()):
        raise ValueError('adoption_target_strategy_path_invalid')
    if (snapshot.get('market') != 'US' or snapshot.get('source') != 'kis'
            or snapshot.get('data_mode') != 'live_observation' or not hasattr(account, 'candidate')):
        raise ValueError('adoption_actual_quote_and_daily_strategy_required')
    quote = snapshot.get('quote') or {}
    for stamp in [snapshot['now'], quote['available_at']]:
        if not 0 <= (now - parse_timestamp(stamp)).total_seconds() <= 30:
            raise ValueError('adoption_quote_stale')
    observation = manager.state.get('execution_observation', {})
    if (getattr(manager, '_execution_observation_valid', False) is not True
            or observation.get('mode') != 'kis_demo'
            or observation.get('account_fingerprint') != manager.state.get('broker_identity')
            or not observation.get('source_hashes')
            or not 0 <= (now - parse_timestamp(observation['as_of'])).total_seconds() <= 30):
        raise ValueError('adoption_current_process_account_observation_required')
    orders = manager.state['orders']
    order = orders.get(order_id)
    if (not order or order['symbol'] != snapshot['symbol'] or order['side'] != 'BUY'
            or order['status'] != 'FILLED' or type(order['filled']) is not int
            or order['filled'] < 1 or order['quantity'] != order['filled'] or not order.get('broker_id')):
        raise ValueError('adoption_confirmed_whole_filled_buy_required')
    contract = observation.get('order_contracts', {}).get(order_id)
    if not contract or any(order.get(key) != value for key, value in contract.items()):
        raise ValueError('adoption_source_order_changed_after_observation')
    from trading.order_contract import broker_key
    # 접수 응답의 짧은 주문번호와 조회의 앞자리0 포함 번호는 같은 공식 키로 대조한다.
    matches = [row for key, row in manager.state.get('demo_settlement', {}).get('orders', {}).items()
               if broker_key(key) == broker_key(order['broker_id'])]
    if len(matches) != 1:
        raise ValueError('adoption_fill_identity_missing_or_duplicated')
    observed_fill = matches[0]
    if (observed_fill.get('quantity') != order['filled']
            or money(observed_fill.get('notional_usd', '0')) != money(order['notional'])
            or observed_fill.get('symbol') != order['symbol'] or observed_fill.get('side') != 'BUY'
            or observed_fill.get('observed_at') != observation['as_of']
            or observed_fill.get('source_hashes') != observation['source_hashes']):
        raise ValueError('adoption_fill_amount_not_observed')
    if any(item['status'] in ACTIVE for item in orders.values()):
        raise ValueError('adoption_active_order_requires_review')
    symbol = order['symbol']
    quantity = order['filled']
    from broker.product_policy import validate_symbol, load_product_rules
    rules = load_product_rules()
    validate_symbol(symbol, rules)
    if rules['verified_instruments'][symbol]['asset_type'] != 'stock':
        raise ValueError('adoption_stock_only')
    inventory = observation['inventory']
    if (inventory['positions'].get(symbol) != quantity or inventory['sellable'].get(symbol) != quantity
            or inventory['remote_reserved_sell'].get(symbol, 0) != 0):
        raise ValueError('adoption_verified_unreserved_holding_required')
    other_owners = {}
    for item in orders.values():
        if item['symbol'] == symbol and item['id'] != order_id and item.get('filled'):
            other_owner = item.get('strategy_owner', '')
            other_owners[other_owner] = other_owners.get(other_owner, 0) + item['filled'] * (1 if item['side'] == 'BUY' else -1)
    # 청산이 완료된 과거 거래는 허용하되, 다른 관리자의 잔여 보유를 배분하지 않는다.
    if any(remaining != 0 for remaining in other_owners.values()):
        raise ValueError('adoption_other_symbol_lots_require_allocation_review')
    owner = str(account.path.relative_to(DATA_ROOT))
    previous = manager.state.get('management_adoptions', {}).get(order_id)
    if previous:
        if (previous['target_owner'] != owner or order.get('strategy_owner') != owner
                or order.get('strategy_position') != previous['management_position']):
            raise ValueError('adoption_already_bound_to_other_strategy')
        return copy.deepcopy(previous)
    if not order.get('strategy_owner', '').startswith(('user_requested_single_demo:', 'manual_user:')):
        raise ValueError('adoption_explicit_manual_test_source_required')
    if 'US:' + symbol in account.state.get('positions', {}):
        raise ValueError('adoption_target_position_already_present')
    candidate = json.loads((CONFIG_ROOT/'fixed-trend-study.json').read_text(encoding='utf-8'))['candidate']
    candidate_hash = hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()
    if (account.candidate != candidate or account.state.get('daily_candidate_hash') != candidate_hash):
        raise ValueError('adoption_frozen_candidate_mismatch')
    if daily_record.get('collection_complete') is not True:
        raise ValueError('adoption_completed_source_collection_required')
    bars = prepare_daily_bars(daily_record)
    closed_day = last_closed_day(now)
    if not bars or bars[-1]['date'] != closed_day:
        raise ValueError('adoption_latest_completed_daily_required')
    feature = make_features(bars)[-1]
    if feature['count'] < 201 or not feature['atr']:
        raise ValueError('adoption_atr_history_insufficient')
    entry_price = money(order['notional']) / Decimal(order['filled'])
    bid, ask = money(quote['bid']), money(quote['ask'])
    if bid <= 0 or bid > ask or entry_price <= 0:
        raise ValueError('adoption_price_invalid')
    if abs(bid / Decimal(str(feature['close'])) - 1) > Decimal('0.20'):
        raise ValueError('adoption_corporate_action_or_price_mismatch')
    broker_day = order['broker_id'].split(':', 1)[0]
    if not re.fullmatch(r'\d{8}', broker_day):
        raise ValueError('adoption_broker_order_day_required')
    entry_day = datetime.strptime(broker_day, '%Y%m%d').date().isoformat()
    from zoneinfo import ZoneInfo
    if entry_day > now.astimezone(ZoneInfo('America/New_York')).date().isoformat():
        raise ValueError('adoption_future_order_day_invalid')
    peak = max(entry_price, bid)  # 과거 장중 고점을 만들어 추적 보호선을 높이지 않는다.
    atr = Decimal(str(feature['atr']))
    original_stop = money(order['stop_price'])
    stop = max(Decimal('0.01'), original_stop,
               entry_price - atr * Decimal(str(candidate['risk']['stop_atr'])),
               peak - atr * Decimal(str(candidate['risk']['trailing_atr'])))
    details = {
        'daily_stop': float(stop), 'daily_peak': float(peak), 'entry_day': entry_day,
        'signal_day': closed_day, 'management_origin': 'adopted_manual_test',
        'management_started_at': now.isoformat(), 'management_entry_price': str(entry_price),
        'initial_stop_at_adoption': float(stop), 'individual_execution_time_known': False,
    }
    # 신규 매수 신호는 만들지 않는다. 이미 확정된 기존 전략의 매도 조건만 이어받는다.
    exit_signal = entry_day <= closed_day and signal(feature, candidate['family'], candidate['strategy'])['exit']
    from broker.sessions import calendar_for
    holding_days = len(calendar_for('US', now.year).schedule.loc[entry_day:closed_day])
    exit_plan = None
    if exit_signal or holding_days >= candidate['strategy']['holding_days']:
        exit_plan = {'id': closed_day + ':SELL:US:' + symbol, 'symbol': 'US:' + symbol,
                     'side': 'SELL', 'execution_day': session_after(closed_day), 'signal_day': closed_day}
    receipt = {
        'schema': 1, 'order_id': order_id, 'broker_id': order['broker_id'],
        'symbol': symbol, 'quantity': quantity, 'adopted_at': now.isoformat(),
        'authorization': 'explicit_manual_management_api_call',
        'authorization_recorded_at': now.isoformat(),
        'operator_request': copy.deepcopy(authorization),
        'account_fingerprint': manager.state['broker_identity'], 'mode': 'kis_demo',
        'target_owner': owner, 'original_owner': order['strategy_owner'],
        'original_order': copy.deepcopy(order), 'candidate_hash': candidate_hash,
        'daily_source_hash': hashlib.sha256(json.dumps(daily_record, sort_keys=True).encode()).hexdigest(),
        'daily_source_day': closed_day, 'atr': str(atr), 'original_stop': str(original_stop),
        'management_position': details, 'pending_exit_plan': exit_plan,
        'costs_finalized_by_adoption': False, 'risk_approved_by_adoption': False,
        'evidence_observed_at': observation['as_of'], 'evidence_hashes': copy.deepcopy(observation['source_hashes']),
    }
    before = copy.deepcopy(manager.state)
    try:
        order['strategy_owner'] = owner
        order['strategy_position'] = copy.deepcopy(details)
        order['management_adoption_order_id'] = order_id
        manager.state.setdefault('management_adoptions', {})[order_id] = receipt
        manager.ready = False
        manager._strategy_settlement_binding = None
        manager._execution_observation_valid = False
        manager._save()
    except BaseException:
        manager.state = before
        manager.ready = False
        manager._execution_observation_valid = False
        raise
    return copy.deepcopy(receipt)


def restore_adopted_exit_plans(manager, account):
    """재시작 중 계좌 저장이 유실돼도 권위 원장에 남은 매도 계획만 이어받는다."""
    if not hasattr(account, 'candidate') or 'pending_daily' not in account.state:
        return
    owner = str(account.path.relative_to(DATA_ROOT))
    for order_id, receipt in manager.state.get('management_adoptions', {}).items():
        if receipt['target_owner'] != owner:
            continue
        order = manager.state['orders'].get(order_id, {})
        if (order.get('strategy_owner') != owner
                or receipt['candidate_hash'] != account.state.get('daily_candidate_hash')
                or receipt['account_fingerprint'] != manager.state.get('broker_identity')
                or order.get('strategy_position') != receipt['management_position']):
            raise ValueError('adoption_management_binding_changed')
        plan = receipt.get('pending_exit_plan')
        if (plan and plan['symbol'] in account.state['positions']
                and not any(item['id'] == plan['id'] for item in account.state['pending_daily'])):
            account.state['pending_daily'].append(copy.deepcopy(plan))
