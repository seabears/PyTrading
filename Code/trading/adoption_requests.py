"""재사용 수동 편입 신청 API. CLI는 신청만 쓰고 실제 대조는 전략 프로세스가 한다.

HTTP 서버나 주문 전송 API가 아니다. 외부 앱의 미등록 체결을 추정해서 가져오지
않으며, 현재 프로그램 주문 원장에 있는 전량 체결 보유만 신청 대상으로 제시한다.
"""
import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from pathlib import Path

from app.stateio import atomic_json
from paths import DATA_ROOT,CONFIG_ROOT
from strategy.engine import parse_timestamp
from trading.orders import ACTIVE
from trading.order_contract import broker_key

REQUEST_LIFETIME_HOURS=24  # 신청 유효기간. 실제 주문·위험 유효기간을 늘리는 값이 아니다.
MANUAL_OWNER_PREFIXES=('user_requested_single_demo:', 'manual_user:')


def _read_journal(path):
    path=Path(path)
    if not path.exists():
        raise ValueError('adoption_order_ledger_not_found')
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as connection:
        row=connection.execute('SELECT body FROM journal WHERE id=1').fetchone()
    if not row:
        raise ValueError('adoption_order_ledger_empty')
    state=json.loads(row[0])
    if state.get('mode')!='kis_demo' or state.get('alias')!='strategies':
        raise ValueError('adoption_demo_strategy_ledger_required')
    return state


def contract_hash(order):
    """수치·주문번호의 공식 표현 차이는 정규화하고 관리 소유자와는 분리한다."""
    contract={key:order.get(key) for key in ['id','symbol','side','quantity','filled','status','order_type','created_at']}
    contract.update(broker_id=broker_key(order['broker_id']),
        price=str(Decimal(order['price']).normalize()),notional=str(Decimal(order['notional']).normalize()))
    return hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()


def _local_status(state, order, owner):
    if order.get('side')!='BUY':
        return 'FILL_REVIEW_REQUIRED'
    owner_net=sum(item.get('filled',0)*(1 if item['side']=='BUY' else -1)
        for item in state['orders'].values() if item['symbol']==order['symbol']
        and item.get('strategy_owner')==order.get('strategy_owner'))
    if owner_net<=0:
        return 'CLOSED'
    if order['id'] in state.get('management_adoptions',{}):
        return 'MANAGED' if order.get('strategy_owner')==owner else 'OTHER_MANAGER'
    if not order.get('strategy_owner','').startswith(MANUAL_OWNER_PREFIXES):
        return 'OTHER_MANAGER'
    if order['status']!='FILLED' or type(order.get('filled')) is not int or order['filled']<1 or order['quantity']!=order['filled']:
        return 'FILL_REVIEW_REQUIRED'
    if any(item['status'] in ACTIVE for item in state['orders'].values()):
        return 'ACTIVE_ORDER_REVIEW_REQUIRED'
    other_owners={}
    for item in state['orders'].values():
        if item['id']!=order['id'] and item['symbol']==order['symbol'] and item.get('filled'):
            other_owner=item.get('strategy_owner','')
            other_owners[other_owner]=other_owners.get(other_owner,0)+item['filled']*(1 if item['side']=='BUY' else -1)
    return 'ALLOCATION_REVIEW_REQUIRED' if any(value!=0 for value in other_owners.values()) else 'REQUESTABLE_REQUIRES_REMOTE_CHECK'


def list_positions(journal_path, target_account_path):
    """로컬 SQLite 조회만 한다. 신청 가능은 실제 계좌 승인 완료라는 뜻이 아니다."""
    state=_read_journal(journal_path)
    owner=str(Path(target_account_path).resolve().relative_to(DATA_ROOT.resolve()))
    rows=[]
    for order in state['orders'].values():
        if order['side']!='BUY' or not order.get('filled'):
            continue
        rows.append({'order_id':order['id'],'symbol':order['symbol'],'filled_quantity':order['filled'],
            'average_fill_price':str(Decimal(order['notional'])/Decimal(order['filled'])),
            'status':_local_status(state,order,owner),'requires_remote_validation':True})
    return rows


def request_adoption(journal_path, target_account_path, selection, order_id, *, now=None):
    """사용자가 선택한 기존 체결을 신청한다. 신규 주문·계좌 승인값은 만들지 않는다."""
    from broker.diagnostic import diagnostic_active
    if diagnostic_active():
        raise ValueError('diagnostic_adoption_request_prohibited')
    if selection.get('mode')!='kis_demo':
        raise ValueError('adoption_demo_selection_required')
    now=now or datetime.now(timezone.utc)
    target=Path(target_account_path).resolve()
    if not target.is_relative_to((DATA_ROOT/'execution-accounts/kis_demo').resolve()):
        raise ValueError('adoption_target_strategy_path_invalid')
    account=json.loads(target.read_text(encoding='utf-8'))
    if account.get('execution_mode')!='kis_demo':
        raise ValueError('adoption_target_mode_invalid')
    state=_read_journal(journal_path)
    if not state.get('broker_identity'):
        raise ValueError('adoption_bound_account_required')
    order=state['orders'].get(order_id)
    owner=str(target.relative_to(DATA_ROOT.resolve()))
    if not order or _local_status(state,order,owner)!='REQUESTABLE_REQUIRES_REMOTE_CHECK':
        raise ValueError('adoption_not_locally_requestable')
    queue=DATA_ROOT/'management/adoption-requests'
    for path in sorted(queue.glob('*.json')):
        previous=json.loads(path.read_text(encoding='utf-8'))
        if (previous.get('order_id')==order_id and previous.get('target_owner')==owner
                and previous.get('status') in {'QUEUED','PROCESSING'}
                and parse_timestamp(previous['expires_at'])>now):
            return previous
    identifier=uuid.uuid4().hex
    request={'schema':1,'request_id':identifier,'status':'QUEUED','mode':'kis_demo',
        'confirmed_at':now.isoformat(),'expires_at':(now+timedelta(hours=REQUEST_LIFETIME_HOURS)).isoformat(),
        'account_fingerprint':state['broker_identity'],'execution_fingerprint':selection['fingerprint'],
        'candidate_hash':account['daily_candidate_hash'],'target_owner':owner,
        'order_id':order_id,'symbol':order['symbol'],'quantity':order['filled'],
        'source_contract_hash':contract_hash(order)}
    atomic_json(queue/(identifier+'.json'),request)
    return request


