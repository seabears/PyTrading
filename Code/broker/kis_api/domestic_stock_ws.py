"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
from .schemas import websocket_columns
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def asking_price_krx(tr_type, tr_key, env_dv='real'):
    """KIS domestic_stock_ws.asking_price_krx 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
env_dv (str): 실전모의구분 (real: 실전, demo: 모의)
message (dict): 실시간 데이터 구독에 대한 메시지 데이터
columns (list[str]): 실시간 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다.')
    if env_dv == 'real':
        tr_id = 'H0STASP0'
    elif env_dv == 'demo':
        tr_id = 'H0STASP0'
    else:
        raise ValueError("env_dv는 'real' 또는 'demo'만 가능합니다.")
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'BSOP_HOUR', 'HOUR_CLS_CODE', 'ASKP1', 'ASKP2', 'ASKP3', 'ASKP4', 'ASKP5', 'ASKP6', 'ASKP7', 'ASKP8', 'ASKP9', 'ASKP10', 'BIDP1', 'BIDP2', 'BIDP3', 'BIDP4', 'BIDP5', 'BIDP6', 'BIDP7', 'BIDP8', 'BIDP9', 'BIDP10', 'ASKP_RSQN1', 'ASKP_RSQN2', 'ASKP_RSQN3', 'ASKP_RSQN4', 'ASKP_RSQN5', 'ASKP_RSQN6', 'ASKP_RSQN7', 'ASKP_RSQN8', 'ASKP_RSQN9', 'ASKP_RSQN10', 'BIDP_RSQN1', 'BIDP_RSQN2', 'BIDP_RSQN3', 'BIDP_RSQN4', 'BIDP_RSQN5', 'BIDP_RSQN6', 'BIDP_RSQN7', 'BIDP_RSQN8', 'BIDP_RSQN9', 'BIDP_RSQN10', 'TOTAL_ASKP_RSQN', 'TOTAL_BIDP_RSQN', 'OVTM_TOTAL_ASKP_RSQN', 'OVTM_TOTAL_BIDP_RSQN', 'ANTC_CNPR', 'ANTC_CNQN', 'ANTC_VOL', 'ANTC_CNTG_VRSS', 'ANTC_CNTG_VRSS_SIGN', 'ANTC_CNTG_PRDY_CTRT', 'ACML_VOL', 'TOTAL_ASKP_RSQN_ICDC', 'TOTAL_BIDP_RSQN_ICDC', 'OVTM_TOTAL_ASKP_ICDC', 'OVTM_TOTAL_BIDP_ICDC', 'STCK_DEAL_CLS_CODE', 'MID_PRC', 'MIDP_TOTAL_RSQN', 'MIDP_CLS_CODE', 'MARKET_CLS_CODE']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.asking_price_krx', tr_id, tr_type, params, tuple(columns), env_dv)

def asking_price_nxt(tr_type, tr_key):
    """KIS domestic_stock_ws.asking_price_nxt 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 실시간 데이터 메시지
columns (list[str]): 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 빈 문자열일 수 없습니다.')
    tr_id = 'H0NXASP0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'BSOP_HOUR', 'HOUR_CLS_CODE', 'ASKP1', 'ASKP2', 'ASKP3', 'ASKP4', 'ASKP5', 'ASKP6', 'ASKP7', 'ASKP8', 'ASKP9', 'ASKP10', 'BIDP1', 'BIDP2', 'BIDP3', 'BIDP4', 'BIDP5', 'BIDP6', 'BIDP7', 'BIDP8', 'BIDP9', 'BIDP10', 'ASKP_RSQN1', 'ASKP_RSQN2', 'ASKP_RSQN3', 'ASKP_RSQN4', 'ASKP_RSQN5', 'ASKP_RSQN6', 'ASKP_RSQN7', 'ASKP_RSQN8', 'ASKP_RSQN9', 'ASKP_RSQN10', 'BIDP_RSQN1', 'BIDP_RSQN2', 'BIDP_RSQN3', 'BIDP_RSQN4', 'BIDP_RSQN5', 'BIDP_RSQN6', 'BIDP_RSQN7', 'BIDP_RSQN8', 'BIDP_RSQN9', 'BIDP_RSQN10', 'TOTAL_ASKP_RSQN', 'TOTAL_BIDP_RSQN', 'OVTM_TOTAL_ASKP_RSQN', 'OVTM_TOTAL_BIDP_RSQN', 'ANTC_CNPR', 'ANTC_CNQN', 'ANTC_VOL', 'ANTC_CNTG_VRSS', 'ANTC_CNTG_VRSS_SIGN', 'ANTC_CNTG_PRDY_CTRT', 'ACML_VOL', 'TOTAL_ASKP_RSQN_ICDC', 'TOTAL_BIDP_RSQN_ICDC', 'OVTM_TOTAL_ASKP_ICDC', 'OVTM_TOTAL_BIDP_ICDC', 'STCK_DEAL_CLS_CODE', 'KMID_PRC', 'KMID_TOTAL_RSQN', 'KMID_CLS_CODE', 'NMID_PRC', 'NMID_TOTAL_RSQN', 'NMID_CLS_CODE']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.asking_price_nxt', tr_id, tr_type, params, tuple(columns), 'real')

