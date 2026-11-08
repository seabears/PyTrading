"""라즈베리파이·Linux SSH 관찰 목록 TUI. 표준 라이브러리만 사용한다.

화면은 로컬 기록을 2초마다 다시 읽는다. 종목·선정 조건 저장과 화면 조회만 제공하며
주문, 인증, 서비스 시작/중지, 매수 중지 해제 기능은 넣지 않는다.
"""
import math
import os
import select
import shutil
import signal
import sys
import time
import unicodedata

from app.watchlist_tui_model import WatchlistModel, POLICY_FIELDS, REASONS

TABS = ['사용자 지정','자동 선정·대기','추가·제외 이력','관리 전용','선정 조건']


def safe_text(value):
    """저장 자료의 제어문자·ANSI 코드·줄바꿈이 터미널 명령으로 작동하지 않게 한다."""
    return ''.join(character if not unicodedata.category(character).startswith('C') else ' '
                   for character in str(value if value is not None else '-'))


def fit(value,width):
    text = safe_text(value)
    result = ''; used = 0
    for character in text:
        size = 0 if unicodedata.combining(character) else (2 if unicodedata.east_asian_width(character) in 'WF' else 1)
        if used+size > width:
            break
        result += character; used += size
    return result+' '*(width-used)


def number(value,scale=1,digits=2):
    try:
        value = float(value)/scale
        return f'{value:,.{digits}f}' if math.isfinite(value) else '-'
    except (TypeError,ValueError):
        return '-'


def table_rows(snapshot,tab):
    """화면에 필요한 허용 필드만 만든다. 계좌 식별자·인증 경로·원문 응답은 출력하지 않는다."""
    view = snapshot['view']; names = snapshot['names']
    if tab==0:
        return [(market+':'+symbol,names.get(symbol,''),'사용자 지정') for market,symbol in view['users']]
    if tab==1:
        rows = snapshot['rows']
        symbols = sorted(set(rows)|set(view['automatic']))
        return [(symbol,'선정' if symbol in view['automatic'] else '대기/탈락',
                 number(rows.get(symbol,{}).get('turnover20_usd_approx'),1e8),
                 number(rows.get(symbol,{}).get('atr_ratio'),.01),
                 str(rows.get(symbol,{}).get('spread',{}).get('samples','-')),
                 REASONS.get(rows.get(symbol,{}).get('reason'),rows.get(symbol,{}).get('reason','자료 대기')))
                for symbol in symbols]
    if tab==2:
        return [(row.get('at','-'),row.get('symbol','-'),row['change'],REASONS.get(row['reason'],row['reason']))
                for row in snapshot['history']]
    if tab==3:
        return [(market+':'+symbol,names.get(symbol,''),'신규 매수 제외 · 보유/주문 관리')
                for market,symbol in view['management_only']]
    rows = []
    for key,label,unit,integer in POLICY_FIELDS:
        value = snapshot['policy'][key]*(100 if unit=='%' else 1)
        rows.append((label,number(value,digits=0 if integer else 3),unit,key))
    return rows


