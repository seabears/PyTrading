"""사용자가 허용한 한정 모의시험의 전방 기준. 공식 현금·과거 자금 이력을 인증하지 않는다.

빈 보유/체결과 자기 취소 주문만 허용한다. 첫 체결 후에는 새 매수를 막고
기존 보유 축소·취소 경로로 넘긴다. 원본 캡처·사용자 현금 기준·시험 한도를
같이 묶으며 재시작 시 캡처를 다시 받아야 한다.
"""
import copy
from datetime import datetime, timezone
from decimal import Decimal

from strategy.engine import parse_timestamp
from trading.risk_ledger import amount, digest, RiskProof
from zoneinfo import ZoneInfo

KIND='user_designated_demo_trial'


def normalize_owned_history(manager, rows):
    """KIS 이력에 주문유형이 없으면 자기 지정가 주문의 저장 계약과 대조해 복원한다.

    수동 주문에 지정가를 추정 적용하지 않는다. 종목/방향/수량/가격/계좌/원주문
    연결이 모두 맞는 자기 주문에만 이미 검증한 LIMIT 전송 계약을 사용한다.
    """
    from trading.reconciliation import normalize_orders
    from trading.order_contract import context, broker_key, validate_identity
    result=normalize_orders(rows,{**context(manager.state),'limit_only':False})
    own=set(manager.state.get('limited_demo_session',{}).get('order_ids',[]))
    if manager.state.get('alias')=='strategies':
        own.update(key for key,order in manager.state['orders'].items() if order.get('strategy_owner'))
    known={broker_key(order['broker_id']):order for key,order in manager.state['orders'].items()
           if key in own and order.get('broker_id')}
    for event in result:
        order=known.get(broker_key(event['broker_id']))
        if order and event['order_type']=='UNKNOWN' and order['order_type']=='LIMIT':
            candidate={**event,'order_type':'LIMIT'}
            validate_identity(order,candidate,manager.state)
            event.update(order_type='LIMIT',order_type_source='stored_managed_limit_contract')
    return result