def asking_price_total(tr_type, tr_key):
    """KIS domestic_stock_ws.asking_price_total 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 실시간 데이터 메시지
columns (list[str]): 응답 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 빈 문자열일 수 없습니다.')
    tr_id = 'H0UNASP0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'BSOP_HOUR', 'HOUR_CLS_CODE', 'ASKP1', 'ASKP2', 'ASKP3', 'ASKP4', 'ASKP5', 'ASKP6', 'ASKP7', 'ASKP8', 'ASKP9', 'ASKP10', 'BIDP1', 'BIDP2', 'BIDP3', 'BIDP4', 'BIDP5', 'BIDP6', 'BIDP7', 'BIDP8', 'BIDP9', 'BIDP10', 'ASKP_RSQN1', 'ASKP_RSQN2', 'ASKP_RSQN3', 'ASKP_RSQN4', 'ASKP_RSQN5', 'ASKP_RSQN6', 'ASKP_RSQN7', 'ASKP_RSQN8', 'ASKP_RSQN9', 'ASKP_RSQN10', 'BIDP_RSQN1', 'BIDP_RSQN2', 'BIDP_RSQN3', 'BIDP_RSQN4', 'BIDP_RSQN5', 'BIDP_RSQN6', 'BIDP_RSQN7', 'BIDP_RSQN8', 'BIDP_RSQN9', 'BIDP_RSQN10', 'TOTAL_ASKP_RSQN', 'TOTAL_BIDP_RSQN', 'OVTM_TOTAL_ASKP_RSQN', 'OVTM_TOTAL_BIDP_RSQN', 'ANTC_CNPR', 'ANTC_CNQN', 'ANTC_VOL', 'ANTC_CNTG_VRSS', 'ANTC_CNTG_VRSS_SIGN', 'ANTC_CNTG_PRDY_CTRT', 'ACML_VOL', 'TOTAL_ASKP_RSQN_ICDC', 'TOTAL_BIDP_RSQN_ICDC', 'OVTM_TOTAL_ASKP_ICDC', 'OVTM_TOTAL_BIDP_ICDC', 'STCK_DEAL_CLS_CODE', 'KMID_PRC', 'KMID_TOTAL_RSQN', 'KMID_CLS_CODE', 'NMID_PRC', 'NMID_TOTAL_RSQN', 'NMID_CLS_CODE', 'ANTC_EXCH_CLS_CODE']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.asking_price_total', tr_id, tr_type, params, tuple(columns), 'real')

def ccnl_krx(tr_type, tr_key, env_dv='real'):
    """KIS domestic_stock_ws.ccnl_krx 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
env_dv (str): 실전모의구분 (real:실전, demo:모의)
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    if env_dv == 'real':
        tr_id = 'H0STCNT0'
    elif env_dv == 'demo':
        tr_id = 'H0STCNT0'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'STCK_CNTG_HOUR', 'STCK_PRPR', 'PRDY_VRSS_SIGN', 'PRDY_VRSS', 'PRDY_CTRT', 'WGHN_AVRG_STCK_PRC', 'STCK_OPRC', 'STCK_HGPR', 'STCK_LWPR', 'ASKP1', 'BIDP1', 'CNTG_VOL', 'ACML_VOL', 'ACML_TR_PBMN', 'SELN_CNTG_CSNU', 'SHNU_CNTG_CSNU', 'NTBY_CNTG_CSNU', 'CTTR', 'SELN_CNTG_SMTN', 'SHNU_CNTG_SMTN', 'CCLD_DVSN', 'SHNU_RATE', 'PRDY_VOL_VRSS_ACML_VOL_RATE', 'OPRC_HOUR', 'OPRC_VRSS_PRPR_SIGN', 'OPRC_VRSS_PRPR', 'HGPR_HOUR', 'HGPR_VRSS_PRPR_SIGN', 'HGPR_VRSS_PRPR', 'LWPR_HOUR', 'LWPR_VRSS_PRPR_SIGN', 'LWPR_VRSS_PRPR', 'BSOP_DATE', 'NEW_MKOP_CLS_CODE', 'TRHT_YN', 'ASKP_RSQN1', 'BIDP_RSQN1', 'TOTAL_ASKP_RSQN', 'TOTAL_BIDP_RSQN', 'VOL_TNRT', 'PRDY_SMNS_HOUR_ACML_VOL', 'PRDY_SMNS_HOUR_ACML_VOL_RATE', 'HOUR_CLS_CODE', 'MRKT_TRTM_CLS_CODE', 'VI_STND_PRC', 'MARKET_CLS_CODE']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.ccnl_krx', tr_id, tr_type, params, tuple(columns), env_dv)

def ccnl_notice(tr_type, tr_key, env_dv='real'):
    """KIS domestic_stock_ws.ccnl_notice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1")/해제("0") 여부
tr_key (str): [필수] 종목코드 (예: "005930")
env_dv (str): 실전모의구분 (real:실전, demo:모의)
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다.')
    if env_dv == 'real':
        tr_id = 'H0STCNI0'
    elif env_dv == 'demo':
        tr_id = 'H0STCNI9'
    else:
        raise ValueError("env_dv는 'real' 또는 'demo'만 가능합니다.")
    params = {'tr_key': tr_key}
    columns = ['CUST_ID', 'ACNT_NO', 'ODER_NO', 'OODER_NO', 'SELN_BYOV_CLS', 'RCTF_CLS', 'ODER_KIND', 'ODER_COND', 'STCK_SHRN_ISCD', 'CNTG_QTY', 'CNTG_UNPR', 'STCK_CNTG_HOUR', 'RFUS_YN', 'CNTG_YN', 'ACPT_YN', 'BRNC_NO', 'ODER_QTY', 'ACNT_NAME', 'ORD_COND_PRC', 'ORD_EXG_GB', 'POPUP_YN', 'FILLER', 'CRDT_CLS', 'CRDT_LOAN_DATE', 'CNTG_ISNM40', 'ODER_PRC']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.ccnl_notice', tr_id, tr_type, params, tuple(columns), env_dv)

def ccnl_nxt(tr_type, tr_key):
    """KIS domestic_stock_ws.ccnl_nxt 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 실시간 체결가 데이터 메시지
columns (list[str]): 데이터의 컬럼 정보 리스트"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다. 유효한 종목코드를 입력하세요.')
    tr_id = 'H0NXCNT0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'STCK_CNTG_HOUR', 'STCK_PRPR', 'PRDY_VRSS_SIGN', 'PRDY_VRSS', 'PRDY_CTRT', 'WGHN_AVRG_STCK_PRC', 'STCK_OPRC', 'STCK_HGPR', 'STCK_LWPR', 'ASKP1', 'BIDP1', 'CNTG_VOL', 'ACML_VOL', 'ACML_TR_PBMN', 'SELN_CNTG_CSNU', 'SHNU_CNTG_CSNU', 'NTBY_CNTG_CSNU', 'CTTR', 'SELN_CNTG_SMTN', 'SHNU_CNTG_SMTN', 'CNTG_CLS_CODE', 'SHNU_RATE', 'PRDY_VOL_VRSS_ACML_VOL_RATE', 'OPRC_HOUR', 'OPRC_VRSS_PRPR_SIGN', 'OPRC_VRSS_PRPR', 'HGPR_HOUR', 'HGPR_VRSS_PRPR_SIGN', 'HGPR_VRSS_PRPR', 'LWPR_HOUR', 'LWPR_VRSS_PRPR_SIGN', 'LWPR_VRSS_PRPR', 'BSOP_DATE', 'NEW_MKOP_CLS_CODE', 'TRHT_YN', 'ASKP_RSQN1', 'BIDP_RSQN1', 'TOTAL_ASKP_RSQN', 'TOTAL_BIDP_RSQN', 'VOL_TNRT', 'PRDY_SMNS_HOUR_ACML_VOL', 'PRDY_SMNS_HOUR_ACML_VOL_RATE', 'HOUR_CLS_CODE', 'MRKT_TRTM_CLS_CODE', 'VI_STND_PRC', 'MARKET_CLS_CODE']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.ccnl_nxt', tr_id, tr_type, params, tuple(columns), 'real')