def render(snapshot,tab,selected,message,width=100,height=30):
    """한글 셀 폭을 계산해 좁은 SSH 터미널에서도 오른쪽 경계를 넘지 않게 한다."""
    if width<60 or height<16:
        return fit('터미널을 가로 60칸·세로 16줄 이상으로 늘려주세요. q 종료',max(1,width))
    rows=table_rows(snapshot,tab)
    capacity=max(3,height-14)
    selected=max(0,min(selected,len(rows)-1))
    page=selected//capacity if rows else 0
    status=snapshot['status'];view=snapshot['view']
    lines=['관찰 목록 관리  |  주문·서비스 제어 없음',
           '  '.join(('['+str(index+1)+' '+name+']') if index==tab else str(index+1)+' '+name for index,name in enumerate(TABS)),
           '-'*width,
           f"사용자 {len(view['users'])}  자동 {len(view['automatic'])}  관리 전용 {len(view['management_only'])}  자동 선정 {'켬' if snapshot['policy']['enabled'] else '끔'}",
           '적용 상태: '+REASONS.get(view['reason'],view['reason'])+' | 수집: '+REASONS.get(status.get('status'),status.get('status','기록 없음')),
           '선정 일봉: '+str(snapshot['manifest'].get('signal_day','-'))+' | 자료 갱신: '+str(status.get('at',snapshot['manifest'].get('published_at','-'))),
           '-'*width]
    headers=[('종목','이름','구분'),('종목','상태','거래대금 억USD','ATR %','표본','사유'),
             ('기록 시각(원본)','종목','변경','사유'),('종목','이름','관리 상태'),('조건','현재 값','단위','설정 이름')][tab]
    widths=[(16, max(12,width-36),16),(12,12,17,10,7,max(10,width-63)),
            (28,12,8,max(10,width-53)),(16,22,max(10,width-42)),(28,18,8,max(10,width-59))][tab]
    lines.append('  '+' '.join(fit(value,size) for value,size in zip(headers,widths)))
    for index,row in enumerate(rows[page*capacity:(page+1)*capacity],page*capacity):
        lines.append(('> ' if index==selected else '  ')+' '.join(fit(value,size) for value,size in zip(row,widths)))
    if not rows:
        lines.append('  '+('계좌 자료가 없어 관리 대상은 미확인입니다.' if tab==3 and not snapshot['account_source_exists'] else '표시할 기록이 없습니다. 미수집은 조건 통과를 뜻하지 않습니다.'))
    while len(lines)<height-6:lines.append('')
    lines += ['-'*width,
              f"{TABS[tab]} · {page+1}/{max(1,math.ceil(len(rows)/capacity))}쪽 · 체결 설정 {snapshot['execution_mode']}",
              '1~5 탭  ↑↓/j k 선택  n/p 페이지  Enter 상세  r 새로고침  q 종료',
              'a 사용자 추가  d 사용자 삭제  t 자동 선정 켜기/끄기  e 조건 수정',
              '변경은 파일 저장 후 관찰 프로그램 재시작이 필요합니다. TUI는 재시작하지 않습니다.',
              message or (' / '.join(snapshot['errors']) if snapshot['errors'] else '화면은 2초마다 로컬 기록을 갱신합니다. 시세 API를 호출하지 않습니다.')]
    return '\n'.join(fit(line,width).rstrip() for line in lines[:height])


