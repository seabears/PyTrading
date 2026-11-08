"""부분 근거로도 실행되는 위험 평가. 미확인은 미확인으로 남기고 주문 권한은 만들지 않는다.

현금/예약 계산이 있으면 투자 한도·관측 기준 일일 손실·낙폭을 계산한다.
최종 비용/자금 사건 근거가 없다는 이유로 계산 자체를 생략하지 않는다.
"""
import copy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from strategy.engine import parse_timestamp
from trading.risk_ledger import amount, digest, local_day


def assess_observation(manager, review, now=None):
    """저장된 조회 검산 → 기존 위험 한도 평가 → 현지 거래일 중지 보존 → 원자 저장.

    pass/fail/unknown은 각 검사의 결과다. 모델 수치와 공식 검증 여부를 섞지 않는다.
    외부 자료가 없는 검사는 unknown이며, 사용자가 지정한 현금 모델을 kis_vps
    공식 현금 또는 완전한 자금 사건으로 승격하지 않는다.
    """
    manager.ready = False
    now = now or datetime.now(timezone.utc)
    stored = manager.state.get('risk_observations', {}).get(review['observation_id'])
    if not stored or any(stored.get(key) != value for key,value in review.items() if key != 'observation_id'):
        raise ValueError('risk_assessment_saved_review_mismatch')
    if (review['mode'] != 'kis_demo' or manager.state['mode'] != 'kis_demo'
            or review['account_fingerprint'] != manager.state.get('broker_identity')):
        raise ValueError('risk_assessment_account_mismatch')
    if not 0 <= (now-parse_timestamp(review['as_of'])).total_seconds() <= 30:
        raise ValueError('risk_assessment_stale')
    model = manager.state['user_cash_account']
    if model['observation_id'] != review['balance_observation_id'] or model['as_of'] != review['as_of']:
        raise ValueError('risk_assessment_model_changed')
    balance = manager.state['risk_observations'][review['balance_observation_id']]['balance_snapshot']
    policy = manager.policy
    before = copy.deepcopy(manager.state)
    prior = manager.state.get('risk_assessment_ledger', {})
    identity = manager.state['broker_identity']
    if prior and (prior['account_fingerprint'] != identity or prior['baseline_hash'] != digest(model['baseline'])):
        raise ValueError('risk_assessment_baseline_changed')
    if prior and parse_timestamp(prior['latest']['as_of']) > parse_timestamp(review['as_of']):
        raise ValueError('risk_assessment_out_of_order')
    ledger = copy.deepcopy(prior) if prior else {'schema':1, 'account_fingerprint':identity,
        'baseline_hash':digest(model['baseline']), 'days':{}, 'checkpoints':{}, 'peak_model_nav_usd':None,
        'maximum_observed_model_drawdown':None}
    controls = {}
    def check(name, status, reason, **values):
        controls[name] = {'status':status, 'reason':reason, **values}

    initial = amount(model['baseline']['cash_usd'])
    exposure = amount(balance['holdings_cost_basis_usd'])
    reserves = amount(review['remote_reserved_buy_usd']) + amount(review['local_reserved_buy_usd'])
    exposure_limit = amount(initial * Decimal(str(policy['maximum_exposure_fraction'])))
    check('usd_cash_and_reservations', 'fail' if Decimal(review['estimated_cash_after_cost_reserve_usd']) < reserves else 'pass',
          'model_cash_reservations_compared', cash_after_cost_reserve_usd=review['estimated_cash_after_cost_reserve_usd'], reserved_usd=str(reserves))
    check('total_investment_limit', 'pass' if exposure+reserves <= exposure_limit else 'fail',
          'existing_policy_applied', exposure_and_reservations_usd=str(exposure+reserves), limit_usd=str(exposure_limit))
    symbols = {row['symbol'] for row in balance['positions']}
    symbols.update(order['symbol'] for order in manager.state['orders'].values()
                   if order['side']=='BUY' and order['status'] in {'INTENT','SENDING','UNKNOWN','ACCEPTED','PARTIAL','CANCEL_PENDING'})
    check('position_count', 'pass' if len(symbols) <= 5 else 'fail', 'existing_five_position_limit', count=len(symbols))
    check('api_buying_power', 'unknown' if review['api_budget']['available_for_new_order_usd'] is None else 'pass',
          'current_account_bound_api_capacity', available_usd=review['api_budget']['available_for_new_order_usd'])
    check('order_reconciliation','fail' if review['unmatched_remote_orders'] or review['unresolved_local_orders'] else 'pass',
          'manual_and_unresolved_orders_checked')
    pause = Path(manager.connection.execute('PRAGMA database_list').fetchone()[2]).parent/'PAUSE_BUYS'
    check('operator_and_restore_gate','fail' if pause.exists() or manager.state.get('restore_gate') else 'pass',
          'existing_pause_restore_gates_preserved')
    check('execution_costs', 'unknown' if model['orders_with_costs_pending'] else 'pass',
          review['historical_cost_status'], final_costs_usd=model['confirmed_fees_usd'] if not model['orders_with_costs_pending'] else None)
    # 공식 RiskLedger 평가가 이미 있으면 그 근거를 재사용한다. 수동 verified 입력은 받지 않는다.
    authoritative_proof = None
    try:
        from trading.risk_ledger import RiskLedger
        candidate = RiskLedger(manager).context(now)
        official = manager.state['risk_ledger']['last_evaluation']
        if (candidate.eligible and candidate.positions == {row['symbol']:row['quantity'] for row in balance['positions']}
                and model['cash_usd'] is not None and model['modeled_nav_usd'] is not None
                and amount(official['cash_balance']) == amount(model['cash_usd'])
                and amount(official['net_asset_value']) == amount(model['modeled_nav_usd'])
                and manager.state['risk_ledger']['last_evaluation']['source_kind'] == 'kis_vps'):
            authoritative_proof = candidate
    except ValueError:
        pass
    check('cash_movement_coverage','pass' if authoritative_proof else 'unknown',
          'existing_authoritative_risk_checkpoint' if authoritative_proof else 'no_validated_complete_vps_cash_event_source')
    filled = sum(order['filled'] for order in model['orders'].values())
    losses = authoritative_proof.consecutive_losses if authoritative_proof else 0 if filled == 0 else None
    check('consecutive_loss_cooldown','pass' if losses is not None else 'unknown',
          'no_trades_in_model_scope' if filled == 0 else 'individual_final_costs_and_trade_close_history_required',
          consecutive_losses=losses)
    if authoritative_proof and losses >= policy['consecutive_losses']:
        last_loss = authoritative_proof.last_loss_at
        if not last_loss or (now-parse_timestamp(last_loss)).total_seconds() < policy['loss_cooldown_minutes']*60:
            controls['consecutive_loss_cooldown']['status'] = 'fail'
    day = local_day(review['as_of'])
    nav = amount(model['modeled_nav_usd']) if model['modeled_nav_usd'] is not None else None
    day_state = ledger['days'].setdefault(day, {'baseline_model_nav_usd':
        (str(initial) if day == local_day(model['baseline']['enrolled_at']) else prior.get('latest',{}).get('model_nav_usd')),
        'halted':False, 'basis':'enrollment_or_previous_model_observation'})
    daily_loss = None
    if nav is not None:
        if day_state['baseline_model_nav_usd'] is None:
            # 장중 첫 관측을 당일 전체 기준으로 소급하지 않는다.
            day_state['baseline_model_nav_usd'] = str(nav)
            day_state['basis'] = 'first_observation_partial_day'
        basis = amount(day_state['baseline_model_nav_usd'])
        daily_loss = max(Decimal(0),(basis-nav)/basis) if basis else Decimal(1)
        if daily_loss >= Decimal(str(policy['daily_loss_limit'])):day_state['halted'] = True
        peak = max(nav, amount(ledger['peak_model_nav_usd']) if ledger['peak_model_nav_usd'] is not None else initial)
        drawdown = (peak-nav)/peak if peak else Decimal(0)
        ledger['peak_model_nav_usd'] = str(peak)
        ledger['maximum_observed_model_drawdown'] = str(max(Decimal(ledger['maximum_observed_model_drawdown'] or '0'),drawdown))
    check('daily_loss_limit','fail' if day_state['halted'] else 'unknown' if daily_loss is None else 'pass',
          'observed_model_only_cash_flows_unverified', loss_ratio=str(daily_loss) if daily_loss is not None else None,
          limit=str(policy['daily_loss_limit']), latched=day_state['halted'])
    # 평가를 생략하지 않되 모델 계산만으로 공식 RiskProof를 발급하지 않는다.
    uncertain = sorted(name for name,row in controls.items() if row['status']=='unknown')
    failed = sorted(name for name,row in controls.items() if row['status']=='fail')
    evaluation = {'schema':1,'account_fingerprint':identity,'mode':'kis_demo','as_of':review['as_of'],
        'review_id':review['observation_id'],'policy_hash':digest(policy),'local_day':day,
        'basis':'user_designated_cash_plus_actual_readonly_observations',
        'model_nav_usd':str(nav) if nav is not None else None,
        'model_pnl_since_enrollment_usd':str(nav-initial) if nav is not None else None,
        'model_daily_loss_ratio':str(daily_loss) if daily_loss is not None else None,
        'order_limits':{'maximum_order_cost_usd':str(amount(initial*Decimal(str(policy['maximum_order_fraction'])))),
                        'maximum_trade_risk_usd':str(amount(initial*Decimal(str(policy['maximum_trade_risk'])))),
                        'maximum_total_exposure_usd':str(exposure_limit)},
        'maximum_observed_model_drawdown':ledger['maximum_observed_model_drawdown'],
        'external_cash_flows_verified':bool(authoritative_proof),'full_day_coverage_verified':False,
        'controls':controls,'failed_controls':failed,'unknown_controls':uncertain,
        'preparation_checks':{'future_final_cost_channel':{'status':'unknown',
            'reason':review['future_cost_channel_status']},'current_regular_quotes':{'status':'not_checked'}},
        'evaluation_complete':True,'evidence_complete':not uncertain,'known_controls_passed':not failed,
        'risk_approved':bool(authoritative_proof and not uncertain and not failed),'new_orders_allowed':False,
        'decision':'blocked_by_failed_controls' if failed else 'blocked_by_missing_evidence' if uncertain else 'risk_checks_approved' if authoritative_proof else 'await_authoritative_risk_ingest',
        'orders_hash':digest(manager.state['orders']),'cash_model_hash':digest(model)}
    identifier = digest(evaluation)
    ledger['checkpoints'][identifier] = evaluation
    ledger['latest'] = evaluation
    manager.state['risk_assessment_ledger'] = ledger
    try:manager._save()
    except Exception:
        manager.state = before
        manager.ready = False
        raise
    return {'assessment_id':identifier, **copy.deepcopy(evaluation)}


def latest_assessment(manager, now=None):
    """재시작 후에도 근거를 대조한다. 조회했다는 이유로 원본 시각을 갱신하지 않는다."""
    now = now or datetime.now(timezone.utc)
    value = manager.state.get('risk_assessment_ledger',{}).get('latest')
    if not value:raise ValueError('risk_assessment_unavailable')
    if value['account_fingerprint'] != manager.state.get('broker_identity') or manager.state['mode'] != 'kis_demo':
        raise ValueError('risk_assessment_account_mismatch')
    if not 0 <= (now-parse_timestamp(value['as_of'])).total_seconds() <= 30:
        raise ValueError('risk_assessment_stale')
    if (value['policy_hash'] != digest(manager.policy) or value['orders_hash'] != digest(manager.state['orders'])
            or value['cash_model_hash'] != digest(manager.state['user_cash_account'])):
        raise ValueError('risk_assessment_inputs_changed')
    return copy.deepcopy(value)