def ccnl_total(tr_type, tr_key):
    """KIS domestic_stock_ws.ccnl_total 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드, 실시간 데이터를 구독할 주식의 종목코드
message (dict): 실시간 체결가 데이터 메시지
columns (list[str]): 데이터의 컬럼 정보 리스트"""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    tr_id = 'H0UNCNT0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'STCK_CNTG_HOUR', 'STCK_PRPR', 'PRDY_VRSS_SIGN', 'PRDY_VRSS', 'PRDY_CTRT', 'WGHN_AVRG_STCK_PRC', 'STCK_OPRC', 'STCK_HGPR', 'STCK_LWPR', 'ASKP1', 'BIDP1', 'CNTG_VOL', 'ACML_VOL', 'ACML_TR_PBMN', 'SELN_CNTG_CSNU', 'SHNU_CNTG_CSNU', 'NTBY_CNTG_CSNU', 'CTTR', 'SELN_CNTG_SMTN', 'SHNU_CNTG_SMTN', 'CNTG_CLS_CODE', 'SHNU_RATE', 'PRDY_VOL_VRSS_ACML_VOL_RATE', 'OPRC_HOUR', 'OPRC_VRSS_PRPR_SIGN', 'OPRC_VRSS_PRPR', 'HGPR_HOUR', 'HGPR_VRSS_PRPR_SIGN', 'HGPR_VRSS_PRPR', 'LWPR_HOUR', 'LWPR_VRSS_PRPR_SIGN', 'LWPR_VRSS_PRPR', 'BSOP_DATE', 'NEW_MKOP_CLS_CODE', 'TRHT_YN', 'ASKP_RSQN1', 'BIDP_RSQN1', 'TOTAL_ASKP_RSQN', 'TOTAL_BIDP_RSQN', 'VOL_TNRT', 'PRDY_SMNS_HOUR_ACML_VOL', 'PRDY_SMNS_HOUR_ACML_VOL_RATE', 'HOUR_CLS_CODE', 'MRKT_TRTM_CLS_CODE', 'VI_STND_PRC', 'MARKET_CLS_CODE']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.ccnl_total', tr_id, tr_type, params, tuple(columns), 'real')

def exp_ccnl_krx(tr_type, tr_key):
    """KIS domestic_stock_ws.exp_ccnl_krx 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타냅니다.
tr_key (str): [필수] 종목코드. 빈 문자열이 아니어야 하며, 유효한 종목코드 형식이어야 합니다.
message (dict): 실시간 데이터 구독에 대한 메시지 데이터.
columns (list[str]): 실시간 데이터의 컬럼 정보."""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    tr_id = 'H0STANC0'
    params = {'tr_key': tr_key}
    columns = ['mksc_shrn_iscd', 'stck_cntg_hour', 'stck_prpr', 'prdy_vrss_sign', 'prdy_vrss', 'prdy_ctrt', 'wghn_avrg_stck_prc', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'askp1', 'bidp1', 'cntg_vol', 'acml_vol', 'acml_tr_pbmn', 'seln_cntg_csnu', 'shnu_cntg_csnu', 'ntby_cntg_csnu', 'cttr', 'seln_cntg_smtn', 'shnu_cntg_smtn', 'cntg_cls_code', 'shnu_rate', 'prdy_vol_vrss_acml_vol_rate', 'oprc_hour', 'oprc_vrss_prpr_sign', 'oprc_vrss_prpr', 'hgpr_hour', 'hgpr_vrss_prpr_sign', 'hgpr_vrss_prpr', 'lwpr_hour', 'lwpr_vrss_prpr_sign', 'lwpr_vrss_prpr', 'bsop_date', 'new_mkop_cls_code', 'trht_yn', 'askp_rsqn1', 'bidp_rsqn1', 'total_askp_rsqn', 'total_bidp_rsqn', 'vol_tnrt', 'prdy_smns_hour_acml_vol', 'prdy_smns_hour_acml_vol_rate', 'hour_cls_code', 'mrkt_trtm_cls_code']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.exp_ccnl_krx', tr_id, tr_type, params, tuple(columns), 'real')

def exp_ccnl_nxt(tr_type, tr_key):
    """KIS domestic_stock_ws.exp_ccnl_nxt 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 실시간 데이터 메시지
columns (list[str]): 응답 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    tr_id = 'H0NXANC0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'STCK_CNTG_HOUR', 'STCK_PRPR', 'PRDY_VRSS_SIGN', 'PRDY_VRSS', 'PRDY_CTRT', 'WGHN_AVRG_STCK_PRC', 'STCK_OPRC', 'STCK_HGPR', 'STCK_LWPR', 'ASKP1', 'BIDP1', 'CNTG_VOL', 'ACML_VOL', 'ACML_TR_PBMN', 'SELN_CNTG_CSNU', 'SHNU_CNTG_CSNU', 'NTBY_CNTG_CSNU', 'CTTR', 'SELN_CNTG_SMTN', 'SHNU_CNTG_SMTN', 'CNTG_CLS_CODE', 'SHNU_RATE', 'PRDY_VOL_VRSS_ACML_VOL_RATE', 'OPRC_HOUR', 'OPRC_VRSS_PRPR_SIGN', 'OPRC_VRSS_PRPR', 'HGPR_HOUR', 'HGPR_VRSS_PRPR_SIGN', 'HGPR_VRSS_PRPR', 'LWPR_HOUR', 'LWPR_VRSS_PRPR_SIGN', 'LWPR_VRSS_PRPR', 'BSOP_DATE', 'NEW_MKOP_CLS_CODE', 'TRHT_YN', 'ASKP_RSQN1', 'BIDP_RSQN1', 'TOTAL_ASKP_RSQN', 'TOTAL_BIDP_RSQN', 'VOL_TNRT', 'PRDY_SMNS_HOUR_ACML_VOL', 'PRDY_SMNS_HOUR_ACML_VOL_RATE', 'HOUR_CLS_CODE', 'MRKT_TRTM_CLS_CODE', 'VI_STND_PRC']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.exp_ccnl_nxt', tr_id, tr_type, params, tuple(columns), 'real')

def exp_ccnl_total(tr_type, tr_key):
    """KIS domestic_stock_ws.exp_ccnl_total 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 실시간 데이터 메시지
