"""조회 원장·사용자 지정 현금·예약·미확정 비용의 읽기 전용 검산.

가입 상태나 미래 수수료 0을 가정하지 않는다. 모델 계산을 RiskProof로 승격하지
않으며 조회 근거와 모델 기준을 같은 SQLite의 미확정 위험 관측으로 보존한다.
"""
import copy
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from strategy.engine import parse_timestamp
from trading.buying_power import ACTIVE_BUYS, assess_buying_power, validate_api_buying_power
from trading.order_contract import broker_key
from trading.risk_ledger import RiskLedger, amount, digest


def review_cash(manager, balance_link, remote_orders, budget_account, records, history_window):
    """현재 계좌·시각·원본 → 모델 일치 → 예약/비용 → 차단 사유 순으로 검사한다.

    0.003은 기존 주문 비용 완충1.003의 비용 부분이며 실제 수수료율이 아니다.
    비용 미확정 체결의 예상 현금은 표시하되 신규 매수 자격은 주지 않는다.
    """
    manager.ready = False
    now = datetime.now(timezone.utc)
    observation = balance_link['observation']
    cash = manager.state.get('user_cash_account')
    if (manager.state['mode'] != 'kis_demo' or not cash
            or observation['account_fingerprint'] != manager.state.get('broker_identity')
            or cash['baseline']['account_fingerprint'] != manager.state['broker_identity']):
        raise ValueError('cash_review_account_or_model_missing')
    if cash['observation_id'] != balance_link['observation_id'] or cash['as_of'] != observation['as_of']:
        raise ValueError('cash_review_model_observation_mismatch')
    if not 0 <= (now-parse_timestamp(observation['as_of'])).total_seconds() <= 30:
        raise ValueError('cash_review_observation_stale')
    if not records or any(row.get('method') != 'GET' or row.get('environment') != 'vps'
            or row.get('account_fingerprint') != manager.state['broker_identity']
            or digest(row['payload']) != row.get('sha256') or row['payload'].get('rt_cd') != '0'
            or not 0 <= (now-parse_timestamp(row['at'])).total_seconds() <= 30 for row in records):
        raise ValueError('cash_review_capture_invalid')
    baseline_day = parse_timestamp(cash['baseline']['enrolled_at']).astimezone(ZoneInfo('America/New_York')).date()
    if (datetime.fromisoformat(history_window['start']).date() > baseline_day
            or datetime.fromisoformat(history_window['end']).date() < now.astimezone(ZoneInfo('America/New_York')).date()):
        raise ValueError('cash_review_history_window_incomplete')
    # bind_api_buying_power가 현재 프로세스에서 확인한 계좌/시각/원본 연결을 재사용한다.
    bound = {**budget_account, 'cash':budget_account['buying_power_usd'],
             'buying_power_evidence':budget_account}
    validate_api_buying_power(manager, bound)
    if len({row['broker_id'] for row in remote_orders}) != len(remote_orders):
        raise ValueError('cash_review_duplicate_remote_order')
    modeled = {row['broker_id']:{field:row[field] for field in ['broker_id','symbol','side','filled','notional']} for row in remote_orders}
    if modeled != cash['orders']:
        raise ValueError('cash_review_history_model_mismatch')

    remote = {broker_key(row['broker_id']):row for row in remote_orders}
    remote_reserved = sum((Decimal(row['quantity']-row['filled']) * amount(row['price']) * Decimal('1.003')
                           for row in remote.values() if row['side']=='BUY' and row['status'] in ACTIVE_BUYS), Decimal(0))
    local_reserved = Decimal(0)
    manual = []
    unresolved = []
    matched_remote = set()
    for order in manager.state['orders'].values():
        identifier = broker_key(order['broker_id']) if order.get('broker_id') else None
        if identifier in remote:
            match = remote[identifier]
            if any(order[key] != match[key] for key in ['symbol','side','quantity']) or amount(order['price']) != amount(match['price']):
                raise ValueError('cash_review_local_remote_contract_mismatch')
            matched_remote.add(identifier)
        if order['status'] in {'SENDING','UNKNOWN'}:
            unresolved.append(order['id'])
        if order['side']=='BUY' and order['status'] in ACTIVE_BUYS and identifier not in remote:
            local_reserved += Decimal(order['quantity']-order.get('filled',0))*amount(order['price'])*Decimal('1.003')
    for identifier,row in remote.items():
        if identifier not in matched_remote:
            manual.append(row['broker_id'])
    try:
        api_budget = assess_buying_power(budget_account, manager.state['orders'].values())
    except ValueError as error:
        if str(error) != 'buying_power_order_state_unknown':
            raise
        api_budget = {'available_for_new_order_usd':None,'reason':'buying_power_order_state_unknown'}
    pending = set(cash['orders_with_costs_pending'])
    pending_fee_reserve = sum((amount(row['notional'])*Decimal('0.003') for row in remote.values()
                               if row['broker_id'] in pending), Decimal(0))
    modeled_cash_before_pending = amount(cash['cash_before_unconfirmed_costs_usd'])-amount(cash['confirmed_fees_usd'])
    estimated_cash = modeled_cash_before_pending-pending_fee_reserve
    cash_available = max(Decimal(0),estimated_cash-remote_reserved-local_reserved)
    api_available = api_budget['available_for_new_order_usd']
    available = min(cash_available, amount(api_available)) if api_available is not None else None
    known_issues = []
    if pending:known_issues.append('filled_execution_final_costs_pending')
    if manual:known_issues.append('remote_orders_not_matched_to_local_ledger')
    if unresolved:known_issues.append('local_order_state_unresolved')
    if estimated_cash < 0:known_issues.append('estimated_costs_exceed_model_cash')
    # 자금 사건이 실제로 조회되지 않은 범위를 '없음'으로 인증하지 않는다.
    known_issues.append('cash_movement_coverage_not_established')
    try:
        proof = RiskLedger(manager).context()
        risk_status = 'eligible' if proof.eligible else 'ineligible'
        if not proof.eligible:known_issues.append('current_risk_checkpoint_ineligible')
    except ValueError:
        risk_status = 'no_current_approved_checkpoint'
        known_issues.append('current_approved_risk_checkpoint_missing')
    value = {'kind':'kis_demo_cash_model_review','as_of':observation['as_of'],
        'account_fingerprint':manager.state['broker_identity'],'mode':'kis_demo',
        'source_hashes':{str(index):row['sha256'] for index,row in enumerate(records)},
        'balance_observation_id':balance_link['observation_id'],'history_window':history_window,
        'initial_cash_usd':cash['baseline']['cash_usd'],'initial_cash_source':'user_designation',
        'initial_basis_at':cash['baseline']['enrolled_at'],'model_cash_usd':cash['cash_usd'],
        'model_nav_usd':cash['modeled_nav_usd'],'api_buying_power_usd':budget_account['buying_power_usd'],
        'remote_reserved_buy_usd':str(remote_reserved),'local_reserved_buy_usd':str(local_reserved),
        'confirmed_costs_usd':cash['confirmed_fees_usd'],
        'pending_execution_cost_estimate_usd':str(pending_fee_reserve),
        'estimated_cash_after_cost_reserve_usd':str(estimated_cash),
        'estimated_available_after_all_reserves_usd':str(available) if available is not None else None,
        'cost_multiplier':'1.003','cost_estimate_is_final':False,
        'historical_cost_status':'pending' if pending else 'not_applicable_no_fills' if not any(row['filled'] for row in remote.values()) else 'settled_in_model',
        'future_cost_channel_status':'not_established_for_vps',
        'unmatched_remote_orders':manual,'unresolved_local_orders':unresolved,
        'api_budget':api_budget,'risk_status':risk_status,
        'account_enrollment_status_required':False,'broker_cash_verified':False,
        'blockers':sorted(set(known_issues)),'new_orders_allowed':False,'risk_approved':False}
    # 동일 캡처는 동일 ID로 보존한다. 다른 관측을 과거 자료로 소급하지 않는다.
    identifier = RiskLedger(manager).record_unsettled_observation(value)
    return {'observation_id':identifier, **copy.deepcopy(value)}
