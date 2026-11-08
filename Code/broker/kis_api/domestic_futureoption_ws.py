# 현재 사용 불허: 구현은 보존하며 Config/kis-api-catalog.json의 enabled=false로 전송·구독을 차단한다.
"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
from .schemas import websocket_columns
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def commodity_futures_realtime_conclusion(tr_type, tr_key):
    """KIS domestic_futureoption_ws.commodity_futures_realtime_conclusion 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록/해제 여부 (ex. "1": 구독, "2": 해제)
tr_key (str): [필수] 종목코드 (ex. 101S12)
message (str): 메시지 데이터"""
    if tr_type == '':
        raise ValueError('tr_type is empty')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0CFCNT0'
    params = {'tr_key': tr_key}
    columns = ['futs_shrn_iscd', 'bsop_hour', 'futs_prdy_vrss', 'prdy_vrss_sign', 'futs_prdy_ctrt', 'futs_prpr', 'futs_oprc', 'futs_hgpr', 'futs_lwpr', 'last_cnqn', 'acml_vol', 'acml_tr_pbmn', 'hts_thpr', 'mrkt_basis', 'dprt', 'nmsc_fctn_stpl_prc', 'fmsc_fctn_stpl_prc', 'spead_prc', 'hts_otst_stpl_qty', 'otst_stpl_qty_icdc', 'oprc_hour', 'oprc_vrss_prpr_sign', 'oprc_vrss_nmix_prpr', 'hgpr_hour', 'hgpr_vrss_prpr_sign', 'hgpr_vrss_nmix_prpr', 'lwpr_hour', 'lwpr_vrss_prpr_sign', 'lwpr_vrss_nmix_prpr', 'shnu_rate', 'cttr', 'esdg', 'otst_stpl_rgbf_qty_icdc', 'thpr_basis', 'futs_askp1', 'futs_bidp1', 'askp_rsqn1', 'bidp_rsqn1', 'seln_cntg_csnu', 'shnu_cntg_csnu', 'ntby_cntg_csnu', 'seln_cntg_smtn', 'shnu_cntg_smtn', 'total_askp_rsqn', 'total_bidp_rsqn', 'prdy_vol_vrss_acml_vol_rate', 'dscs_bltr_acml_qty', 'dynm_mxpr', 'dynm_llam', 'dynm_prc_limt_yn']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.commodity_futures_realtime_conclusion', tr_id, tr_type, params, tuple(columns), 'real')

def commodity_futures_realtime_quote(tr_type, tr_key):
    """KIS domestic_futureoption_ws.commodity_futures_realtime_quote 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록/해제 여부 (ex. "1": 구독, "2": 해제)
tr_key (str): [필수] 종목코드 (ex. 101S12)
message (str): 메시지 데이터"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0CFASP0'
    params = {'tr_key': tr_key}
    columns = ['futs_shrn_iscd', 'bsop_hour', 'futs_askp1', 'futs_askp2', 'futs_askp3', 'futs_askp4', 'futs_askp5', 'futs_bidp1', 'futs_bidp2', 'futs_bidp3', 'futs_bidp4', 'futs_bidp5', 'askp_csnu1', 'askp_csnu2', 'askp_csnu3', 'askp_csnu4', 'askp_csnu5', 'bidp_csnu1', 'bidp_csnu2', 'bidp_csnu3', 'bidp_csnu4', 'bidp_csnu5', 'askp_rsqn1', 'askp_rsqn2', 'askp_rsqn3', 'askp_rsqn4', 'askp_rsqn5', 'bidp_rsqn1', 'bidp_rsqn2', 'bidp_rsqn3', 'bidp_rsqn4', 'bidp_rsqn5', 'total_askp_csnu', 'total_bidp_csnu', 'total_askp_rsqn', 'total_bidp_rsqn', 'total_askp_rsqn_icdc', 'total_bidp_rsqn_icdc']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.commodity_futures_realtime_quote', tr_id, tr_type, params, tuple(columns), 'real')

def fuopt_ccnl_notice(tr_type, tr_key):
    """KIS domestic_futureoption_ws.fuopt_ccnl_notice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록/해제 여부 (ex. "1": 구독, "2": 해제)
