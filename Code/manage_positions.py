"""수동 편입 메뉴. 번호 선택 후 신청만 저장하며 실제 주문은 전송하지 않는다."""
import json
from pathlib import Path

from paths import DATA_ROOT
from trading.execution import load_execution
from trading.adoption_requests import list_positions,list_requests,request_adoption

LABELS={
    'CLOSED':'청산 완료',
    'MANAGED':'이미 자동 관리 중','OTHER_MANAGER':'다른 관리자 보유',
    'FILL_REVIEW_REQUIRED':'전량 체결 확인 필요','ACTIVE_ORDER_REVIEW_REQUIRED':'미체결 주문 확인 필요',
    'ALLOCATION_REVIEW_REQUIRED':'잔여 수량 배분 확인 필요',
    'REQUESTABLE_REQUIRES_REMOTE_CHECK':'편입 신청 가능(실제 계좌 대조는 처리 시 수행)',
}


def current_context():
    """실행 중인 프로필이 있으면 재사용하고, 없으면 현재 선택된 모의 설정을 쓴다."""
    metadata=DATA_ROOT/'operations/strategy-session-latest.json'
    if metadata.exists():
        value=json.loads(metadata.read_text(encoding='utf-8'))
        selection=load_execution(Path(value['execution_config']))
        target=Path(value['account_folder'])/'account.json'
    else:
        selection=load_execution()
        target=DATA_ROOT/'execution-accounts/kis_demo/paper-daily-frozen/account.json'
    if selection['mode']!='kis_demo':
        raise ValueError('adoption_demo_selection_required')
    return DATA_ROOT/'execution/kis_demo/strategy-orders.sqlite',target,selection


def main():
    try:
        journal,target,selection=current_context()
        rows=list_positions(journal,target)
        print('KIS 모의 보유 수동 편입 — 이 메뉴는 매수·매도·취소를 전송하지 않습니다.')
        for index,row in enumerate(rows,1):
            print(f"{index}: {row['symbol']} / 원매수 {row['filled_quantity']}주 / 평균 {row['average_fill_price']} USD / {LABELS[row['status']]}")
        if not rows:print('원장에 편입 대상으로 표시할 체결이 없습니다.')
        requests=list_requests()
        if requests:
            print('편입 신청 상태:')
            for row in requests:
                print(f"  {row.get('symbol')} {row.get('quantity')}주: {row.get('status')} / {row.get('last_reason','처리 대기')}")
        print('0: 종료')
        answer=input('편입할 번호: ').strip()
        if answer in {'','0'}:return 0
        if not answer.isdigit() or not 1<=int(answer)<=len(rows):
            print('잘못된 번호입니다. 변경하지 않았습니다.');return 1
        row=rows[int(answer)-1]
        if row['status']!='REQUESTABLE_REQUIRES_REMOTE_CHECK':
            print(LABELS[row['status']]+'. 변경하지 않았습니다.');return 1
        print(f"{row['symbol']}의 확인된 전량 보유를 기존 일봉 전략에 연결합니다. 이후 매도 조건 충족 시 모의 매도될 수 있습니다.")
        if input('신청하려면 편입 입력: ').strip()!='편입':
            print('취소했습니다.');return 0
        requested=request_adoption(journal,target,selection,row['order_id'])
        print('신청 저장: '+requested['request_id']+' / '+requested['status'])
        print('실행 중인 일봉 전략이 다음 해당 종목 정규장 관측에서 검증 후 처리합니다. 같은 메뉴에서 결과를 확인하세요.')
        return 0
    except (EOFError,KeyboardInterrupt):
        print('신청하지 않고 종료했습니다.');return 0
    except (OSError,ValueError,KeyError,TypeError):
        print('편입 메뉴를 열 수 없습니다. 모의 모드·실행 계좌·주문 원장·파일 권한을 확인하세요.');return 1


if __name__=='__main__':raise SystemExit(main())
