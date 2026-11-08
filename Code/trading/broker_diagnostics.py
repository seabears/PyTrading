"""증권사 조회·계좌 대조·저장 장애의 허용 목록 기반 진단. 예외 자유문은 저장하지 않는다."""
import copy
import json
import sqlite3
import time
import urllib.error
from datetime import datetime, timezone

STAGES = {
    'account_refresh', 'history_query_initial', 'history_query_final', 'history_normalization',
    'balances_query', 'buying_power_query', 'present_balance_query', 'snapshot_validation',
    'settlement_observation', 'balance_linkage', 'cash_model_update', 'risk_review', 'risk_ingest',
    'account_reconciliation', 'cost_import', 'posttrade_recording', 'account_contract',
    'position_projection', 'daily_plan_linkage', 'account_projection_storage',
    'cancel_preflight', 'cancel_transmission', 'intent_creation', 'intent_storage',
    'order_transmission', 'settlement_source_validation', 'authentication', 'broker_processing',
}
SAFE_CODES = {
    'history_changed_during_snapshot', 'captured_snapshot_hash_or_freshness_invalid',
    'actual_demo_capture_missing', 'buying_power_capture_missing_or_duplicated',
    'execution_observation_contract_mismatch', 'execution_observation_position_mismatch',
    'execution_observation_remote_order_missing', 'strategy_owned_position_mismatch',
    'daily_broker_position_metadata_missing', 'strategy_owned_settlement_quantity_mismatch',
    'strategy_shared_symbol_cost_allocation_requires_evidence', 'user_cash_history_missing',
    'user_cash_inventory_history_mismatch', 'user_cash_cumulative_history_changed',
    'strategy_daily_plan_identity_mismatch', 'strategy_daily_plan_identity_ambiguous',
    'risk_and_broker_snapshot_mismatch', 'account_observation_requires_review',
    'cancel_identity_unverified', 'diagnostic_broker_order_transmission_prohibited',
    'managed_order_preflight_failed', 'managed_order_not_transmitted',
    'strategy_mode_changed_before_http', 'strategy_regular_session_required_before_http',
    'untracked_remote_order', 'duplicate_order_identifier', 'duplicate_local_identifier',
    'account_or_mode_mismatch', 'symbol_mismatch', 'side_mismatch', 'quantity_mismatch',
    'price_or_type_mismatch', 'stale_cumulative_history',
}
PROVIDER_CODES = {'EGW00103', 'EGW00121', 'EGW00123', 'EGW00201', 'EGW00133'}
CATEGORIES = {'authentication_expired', 'authentication_cooldown', 'rate_limit', 'http_error',
              'connection_error', 'connection_cooldown', 'timeout', 'api_error', 'business_error',
              'response_decode_error', 'token_storage_error'}


def failure_details(error, stage, started, step_started=None):
    """이번 처리 시간만 측정한다. 메시지·URL·헤더·파일명은 반환하지 않는다."""
    from broker.kis import KisApiError, KisRateLimitError
    from broker.kis_api.client import KisPreflightError, KisOrderStateUnknown, KisOrderRejected
    stage = stage if isinstance(stage,str) and stage in STAGES else 'broker_processing'
    category, code, hint = 'processing_error', 'broker_processing_failed', '실행 기록의 실패 단계 확인'
    http_status, provider_code = None, None
    if isinstance(error, KisApiError):
        category = getattr(error, 'category', None)
        category = category if isinstance(category,str) and category in CATEGORIES else 'api_error'
        if getattr(error, 'stage', None) == 'authentication': stage = 'authentication'
        if isinstance(error, KisRateLimitError): category = 'rate_limit'
        if isinstance(error, KisPreflightError): category = 'preflight_blocked'
        if isinstance(error, KisOrderStateUnknown): category = 'order_state_unknown'
        if isinstance(error, KisOrderRejected): category = 'broker_rejected'
        raw_status = getattr(error, 'http_status', None)
        http_status = raw_status if type(raw_status) is int and 100 <= raw_status <= 599 else None
        raw_code = getattr(error, 'provider_code', None)
        provider_code = raw_code if isinstance(raw_code,str) and raw_code in PROVIDER_CODES else None
        code = category
        hint = '인증 환경·권한·호출 제한·통신 상태 확인; 불명 주문은 먼저 전체 대조'
    elif isinstance(error, sqlite3.Error):
        category, code, hint = 'ledger_storage_error', 'broker_ledger_storage_failed', 'SQLite 원장 경로·디스크 여유·쓰기 권한 확인'
    elif isinstance(error, (TimeoutError, urllib.error.URLError)):
        category, code, hint = 'connection_error', 'broker_connection_failed', '네트워크·DNS·응답 지연 확인'
    elif isinstance(error, OSError):
        category, code, hint = 'local_io_error', 'broker_local_io_failed', '해당 단계의 파일·디스크·권한 확인'
        if stage == 'account_projection_storage':
            category, code = 'projection_storage_error', 'strategy_projection_storage_failed'
    elif isinstance(error, (KeyError, TypeError)):
        category, code, hint = 'response_contract_error', 'broker_response_contract_failed', '응답 필드·형식과 정규화 계약 확인'
    elif isinstance(error, ValueError):
        category, code, hint = 'reconciliation_error', 'broker_reconciliation_failed', '전체 주문·보유·현금·원가와 로컬 원장 대조'
    message = str(error)
    if message in SAFE_CODES: code = message
    finished = time.monotonic()
    return {'at': datetime.now(timezone.utc).isoformat(), 'stage': stage, 'category': category,
            'code': code, 'hint': hint, 'http_status': http_status, 'provider_code': provider_code,
            'elapsed_seconds': max(0, finished - started),
            'step_seconds': max(0, finished - (step_started if step_started is not None else started)),
            'new_orders_allowed': False}


def record_failure(manager, details):
    """기록 실패로 원래 장애를 덮지 않는다. SQLite 실패 시 안전한 구조만 표준 출력에 남긴다."""
    manager.ready = False
    manager._broker_failure = copy.deepcopy(details)
    manager.state['broker_last_failure'] = copy.deepcopy(details)
    records = manager.state.setdefault('broker_failure_history', [])
    records.append(copy.deepcopy(details))
    # 금융 원장/체결은 그대로 두고 운영 진단만 최근 100건으로 제한한다.
    manager.state['broker_failure_history'] = records[-100:]
    try:
        manager._save()
    except Exception:
        manager._broker_failure['secondary_code'] = 'diagnostic_storage_failed'
        print(json.dumps({'broker_failure': manager._broker_failure}, ensure_ascii=False), flush=True)
    return copy.deepcopy(manager._broker_failure)


def failed_result(manager, error, stage, started, step_started=None):
    details = record_failure(manager, failure_details(error, stage, started, step_started))
    return {'observation_valid': False, 'reason': 'broker_' + details['stage'] + '_failed',
            'broker_error': details}