tr_key (str): [필수] 코드 (ex. dttest11)
message (str): 메시지 데이터"""
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0IFCNI0'
    params = {'tr_key': tr_key}
    columns = ['cust_id', 'acnt_no', 'oder_no', 'ooder_no', 'seln_byov_cls', 'rctf_cls', 'oder_kind2', 'stck_shrn_iscd', 'cntg_qty', 'cntg_unpr', 'stck_cntg_hour', 'rfus_yn', 'cntg_yn', 'acpt_yn', 'brnc_no', 'oder_qty', 'acnt_name', 'cntg_isnm', 'oder_cond', 'ord_grp', 'ord_grpseq', 'order_prc']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.fuopt_ccnl_notice', tr_id, tr_type, params, tuple(columns), 'real')

def futures_exp_ccnl(tr_type, tr_key):
    """KIS domestic_futureoption_ws.futures_exp_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0ZFANC0'
    params = {'tr_key': tr_key}
    columns = ['futs_shrn_iscd', 'bsop_hour', 'antc_cnpr', 'antc_cntg_vrss', 'antc_cntg_vrss_sign', 'antc_cntg_prdy_ctrt', 'antc_mkop_cls_code', 'antc_cnqn']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.futures_exp_ccnl', tr_id, tr_type, params, tuple(columns), 'real')

def index_futures_realtime_conclusion(tr_type, tr_key):
    """KIS domestic_futureoption_ws.index_futures_realtime_conclusion 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록/해제 여부 (ex. "1": 구독, "2": 해제)
tr_key (str): [필수] 코드 (ex. 101S12)
message (str): 메시지 데이터"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0IFCNT0'
    params = {'tr_key': tr_key}
    columns = ['futs_shrn_iscd', 'bsop_hour', 'futs_prdy_vrss', 'prdy_vrss_sign', 'futs_prdy_ctrt', 'futs_prpr', 'futs_oprc', 'futs_hgpr', 'futs_lwpr', 'last_cnqn', 'acml_vol', 'acml_tr_pbmn', 'hts_thpr', 'mrkt_basis', 'dprt', 'nmsc_fctn_stpl_prc', 'fmsc_fctn_stpl_prc', 'spead_prc', 'hts_otst_stpl_qty', 'otst_stpl_qty_icdc', 'oprc_hour', 'oprc_vrss_prpr_sign', 'oprc_vrss_nmix_prpr', 'hgpr_hour', 'hgpr_vrss_prpr_sign', 'hgpr_vrss_nmix_prpr', 'lwpr_hour', 'lwpr_vrss_prpr_sign', 'lwpr_vrss_nmix_prpr', 'shnu_rate', 'cttr', 'esdg', 'otst_stpl_rgbf_qty_icdc', 'thpr_basis', 'futs_askp1', 'futs_bidp1', 'askp_rsqn1', 'bidp_rsqn1', 'seln_cntg_csnu', 'shnu_cntg_csnu', 'ntby_cntg_csnu', 'seln_cntg_smtn', 'shnu_cntg_smtn', 'total_askp_rsqn', 'total_bidp_rsqn', 'prdy_vol_vrss_acml_vol_rate', 'dscs_bltr_acml_qty', 'dynm_mxpr', 'dynm_llam', 'dynm_prc_limt_yn']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.index_futures_realtime_conclusion', tr_id, tr_type, params, tuple(columns), 'real')

def index_futures_realtime_quote(tr_type, tr_key):
    """KIS domestic_futureoption_ws.index_futures_realtime_quote 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록/해제 여부 (ex. "1": 구독, "2": 해제)
tr_key (str): [필수] 코드 (ex. 101S12)
message (str): 메시지 데이터"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0IFASP0'
    params = {'tr_key': tr_key}
    columns = ['futs_shrn_iscd', 'bsop_hour', 'futs_askp1', 'futs_askp2', 'futs_askp3', 'futs_askp4', 'futs_askp5', 'futs_bidp1', 'futs_bidp2', 'futs_bidp3', 'futs_bidp4', 'futs_bidp5', 'askp_csnu1', 'askp_csnu2', 'askp_csnu3', 'askp_csnu4', 'askp_csnu5', 'bidp_csnu1', 'bidp_csnu2', 'bidp_csnu3', 'bidp_csnu4', 'bidp_csnu5', 'askp_rsqn1', 'askp_rsqn2', 'askp_rsqn3', 'askp_rsqn4', 'askp_rsqn5', 'bidp_rsqn1', 'bidp_rsqn2', 'bidp_rsqn3', 'bidp_rsqn4', 'bidp_rsqn5', 'total_askp_csnu', 'total_bidp_csnu', 'total_askp_rsqn', 'total_bidp_rsqn', 'total_askp_rsqn_icdc', 'total_bidp_rsqn_icdc']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.index_futures_realtime_quote', tr_id, tr_type, params, tuple(columns), 'real')