columns (list[str]): 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다. 빈 문자열을 사용할 수 없습니다.')
    tr_id = 'H0UNANC0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'STCK_CNTG_HOUR', 'STCK_PRPR', 'PRDY_VRSS_SIGN', 'PRDY_VRSS', 'PRDY_CTRT', 'WGHN_AVRG_STCK_PRC', 'STCK_OPRC', 'STCK_HGPR', 'STCK_LWPR', 'ASKP1', 'BIDP1', 'CNTG_VOL', 'ACML_VOL', 'ACML_TR_PBMN', 'SELN_CNTG_CSNU', 'SHNU_CNTG_CSNU', 'NTBY_CNTG_CSNU', 'CTTR', 'SELN_CNTG_SMTN', 'SHNU_CNTG_SMTN', 'CNTG_CLS_CODE', 'SHNU_RATE', 'PRDY_VOL_VRSS_ACML_VOL_RATE', 'OPRC_HOUR', 'OPRC_VRSS_PRPR_SIGN', 'OPRC_VRSS_PRPR', 'HGPR_HOUR', 'HGPR_VRSS_PRPR_SIGN', 'HGPR_VRSS_PRPR', 'LWPR_HOUR', 'LWPR_VRSS_PRPR_SIGN', 'LWPR_VRSS_PRPR', 'BSOP_DATE', 'NEW_MKOP_CLS_CODE', 'TRHT_YN', 'ASKP_RSQN1', 'BIDP_RSQN1', 'TOTAL_ASKP_RSQN', 'TOTAL_BIDP_RSQN', 'VOL_TNRT', 'PRDY_SMNS_HOUR_ACML_VOL', 'PRDY_SMNS_HOUR_ACML_VOL_RATE', 'HOUR_CLS_CODE', 'MRKT_TRTM_CLS_CODE', 'VI_STND_PRC']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.exp_ccnl_total', tr_id, tr_type, params, tuple(columns), 'real')

def index_ccnl(tr_type, tr_key):
    """KIS domestic_stock_ws.index_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 메시지 데이터
columns (list[str]): 응답 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다.')
    tr_id = 'H0UPCNT0'
    params = {'tr_key': tr_key}
    columns = ['bstp_cls_code', 'bsop_hour', 'prpr_nmix', 'prdy_vrss_sign', 'bstp_nmix_prdy_vrss', 'acml_vol', 'acml_tr_pbmn', 'pcas_vol', 'pcas_tr_pbmn', 'prdy_ctrt', 'oprc_nmix', 'nmix_hgpr', 'nmix_lwpr', 'oprc_vrss_nmix_prpr', 'oprc_vrss_nmix_sign', 'hgpr_vrss_nmix_prpr', 'hgpr_vrss_nmix_sign', 'lwpr_vrss_nmix_prpr', 'lwpr_vrss_nmix_sign', 'prdy_clpr_vrss_oprc_rate', 'prdy_clpr_vrss_hgpr_rate', 'prdy_clpr_vrss_lwpr_rate', 'uplm_issu_cnt', 'ascn_issu_cnt', 'stnr_issu_cnt', 'down_issu_cnt', 'lslm_issu_cnt', 'qtqt_ascn_issu_cnt', 'qtqt_down_issu_cnt', 'tick_vrss']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.index_ccnl', tr_id, tr_type, params, tuple(columns), 'real')

def index_exp_ccnl(tr_type, tr_key):
    """KIS domestic_stock_ws.index_exp_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 문자열
tr_key (str): [필수] 종목코드를 나타내는 문자열. 빈 문자열일 수 없습니다.
message (dict): 실시간 데이터 구독에 대한 응답 메시지
columns (list[str]): 실시간 데이터의 컬럼 정보 리스트"""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    tr_id = 'H0UPANC0'
    params = {'tr_key': tr_key}
    columns = ['bstp_cls_code', 'bsop_hour', 'prpr_nmix', 'prdy_vrss_sign', 'bstp_nmix_prdy_vrss', 'acml_vol', 'acml_tr_pbmn', 'pcas_vol', 'pcas_tr_pbmn', 'prdy_ctrt', 'oprc_nmix', 'nmix_hgpr', 'nmix_lwpr', 'oprc_vrss_nmix_prpr', 'oprc_vrss_nmix_sign', 'hgpr_vrss_nmix_prpr', 'hgpr_vrss_nmix_sign', 'lwpr_vrss_nmix_prpr', 'lwpr_vrss_nmix_sign', 'prdy_clpr_vrss_oprc_rate', 'prdy_clpr_vrss_hgpr_rate', 'prdy_clpr_vrss_lwpr_rate', 'uplm_issu_cnt', 'ascn_issu_cnt', 'stnr_issu_cnt', 'down_issu_cnt', 'lslm_issu_cnt', 'qtqt_ascn_issu_cnt', 'qtqt_down_issu_cnt', 'tick_vrss']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.index_exp_ccnl', tr_id, tr_type, params, tuple(columns), 'real')

def index_program_trade(tr_type, tr_key):
    """KIS domestic_stock_ws.index_program_trade 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 문자열
