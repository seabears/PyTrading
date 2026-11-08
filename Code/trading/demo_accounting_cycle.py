"""한정 모의 주문의 사전 기준 저장과 사후 정산. 이 모듈은 HTTP를 보내지 않는다.

미래 체결 비용을 사전 조건으로 요구하지 않는다. 기존 현금·계좌·위험 검사는
유지하며 승인 근거가 있을 때만 기준을 저장한다. 체결 후 비용이 미확정이면
추가 매수를 막고 확인된 보유 축소/취소는 기존 경로로 처리한다.
"""
import copy
from datetime import datetime, timezone
from decimal import Decimal

from strategy.engine import parse_timestamp
from trading.risk_ledger import RiskLedger, amount, digest
from trading.cash_service_policy import require_usd_funding
from trading.buying_power import assess_buying_power
from trading.order_contract import broker_key, validate_identity


def contract(order):
    """상태 변경과 무관한 계약·호가 시각만 고정한다."""
    return {key:order[key] for key in ('id','symbol','side','quantity','price','order_type','quote_at')}


def prepare_pretrade(manager, identifier, limits, now=None):
    """새 주문 의도 전송 직전에 현재 기준을 영속 저장한다. 미래 비용 자료는 입력이 아니다."""
    now = now or datetime.now(timezone.utc)
    order = manager.state['orders'][identifier]
    if manager.state['mode'] != 'kis_demo' or order['side'] != 'BUY' or order['status'] != 'INTENT':
        raise ValueError('pretrade_demo_buy_intent_required')
    session = manager.state['limited_demo_session']
    if identifier not in session['order_ids'] or session['limits_hash'] != limits['limits_hash']:
        raise ValueError('pretrade_session_scope_mismatch')
    if order['symbol'] != limits['symbol'] or order['quantity'] != 1 or order['order_type'] != 'LIMIT':
        raise ValueError('pretrade_contract_scope_mismatch')
    if not manager.ready or not 0 <= (now-parse_timestamp(order['quote_at'])).total_seconds() <= 30:
        raise ValueError('pretrade_account_or_quote_not_current')
    ledger = RiskLedger(manager)
    proof = ledger.context(now)
    ledger.validate_snapshot(manager.state['account'])
    from trading.demo_user_basis import require_execution_basis
    require_execution_basis(manager,now,order)
    if not proof.eligible:raise ValueError('pretrade_current_account_risk_required')
    if any(row.get('final_costs_usd') is None for row in manager.state.get('demo_settlement',{}).get('orders',{}).values()):
        raise ValueError('pretrade_existing_filled_costs_pending')
    required = amount(Decimal(order['quantity'])*amount(order['price'])*Decimal('1.003'))
    if required > amount(limits['maximum_gross_buy_commitments_usd']):
        raise ValueError('pretrade_profile_budget_exceeded')
    funding = require_usd_funding(manager,order)
    budget = assess_buying_power(manager.state['account'],manager.state['orders'].values(),current_id=identifier,order_cost=str(required))
    if not budget['within_buying_power']:raise ValueError('pretrade_api_capacity_exceeded')
    value = {'schema':1,'phase':'PREPARED','as_of':proof.as_of,'prepared_at':now.isoformat(),
        'account_fingerprint':proof.account_fingerprint,'mode':'kis_demo','session_id':session['id'],
        'limits_hash':limits['limits_hash'],'risk_checkpoint_hash':proof.checkpoint_hash,
        'policy_hash':digest(manager.policy),'contract':contract(order),
        'cash_before_usd':manager.state['risk_ledger']['last_evaluation']['cash_balance'],
        'baseline_fill_ids':sorted(manager.state['risk_ledger'].get('fills',{})),
        'baseline_cash_event_ids':sorted(manager.state['risk_ledger'].get('cash_events',{})),
        'positions_before':copy.deepcopy(manager.state['account']['positions']),
        'reserved_cost_usd':str(required),'funding':funding,'api_budget':budget,
        'future_order_final_costs_required_before_submit':False,
        'future_order_final_costs_usd':None,'after_fill':'block_additional_buys_until_final_costs_reconciled'}
    before=copy.deepcopy(manager.state)
    records=manager.state.setdefault('demo_accounting_cycle',{'schema':1,'pretrade':{},'posttrade':{}})['pretrade']
    if identifier in records:
        raise ValueError('pretrade_existing_intent_no_resend')
    records[identifier]=value
    try:manager._save()
    except Exception:
        manager.state=before;manager.ready=False
        raise
    return copy.deepcopy(value)


