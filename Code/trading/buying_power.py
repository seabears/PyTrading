"""매수 한도와 현금·손익 계산을 분리한다. 현금/NAV 원장은 입력으로 받지 않는다.

API 주문가능액에는 원격 미체결 예약이 반영된 것으로 처리한다. 완전한 주문 대조에서
확인된 원격 예약은 다시 빼지 않고, 아직 API에 반영되지 않은 로컬 주문만 차감한다.
이 함수의 통과는 상품·계좌 서비스·손실 한도·전송 허가의 통과를 뜻하지 않는다.
"""
from decimal import Decimal
from datetime import datetime, timezone
from strategy.engine import parse_timestamp
from trading.order_contract import broker_key
from trading.risk_ledger import amount, digest

ACTIVE_BUYS = {'INTENT','SENDING','UNKNOWN','ACCEPTED','PARTIAL','CANCEL_PENDING'}


def assess_buying_power(account, orders, *, current_id=None, order_cost='0'):
    """기존 비용 예약 완충1.003을 유지한다. order_cost는 완충을 포함한 USD다."""
    # cash는 구버전 계좌 스냅샷의 주문 여력 별칭이다. user_cash_account는 읽지 않는다.
    raw = account.get('buying_power_usd', account.get('cash'))
    if raw is None:
        raise ValueError('api_buying_power_missing')
    power = amount(raw)
    if 'buying_power_usd' in account and account.get('cash_is_available_order_capacity'):
        if power != amount(account['cash']):
            raise ValueError('buying_power_alias_mismatch')
    remote_ids = set(account.get('broker_reserved_ids', []))
    if remote_ids and account.get('remote_reservations_included') is not True:
        raise ValueError('remote_reservation_coverage_unproven')
    remote_ids = {broker_key(value) for value in remote_ids}
    local = Decimal(0)
    skipped = []
    for order in orders:
        if order['id'] == current_id or order['side'] != 'BUY' or order['status'] not in ACTIVE_BUYS:
            continue
        if order['status'] in {'SENDING','UNKNOWN'}:
            raise ValueError('buying_power_order_state_unknown')
        quantity, filled = order['quantity'], order['filled']
        if type(quantity) is not int or type(filled) is not int or not 0 <= filled <= quantity:
            raise ValueError('buying_power_quantity_invalid')
        identifier = order.get('broker_id')
        if identifier and broker_key(identifier) in remote_ids:
            skipped.append(order['id'])
        else:
            local += Decimal(quantity-filled) * amount(order['price']) * Decimal('1.003')
    required = amount(order_cost)
    available = max(Decimal(0), power-local)
    return {'source':'api_buying_power', 'buying_power_usd':str(power),
            'local_not_yet_reflected_reserve_usd':str(local),
            'broker_reserved_orders_not_deducted_again':skipped,
            'available_for_new_order_usd':str(available), 'requested_cost_usd':str(required),
            'within_buying_power':required + local <= power,
            'cash_or_nav_verification_required_for_this_calculation':False,
            'order_authorization_granted':False}


def capacity_account(capacity, inventory, as_of):
    """API 값과 대조된 원격 예약을 주문 한도 전용 스냅샷으로 만든다."""
    output = capacity['output']
    if output['tr_crcy_cd'] != 'USD':
        raise ValueError('buying_power_currency_invalid')
    return {'buying_power_usd':str(amount(output['ovrs_ord_psbl_amt'])),
            'buying_power_source':'inquire-psamount.output.ovrs_ord_psbl_amt',
            'as_of':as_of,'broker_reserved_ids':inventory['broker_reserved_ids'],
            'remote_reservations_included':inventory['remote_reservations_included']}


def bind_api_buying_power(manager, record, inventory):
    """현금 증명 대신 현재 프로세스가 검산한 API 주문가능액을 계좌에 연결한다."""
    manager._buying_power_binding = None
    now = datetime.now(timezone.utc)
    if (manager.state['mode'] != 'kis_demo' or record.get('environment') != 'vps'
            or record.get('operation') != 'overseas_stock.inquire_psamount'
            or record.get('method') != 'GET'
            or record.get('account_fingerprint') != manager.state.get('broker_identity')):
        raise ValueError('buying_power_capture_identity_invalid')
    if digest(record['payload']) != record.get('sha256') or record['payload'].get('rt_cd') != '0':
        raise ValueError('buying_power_capture_hash_or_status_invalid')
    if not 0 <= (now-parse_timestamp(record['at'])).total_seconds() <= 30:
        raise ValueError('buying_power_capture_stale')
    result = capacity_account(record['payload'], inventory, record['at'])
    result.update(account_fingerprint=manager.state['broker_identity'], mode='kis_demo',
                  payload_sha256=record['sha256'], request_context=record.get('request_context', {}))
    manager._buying_power_binding = digest(result)
    return result


def validate_api_buying_power(manager, account):
    """API 한도 자체의 계좌·해시·시각을 검증한다. 현금/NAV와 금액이 같을 필요는 없다."""
    evidence = account.get('buying_power_evidence')
    if not isinstance(evidence, dict) or getattr(manager,'_buying_power_binding',None) != digest(evidence):
        raise ValueError('current_api_buying_power_capture_required')
    if (evidence['account_fingerprint'] != manager.state.get('broker_identity')
            or evidence['mode'] != manager.state['mode'] or evidence['mode'] != 'kis_demo'):
        raise ValueError('buying_power_account_mismatch')
    if not 0 <= (datetime.now(timezone.utc)-parse_timestamp(evidence['as_of'])).total_seconds() <= 30:
        raise ValueError('buying_power_evidence_stale')
    if amount(account['buying_power_usd']) != amount(evidence['buying_power_usd']):
        raise ValueError('buying_power_snapshot_changed')
    for field in ['broker_reserved_ids','remote_reservations_included']:
        if account.get(field) != evidence[field]:
            raise ValueError('buying_power_snapshot_changed')
    if amount(account['cash']) != amount(evidence['buying_power_usd']):
        raise ValueError('buying_power_legacy_alias_changed')
    return evidence
