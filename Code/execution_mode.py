"""체결 방식 선택. 주문·서비스를 시작하지 않고 Config만 원자적으로 저장한다."""
import json
from trading.execution import load_execution,MODES
from app.stateio import atomic_json

def select_mode(mode,path=None):
    if mode not in (*MODES,'disabled'):raise ValueError('execution_mode_invalid')
    current=load_execution(path);values=current['settings']
    for name in MODES:values[name]['enabled']=name==mode
    atomic_json(current['path'],values,backup=True)
    return mode

def main():
    selected=load_execution();print('현재 체결 방식: '+selected['mode'])
    print('0: 모두 끄기 / 1: 내부 가상체결 / 2: KIS 모의체결 / 3: 실계좌(전송 잠금 유지)')
    try:
        value=input('번호: ').strip()
        modes={'0':'disabled','1':'internal_paper','2':'kis_demo','3':'live'}
        if value not in modes:print('변경하지 않았습니다.');return 1
        mode=select_mode(modes[value]);print('저장: '+mode+' / 실행 중인 전략을 종료한 뒤 다시 시작해야 적용됩니다.')
        if mode=='live':print('실계좌 전송 잠금은 해제하지 않았습니다.')
        return 0
    except (EOFError,KeyboardInterrupt):print('변경하지 않았습니다.');return 1

if __name__=='__main__':raise SystemExit(main())
