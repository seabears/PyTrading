# 현재 사용 불허: 구현은 보존하며 Config/kis-api-catalog.json의 enabled=false로 전송·구독을 차단한다.
"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
from .schemas import websocket_columns
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def asking_price(tr_type, tr_key):
    """KIS overseas_futureoption_ws.asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'HDFFF010'
    params = {'tr_key': tr_key}
    columns = ['series_cd', 'recv_date', 'recv_time', 'prev_price', 'bid_qntt_1', 'bid_num_1', 'bid_price_1', 'ask_qntt_1', 'ask_num_1', 'ask_price_1', 'bid_qntt_2', 'bid_num_2', 'bid_price_2', 'ask_qntt_2', 'ask_num_2', 'ask_price_2', 'bid_qntt_3', 'bid_num_3', 'bid_price_3', 'ask_qntt_3', 'ask_num_3', 'ask_price_3', 'bid_qntt_4', 'bid_num_4', 'bid_price_4', 'ask_qntt_4', 'ask_num_4', 'ask_price_4', 'bid_qntt_5', 'bid_num_5', 'bid_price_5', 'ask_qntt_5', 'ask_num_5', 'ask_price_5', 'sttl_price']
    columns = websocket_columns(tr_id, columns)
    return Subscription('overseas_futureoption_ws.asking_price', tr_id, tr_type, params, tuple(columns), 'real')

def ccnl(tr_type, tr_key):
    """KIS overseas_futureoption_ws.ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'HDFFF020'
    params = {'tr_key': tr_key}
    columns = ['series_cd', 'bsns_date', 'mrkt_open_date', 'mrkt_open_time', 'mrkt_close_date', 'mrkt_close_time', 'prev_price', 'recv_date', 'recv_time', 'active_flag', 'last_price', 'last_qntt', 'prev_diff_price', 'prev_diff_rate', 'open_price', 'high_price', 'low_price', 'vol', 'prev_sign', 'quotsign', 'recv_time2', 'psttl_price', 'psttl_sign', 'psttl_diff_price', 'psttl_diff_rate']
    columns = websocket_columns(tr_id, columns)
    return Subscription('overseas_futureoption_ws.ccnl', tr_id, tr_type, params, tuple(columns), 'real')

def ccnl_notice(tr_type, tr_key):
    """KIS overseas_futureoption_ws.ccnl_notice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] 종목코드
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'HDFFF2C0'
    params = {'tr_key': tr_key}
    columns = ['acct_no', 'ord_dt', 'odno', 'orgn_ord_dt', 'orgn_odno', 'series', 'rvse_cncl_dvsn_cd', 'sll_buy_dvsn_cd', 'cplx_ord_dvsn_cd', 'prce_tp', 'fm_excg_rcit_dvsn_cd', 'ord_qty', 'fm_lmt_pric', 'fm_stop_ord_pric', 'tot_ccld_qty', 'tot_ccld_uv', 'ord_remq', 'fm_ord_grp_dt', 'ord_grp_stno', 'ord_dtl_dtime', 'oprt_dtl_dtime', 'work_empl', 'ccld_dt', 'ccno', 'api_ccno', 'ccld_qty', 'fm_ccld_pric', 'crcy_cd', 'trst_fee', 'ord_mdia_online_yn', 'fm_ccld_amt', 'fuop_item_dvsn_cd']
    columns = websocket_columns(tr_id, columns)
    return Subscription('overseas_futureoption_ws.ccnl_notice', tr_id, tr_type, params, tuple(columns), 'real')

def order_notice(tr_type, tr_key):
    """KIS overseas_futureoption_ws.order_notice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_type (str): [필수] 등록/해제
tr_key (str): [필수] HTS ID
message (dict): 메시지 데이터
columns (list[str]): 컬럼 정보"""
    if tr_type == '':
        raise ValueError('tr_type is required')
    if tr_key == '':
        raise ValueError('tr_key is required')
    tr_id = 'HDFFF1C0'
    params = {'tr_key': tr_key}
    columns = ['acct_no', 'ord_dt', 'odno', 'orgn_ord_dt', 'orgn_odno', 'series', 'rvse_cncl_dvsn_cd', 'sll_buy_dvsn_cd', 'cplx_ord_dvsn_cd', 'prce_tp', 'fm_excg_rcit_dvsn_cd', 'ord_qty', 'fm_lmt_pric', 'fm_stop_ord_pric', 'tot_ccld_qty', 'tot_ccld_uv', 'ord_remq', 'fm_ord_grp_dt', 'ord_grp_stno', 'ord_dtl_dtime', 'oprt_dtl_dtime', 'work_empl', 'crcy_cd', 'lqd_yn', 'lqd_lmt_pric', 'lqd_stop_pric', 'trd_cond', 'term_ord_vald_dtime', 'spec_tp', 'ecis_rsvn_ord_yn', 'fuop_item_dvsn_cd', 'auto_ord_dvsn_cd']
    columns = websocket_columns(tr_id, columns)
    return Subscription('overseas_futureoption_ws.order_notice', tr_id, tr_type, params, tuple(columns), 'real')
