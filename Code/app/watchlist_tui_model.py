"""관찰 목록 TUI의 파일 조회·설정 저장. 인증 파일·증권사 API·서비스 제어를 호출하지 않는다."""
import copy
from contextlib import closing
import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.runtime import SETTINGS_PATH, acquire_run_lock, load_run_settings
from app.stateio import atomic_json
from app.universe import load_policy, selection_view
from paths import CONFIG_ROOT, DATA_ROOT, PROJECT_ROOT

REASONS = {
    'eligible':'선정 완료', 'awaiting_regular_spread_samples':'정규장 호가 표본 대기',
    'regular_spread_samples_missing':'정규장 호가 표본 없음', 'insufficient_or_wide_spread':'호가 표본 부족/간격 초과',
    'price_below_minimum':'최소 주가 미달', 'median_turnover_below_minimum':'20일 거래대금 미달',
    'recent_turnover_below_minimum':'최근 5일 거래대금 미달', 'atr_above_maximum':'변동성 상한 초과',
    'market_cap_below_minimum':'최소 시총 미달', 'latest_completed_daily_missing':'최신 완료 일봉 누락',
    'daily_coverage_below_59_of_60':'최근 일봉 부족', 'corporate_action_or_price_mismatch':'기업행동/가격 불일치 검토',
    'currency_or_trade_permission_unconfirmed':'통화/거래 가능 여부 미확인', 'screen_failed':'선정 작업 실패',
    'not_in_daily_search_scope':'당일 검색 범위에서 제외', 'below_selection_limit':'선정 순위 상한 초과',
    'selection_unavailable':'유효한 선정 자료 없음', 'selection_missing':'선정 자료 준비 전',
    'current_selection':'최신 목록 적용 가능', 'selection_expired_or_policy_changed':'목록 만료/설정 변경',
    'latest_screen_failed':'최근 검색 실패', 'disabled':'자동 선정 끔', 'daily_screening':'일봉 검사 중',
    'awaiting_samples_or_ready':'표본 수집/선정 준비', 'failed':'검색 실패',
}

# 화면은 비율을 %로 보여주고 입력받는다. 저장 단위는 기존 0~1 비율을 그대로 쓴다.
POLICY_FIELDS = [
    ('minimum_price_usd','최소 주가','USD',False),
    ('minimum_market_cap_usd','최소 시총 계산값','USD',False),
    ('minimum_turnover20_usd','20일 거래대금 중앙값','USD',False),
    ('minimum_turnover5_usd','최근 5일 최소 거래대금','USD',False),
    ('maximum_atr_ratio','최대 ATR 비율','%',False),
    ('maximum_spread_ratio','최대 호가 간격','%',False),
    ('minimum_spread_samples','최소 호가 표본','개',True),
    ('maximum_auto_symbols','자동 선정 최대 종목','개',True),
    ('ranking_per_exchange','거래소별 순위 상한','개',True),
    ('maximum_ranking_pages','최대 순위 페이지','쪽',True),
    ('spread_sample_seconds','호가 표본 최소 간격','초',True),
    ('request_interval_seconds','검색 요청 간격','초',False),
    ('retry_seconds','오류 재시도 간격','초',True),
]


def read_json(path, default=None):
    if not path.exists():
        return copy.deepcopy(default)
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def settings_path():
    """기존 실행과 동일하게 PYTRADING_SETTINGS를 적용한다. 상대 경로는 Code 기준이다."""
    path = Path(os.environ.get('PYTRADING_SETTINGS', str(SETTINGS_PATH))).expanduser()
    return (path if path.is_absolute() else PROJECT_ROOT/path).resolve()


