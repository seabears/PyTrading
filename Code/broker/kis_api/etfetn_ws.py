"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
from .schemas import websocket_columns
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def etf_nav_trend(tr_type, tr_key):
    """KIS etfetn_ws.etf_nav_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 문자열
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 수신된 메시지 데이터
columns (list[str]): 수신된 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    tr_id = 'H0STNAV0'
    params = {'tr_key': tr_key}
    columns = ['rt_cd', 'msg_cd', 'output1', 'msg1', 'mksc_shrn_iscd', 'nav', 'nav_prdy_vrss_sign', 'nav_prdy_vrss', 'nav_prdy_ctrt', 'oprc_nav', 'hprc_nav', 'lprc_nav']
    columns = websocket_columns(tr_id, columns)
    return Subscription('etfetn_ws.etf_nav_trend', tr_id, tr_type, params, tuple(columns), 'real')