def index_option_realtime_conclusion(tr_type, tr_key):
    """KIS domestic_futureoption_ws.index_option_realtime_conclusion 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록/해제 여부 (ex. "1": 구독, "2": 해제)
tr_key (str): [필수] 코드 (ex. 201S11305)
message (str): 메시지 데이터"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0IOCNT0'
    params = {'tr_key': tr_key}
    columns = ['optn_shrn_iscd', 'bsop_hour', 'optn_prpr', 'prdy_vrss_sign', 'optn_prdy_vrss', 'prdy_ctrt', 'optn_oprc', 'optn_hgpr', 'optn_lwpr', 'last_cnqn', 'acml_vol', 'acml_tr_pbmn', 'hts_thpr', 'hts_otst_stpl_qty', 'otst_stpl_qty_icdc', 'oprc_hour', 'oprc_vrss_prpr_sign', 'oprc_vrss_nmix_prpr', 'hgpr_hour', 'hgpr_vrss_prpr_sign', 'hgpr_vrss_nmix_prpr', 'lwpr_hour', 'lwpr_vrss_prpr_sign', 'lwpr_vrss_nmix_prpr', 'shnu_rate', 'prmm_val', 'invl_val', 'tmvl_val', 'delta', 'gama', 'vega', 'theta', 'rho', 'hts_ints_vltl', 'esdg', 'otst_stpl_rgbf_qty_icdc', 'thpr_basis', 'unas_hist_vltl', 'cttr', 'dprt', 'mrkt_basis', 'optn_askp1', 'optn_bidp1', 'askp_rsqn1', 'bidp_rsqn1', 'seln_cntg_csnu', 'shnu_cntg_csnu', 'ntby_cntg_csnu', 'seln_cntg_smtn', 'shnu_cntg_smtn', 'total_askp_rsqn', 'total_bidp_rsqn', 'prdy_vol_vrss_acml_vol_rate', 'avrg_vltl', 'dscs_lrqn_vol', 'dynm_mxpr', 'dynm_llam', 'dynm_prc_limt_yn']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.index_option_realtime_conclusion', tr_id, tr_type, params, tuple(columns), 'real')

def index_option_realtime_quote(tr_type, tr_key):
    """KIS domestic_futureoption_ws.index_option_realtime_quote 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록/해제 여부 (ex. "1": 구독, "2": 해제)
tr_key (str): [필수] 코드 (ex. 201S11305)
message (str): 메시지 데이터"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0IOASP0'
    params = {'tr_key': tr_key}
    columns = ['optn_shrn_iscd', 'bsop_hour', 'optn_askp1', 'optn_askp2', 'optn_askp3', 'optn_askp4', 'optn_askp5', 'optn_bidp1', 'optn_bidp2', 'optn_bidp3', 'optn_bidp4', 'optn_bidp5', 'askp_csnu1', 'askp_csnu2', 'askp_csnu3', 'askp_csnu4', 'askp_csnu5', 'bidp_csnu1', 'bidp_csnu2', 'bidp_csnu3', 'bidp_csnu4', 'bidp_csnu5', 'askp_rsqn1', 'askp_rsqn2', 'askp_rsqn3', 'askp_rsqn4', 'askp_rsqn5', 'bidp_rsqn1', 'bidp_rsqn2', 'bidp_rsqn3', 'bidp_rsqn4', 'bidp_rsqn5', 'total_askp_csnu', 'total_bidp_csnu', 'total_askp_rsqn', 'total_bidp_rsqn', 'total_askp_rsqn_icdc', 'total_bidp_rsqn_icdc']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.index_option_realtime_quote', tr_id, tr_type, params, tuple(columns), 'real')