class WatchlistModel:
    def __init__(self, *, settings=None, config_root=None, data_root=None, clock=None):
        self.settings = Path(settings) if settings else settings_path()
        self.config_root = Path(config_root or CONFIG_ROOT)
        self.data_root = Path(data_root or DATA_ROOT)
        self.policy_path = self.config_root/'universe.json'
        self.folder = self.data_root/'universe'
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def snapshot(self, *, include_history=True):
        """실행 설정·유효 목록·검색 진행·이력만 읽는다. 빈 기록과 읽기 실패를 구분한다."""
        runtime = load_run_settings(self.settings)
        policy = load_policy(self.policy_path)
        errors = []
        def optional(path, fallback):
            try:
                return read_json(path,fallback)
            except (OSError,ValueError,TypeError):
                errors.append('읽기 실패: '+path.name)
                return copy.deepcopy(fallback)
        manifest = optional(self.folder/'selection.json',{})
        status = optional(self.folder/'status.json',{})
        work = optional(self.folder/'work.json',{})
        # 선택된 체결 방식의 계좌 투영만 읽는다. 자료가 없으면 계좌를 새로 만들지 않는다.
        from trading.execution import load_execution, strategy_path
        execution = load_execution(None if self.config_root==CONFIG_ROOT else self.config_root/'execution.json')
        base = self.data_root/'paper-daily-frozen'/'account.json'
        if self.data_root == DATA_ROOT:
            target = Path(os.environ.get('PYTRADING_DAILY_DIR', str(base.parent))).resolve()
            if not target.is_relative_to(self.data_root.resolve()):
                raise ValueError('daily_account_path_outside_data')
            base = target/'account.json'
            account_path = strategy_path(base,execution)
        else:
            account_path = base  # 합성 검사/격리 미리보기용 경로. 운영 계좌로 바꾸지 않는다.
        account = optional(account_path,{})
        orders = []
        ledger_path = self.data_root/'execution/kis_demo/strategy-orders.sqlite'
        if execution['mode']=='kis_demo' and ledger_path.exists():
            try:
                with closing(sqlite3.connect(ledger_path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.5)) as connection:
                    connection.execute('PRAGMA query_only=ON')
                    row = connection.execute('SELECT body FROM journal WHERE id=1').fetchone()
                    if row:
                        orders = list(json.loads(row[0]).get('orders',{}).values())
            except (sqlite3.Error,ValueError,TypeError):
                errors.append('주문 원장 읽기 실패: 관리 대상은 미확인')
        view = selection_view(runtime['symbols'],account,self.clock(),folder=self.folder,policy=policy,broker_orders=orders)
        rules = optional(self.config_root/'product-policy.json',{}).get('verified_instruments',{})
        discovered = optional(self.folder/'verified-stocks.json',{})
        names = {symbol:row.get('name','') for symbol,row in {**discovered,**rules}.items()}
        rows = manifest.get('rows',[]) if isinstance(manifest,dict) else []
        by_symbol = {row['symbol']:row for row in rows if isinstance(row,dict) and 'symbol' in row}
        if isinstance(work,dict):
            for symbol,row in work.get('daily',{}).items():
                by_symbol.setdefault(symbol,dict(row,symbol=symbol))
        history = []
        history_paths=sorted((self.folder/'history').glob('*/*.json'),reverse=True)[:80] if include_history else []
        for path in history_paths:
            record = optional(path,{})
            for symbol in record.get('added',[]):
                history.append({'at':record.get('published_at'),'symbol':symbol,'change':'추가','reason':'eligible'})
            for removed in record.get('removed',[]):
                history.append({'at':record.get('published_at'),'symbol':removed.get('symbol'),
                                'change':'제외','reason':removed.get('reason')})
        return {'runtime':runtime,'policy':policy,'view':view,'status':status,'manifest':manifest,
                'rows':by_symbol,'history':history,'names':names,'errors':errors,'execution_mode':execution['mode'],
                'account_source_exists':account_path.exists(),'account_path':str(account_path),
                'settings_path':str(self.settings),'settings_hash':digest(self.settings),'policy_hash':digest(self.policy_path),
                'read_at':self.clock().isoformat()}

    def _save(self,path,value,expected,operation,changes):
        """동시 수정은 거절하고 원본 한 세대를 보존한다. 감사 기록에는 설정 전체를 넣지 않는다."""
        lock_path = path.with_suffix(path.suffix+'.edit.lock')
        with acquire_run_lock(lock_path):
            if digest(path)!=expected:
                raise ValueError('설정이 다른 곳에서 변경됐습니다. 새로고침 후 다시 시도하세요.')
            identifier = self.clock().strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:12]
            audit_path = self.data_root/'watchlist-tui/audit'/(identifier+'.json')
            audit = {'at':self.clock().isoformat(),'operation':operation,'changes':changes,'status':'INTENT',
                     'restart_required':True,'orders_sent':False}
            atomic_json(audit_path,audit)
            atomic_json(path,value,backup=True)
            audit['status']='SAVED'
            try:
                atomic_json(audit_path,audit)
                return '저장했습니다. 실행 중인 관찰 프로그램에는 재시작 후 반영됩니다.'
            except OSError:
                return '설정은 저장됐습니다. 감사 기록 완료 저장에 실패했습니다. 재시작 전 기록을 확인하세요.'

    def add_user(self,text,expected):
        """확인된 USD 주식만 추가한다. 상품 등록·거래소·금지 정책을 TUI에서 우회하지 않는다."""
        symbol = text.strip().upper().removeprefix('US:')
        if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',symbol):
            raise ValueError('미국 주식 티커를 입력하세요. 예: MSFT 또는 US:MSFT')
        from broker.product_policy import load_product_rules, validate_symbol
        rules = load_product_rules()
        item = rules['verified_instruments'].get(symbol)
        if not item or item.get('asset_type')!='stock':
            raise ValueError('공식 상품 분류가 등록된 미국 주식만 추가할 수 있습니다. 자동 검색의 상품 확인 자료를 먼저 준비하세요.')
        validate_symbol(symbol,rules)
        from broker.kis_setup import load_kis_settings
        runtime = load_run_settings(self.settings)
        options = load_kis_settings(runtime['broker_config'])
        if symbol not in options['us_exchanges']:
            raise ValueError('확인된 거래소 정보가 없습니다. 거래소 자료를 먼저 준비하세요.')
        raw = read_json(self.settings)
        ticker = 'US:'+symbol
        if ticker in raw['symbols']:
            raise ValueError('이미 사용자 지정 목록에 있습니다.')
        raw['symbols'].append(ticker)
        return self._save(self.settings,raw,expected,'add_user',{'symbol':ticker})

    def remove_user(self,ticker,expected):
        raw = read_json(self.settings)
        if ticker not in raw['symbols']:
            raise ValueError('현재 사용자 지정 목록에 없는 종목입니다.')
        if len(raw['symbols'])<=1:
            raise ValueError('사용자 지정 종목은 최소 1개를 유지해야 합니다.')
        raw['symbols'].remove(ticker)
        return self._save(self.settings,raw,expected,'remove_user',{'symbol':ticker})

    def toggle(self,expected):
        policy = load_policy(self.policy_path)
        policy['enabled'] = not policy['enabled']
        return self._save(self.policy_path,policy,expected,'toggle_auto',{'enabled':policy['enabled']})

    def edit_condition(self,key,text,expected):
        fields = {row[0]:row for row in POLICY_FIELDS}
        if key not in fields:
            raise ValueError('지원하지 않는 조건입니다.')
        _,label,unit,integer = fields[key]
        cleaned = text.strip().replace(',','')
        if integer and not re.fullmatch(r'\d+',cleaned):
            raise ValueError('정수를 입력하세요.')
        try:
            value = int(cleaned) if integer else float(cleaned)
        except ValueError:
            raise ValueError('숫자를 입력하세요.') from None
        if unit=='%':
            value /= 100
        policy = load_policy(self.policy_path)
        policy[key] = value
        # 기존 검증기의 상한/하한을 그대로 사용하며 임시 파일을 운영 Config에 만들지 않는다.
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            temporary=Path(directory)/'universe.json'
            temporary.write_text(json.dumps(policy),encoding='utf-8')
            try:
                load_policy(temporary)
            except ValueError:
                raise ValueError('허용 범위를 벗어났습니다. 기존 최소 기준·최대 한도 안에서 입력하세요.') from None
        return self._save(self.policy_path,policy,expected,'edit_condition',{'key':key,'value':value,'display_unit':unit})