tr_key (str): [필수] 종목코드를 나타내는 문자열. 빈 문자열일 수 없습니다.
message (dict): 웹소켓으로부터 수신된 메시지 데이터
columns (list[str]): 응답 데이터의 컬럼 정보 리스트"""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    tr_id = 'H0UPPGM0'
    params = {'tr_key': tr_key}
    columns = ['bstp_cls_code', 'bsop_hour', 'arbt_seln_entm_cnqn', 'arbt_seln_onsl_cnqn', 'arbt_shnu_entm_cnqn', 'arbt_shnu_onsl_cnqn', 'nabt_seln_entm_cnqn', 'nabt_seln_onsl_cnqn', 'nabt_shnu_entm_cnqn', 'nabt_shnu_onsl_cnqn', 'arbt_seln_entm_cntg_amt', 'arbt_seln_onsl_cntg_amt', 'arbt_shnu_entm_cntg_amt', 'arbt_shnu_onsl_cntg_amt', 'nabt_seln_entm_cntg_amt', 'nabt_seln_onsl_cntg_amt', 'nabt_shnu_entm_cntg_amt', 'nabt_shnu_onsl_cntg_amt', 'arbt_smtn_seln_vol', 'arbt_smtm_seln_vol_rate', 'arbt_smtn_seln_tr_pbmn', 'arbt_smtm_seln_tr_pbmn_rate', 'arbt_smtn_shnu_vol', 'arbt_smtm_shnu_vol_rate', 'arbt_smtn_shnu_tr_pbmn', 'arbt_smtm_shnu_tr_pbmn_rate', 'arbt_smtn_ntby_qty', 'arbt_smtm_ntby_qty_rate', 'arbt_smtn_ntby_tr_pbmn', 'arbt_smtm_ntby_tr_pbmn_rate', 'nabt_smtn_seln_vol', 'nabt_smtm_seln_vol_rate', 'nabt_smtn_seln_tr_pbmn', 'nabt_smtm_seln_tr_pbmn_rate', 'nabt_smtn_shnu_vol', 'nabt_smtm_shnu_vol_rate', 'nabt_smtn_shnu_tr_pbmn', 'nabt_smtm_shnu_tr_pbmn_rate', 'nabt_smtn_ntby_qty', 'nabt_smtm_ntby_qty_rate', 'nabt_smtn_ntby_tr_pbmn', 'nabt_smtm_ntby_tr_pbmn_rate', 'whol_entm_seln_vol', 'entm_seln_vol_rate', 'whol_entm_seln_tr_pbmn', 'entm_seln_tr_pbmn_rate', 'whol_entm_shnu_vol', 'entm_shnu_vol_rate', 'whol_entm_shnu_tr_pbmn', 'entm_shnu_tr_pbmn_rate', 'whol_entm_ntby_qt', 'entm_ntby_qty_rat', 'whol_entm_ntby_tr_pbmn', 'entm_ntby_tr_pbmn_rate', 'whol_onsl_seln_vol', 'onsl_seln_vol_rate', 'whol_onsl_seln_tr_pbmn', 'onsl_seln_tr_pbmn_rate', 'whol_onsl_shnu_vol', 'onsl_shnu_vol_rate', 'whol_onsl_shnu_tr_pbmn', 'onsl_shnu_tr_pbmn_rate', 'whol_onsl_ntby_qty', 'onsl_ntby_qty_rate', 'whol_onsl_ntby_tr_pbmn', 'onsl_ntby_tr_pbmn_rate', 'total_seln_qty', 'whol_seln_vol_rate', 'total_seln_tr_pbmn', 'whol_seln_tr_pbmn_rate', 'shnu_cntg_smtn', 'whol_shun_vol_rate', 'total_shnu_tr_pbmn', 'whol_shun_tr_pbmn_rate', 'whol_ntby_qty', 'whol_smtm_ntby_qty_rate', 'whol_ntby_tr_pbmn', 'whol_ntby_tr_pbmn_rate', 'arbt_entm_ntby_qty', 'arbt_entm_ntby_tr_pbmn', 'arbt_onsl_ntby_qty', 'arbt_onsl_ntby_tr_pbmn', 'nabt_entm_ntby_qty', 'nabt_entm_ntby_tr_pbmn', 'nabt_onsl_ntby_qty', 'nabt_onsl_ntby_tr_pbmn', 'acml_vol', 'acml_tr_pbmn']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.index_program_trade', tr_id, tr_type, params, tuple(columns), 'real')

def market_status_krx(tr_type, tr_key):
    """KIS domestic_stock_ws.market_status_krx 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 문자열
tr_key (str): [필수] 종목코드. 빈 문자열이 아니어야 하며, 유효한 종목코드 형식이어야 합니다.
message (dict): 서버로부터 수신된 메시지 데이터
columns (list[str]): 응답 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다.')
    tr_id = 'H0STMKO0'
    params = {'tr_key': tr_key}
    columns = ['mksc_shrn_iscd', 'trht_yn', 'tr_susp_reas_cntt', 'mkop_cls_code', 'antc_mkop_cls_code', 'mrkt_trtm_cls_code', 'divi_app_cls_code', 'iscd_stat_cls_code', 'vi_cls_code', 'ovtm_vi_cls_code', 'EXCH_CLS_CODE']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.market_status_krx', tr_id, tr_type, params, tuple(columns), 'real')

def market_status_nxt(tr_type, tr_key):
    """KIS domestic_stock_ws.market_status_nxt 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 실시간으로 수신된 메시지 데이터
columns (list[str]): 응답 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 빈 문자열일 수 없습니다.')
    tr_id = 'H0NXMKO0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'TRHT_YN', 'TR_SUSP_REAS_CNTT', 'MKOP_CLS_CODE', 'ANTC_MKOP_CLS_CODE', 'MRKT_TRTM_CLS_CODE', 'DIVI_APP_CLS_CODE', 'ISCD_STAT_CLS_CODE', 'VI_CLS_CODE', 'OVTM_VI_CLS_CODE', 'EXCH_CLS_CODE']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.market_status_nxt', tr_id, tr_type, params, tuple(columns), 'real')

def market_status_total(tr_type, tr_key):
    """KIS domestic_stock_ws.market_status_total 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드, 구독할 종목의 고유 코드
message (dict): 실시간으로 수신된 메시지 데이터
columns (list[str]): 수신된 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다.')
    tr_id = 'H0UNMKO0'
    params = {'tr_key': tr_key}
    columns = ['TRHT_YN', 'TR_SUSP_REAS_CNTT', 'MKOP_CLS_CODE', 'ANTC_MKOP_CLS_CODE', 'MRKT_TRTM_CLS_CODE', 'DIVI_APP_CLS_CODE', 'ISCD_STAT_CLS_CODE', 'VI_CLS_CODE', 'OVTM_VI_CLS_CODE', 'EXCH_CLS_CODE']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.market_status_total', tr_id, tr_type, params, tuple(columns), 'real')