def krx_ngt_futures_asking_price(tr_type, tr_key):
    """KIS domestic_futureoption_ws.krx_ngt_futures_asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0MFASP0'
    params = {'tr_key': tr_key}
    columns = ['futs_shrn_iscd', 'bsop_hour', 'futs_askp1', 'futs_askp2', 'futs_askp3', 'futs_askp4', 'futs_askp5', 'futs_bidp1', 'futs_bidp2', 'futs_bidp3', 'futs_bidp4', 'futs_bidp5', 'askp_csnu1', 'askp_csnu2', 'askp_csnu3', 'askp_csnu4', 'askp_csnu5', 'bidp_csnu1', 'bidp_csnu2', 'bidp_csnu3', 'bidp_csnu4', 'bidp_csnu5', 'askp_rsqn1', 'askp_rsqn2', 'askp_rsqn3', 'askp_rsqn4', 'askp_rsqn5', 'bidp_rsqn1', 'bidp_rsqn2', 'bidp_rsqn3', 'bidp_rsqn4', 'bidp_rsqn5', 'total_askp_csnu', 'total_bidp_csnu', 'total_askp_rsqn', 'total_bidp_rsqn', 'total_askp_rsqn_icdc', 'total_bidp_rsqn_icdc']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.krx_ngt_futures_asking_price', tr_id, tr_type, params, tuple(columns), 'real')

def krx_ngt_futures_ccnl(tr_type, tr_key):
    """KIS domestic_futureoption_ws.krx_ngt_futures_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0MFCNT0'
    params = {'tr_key': tr_key}
    columns = ['futs_shrn_iscd', 'bsop_hour', 'futs_prdy_vrss', 'prdy_vrss_sign', 'futs_prdy_ctrt', 'futs_prpr', 'futs_oprc', 'futs_hgpr', 'futs_lwpr', 'last_cnqn', 'acml_vol', 'acml_tr_pbmn', 'hts_thpr', 'mrkt_basis', 'dprt', 'nmsc_fctn_stpl_prc', 'fmsc_fctn_stpl_prc', 'spead_prc', 'hts_otst_stpl_qty', 'otst_stpl_qty_icdc', 'oprc_hour', 'oprc_vrss_prpr_sign', 'oprc_vrss_nmix_prpr', 'hgpr_hour', 'hgpr_vrss_prpr_sign', 'hgpr_vrss_nmix_prpr', 'lwpr_hour', 'lwpr_vrss_prpr_sign', 'lwpr_vrss_nmix_prpr', 'shnu_rate', 'cttr', 'esdg', 'otst_stpl_rgbf_qty_icdc', 'thpr_basis', 'futs_askp1', 'futs_bidp1', 'askp_rsqn1', 'bidp_rsqn1', 'seln_cntg_csnu', 'shnu_cntg_csnu', 'ntby_cntg_csnu', 'seln_cntg_smtn', 'shnu_cntg_smtn', 'total_askp_rsqn', 'total_bidp_rsqn', 'prdy_vol_vrss_acml_vol_rate', 'dynm_mxpr', 'dynm_llam', 'dynm_prc_limt_yn']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.krx_ngt_futures_ccnl', tr_id, tr_type, params, tuple(columns), 'real')

def krx_ngt_futures_ccnl_notice(tr_type, tr_key):
    """KIS domestic_futureoption_ws.krx_ngt_futures_ccnl_notice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0MFCNI0'
    params = {'tr_key': tr_key}
    columns = ['cust_id', 'acnt_no', 'oder_no', 'ooder_no', 'seln_byov_cls', 'rctf_cls', 'oder_kind2', 'stck_shrn_iscd', 'cntg_qty', 'cntg_unpr', 'stck_cntg_hour', 'rfus_yn', 'cntg_yn', 'acpt_yn', 'brnc_no', 'oder_qty', 'acnt_name', 'cntg_isnm', 'oder_cond']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.krx_ngt_futures_ccnl_notice', tr_id, tr_type, params, tuple(columns), 'real')

def krx_ngt_option_asking_price(tr_type, tr_key):
    """KIS domestic_futureoption_ws.krx_ngt_option_asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0EUASP0'
    params = {'tr_key': tr_key}
    columns = ['optn_shrn_iscd', 'bsop_hour', 'optn_askp1', 'optn_askp2', 'optn_askp3', 'optn_askp4', 'optn_askp5', 'optn_bidp1', 'optn_bidp2', 'optn_bidp3', 'optn_bidp4', 'optn_bidp5', 'askp_csnu1', 'askp_csnu2', 'askp_csnu3', 'askp_csnu4', 'askp_csnu5', 'bidp_csnu1', 'bidp_csnu2', 'bidp_csnu3', 'bidp_csnu4', 'bidp_csnu5', 'askp_rsqn1', 'askp_rsqn2', 'askp_rsqn3', 'askp_rsqn4', 'askp_rsqn5', 'bidp_rsqn1', 'bidp_rsqn2', 'bidp_rsqn3', 'bidp_rsqn4', 'bidp_rsqn5', 'total_askp_csnu', 'total_bidp_csnu', 'total_askp_rsqn', 'total_bidp_rsqn', 'total_askp_rsqn_icdc', 'total_bidp_rsqn_icdc']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.krx_ngt_option_asking_price', tr_id, tr_type, params, tuple(columns), 'real')

