"""KIS 모의 전략의 최초 진입 및 확정 정산 이후 위험 근거. 사용자 지정 초기금과 실제 계좌 관측을 구분한다.

기존 전략 수량을 실행하도록 요청한2026-11-02 지시를 적용한다. 단순 enabled만으로
자금을 인증하지 않는다. 기존 사용자 지정 기준, 실제 빈 보유/전체 주문/순수USD여력,
대출/매도대금재사용0, 중지 상태, 원본 시각·해시를 모두 검산한다. 공식 현금/NAV나
과거 자금 변동을 검증한 것으로 표시하지 않는다. 체결 후 미확정 비용/외부 거래가
있으면 신규 매수를 중지하고 확인된 보유 관리는 기존 감소 전용 경로로 처리한다.
"""
import copy
from datetime import datetime,timezone
from trading.risk_ledger import amount,digest,RiskProof
from strategy.engine import parse_timestamp
from trading.order_contract import broker_key

KIND='user_designated_strategy_demo'


def selected_mode(manager):
    """생성된 실제 전략 포트와 현재 설정이 일치해야 한다. 저장 플래그만으로 승인하지 않는다."""
    from trading.execution import load_execution
    selected=getattr(manager,'_strategy_execution_selection',None)
    if not selected:raise ValueError('strategy_current_runtime_binding_required')
    current=load_execution(selected['path'])
    if current['mode']!='kis_demo' or current['fingerprint']!=selected['fingerprint']:
        raise ValueError('strategy_demo_mode_changed')
    return current


