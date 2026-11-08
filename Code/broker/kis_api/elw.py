# 현재 사용 불허: 구현은 보존하며 Config/kis-api-catalog.json의 enabled=false로 전송·구독을 차단한다.
"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def compare_stocks(fid_cond_scr_div_code, fid_input_iscd, tr_cont=''):
    """KIS elw.compare_stocks 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_scr_div_code (str): 조건화면분류코드 (예: '11517')
fid_input_iscd (str): 입력종목코드 (예: '005930')
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '11517')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '11517')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '005930')")
        raise ValueError("fid_input_iscd is required. (e.g. '005930')")
    tr_id = 'FHKEW151701C0'
    api_url = '/uapi/elw/v1/quotations/compare-stocks'
    params = {'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('elw.compare_stocks', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def cond_search(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_rank_sort_cls_code, fid_input_cnt_1, fid_rank_sort_cls_code_2='', fid_input_cnt_2='', fid_rank_sort_cls_code_3='', fid_input_cnt_3='', fid_trgt_cls_code='', fid_input_iscd='', fid_unas_input_iscd='', fid_mrkt_cls_code='', fid_input_date_1='', fid_input_date_2='', fid_input_iscd_2='', fid_etc_cls_code='', fid_input_rmnn_dynu_1='', fid_input_rmnn_dynu_2='', fid_prpr_cnt1='', fid_prpr_cnt2='', fid_rsfl_rate1='', fid_rsfl_rate2='', fid_vol1='', fid_vol2='', fid_aply_rang_prc_1='', fid_aply_rang_prc_2='', fid_lvrg_val1='', fid_lvrg_val2='', fid_vol3='', fid_vol4='', fid_ints_vltl1='', fid_ints_vltl2='', fid_prmm_val1='', fid_prmm_val2='', fid_gear1='', fid_gear2='', fid_prls_qryr_rate1='', fid_prls_qryr_rate2='', fid_delta1='', fid_delta2='', fid_acpr1='', fid_acpr2='', fid_stck_cnvr_rate1='', fid_stck_cnvr_rate2='', fid_div_cls_code='', fid_prit1='', fid_prit2='', fid_cfp1='', fid_cfp2='', fid_input_nmix_price_1='', fid_input_nmix_price_2='', fid_egea_val1='', fid_egea_val2='', fid_input_dvdn_ert='', fid_input_hist_vltl='', fid_theta1='', fid_theta2='', tr_cont=''):
    """KIS elw.cond_search 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (ELW의 경우 "W" 입력)