def build_sources(manager, api, normalized, profile):
    """실제 조회와 사용자 기준으로 시험 전용 원본을 만든다. 권한은 활성화하지 않는다."""
    from trading.demo_profile import validate_trial_basis
    validate_trial_basis(profile)
    if profile.get('risk_basis')!=KIND:return None
    manager._user_trial_binding=None
    if manager.state['mode']!='kis_demo' or manager.state.get('replay_only') or manager.state.get('restore_gate'):
        raise ValueError('user_trial_mode_or_restore_blocked')
    cash=manager.state.get('user_cash_account')
    if not cash or cash['cash_basis_source']!='user_designation' or cash['cash_usd'] is None:
        raise ValueError('user_trial_designated_cash_missing')
    if (amount(cash['baseline']['cash_usd'])!=amount(profile['initial_reference']['amount'])
            or amount(cash['cash_usd'])!=amount(cash['baseline']['cash_usd'])
            or amount(cash['modeled_nav_usd'])!=amount(cash['cash_usd'])):
        raise ValueError('user_trial_cash_basis_inconsistent')
    if cash['orders_with_costs_pending'] or any(row['filled'] for row in cash['orders'].values()):
        raise ValueError('user_trial_existing_fill_requires_posttrade')
    inventory=normalized['inventory']
    if inventory['positions'] or inventory['position_costs']:
        raise ValueError('user_trial_existing_holdings_blocked')
    now=datetime.now(timezone.utc)
    # 동일 새로고침의 양끝 이력과 잔고만 받는다. 과거 성공 캡처를 섞지 않는다.
    records=[row for row in api.records if parse_timestamp(row['at'])>=parse_timestamp(normalized['query_started_at'])]
    if not records:raise ValueError('user_trial_actual_records_missing')
    allowed={'overseas_stock.inquire_ccnl','overseas_stock.inquire_balance','overseas_stock.inquire_psamount','overseas_stock.inquire_present_balance'}
    for row in records:
        if (row.get('method')!='GET' or row.get('environment')!='vps' or row.get('operation') not in allowed
                or row.get('account_fingerprint')!=manager.state.get('broker_identity')
                or row['payload'].get('rt_cd')!='0' or digest(row['payload'])!=row.get('sha256')
                or not 0<=(now-parse_timestamp(row['at'])).total_seconds()<=30):
            raise ValueError('user_trial_capture_invalid')
    histories=[row for row in records if row['operation']=='overseas_stock.inquire_ccnl']
    if len(histories)<2 or records[0]['operation']!='overseas_stock.inquire_ccnl' or records[-1]['operation']!='overseas_stock.inquire_ccnl':
        raise ValueError('user_trial_bracketed_history_required')
    # 현재 한정 시험은 최대 두 원주문이다. 페이지가 더 있으면 잘라 추정하지 않고 보류한다.
    if any(row.get('continuation') not in {'','D','E'} for row in histories):
        raise ValueError('user_trial_history_pagination_requires_review')
    first,last=histories[0],histories[-1]
    if first['request_context']!=last['request_context']:
        raise ValueError('user_trial_history_period_changed')
    baseline_day=parse_timestamp(cash['baseline']['enrolled_at']).astimezone(ZoneInfo('America/New_York')).strftime('%Y%m%d')
    today=now.astimezone(ZoneInfo('America/New_York')).strftime('%Y%m%d')
    period=first['request_context']
    if period.get('ORD_STRT_DT','99999999')>baseline_day or period.get('ORD_END_DT','00000000')<today:
        raise ValueError('user_trial_history_period_incomplete')
    first_rows=normalize_owned_history(manager,first['payload']['output'])
    last_rows=normalize_owned_history(manager,last['payload']['output'])
    if sorted(row['event_id'] for row in first_rows)!=sorted(row['event_id'] for row in last_rows):
        raise ValueError('user_trial_history_changed')
    session=manager.state.get('limited_demo_session',{})
    from trading.order_contract import broker_key
    own={broker_key(manager.state['orders'][key]['broker_id']) for key in session.get('order_ids',[]) if manager.state['orders'][key].get('broker_id')}
    for row in last_rows:
        if row['filled'] or row['broker_id'] not in own or row['status'] not in {'CANCELLED','REJECTED'}:
            raise ValueError('user_trial_remote_activity_requires_review')
    if any(order['status'] in {'INTENT','SENDING','UNKNOWN','ACCEPTED','PARTIAL','CANCEL_PENDING'} for order in manager.state['orders'].values()):
        raise ValueError('user_trial_active_or_ambiguous_order')
    from trading.demo_balance import checked_records,holdings_from_pages
    selected=checked_records(manager,records,now)
    positions,_=holdings_from_pages(selected)
    if positions:raise ValueError('user_trial_existing_holdings_blocked')
    capacities=[row for row in records if row['operation']=='overseas_stock.inquire_psamount']
    if len(capacities)!=1:raise ValueError('user_trial_single_capacity_required')
    capacity=capacities[0]['payload']['output']
    if capacity['tr_crcy_cd']!='USD':raise ValueError('user_trial_usd_required')
    if 'sll_ruse_psbl_amt' not in capacity:raise ValueError('user_trial_sell_reuse_field_missing')
    if amount(capacity['sll_ruse_psbl_amt'])!=0:
        raise ValueError('user_trial_unexplained_sell_reuse')
    for row in selected:
        if row['operation']=='overseas_stock.inquire_present_balance':
            if amount(row['payload']['output3'].get('tot_loan_amt','-1'))!=0:
                raise ValueError('user_trial_loan_zero_evidence_required')
    # 이전 정식 위험 원장의 손실/중지/오류를 새 기준으로 지우지 않는다.
    existing=manager.state.get('risk_ledger',{})
    previous=existing.get('last_evaluation',{})
    if existing.get('baseline') and previous.get('source_kind')!=KIND:
        raise ValueError('user_trial_existing_risk_baseline_requires_review')
    model_days=manager.state.get('risk_assessment_ledger',{}).get('days',{})
    if any(row.get('halted') for row in existing.get('days',{}).values()) or any(row.get('halted') for row in model_days.values()) or previous.get('day_halted') or previous.get('issues'):
        raise ValueError('user_trial_existing_risk_halt_preserved')
    result={'source_kind':KIND,'mode':'kis_demo','account_fingerprint':manager.state['broker_identity'],
        'as_of':records[-1]['at'],'cash_model_as_of':cash['as_of'],'cash':cash['cash_usd'],
        'initial':cash['baseline']['cash_usd'],'nav':cash['modeled_nav_usd'],
        'buying_power':str(amount(capacity['ovrs_ord_psbl_amt'])),'positions':{},'position_costs':{},
        'source_hashes':{str(i):row['sha256'] for i,row in enumerate(records)},
        'cash_model_hash':digest(cash),'limits_hash':profile['limits_hash'],'policy_hash':digest(manager.policy),
        'trial_session_id':session.get('id'),'profile':copy.deepcopy(profile),
        'cash_basis_source':'user_designation','broker_cash_verified':False,
        'past_cash_movements_verified':False,'coverage_scope':'forward_from_current_trial_snapshot',
        'fees_for_future_fills_final':False,'history_window':copy.deepcopy(normalized['history_window'])}
    manager._user_trial_binding=digest(result)
    return result