def build_sources(manager,api,normalized):
    """런타임 모드→사용자 자금→실제 전체 캡처→위험 중지 순으로 최초 진입을 검산한다."""
    selected=selected_mode(manager)
    manager._strategy_sources_binding=None
    if (manager.state['mode']!='kis_demo' or manager.state['alias']!='strategies'
            or manager.state.get('restore_gate') or manager.state.get('replay_only')
            or manager.state.get('limited_demo_session')):
        raise ValueError('strategy_account_scope_or_restore_blocked')
    cash=manager.state.get('user_cash_account')
    if not cash or cash['cash_basis_source']!='user_designation' or cash['cash_usd'] is None:
        raise ValueError('strategy_designated_cash_unavailable')
    has_fills=any(row.get('filled') for row in cash['orders'].values())
    now=datetime.now(timezone.utc)
    records=[row for row in api.records if parse_timestamp(row['at'])>=parse_timestamp(normalized['query_started_at'])]
    history='overseas_stock.inquire_ccnl'
    allowed={history,'overseas_stock.inquire_balance','overseas_stock.inquire_present_balance','overseas_stock.inquire_psamount'}
    if len(records)<7 or records[0]['operation']!=history or records[-1]['operation']!=history:
        raise ValueError('strategy_full_bracketed_snapshot_required')
    for row in records:
        if (row.get('method')!='GET' or row.get('environment')!='vps' or row.get('operation') not in allowed
                or row.get('account_fingerprint')!=manager.state.get('broker_identity')
                or row['payload'].get('rt_cd')!='0' or digest(row['payload'])!=row.get('sha256')
                or not 0<=(now-parse_timestamp(row['at'])).total_seconds()<=30):
            raise ValueError('strategy_actual_capture_invalid')
    histories=[row for row in records if row['operation']==history]
    if len(histories)!=2 or any(row.get('continuation') not in {'','D','E'} for row in histories):
        raise ValueError('strategy_history_coverage_requires_review')
    first,last=histories
    if first['request_context']!=last['request_context']:
        raise ValueError('strategy_history_window_changed')
    from zoneinfo import ZoneInfo
    baseline_day=parse_timestamp(cash['baseline']['enrolled_at']).astimezone(ZoneInfo('America/New_York')).strftime('%Y%m%d')
    today=now.astimezone(ZoneInfo('America/New_York')).strftime('%Y%m%d')
    context=first['request_context']
    if context.get('ORD_STRT_DT','99999999')>baseline_day or context.get('ORD_END_DT','00000000')<today:
        raise ValueError('strategy_history_period_incomplete')
    from trading.demo_user_basis import normalize_owned_history
    before=normalize_owned_history(manager,first['payload']['output'])
    after=normalize_owned_history(manager,last['payload']['output'])
    if sorted(row['event_id'] for row in before)!=sorted(row['event_id'] for row in after):
        raise ValueError('strategy_history_changed_during_capture')
    if has_fills:
        from trading.strategy_posttrade import current_settlement
        settled=current_settlement(manager,now)
        if (settled['evidence']['positions']!=normalized['inventory']['positions']
                or amount(settled['calculation']['cash_balance'])!=amount(cash['cash_usd'])
                or amount(settled['calculation']['net_asset_value'])!=amount(cash['modeled_nav_usd'])):
            raise ValueError('strategy_posttrade_model_or_inventory_changed')
        # 양끝 조회와 현재 원장 계약도 아래의 공통 검사 이후 검산한다.
    else:
        settled=None
        if (cash['orders_with_costs_pending'] or amount(cash['cash_usd'])!=amount(cash['baseline']['cash_usd'])
                or amount(cash['modeled_nav_usd'])!=amount(cash['cash_usd'])):
            raise ValueError('strategy_posttrade_cash_and_cost_reconciliation_required')
        if normalized['inventory']['positions'] or normalized['inventory']['position_costs']:
            raise ValueError('strategy_existing_holdings_require_cost_risk_reconciliation')
    known={broker_key(row['broker_id']) for row in manager.state['orders'].values() if row.get('broker_id') and row.get('strategy_owner')}
    if any(broker_key(row['broker_id']) not in known or (not settled and (row['filled'] or row['status'] not in {'CANCELLED','REJECTED'})) for row in after):
        raise ValueError('strategy_remote_activity_requires_reconciliation')
    from trading.orders import ACTIVE
    if any(row['status'] in ACTIVE for row in manager.state['orders'].values()):
        raise ValueError('strategy_active_or_uncertain_order')
    from trading.demo_balance import checked_records,holdings_from_pages
    selected_records=checked_records(manager,records,now)
    positions,_=holdings_from_pages(selected_records)
    if not settled and positions:raise ValueError('strategy_actual_holdings_not_empty')
    if settled and {row['symbol']:row['quantity'] for row in positions}!=settled['calculation']['positions']:
        raise ValueError('strategy_posttrade_balance_changed')
    capacities=[row for row in records if row['operation']=='overseas_stock.inquire_psamount']
    if len(capacities)!=1:raise ValueError('strategy_capacity_capture_invalid')
    capacity=capacities[0]['payload']['output']
    if capacity['tr_crcy_cd']!='USD' or 'sll_ruse_psbl_amt' not in capacity or amount(capacity['sll_ruse_psbl_amt'])!=0:
        raise ValueError('strategy_pure_usd_or_reuse_evidence_required')
    # 빈 계좌/예약0에서 사용자 기준과 순수USD여력이 다르면 자금 변동을 추정하지 않는다.
    if not settled and amount(capacity['ovrs_ord_psbl_amt'])!=amount(cash['cash_usd']):
        raise ValueError('strategy_unexplained_cash_capacity_difference')
    for row in selected_records:
        if row['operation']=='overseas_stock.inquire_present_balance' and amount(row['payload']['output3'].get('tot_loan_amt','-1'))!=0:
            raise ValueError('strategy_loan_zero_evidence_required')
    existing=manager.state.get('risk_ledger',{});previous=existing.get('last_evaluation',{})
    model_days=manager.state.get('risk_assessment_ledger',{}).get('days',{})
    if (any(row.get('halted') for row in existing.get('days',{}).values())
            or any(row.get('halted') for row in model_days.values()) or previous.get('day_halted') or previous.get('issues')):
        raise ValueError('strategy_existing_loss_halt_preserved')
    if existing.get('baseline') and previous.get('source_kind')!=KIND:
        raise ValueError('strategy_existing_baseline_requires_review')
    source={'source_kind':KIND,'mode':'kis_demo','account_fingerprint':manager.state['broker_identity'],
        'as_of':records[-1]['at'],'initial':cash['baseline']['cash_usd'],'cash':cash['cash_usd'],
        'nav':cash['modeled_nav_usd'],'buying_power':str(amount(capacity['ovrs_ord_psbl_amt'])),
        'positions':{},'position_costs':{},'source_hashes':{str(i):row['sha256'] for i,row in enumerate(records)},
        'cash_model_hash':digest(cash),'policy_hash':digest(manager.policy),'execution_fingerprint':selected['fingerprint'],
        'broker_cash_verified':False,'past_cash_movements_verified':False,
        'basis':'user_designated_initial_cash_plus_current_empty_account','scope':'forward_only_before_first_unsettled_fill',
        'history_window':copy.deepcopy(normalized['history_window']),'future_costs_final':False}
    if settled:
        source.update(positions=settled['calculation']['positions'],position_costs=settled['calculation']['position_costs'],
            scope='forward_settled_user_model_not_official_baseline',basis='user_initial_plus_verified_forward_settlement',
            settlement_hash=digest(settled),calculation=settled['calculation'],risk_candidate=settled['risk_candidate'])
    manager._strategy_sources_binding=digest(source)
    return source