def validate_pretrade(manager, identifier, now=None):
    """의도 생성 후 저장값 변조·지연·다른 계좌·위험 기준 변경을 전송 직전에 거절한다."""
    now=now or datetime.now(timezone.utc)
    record=manager.state.get('demo_accounting_cycle',{}).get('pretrade',{}).get(identifier)
    if record is None:raise ValueError('pretrade_snapshot_required')
    session=manager.state['limited_demo_session']
    order=manager.state['orders'][identifier]
    if (record['account_fingerprint'] != manager.state.get('broker_identity') or manager.state['mode']!='kis_demo'
            or record['session_id'] != session['id'] or record['limits_hash'] != session['limits_hash']):
        raise ValueError('pretrade_account_or_session_changed')
    if record['contract'] != contract(order) or record['policy_hash'] != digest(manager.policy):
        raise ValueError('pretrade_contract_or_policy_changed')
    if not 0 <= (now-parse_timestamp(record['as_of'])).total_seconds() <= 30:
        raise ValueError('pretrade_snapshot_stale')
    proof=RiskLedger(manager).context(now)
    if not proof.eligible or proof.checkpoint_hash != record['risk_checkpoint_hash']:
        raise ValueError('pretrade_risk_checkpoint_changed')
    return copy.deepcopy(record)


def apply_verified_costs(manager):
    """기존 RiskLedger가 검산한 최종 체결 비용만 주문별 정산에 연결한다.

    주문 접수시각/누적 금액으로 개별 체결을 만들어내지 않는다. 수량·금액이
    정산 관측과 정확히 일치해야 확정한다. 실제 원본이 없으면 아무 값도 채우지 않는다.
    """
    ledger=RiskLedger(manager)
    try:proof=ledger.context()
    except ValueError:return {'applied_orders':0,'reason':'verified_execution_cost_evidence_unavailable'}
    risk=manager.state['risk_ledger']
    if risk['last_evaluation']['source_kind']!='kis_vps' or risk['last_evaluation']['issues']:
        return {'applied_orders':0,'reason':'broker_execution_cost_evidence_required'}
    before=copy.deepcopy(manager.state)
    settlement=manager.state.get('demo_settlement',{})
    changes=0
    for broker_id,row in settlement.get('orders',{}).items():
        orders=[order for order in manager.state['orders'].values() if order.get('broker_id') and broker_key(order['broker_id'])==broker_key(broker_id)]
        if len(orders)!=1:continue
        fills=[fill for fill in risk.get('fills',{}).values() if fill['order_id']==orders[0]['id']]
        if not fills or any(fill['fees_final'] is not True for fill in fills):continue
        if (sum(fill['quantity'] for fill in fills)!=row['quantity']
                or sum((amount(fill['notional']) for fill in fills),Decimal(0))!=amount(row['notional_usd'])):continue
        fees=str(sum((amount(fill['fees']) for fill in fills),Decimal(0)))
        row.update(final_costs_usd=fees,cost_state='CONFIRMED',
                   cost_source={'risk_checkpoint_hash':proof.checkpoint_hash,'fill_ids':sorted(fill['id'] for fill in fills)})
        changes+=1
    if not changes:return {'applied_orders':0,'reason':'no_matching_final_execution_costs'}
    settlement['final_costs_complete']=all(row.get('final_costs_usd') is not None for row in settlement['orders'].values())
    settlement['reconciliation_required']=not settlement['final_costs_complete']
    try:manager._save()
    except Exception:
        manager.state=before;manager.ready=False
        raise
    return {'applied_orders':changes,'reason':'existing_verified_ledger_costs_applied'}