def ingest_sources(manager,sources):
    """시험 전용 평가를 저장한다. 과거 이력의 complete=True를 만들지 않는다."""
    if getattr(manager,'_user_trial_binding',None)!=digest(sources):
        raise ValueError('user_trial_current_capture_required')
    before=copy.deepcopy(manager.state)
    risk=copy.deepcopy(manager.state.get('risk_ledger',{}))
    risk.setdefault('baseline',{'positions':{},'source_kind':KIND,'cash_basis_source':'user_designation',
                                'as_of':sources['as_of'],'cash':sources['cash'],'net_asset_value':sources['nav']})
    evaluation={'source_kind':KIND,'as_of':sources['as_of'],'checkpoint_hash':digest(sources),
        'initial':sources['initial'],'cash_balance':sources['cash'],'buying_power':sources['buying_power'],
        'net_asset_value':sources['nav'],'exposure':'0','positions':{},'position_costs':{},
        'daily_loss_ratio':'0','consecutive_losses':0,'last_loss_at':None,'eligible':True,'issues':[],
        'day_halted':False,'broker_cash_verified':False,'past_cash_movements_verified':False,
        'scope':sources['coverage_scope'],'basis':'user_designated_bounded_demo_only'}
    risk.update(schema=1,account_fingerprint=sources['account_fingerprint'],mode='kis_demo',last_evaluation=evaluation,
                user_trial_sources=copy.deepcopy(sources),policy_hash=sources['policy_hash'])
    risk.setdefault('days',{});risk.setdefault('fills',{});risk.setdefault('cash_events',{});risk.setdefault('checkpoints',[])
    risk['checkpoints'].append({'as_of':sources['as_of'],'hash':digest(sources),'source_kind':KIND,'source_hashes':sources['source_hashes']})
    risk.pop('last_failure',None)
    manager.state['risk_ledger']=risk
    manager._user_trial_evaluation_binding=digest(evaluation)
    try:manager._save()
    except Exception:
        manager.state=before;manager.ready=False
        raise
    return trial_context(manager)


def trial_context(manager,now=None):
    """재시작·변경·만료를 차단한다. 원문을 다시 읽었다고 시각을 갱신하지 않는다."""
    now=now or datetime.now(timezone.utc)
    risk=manager.state['risk_ledger'];sources=risk['user_trial_sources'];value=risk['last_evaluation']
    if manager.state['mode']!='kis_demo' or manager.state.get('restore_gate') or manager.state.get('replay_only'):
        raise ValueError('user_trial_execution_mode_blocked')
    if (getattr(manager,'_user_trial_binding',None)!=digest(sources) or value['checkpoint_hash']!=digest(sources)
            or getattr(manager,'_user_trial_evaluation_binding',None)!=digest(value)
            or sources['account_fingerprint']!=manager.state.get('broker_identity')
            or sources['policy_hash']!=digest(manager.policy) or sources['cash_model_hash']!=digest(manager.state.get('user_cash_account'))):
        raise ValueError('user_trial_capture_or_inputs_changed')
    if not 0<=(now-parse_timestamp(sources['as_of'])).total_seconds()<=30:
        raise ValueError('user_trial_evidence_stale')
    if risk.get('last_failure') or value.get('day_halted') or any(row.get('halted') for row in risk['days'].values()):
        raise ValueError('user_trial_risk_halt')
    return RiskProof(sources['account_fingerprint'],digest(sources),sources['as_of'],sources['initial'],
                     '0',0,None,True,{}, {},sources['buying_power'],'0')


def require_execution_basis(manager,now=None,order=None):
    """정식 KIS 근거 또는 명시 허용된 빈 계좌 한정 시험만 실행 근거로 인정한다."""
    from trading.risk_ledger import RiskLedger
    proof=RiskLedger(manager).context(now)
    kind=manager.state['risk_ledger']['last_evaluation']['source_kind']
    if kind in {'kis_vps','user_designated_strategy_demo'}:return proof
    if kind!=KIND:raise ValueError('broker_risk_evidence_required')
    sources=manager.state['risk_ledger']['user_trial_sources'];session=manager.state.get('limited_demo_session',{})
    if not session.get('id') or session['id']!=sources['trial_session_id'] or session['limits_hash']!=sources['limits_hash']:
        raise ValueError('user_trial_limited_session_required')
    own=[manager.state['orders'][key] for key in session['order_ids']]
    if order is not None and not any(item['id']==order['id'] for item in own):own.append(order)
    if any(order.get('filled',0) for order in own):raise ValueError('user_trial_new_buy_after_fill_blocked')
    buys=[item for item in own if item['side']=='BUY']
    if (len(buys)>sources['profile']['maximum_buy_attempts']
            or any(item['quantity']!=1 or item['symbol']!=sources['profile']['symbol'] for item in buys)
            or sum((amount(item['price'])*Decimal('1.003') for item in buys),Decimal(0))>amount(sources['profile']['maximum_gross_buy_commitments_usd'])):
        raise ValueError('user_trial_immutable_budget_or_quantity_limit')
    if session['buy_attempts']>sources['profile']['maximum_buy_attempts']:
        raise ValueError('user_trial_attempt_limit')
    return proof