def ingest(manager,source):
    """검산한 원본과 연결된 평가만 저장하며 기존 손실/중지 이력을 보존한다."""
    if getattr(manager,'_strategy_sources_binding',None)!=digest(source):
        raise ValueError('strategy_current_actual_capture_required')
    before=copy.deepcopy(manager.state)
    risk=copy.deepcopy(manager.state.get('risk_ledger',{}))
    evaluation={'source_kind':KIND,'as_of':source['as_of'],'checkpoint_hash':digest(source),
        'initial':source['initial'],'cash_balance':source['cash'],'net_asset_value':source['nav'],
        'buying_power':source['buying_power'],'positions':{},'position_costs':{},'exposure':'0',
        'daily_loss_ratio':'0','consecutive_losses':0,'last_loss_at':None,'day_halted':False,'issues':[],
        'eligible':not source['positions'] and source['cash'] is not None,
        'broker_cash_verified':False,'past_cash_movements_verified':False,'scope':source['scope']}
    if source.get('settlement_hash'):
        calculation=copy.deepcopy(source['calculation'])
        calculation.update(source_kind=KIND,checkpoint_hash=digest(source),
            broker_cash_verified=False,past_cash_movements_verified=False,scope=source['scope'])
        evaluation=calculation
        candidate=source['risk_candidate']
        for field in ('baseline','fills','cash_events','days','issues'):
            risk[field]=copy.deepcopy(candidate[field])
    risk.update(schema=1,mode='kis_demo',account_fingerprint=source['account_fingerprint'],last_evaluation=evaluation,
                strategy_sources=copy.deepcopy(source),policy_hash=source['policy_hash'])
    risk.setdefault('days',{});risk.setdefault('fills',{});risk.setdefault('cash_events',{});risk.setdefault('checkpoints',[])
    risk['checkpoints'].append({'as_of':source['as_of'],'hash':digest(source),'source_kind':KIND,'source_hashes':source['source_hashes']})
    risk.pop('last_failure',None);manager.state['risk_ledger']=risk
    manager._strategy_evaluation_binding=digest(evaluation)
    try:manager._save()
    except BaseException:
        manager.state=before;manager.ready=False;raise
    return context(manager)


def context(manager,now=None):
    """전송 직전 모드·원본·계좌·정책·신선도를 다시 검사한다. 재시작은 재조회가 필요하다."""
    selected=selected_mode(manager);now=now or datetime.now(timezone.utc)
    risk=manager.state['risk_ledger'];source=risk['strategy_sources'];value=risk['last_evaluation']
    if (manager.state['mode']!='kis_demo' or manager.state.get('restore_gate') or manager.state.get('replay_only')
            or getattr(manager,'_strategy_sources_binding',None)!=digest(source)
            or getattr(manager,'_strategy_evaluation_binding',None)!=digest(value)
            or value['checkpoint_hash']!=digest(source) or source['execution_fingerprint']!=selected['fingerprint']
            or source['account_fingerprint']!=manager.state['broker_identity']
            or source['cash_model_hash']!=digest(manager.state.get('user_cash_account'))
            or source['policy_hash']!=digest(manager.policy)):
        raise ValueError('strategy_context_inputs_or_runtime_changed')
    if not 0<=(now-parse_timestamp(source['as_of'])).total_seconds()<=30:
        raise ValueError('strategy_evidence_stale')
    if risk.get('last_failure') or any(row.get('halted') for row in risk['days'].values()):
        raise ValueError('strategy_risk_halt')
    if any(row.get('filled') for row in manager.state['orders'].values()):
        if not source.get('settlement_hash'):
            raise ValueError('strategy_posttrade_risk_not_approved')
        from trading.strategy_posttrade import current_settlement
        if digest(current_settlement(manager,now))!=source['settlement_hash']:
            raise ValueError('strategy_posttrade_settlement_changed')
    return RiskProof(source['account_fingerprint'],digest(source),source['as_of'],source['initial'],
                     value['daily_loss_ratio'],value['consecutive_losses'],value['last_loss_at'],value['eligible'],
                     copy.deepcopy(value['positions']),copy.deepcopy(value['position_costs']),source['buying_power'],value['exposure'])