def list_requests():
    """현재 설치의 신청 상태만 읽는다. 다른 설치/Pi와 자동 동기화하지 않는다."""
    return [json.loads(path.read_text(encoding='utf-8')) for path in sorted((DATA_ROOT/'management/adoption-requests').glob('*.json'))]


def apply_pending_requests(manager, account, snapshot, *, now=None):
    """기존 전략 sync의 실제 전체 대조 뒤 호출한다. 적용한 수를 돌려줘 재조회를 요구한다."""
    if not hasattr(account,'candidate'):
        return 0
    queue=DATA_ROOT/'management/adoption-requests'
    if not queue.exists():
        return 0
    now=now or datetime.now(timezone.utc)
    try:
        owner=str(account.path.resolve().relative_to(DATA_ROOT.resolve()))
    except ValueError:
        return 0  # 다른 계좌/격리 진단은 이 설치의 관리 신청을 처리하지 않는다.
    applied=0
    for path in sorted(queue.glob('*.json')):
        request=json.loads(path.read_text(encoding='utf-8'))
        if (request.get('status') not in {'QUEUED','PROCESSING'} or request.get('target_owner')!=owner
                or request.get('symbol')!=snapshot['symbol']):
            continue
        try:
            if now>parse_timestamp(request['expires_at']):
                request.update(status='EXPIRED',last_reason='request_expired')
                atomic_json(path,request);continue
            selection=getattr(manager,'_strategy_execution_selection',{})
            order=manager.state['orders'].get(request['order_id'])
            if (request.get('mode')!='kis_demo' or manager.state.get('mode')!='kis_demo'
                or request.get('account_fingerprint')!=manager.state.get('broker_identity')
                or request.get('execution_fingerprint')!=selection.get('fingerprint')
                or request.get('candidate_hash')!=account.state.get('daily_candidate_hash')
                or not re.fullmatch(r'[0-9a-f]{32}',request.get('request_id',''))
                or not 0 <= (now-parse_timestamp(request['confirmed_at'])).total_seconds() <= REQUEST_LIFETIME_HOURS*3600
                or not order or request.get('quantity')!=order['filled']
                or request.get('source_contract_hash')!=contract_hash(order)):
                raise ValueError('request_binding_or_source_changed')
            previous=manager.state.get('management_adoptions',{}).get(request['order_id'])
            if previous:
                if (previous['target_owner']!=owner or order.get('strategy_owner')!=owner
                        or previous['account_fingerprint']!=manager.state.get('broker_identity')
                        or previous['candidate_hash']!=account.state.get('daily_candidate_hash')
                        or order.get('strategy_position')!=previous['management_position']):
                    raise ValueError('request_source_already_managed_elsewhere')
                request.update(status='APPLIED',applied_at=previous['adopted_at'],last_reason='existing_receipt_restored')
                atomic_json(path,request);continue
            if getattr(manager,'_execution_observation_valid',False) is not True:
                continue
            source=account.path.parent/'sources'/account.state['last_signal_day']/(request['symbol']+'.json')
            if not source.exists():
                request.update(status='QUEUED',last_reason='closed_daily_source_unavailable',last_attempt_at=now.isoformat())
                atomic_json(path,request);continue
            request.update(status='PROCESSING',last_attempt_at=now.isoformat())
            atomic_json(path,request)
            from trading.strategy_adoption import adopt_manual_fill
            receipt=adopt_manual_fill(manager,account,request['order_id'],snapshot,
                json.loads(source.read_text(encoding='utf-8')),now=now,
                authorization={'request_id':request['request_id'],'confirmed_at':request['confirmed_at'],
                               'source':'local_operator_confirmation'})
            request.update(status='APPLIED',applied_at=receipt['adopted_at'],last_reason='management_adopted')
            atomic_json(path,request);applied+=1
        except (ValueError,KeyError,TypeError) as error:
            # 고정 검증 코드만 기록한다. 서버 자유문·키·응답 본문은 저장하지 않는다.
            code=str(error)
            code=code if re.fullmatch(r'(adoption|request)_[a-z0-9_]{1,100}',code) else 'request_validation_failed'
            transient={'adoption_quote_stale','adoption_current_process_account_observation_required'}
            request.update(status='QUEUED' if code in transient else 'FAILED',last_reason=code,last_attempt_at=now.isoformat())
            atomic_json(path,request)
    return applied