def member_krx(tr_type, tr_key):
    """KIS domestic_stock_ws.member_krx 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 문자열
tr_key (str): [필수] 종목코드를 나타내는 문자열. 빈 문자열일 수 없습니다.
message (dict): 구독 요청에 대한 응답 메시지
columns (list[str]): 응답 데이터의 컬럼 정보 리스트"""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    tr_id = 'H0STMBC0'
    params = {'tr_key': tr_key}
    columns = ['mksc_shrn_iscd', 'seln2_mbcr_name1', 'seln2_mbcr_name2', 'seln2_mbcr_name3', 'seln2_mbcr_name4', 'seln2_mbcr_name5', 'byov_mbcr_name1', 'byov_mbcr_name2', 'byov_mbcr_name3', 'byov_mbcr_name4', 'byov_mbcr_name5', 'total_seln_qty1', 'total_seln_qty2', 'total_seln_qty3', 'total_seln_qty4', 'total_seln_qty5', 'total_shnu_qty1', 'total_shnu_qty2', 'total_shnu_qty3', 'total_shnu_qty4', 'total_shnu_qty5', 'seln_mbcr_glob_yn_1', 'seln_mbcr_glob_yn_2', 'seln_mbcr_glob_yn_3', 'seln_mbcr_glob_yn_4', 'seln_mbcr_glob_yn_5', 'shnu_mbcr_glob_yn_1', 'shnu_mbcr_glob_yn_2', 'shnu_mbcr_glob_yn_3', 'shnu_mbcr_glob_yn_4', 'shnu_mbcr_glob_yn_5', 'seln_mbcr_no1', 'seln_mbcr_no2', 'seln_mbcr_no3', 'seln_mbcr_no4', 'seln_mbcr_no5', 'shnu_mbcr_no1', 'shnu_mbcr_no2', 'shnu_mbcr_no3', 'shnu_mbcr_no4', 'shnu_mbcr_no5', 'seln_mbcr_rlim1', 'seln_mbcr_rlim2', 'seln_mbcr_rlim3', 'seln_mbcr_rlim4', 'seln_mbcr_rlim5', 'shnu_mbcr_rlim1', 'shnu_mbcr_rlim2', 'shnu_mbcr_rlim3', 'shnu_mbcr_rlim4', 'shnu_mbcr_rlim5', 'seln_qty_icdc1', 'seln_qty_icdc2', 'seln_qty_icdc3', 'seln_qty_icdc4', 'seln_qty_icdc5', 'shnu_qty_icdc1', 'shnu_qty_icdc2', 'shnu_qty_icdc3', 'shnu_qty_icdc4', 'shnu_qty_icdc5', 'glob_total_seln_qty', 'glob_total_shnu_qty', 'glob_total_seln_qty_icdc', 'glob_total_shnu_qty_icdc', 'glob_ntby_qty', 'glob_seln_rlim', 'glob_shnu_rlim', 'seln2_mbcr_eng_name1', 'seln2_mbcr_eng_name2', 'seln2_mbcr_eng_name3', 'seln2_mbcr_eng_name4', 'seln2_mbcr_eng_name5', 'byov_mbcr_eng_name1', 'byov_mbcr_eng_name2', 'byov_mbcr_eng_name3', 'byov_mbcr_eng_name4', 'byov_mbcr_eng_name5']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.member_krx', tr_id, tr_type, params, tuple(columns), 'real')

def member_nxt(tr_type, tr_key):
    """KIS domestic_stock_ws.member_nxt 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드, 빈 문자열이 아니어야 함
message (dict): 실시간 데이터 메시지
columns (list[str]): 응답 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 빈 문자열일 수 없습니다.')
    tr_id = 'H0NXMBC0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'SELN2_MBCR_NAME1', 'SELN2_MBCR_NAME2', 'SELN2_MBCR_NAME3', 'SELN2_MBCR_NAME4', 'SELN2_MBCR_NAME5', 'BYOV_MBCR_NAME1', 'BYOV_MBCR_NAME2', 'BYOV_MBCR_NAME3', 'BYOV_MBCR_NAME4', 'BYOV_MBCR_NAME5', 'TOTAL_SELN_QTY1', 'TOTAL_SELN_QTY2', 'TOTAL_SELN_QTY3', 'TOTAL_SELN_QTY4', 'TOTAL_SELN_QTY5', 'TOTAL_SHNU_QTY1', 'TOTAL_SHNU_QTY2', 'TOTAL_SHNU_QTY3', 'TOTAL_SHNU_QTY4', 'TOTAL_SHNU_QTY5', 'SELN_MBCR_GLOB_YN_1', 'SELN_MBCR_GLOB_YN_2', 'SELN_MBCR_GLOB_YN_3', 'SELN_MBCR_GLOB_YN_4', 'SELN_MBCR_GLOB_YN_5', 'SHNU_MBCR_GLOB_YN_1', 'SHNU_MBCR_GLOB_YN_2', 'SHNU_MBCR_GLOB_YN_3', 'SHNU_MBCR_GLOB_YN_4', 'SHNU_MBCR_GLOB_YN_5', 'SELN_MBCR_NO1', 'SELN_MBCR_NO2', 'SELN_MBCR_NO3', 'SELN_MBCR_NO4', 'SELN_MBCR_NO5', 'SHNU_MBCR_NO1', 'SHNU_MBCR_NO2', 'SHNU_MBCR_NO3', 'SHNU_MBCR_NO4', 'SHNU_MBCR_NO5', 'SELN_MBCR_RLIM1', 'SELN_MBCR_RLIM2', 'SELN_MBCR_RLIM3', 'SELN_MBCR_RLIM4', 'SELN_MBCR_RLIM5', 'SHNU_MBCR_RLIM1', 'SHNU_MBCR_RLIM2', 'SHNU_MBCR_RLIM3', 'SHNU_MBCR_RLIM4', 'SHNU_MBCR_RLIM5', 'SELN_QTY_ICDC1', 'SELN_QTY_ICDC2', 'SELN_QTY_ICDC3', 'SELN_QTY_ICDC4', 'SELN_QTY_ICDC5', 'SHNU_QTY_ICDC1', 'SHNU_QTY_ICDC2', 'SHNU_QTY_ICDC3', 'SHNU_QTY_ICDC4', 'SHNU_QTY_ICDC5', 'GLOB_TOTAL_SELN_QTY', 'GLOB_TOTAL_SHNU_QTY', 'GLOB_TOTAL_SELN_QTY_ICDC', 'GLOB_TOTAL_SHNU_QTY_ICDC', 'GLOB_NTBY_QTY', 'GLOB_SELN_RLIM', 'GLOB_SHNU_RLIM', 'SELN2_MBCR_ENG_NAME1', 'SELN2_MBCR_ENG_NAME2', 'SELN2_MBCR_ENG_NAME3', 'SELN2_MBCR_ENG_NAME4', 'SELN2_MBCR_ENG_NAME5', 'BYOV_MBCR_ENG_NAME1', 'BYOV_MBCR_ENG_NAME2', 'BYOV_MBCR_ENG_NAME3', 'BYOV_MBCR_ENG_NAME4', 'BYOV_MBCR_ENG_NAME5']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.member_nxt', tr_id, tr_type, params, tuple(columns), 'real')

def member_total(tr_type, tr_key):
    """KIS domestic_stock_ws.member_total 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드, 빈 문자열이 아니어야 함