def krx_ngt_option_ccnl(tr_type, tr_key):
    """KIS domestic_futureoption_ws.krx_ngt_option_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 선물단축종목코드
message (str): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0EUCNT0'
    params = {'tr_key': tr_key}
    columns = ['optn_shrn_iscd', 'bsop_hour', 'optn_prpr', 'prdy_vrss_sign', 'optn_prdy_vrss', 'prdy_ctrt', 'optn_oprc', 'optn_hgpr', 'optn_lwpr', 'last_cnqn', 'acml_vol', 'acml_tr_pbmn', 'hts_thpr', 'hts_otst_stpl_qty', 'otst_stpl_qty_icdc', 'oprc_hour', 'oprc_vrss_prpr_sign', 'oprc_vrss_nmix_prpr', 'hgpr_hour', 'hgpr_vrss_prpr_sign', 'hgpr_vrss_nmix_prpr', 'lwpr_hour', 'lwpr_vrss_prpr_sign', 'lwpr_vrss_nmix_prpr', 'shnu_rate', 'prmm_val', 'invl_val', 'tmvl_val', 'delta', 'gama', 'vega', 'theta', 'rho', 'hts_ints_vltl', 'esdg', 'otst_stpl_rgbf_qty_icdc', 'thpr_basis', 'unas_hist_vltl', 'cttr', 'dprt', 'mrkt_basis', 'optn_askp1', 'optn_bidp1', 'askp_rsqn1', 'bidp_rsqn1', 'seln_cntg_csnu', 'shnu_cntg_csnu', 'ntby_cntg_csnu', 'seln_cntg_smtn', 'shnu_cntg_smtn', 'total_askp_rsqn', 'total_bidp_rsqn', 'prdy_vol_vrss_acml_vol_rate', 'dynm_mxpr', 'dynm_prc_limt_yn', 'dynm_llam']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.krx_ngt_option_ccnl', tr_id, tr_type, params, tuple(columns), 'real')

def krx_ngt_option_exp_ccnl(tr_type, tr_key):
    """KIS domestic_futureoption_ws.krx_ngt_option_exp_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 선물단축종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0EUANC0'
    params = {'tr_key': tr_key}
    columns = ['optn_shrn_iscd', 'bsop_hour', 'antc_cnpr', 'antc_cntg_vrss', 'antc_cntg_vrss_sign', 'antc_cntg_prdy_ctrt', 'antc_mkop_cls_code', 'antc_cnqn']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.krx_ngt_option_exp_ccnl', tr_id, tr_type, params, tuple(columns), 'real')

def krx_ngt_option_notice(tr_type, tr_key):
    """KIS domestic_futureoption_ws.krx_ngt_option_notice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 고객 ID
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0EUCNI0'
    params = {'tr_key': tr_key}
    columns = ['cust_id', 'acnt_no', 'oder_no', 'ooder_no', 'seln_byov_cls', 'rctf_cls', 'oder_kind2', 'stck_shrn_iscd', 'cntg_qty', 'cntg_unpr', 'stck_cntg_hour', 'rfus_yn', 'cntg_yn', 'acpt_yn', 'brnc_no', 'oder_qty', 'acnt_name', 'cntg_isnm', 'oder_cond']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.krx_ngt_option_notice', tr_id, tr_type, params, tuple(columns), 'real')

def option_exp_ccnl(tr_type, tr_key):
    """KIS domestic_futureoption_ws.option_exp_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0ZOANC0'
    params = {'tr_key': tr_key}
    columns = ['optn_shrn_iscd', 'bsop_hour', 'antc_cnpr', 'antc_cntg_vrss', 'antc_cntg_vrss_sign', 'antc_cntg_prdy_ctrt', 'antc_mkop_cls_code']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.option_exp_ccnl', tr_id, tr_type, params, tuple(columns), 'real')

