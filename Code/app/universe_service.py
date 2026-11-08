"""일별 자동 관찰 목록 갱신. 독립 스레드의 읽기 전용 수집으로 보유 관리를 막지 않는다."""
import copy
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.runtime import acquire_run_lock, AlreadyRunningError
from app.stateio import atomic_json
from app.universe import evaluate_daily, load_policy, policy_hash, publish_selection, spread_result
from paths import DATA_ROOT
from trading.daily_account import last_closed_day


class UniverseService:
    def __init__(self, runtime, options, *, folder=None, provider=None, clock=None):
        self.runtime, self.options = runtime, options
        self.folder = Path(folder or DATA_ROOT/'universe')
        self.policy = load_policy()
        self.provider = provider
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        """초기 검색은 비동기다. 준비 전에는 사용자 지정 종목만 사용하며 매수 창을 연장하지 않는다."""
        if self.policy['enabled']:
            self.thread = threading.Thread(target=self._loop, name='daily-universe-readonly', daemon=True)
            self.thread.start()
        return self

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=20)

    def _loop(self):
        self.folder.mkdir(parents=True,exist_ok=True)
        while not self.stop_event.is_set():
            try:
                with acquire_run_lock(self.folder/'scan.lock'):
                    if self.provider is None:
                        from broker.universe_data import UniverseData
                        self.provider = UniverseData(self.runtime, self.options, self.policy, self.folder)
                    while not self.stop_event.is_set():
                        try:
                            self.refresh()
                            delay = self.policy['spread_sample_seconds']
                        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
                            self._error(error, 'scan')
                            delay = self.policy['retry_seconds']
                        self.stop_event.wait(delay)
            except AlreadyRunningError:
                # 다른 전략의 정상 수집기를 오류로 처리해 공통 목록을 지우지 않는다.
                # 기존 수집기가 종료되면 잠금을 이어받아 다음 거래일 갱신을 계속한다.
                self.stop_event.wait(self.policy['spread_sample_seconds'])
            except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
                self._error(error, 'startup_or_lock')
                self.stop_event.wait(self.policy['retry_seconds'])

    def _error(self, error, stage):
        """자유문 예외·응답 원문·인증값을 기록하지 않는다. 손상 상태는 자동 초기화하지 않는다."""
        from broker.kis import KisApiError
        diagnostic = error.diagnostic() if isinstance(error,KisApiError) else {'category':type(error).__name__}
        allowed = {'universe_master_archive_invalid','universe_master_contract_changed','universe_master_duplicate',
                   'universe_master_empty','universe_master_size_limit','universe_multiple_exchange_conflict',
                   'universe_exchange_changed_requires_review','universe_ranking_empty_or_invalid',
                   'universe_ranking_page_repeated','universe_ranking_cursor_missing_or_repeated',
                   'universe_daily_pages_incomplete','universe_invalid_number'}
        if not isinstance(error,KisApiError) and str(error) in allowed:
            diagnostic['code'] = str(error)
        try:
            # 이전 자동 목록은 유지 자료로 보존하되 신규 진입 목록에서는 즉시 제외한다.
            # 이력에 원래 실패 원인(안전한 분류)과 실제 제외된 종목을 함께 남긴다.
            previous_path = self.folder/'selection.json'
            if previous_path.exists():
                previous = json.loads(previous_path.read_text(encoding='utf-8'))
                if previous.get('selected'):
                    rows = [{'symbol':symbol,'exchange':exchange,'passed':False,'reason':'screen_failed'}
                            for symbol,exchange in previous['selected'].items()]
                    publish_selection(self.folder,rows,previous['signal_day'],self.clock(),self.policy,
                                      scope={'failure_stage':stage,'error':diagnostic})
            atomic_json(self.folder/'status.json', {'at':self.clock().isoformat(),'status':'failed',
                        'stage':stage,'error':diagnostic,'new_selection_published':False})
        except (OSError, ValueError):
            print('자동 관찰 목록 상태 저장 실패 — 사용자 지정·보유 관리만 유지합니다.',flush=True)

    def refresh(self):
        """완료 일봉 날짜별로 검색한다. 표본 미달은 대기, 탈락은 제외하며 매 주기 이력을 보존한다."""
        now = self.clock(); required = last_closed_day(now)
        work_path = self.folder/'work.json'
        work = json.loads(work_path.read_text(encoding='utf-8')) if work_path.exists() else None
        if work is None or work['signal_day'] != required or work['policy_hash'] != policy_hash(self.policy):
            stocks = self.provider.masters(now,self.stop_event)
            users = {symbol for market,symbol in self.runtime['symbols'] if market=='US'}
            candidates, scope = self.provider.shortlist(stocks, users, self.stop_event)
            work = {'signal_day':required,'policy_hash':policy_hash(self.policy),'candidates':candidates,
                    'scope':scope,'daily':{}}
            atomic_json(work_path,work)
            # 전일 목록은 여기서 만료된다. 새 완료 일봉 미확인은 자동 선정 0건으로 처리한다.
            publish_selection(self.folder, [], required, now, self.policy, scope=scope)
        for symbol,stock in work['candidates'].items():
            if self.stop_event.is_set():
                return
            if symbol in work['daily'] and work['daily'][symbol]['reason'] != 'latest_completed_daily_missing':
                continue
            try:
                bars,detail = self.provider.daily(symbol,stock['exchange'],required)
                outcome = evaluate_daily(bars,detail,required,self.policy)
            except (OSError,ValueError,RuntimeError,KeyError,TypeError) as error:
                # 공통 인증·통신 오류를 모든 종목에서 반복하지 않고 제한된 다음 재시도로 넘긴다.
                self._error(error,'candidate_daily')
                raise
            work['daily'][symbol] = outcome
            atomic_json(work_path,work)
            atomic_json(self.folder/'status.json',{'at':self.clock().isoformat(),'status':'daily_screening',
                        'completed':len(work['daily']),'candidates':len(work['candidates']),'signal_day':required})
        rows=[]
        for symbol,stock in work['candidates'].items():
            if self.stop_event.is_set():
                return
            outcome = copy.deepcopy(work['daily'][symbol])
            if outcome['passed']:
                path = self.folder/'spreads'/(symbol+'.json')
                samples = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
                quote = self.provider.quote(symbol,stock['exchange'],self.clock())
                if quote:
                    samples.append(quote)
                    # 전 정규장과 당일 표본을 제한해 보존한다. 날짜별 이력에는 판정값이 남는다.
                    samples = samples[-2*self.policy['minimum_spread_samples']:]
                    atomic_json(path,samples)
                spread = spread_result(samples,required,self.clock(),self.policy)
                outcome.update(passed=spread['passed'],reason=spread['reason'],spread=spread)
            rows.append(dict(outcome,symbol=symbol,exchange=stock['exchange']))
        if last_closed_day(self.clock()) != required:
            return  # 날짜가 바뀌는 동안 수집한 목록을 새 날짜의 결과로 공개하지 않는다.
        manifest = publish_selection(self.folder, rows, required, self.clock(), self.policy, scope=work['scope'])
        atomic_json(self.folder/'status.json', {'at':self.clock().isoformat(),'status':'awaiting_samples_or_ready',
                    'signal_day':required,'selected':len(manifest['selected']),'screened':len(rows)})