message (dict): 실시간으로 수신된 메시지 데이터
columns (list[str]): 응답 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다.')
    tr_id = 'H0UNMBC0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'SELN2_MBCR_NAME1', 'SELN2_MBCR_NAME2', 'SELN2_MBCR_NAME3', 'SELN2_MBCR_NAME4', 'SELN2_MBCR_NAME5', 'BYOV_MBCR_NAME1', 'BYOV_MBCR_NAME2', 'BYOV_MBCR_NAME3', 'BYOV_MBCR_NAME4', 'BYOV_MBCR_NAME5', 'TOTAL_SELN_QTY1', 'TOTAL_SELN_QTY2', 'TOTAL_SELN_QTY3', 'TOTAL_SELN_QTY4', 'TOTAL_SELN_QTY5', 'TOTAL_SHNU_QTY1', 'TOTAL_SHNU_QTY2', 'TOTAL_SHNU_QTY3', 'TOTAL_SHNU_QTY4', 'TOTAL_SHNU_QTY5', 'SELN_MBCR_GLOB_YN_1', 'SELN_MBCR_GLOB_YN_2', 'SELN_MBCR_GLOB_YN_3', 'SELN_MBCR_GLOB_YN_4', 'SELN_MBCR_GLOB_YN_5', 'SHNU_MBCR_GLOB_YN_1', 'SHNU_MBCR_GLOB_YN_2', 'SHNU_MBCR_GLOB_YN_3', 'SHNU_MBCR_GLOB_YN_4', 'SHNU_MBCR_GLOB_YN_5', 'SELN_MBCR_NO1', 'SELN_MBCR_NO2', 'SELN_MBCR_NO3', 'SELN_MBCR_NO4', 'SELN_MBCR_NO5', 'SHNU_MBCR_NO1', 'SHNU_MBCR_NO2', 'SHNU_MBCR_NO3', 'SHNU_MBCR_NO4', 'SHNU_MBCR_NO5', 'SELN_MBCR_RLIM1', 'SELN_MBCR_RLIM2', 'SELN_MBCR_RLIM3', 'SELN_MBCR_RLIM4', 'SELN_MBCR_RLIM5', 'SHNU_MBCR_RLIM1', 'SHNU_MBCR_RLIM2', 'SHNU_MBCR_RLIM3', 'SHNU_MBCR_RLIM4', 'SHNU_MBCR_RLIM5', 'SELN_QTY_ICDC1', 'SELN_QTY_ICDC2', 'SELN_QTY_ICDC3', 'SELN_QTY_ICDC4', 'SELN_QTY_ICDC5', 'SHNU_QTY_ICDC1', 'SHNU_QTY_ICDC2', 'SHNU_QTY_ICDC3', 'SHNU_QTY_ICDC4', 'SHNU_QTY_ICDC5', 'GLOB_TOTAL_SELN_QTY', 'GLOB_TOTAL_SHNU_QTY', 'GLOB_TOTAL_SELN_QTY_ICDC', 'GLOB_TOTAL_SHNU_QTY_ICDC', 'GLOB_NTBY_QTY', 'GLOB_SELN_RLIM', 'GLOB_SHNU_RLIM', 'SELN2_MBCR_ENG_NAME1', 'SELN2_MBCR_ENG_NAME2', 'SELN2_MBCR_ENG_NAME3', 'SELN2_MBCR_ENG_NAME4', 'SELN2_MBCR_ENG_NAME5', 'BYOV_MBCR_ENG_NAME1', 'BYOV_MBCR_ENG_NAME2', 'BYOV_MBCR_ENG_NAME3', 'BYOV_MBCR_ENG_NAME4', 'BYOV_MBCR_ENG_NAME5']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.member_total', tr_id, tr_type, params, tuple(columns), 'real')

def overtime_asking_price_krx(tr_type, tr_key):
    """KIS domestic_stock_ws.overtime_asking_price_krx 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다.')
    tr_id = 'H0STOAA0'
    params = {'tr_key': tr_key}
    columns = ['mksc_shrn_iscd', 'bsop_hour', 'hour_cls_code', 'askp1', 'askp2', 'askp3', 'askp4', 'askp5', 'askp6', 'askp7', 'askp8', 'askp9', 'bidp1', 'bidp2', 'bidp3', 'bidp4', 'bidp5', 'bidp6', 'bidp7', 'bidp8', 'bidp9', 'askp_rsqn1', 'askp_rsqn2', 'askp_rsqn3', 'askp_rsqn4', 'askp_rsqn5', 'askp_rsqn6', 'askp_rsqn7', 'askp_rsqn8', 'askp_rsqn9', 'bidp_rsqn1', 'bidp_rsqn2', 'bidp_rsqn3', 'bidp_rsqn4', 'bidp_rsqn5', 'bidp_rsqn6', 'bidp_rsqn7', 'bidp_rsqn8', 'bidp_rsqn9', 'total_askp_rsqn', 'total_bidp_rsqn', 'ovtm_total_askp_rsqn', 'ovtm_total_bidp_rsqn', 'antc_cnpr', 'antc_cnqn', 'antc_vol', 'antc_cntg_vrss', 'antc_cntg_vrss_sign', 'antc_cntg_prdy_ctrt', 'acml_vol', 'total_askp_rsqn_icdc', 'total_bidp_rsqn_icdc', 'ovtm_total_askp_icdc', 'ovtm_total_bidp_icdc']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.overtime_asking_price_krx', tr_id, tr_type, params, tuple(columns), 'real')

def overtime_ccnl_krx(tr_type, tr_key):
    """KIS domestic_stock_ws.overtime_ccnl_krx 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부