def observe_posttrade(manager, remote_orders, inventory, as_of, source_hashes):
    """전체 주문 대조 후 호출한다. 체결·비용·잔여 상태를 단계별로 저장한다."""
    if manager.state['mode']!='kis_demo' or not source_hashes:
        raise ValueError('posttrade_demo_source_required')
    if not 0 <= (datetime.now(timezone.utc)-parse_timestamp(as_of)).total_seconds() <= 30:
        raise ValueError('posttrade_snapshot_stale')
    context=manager.state.get('limited_demo_session')
    if not context:return {'phase':'NO_SESSION','new_orders_allowed':False}
    before=copy.deepcopy(manager.state)
    cycle=manager.state.setdefault('demo_accounting_cycle',{'schema':1,'pretrade':{},'posttrade':{}})
    own=[manager.state['orders'][key] for key in context['order_ids']]
    if len({broker_key(row['broker_id']) for row in remote_orders})!=len(remote_orders):
        raise ValueError('posttrade_duplicate_remote_identifier')
    remote={broker_key(row['broker_id']):row for row in remote_orders}
    active={'INTENT','SENDING','UNKNOWN','ACCEPTED','PARTIAL','CANCEL_PENDING'}
    errors=[]
    for order in own:
        if order.get('broker_id'):
            row=remote.get(broker_key(order['broker_id']))
            if row is None:errors.append('trial_order_missing_from_full_history')
            else:
                validate_identity(order,row,manager.state)
                if order['filled']!=row['filled']:errors.append('local_remote_fill_quantity_mismatch')
    open_count=sum(order['status'] in active for order in own)
    net=sum(order['filled']*(1 if order['side']=='BUY' else -1) for order in own)
    pending=[order['id'] for order in own if order['filled'] and
        manager.state.get('demo_settlement',{}).get('orders',{}).get(order.get('broker_id'),{}).get('final_costs_usd') is None]
    if net < 0 or net > 1:errors.append('trial_net_position_invalid')
    if errors:phase='REVIEW'
    elif pending:phase='SETTLEMENT_PENDING'
    elif open_count:phase='ORDER_PENDING'
    elif net:phase='HOLDING'
    elif own:phase='RECONCILED'
    else:phase='BASELINE_OBSERVED'
    result={'phase':phase,'as_of':as_of,'source_hashes':dict(source_hashes),'session_id':context['id'],
        'account_fingerprint':manager.state['broker_identity'],'remaining_orders':open_count,'remaining_shares':net,
        'cost_pending_orders':pending,'issues':errors,'new_buy_blocked':bool(pending or errors),
        'actual_cash_delta_usd':None,'expected_cash_delta_usd':None,'cash_delta_matches':False,
        'cash_delta_status':'requires_current_verified_cash_checkpoint',
        'new_orders_allowed':False}
    # 현금은 API 주문가능액으로 대체하지 않는다. 검산된 기준과 현재 평가가 있을 때만 차액을 계산한다.
    prepared=list(cycle['pretrade'].values())
    if prepared:
        try:
            proof=RiskLedger(manager).context()
            risk=manager.state['risk_ledger']
            if risk['last_evaluation']['source_kind']=='kis_vps' and not risk['last_evaluation']['issues'] and proof.positions==inventory['positions']:
                initial=min(prepared,key=lambda row:parse_timestamp(row['prepared_at']))
                delta=amount(risk['last_evaluation']['cash_balance'])-amount(initial['cash_before_usd'])
                expected=Decimal(0)
                new_fills=[fill for key,fill in risk['fills'].items() if key not in initial['baseline_fill_ids']]
                if any(fill['order_id'] not in context['order_ids'] for fill in new_fills):
                    result['issues'].append('non_trial_execution_since_baseline')
                for fill in new_fills:
                    notional=amount(fill['notional'])
                    expected += (notional if fill['side']=='SELL' else -notional)-amount(fill['fees'])
                for key,event in risk['cash_events'].items():
                    if key not in initial['baseline_cash_event_ids']:expected+=amount(event['amount'],signed=True)
                result['actual_cash_delta_usd']=str(delta)
                result['expected_cash_delta_usd']=str(expected)
                result['cash_delta_matches']=delta==expected
                result['cash_delta_status']='current_verified_risk_checkpoint'
                result['risk_checkpoint_hash']=proof.checkpoint_hash
        except ValueError:pass
    if result['issues']:
        result.update(phase='REVIEW',new_buy_blocked=True)
    elif result['actual_cash_delta_usd'] is not None and not result['cash_delta_matches']:
        result['issues'].append('posttrade_cash_delta_mismatch')
        result.update(phase='REVIEW',new_buy_blocked=True)
    elif phase=='RECONCILED' and any(order['filled'] for order in own) and result['actual_cash_delta_usd'] is None:
        result.update(phase='CASH_RECONCILIATION_PENDING',new_buy_blocked=True)
    identifier=digest(result);cycle['posttrade'][identifier]=result;cycle['latest']=result
    if result['new_buy_blocked']:manager.ready=False
    try:manager._save()
    except Exception:
        manager.state=before;manager.ready=False
        raise
    return copy.deepcopy(result)


def readonly_plan(manager, review, assessment):
    """사전 검사와 사후 확인 항목을 구분한다. 이 계획으로 주문 권한을 만들지 않는다."""
    before_fill=[]
    before_fill.extend(assessment['failed_controls'])
    before_fill.extend(assessment['unknown_controls'])
    trial_candidate=False
    if manager.state.get('risk_ledger',{}).get('last_evaluation',{}).get('source_kind')=='user_designated_demo_trial':
        from trading.demo_user_basis import trial_context
        try:
            trial_context(manager)
        except ValueError:
            pass
        else:
            # 사용자 허용 전방 시험 범위에서만 과거 자금 사건 미확인을 별도로 표시한다.
            before_fill=[name for name in before_fill if name!='cash_movement_coverage']
            trial_candidate=True
    return {'stage':'PRETRADE_REVIEW','pretrade_blockers':sorted(set(before_fill)),
        'user_basis_trial_candidate':trial_candidate,'past_cash_movements_verified':False,
        'historical_costs':review['historical_cost_status'],
        'cost_reservation_multiplier':'1.003',
        'future_final_cost_is_pretrade_requirement':False,
        'after_submission':['confirm_order_identity','confirm_fill_and_inventory',
                            'obtain_final_costs','reconcile_actual_cash_delta'],
        'pending_final_costs_action':'block_additional_buys_allow_verified_reduction_and_cancel',
        'observed_at':review['as_of'],'new_orders_allowed':False}