fid_cond_scr_div_code (str): 조건화면분류코드 (화면번호 "11510" 입력)
fid_rank_sort_cls_code (str): 순위정렬구분코드
fid_input_cnt_1 (str): 정렬1기준 (1: 상위, 2: 하위)
tr_cont (str): 연속 거래 여부 (초기 조회시 공백, 연속 조회시 "N")"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '11510')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '11510')")
    if fid_rank_sort_cls_code is None:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '0')")
    if not fid_input_cnt_1:
        logger.error("fid_input_cnt_1 is required. (e.g. '1')")
        raise ValueError("fid_input_cnt_1 is required. (e.g. '1')")
    tr_id = 'FHKEW15100000'
    api_url = '/uapi/elw/v1/quotations/cond-search'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_INPUT_CNT_1': fid_input_cnt_1, 'FID_RANK_SORT_CLS_CODE_2': fid_rank_sort_cls_code_2, 'FID_INPUT_CNT_2': fid_input_cnt_2, 'FID_RANK_SORT_CLS_CODE_3': fid_rank_sort_cls_code_3, 'FID_INPUT_CNT_3': fid_input_cnt_3, 'FID_TRGT_CLS_CODE': fid_trgt_cls_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_UNAS_INPUT_ISCD': fid_unas_input_iscd, 'FID_MRKT_CLS_CODE': fid_mrkt_cls_code, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2, 'FID_INPUT_ISCD_2': fid_input_iscd_2, 'FID_ETC_CLS_CODE': fid_etc_cls_code, 'FID_INPUT_RMNN_DYNU_1': fid_input_rmnn_dynu_1, 'FID_INPUT_RMNN_DYNU_2': fid_input_rmnn_dynu_2, 'FID_PRPR_CNT1': fid_prpr_cnt1, 'FID_PRPR_CNT2': fid_prpr_cnt2, 'FID_RSFL_RATE1': fid_rsfl_rate1, 'FID_RSFL_RATE2': fid_rsfl_rate2, 'FID_VOL1': fid_vol1, 'FID_VOL2': fid_vol2, 'FID_APLY_RANG_PRC_1': fid_aply_rang_prc_1, 'FID_APLY_RANG_PRC_2': fid_aply_rang_prc_2, 'FID_LVRG_VAL1': fid_lvrg_val1, 'FID_LVRG_VAL2': fid_lvrg_val2, 'FID_VOL3': fid_vol3, 'FID_VOL4': fid_vol4, 'FID_INTS_VLTL1': fid_ints_vltl1, 'FID_INTS_VLTL2': fid_ints_vltl2, 'FID_PRMM_VAL1': fid_prmm_val1, 'FID_PRMM_VAL2': fid_prmm_val2, 'FID_GEAR1': fid_gear1, 'FID_GEAR2': fid_gear2, 'FID_PRLS_QRYR_RATE1': fid_prls_qryr_rate1, 'FID_PRLS_QRYR_RATE2': fid_prls_qryr_rate2, 'FID_DELTA1': fid_delta1, 'FID_DELTA2': fid_delta2, 'FID_ACPR1': fid_acpr1, 'FID_ACPR2': fid_acpr2, 'FID_STCK_CNVR_RATE1': fid_stck_cnvr_rate1, 'FID_STCK_CNVR_RATE2': fid_stck_cnvr_rate2, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_PRIT1': fid_prit1, 'FID_PRIT2': fid_prit2, 'FID_CFP1': fid_cfp1, 'FID_CFP2': fid_cfp2, 'FID_INPUT_NMIX_PRICE_1': fid_input_nmix_price_1, 'FID_INPUT_NMIX_PRICE_2': fid_input_nmix_price_2, 'FID_EGEA_VAL1': fid_egea_val1, 'FID_EGEA_VAL2': fid_egea_val2, 'FID_INPUT_DVDN_ERT': fid_input_dvdn_ert, 'FID_INPUT_HIST_VLTL': fid_input_hist_vltl, 'FID_THETA1': fid_theta1, 'FID_THETA2': fid_theta2}
    return ApiRequest('elw.cond_search', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def expiration_stocks(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_date_1, fid_input_date_2, fid_div_cls_code, fid_etc_cls_code, fid_unas_input_iscd, fid_input_iscd_2, fid_blng_cls_code, fid_input_option_1, tr_cont=''):
    """KIS elw.expiration_stocks 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): W 입력
fid_cond_scr_div_code (str): 11547 입력
fid_input_date_1 (str): 입력날짜 ~ (ex) 20240402)
fid_input_date_2 (str): ~입력날짜 (ex) 20240408)
fid_div_cls_code (str): 0(콜),1(풋),2(전체)
fid_etc_cls_code (str): 공백 입력
fid_unas_input_iscd (str): 000000(전체), 2001(KOSPI 200), 기초자산코드(종목코드 ex. 삼성전자-005930)
fid_input_iscd_2 (str): 00000(전체), 00003(한국투자증권), 00017(KB증권), 00005(미래에셋증권)
fid_blng_cls_code (str): 0(전체),1(일반),2(조기종료)
fid_input_option_1 (str): 공백 입력
tr_cont (str): 연속 거래 여부"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '11547')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '11547')")
    if not fid_input_date_1:
        logger.error("fid_input_date_1 is required. (e.g. '20240402')")
        raise ValueError("fid_input_date_1 is required. (e.g. '20240402')")
    if not fid_input_date_2:
        logger.error("fid_input_date_2 is required. (e.g. '20240408')")
        raise ValueError("fid_input_date_2 is required. (e.g. '20240408')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    if not fid_unas_input_iscd:
        logger.error("fid_unas_input_iscd is required. (e.g. '000000')")
        raise ValueError("fid_unas_input_iscd is required. (e.g. '000000')")
    if not fid_input_iscd_2:
        logger.error("fid_input_iscd_2 is required. (e.g. '00000')")
        raise ValueError("fid_input_iscd_2 is required. (e.g. '00000')")
    if not fid_blng_cls_code:
        logger.error("fid_blng_cls_code is required. (e.g. '0')")
        raise ValueError("fid_blng_cls_code is required. (e.g. '0')")
    tr_id = 'FHKEW154700C0'
    api_url = '/uapi/elw/v1/quotations/expiration-stocks'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_ETC_CLS_CODE': fid_etc_cls_code, 'FID_UNAS_INPUT_ISCD': fid_unas_input_iscd, 'FID_INPUT_ISCD_2': fid_input_iscd_2, 'FID_BLNG_CLS_CODE': fid_blng_cls_code, 'FID_INPUT_OPTION_1': fid_input_option_1}
    return ApiRequest('elw.expiration_stocks', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def indicator(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_unas_input_iscd, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_rank_sort_cls_code, fid_blng_cls_code, tr_cont=''):
    """KIS elw.indicator 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (필수)
fid_cond_scr_div_code (str): 조건화면분류코드 (필수)
fid_unas_input_iscd (str): 기초자산입력종목코드 (필수)
fid_input_iscd (str): 발행사 (필수)
fid_div_cls_code (str): 콜풋구분코드 (필수)
fid_input_price_1 (str): 가격(이상) (필수)
fid_input_price_2 (str): 가격(이하) (필수)
fid_input_vol_1 (str): 거래량(이상) (필수)
fid_input_vol_2 (str): 거래량(이하) (필수)
fid_rank_sort_cls_code (str): 순위정렬구분코드 (필수)
fid_blng_cls_code (str): 결재방법 (필수)
tr_cont (str): 연속 거래 여부 (옵션)"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20279')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20279')")
    if not fid_unas_input_iscd:
        logger.error("fid_unas_input_iscd is required. (e.g. '000000')")
        raise ValueError("fid_unas_input_iscd is required. (e.g. '000000')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '00000')")
        raise ValueError("fid_input_iscd is required. (e.g. '00000')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '0')")
    if not fid_blng_cls_code:
        logger.error("fid_blng_cls_code is required. (e.g. '0')")
        raise ValueError("fid_blng_cls_code is required. (e.g. '0')")
    tr_id = 'FHPEW02790000'
    api_url = '/uapi/elw/v1/ranking/indicator'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_UNAS_INPUT_ISCD': fid_unas_input_iscd, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_INPUT_VOL_1': fid_input_vol_1, 'FID_INPUT_VOL_2': fid_input_vol_2, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_BLNG_CLS_CODE': fid_blng_cls_code}
    return ApiRequest('elw.indicator', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def indicator_trend_ccnl(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS elw.indicator_trend_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (필수)
fid_input_iscd (str): 입력종목코드 (필수)
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '58J297')")
        raise ValueError("fid_input_iscd is required. (e.g. '58J297')")
    tr_id = 'FHPEW02740100'
    api_url = '/uapi/elw/v1/quotations/indicator-trend-ccnl'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('elw.indicator_trend_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def indicator_trend_daily(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS elw.indicator_trend_daily 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 시장 분류 코드 (예: 'W')
fid_input_iscd (str): 종목코드 (6자리, 예: '57K281')
tr_cont (str): 연속 거래 여부"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '57K281')")
        raise ValueError("fid_input_iscd is required. (e.g. '57K281')")
    tr_id = 'FHPEW02740200'
    api_url = '/uapi/elw/v1/quotations/indicator-trend-daily'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('elw.indicator_trend_daily', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def indicator_trend_minute(fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code, fid_pw_data_incu_yn, tr_cont=''):
    """KIS elw.indicator_trend_minute 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 시장구분코드 (W)
fid_input_iscd (str): 입력종목코드 예시: 58J297(KBJ297삼성전자콜)
fid_hour_cls_code (str): 시간구분코드 예시: '60(1분), 180(3분), 300(5분), 600(10분), 1800(30분), 3600(60분), 7200(60분)'
fid_pw_data_incu_yn (str): 과거데이터 포함 여부 예시: N(과거데이터포함X), Y(과거데이터포함O)
tr_cont (str): 연속 거래 여부"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '58J297')")
        raise ValueError("fid_input_iscd is required. (e.g. '58J297')")
    if not fid_hour_cls_code:
        logger.error("fid_hour_cls_code is required. (e.g. '60')")
        raise ValueError("fid_hour_cls_code is required. (e.g. '60')")
    if not fid_pw_data_incu_yn:
        logger.error("fid_pw_data_incu_yn is required. (e.g. 'N')")
        raise ValueError("fid_pw_data_incu_yn is required. (e.g. 'N')")
    tr_id = 'FHPEW02740300'
    api_url = '/uapi/elw/v1/quotations/indicator-trend-minute'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_HOUR_CLS_CODE': fid_hour_cls_code, 'FID_PW_DATA_INCU_YN': fid_pw_data_incu_yn}
    return ApiRequest('elw.indicator_trend_minute', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def lp_trade_trend(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS elw.lp_trade_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 시장구분(W)
fid_input_iscd (str): 입력종목코드(ex 52K577(미래 K577KOSDAQ150콜)
tr_cont (str): 연속 거래 여부"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '52K577')")
        raise ValueError("fid_input_iscd is required. (e.g. '52K577')")
    tr_id = 'FHPEW03760000'
    api_url = '/uapi/elw/v1/quotations/lp-trade-trend'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('elw.lp_trade_trend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def newly_listed(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_unas_input_iscd, fid_input_iscd_2, fid_input_date_1, fid_blng_cls_code, tr_cont=''):
    """KIS elw.newly_listed 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 시장구분코드 (W)
fid_cond_scr_div_code (str): Unique key(11548)
fid_div_cls_code (str): 전체(02), 콜(00), 풋(01)
fid_unas_input_iscd (str): 'ex) 000000(전체), 2001(코스피200) , 3003(코스닥150), 005930(삼성전자) '
fid_input_iscd_2 (str): '00003(한국투자증권), 00017(KB증권),  00005(미래에셋증권)'
fid_input_date_1 (str): 날짜 (ex) 20240402)
fid_blng_cls_code (str): 0(전체), 1(일반), 2(조기종료)
tr_cont (str): 연속 거래 여부"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '11548')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '11548')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '02')")
        raise ValueError("fid_div_cls_code is required. (e.g. '02')")
    if not fid_unas_input_iscd:
        logger.error("fid_unas_input_iscd is required. (e.g. '000000')")
        raise ValueError("fid_unas_input_iscd is required. (e.g. '000000')")
    if not fid_input_iscd_2:
        logger.error("fid_input_iscd_2 is required. (e.g. '00003')")
        raise ValueError("fid_input_iscd_2 is required. (e.g. '00003')")
    if not fid_input_date_1:
        logger.error("fid_input_date_1 is required. (e.g. '20240402')")
        raise ValueError("fid_input_date_1 is required. (e.g. '20240402')")
    if not fid_blng_cls_code:
        logger.error("fid_blng_cls_code is required. (e.g. '0')")
        raise ValueError("fid_blng_cls_code is required. (e.g. '0')")
    tr_id = 'FHKEW154800C0'
    api_url = '/uapi/elw/v1/quotations/newly-listed'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_UNAS_INPUT_ISCD': fid_unas_input_iscd, 'FID_INPUT_ISCD_2': fid_input_iscd_2, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_BLNG_CLS_CODE': fid_blng_cls_code}
    return ApiRequest('elw.newly_listed', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def quick_change(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_unas_input_iscd, fid_input_iscd, fid_mrkt_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_hour_cls_code, fid_input_hour_1, fid_input_hour_2, fid_rank_sort_cls_code, fid_blng_cls_code, tr_cont=''):
    """KIS elw.quick_change 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (필수)
fid_cond_scr_div_code (str): 조건화면분류코드 (필수)
fid_unas_input_iscd (str): 기초자산입력종목코드 (필수)
fid_input_iscd (str): 발행사 (필수)
fid_mrkt_cls_code (str): 시장구분코드 (필수)
fid_input_price_1 (str): 가격(이상) (필수)
fid_input_price_2 (str): 가격(이하) (필수)
fid_input_vol_1 (str): 거래량(이상) (필수)
fid_input_vol_2 (str): 거래량(이하) (필수)
fid_hour_cls_code (str): 시간구분코드 (필수)
fid_input_hour_1 (str): 입력 일 또는 분 (필수)
fid_input_hour_2 (str): 기준시간(분 선택 시) (필수)
fid_rank_sort_cls_code (str): 순위정렬구분코드 (필수)
fid_blng_cls_code (str): 결재방법 (필수)
tr_cont (str): 연속 거래 여부 (옵션)"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20287')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20287')")
    if not fid_unas_input_iscd:
        logger.error("fid_unas_input_iscd is required. (e.g. '000000')")
        raise ValueError("fid_unas_input_iscd is required. (e.g. '000000')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '00000')")
        raise ValueError("fid_input_iscd is required. (e.g. '00000')")
    if not fid_mrkt_cls_code:
        logger.error("fid_mrkt_cls_code is required. (e.g. 'A')")
        raise ValueError("fid_mrkt_cls_code is required. (e.g. 'A')")
    if not fid_hour_cls_code:
        logger.error("fid_hour_cls_code is required. (e.g. '1')")
        raise ValueError("fid_hour_cls_code is required. (e.g. '1')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '1')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '1')")
    if not fid_blng_cls_code:
        logger.error("fid_blng_cls_code is required. (e.g. '0')")
        raise ValueError("fid_blng_cls_code is required. (e.g. '0')")
    tr_id = 'FHPEW02870000'
    api_url = '/uapi/elw/v1/ranking/quick-change'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_UNAS_INPUT_ISCD': fid_unas_input_iscd, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_MRKT_CLS_CODE': fid_mrkt_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_INPUT_VOL_1': fid_input_vol_1, 'FID_INPUT_VOL_2': fid_input_vol_2, 'FID_HOUR_CLS_CODE': fid_hour_cls_code, 'FID_INPUT_HOUR_1': fid_input_hour_1, 'FID_INPUT_HOUR_2': fid_input_hour_2, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_BLNG_CLS_CODE': fid_blng_cls_code}
    return ApiRequest('elw.quick_change', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def sensitivity(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_unas_input_iscd, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_rank_sort_cls_code, fid_input_rmnn_dynu_1, fid_input_date_1, fid_blng_cls_code, tr_cont=''):
    """KIS elw.sensitivity 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드
fid_cond_scr_div_code (str): 조건화면분류코드
fid_unas_input_iscd (str): 기초자산입력종목코드
fid_input_iscd (str): 입력종목코드
fid_div_cls_code (str): 콜풋구분코드
fid_input_price_1 (str): 가격(이상)
fid_input_price_2 (str): 가격(이하)
fid_input_vol_1 (str): 거래량(이상)
fid_input_vol_2 (str): 거래량(이하)
fid_rank_sort_cls_code (str): 순위정렬구분코드
fid_input_rmnn_dynu_1 (str): 잔존일수(이상)
fid_input_date_1 (str): 조회기준일
fid_blng_cls_code (str): 결재방법
tr_cont (str): 연속 거래 여부"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20285')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20285')")
    if not fid_unas_input_iscd:
        logger.error("fid_unas_input_iscd is required. (e.g. '000000')")
        raise ValueError("fid_unas_input_iscd is required. (e.g. '000000')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '00000')")
        raise ValueError("fid_input_iscd is required. (e.g. '00000')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '0')")
    if not fid_blng_cls_code:
        logger.error("fid_blng_cls_code is required. (e.g. '0')")
        raise ValueError("fid_blng_cls_code is required. (e.g. '0')")
    tr_id = 'FHPEW02850000'
    api_url = '/uapi/elw/v1/ranking/sensitivity'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_UNAS_INPUT_ISCD': fid_unas_input_iscd, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_INPUT_VOL_1': fid_input_vol_1, 'FID_INPUT_VOL_2': fid_input_vol_2, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_INPUT_RMNN_DYNU_1': fid_input_rmnn_dynu_1, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_BLNG_CLS_CODE': fid_blng_cls_code}
    return ApiRequest('elw.sensitivity', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def sensitivity_trend_ccnl(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS elw.sensitivity_trend_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (필수)
fid_input_iscd (str): 입력종목코드 (필수)
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '58J297')")
        raise ValueError("fid_input_iscd is required. (e.g. '58J297')")
    tr_id = 'FHPEW02830100'
    api_url = '/uapi/elw/v1/quotations/sensitivity-trend-ccnl'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('elw.sensitivity_trend_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def sensitivity_trend_daily(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS elw.sensitivity_trend_daily 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (필수)
fid_input_iscd (str): 입력종목코드 (필수)
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '58J438')")
        raise ValueError("fid_input_iscd is required. (e.g. '58J438')")
    tr_id = 'FHPEW02830200'
    api_url = '/uapi/elw/v1/quotations/sensitivity-trend-daily'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('elw.sensitivity_trend_daily', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def udrl_asset_list(fid_cond_scr_div_code, fid_rank_sort_cls_code, fid_input_iscd, tr_cont=''):
    """KIS elw.udrl_asset_list 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_scr_div_code (str): 조건화면분류코드, 예: '11541'
fid_rank_sort_cls_code (str): 순위정렬구분코드, 예: '0', '1', '2', '3', '4', '5', '6'
fid_input_iscd (str): 입력종목코드, 예: '00000', '00003', '00017', '00005'
tr_cont (str): 연속 거래 여부, 기본값은 공백"""
    logger = logging.getLogger(__name__)
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '11541')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '11541')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '0')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '00000')")
        raise ValueError("fid_input_iscd is required. (e.g. '00000')")
    tr_id = 'FHKEW154100C0'
    api_url = '/uapi/elw/v1/quotations/udrl-asset-list'
    params = {'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('elw.udrl_asset_list', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def udrl_asset_price(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_mrkt_cls_code, fid_input_iscd, fid_unas_input_iscd, fid_vol_cnt, fid_trgt_exls_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_input_rmnn_dynu_1, fid_input_rmnn_dynu_2, fid_option, fid_input_option_1, fid_input_option_2, tr_cont=''):
    """KIS elw.udrl_asset_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 시장구분(W)
fid_cond_scr_div_code (str): Uniquekey(11541)
fid_mrkt_cls_code (str): 전체(A),콜(C),풋(P)
fid_input_iscd (str): '00000(전체), 00003(한국투자증권) , 00017(KB증권), 00005(미래에셋주식회사)'
fid_unas_input_iscd (str): 기초자산입력종목코드
fid_vol_cnt (str): 전일거래량(정수량미만)
fid_trgt_exls_cls_code (str): 거래불가종목제외(0:미체크,1:체크)
fid_input_price_1 (str): 가격~원이상
fid_input_price_2 (str): 가격~월이하
fid_input_vol_1 (str): 거래량~계약이상
fid_input_vol_2 (str): 거래량~계약이하
fid_input_rmnn_dynu_1 (str): 잔존일(~일이상)
fid_input_rmnn_dynu_2 (str): 잔존일(~일이하)
fid_option (str): 옵션상태(0:없음,1:ATM,2:ITM,3:OTM)
fid_input_option_1 (str): 입력옵션1
fid_input_option_2 (str): 입력옵션2
tr_cont (str): 연속 거래 여부"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '11541')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '11541')")
    if not fid_mrkt_cls_code:
        logger.error("fid_mrkt_cls_code is required. (e.g. 'A')")
        raise ValueError("fid_mrkt_cls_code is required. (e.g. 'A')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '00000')")
        raise ValueError("fid_input_iscd is required. (e.g. '00000')")
    if not fid_unas_input_iscd:
        logger.error("fid_unas_input_iscd is required. (e.g. '00001')")
        raise ValueError("fid_unas_input_iscd is required. (e.g. '00001')")
    if not fid_trgt_exls_cls_code:
        logger.error("fid_trgt_exls_cls_code is required. (e.g. '0')")
        raise ValueError("fid_trgt_exls_cls_code is required. (e.g. '0')")
    if not fid_option:
        logger.error("fid_option is required. (e.g. '0')")
        raise ValueError("fid_option is required. (e.g. '0')")
    tr_id = 'FHKEW154101C0'
    api_url = '/uapi/elw/v1/quotations/udrl-asset-price'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_MRKT_CLS_CODE': fid_mrkt_cls_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_UNAS_INPUT_ISCD': fid_unas_input_iscd, 'FID_VOL_CNT': fid_vol_cnt, 'FID_TRGT_EXLS_CLS_CODE': fid_trgt_exls_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_INPUT_VOL_1': fid_input_vol_1, 'FID_INPUT_VOL_2': fid_input_vol_2, 'FID_INPUT_RMNN_DYNU_1': fid_input_rmnn_dynu_1, 'FID_INPUT_RMNN_DYNU_2': fid_input_rmnn_dynu_2, 'FID_OPTION': fid_option, 'FID_INPUT_OPTION_1': fid_input_option_1, 'FID_INPUT_OPTION_2': fid_input_option_2}
    return ApiRequest('elw.udrl_asset_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def updown_rate(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_unas_input_iscd, fid_input_iscd, fid_input_rmnn_dynu_1, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_input_date_1, fid_rank_sort_cls_code, fid_blng_cls_code, fid_input_date_2, tr_cont=''):
    """KIS elw.updown_rate 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 시장구분코드 (W)
fid_cond_scr_div_code (str): Unique key(20277)
fid_unas_input_iscd (str): '000000(전체), 2001(코스피200) , 3003(코스닥150), 005930(삼성전자) '
fid_input_iscd (str): '00000(전체), 00003(한국투자증권) , 00017(KB증권), 00005(미래에셋주식회사)'
fid_input_rmnn_dynu_1 (str): '0(전체), 1(1개월이하), 2(1개월~2개월),  3(2개월~3개월), 4(3개월~6개월), 5(6개월~9개월),6(9개월~12개월), 7(12개월이상)'
fid_div_cls_code (str): 0(전체), 1(콜), 2(풋)
fid_input_price_1 (str):
fid_input_price_2 (str):
fid_input_vol_1 (str):
fid_input_vol_2 (str):
fid_input_date_1 (str):
fid_rank_sort_cls_code (str): '0(상승율), 1(하락율), 2(시가대비상승율) , 3(시가대비하락율), 4(변동율)'
fid_blng_cls_code (str): 0(전체)
fid_input_date_2 (str):
tr_cont (str): 연속 거래 여부"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20277')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20277')")
    if not fid_unas_input_iscd:
        logger.error("fid_unas_input_iscd is required. (e.g. '000000')")
        raise ValueError("fid_unas_input_iscd is required. (e.g. '000000')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '00000')")
        raise ValueError("fid_input_iscd is required. (e.g. '00000')")
    if not fid_input_rmnn_dynu_1:
        logger.error("fid_input_rmnn_dynu_1 is required. (e.g. '0')")
        raise ValueError("fid_input_rmnn_dynu_1 is required. (e.g. '0')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '0')")
    if not fid_blng_cls_code:
        logger.error("fid_blng_cls_code is required. (e.g. '0')")
        raise ValueError("fid_blng_cls_code is required. (e.g. '0')")
    tr_id = 'FHPEW02770000'
    api_url = '/uapi/elw/v1/ranking/updown-rate'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_UNAS_INPUT_ISCD': fid_unas_input_iscd, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_RMNN_DYNU_1': fid_input_rmnn_dynu_1, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_INPUT_VOL_1': fid_input_vol_1, 'FID_INPUT_VOL_2': fid_input_vol_2, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_BLNG_CLS_CODE': fid_blng_cls_code, 'FID_INPUT_DATE_2': fid_input_date_2}
    return ApiRequest('elw.updown_rate', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def volatility_trend_ccnl(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS elw.volatility_trend_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (필수)
fid_input_iscd (str): 입력종목코드 (필수)
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '58J297')")
        raise ValueError("fid_input_iscd is required. (e.g. '58J297')")
    tr_id = 'FHPEW02840100'
    api_url = '/uapi/elw/v1/quotations/volatility-trend-ccnl'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('elw.volatility_trend_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def volatility_trend_daily(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS elw.volatility_trend_daily 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (예: 'W')
fid_input_iscd (str): 입력종목코드 (예: '58J297')
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '58J297')")
        raise ValueError("fid_input_iscd is required. (e.g. '58J297')")
    tr_id = 'FHPEW02840200'
    api_url = '/uapi/elw/v1/quotations/volatility-trend-daily'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('elw.volatility_trend_daily', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def volatility_trend_minute(fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code, fid_pw_data_incu_yn, tr_cont=''):
    """KIS elw.volatility_trend_minute 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (예: 'W')
fid_input_iscd (str): 입력종목코드 (예: '58J297')
fid_hour_cls_code (str): 시간구분코드 (예: '60', '180', '300', '600', '1800', '3600')
fid_pw_data_incu_yn (str): 과거데이터 포함 여부 ('N' 또는 'Y')
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '58J297')")
        raise ValueError("fid_input_iscd is required. (e.g. '58J297')")
    if not fid_hour_cls_code:
        logger.error("fid_hour_cls_code is required. (e.g. '60')")
        raise ValueError("fid_hour_cls_code is required. (e.g. '60')")
    if not fid_pw_data_incu_yn:
        logger.error("fid_pw_data_incu_yn is required. (e.g. 'N')")
        raise ValueError("fid_pw_data_incu_yn is required. (e.g. 'N')")
    tr_id = 'FHPEW02840300'
    api_url = '/uapi/elw/v1/quotations/volatility-trend-minute'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_HOUR_CLS_CODE': fid_hour_cls_code, 'FID_PW_DATA_INCU_YN': fid_pw_data_incu_yn}
    return ApiRequest('elw.volatility_trend_minute', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def volatility_trend_tick(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS elw.volatility_trend_tick 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (예: 'W')
fid_input_iscd (str): 입력종목코드 (예: '58J297')
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '58J297')")
        raise ValueError("fid_input_iscd is required. (e.g. '58J297')")
    tr_id = 'FHPEW02840400'
    api_url = '/uapi/elw/v1/quotations/volatility-trend-tick'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('elw.volatility_trend_tick', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def volume_rank(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_unas_input_iscd, fid_input_iscd, fid_input_rmnn_dynu_1, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_input_date_1, fid_rank_sort_cls_code, fid_blng_cls_code, fid_input_iscd_2, fid_input_date_2, tr_cont=''):
    """KIS elw.volume_rank 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (예: 'W')
fid_cond_scr_div_code (str): 조건화면분류코드 (예: '20278')
fid_unas_input_iscd (str): 기초자산입력종목코드 (예: '000000')
fid_input_iscd (str): 발행사 (예: '00000')
fid_input_rmnn_dynu_1 (str): 입력잔존일수
fid_div_cls_code (str): 콜풋구분코드 (예: '0')
fid_input_price_1 (str): 가격(이상)
fid_input_price_2 (str): 가격(이하)
fid_input_vol_1 (str): 거래량(이상)
fid_input_vol_2 (str): 거래량(이하)
fid_input_date_1 (str): 조회기준일
fid_rank_sort_cls_code (str): 순위정렬구분코드 (예: '0')
fid_blng_cls_code (str): 소속구분코드 (예: '0')
fid_input_iscd_2 (str): LP발행사 (예: '0000')
fid_input_date_2 (str): 만기일-최종거래일조회
tr_cont (str): 연속 거래 여부"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20278')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20278')")
    if not fid_unas_input_iscd:
        logger.error("fid_unas_input_iscd is required. (e.g. '000000')")
        raise ValueError("fid_unas_input_iscd is required. (e.g. '000000')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '00000')")
        raise ValueError("fid_input_iscd is required. (e.g. '00000')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '0')")
    if not fid_blng_cls_code:
        logger.error("fid_blng_cls_code is required. (e.g. '0')")
        raise ValueError("fid_blng_cls_code is required. (e.g. '0')")
    if not fid_input_iscd_2:
        logger.error("fid_input_iscd_2 is required. (e.g. '0000')")
        raise ValueError("fid_input_iscd_2 is required. (e.g. '0000')")
    tr_id = 'FHPEW02780000'
    api_url = '/uapi/elw/v1/ranking/volume-rank'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_UNAS_INPUT_ISCD': fid_unas_input_iscd, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_RMNN_DYNU_1': fid_input_rmnn_dynu_1, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_INPUT_VOL_1': fid_input_vol_1, 'FID_INPUT_VOL_2': fid_input_vol_2, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_BLNG_CLS_CODE': fid_blng_cls_code, 'FID_INPUT_ISCD_2': fid_input_iscd_2, 'FID_INPUT_DATE_2': fid_input_date_2}
    return ApiRequest('elw.volume_rank', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)