tr_key (str): [필수] 구독할 종목의 코드 (빈 문자열 불가)
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key is required and cannot be an empty string')
    tr_id = 'H0STOUP0'
    params = {'tr_key': tr_key}
    columns = ['mksc_shrn_iscd', 'stck_cntg_hour', 'stck_prpr', 'prdy_vrss_sign', 'prdy_vrss', 'prdy_ctrt', 'wghn_avrg_stck_prc', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'askp1', 'bidp1', 'cntg_vol', 'acml_vol', 'acml_tr_pbmn', 'seln_cntg_csnu', 'shnu_cntg_csnu', 'ntby_cntg_csnu', 'cttr', 'seln_cntg_smtn', 'shnu_cntg_smtn', 'cntg_cls_code', 'shnu_rate', 'prdy_vol_vrss_acml_vol_rate', 'oprc_hour', 'oprc_vrss_prpr_sign', 'oprc_vrss_prpr', 'hgpr_hour', 'hgpr_vrss_prpr_sign', 'hgpr_vrss_prpr', 'lwpr_hour', 'lwpr_vrss_prpr_sign', 'lwpr_vrss_prpr', 'bsop_date', 'new_mkop_cls_code', 'trht_yn', 'askp_rsqn1', 'bidp_rsqn1', 'total_askp_rsqn', 'total_bidp_rsqn', 'vol_tnrt', 'prdy_smns_hour_acml_vol', 'prdy_smns_hour_acml_vol_rate']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.overtime_ccnl_krx', tr_id, tr_type, params, tuple(columns), 'real')

def overtime_exp_ccnl_krx(tr_type, tr_key):
    """KIS domestic_stock_ws.overtime_exp_ccnl_krx 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타냅니다.
tr_key (str): [필수] 종목코드. 빈 문자열이 아니어야 합니다.
message (dict): 실시간 데이터 구독에 대한 메시지 데이터.
columns (list[str]): 실시간 데이터의 컬럼 정보."""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다.')
    tr_id = 'H0STOAC0'
    params = {'tr_key': tr_key}
    columns = ['mksc_shrn_iscd', 'stck_cntg_hour', 'stck_prpr', 'prdy_vrss_sign', 'prdy_vrss', 'prdy_ctrt', 'wghn_avrg_stck_prc', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'askp1', 'bidp1', 'cntg_vol', 'acml_vol', 'acml_tr_pbmn', 'seln_cntg_csnu', 'shnu_cntg_csnu', 'ntby_cntg_csnu', 'cttr', 'seln_cntg_smtn', 'shnu_cntg_smtn', 'cntg_cls_code', 'shnu_rate', 'prdy_vol_vrss_acml_vol_rate', 'oprc_hour', 'oprc_vrss_prpr_sign', 'oprc_vrss_prpr', 'hgpr_hour', 'hgpr_vrss_prpr_sign', 'hgpr_vrss_prpr', 'lwpr_hour', 'lwpr_vrss_prpr_sign', 'lwpr_vrss_prpr', 'bsop_date', 'new_mkop_cls_code', 'trht_yn', 'askp_rsqn1', 'bidp_rsqn1', 'total_askp_rsqn', 'total_bidp_rsqn', 'vol_tnrt', 'prdy_smns_hour_acml_vol', 'prdy_smns_hour_acml_vol_rate']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.overtime_exp_ccnl_krx', tr_id, tr_type, params, tuple(columns), 'real')

def program_trade_krx(tr_type, tr_key):
    """KIS domestic_stock_ws.program_trade_krx 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 문자열
tr_key (str): [필수] 종목코드. 빈 문자열이 아니어야 하며, 유효한 종목코드 형식이어야 합니다.
message (dict): 웹소켓을 통해 수신된 메시지 데이터
columns (list[str]): 응답 데이터의 컬럼 정보 리스트"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다.')
    tr_id = 'H0STPGM0'
    params = {'tr_key': tr_key}
    columns = ['mksc_shrn_iscd', 'stck_cntg_hour', 'seln_cnqn', 'seln_tr_pbmn', 'shnu_cnqn', 'shnu_tr_pbmn', 'ntby_cnqn', 'ntby_tr_pbmn', 'seln_rsqn', 'shnu_rsqn', 'whol_ntby_qty']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.program_trade_krx', tr_id, tr_type, params, tuple(columns), 'real')

def program_trade_nxt(tr_type, tr_key):
    """KIS domestic_stock_ws.program_trade_nxt 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 실시간 데이터 메시지
columns (list[str]): 응답 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 필수 입력값입니다.')
    tr_id = 'H0NXPGM0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'STCK_CNTG_HOUR', 'SELN_CNQN', 'SELN_TR_PBMN', 'SHNU_CNQN', 'SHNU_TR_PBMN', 'NTBY_CNQN', 'NTBY_TR_PBMN', 'SELN_RSQN', 'SHNU_RSQN', 'WHOL_NTBY_QTY']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.program_trade_nxt', tr_id, tr_type, params, tuple(columns), 'real')

def program_trade_total(tr_type, tr_key):
    """KIS domestic_stock_ws.program_trade_total 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록("1") 또는 해제("0") 여부를 나타내는 값
tr_key (str): [필수] 종목코드 (빈 문자열 불가)
message (dict): 실시간 데이터 메시지
columns (list[str]): 응답 데이터의 컬럼 정보"""
    if not tr_key:
        raise ValueError('tr_key는 빈 문자열일 수 없습니다.')
    tr_id = 'H0UNPGM0'
    params = {'tr_key': tr_key}
    columns = ['MKSC_SHRN_ISCD', 'STCK_CNTG_HOUR', 'SELN_CNQN', 'SELN_TR_PBMN', 'SHNU_CNQN', 'SHNU_TR_PBMN', 'NTBY_CNQN', 'NTBY_TR_PBMN', 'SELN_RSQN', 'SHNU_RSQN', 'WHOL_NTBY_QTY']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_stock_ws.program_trade_total', tr_id, tr_type, params, tuple(columns), 'real')


def vi_krx(tr_type, tr_key):
    """KRX VI 통보. tr_key는 종목이 아닌 영업일 YYYYMMDD다."""
    return Subscription("domestic_stock_ws.vi_krx", "H0STVIC0", tr_type, {"tr_key": tr_key}, websocket_columns("H0STVIC0"))



def vi_integrated(tr_type, tr_key):
    """통합 VI 통보. tr_key는 종목코드다."""
    return Subscription("domestic_stock_ws.vi_integrated", "H0UNVIC0", tr_type, {"tr_key": tr_key}, websocket_columns("H0UNVIC0"))



def vi_nxt(tr_type, tr_key):
    """NXT VI 통보. tr_key는 종목코드다."""
    return Subscription("domestic_stock_ws.vi_nxt", "H0NXVIC0", tr_type, {"tr_key": tr_key}, websocket_columns("H0NXVIC0"))

