"""한정 시험용 정규장 시세 관측. 별도 폴더에 실제 호가만 기록하며 주문 기능이 없다."""
import argparse,json,signal,sys,time,threading,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from app.runtime import load_run_settings,acquire_run_lock
from app.operations import OperationMonitor
from app.stateio import atomic_json
from broker.kis_setup import create_kis_client,load_kis_settings
from broker.kis import BASE_URLS,TOKEN_PATH,KisApiError
from broker.kis_market import US_QUOTE,normalize_quote,wait_for_quote_time
from broker.sessions import regular_session
from paths import CONFIG_ROOT,DATA_ROOT
from trading.observation_journal import ObservationJournal
from tools.verify_quote_recovery import evaluate


def validate_quote_request(request):
    """인증과 실제 호가GET만 허용한다. 계좌/주문 URL은 전부 거절한다."""
    url=urllib.parse.urlsplit(request.full_url)
    expected=urllib.parse.urlsplit(BASE_URLS['prod'])
    if url.scheme!='https' or url.netloc!=expected.netloc:
        raise ValueError('quote_watch_prod_quote_host_required')
    if (request.get_method()=='GET' and url.path==US_QUOTE
            or request.get_method()=='POST' and url.path==TOKEN_PATH):return
    raise ValueError('quote_watch_order_or_account_http_blocked')


def collect(folder,stop,maximum_seconds=1800):
    """모든 종목을 실제 순회한다. 과거 호가·가상 계좌·성과 기록은 만들지 않는다."""
    if not folder.resolve().is_relative_to(DATA_ROOT.resolve()):raise ValueError('quote_watch_folder_outside_data')
    if regular_session('US',datetime.now(timezone.utc)) is None:raise ValueError('quote_watch_regular_session_required')
    folder.mkdir(parents=True,exist_ok=True)
    runtime=load_run_settings();options=load_kis_settings(CONFIG_ROOT/'kis.json')
    symbols=sorted({symbol for market,symbol in runtime['symbols'] if market=='US'})
    client=create_kis_client(runtime['env_file'],options)
    if client.environment!='prod':raise ValueError('quote_watch_separate_prod_quotes_required')
    original=urllib.request.urlopen
    def guarded(request,*args,**kwargs):
        validate_quote_request(request)
        return original(request,*args,**kwargs)
    urllib.request.urlopen=guarded
    deadline=time.monotonic()+maximum_seconds
    try:
        with acquire_run_lock(folder/'watch.lock'),ObservationJournal(folder) as journal:
            monitor=OperationMonitor(folder);monitor.save()
            journal.record('startup',{'versions':{'purpose':'quotes_only_no_account'},'restored_plans':[]})
            empty_account=SimpleNamespace(state={'positions':{},'quote_times':{}})
            while not stop.is_set() and time.monotonic()<deadline:
                cycle_start=time.monotonic();monitor.begin_cycle()
                for symbol in symbols:
                    if stop.is_set() or time.monotonic()>=deadline:break
                    now=datetime.now(timezone.utc);session=regular_session('US',now)
                    if session is None:return
                    started=time.monotonic();quote=None;failed=False;diagnostic=None
                    try:
                        raw=client.get(US_QUOTE,{'AUTH':'','EXCD':options['us_exchanges'][symbol],'SYMB':symbol})
                        quote=normalize_quote(raw,'US',session)
                        now=wait_for_quote_time(quote,datetime.now(timezone.utc))
                    except (ValueError,OSError,RuntimeError,KeyError) as error:
                        failed=True
                        diagnostic=error.diagnostic() if isinstance(error,KisApiError) else {'category':'quote_processing_error'}
                        now=datetime.now(timezone.utc)
                    elapsed=time.monotonic()-started
                    snapshot={'market':'US','symbol':symbol,'now':now.isoformat(),'quote':quote,
                              'regular_session_open':regular_session('US',now) is not None,'data_mode':'live_observation'}
                    if failed:monitor.error('US:'+symbol,'quote_lookup_failed',diagnostic,elapsed)
                    else:monitor.observe(snapshot,elapsed)
                    age=(now-datetime.fromisoformat(quote['available_at'])).total_seconds() if quote else None
                    journal.record('observation',{'symbol':symbol,'input_kind':'live_observation',
                        'regular_session_open':snapshot['regular_session_open'],'quote':quote,'quote_age_seconds':age,
                        'request_seconds':elapsed,'lookup_error':failed,'error':diagnostic,
                        'reason':'quote_lookup_failed' if failed else 'quote_only_observation','action':'OBSERVE',
                        'cash':None,'positions':{},'pending_plans':[],'buy_halts':monitor.state['buy_halts'],
                        'manual_buy_pause':False,'affected_plans':[],'valuation':None,'fill':None},now.isoformat())
                monitor.end_cycle(empty_account,max(0,60-(time.monotonic()-cycle_start)))
                journal.record('heartbeat',{})
                recovery=evaluate(folder,expected_symbols=symbols)
                atomic_json(folder/'recovery.json',{'recovery':recovery,'observation_folder':str(folder)})
                print(json.dumps({'quote_watch':True,'normal_quotes':recovery['normal_quotes'],
                                  'regular_recovery_verified':recovery['regular_recovery_verified']}),flush=True)
                if monitor.state['buy_halts'] and recovery['quote_errors_or_missing']:
                    return  # 실패 구간을 지우거나 새 폴더로 자동 재시작하지 않는다.
                stop.wait(max(0,60-(time.monotonic()-cycle_start)))
            journal.record('control',{'action':'process_stopped'})
    finally:
        urllib.request.urlopen=original


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder',type=Path,required=True)
    args=parser.parse_args();stop=threading.Event()
    for signum in (signal.SIGINT,signal.SIGTERM):signal.signal(signum,lambda *_:stop.set())
    try:collect(args.folder,stop)
    except (ValueError,OSError,RuntimeError,KeyError):
        print('호가 관측 실패. 원장과 안전한 진단을 확인하세요. 주문은 전송하지 않았습니다.',flush=True);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