class Terminal:
    """Windows는 msvcrt, Linux는 termios/select를 쓴다. 입력 모드는 항상 복원한다."""
    def __init__(self):
        self.interactive=sys.stdin.isatty() and sys.stdout.isatty()
        self.ansi=self.interactive
        self.console_mode=None
        self._frame_lines = None
        self._frame_size = None

    def __enter__(self):
        if self.interactive and os.name=='nt':
            import ctypes
            from ctypes import wintypes
            kernel=ctypes.windll.kernel32
            kernel.GetStdHandle.argtypes=[wintypes.DWORD];kernel.GetStdHandle.restype=wintypes.HANDLE
            kernel.GetConsoleMode.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
            kernel.SetConsoleMode.argtypes=[wintypes.HANDLE,wintypes.DWORD]
            handle=kernel.GetStdHandle(-11)
            mode=wintypes.DWORD()
            if kernel.GetConsoleMode(handle,ctypes.byref(mode)):
                self.console_mode=(handle,mode.value)
                self.ansi=bool(kernel.SetConsoleMode(handle,mode.value|4))
            else:self.ansi=False
            if not self.ansi:self.interactive=False
        if self.ansi:
            sys.stdout.write('\x1b[?1049h\x1b[?25l');sys.stdout.flush()
        return self

    def __exit__(self,*unused):
        if self.ansi:
            sys.stdout.write('\x1b[?25h\x1b[?1049l');sys.stdout.flush()
        if self.console_mode:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(*self.console_mode)

    def invalidate(self):
        """입력창·창 크기 변경 후에는 행을 다시 그리되 화면 전체를 비우지 않는다."""
        self._frame_lines = None

    def draw(self,text):
        """변경 행만 절대 좌표로 덮어쓴다. 같은 화면은 출력하지 않아 SSH 깜빡임을 줄인다.

        매 2초 전체 화면 지우기(ED 2)를 보내던 방식을 제거했다. 수정할 모든 행을
        한 문자열로 모아 한 번에 출력한다. 짧아진 행의 나머지만 EL로 지우며,
        마지막 열까지 찬 행은 EL을 생략해 오른쪽 끝 문자가 지워지지 않게 한다.
        """
        if not self.ansi:
            print(text,flush=True)
            return
        size = shutil.get_terminal_size((100,30))
        lines = [fit(line,size.columns).rstrip() for line in text.splitlines()[:size.lines]]
        previous = self._frame_lines
        force = previous is None or self._frame_size != size
        previous = previous or []
        changes = []
        count = size.lines if force else min(size.lines,max(len(previous),len(lines)))
        for index in range(count):
            line = lines[index] if index<len(lines) else ''
            old = previous[index] if index<len(previous) else ''
            if not force and line == old:
                continue
            width = sum(0 if unicodedata.combining(character) else
                        (2 if unicodedata.east_asian_width(character) in 'WF' else 1)
                        for character in line)
            changes.append(f'\x1b[{index+1};1H'+line+('\x1b[K' if width<size.columns else ''))
        if changes:
            sys.stdout.write(''.join(changes))
            sys.stdout.flush()
        self._frame_lines = lines
        self._frame_size = size

    def prompt(self,text):
        if self.ansi:
            height=shutil.get_terminal_size((100,30)).lines
            sys.stdout.write(f'\x1b[{height};1H\x1b[2K\x1b[?25h')
        try:return input(text)
        finally:
            if self.ansi:
                sys.stdout.write('\x1b[?25l')
                self.invalidate()  # 입력 안내·줄바꿈이 남은 행도 다음 프레임에서 덮어쓴다.

    def key(self,timeout=2):
        if not self.interactive:
            try:return input('명령> ').strip().lower() or 'enter'
            except EOFError:return 'q'
        if os.name=='nt':
            import msvcrt
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                if msvcrt.kbhit():
                    key=msvcrt.getwch()
                    if key in ('\x00','\xe0'):
                        return {'H':'up','P':'down','K':'left','M':'right','I':'pageup','Q':'pagedown'}.get(msvcrt.getwch(),'')
                    return {'\r':'enter','\x03':'q','\x1b':'q'}.get(key,key.lower())
                time.sleep(.03)
            return ''
        import termios
        import tty
        descriptor=sys.stdin.fileno();previous=termios.tcgetattr(descriptor)
        try:
            # 화면 표시 직후 들어온 키를 버리지 않는다. 기본 TCSAFLUSH는 입력을 지울 수 있다.
            tty.setcbreak(descriptor,termios.TCSANOW)
            if not select.select([descriptor],[],[],timeout)[0]:return ''
            first=os.read(descriptor,1)
            if first==b'\x1b':
                sequence=first
                while select.select([descriptor],[],[],.03)[0] and len(sequence)<8:
                    sequence+=os.read(descriptor,1)
                return {b'\x1b[A':'up',b'\x1b[B':'down',b'\x1b[C':'right',b'\x1b[D':'left',
                        b'\x1b[5~':'pageup',b'\x1b[6~':'pagedown',b'\x1b':'q'}.get(sequence,'')
            return {b'\n':'enter',b'\r':'enter',b'\x03':'q'}.get(first,first.decode('utf-8',errors='ignore').lower())
        finally:
            termios.tcsetattr(descriptor,termios.TCSADRAIN,previous)