def stock_futures_realtime_conclusion(tr_type, tr_key):
    """KIS domestic_futureoption_ws.stock_futures_realtime_conclusion 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록/해제 여부 (ex. "1": 구독, "2": 해제)
tr_key (str): [필수] 종목코드 (ex. 101S12)
message (str): 메시지 데이터"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0ZFCNT0'
    params = {'tr_key': tr_key}
    columns = ['futs_shrn_iscd', 'bsop_hour', 'stck_prpr', 'prdy_vrss_sign', 'prdy_vrss', 'futs_prdy_ctrt', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'last_cnqn', 'acml_vol', 'acml_tr_pbmn', 'hts_thpr', 'mrkt_basis', 'dprt', 'nmsc_fctn_stpl_prc', 'fmsc_fctn_stpl_prc', 'spead_prc', 'hts_otst_stpl_qty', 'otst_stpl_qty_icdc', 'oprc_hour', 'oprc_vrss_prpr_sign', 'oprc_vrss_prpr', 'hgpr_hour', 'hgpr_vrss_prpr_sign', 'hgpr_vrss_prpr', 'lwpr_hour', 'lwpr_vrss_prpr_sign', 'lwpr_vrss_prpr', 'shnu_rate', 'cttr', 'esdg', 'otst_stpl_rgbf_qty_icdc', 'thpr_basis', 'askp1', 'bidp1', 'askp_rsqn1', 'bidp_rsqn1', 'seln_cntg_csnu', 'shnu_cntg_csnu', 'ntby_cntg_csnu', 'seln_cntg_smtn', 'shnu_cntg_smtn', 'total_askp_rsqn', 'total_bidp_rsqn', 'prdy_vol_vrss_acml_vol_rate', 'dynm_mxpr', 'dynm_llam', 'dynm_prc_limt_yn']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.stock_futures_realtime_conclusion', tr_id, tr_type, params, tuple(columns), 'real')

def stock_futures_realtime_quote(tr_type, tr_key):
    """KIS domestic_futureoption_ws.stock_futures_realtime_quote 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 구독 등록/해제 여부 (ex. "1": 구독, "2": 해제)
tr_key (str): [필수] 종목코드 (ex. 101S12)
message (str): 메시지 데이터"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0ZFASP0'
    params = {'tr_key': tr_key}
    columns = ['futs_shrn_iscd', 'bsop_hour', 'askp1', 'askp2', 'askp3', 'askp4', 'askp5', 'askp6', 'askp7', 'askp8', 'askp9', 'askp10', 'bidp1', 'bidp2', 'bidp3', 'bidp4', 'bidp5', 'bidp6', 'bidp7', 'bidp8', 'bidp9', 'bidp10', 'askp_csnu1', 'askp_csnu2', 'askp_csnu3', 'askp_csnu4', 'askp_csnu5', 'askp_csnu6', 'askp_csnu7', 'askp_csnu8', 'askp_csnu9', 'askp_csnu10', 'bidp_csnu1', 'bidp_csnu2', 'bidp_csnu3', 'bidp_csnu4', 'bidp_csnu5', 'bidp_csnu6', 'bidp_csnu7', 'bidp_csnu8', 'bidp_csnu9', 'bidp_csnu10', 'askp_rsqn1', 'askp_rsqn2', 'askp_rsqn3', 'askp_rsqn4', 'askp_rsqn5', 'askp_rsqn6', 'askp_rsqn7', 'askp_rsqn8', 'askp_rsqn9', 'askp_rsqn10', 'bidp_rsqn1', 'bidp_rsqn2', 'bidp_rsqn3', 'bidp_rsqn4', 'bidp_rsqn5', 'bidp_rsqn6', 'bidp_rsqn7', 'bidp_rsqn8', 'bidp_rsqn9', 'bidp_rsqn10', 'total_askp_csnu', 'total_bidp_csnu', 'total_askp_rsqn', 'total_bidp_rsqn', 'total_askp_rsqn_icdc', 'total_bidp_rsqn_icdc']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.stock_futures_realtime_quote', tr_id, tr_type, params, tuple(columns), 'real')

