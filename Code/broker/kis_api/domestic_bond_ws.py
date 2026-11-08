"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
from .schemas import websocket_columns
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def bond_asking_price(tr_type, tr_key):
    """KIS domestic_bond_ws.bond_asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타냅니다.
tr_key (str): [필수] 종목코드. 빈 문자열일 수 없습니다.
message (dict): 실시간 데이터 메시지.
columns (list[str]): 응답 데이터의 컬럼 정보."""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    tr_id = 'H0BJASP0'
    params = {'tr_key': tr_key}
    columns = ['stnd_iscd', 'stck_cntg_hour', 'askp_ert1', 'bidp_ert1', 'askp1', 'bidp1', 'askp_rsqn1', 'bidp_rsqn1', 'askp_ert2', 'bidp_ert2', 'askp2', 'bidp2', 'askp_rsqn2', 'bidp_rsqn2', 'askp_ert3', 'bidp_ert3', 'askp3', 'bidp3', 'askp_rsqn3', 'bidp_rsqn3', 'askp_ert4', 'bidp_ert4', 'askp4', 'bidp4', 'askp_rsqn4', 'bidp_rsqn4', 'askp_ert5', 'bidp_ert5', 'askp5', 'bidp5', 'askp_rsqn52', 'bidp_rsqn53', 'total_askp_rsqn', 'total_bidp_rsqn']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_bond_ws.bond_asking_price', tr_id, tr_type, params, tuple(columns), 'real')

def bond_ccnl(tr_type, tr_key):
    """KIS domestic_bond_ws.bond_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 실시간 데이터 구독 결과 메시지
columns (list[str]): 응답 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 빈 문자열일 수 없습니다.')
    tr_id = 'H0BJCNT0'
    params = {'tr_key': tr_key}
    columns = ['stnd_iscd', 'bond_isnm', 'stck_cntg_hour', 'prdy_vrss_sign', 'prdy_vrss', 'prdy_ctrt', 'stck_prpr', 'cntg_vol', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'stck_prdy_clpr', 'bond_cntg_ert', 'oprc_ert', 'hgpr_ert', 'lwpr_ert', 'acml_vol', 'prdy_vol', 'cntg_type_cls_code']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_bond_ws.bond_ccnl', tr_id, tr_type, params, tuple(columns), 'real')

def bond_index_ccnl(tr_type, tr_key):
    """KIS domestic_bond_ws.bond_index_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타냅니다.
tr_key (str): [필수] 구독할 종목코드. 빈 문자열이 아니어야 합니다.
message (dict): 구독 요청에 대한 응답 메시지.
columns (list[str]): 실시간 데이터의 컬럼 정보."""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    tr_id = 'H0BICNT0'
    params = {'tr_key': tr_key}
    columns = ['nmix_id', 'stnd_date1', 'trnm_hour', 'totl_ernn_nmix_oprc', 'totl_ernn_nmix_hgpr', 'totl_ernn_nmix_lwpr', 'totl_ernn_nmix', 'prdy_totl_ernn_nmix', 'totl_ernn_nmix_prdy_vrss', 'totl_ernn_nmix_prdy_vrss_sign', 'totl_ernn_nmix_prdy_ctrt', 'clen_prc_nmix', 'mrkt_prc_nmix', 'bond_call_rnvs_nmix', 'bond_zero_rnvs_nmix', 'bond_futs_thpr', 'bond_avrg_drtn_val', 'bond_avrg_cnvx_val', 'bond_avrg_ytm_val', 'bond_avrg_frdl_ytm_val']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_bond_ws.bond_index_ccnl', tr_id, tr_type, params, tuple(columns), 'real')