def run(model=None,terminal=None):
    model=model or WatchlistModel()
    tab=0;selected=0;message=''
    with (terminal or Terminal()) as screen:
        while True:
            try:
                snapshot=model.snapshot(include_history=tab==2)
            except (ValueError,OSError,KeyError,TypeError):
                screen.draw('관찰 목록 자료를 읽지 못했습니다. 설정·파일 상태를 확인하세요. r 재시도 / q 종료\n기존 파일과 계좌는 수정하지 않았습니다.')
                if screen.key()=='q':break
                continue
            rows=table_rows(snapshot,tab)
            selected=max(0,min(selected,len(rows)-1))
            size=shutil.get_terminal_size((100,30))
            screen.draw(render(snapshot,tab,selected,message,size.columns,size.lines))
            key=screen.key()
            if key=='q':break
            if key in {'1','2','3','4','5'}:tab=int(key)-1;selected=0;message='';continue
            if key in {'left','right'}:tab=(tab+(-1 if key=='left' else 1))%5;selected=0;continue
            if key in {'up','k'}:selected=max(0,selected-1);continue
            if key in {'down','j'}:selected=min(len(rows)-1,selected+1);continue
            if key in {'n','pagedown','p','pageup'}:
                selected=max(0,min(len(rows)-1,selected+max(3,size.lines-14)*(1 if key in {'n','pagedown'} else -1)));continue
            if key=='r':
                if hasattr(screen,'invalidate'):screen.invalidate()
                continue
            if key=='':continue
            try:
                if key=='a':
                    value=screen.prompt('추가할 미국 주식 티커 (Enter 취소): ').strip()
                    if value:message=model.add_user(value,snapshot['settings_hash'])
                elif key=='d':
                    if tab!=0 or not rows:
                        message='사용자 지정 탭에서 삭제할 종목을 선택하세요. 자동 목록은 일별 조건으로 제외됩니다.'
                    else:
                        ticker=rows[selected][0]
                        confirmation=screen.prompt(ticker+' 사용자 목록에서 삭제? 자동 선정·보유 관리는 남을 수 있습니다. (y/N): ')
                        if confirmation.lower()=='y':message=model.remove_user(ticker,snapshot['settings_hash'])
                elif key=='t':
                    if screen.prompt('자동 선정 설정을 전환해 저장할까요? 실행 프로그램은 재시작하지 않습니다. (y/N): ').lower()=='y':
                        message=model.toggle(snapshot['policy_hash'])
                elif key=='e':
                    if tab!=4:message='선정 조건 탭에서 수정할 항목을 선택하세요.'
                    else:
                        field,label,unit,integer=POLICY_FIELDS[selected]
                        value=screen.prompt(label+' 새 값 ('+unit+', Enter 취소): ').strip()
                        if value:message=model.edit_condition(field,value,snapshot['policy_hash'])
                elif key=='enter' and rows:
                    screen.prompt(' | '.join(safe_text(value) for value in rows[selected])+'\nEnter로 돌아가기: ')
                else:message='표시된 명령 키를 사용하세요.'
            except ValueError as error:
                message=safe_text(error)
            except (OSError,RuntimeError,KeyError,TypeError):
                message='파일/검증 오류로 저장하지 못했습니다. 새로고침해 현재 설정을 확인하세요.'
    return 0


def stop_tui(*unused):
    """종료 신호도 정상 예외 경로를 지나 커서·입력 모드가 복원되게 한다."""
    raise KeyboardInterrupt()


def main():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='replace')
    previous=signal.signal(signal.SIGTERM,stop_tui)
    try:
        return run()
    except (KeyboardInterrupt,EOFError):
        return 0
    finally:
        signal.signal(signal.SIGTERM,previous)


if __name__=='__main__':
    raise SystemExit(main())