def stock_option_asking_price(tr_type, tr_key):
    """KIS domestic_futureoption_ws.stock_option_asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 선물단축종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0ZOASP0'
    params = {'tr_key': tr_key}
    columns = ['optn_shrn_iscd', 'bsop_hour', 'optn_askp1', 'optn_askp2', 'optn_askp3', 'optn_askp4', 'optn_askp5', 'optn_bidp1', 'optn_bidp2', 'optn_bidp3', 'optn_bidp4', 'optn_bidp5', 'askp_csnu1', 'askp_csnu2', 'askp_csnu3', 'askp_csnu4', 'askp_csnu5', 'bidp_csnu1', 'bidp_csnu2', 'bidp_csnu3', 'bidp_csnu4', 'bidp_csnu5', 'askp_rsqn1', 'askp_rsqn2', 'askp_rsqn3', 'askp_rsqn4', 'askp_rsqn5', 'bidp_rsqn1', 'bidp_rsqn2', 'bidp_rsqn3', 'bidp_rsqn4', 'bidp_rsqn5', 'total_askp_csnu', 'total_bidp_csnu', 'total_askp_rsqn', 'total_bidp_rsqn', 'total_askp_rsqn_icdc', 'total_bidp_rsqn_icdc', 'optn_askp6', 'optn_askp7', 'optn_askp8', 'optn_askp9', 'optn_askp10', 'optn_bidp6', 'optn_bidp7', 'optn_bidp8', 'optn_bidp9', 'optn_bidp10', 'askp_csnu6', 'askp_csnu7', 'askp_csnu8', 'askp_csnu9', 'askp_csnu10', 'bidp_csnu6', 'bidp_csnu7', 'bidp_csnu8', 'bidp_csnu9', 'bidp_csnu10', 'askp_rsqn6', 'askp_rsqn7', 'askp_rsqn8', 'askp_rsqn9', 'askp_rsqn10', 'bidp_rsqn6', 'bidp_rsqn7', 'bidp_rsqn8', 'bidp_rsqn9', 'bidp_rsqn10']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.stock_option_asking_price', tr_id, tr_type, params, tuple(columns), 'real')

def stock_option_ccnl(tr_type, tr_key):
    """KIS domestic_futureoption_ws.stock_option_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'H0ZOCNT0'
    params = {'tr_key': tr_key}
    columns = ['optn_shrn_iscd', 'bsop_hour', 'optn_prpr', 'prdy_vrss_sign', 'optn_prdy_vrss', 'prdy_ctrt', 'optn_oprc', 'optn_hgpr', 'optn_lwpr', 'last_cnqn', 'acml_vol', 'acml_tr_pbmn', 'hts_thpr', 'hts_otst_stpl_qty', 'otst_stpl_qty_icdc', 'oprc_hour', 'oprc_vrss_prpr_sign', 'oprc_vrss_nmix_prpr', 'hgpr_hour', 'hgpr_vrss_prpr_sign', 'hgpr_vrss_nmix_prpr', 'lwpr_hour', 'lwpr_vrss_prpr_sign', 'lwpr_vrss_nmix_prpr', 'shnu_rate', 'prmm_val', 'invl_val', 'tmvl_val', 'delta', 'gama', 'vega', 'theta', 'rho', 'hts_ints_vltl', 'esdg', 'otst_stpl_rgbf_qty_icdc', 'thpr_basis', 'unas_hist_vltl', 'cttr', 'dprt', 'mrkt_basis', 'optn_askp1', 'optn_bidp1', 'askp_rsqn1', 'bidp_rsqn1', 'seln_cntg_csnu', 'shnu_cntg_csnu', 'ntby_cntg_csnu', 'seln_cntg_smtn', 'shnu_cntg_smtn', 'total_askp_rsqn', 'total_bidp_rsqn', 'prdy_vol_vrss_acml_vol_rate']
    columns = websocket_columns(tr_id, columns)
    return Subscription('domestic_futureoption_ws.stock_option_ccnl', tr_id, tr_type, params, tuple(columns), 'real')
