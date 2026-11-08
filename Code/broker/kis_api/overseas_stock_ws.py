"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
from .schemas import websocket_columns
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def asking_price(tr_type, tr_key):
    """KIS overseas_stock_ws.asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'HDFSASP0'
    params = {'tr_key': tr_key}
    columns = ['symb', 'zdiv', 'xymd', 'xhms', 'kymd', 'khms', 'bvol', 'avol', 'bdvl', 'advl', 'pbid1', 'pask1', 'vbid1', 'vask1', 'dbid1', 'dask1']
    columns = websocket_columns(tr_id, columns)
    return Subscription('overseas_stock_ws.asking_price', tr_id, tr_type, params, tuple(columns), 'real')

def ccnl_notice(tr_type, tr_key, env_dv):
    """KIS overseas_stock_ws.ccnl_notice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real', 'demo')")
    if env_dv == 'real':
        tr_id = 'H0GSCNI0'
    elif env_dv == 'demo':
        tr_id = 'H0GSCNI9'
    else:
        raise ValueError('env_dv can only be real or demo')
    params = {'tr_key': tr_key}
    columns = ['CUST_ID', 'ACNT_NO', 'ODER_NO', 'OODER_NO', 'SELN_BYOV_CLS', 'RCTF_CLS', 'ODER_KIND2', 'STCK_SHRN_ISCD', 'CNTG_QTY', 'CNTG_UNPR', 'STCK_CNTG_HOUR', 'RFUS_YN', 'CNTG_YN', 'ACPT_YN', 'BRNC_NO', 'ODER_QTY', 'ACNT_NAME', 'CNTG_ISNM', 'ODER_COND', 'DEBT_GB', 'DEBT_DATE', 'START_TM', 'END_TM', 'TM_DIV_TP', 'CNTG_UNPR12']
    columns = websocket_columns(tr_id, columns)
    return Subscription('overseas_stock_ws.ccnl_notice', tr_id, tr_type, params, tuple(columns), env_dv)

def delayed_asking_price_asia(tr_type, tr_key):
    """KIS overseas_stock_ws.delayed_asking_price_asia 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'HDFSASP1'
    params = {'tr_key': tr_key}
    columns = ['symb', 'zdiv', 'xymd', 'xhms', 'kymd', 'khms', 'bvol', 'avol', 'bdvl', 'advl', 'pbid1', 'pask1', 'vbid1', 'vask1', 'dbid1', 'dask1']
    columns = websocket_columns(tr_id, columns)
    return Subscription('overseas_stock_ws.delayed_asking_price_asia', tr_id, tr_type, params, tuple(columns), 'real')

def delayed_ccnl(tr_type, tr_key):
    """KIS overseas_stock_ws.delayed_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'HDFSCNT0'
    params = {'tr_key': tr_key}
    columns = ['SYMB', 'ZDIV', 'TYMD', 'XYMD', 'XHMS', 'KYMD', 'KHMS', 'OPEN', 'HIGH', 'LOW', 'LAST', 'SIGN', 'DIFF', 'RATE', 'PBID', 'PASK', 'VBID', 'VASK', 'EVOL', 'TVOL', 'TAMT', 'BIVL', 'ASVL', 'STRN', 'MTYP']
    columns = websocket_columns(tr_id, columns)
    return Subscription('overseas_stock_ws.delayed_ccnl', tr_id, tr_type, params, tuple(columns), 'real')
