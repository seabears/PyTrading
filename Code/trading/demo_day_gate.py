"""기존 모의 시험 진입점의 정규장 사전 관측 수명 관리. 서비스·부팅 설정을 변경하지 않는다."""
import json,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
from broker.sessions import regular_session
from paths import CODE_ROOT,DATA_ROOT
from tools.verify_quote_recovery import evaluate,session_bounds


def today_session():
    """현재 달력으로 오늘 장 시간을 반환한다. 장외면 인증도 읽지 않는다."""
    now=datetime.now(timezone.utc)
    day,opening,closing=session_bounds(now)
    return {'day':day,'opening':opening.isoformat() if opening else None,
            'closing':closing.isoformat() if closing else None,'regular_now':regular_session('US',now) is not None}


class QuoteWatchProcess:
    def __init__(self,folder):self.folder=Path(folder);self.process=None;self.log=None
    def close(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=10)
        if self.log:self.log.close()
    def __enter__(self):
        if not today_session()['regular_now']:raise ValueError('today_regular_session_not_open')
        if not self.folder.resolve().is_relative_to(DATA_ROOT.resolve()):raise ValueError('quote_watch_folder_outside_data')
        self.folder.mkdir(parents=True,exist_ok=False)
        self.log=(self.folder/'console.log').open('w',encoding='utf-8')
        self.process=subprocess.Popen([sys.executable,'-X','utf8',str(CODE_ROOT/'tools/demo_quote_watch.py'),
                                       '--folder',str(self.folder)],stdout=self.log,stderr=self.log)
        start=time.monotonic();last_notice=0
        try:
            while time.monotonic()-start<1050:
                if self.process.poll() is not None:raise ValueError('quote_watch_exited_before_recovery')
                if (self.folder/'recovery.json').exists():
                    recovery=evaluate(self.folder)
                    if recovery['regular_recovery_verified']:return self.folder/'recovery.json'
                    if recovery['day_history']['non_normal']:raise ValueError('quote_watch_has_failed_regular_observations')
                if time.monotonic()-last_notice>30:
                    print('정규장 전체 종목 시세 관측 중: 종목별10분·전체3회 기준을 확인합니다.',flush=True)
                    last_notice=time.monotonic()
                time.sleep(1)
            raise ValueError('quote_watch_recovery_time_limit')
        except BaseException:
            self.close();raise
    def __exit__(self,*_):self.close()
