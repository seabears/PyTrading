"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def after_hour_balance(fid_input_price_1, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_rank_sort_cls_code, fid_div_cls_code, fid_input_iscd, fid_trgt_exls_cls_code, fid_trgt_cls_code, fid_vol_cnt, fid_input_price_2, tr_cont=''):
    """KIS domestic_stock.after_hour_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_input_price_1 (str): 입력값 없을때 전체 (가격 ~)
fid_cond_mrkt_div_code (str): 시장구분코드 (주식 J)
fid_cond_scr_div_code (str): Unique key( 20176 )
fid_rank_sort_cls_code (str): 1: 장전 시간외, 2: 장후 시간외, 3:매도잔량, 4:매수잔량
fid_div_cls_code (str): 0 : 전체
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200
fid_trgt_exls_cls_code (str): 0 : 전체
fid_trgt_cls_code (str): 0 : 전체
fid_vol_cnt (str): 입력값 없을때 전체 (거래량 ~)
fid_input_price_2 (str): 입력값 없을때 전체 (~ 가격)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/after-hour-balance'
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20176')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20176')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '1')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '1')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0000')")
        raise ValueError("fid_input_iscd is required. (e.g. '0000')")
    tr_id = 'FHPST01760000'
    params = {'fid_input_price_1': fid_input_price_1, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_rank_sort_cls_code': fid_rank_sort_cls_code, 'fid_div_cls_code': fid_div_cls_code, 'fid_input_iscd': fid_input_iscd, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_vol_cnt': fid_vol_cnt, 'fid_input_price_2': fid_input_price_2}
    return ApiRequest('domestic_stock.after_hour_balance', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def bulk_trans_num(fid_aply_rang_prc_2, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_div_cls_code, fid_input_price_1, fid_aply_rang_prc_1, fid_input_iscd_2, fid_trgt_exls_cls_code, fid_trgt_cls_code, fid_vol_cnt, tr_cont=''):
    """KIS domestic_stock.bulk_trans_num 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_aply_rang_prc_2 (str): ~ 가격
fid_cond_mrkt_div_code (str): 시장구분코드 (J:KRX, NX:NXT)
fid_cond_scr_div_code (str): Unique key(11909)
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200, 4001: KRX100
fid_rank_sort_cls_code (str): 0:매수상위, 1:매도상위
fid_div_cls_code (str): 0:전체
fid_input_price_1 (str): 건별금액 ~
fid_aply_rang_prc_1 (str): 가격 ~
fid_input_iscd_2 (str): 공백:전체종목, 개별종목 조회시 종목코드 (000660)
fid_trgt_exls_cls_code (str): 0:전체
fid_trgt_cls_code (str): 0:전체
fid_vol_cnt (str): 거래량 ~
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/bulk-trans-num'
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '11909')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '11909')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0000')")
        raise ValueError("fid_input_iscd is required. (e.g. '0000')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '0')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    if not fid_trgt_exls_cls_code:
        logger.error("fid_trgt_exls_cls_code is required. (e.g. '0')")
        raise ValueError("fid_trgt_exls_cls_code is required. (e.g. '0')")
    if not fid_trgt_cls_code:
        logger.error("fid_trgt_cls_code is required. (e.g. '0')")
        raise ValueError("fid_trgt_cls_code is required. (e.g. '0')")
    tr_id = 'FHKST190900C0'
    params = {'fid_aply_rang_prc_2': fid_aply_rang_prc_2, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_input_iscd': fid_input_iscd, 'fid_rank_sort_cls_code': fid_rank_sort_cls_code, 'fid_div_cls_code': fid_div_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_aply_rang_prc_1': fid_aply_rang_prc_1, 'fid_input_iscd_2': fid_input_iscd_2, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_vol_cnt': fid_vol_cnt}
    return ApiRequest('domestic_stock.bulk_trans_num', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def capture_uplowprice(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_prc_cls_code, fid_div_cls_code, fid_input_iscd, fid_trgt_cls_code='', fid_trgt_exls_cls_code='', fid_input_price_1='', fid_input_price_2='', fid_vol_cnt=''):
    """KIS domestic_stock.capture_uplowprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건시장분류코드 (ex. J:주식)
fid_cond_scr_div_code (str): [필수] 조건화면분류코드 (ex. 11300)
fid_prc_cls_code (str): [필수] 상하한가 구분코드 (ex. 0:상한가, 1:하한가)
fid_div_cls_code (str): [필수] 분류구분코드 (ex. 0:상하한가종목, 6:8%상하한가 근접, 5:10%상하한가 근접, 1:15%상하한가 근접, 2:20%상하한가 근접, 3:25%상하한가 근접)
fid_input_iscd (str): [필수] 입력종목코드 (ex. 0000:전체, 0001:코스피, 1001:코스닥)
fid_trgt_cls_code (str): 대상구분코드
fid_trgt_exls_cls_code (str): 대상제외구분코드
fid_input_price_1 (str): 입력가격1
fid_input_price_2 (str): 입력가격2
fid_vol_cnt (str): 거래량수"""
    api_url = '/uapi/domestic-stock/v1/quotations/capture-uplowprice'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '11300')")
    if fid_prc_cls_code == '':
        raise ValueError("fid_prc_cls_code is required (e.g. '0', '1')")
    if fid_div_cls_code == '':
        raise ValueError("fid_div_cls_code is required (e.g. '0', '6', '5', '1', '2', '3')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '0000', '0001', '1001')")
    tr_id = 'FHKST130000C0'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_PRC_CLS_CODE': fid_prc_cls_code, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_TRGT_CLS_CODE': fid_trgt_cls_code, 'FID_TRGT_EXLS_CLS_CODE': fid_trgt_exls_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_VOL_CNT': fid_vol_cnt}
    return ApiRequest('domestic_stock.capture_uplowprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def chk_holiday(bass_dt, NK100='', FK100='', tr_cont=''):
    """KIS domestic_stock.chk_holiday 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
bass_dt (str): [필수] 기준일자 (ex. YYYYMMDD)
NK100 (str): 연속조회키
FK100 (str): 연속조회검색조건
tr_cont (str): 연속거래여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/chk-holiday'
    if bass_dt == '':
        raise ValueError("bass_dt is required (e.g. 'YYYYMMDD')")
    tr_id = 'CTCA0903R'
    params = {'BASS_DT': bass_dt, 'CTX_AREA_FK': FK100, 'CTX_AREA_NK': NK100}
    return ApiRequest('domestic_stock.chk_holiday', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def comp_interest(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_div_cls_code1, tr_cont=''):
    """KIS domestic_stock.comp_interest 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (필수)
fid_cond_scr_div_code (str): 조건화면분류코드 (필수)
fid_div_cls_code (str): 분류구분코드 (필수)
fid_div_cls_code1 (str): 분류구분코드 (공백 허용)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/comp-interest'
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. '01')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. '01')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20702')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20702')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '1')")
        raise ValueError("fid_div_cls_code is required. (e.g. '1')")
    tr_id = 'FHPST07020000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_DIV_CLS_CODE1': fid_div_cls_code1}
    return ApiRequest('domestic_stock.comp_interest', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def comp_program_trade_daily(fid_cond_mrkt_div_code, fid_mrkt_cls_code, fid_input_date_1='', fid_input_date_2=''):
    """KIS domestic_stock.comp_program_trade_daily 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건시장분류코드 (ex. J:주식,NX:NXT,UN:통합)
fid_mrkt_cls_code (str): [필수] 시장구분코드 (ex. K:코스피,Q:코스닥)
fid_input_date_1 (str): 검색시작일
fid_input_date_2 (str): 검색종료일"""
    api_url = '/uapi/domestic-stock/v1/quotations/comp-program-trade-daily'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:주식,NX:NXT,UN:통합')")
    if fid_mrkt_cls_code == '':
        raise ValueError("fid_mrkt_cls_code is required (e.g. 'K:코스피,Q:코스닥')")
    tr_id = 'FHPPG04600001'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_MRKT_CLS_CODE': fid_mrkt_cls_code, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2}
    return ApiRequest('domestic_stock.comp_program_trade_daily', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def comp_program_trade_today(fid_cond_mrkt_div_code, fid_mrkt_cls_code, fid_sctn_cls_code='', fid_input_iscd='', fid_cond_mrkt_div_code1='', fid_input_hour_1=''):
    """KIS domestic_stock.comp_program_trade_today 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 시장 구분 코드 (ex. J:KRX,NX:NXT,UN:통합)
fid_mrkt_cls_code (str): [필수] 시장구분코드 (ex. K:코스피, Q:코스닥)
fid_sctn_cls_code (str): 구간 구분 코드
fid_input_iscd (str): 입력종목코드
fid_cond_mrkt_div_code1 (str): 시장분류코드
fid_input_hour_1 (str): 입력시간"""
    api_url = '/uapi/domestic-stock/v1/quotations/comp-program-trade-today'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX,NX:NXT,UN:통합')")
    if fid_mrkt_cls_code == '':
        raise ValueError("fid_mrkt_cls_code is required (e.g. 'K:코스피, Q:코스닥')")
    tr_id = 'FHPPG04600101'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_MRKT_CLS_CODE': fid_mrkt_cls_code, 'FID_SCTN_CLS_CODE': fid_sctn_cls_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_COND_MRKT_DIV_CODE1': fid_cond_mrkt_div_code1, 'FID_INPUT_HOUR_1': fid_input_hour_1}
    return ApiRequest('domestic_stock.comp_program_trade_today', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def daily_short_sale(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1='', fid_input_date_2=''):
    """KIS domestic_stock.daily_short_sale 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 시장분류코드 (ex. J:주식)
fid_input_iscd (str): [필수] 종목코드 (ex. 123456)
fid_input_date_1 (str): 시작일자
fid_input_date_2 (str): 종료일자"""
    api_url = '/uapi/domestic-stock/v1/quotations/daily-short-sale'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:주식')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    tr_id = 'FHPST04830000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2}
    return ApiRequest('domestic_stock.daily_short_sale', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def disparity(fid_input_price_2, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_rank_sort_cls_code, fid_hour_cls_code, fid_input_iscd, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_vol_cnt, tr_cont=''):
    """KIS domestic_stock.disparity 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_input_price_2 (str): 입력값 없을때 전체 (~ 가격)
fid_cond_mrkt_div_code (str): 시장구분코드 (ex. J:KRX, NX:NXT)
fid_cond_scr_div_code (str): Unique key( 20178 )
fid_div_cls_code (str): 0: 전체, 1:관리종목, 2:투자주의, 3:투자경고, 4:투자위험예고, 5:투자위험, 6:보톧주, 7:우선주
fid_rank_sort_cls_code (str): 0: 이격도상위순, 1:이격도하위순
fid_hour_cls_code (str): 5:이격도5, 10:이격도10, 20:이격도20, 60:이격도60, 120:이격도120
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200
fid_trgt_cls_code (str): 0 : 전체
fid_trgt_exls_cls_code (str): 0 : 전체
fid_input_price_1 (str): 입력값 없을때 전체 (가격 ~)
fid_vol_cnt (str): 입력값 없을때 전체 (거래량 ~)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/disparity'
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20178')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20178')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '0')")
    if not fid_hour_cls_code:
        logger.error("fid_hour_cls_code is required. (e.g. '5')")
        raise ValueError("fid_hour_cls_code is required. (e.g. '5')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0000')")
        raise ValueError("fid_input_iscd is required. (e.g. '0000')")
    tr_id = 'FHPST01780000'
    params = {'fid_input_price_2': fid_input_price_2, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_div_cls_code': fid_div_cls_code, 'fid_rank_sort_cls_code': fid_rank_sort_cls_code, 'fid_hour_cls_code': fid_hour_cls_code, 'fid_input_iscd': fid_input_iscd, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_vol_cnt': fid_vol_cnt}
    return ApiRequest('domestic_stock.disparity', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def dividend_rate(cts_area, gb1, upjong, gb2, gb3, f_dt, t_dt, gb4, tr_cont=''):
    """KIS domestic_stock.dividend_rate 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cts_area (str): 공백
gb1 (str): 0:전체, 1:코스피,  2: 코스피200, 3: 코스닥,
upjong (str): '코스피(0001:종합, 0002:대형주.…0027:제조업 ),  코스닥(1001:종합, …. 1041:IT부품 코스피200 (2001:KOSPI200, 2007:KOSPI100, 2008:KOSPI50)'
gb2 (str): 0:전체, 6:보통주, 7:우선주
gb3 (str): 1:주식배당, 2: 현금배당
f_dt (str): 기준일 시작
t_dt (str): 기준일 종료
gb4 (str): 0:전체, 1:결산배당, 2:중간배당
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/dividend-rate'
    if not gb1:
        logger.error("gb1 is required. (e.g. '1')")
        raise ValueError("gb1 is required. (e.g. '1')")
    if not upjong:
        logger.error("upjong is required. (e.g. '0001')")
        raise ValueError("upjong is required. (e.g. '0001')")
    if not gb2:
        logger.error("gb2 is required. (e.g. '0')")
        raise ValueError("gb2 is required. (e.g. '0')")
    if not gb3:
        logger.error("gb3 is required. (e.g. '1')")
        raise ValueError("gb3 is required. (e.g. '1')")
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20230101')")
        raise ValueError("f_dt is required. (e.g. '20230101')")
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231231')")
        raise ValueError("t_dt is required. (e.g. '20231231')")
    if not gb4:
        logger.error("gb4 is required. (e.g. '0')")
        raise ValueError("gb4 is required. (e.g. '0')")
    tr_id = 'HHKDB13470100'
    params = {'CTS_AREA': cts_area, 'GB1': gb1, 'UPJONG': upjong, 'GB2': gb2, 'GB3': gb3, 'F_DT': f_dt, 'T_DT': t_dt, 'GB4': gb4}
    return ApiRequest('domestic_stock.dividend_rate', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def estimate_perform(sht_cd, tr_cont=''):
    """KIS domestic_stock.estimate_perform 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
sht_cd (str): 종목코드 (예: 265520)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/estimate-perform'
    if not sht_cd:
        logger.error("sht_cd is required. (e.g. '265520')")
        raise ValueError("sht_cd is required. (e.g. '265520')")
    tr_id = 'HHKST668300C0'
    params = {'SHT_CD': sht_cd}
    return ApiRequest('domestic_stock.estimate_perform', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def exp_closing_price(fid_cond_mrkt_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_cond_scr_div_code, fid_blng_cls_code):
    """KIS domestic_stock.exp_closing_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건시장분류코드 (ex. J:주식)
fid_input_iscd (str): [필수] 입력종목코드 (ex. 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200, 4001: KRX100)
fid_rank_sort_cls_code (str): [필수] 순위정렬구분코드 (ex. 0:전체, 1:상한가마감예상, 2:하한가마감예상, 3:직전대비상승률상위, 4:직전대비하락률상위)
fid_cond_scr_div_code (str): [필수] 조건화면분류코드 (ex. 11173)
fid_blng_cls_code (str): [필수] 소속구분코드 (ex. 0:전체, 1:종가범위연장)"""
    api_url = '/uapi/domestic-stock/v1/quotations/exp-closing-price'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '0000', '0001', '1001', '2001', '4001')")
    if fid_rank_sort_cls_code == '':
        raise ValueError("fid_rank_sort_cls_code is required (e.g. '0', '1', '2', '3', '4')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '11173')")
    if fid_blng_cls_code == '':
        raise ValueError("fid_blng_cls_code is required (e.g. '0', '1')")
    tr_id = 'FHKST117300C0'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_BLNG_CLS_CODE': fid_blng_cls_code}
    return ApiRequest('domestic_stock.exp_closing_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def exp_index_trend(fid_mkop_cls_code, fid_input_hour_1, fid_input_iscd, fid_cond_mrkt_div_code, tr_cont=''):
    """KIS domestic_stock.exp_index_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_mkop_cls_code (str): 1: 장시작전, 2: 장마감
fid_input_hour_1 (str): 10(10초), 30(30초), 60(1분), 600(10분)
fid_input_iscd (str): 0000:전체, 0001:코스피, 1001:코스닥, 2001:코스피200, 4001: KRX100
fid_cond_mrkt_div_code (str): 시장구분코드 (주식 U)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/exp-index-trend'
    if not fid_mkop_cls_code:
        logger.error("fid_mkop_cls_code is required. (e.g. '1')")
        raise ValueError("fid_mkop_cls_code is required. (e.g. '1')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0000')")
        raise ValueError("fid_input_iscd is required. (e.g. '0000')")
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'U')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'U')")
    tr_id = 'FHPST01840000'
    params = {'FID_MKOP_CLS_CODE': fid_mkop_cls_code, 'FID_INPUT_HOUR_1': fid_input_hour_1, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code}
    return ApiRequest('domestic_stock.exp_index_trend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def exp_price_trend(fid_cond_mrkt_div_code, fid_input_iscd, fid_mkop_cls_code):
    """KIS domestic_stock.exp_price_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)
fid_mkop_cls_code (str): [필수]  (ex. 0:전체, 4:체결량 0 제외)"""
    api_url = '/uapi/domestic-stock/v1/quotations/exp-price-trend'
    if not fid_cond_mrkt_div_code:
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if not fid_input_iscd:
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if not fid_mkop_cls_code:
        raise ValueError("fid_mkop_cls_code is required (e.g. '0')")
    tr_id = 'FHPST01810000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_MKOP_CLS_CODE': fid_mkop_cls_code}
    return ApiRequest('domestic_stock.exp_price_trend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def exp_total_index(fid_mrkt_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_mkop_cls_code, tr_cont=''):
    """KIS domestic_stock.exp_total_index 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_mrkt_cls_code (str): 0:전체 K:거래소 Q:코스닥
fid_cond_mrkt_div_code (str): 시장구분코드 (업종 U)
fid_cond_scr_div_code (str): Unique key(11175)
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200, 4001: KRX100
fid_mkop_cls_code (str): 1:장시작전, 2:장마감
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/exp-total-index'
    logger = logging.getLogger(__name__)
    if not fid_mrkt_cls_code:
        logger.error("fid_mrkt_cls_code is required. (e.g. 'K')")
        raise ValueError("fid_mrkt_cls_code is required. (e.g. 'K')")
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'U')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'U')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '11175')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '11175')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '1001')")
        raise ValueError("fid_input_iscd is required. (e.g. '1001')")
    if not fid_mkop_cls_code:
        logger.error("fid_mkop_cls_code is required. (e.g. '1')")
        raise ValueError("fid_mkop_cls_code is required. (e.g. '1')")
    tr_id = 'FHKUP11750000'
    params = {'fid_mrkt_cls_code': fid_mrkt_cls_code, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_input_iscd': fid_input_iscd, 'fid_mkop_cls_code': fid_mkop_cls_code}
    return ApiRequest('domestic_stock.exp_total_index', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def exp_trans_updown(fid_rank_sort_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_aply_rang_prc_1, fid_vol_cnt, fid_pbmn, fid_blng_cls_code, fid_mkop_cls_code, tr_cont=''):
    """KIS domestic_stock.exp_trans_updown 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_rank_sort_cls_code (str): 0:상승률1:상승폭2:보합3:하락율4:하락폭5:체결량6:거래대금
fid_cond_mrkt_div_code (str): 시장구분코드 (주식 J)
fid_cond_scr_div_code (str): Unique key(20182)
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200, 4001: KRX100
fid_div_cls_code (str): 0:전체 1:보통주 2:우선주
fid_aply_rang_prc_1 (str): 입력값 없을때 전체 (가격 ~)
fid_vol_cnt (str): 입력값 없을때 전체 (거래량 ~)
fid_pbmn (str): 입력값 없을때 전체 (거래대금 ~) 천원단위
fid_blng_cls_code (str): 0: 전체
fid_mkop_cls_code (str): 0:장전예상1:장마감예상
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/exp-trans-updown'
    logger = logging.getLogger(__name__)
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '0')")
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20182')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20182')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0000')")
        raise ValueError("fid_input_iscd is required. (e.g. '0000')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    if not fid_blng_cls_code:
        logger.error("fid_blng_cls_code is required. (e.g. '0')")
        raise ValueError("fid_blng_cls_code is required. (e.g. '0')")
    if not fid_mkop_cls_code:
        logger.error("fid_mkop_cls_code is required. (e.g. '0')")
        raise ValueError("fid_mkop_cls_code is required. (e.g. '0')")
    tr_id = 'FHPST01820000'
    params = {'fid_rank_sort_cls_code': fid_rank_sort_cls_code, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_input_iscd': fid_input_iscd, 'fid_div_cls_code': fid_div_cls_code, 'fid_aply_rang_prc_1': fid_aply_rang_prc_1, 'fid_vol_cnt': fid_vol_cnt, 'fid_pbmn': fid_pbmn, 'fid_blng_cls_code': fid_blng_cls_code, 'fid_mkop_cls_code': fid_mkop_cls_code}
    return ApiRequest('domestic_stock.exp_trans_updown', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)







def finance_ratio(fid_trgt_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_input_option_1, fid_input_option_2, fid_rank_sort_cls_code, fid_blng_cls_code, fid_trgt_exls_cls_code, tr_cont=''):
    """KIS domestic_stock.finance_ratio 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_trgt_cls_code (str): 대상 구분 코드 (0 : 전체)
fid_cond_mrkt_div_code (str): 조건 시장 분류 코드 (J:KRX, NX:NXT)
fid_cond_scr_div_code (str): 조건 화면 분류 코드 (Unique key, 20175)
fid_input_iscd (str): 입력 종목코드 (0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200)
fid_div_cls_code (str): 분류 구분 코드 (0 : 전체)
fid_input_price_1 (str): 입력 가격1 (입력값 없을때 전체, 가격 ~)
fid_input_price_2 (str): 입력 가격2 (입력값 없을때 전체, ~ 가격)
fid_vol_cnt (str): 거래량 수 (입력값 없을때 전체, 거래량 ~)
fid_input_option_1 (str): 입력 옵션1 (회계년도 입력, ex 2023)
fid_input_option_2 (str): 입력 옵션2 (0: 1/4분기, 1: 반기, 2: 3/4분기, 3: 결산)
fid_rank_sort_cls_code (str): 순위 정렬 구분 코드 (7: 수익성 분석, 11: 안정성 분석, 15: 성장성 분석, 20: 활동성 분석)
fid_blng_cls_code (str): 소속 구분 코드 (0)
fid_trgt_exls_cls_code (str): 대상 제외 구분 코드 (0 : 전체)
tr_cont (str): 연속 거래 여부 (공백 : 초기 조회, N : 다음 데이터 조회)"""
    api_url = '/uapi/domestic-stock/v1/ranking/finance-ratio'
    if fid_trgt_cls_code == '':
        raise ValueError('대상 구분 코드 확인요망!!!')
    if fid_cond_mrkt_div_code != 'J':
        raise ValueError('조건 시장 분류 코드 확인요망!!!')
    if fid_cond_scr_div_code != '20175':
        raise ValueError('조건 화면 분류 코드 확인요망!!!')
    if fid_input_iscd not in ['0000', '0001', '1001', '2001']:
        raise ValueError('입력 종목코드 확인요망!!!')
    if fid_div_cls_code != '0':
        raise ValueError('분류 구분 코드 확인요망!!!')
    if fid_input_option_2 not in ['0', '1', '2', '3']:
        raise ValueError('입력 옵션2 확인요망!!!')
    if fid_rank_sort_cls_code not in ['7', '11', '15', '20']:
        raise ValueError('순위 정렬 구분 코드 확인요망!!!')
    if fid_blng_cls_code != '0':
        raise ValueError('소속 구분 코드 확인요망!!!')
    if fid_trgt_exls_cls_code != '0':
        raise ValueError('대상 제외 구분 코드 확인요망!!!')
    tr_id = 'FHPST01750000'
    params = {'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_input_iscd': fid_input_iscd, 'fid_div_cls_code': fid_div_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_input_price_2': fid_input_price_2, 'fid_vol_cnt': fid_vol_cnt, 'fid_input_option_1': fid_input_option_1, 'fid_input_option_2': fid_input_option_2, 'fid_rank_sort_cls_code': fid_rank_sort_cls_code, 'fid_blng_cls_code': fid_blng_cls_code, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code}
    return ApiRequest('domestic_stock.finance_ratio', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)


def fluctuation(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_input_cnt_1, fid_prc_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_div_cls_code, fid_rsfl_rate1, fid_rsfl_rate2, tr_cont=''):
    """KIS domestic_stock.fluctuation 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건 시장 분류 코드 (J:KRX, NX:NXT)
fid_cond_scr_div_code (str): 조건 화면 분류 코드 (20170: 등락률)
fid_input_iscd (str): 입력 종목코드 (0000: 전체)
fid_rank_sort_cls_code (str): 순위 정렬 구분 코드 (0000: 등락률순)
fid_input_cnt_1 (str): 입력 수1 (조회할 종목 수)
fid_prc_cls_code (str): 가격 구분 코드 (0: 전체)
fid_input_price_1 (str): 입력 가격1 (하한가)
fid_input_price_2 (str): 입력 가격2 (상한가)
fid_vol_cnt (str): 거래량 수 (최소 거래량)
fid_trgt_cls_code (str): 대상 구분 코드 (9자리, "1" or "0", 증거금30% 40% 50% 60% 100% 신용보증금30% 40% 50% 60%)
fid_trgt_exls_cls_code (str): 대상 제외 구분 코드 (10자리, "1" or "0", 투자위험/경고/주의 관리종목 정리매매 불성실공시 우선주 거래정지 ETF ETN 신용주문불가 SPAC)
fid_div_cls_code (str): 분류 구분 코드 (0: 전체)
fid_rsfl_rate1 (str): 등락 비율1 (하락률 하한)
fid_rsfl_rate2 (str): 등락 비율2 (상승률 상한)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/fluctuation'
    if fid_cond_mrkt_div_code not in ['J', 'W', 'Q']:
        raise ValueError('조건 시장 분류 코드 확인요망!!!')
    if fid_cond_scr_div_code != '20170':
        raise ValueError('조건 화면 분류 코드 확인요망!!!')
    tr_id = 'FHPST01700000'
    params = {'fid_rsfl_rate2': fid_rsfl_rate2, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_input_iscd': fid_input_iscd, 'fid_rank_sort_cls_code': fid_rank_sort_cls_code, 'fid_input_cnt_1': fid_input_cnt_1, 'fid_prc_cls_code': fid_prc_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_input_price_2': fid_input_price_2, 'fid_vol_cnt': fid_vol_cnt, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_div_cls_code': fid_div_cls_code, 'fid_rsfl_rate1': fid_rsfl_rate1}
    return ApiRequest('domestic_stock.fluctuation', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def foreign_institution_total(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_rank_sort_cls_code, fid_etc_cls_code):
    """KIS domestic_stock.foreign_institution_total 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. V)
fid_cond_scr_div_code (str): [필수] 조건화면분류코드 (ex. 16449)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 0000:전체,0001:코스피,1001:코스닥,...,FAQ 종목정보 다운로드(국내) - 업종코드 참조 )
fid_div_cls_code (str): [필수] 분류구분코드 (ex. 0:수량정열, 1:금액정열)
fid_rank_sort_cls_code (str): [필수] 순위정렬구분코드 (ex. 0:순매수상위,1:순매도상위)
fid_etc_cls_code (str): [필수] 기타구분정렬 (ex. 0:전체,1:외국인,2:기관계,3:기타)"""
    api_url = '/uapi/domestic-stock/v1/quotations/foreign-institution-total'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'V')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '16449')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '0000:전체,0001:코스피,1001:코스닥,...,FAQ 종목정보 다운로드(국내) - 업종코드 참조 ')")
    if fid_div_cls_code == '':
        raise ValueError("fid_div_cls_code is required (e.g. '0:수량정열, 1:금액정열')")
    if fid_rank_sort_cls_code == '':
        raise ValueError("fid_rank_sort_cls_code is required (e.g. '0:순매수상위,1:순매도상위')")
    if fid_etc_cls_code == '':
        raise ValueError("fid_etc_cls_code is required (e.g. '0:전체,1:외국인,2:기관계,3:기타')")
    tr_id = 'FHPTJ04400000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_ETC_CLS_CODE': fid_etc_cls_code}
    return ApiRequest('domestic_stock.foreign_institution_total', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def frgnmem_pchs_trend(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_iscd_2):
    """KIS domestic_stock.frgnmem_pchs_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)
fid_input_iscd_2 (str): [필수] 입력 종목코드 (ex. 99999)"""
    api_url = '/uapi/domestic-stock/v1/quotations/frgnmem-pchs-trend'
    if not fid_cond_mrkt_div_code:
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if not fid_input_iscd:
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if not fid_input_iscd_2:
        raise ValueError("fid_input_iscd_2 is required (e.g. '99999')")
    tr_id = 'FHKST644400C0'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_ISCD_2': fid_input_iscd_2}
    return ApiRequest('domestic_stock.frgnmem_pchs_trend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def frgnmem_trade_estimate(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_rank_sort_cls_code_2):
    """KIS domestic_stock.frgnmem_trade_estimate 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건시장분류코드 (ex. J)
fid_cond_scr_div_code (str): [필수] 조건화면분류코드 (ex. 16441)
fid_input_iscd (str): [필수] 입력종목코드 (ex. 0000:전체, 1001:코스피, 2001:코스닥)
fid_rank_sort_cls_code (str): [필수] 순위정렬구분코드 (ex. 0:금액순, 1:수량순)
fid_rank_sort_cls_code_2 (str): [필수] 순위정렬구분코드2 (ex. 0:매수순, 1:매도순)"""
    api_url = '/uapi/domestic-stock/v1/quotations/frgnmem-trade-estimate'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '16441')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '0000')")
    if fid_rank_sort_cls_code == '':
        raise ValueError("fid_rank_sort_cls_code is required (e.g. '0')")
    if fid_rank_sort_cls_code_2 == '':
        raise ValueError("fid_rank_sort_cls_code_2 is required (e.g. '0')")
    tr_id = 'FHKST644100C0'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_RANK_SORT_CLS_CODE_2': fid_rank_sort_cls_code_2}
    return ApiRequest('domestic_stock.frgnmem_trade_estimate', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def frgnmem_trade_trend(fid_cond_scr_div_code, fid_cond_mrkt_div_code, fid_input_iscd, fid_input_iscd_2, fid_mrkt_cls_code, fid_vol_cnt, tr_cont=''):
    """KIS domestic_stock.frgnmem_trade_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_scr_div_code (str): 20432(primary key)
fid_cond_mrkt_div_code (str): J 고정입력
fid_input_iscd (str): ex. 005930(삼성전자)   ※ FID_INPUT_ISCD(종목코드) 혹은 FID_MRKT_CLS_CODE(시장구분코드) 둘 중 하나만 입력
fid_input_iscd_2 (str): ex. 99999(전체)  ※ 회원사코드 (kis developers 포탈 사이트 포럼-> FAQ -> 종목정보 다운로드(국내) 참조)
fid_mrkt_cls_code (str): A(전체),K(코스피), Q(코스닥), K2(코스피200), W(ELW)  ※ FID_INPUT_ISCD(종목코드) 혹은 FID_MRKT_CLS_CODE(시장구분코드) 둘 중 하나만 입력
fid_vol_cnt (str): 거래량 ~
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/frgnmem-trade-trend'
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20432')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20432')")
    if not fid_cond_mrkt_div_code or fid_cond_mrkt_div_code != 'J':
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '005930')")
        raise ValueError("fid_input_iscd is required. (e.g. '005930')")
    if not fid_input_iscd_2:
        logger.error("fid_input_iscd_2 is required. (e.g. '99999')")
        raise ValueError("fid_input_iscd_2 is required. (e.g. '99999')")
    if not fid_mrkt_cls_code:
        logger.error("fid_mrkt_cls_code is required. (e.g. 'A')")
        raise ValueError("fid_mrkt_cls_code is required. (e.g. 'A')")
    tr_id = 'FHPST04320000'
    params = {'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_ISCD_2': fid_input_iscd_2, 'FID_MRKT_CLS_CODE': fid_mrkt_cls_code, 'FID_VOL_CNT': fid_vol_cnt}
    return ApiRequest('domestic_stock.frgnmem_trade_trend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def hts_top_view(tr_cont=''):
    """KIS domestic_stock.hts_top_view 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
tr_cont (str): 연속 거래 여부 ("공백": 초기 조회, "N": 다음 데이터 조회)"""
    api_url = '/uapi/domestic-stock/v1/ranking/hts-top-view'
    logger = logging.getLogger(__name__)
    tr_id = 'HHMCM000100C0'
    params = {}
    return ApiRequest('domestic_stock.hts_top_view', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_account_balance(cano, acnt_prdt_cd, inqr_dvsn_1='', bspr_bf_dt_aply_yn=''):
    """KIS domestic_stock.inquire_account_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. 12345678)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 19 or 21)
inqr_dvsn_1 (str): 조회구분1
bspr_bf_dt_aply_yn (str): 기준가이전일자적용여부"""
    api_url = '/uapi/domestic-stock/v1/trading/inquire-account-balance'
    if cano == '':
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '19' or '21')")
    tr_id = 'CTRP6548R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'INQR_DVSN_1': inqr_dvsn_1, 'BSPR_BF_DT_APLY_YN': bspr_bf_dt_aply_yn}
    return ApiRequest('domestic_stock.inquire_account_balance', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_asking_price_exp_ccn(env_dv, fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS domestic_stock.inquire_asking_price_exp_ccn 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn'
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX, NX:NXT, UN:통합')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if env_dv == 'real':
        tr_id = 'FHKST01010200'
    elif env_dv == 'demo':
        tr_id = 'FHKST01010200'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_asking_price_exp_ccn', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_balance(env_dv, cano, acnt_prdt_cd, afhr_flpr_yn, inqr_dvsn, unpr_dvsn, fund_sttl_icld_yn, fncg_amt_auto_rdpt_yn, prcs_dvsn, FK100='', NK100='', tr_cont=''):
    """KIS domestic_stock.inquire_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
cano (str): [필수] 종합계좌번호 (ex. 계좌번호 체계(8-2)의 앞 8자리)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 계좌번호 체계(8-2)의 뒤 2자리)
afhr_flpr_yn (str): [필수] 시간외단일가·거래소여부 (ex. N:기본값, Y:시간외단일가, X:NXT)
inqr_dvsn (str): [필수] 조회구분 (ex. 01 – 대출일별 | 02 – 종목별)
unpr_dvsn (str): [필수] 단가구분 (ex. 01)
fund_sttl_icld_yn (str): [필수] 펀드결제분포함여부 (ex. N, Y)
fncg_amt_auto_rdpt_yn (str): [필수] 융자금액자동상환여부 (ex. N)
prcs_dvsn (str): [필수] 처리구분 (ex. 00: 전일매매포함, 01:전일매매미포함)
FK100 (str): 연속조회검색조건100
NK100 (str): 연속조회키100
tr_cont (str): 연속거래여부"""
    api_url = '/uapi/domestic-stock/v1/trading/inquire-balance'
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if cano == '':
        raise ValueError("cano is required (e.g. '계좌번호 체계(8-2)의 앞 8자리')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '계좌번호 체계(8-2)의 뒤 2자리')")
    if afhr_flpr_yn == '':
        raise ValueError("afhr_flpr_yn is required (e.g. 'N:기본값, Y:시간외단일가, X:NXT')")
    if inqr_dvsn == '':
        raise ValueError("inqr_dvsn is required (e.g. '01 – 대출일별 | 02 – 종목별')")
    if unpr_dvsn == '':
        raise ValueError("unpr_dvsn is required (e.g. '01')")
    if fund_sttl_icld_yn == '':
        raise ValueError("fund_sttl_icld_yn is required (e.g. 'N, Y')")
    if fncg_amt_auto_rdpt_yn == '':
        raise ValueError("fncg_amt_auto_rdpt_yn is required (e.g. 'N')")
    if prcs_dvsn == '':
        raise ValueError("prcs_dvsn is required (e.g. '00: 전일매매포함, 01:전일매매미포함')")
    if env_dv == 'real':
        tr_id = 'TTTC8434R'
    elif env_dv == 'demo':
        tr_id = 'VTTC8434R'
    else:
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'AFHR_FLPR_YN': afhr_flpr_yn, 'OFL_YN': '', 'INQR_DVSN': inqr_dvsn, 'UNPR_DVSN': unpr_dvsn, 'FUND_STTL_ICLD_YN': fund_sttl_icld_yn, 'FNCG_AMT_AUTO_RDPT_YN': fncg_amt_auto_rdpt_yn, 'PRCS_DVSN': prcs_dvsn, 'CTX_AREA_FK100': FK100, 'CTX_AREA_NK100': NK100}
    return ApiRequest('domestic_stock.inquire_balance', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_balance_rlz_pl(cano, acnt_prdt_cd, afhr_flpr_yn, inqr_dvsn, unpr_dvsn, fund_sttl_icld_yn, fncg_amt_auto_rdpt_yn, prcs_dvsn, ofl_yn='', cost_icld_yn='', FK100='', NK100='', tr_cont=''):
    """KIS domestic_stock.inquire_balance_rlz_pl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (계좌번호 체계(8-2)의 앞 8자리)
acnt_prdt_cd (str): [필수] 계좌상품코드 (계좌번호 체계(8-2)의 뒤 2자리)
afhr_flpr_yn (str): [필수] 시간외단일가여부 (N:기본값, Y:시간외단일가)
inqr_dvsn (str): [필수] 조회구분 (00:전체)
unpr_dvsn (str): [필수] 단가구분 (01:기본값)
fund_sttl_icld_yn (str): [필수] 펀드결제포함여부 (N:포함하지 않음, Y:포함)
fncg_amt_auto_rdpt_yn (str): [필수] 융자금액자동상환여부 (N:기본값)
prcs_dvsn (str): [필수] PRCS_DVSN (00:전일매매포함, 01:전일매매미포함)
ofl_yn (str): 오프라인여부
cost_icld_yn (str): 비용포함여부
FK100 (str): 연속조회검색조건100
NK100 (str): 연속조회키100
tr_cont (str): 연속거래여부"""
    api_url = '/uapi/domestic-stock/v1/trading/inquire-balance-rlz-pl'
    if cano == '':
        raise ValueError("cano is required (e.g. '계좌번호 체계(8-2)의 앞 8자리')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '계좌번호 체계(8-2)의 뒤 2자리')")
    if afhr_flpr_yn == '':
        raise ValueError("afhr_flpr_yn is required (e.g. 'N:기본값, Y:시간외단일가')")
    if inqr_dvsn == '':
        raise ValueError("inqr_dvsn is required (e.g. '00:전체')")
    if unpr_dvsn == '':
        raise ValueError("unpr_dvsn is required (e.g. '01:기본값')")
    if fund_sttl_icld_yn == '':
        raise ValueError("fund_sttl_icld_yn is required (e.g. 'N:포함하지 않음, Y:포함')")
    if fncg_amt_auto_rdpt_yn == '':
        raise ValueError("fncg_amt_auto_rdpt_yn is required (e.g. 'N:기본값')")
    if prcs_dvsn == '':
        raise ValueError("prcs_dvsn is required (e.g. '00:전일매매포함, 01:전일매매미포함')")
    tr_id = 'TTTC8494R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'AFHR_FLPR_YN': afhr_flpr_yn, 'OFL_YN': ofl_yn, 'INQR_DVSN': inqr_dvsn, 'UNPR_DVSN': unpr_dvsn, 'FUND_STTL_ICLD_YN': fund_sttl_icld_yn, 'FNCG_AMT_AUTO_RDPT_YN': fncg_amt_auto_rdpt_yn, 'PRCS_DVSN': prcs_dvsn, 'COST_ICLD_YN': cost_icld_yn, 'CTX_AREA_FK100': FK100, 'CTX_AREA_NK100': NK100}
    return ApiRequest('domestic_stock.inquire_balance_rlz_pl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_ccnl(env_dv, fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS domestic_stock.inquire_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-ccnl'
    if env_dv == '' or env_dv is None:
        raise ValueError("env_dv is required (e.g. 'real:실전', 'demo:모의')")
    if fid_cond_mrkt_div_code == '' or fid_cond_mrkt_div_code is None:
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX', 'NX:NXT', 'UN:통합')")
    if fid_input_iscd == '' or fid_input_iscd is None:
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if env_dv == 'real':
        tr_id = 'FHKST01010300'
    elif env_dv == 'demo':
        tr_id = 'FHKST01010300'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_daily_ccld(env_dv, pd_dv, cano, acnt_prdt_cd, inqr_strt_dt, inqr_end_dt, sll_buy_dvsn_cd, ccld_dvsn, inqr_dvsn, inqr_dvsn_3, pdno='', ord_gno_brno='', odno='', inqr_dvsn_1='', FK100='', NK100='', tr_cont='', excg_id_dvsn_cd='KRX'):
    """KIS domestic_stock.inquire_daily_ccld 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
pd_dv (str): [필수] 3개월이전이내구분 (ex. before:이전, inner:이내)
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드
inqr_strt_dt (str): [필수] 조회시작일자
inqr_end_dt (str): [필수] 조회종료일자
sll_buy_dvsn_cd (str): [필수] 매도매수구분코드 (ex. 00 : 전체 / 01 : 매도 / 02 : 매수)
pdno (str): 상품번호
ccld_dvsn (str): [필수] 체결구분 (ex. 00 전체 / 01 체결 / 02 미체결)
inqr_dvsn (str): [필수] 조회구분 (ex. 00 역순 / 01 정순)
inqr_dvsn_3 (str): [필수] 조회구분3 (ex. 00 전체 / 01 현금 / 02 신용 / 03 담보 / 04 대주 / 05 대여 / 06 자기융자신규/상환 / 07 유통융자신규/상환)
ord_gno_brno (str): 주문채번지점번호
odno (str): 주문번호 (ex. 주문시 한국투자증권 시스템에서 채번된 주문번호)
inqr_dvsn_1 (str): 조회구분1 (ex. 없음: 전체 / 1: ELW / 2: 프리보드)
FK100 (str): 연속조회검색조건100 (ex. 공란: 최초 조회 / 이전 조회 Output 사용)
NK100 (str): 연속조회키100 (ex. 공란: 최초 조회 / 이전 조회 Output 사용)
tr_cont (str): 연속거래여부
excg_id_dvsn_cd (Optional[str]): 거래소ID구분코드 (ex. KRX / NXT / SOR / ALL)"""
    api_url = '/uapi/domestic-stock/v1/trading/inquire-daily-ccld'
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real:실전', 'demo:모의')")
    if pd_dv == '':
        raise ValueError("pd_dv is required (e.g. 'before:이전', 'inner:이내')")
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError('acnt_prdt_cd is required')
    if inqr_strt_dt == '':
        raise ValueError('inqr_strt_dt is required')
    if inqr_end_dt == '':
        raise ValueError('inqr_end_dt is required')
    if sll_buy_dvsn_cd == '':
        raise ValueError("sll_buy_dvsn_cd is required (e.g. '00 : 전체 / 01 : 매도 / 02 : 매수')")
    if ccld_dvsn == '':
        raise ValueError("ccld_dvsn is required (e.g. '00 전체 / 01 체결 / 02 미체결')")
    if inqr_dvsn == '':
        raise ValueError("inqr_dvsn is required (e.g. '00 역순 / 01 정순')")
    if inqr_dvsn_3 == '':
        raise ValueError("inqr_dvsn_3 is required (e.g. '00 전체 / 01 현금 / 02 신용 / 03 담보 / 04 대주 / 05 대여 / 06 자기융자신규/상환 / 07 유통융자신규/상환')")
    if env_dv == 'real':
        if pd_dv == 'before':
            tr_id = 'CTSC9215R'
        elif pd_dv == 'inner':
            tr_id = 'TTTC0081R'
        else:
            raise ValueError("pd_dv can only be 'before' or 'inner'")
    elif env_dv == 'demo':
        if pd_dv == 'before':
            tr_id = 'VTSC9215R'
        elif pd_dv == 'inner':
            tr_id = 'VTTC0081R'
        else:
            raise ValueError("pd_dv can only be 'before' or 'inner'")
    else:
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'INQR_STRT_DT': inqr_strt_dt, 'INQR_END_DT': inqr_end_dt, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'PDNO': pdno, 'CCLD_DVSN': ccld_dvsn, 'INQR_DVSN': inqr_dvsn, 'INQR_DVSN_3': inqr_dvsn_3, 'ORD_GNO_BRNO': ord_gno_brno, 'ODNO': odno, 'INQR_DVSN_1': inqr_dvsn_1, 'CTX_AREA_FK100': FK100, 'CTX_AREA_NK100': NK100}
    if excg_id_dvsn_cd is not None:
        params['EXCG_ID_DVSN_CD'] = excg_id_dvsn_cd
    return ApiRequest('domestic_stock.inquire_daily_ccld', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_daily_indexchartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2, fid_period_div_code, env_dv='real', tr_cont=''):
    """KIS domestic_stock.inquire_daily_indexchartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 업종 : U
fid_input_iscd (str): 0001 : 종합 0002 : 대형주 ... 포탈 (FAQ : 종목정보 다운로드(국내) - 업종코드 참조)
fid_input_date_1 (str): 조회 시작일자 (ex. 20220501)
fid_input_date_2 (str): 조회 종료일자 (ex. 20220530)
fid_period_div_code (str): D:일봉 W:주봉, M:월봉, Y:년봉
env_dv (str): [추가] 실전모의구분 (real:실전, demo:모의, 기본값: 'real')
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice'
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'U')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'U')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0001')")
        raise ValueError("fid_input_iscd is required. (e.g. '0001')")
    if not fid_input_date_1:
        logger.error("fid_input_date_1 is required. (e.g. '20220501')")
        raise ValueError("fid_input_date_1 is required. (e.g. '20220501')")
    if not fid_input_date_2:
        logger.error("fid_input_date_2 is required. (e.g. '20220530')")
        raise ValueError("fid_input_date_2 is required. (e.g. '20220530')")
    if not fid_period_div_code:
        logger.error("fid_period_div_code is required. (e.g. 'D')")
        raise ValueError("fid_period_div_code is required. (e.g. 'D')")
    if env_dv not in ['real', 'demo']:
        logger.error("env_dv must be 'real' or 'demo'")
        raise ValueError("env_dv must be 'real' or 'demo'")
    if env_dv == 'real' or env_dv == 'demo':
        tr_id = 'FHKUP03500100'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2, 'FID_PERIOD_DIV_CODE': fid_period_div_code}
    return ApiRequest('domestic_stock.inquire_daily_indexchartprice', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_daily_itemchartprice(env_dv, fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2, fid_period_div_code, fid_org_adj_prc):
    """KIS domestic_stock.inquire_daily_itemchartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 종목코드 (ex 005930 삼성전자))
fid_input_date_1 (str): [필수] 입력 날짜 1 (ex. 조회 시작일자)
fid_input_date_2 (str): [필수] 입력 날짜 2 (ex. 조회 종료일자 (최대 100개))
fid_period_div_code (str): [필수] 기간분류코드 (ex. D:일봉 W:주봉, M:월봉, Y:년봉)
fid_org_adj_prc (str): [필수] 수정주가 원주가 가격 여부 (ex. 0:수정주가 1:원주가)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice'
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX, NX:NXT, UN:통합')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '종목코드 (ex 005930 삼성전자)')")
    if fid_input_date_1 == '':
        raise ValueError("fid_input_date_1 is required (e.g. '조회 시작일자')")
    if fid_input_date_2 == '':
        raise ValueError("fid_input_date_2 is required (e.g. '조회 종료일자 (최대 100개)')")
    if fid_period_div_code == '':
        raise ValueError("fid_period_div_code is required (e.g. 'D:일봉 W:주봉, M:월봉, Y:년봉')")
    if fid_org_adj_prc == '':
        raise ValueError("fid_org_adj_prc is required (e.g. '0:수정주가 1:원주가')")
    if env_dv == 'real':
        tr_id = 'FHKST03010100'
    elif env_dv == 'demo':
        tr_id = 'FHKST03010100'
    else:
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2, 'FID_PERIOD_DIV_CODE': fid_period_div_code, 'FID_ORG_ADJ_PRC': fid_org_adj_prc}
    return ApiRequest('domestic_stock.inquire_daily_itemchartprice', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_daily_overtimeprice(env_dv, fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS domestic_stock.inquire_daily_overtimeprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J)
fid_input_iscd (str): [필수] 입력 종목코드"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-daily-overtimeprice'
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_input_iscd == '':
        raise ValueError('fid_input_iscd is required')
    if env_dv == 'real':
        tr_id = 'FHPST02320000'
    elif env_dv == 'demo':
        tr_id = 'FHPST02320000'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_daily_overtimeprice', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_daily_price(env_dv, fid_cond_mrkt_div_code, fid_input_iscd, fid_period_div_code, fid_org_adj_prc):
    """KIS domestic_stock.inquire_daily_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 종목코드 (ex 005930 삼성전자))
fid_period_div_code (str): [필수] 기간 분류 코드 (ex. D:(일)최근 30거래일, W:(주)최근 30주, M:(월)최근 30개월)
fid_org_adj_prc (str): [필수] 수정주가 원주가 가격 (ex. 0:수정주가미반영, 1:수정주가반영, *수정주가는 액면분할/액면병합 등 권리 발생 시 과거 시세를 현재 주가에 맞게 보정한 가격)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-daily-price'
    if env_dv == '' or env_dv is None:
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if fid_cond_mrkt_div_code == '' or fid_cond_mrkt_div_code is None:
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX, NX:NXT, UN:통합')")
    if fid_input_iscd == '' or fid_input_iscd is None:
        raise ValueError("fid_input_iscd is required (e.g. '종목코드 (ex 005930 삼성전자)')")
    if fid_period_div_code == '' or fid_period_div_code is None:
        raise ValueError("fid_period_div_code is required (e.g. 'D:(일)최근 30거래일, W:(주)최근 30주, M:(월)최근 30개월')")
    if fid_org_adj_prc == '' or fid_org_adj_prc is None:
        raise ValueError("fid_org_adj_prc is required (e.g. '0:수정주가미반영, 1:수정주가반영, *수정주가는 액면분할/액면병합 등 권리 발생 시 과거 시세를 현재 주가에 맞게 보정한 가격')")
    if env_dv == 'real':
        tr_id = 'FHKST01010400'
    elif env_dv == 'demo':
        tr_id = 'FHKST01010400'
    else:
        raise ValueError('env_dv can only be real or demo')
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_PERIOD_DIV_CODE': fid_period_div_code, 'FID_ORG_ADJ_PRC': fid_org_adj_prc}
    return ApiRequest('domestic_stock.inquire_daily_price', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_daily_trade_volume(fid_cond_mrkt_div_code, fid_input_iscd, fid_period_div_code, fid_input_date_1='', fid_input_date_2=''):
    """KIS domestic_stock.inquire_daily_trade_volume 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] FID 조건 시장 분류 코드 (J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] FID 입력 종목코드 (ex. 123456)
fid_period_div_code (str): [필수] FID 기간 분류 코드 (ex. D)
fid_input_date_1 (str): FID 입력 날짜1
fid_input_date_2 (str): FID 입력 날짜2"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-daily-trade-volume'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '005930')")
    if fid_period_div_code == '':
        raise ValueError("fid_period_div_code is required (e.g. 'D')")
    tr_id = 'FHKST03010800'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_PERIOD_DIV_CODE': fid_period_div_code, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2}
    return ApiRequest('domestic_stock.inquire_daily_trade_volume', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_elw_price(fid_cond_mrkt_div_code, fid_input_iscd, env_dv='real', tr_cont=''):
    """KIS domestic_stock.inquire_elw_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): FID 조건 시장 분류 코드 (예: 'W')
fid_input_iscd (str): FID 입력 종목코드 (예: '000660')
env_dv (str): [추가] 실전모의구분 (real:실전, demo:모의, 기본값: 'real')
tr_cont (str): 연속 거래 여부 (기본값: '')"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-elw-price'
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'W')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'W')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '000660')")
        raise ValueError("fid_input_iscd is required. (e.g. '000660')")
    if env_dv not in ['real', 'demo']:
        logger.error("env_dv must be 'real' or 'demo'")
        raise ValueError("env_dv must be 'real' or 'demo'")
    if env_dv == 'real' or env_dv == 'demo':
        tr_id = 'FHKEW15010000'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_elw_price', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_index_category_price(fid_cond_mrkt_div_code, fid_input_iscd, fid_cond_scr_div_code, fid_mrkt_cls_code, fid_blng_cls_code, tr_cont=''):
    """KIS domestic_stock.inquire_index_category_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 시장구분코드 (업종 U)
fid_input_iscd (str): 코스피(0001), 코스닥(1001), 코스피200(2001) ... 포탈 (FAQ : 종목정보 다운로드(국내) - 업종코드 참조)
fid_cond_scr_div_code (str): Unique key( 20214 )
fid_mrkt_cls_code (str): 시장구분코드(K:거래소, Q:코스닥, K2:코스피200)
fid_blng_cls_code (str): 시장구분코드에 따라 아래와 같이 입력 시장구분코드(K:거래소) 0:전업종, 1:기타구분, 2:자본금구분 3:상업별구분 시장구분코드(Q:코스닥) 0:전업종, 1:기타구분, 2:벤처구분 3:일반구분 시장구분코드(K2:코스닥) 0:전업종
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-index-category-price'
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'U')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'U')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0001')")
        raise ValueError("fid_input_iscd is required. (e.g. '0001')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20214')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20214')")
    if not fid_mrkt_cls_code:
        logger.error("fid_mrkt_cls_code is required. (e.g. 'K')")
        raise ValueError("fid_mrkt_cls_code is required. (e.g. 'K')")
    if not fid_blng_cls_code:
        logger.error("fid_blng_cls_code is required. (e.g. '0')")
        raise ValueError("fid_blng_cls_code is required. (e.g. '0')")
    tr_id = 'FHPUP02140000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_MRKT_CLS_CODE': fid_mrkt_cls_code, 'FID_BLNG_CLS_CODE': fid_blng_cls_code}
    return ApiRequest('domestic_stock.inquire_index_category_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_index_daily_price(fid_period_div_code, fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, tr_cont=''):
    """KIS domestic_stock.inquire_index_daily_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_period_div_code (str): 일/주/월 구분코드 ( D:일별 , W:주별, M:월별 )
fid_cond_mrkt_div_code (str): 시장구분코드 (업종 U)
fid_input_iscd (str): 코스피(0001), 코스닥(1001), 코스피200(2001) ... 포탈 (FAQ : 종목정보 다운로드(국내) - 업종코드 참조)
fid_input_date_1 (str): 입력 날짜(ex. 20240223)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-index-daily-price'
    if not fid_period_div_code:
        logger.error("fid_period_div_code is required. (e.g. 'D')")
        raise ValueError("fid_period_div_code is required. (e.g. 'D')")
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'U')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'U')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0001')")
        raise ValueError("fid_input_iscd is required. (e.g. '0001')")
    if not fid_input_date_1:
        logger.error("fid_input_date_1 is required. (e.g. '20240223')")
        raise ValueError("fid_input_date_1 is required. (e.g. '20240223')")
    tr_id = 'FHPUP02120000'
    params = {'FID_PERIOD_DIV_CODE': fid_period_div_code, 'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1}
    return ApiRequest('domestic_stock.inquire_index_daily_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_index_price(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS domestic_stock.inquire_index_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 업종(U)
fid_input_iscd (str): 코스피(0001), 코스닥(1001), 코스피200(2001) ... 포탈 (FAQ : 종목정보 다운로드(국내) - 업종코드 참조)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-index-price'
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'U')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'U')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0001')")
        raise ValueError("fid_input_iscd is required. (e.g. '0001')")
    tr_id = 'FHPUP02100000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_index_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_index_tickprice(fid_input_iscd, fid_cond_mrkt_div_code, tr_cont=''):
    """KIS domestic_stock.inquire_index_tickprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_input_iscd (str): 0001:거래소, 1001:코스닥, 2001:코스피200, 3003:KSQ150
fid_cond_mrkt_div_code (str): 시장구분코드 (업종 U)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-index-tickprice'
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0001')")
        raise ValueError("fid_input_iscd is required. (e.g. '0001')")
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'U')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'U')")
    tr_id = 'FHPUP02110100'
    params = {'FID_INPUT_ISCD': fid_input_iscd, 'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code}
    return ApiRequest('domestic_stock.inquire_index_tickprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_index_timeprice(fid_input_hour_1, fid_input_iscd, fid_cond_mrkt_div_code, tr_cont=''):
    """KIS domestic_stock.inquire_index_timeprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_input_hour_1 (str): 초단위, 60(1분), 300(5분), 600(10분)
fid_input_iscd (str): 0001:거래소, 1001:코스닥, 2001:코스피200, 3003:KSQ150
fid_cond_mrkt_div_code (str): 시장구분코드 (업종 U)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-index-timeprice'
    if not fid_input_hour_1:
        logger.error("fid_input_hour_1 is required. (e.g. '60')")
        raise ValueError("fid_input_hour_1 is required. (e.g. '60')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0001')")
        raise ValueError("fid_input_iscd is required. (e.g. '0001')")
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'U')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'U')")
    tr_id = 'FHPUP02110200'
    params = {'FID_INPUT_HOUR_1': fid_input_hour_1, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code}
    return ApiRequest('domestic_stock.inquire_index_timeprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_investor(env_dv, fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS domestic_stock.inquire_investor 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-investor'
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if env_dv == 'real':
        tr_id = 'FHKST01010900'
    elif env_dv == 'demo':
        tr_id = 'FHKST01010900'
    else:
        raise ValueError('env_dv can only be real or demo')
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_investor', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_investor_daily_by_market(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_iscd_1, fid_input_date_2, fid_input_iscd_2):
    """KIS domestic_stock.inquire_investor_daily_by_market 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. U:업종)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 0001)
fid_input_date_1 (str): [필수] 입력 날짜1 (ex. 20250701)
fid_input_iscd_1 (str): [필수] 입력 종목코드 (ex. KSP:코스피, KSQ:코스닥)
fid_input_date_2 (str): [필수] 입력 날짜1과 동일날짜 입력
fid_input_iscd_2 (str): [필수] 입력 종목코드 (ex. 업종분류코드)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'U')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '0001')")
    if fid_input_date_1 == '':
        raise ValueError("fid_input_date_1 is required (e.g. '20250701')")
    if fid_input_iscd_1 == '':
        raise ValueError("fid_input_iscd_1 is required (e.g. 'KSP')")
    if fid_input_date_2 == '':
        raise ValueError("fid_input_date_2 is required (e.g. '20250701')")
    if fid_input_iscd_2 == '':
        raise ValueError("fid_input_iscd_2 is required (e.g. 업종분류코드')")
    tr_id = 'FHPTJ04040000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_ISCD_1': fid_input_iscd_1, 'FID_INPUT_DATE_2': fid_input_date_2, 'FID_INPUT_ISCD_2': fid_input_iscd_2}
    return ApiRequest('domestic_stock.inquire_investor_daily_by_market', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_investor_time_by_market(fid_input_iscd, fid_input_iscd_2):
    """KIS domestic_stock.inquire_investor_time_by_market 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_input_iscd (str): [필수] 시장구분
fid_input_iscd_2 (str): [필수] 업종구분"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market'
    if fid_input_iscd == '':
        raise ValueError('fid_input_iscd is required')
    if fid_input_iscd_2 == '':
        raise ValueError('fid_input_iscd_2 is required')
    tr_id = 'FHPTJ04030000'
    params = {'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_ISCD_2': fid_input_iscd_2}
    return ApiRequest('domestic_stock.inquire_investor_time_by_market', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_member(env_dv, fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS domestic_stock.inquire_member 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-member'
    if env_dv == '' or env_dv is None:
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if fid_cond_mrkt_div_code == '' or fid_cond_mrkt_div_code is None:
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX')")
    if fid_input_iscd == '' or fid_input_iscd is None:
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if env_dv == 'real':
        tr_id = 'FHKST01010600'
    elif env_dv == 'demo':
        tr_id = 'FHKST01010600'
    else:
        raise ValueError('env_dv can only be real or demo')
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_member', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_member_daily(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_iscd_2, fid_input_date_1, fid_input_date_2, fid_sctn_cls_code=''):
    """KIS domestic_stock.inquire_member_daily 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건시장분류코드 (ex. J:KRX, NX:NXT)
fid_input_iscd (str): [필수] 입력종목코드 (ex. 123456)
fid_input_iscd_2 (str): [필수] 회원사코드 (ex. 회원사코드 FAQ 종목정보 다운로드(국내) > 회원사 참조)
fid_input_date_1 (str): [필수] 입력날짜1
fid_input_date_2 (str): [필수] 입력날짜2
fid_sctn_cls_code (str): 데이터 순위 (초기값: "")"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-member-daily'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if fid_input_iscd_2 == '':
        raise ValueError("fid_input_iscd_2 is required (e.g. '00003')")
    if fid_input_date_1 == '':
        raise ValueError('fid_input_date_1 is required')
    if fid_input_date_2 == '':
        raise ValueError('fid_input_date_2 is required')
    tr_id = 'FHPST04540000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_ISCD_2': fid_input_iscd_2, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2, 'FID_SCTN_CLS_CODE': fid_sctn_cls_code}
    return ApiRequest('domestic_stock.inquire_member_daily', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_overtime_asking_price(fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS domestic_stock.inquire_overtime_asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 시장 분류 코드 (ex. J:주식)
fid_input_iscd (str): [필수] 종목코드 (ex. 123456)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-overtime-asking-price'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    tr_id = 'FHPST02300400'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_overtime_asking_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_overtime_price(fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS domestic_stock.inquire_overtime_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 시장 분류 코드 (ex. J: 주식)
fid_input_iscd (str): [필수] 종목코드 (ex. 005930)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-overtime-price'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '005930')")
    tr_id = 'FHPST02300000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_overtime_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_period_profit(cano, acnt_prdt_cd, inqr_strt_dt, inqr_end_dt, sort_dvsn, inqr_dvsn, cblc_dvsn, pdno='', NK100='', FK100='', tr_cont=''):
    """KIS domestic_stock.inquire_period_profit 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드
inqr_strt_dt (str): [필수] 조회시작일자
inqr_end_dt (str): [필수] 조회종료일자
sort_dvsn (str): [필수] 정렬구분 (00: 최근 순, 01: 과거 순, 02: 최근 순)
inqr_dvsn (str): [필수] 조회구분 (00)
cblc_dvsn (str): [필수] 잔고구분 (00: 전체)
pdno (str): 상품번호
NK100 (str): 연속조회키100
FK100 (str): 연속조회검색조건100
tr_cont (str): 연속거래여부"""
    api_url = '/uapi/domestic-stock/v1/trading/inquire-period-profit'
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError('acnt_prdt_cd is required')
    if inqr_strt_dt == '':
        raise ValueError('inqr_strt_dt is required')
    if inqr_end_dt == '':
        raise ValueError('inqr_end_dt is required')
    if sort_dvsn == '':
        raise ValueError("sort_dvsn is required (e.g. '00', '01', '02')")
    if inqr_dvsn == '':
        raise ValueError("inqr_dvsn is required (e.g. '00')")
    if cblc_dvsn == '':
        raise ValueError("cblc_dvsn is required (e.g. '00')")
    tr_id = 'TTTC8708R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'INQR_STRT_DT': inqr_strt_dt, 'INQR_END_DT': inqr_end_dt, 'SORT_DVSN': sort_dvsn, 'INQR_DVSN': inqr_dvsn, 'CBLC_DVSN': cblc_dvsn, 'PDNO': pdno, 'CTX_AREA_FK100': FK100, 'CTX_AREA_NK100': NK100}
    return ApiRequest('domestic_stock.inquire_period_profit', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_period_trade_profit(cano, acnt_prdt_cd, sort_dvsn, inqr_strt_dt, inqr_end_dt, cblc_dvsn, pdno='', NK100='', FK100='', tr_cont=''):
    """KIS domestic_stock.inquire_period_trade_profit 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드
sort_dvsn (str): [필수] 정렬구분 (ex. 00: 최근, 01:과거, 02:최근)
inqr_strt_dt (str): [필수] 조회시작일자
inqr_end_dt (str): [필수] 조회종료일자
cblc_dvsn (str): [필수] 잔고구분 (ex. 00: 전체)
pdno (str): 상품번호
NK100 (str): 연속조회키100
FK100 (str): 연속조회검색조건100
tr_cont (str): 연속거래여부"""
    api_url = '/uapi/domestic-stock/v1/trading/inquire-period-trade-profit'
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError('acnt_prdt_cd is required')
    if sort_dvsn == '':
        raise ValueError("sort_dvsn is required (e.g. '00', '01', '02')")
    if inqr_strt_dt == '':
        raise ValueError('inqr_strt_dt is required')
    if inqr_end_dt == '':
        raise ValueError('inqr_end_dt is required')
    if cblc_dvsn == '':
        raise ValueError("cblc_dvsn is required (e.g. '00')")
    tr_id = 'TTTC8715R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'SORT_DVSN': sort_dvsn, 'INQR_STRT_DT': inqr_strt_dt, 'INQR_END_DT': inqr_end_dt, 'CBLC_DVSN': cblc_dvsn, 'PDNO': pdno, 'CTX_AREA_FK100': FK100, 'CTX_AREA_NK100': NK100}
    return ApiRequest('domestic_stock.inquire_period_trade_profit', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_price(env_dv, fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS domestic_stock.inquire_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 종목코드 (ex 005930 삼성전자), ETN은 종목코드 6자리 앞에 Q 입력 필수)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-price'
    if env_dv == '' or env_dv is None:
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if fid_cond_mrkt_div_code == '' or fid_cond_mrkt_div_code is None:
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX, NX:NXT, UN:통합')")
    if fid_input_iscd == '' or fid_input_iscd is None:
        raise ValueError("fid_input_iscd is required (e.g. '종목코드 (ex 005930 삼성전자), ETN은 종목코드 6자리 앞에 Q 입력 필수')")
    if env_dv == 'real':
        tr_id = 'FHKST01010100'
    elif env_dv == 'demo':
        tr_id = 'FHKST01010100'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_price', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_price_2(fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS domestic_stock.inquire_price_2 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-price-2'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_input_iscd == '':
        raise ValueError('fid_input_iscd is required')
    tr_id = 'FHPST01010000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.inquire_price_2', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_psbl_order(env_dv, cano, acnt_prdt_cd, pdno, ord_unpr, ord_dvsn, cma_evlu_amt_icld_yn, ovrs_icld_yn):
    """KIS domestic_stock.inquire_psbl_order 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
cano (str): [필수] 종합계좌번호 (ex. 계좌번호 체계(8-2)의 앞 8자리)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 계좌번호 체계(8-2)의 뒤 2자리)
pdno (str): [필수] 상품번호 (ex. 종목번호(6자리))
ord_unpr (str): [필수] 주문단가 (ex. 1주당 가격)
ord_dvsn (str): [필수] 주문구분 (ex. 01 : 시장가)
cma_evlu_amt_icld_yn (str): [필수] CMA평가금액포함여부 (ex. Y)
ovrs_icld_yn (str): [필수] 해외포함여부 (ex. N)"""
    api_url = '/uapi/domestic-stock/v1/trading/inquire-psbl-order'
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if cano == '':
        raise ValueError("cano is required (e.g. '계좌번호 체계(8-2)의 앞 8자리')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '계좌번호 체계(8-2)의 뒤 2자리')")
    if pdno == '':
        raise ValueError("pdno is required (e.g. '종목번호(6자리)')")
    if ord_unpr == '':
        raise ValueError("ord_unpr is required (e.g. '1주당 가격')")
    if ord_dvsn == '':
        raise ValueError("ord_dvsn is required (e.g. '01 : 시장가')")
    if cma_evlu_amt_icld_yn == '':
        raise ValueError("cma_evlu_amt_icld_yn is required (e.g. 'Y')")
    if ovrs_icld_yn == '':
        raise ValueError("ovrs_icld_yn is required (e.g. 'N')")
    if env_dv == 'real':
        tr_id = 'TTTC8908R'
    elif env_dv == 'demo':
        tr_id = 'VTTC8908R'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'ORD_UNPR': ord_unpr, 'ORD_DVSN': ord_dvsn, 'CMA_EVLU_AMT_ICLD_YN': cma_evlu_amt_icld_yn, 'OVRS_ICLD_YN': ovrs_icld_yn}
    return ApiRequest('domestic_stock.inquire_psbl_order', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_psbl_rvsecncl(cano, acnt_prdt_cd, inqr_dvsn_1, inqr_dvsn_2, FK100='', NK100='', tr_cont=''):
    """KIS domestic_stock.inquire_psbl_rvsecncl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. 계좌번호 체계(8-2)의 앞 8자리)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 계좌번호 체계(8-2)의 뒤 2자리)
inqr_dvsn_1 (str): [필수] 조회구분1 (ex. 0: 주문, 1: 종목)
inqr_dvsn_2 (str): [필수] 조회구분2 (ex. 0: 전체, 1: 매도, 2: 매수)
FK100 (str): 연속조회검색조건100
NK100 (str): 연속조회키100
tr_cont (str): 연속거래여부"""
    api_url = '/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl'
    if cano == '':
        raise ValueError("cano is required (e.g. '계좌번호 체계(8-2)의 앞 8자리')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '계좌번호 체계(8-2)의 뒤 2자리')")
    if inqr_dvsn_1 == '':
        raise ValueError("inqr_dvsn_1 is required (e.g. '0: 주문, 1: 종목')")
    if inqr_dvsn_2 == '':
        raise ValueError("inqr_dvsn_2 is required (e.g. '0: 전체, 1: 매도, 2: 매수')")
    tr_id = 'TTTC0084R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'INQR_DVSN_1': inqr_dvsn_1, 'INQR_DVSN_2': inqr_dvsn_2, 'CTX_AREA_FK100': FK100, 'CTX_AREA_NK100': NK100}
    return ApiRequest('domestic_stock.inquire_psbl_rvsecncl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_psbl_sell(cano, acnt_prdt_cd, pdno, tr_cont=''):
    """KIS domestic_stock.inquire_psbl_sell 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호
acnt_prdt_cd (str): 계좌상품코드
pdno (str): 보유종목 코드 ex)000660
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/trading/inquire-psbl-sell'
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not pdno:
        logger.error("pdno is required. (e.g. '000660')")
        raise ValueError("pdno is required. (e.g. '000660')")
    tr_id = 'TTTC8408R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno}
    return ApiRequest('domestic_stock.inquire_psbl_sell', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_time_dailychartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_hour_1, fid_input_date_1, fid_pw_data_incu_yn='N', fid_fake_tick_incu_yn=''):
    """KIS domestic_stock.inquire_time_dailychartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 시장 분류 코드 (ex. J:주식,NX:NXT,UN:통합)
fid_input_iscd (str): [필수] 종목코드 (ex. 123456)
fid_input_hour_1 (str): [필수] 입력 시간1 (ex. 130000)
fid_input_date_1 (str): [필수] 입력 날짜1 (ex. 20241023)
fid_pw_data_incu_yn (str): 과거 데이터 포함 여부 (기본값: "N")
fid_fake_tick_incu_yn (str): 허봉 포함 여부 (기본값: "")"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J', 'NX', 'UN')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if fid_input_hour_1 == '':
        raise ValueError("fid_input_hour_1 is required (e.g. '130000')")
    if fid_input_date_1 == '':
        raise ValueError("fid_input_date_1 is required (e.g. '20241023')")
    tr_id = 'FHKST03010230'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_HOUR_1': fid_input_hour_1, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_PW_DATA_INCU_YN': fid_pw_data_incu_yn, 'FID_FAKE_TICK_INCU_YN': fid_fake_tick_incu_yn}
    return ApiRequest('domestic_stock.inquire_time_dailychartprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_time_indexchartprice(fid_cond_mrkt_div_code, fid_etc_cls_code, fid_input_iscd, fid_input_hour_1, fid_pw_data_incu_yn, tr_cont=''):
    """KIS domestic_stock.inquire_time_indexchartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): FID 조건 시장 분류 코드 (예: 'U')
fid_etc_cls_code (str): FID 기타 구분 코드 (예: '0' 기본, '1' 장마감, 시간외 제외)
fid_input_iscd (str): FID 입력 종목코드 (예: '0001' 종합, '0002' 대형주)
fid_input_hour_1 (str): FID 입력 시간1 (예: '30', '60', '600', '3600')
fid_pw_data_incu_yn (str): FID 과거 데이터 포함 여부 (예: 'Y' 과거, 'N' 당일)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-time-indexchartprice'
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'U')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'U')")
    if not fid_etc_cls_code:
        logger.error("fid_etc_cls_code is required. (e.g. '0')")
        raise ValueError("fid_etc_cls_code is required. (e.g. '0')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0001')")
        raise ValueError("fid_input_iscd is required. (e.g. '0001')")
    if not fid_input_hour_1:
        logger.error("fid_input_hour_1 is required. (e.g. '30')")
        raise ValueError("fid_input_hour_1 is required. (e.g. '30')")
    if not fid_pw_data_incu_yn:
        logger.error("fid_pw_data_incu_yn is required. (e.g. 'Y')")
        raise ValueError("fid_pw_data_incu_yn is required. (e.g. 'Y')")
    tr_id = 'FHKUP03500200'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_ETC_CLS_CODE': fid_etc_cls_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_HOUR_1': fid_input_hour_1, 'FID_PW_DATA_INCU_YN': fid_pw_data_incu_yn}
    return ApiRequest('domestic_stock.inquire_time_indexchartprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_time_itemchartprice(env_dv, fid_cond_mrkt_div_code, fid_input_iscd, fid_input_hour_1, fid_pw_data_incu_yn, fid_etc_cls_code=''):
    """KIS domestic_stock.inquire_time_itemchartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)
fid_input_hour_1 (str): [필수] 입력 시간1 (ex. 입력시간)
fid_pw_data_incu_yn (str): [필수] 과거 데이터 포함 여부
fid_etc_cls_code (str): [필수] 기타 구분 코드"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice'
    if env_dv == '' or env_dv is None:
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if fid_cond_mrkt_div_code == '' or fid_cond_mrkt_div_code is None:
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX, NX:NXT, UN:통합')")
    if fid_input_iscd == '' or fid_input_iscd is None:
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if fid_input_hour_1 == '' or fid_input_hour_1 is None:
        raise ValueError("fid_input_hour_1 is required (e.g. '입력시간')")
    if fid_pw_data_incu_yn == '' or fid_pw_data_incu_yn is None:
        raise ValueError('fid_pw_data_incu_yn is required')
    if env_dv == 'real' or env_dv == 'demo':
        tr_id = 'FHKST03010200'
    else:
        raise ValueError('env_dv can only be real or demo')
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_HOUR_1': fid_input_hour_1, 'FID_PW_DATA_INCU_YN': fid_pw_data_incu_yn, 'FID_ETC_CLS_CODE': fid_etc_cls_code}
    return ApiRequest('domestic_stock.inquire_time_itemchartprice', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_time_itemconclusion(env_dv, fid_cond_mrkt_div_code, fid_input_iscd, fid_input_hour_1):
    """KIS domestic_stock.inquire_time_itemconclusion 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드
fid_input_hour_1 (str): [필수] 입력 시간1"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion'
    if env_dv == '' or env_dv is None:
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if fid_cond_mrkt_div_code == '' or fid_cond_mrkt_div_code is None:
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX, NX:NXT, UN:통합')")
    if fid_input_iscd == '' or fid_input_iscd is None:
        raise ValueError("fid_input_iscd is required (e.g. '입력 종목코드')")
    if fid_input_hour_1 == '' or fid_input_hour_1 is None:
        raise ValueError("fid_input_hour_1 is required (e.g. '입력 시간1')")
    if env_dv == 'real':
        tr_id = 'FHPST01060000'
    elif env_dv == 'demo':
        tr_id = 'FHPST01060000'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_HOUR_1': fid_input_hour_1}
    return ApiRequest('domestic_stock.inquire_time_itemconclusion', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_time_overtimeconclusion(env_dv, fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code):
    """KIS domestic_stock.inquire_time_overtimeconclusion 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
fid_cond_mrkt_div_code (str): [필수] 조건시장분류코드 (ex. J:주식/ETF/ETN)
fid_input_iscd (str): [필수] 입력종목코드 (ex. 123456(ETN의 경우 Q로 시작 Q500001))
fid_hour_cls_code (str): [필수] 적립금구분코드 (ex. 1: 시간외)"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-time-overtimeconclusion'
    if env_dv == '' or env_dv is None:
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if fid_cond_mrkt_div_code == '' or fid_cond_mrkt_div_code is None:
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:주식/ETF/ETN')")
    if fid_input_iscd == '' or fid_input_iscd is None:
        raise ValueError("fid_input_iscd is required (e.g. '123456(ETN의 경우 Q로 시작 Q500001)')")
    if fid_hour_cls_code == '' or fid_hour_cls_code is None:
        raise ValueError("fid_hour_cls_code is required (e.g. '1: 시간외')")
    if env_dv == 'real':
        tr_id = 'FHPST02310000'
    elif env_dv == 'demo':
        tr_id = 'FHPST02310000'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_HOUR_CLS_CODE': fid_hour_cls_code}
    return ApiRequest('domestic_stock.inquire_time_overtimeconclusion', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_vi_status(fid_div_cls_code, fid_cond_scr_div_code, fid_mrkt_cls_code, fid_input_iscd, fid_rank_sort_cls_code, fid_input_date_1, fid_trgt_cls_code, fid_trgt_exls_cls_code, tr_cont=''):
    """KIS domestic_stock.inquire_vi_status 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_div_cls_code (str): 0:전체 1:상승 2:하락
fid_cond_scr_div_code (str): 20139
fid_mrkt_cls_code (str): 0:전체 K:거래소 Q:코스닥
fid_input_iscd (str): 종목코드
fid_rank_sort_cls_code (str): 0:전체 1:정적 2:동적 3:정적&동적
fid_input_date_1 (str): 영업일
fid_trgt_cls_code (str): 대상 구분 코드
fid_trgt_exls_cls_code (str): 대상 제외 구분 코드
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/inquire-vi-status'
    logger = logging.getLogger(__name__)
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20139')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20139')")
    if not fid_mrkt_cls_code:
        logger.error("fid_mrkt_cls_code is required. (e.g. '0')")
        raise ValueError("fid_mrkt_cls_code is required. (e.g. '0')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '0')")
    if not fid_input_date_1:
        logger.error("fid_input_date_1 is required. (e.g. '20200420')")
        raise ValueError("fid_input_date_1 is required. (e.g. '20200420')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    tr_id = 'FHPST01390000'
    params = {'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_MRKT_CLS_CODE': fid_mrkt_cls_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_TRGT_CLS_CODE': fid_trgt_cls_code, 'FID_TRGT_EXLS_CLS_CODE': fid_trgt_exls_cls_code}
    return ApiRequest('domestic_stock.inquire_vi_status', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def intgr_margin(cano, acnt_prdt_cd, cma_evlu_amt_icld_yn, wcrc_frcr_dvsn_cd, fwex_ctrt_frcr_dvsn_cd):
    """KIS domestic_stock.intgr_margin 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. 12345678)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 01)
cma_evlu_amt_icld_yn (str): [필수] CMA평가금액포함여부 (ex. Y: 포함, N: 미포함)
wcrc_frcr_dvsn_cd (str): [필수] 원화외화구분코드 (ex. 01: 외화기준, 02: 원화기준)
fwex_ctrt_frcr_dvsn_cd (str): [필수] 선도환계약외화구분코드 (ex. 01: 외화기준, 02: 원화기준)"""
    api_url = '/uapi/domestic-stock/v1/trading/intgr-margin'
    if cano == '':
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '01')")
    if cma_evlu_amt_icld_yn == '':
        raise ValueError("cma_evlu_amt_icld_yn is required (e.g. 'Y' or 'N')")
    if wcrc_frcr_dvsn_cd == '':
        raise ValueError("wcrc_frcr_dvsn_cd is required (e.g. '01' or '02')")
    if fwex_ctrt_frcr_dvsn_cd == '':
        raise ValueError("fwex_ctrt_frcr_dvsn_cd is required (e.g. '01' or '02')")
    tr_id = 'TTTC0869R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'CMA_EVLU_AMT_ICLD_YN': cma_evlu_amt_icld_yn, 'WCRC_FRCR_DVSN_CD': wcrc_frcr_dvsn_cd, 'FWEX_CTRT_FRCR_DVSN_CD': fwex_ctrt_frcr_dvsn_cd}
    return ApiRequest('domestic_stock.intgr_margin', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def intstock_grouplist(type, fid_etc_cls_code, user_id):
    """KIS domestic_stock.intstock_grouplist 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
type (str): [필수] 관심종목구분코드 (ex. 1)
fid_etc_cls_code (str): [필수] FID 기타 구분 코드 (ex. 00)
user_id (str): [필수] 사용자 ID"""
    api_url = '/uapi/domestic-stock/v1/quotations/intstock-grouplist'
    if type == '':
        raise ValueError("type is required (e.g. '1')")
    if fid_etc_cls_code == '':
        raise ValueError("fid_etc_cls_code is required (e.g. '00')")
    if user_id == '':
        raise ValueError('user_id is required')
    tr_id = 'HHKCM113004C7'
    params = {'TYPE': type, 'FID_ETC_CLS_CODE': fid_etc_cls_code, 'USER_ID': user_id}
    return ApiRequest('domestic_stock.intstock_grouplist', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def intstock_multprice(fid_cond_mrkt_div_code_1, fid_input_iscd_1, fid_cond_mrkt_div_code_2=None, fid_input_iscd_2=None, fid_cond_mrkt_div_code_3=None, fid_input_iscd_3=None, fid_cond_mrkt_div_code_4=None, fid_input_iscd_4=None, fid_cond_mrkt_div_code_5=None, fid_input_iscd_5=None, fid_cond_mrkt_div_code_6=None, fid_input_iscd_6=None, fid_cond_mrkt_div_code_7=None, fid_input_iscd_7=None, fid_cond_mrkt_div_code_8=None, fid_input_iscd_8=None, fid_cond_mrkt_div_code_9=None, fid_input_iscd_9=None, fid_cond_mrkt_div_code_10=None, fid_input_iscd_10=None, fid_cond_mrkt_div_code_11=None, fid_input_iscd_11=None, fid_cond_mrkt_div_code_12=None, fid_input_iscd_12=None, fid_cond_mrkt_div_code_13=None, fid_input_iscd_13=None, fid_cond_mrkt_div_code_14=None, fid_input_iscd_14=None, fid_cond_mrkt_div_code_15=None, fid_input_iscd_15=None, fid_cond_mrkt_div_code_16=None, fid_input_iscd_16=None, fid_cond_mrkt_div_code_17=None, fid_input_iscd_17=None, fid_cond_mrkt_div_code_18=None, fid_input_iscd_18=None, fid_cond_mrkt_div_code_19=None, fid_input_iscd_19=None, fid_cond_mrkt_div_code_20=None, fid_input_iscd_20=None, fid_cond_mrkt_div_code_21=None, fid_input_iscd_21=None, fid_cond_mrkt_div_code_22=None, fid_input_iscd_22=None, fid_cond_mrkt_div_code_23=None, fid_input_iscd_23=None, fid_cond_mrkt_div_code_24=None, fid_input_iscd_24=None, fid_cond_mrkt_div_code_25=None, fid_input_iscd_25=None, fid_cond_mrkt_div_code_26=None, fid_input_iscd_26=None, fid_cond_mrkt_div_code_27=None, fid_input_iscd_27=None, fid_cond_mrkt_div_code_28=None, fid_input_iscd_28=None, fid_cond_mrkt_div_code_29=None, fid_input_iscd_29=None, fid_cond_mrkt_div_code_30=None, fid_input_iscd_30=None):
    """KIS domestic_stock.intstock_multprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code_1 (str): [필수] 조건 시장 분류 코드1 (ex. J:KRX, NX:NXT)
fid_input_iscd_1 (str): [필수] 입력 종목코드1 (ex. 123456)
fid_cond_mrkt_div_code_2 (Optional[str]): 조건 시장 분류 코드2
fid_input_iscd_2 (Optional[str]): 입력 종목코드2
fid_cond_mrkt_div_code_3 (Optional[str]): 조건 시장 분류 코드3
fid_input_iscd_3 (Optional[str]): 입력 종목코드3
fid_cond_mrkt_div_code_4 (Optional[str]): 조건 시장 분류 코드4
fid_input_iscd_4 (Optional[str]): 입력 종목코드4
fid_cond_mrkt_div_code_5 (Optional[str]): 조건 시장 분류 코드5
fid_input_iscd_5 (Optional[str]): 입력 종목코드5
fid_cond_mrkt_div_code_6 (Optional[str]): 조건 시장 분류 코드6
fid_input_iscd_6 (Optional[str]): 입력 종목코드6
fid_cond_mrkt_div_code_7 (Optional[str]): 조건 시장 분류 코드7
fid_input_iscd_7 (Optional[str]): 입력 종목코드7
fid_cond_mrkt_div_code_8 (Optional[str]): 조건 시장 분류 코드8
fid_input_iscd_8 (Optional[str]): 입력 종목코드8
fid_cond_mrkt_div_code_9 (Optional[str]): 조건 시장 분류 코드9
fid_input_iscd_9 (Optional[str]): 입력 종목코드9
fid_cond_mrkt_div_code_10 (Optional[str]): 조건 시장 분류 코드10
fid_input_iscd_10 (Optional[str]): 입력 종목코드10
fid_cond_mrkt_div_code_11 (Optional[str]): 조건 시장 분류 코드11
fid_input_iscd_11 (Optional[str]): 입력 종목코드11
fid_cond_mrkt_div_code_12 (Optional[str]): 조건 시장 분류 코드12
fid_input_iscd_12 (Optional[str]): 입력 종목코드12
fid_cond_mrkt_div_code_13 (Optional[str]): 조건 시장 분류 코드13
fid_input_iscd_13 (Optional[str]): 입력 종목코드13
fid_cond_mrkt_div_code_14 (Optional[str]): 조건 시장 분류 코드14
fid_input_iscd_14 (Optional[str]): 입력 종목코드14
fid_cond_mrkt_div_code_15 (Optional[str]): 조건 시장 분류 코드15
fid_input_iscd_15 (Optional[str]): 입력 종목코드15
fid_cond_mrkt_div_code_16 (Optional[str]): 조건 시장 분류 코드16
fid_input_iscd_16 (Optional[str]): 입력 종목코드16
fid_cond_mrkt_div_code_17 (Optional[str]): 조건 시장 분류 코드17
fid_input_iscd_17 (Optional[str]): 입력 종목코드17
fid_cond_mrkt_div_code_18 (Optional[str]): 조건 시장 분류 코드18
fid_input_iscd_18 (Optional[str]): 입력 종목코드18
fid_cond_mrkt_div_code_19 (Optional[str]): 조건 시장 분류 코드19
fid_input_iscd_19 (Optional[str]): 입력 종목코드19
fid_cond_mrkt_div_code_20 (Optional[str]): 조건 시장 분류 코드20
fid_input_iscd_20 (Optional[str]): 입력 종목코드20
fid_cond_mrkt_div_code_21 (Optional[str]): 조건 시장 분류 코드21
fid_input_iscd_21 (Optional[str]): 입력 종목코드21
fid_cond_mrkt_div_code_22 (Optional[str]): 조건 시장 분류 코드22
fid_input_iscd_22 (Optional[str]): 입력 종목코드22
fid_cond_mrkt_div_code_23 (Optional[str]): 조건 시장 분류 코드23
fid_input_iscd_23 (Optional[str]): 입력 종목코드23
fid_cond_mrkt_div_code_24 (Optional[str]): 조건 시장 분류 코드24
fid_input_iscd_24 (Optional[str]): 입력 종목코드24
fid_cond_mrkt_div_code_25 (Optional[str]): 조건 시장 분류 코드25
fid_input_iscd_25 (Optional[str]): 입력 종목코드25
fid_cond_mrkt_div_code_26 (Optional[str]): 조건 시장 분류 코드26
fid_input_iscd_26 (Optional[str]): 입력 종목코드26
fid_cond_mrkt_div_code_27 (Optional[str]): 조건 시장 분류 코드27
fid_input_iscd_27 (Optional[str]): 입력 종목코드27
fid_cond_mrkt_div_code_28 (Optional[str]): 조건 시장 분류 코드28
fid_input_iscd_28 (Optional[str]): 입력 종목코드28
fid_cond_mrkt_div_code_29 (Optional[str]): 조건 시장 분류 코드29
fid_input_iscd_29 (Optional[str]): 입력 종목코드29
fid_cond_mrkt_div_code_30 (Optional[str]): 조건 시장 분류 코드30
fid_input_iscd_30 (Optional[str]): 입력 종목코드30"""
    api_url = '/uapi/domestic-stock/v1/quotations/intstock-multprice'
    if fid_cond_mrkt_div_code_1 == '':
        raise ValueError("fid_cond_mrkt_div_code_1 is required (e.g. 'J')")
    if fid_input_iscd_1 == '':
        raise ValueError("fid_input_iscd_1 is required (e.g. '123456')")
    tr_id = 'FHKST11300006'
    params = {'FID_COND_MRKT_DIV_CODE_1': fid_cond_mrkt_div_code_1, 'FID_INPUT_ISCD_1': fid_input_iscd_1}
    if fid_cond_mrkt_div_code_2 is not None:
        params['FID_COND_MRKT_DIV_CODE_2'] = fid_cond_mrkt_div_code_2
    if fid_input_iscd_2 is not None:
        params['FID_INPUT_ISCD_2'] = fid_input_iscd_2
    if fid_cond_mrkt_div_code_3 is not None:
        params['FID_COND_MRKT_DIV_CODE_3'] = fid_cond_mrkt_div_code_3
    if fid_input_iscd_3 is not None:
        params['FID_INPUT_ISCD_3'] = fid_input_iscd_3
    if fid_cond_mrkt_div_code_4 is not None:
        params['FID_COND_MRKT_DIV_CODE_4'] = fid_cond_mrkt_div_code_4
    if fid_input_iscd_4 is not None:
        params['FID_INPUT_ISCD_4'] = fid_input_iscd_4
    if fid_cond_mrkt_div_code_5 is not None:
        params['FID_COND_MRKT_DIV_CODE_5'] = fid_cond_mrkt_div_code_5
    if fid_input_iscd_5 is not None:
        params['FID_INPUT_ISCD_5'] = fid_input_iscd_5
    if fid_cond_mrkt_div_code_6 is not None:
        params['FID_COND_MRKT_DIV_CODE_6'] = fid_cond_mrkt_div_code_6
    if fid_input_iscd_6 is not None:
        params['FID_INPUT_ISCD_6'] = fid_input_iscd_6
    if fid_cond_mrkt_div_code_7 is not None:
        params['FID_COND_MRKT_DIV_CODE_7'] = fid_cond_mrkt_div_code_7
    if fid_input_iscd_7 is not None:
        params['FID_INPUT_ISCD_7'] = fid_input_iscd_7
    if fid_cond_mrkt_div_code_8 is not None:
        params['FID_COND_MRKT_DIV_CODE_8'] = fid_cond_mrkt_div_code_8
    if fid_input_iscd_8 is not None:
        params['FID_INPUT_ISCD_8'] = fid_input_iscd_8
    if fid_cond_mrkt_div_code_9 is not None:
        params['FID_COND_MRKT_DIV_CODE_9'] = fid_cond_mrkt_div_code_9
    if fid_input_iscd_9 is not None:
        params['FID_INPUT_ISCD_9'] = fid_input_iscd_9
    if fid_cond_mrkt_div_code_10 is not None:
        params['FID_COND_MRKT_DIV_CODE_10'] = fid_cond_mrkt_div_code_10
    if fid_input_iscd_10 is not None:
        params['FID_INPUT_ISCD_10'] = fid_input_iscd_10
    if fid_cond_mrkt_div_code_11 is not None:
        params['FID_COND_MRKT_DIV_CODE_11'] = fid_cond_mrkt_div_code_11
    if fid_input_iscd_11 is not None:
        params['FID_INPUT_ISCD_11'] = fid_input_iscd_11
    if fid_cond_mrkt_div_code_12 is not None:
        params['FID_COND_MRKT_DIV_CODE_12'] = fid_cond_mrkt_div_code_12
    if fid_input_iscd_12 is not None:
        params['FID_INPUT_ISCD_12'] = fid_input_iscd_12
    if fid_cond_mrkt_div_code_13 is not None:
        params['FID_COND_MRKT_DIV_CODE_13'] = fid_cond_mrkt_div_code_13
    if fid_input_iscd_13 is not None:
        params['FID_INPUT_ISCD_13'] = fid_input_iscd_13
    if fid_cond_mrkt_div_code_14 is not None:
        params['FID_COND_MRKT_DIV_CODE_14'] = fid_cond_mrkt_div_code_14
    if fid_input_iscd_14 is not None:
        params['FID_INPUT_ISCD_14'] = fid_input_iscd_14
    if fid_cond_mrkt_div_code_15 is not None:
        params['FID_COND_MRKT_DIV_CODE_15'] = fid_cond_mrkt_div_code_15
    if fid_input_iscd_15 is not None:
        params['FID_INPUT_ISCD_15'] = fid_input_iscd_15
    if fid_cond_mrkt_div_code_16 is not None:
        params['FID_COND_MRKT_DIV_CODE_16'] = fid_cond_mrkt_div_code_16
    if fid_input_iscd_16 is not None:
        params['FID_INPUT_ISCD_16'] = fid_input_iscd_16
    if fid_cond_mrkt_div_code_17 is not None:
        params['FID_COND_MRKT_DIV_CODE_17'] = fid_cond_mrkt_div_code_17
    if fid_input_iscd_17 is not None:
        params['FID_INPUT_ISCD_17'] = fid_input_iscd_17
    if fid_cond_mrkt_div_code_18 is not None:
        params['FID_COND_MRKT_DIV_CODE_18'] = fid_cond_mrkt_div_code_18
    if fid_input_iscd_18 is not None:
        params['FID_INPUT_ISCD_18'] = fid_input_iscd_18
    if fid_cond_mrkt_div_code_19 is not None:
        params['FID_COND_MRKT_DIV_CODE_19'] = fid_cond_mrkt_div_code_19
    if fid_input_iscd_19 is not None:
        params['FID_INPUT_ISCD_19'] = fid_input_iscd_19
    if fid_cond_mrkt_div_code_20 is not None:
        params['FID_COND_MRKT_DIV_CODE_20'] = fid_cond_mrkt_div_code_20
    if fid_input_iscd_20 is not None:
        params['FID_INPUT_ISCD_20'] = fid_input_iscd_20
    if fid_cond_mrkt_div_code_21 is not None:
        params['FID_COND_MRKT_DIV_CODE_21'] = fid_cond_mrkt_div_code_21
    if fid_input_iscd_21 is not None:
        params['FID_INPUT_ISCD_21'] = fid_input_iscd_21
    if fid_cond_mrkt_div_code_22 is not None:
        params['FID_COND_MRKT_DIV_CODE_22'] = fid_cond_mrkt_div_code_22
    if fid_input_iscd_22 is not None:
        params['FID_INPUT_ISCD_22'] = fid_input_iscd_22
    if fid_cond_mrkt_div_code_23 is not None:
        params['FID_COND_MRKT_DIV_CODE_23'] = fid_cond_mrkt_div_code_23
    if fid_input_iscd_23 is not None:
        params['FID_INPUT_ISCD_23'] = fid_input_iscd_23
    if fid_cond_mrkt_div_code_24 is not None:
        params['FID_COND_MRKT_DIV_CODE_24'] = fid_cond_mrkt_div_code_24
    if fid_input_iscd_24 is not None:
        params['FID_INPUT_ISCD_24'] = fid_input_iscd_24
    if fid_cond_mrkt_div_code_25 is not None:
        params['FID_COND_MRKT_DIV_CODE_25'] = fid_cond_mrkt_div_code_25
    if fid_input_iscd_25 is not None:
        params['FID_INPUT_ISCD_25'] = fid_input_iscd_25
    if fid_cond_mrkt_div_code_26 is not None:
        params['FID_COND_MRKT_DIV_CODE_26'] = fid_cond_mrkt_div_code_26
    if fid_input_iscd_26 is not None:
        params['FID_INPUT_ISCD_26'] = fid_input_iscd_26
    if fid_cond_mrkt_div_code_27 is not None:
        params['FID_COND_MRKT_DIV_CODE_27'] = fid_cond_mrkt_div_code_27
    if fid_input_iscd_27 is not None:
        params['FID_INPUT_ISCD_27'] = fid_input_iscd_27
    if fid_cond_mrkt_div_code_28 is not None:
        params['FID_COND_MRKT_DIV_CODE_28'] = fid_cond_mrkt_div_code_28
    if fid_input_iscd_28 is not None:
        params['FID_INPUT_ISCD_28'] = fid_input_iscd_28
    if fid_cond_mrkt_div_code_29 is not None:
        params['FID_COND_MRKT_DIV_CODE_29'] = fid_cond_mrkt_div_code_29
    if fid_input_iscd_29 is not None:
        params['FID_INPUT_ISCD_29'] = fid_input_iscd_29
    if fid_cond_mrkt_div_code_30 is not None:
        params['FID_COND_MRKT_DIV_CODE_30'] = fid_cond_mrkt_div_code_30
    if fid_input_iscd_30 is not None:
        params['FID_INPUT_ISCD_30'] = fid_input_iscd_30
    return ApiRequest('domestic_stock.intstock_multprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def intstock_stocklist_by_group(type, user_id, inter_grp_code, fid_etc_cls_code, data_rank='', inter_grp_name='', hts_kor_isnm='', cntg_cls_code=''):
    """KIS domestic_stock.intstock_stocklist_by_group 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
type (str): [필수] 관심종목구분코드 (ex. 1)
user_id (str): [필수] 사용자 ID
inter_grp_code (str): [필수] 관심 그룹 코드 (ex. 001)
fid_etc_cls_code (str): [필수] 기타 구분 코드 (ex. 4)
data_rank (str): 데이터 순위
inter_grp_name (str): 관심 그룹 명
hts_kor_isnm (str): HTS 한글 종목명
cntg_cls_code (str): 체결 구분 코드"""
    api_url = '/uapi/domestic-stock/v1/quotations/intstock-stocklist-by-group'
    if type == '':
        raise ValueError("type is required (e.g. '1')")
    if user_id == '':
        raise ValueError('user_id is required')
    if inter_grp_code == '':
        raise ValueError("inter_grp_code is required (e.g. '001')")
    if fid_etc_cls_code == '':
        raise ValueError("fid_etc_cls_code is required (e.g. '4')")
    tr_id = 'HHKCM113004C6'
    params = {'TYPE': type, 'USER_ID': user_id, 'INTER_GRP_CODE': inter_grp_code, 'FID_ETC_CLS_CODE': fid_etc_cls_code, 'DATA_RANK': data_rank, 'INTER_GRP_NAME': inter_grp_name, 'HTS_KOR_ISNM': hts_kor_isnm, 'CNTG_CLS_CODE': cntg_cls_code}
    return ApiRequest('domestic_stock.intstock_stocklist_by_group', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def invest_opbysec(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_date_1, fid_input_date_2, tr_cont=''):
    """KIS domestic_stock.invest_opbysec 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): J(시장 구분 코드)
fid_cond_scr_div_code (str): 16634(Primary key)
fid_input_iscd (str): 회원사코드 (kis developers 포탈 사이트 포럼-> FAQ -> 종목정보 다운로드(국내) 참조)
fid_div_cls_code (str): 전체(0) 매수(1) 중립(2) 매도(3)
fid_input_date_1 (str): 이후 ~
fid_input_date_2 (str): ~ 이전
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/invest-opbysec'
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '16634')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '16634')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '005930')")
        raise ValueError("fid_input_iscd is required. (e.g. '005930')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    if not fid_input_date_1:
        logger.error("fid_input_date_1 is required. (e.g. '20230101')")
        raise ValueError("fid_input_date_1 is required. (e.g. '20230101')")
    if not fid_input_date_2:
        logger.error("fid_input_date_2 is required. (e.g. '20231231')")
        raise ValueError("fid_input_date_2 is required. (e.g. '20231231')")
    tr_id = 'FHKST663400C0'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2}
    return ApiRequest('domestic_stock.invest_opbysec', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def invest_opinion(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2, tr_cont=''):
    """KIS domestic_stock.invest_opinion 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): J(시장 구분 코드)
fid_cond_scr_div_code (str): 16633(Primary key)
fid_input_iscd (str): 종목코드(ex) 005930(삼성전자))
fid_input_date_1 (str): 이후 ~(ex) 0020231113)
fid_input_date_2 (str): ~ 이전(ex) 0020240513)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/invest-opinion'
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '16633')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '16633')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '005930')")
        raise ValueError("fid_input_iscd is required. (e.g. '005930')")
    if not fid_input_date_1:
        logger.error("fid_input_date_1 is required. (e.g. '20231113')")
        raise ValueError("fid_input_date_1 is required. (e.g. '20231113')")
    if not fid_input_date_2:
        logger.error("fid_input_date_2 is required. (e.g. '20240513')")
        raise ValueError("fid_input_date_2 is required. (e.g. '20240513')")
    tr_id = 'FHKST663300C0'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2}
    return ApiRequest('domestic_stock.invest_opinion', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def investor_program_trade_today(mrkt_div_cls_code):
    """KIS domestic_stock.investor_program_trade_today 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
mrkt_div_cls_code (str): [필수] 시장 구분 코드 (ex. 1:코스피, 4:코스닥)"""
    api_url = '/uapi/domestic-stock/v1/quotations/investor-program-trade-today'
    if mrkt_div_cls_code == '':
        raise ValueError("mrkt_div_cls_code is required (e.g. '1' or '4')")
    tr_id = 'HHPPG046600C1'
    params = {'MRKT_DIV_CLS_CODE': mrkt_div_cls_code}
    return ApiRequest('domestic_stock.investor_program_trade_today', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def investor_trade_by_stock_daily(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_org_adj_prc, fid_etc_cls_code, tr_cont=''):
    """KIS domestic_stock.investor_trade_by_stock_daily 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): J:KRX, NX:NXT, UN:통합
fid_input_iscd (str): 종목번호 (6자리)
fid_input_date_1 (str): 입력 날짜(20250812)
fid_org_adj_prc (str): 공란 입력
fid_etc_cls_code (str): 공란 입력
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily'
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '005930')")
        raise ValueError("fid_input_iscd is required. (e.g. '005930')")
    if not fid_input_date_1:
        logger.error("fid_input_date_1 is required. (e.g. '20250812')")
        raise ValueError("fid_input_date_1 is required. (e.g. '20250812')")
    tr_id = 'FHPTJ04160001'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_ORG_ADJ_PRC': fid_org_adj_prc, 'FID_ETC_CLS_CODE': fid_etc_cls_code}
    return ApiRequest('domestic_stock.investor_trade_by_stock_daily', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def investor_trend_estimate(mksc_shrn_iscd):
    """KIS domestic_stock.investor_trend_estimate 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
mksc_shrn_iscd (str): [필수] 종목코드 (ex. 123456)"""
    api_url = '/uapi/domestic-stock/v1/quotations/investor-trend-estimate'
    if mksc_shrn_iscd == '':
        raise ValueError("mksc_shrn_iscd is required (ex. '123456')")
    tr_id = 'HHPTJ04160200'
    params = {'MKSC_SHRN_ISCD': mksc_shrn_iscd}
    return ApiRequest('domestic_stock.investor_trend_estimate', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def ksdinfo_bonus_issue(cts, f_dt, t_dt, sht_cd, tr_cont=''):
    """KIS domestic_stock.ksdinfo_bonus_issue 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cts (str): 공백
f_dt (str): 일자 ~
t_dt (str): ~ 일자
sht_cd (str): 공백: 전체, 특정종목 조회시 : 종목코드
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/bonus-issue'
    logger = logging.getLogger(__name__)
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20230101')")
        raise ValueError("f_dt is required. (e.g. '20230101')")
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231231')")
        raise ValueError("t_dt is required. (e.g. '20231231')")
    tr_id = 'HHKDB669101C0'
    params = {'CTS': cts, 'F_DT': f_dt, 'T_DT': t_dt, 'SHT_CD': sht_cd}
    return ApiRequest('domestic_stock.ksdinfo_bonus_issue', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_cap_dcrs(cts, f_dt, t_dt, sht_cd, tr_cont=''):
    """KIS domestic_stock.ksdinfo_cap_dcrs 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cts (str): 공백
f_dt (str): 일자 ~
t_dt (str): ~ 일자
sht_cd (str): 공백: 전체,  특정종목 조회시 : 종목코드
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/cap-dcrs'
    logger = logging.getLogger(__name__)
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20230101')")
        raise ValueError("f_dt is required. (e.g. '20230101')")
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231231')")
        raise ValueError("t_dt is required. (e.g. '20231231')")
    tr_id = 'HHKDB669106C0'
    params = {'CTS': cts, 'F_DT': f_dt, 'T_DT': t_dt, 'SHT_CD': sht_cd}
    return ApiRequest('domestic_stock.ksdinfo_cap_dcrs', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_dividend(cts, gb1, f_dt, t_dt, sht_cd, high_gb, tr_cont=''):
    """KIS domestic_stock.ksdinfo_dividend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cts (str): 공백
gb1 (str): 0:배당전체, 1:결산배당, 2:중간배당
f_dt (str): 일자 ~
t_dt (str): ~ 일자
sht_cd (str): 공백: 전체,  특정종목 조회시 : 종목코드
high_gb (str): 공백
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/dividend'
    logger = logging.getLogger(__name__)
    if not gb1:
        logger.error("gb1 is required. (e.g. '0')")
        raise ValueError("gb1 is required. (e.g. '0')")
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20230101')")
        raise ValueError("f_dt is required. (e.g. '20230101')")
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231231')")
        raise ValueError("t_dt is required. (e.g. '20231231')")
    tr_id = 'HHKDB669102C0'
    params = {'CTS': cts, 'GB1': gb1, 'F_DT': f_dt, 'T_DT': t_dt, 'SHT_CD': sht_cd, 'HIGH_GB': high_gb}
    return ApiRequest('domestic_stock.ksdinfo_dividend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_forfeit(sht_cd, t_dt, f_dt, cts, tr_cont=''):
    """KIS domestic_stock.ksdinfo_forfeit 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
sht_cd (str): 공백: 전체, 특정종목 조회시 : 종목코드
t_dt (str): ~ 일자
f_dt (str): 일자 ~
cts (str): 공백
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/forfeit'
    logger = logging.getLogger(__name__)
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20240315')")
        raise ValueError("t_dt is required. (e.g. '20240315')")
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20240314')")
        raise ValueError("f_dt is required. (e.g. '20240314')")
    tr_id = 'HHKDB669109C0'
    params = {'SHT_CD': sht_cd, 'T_DT': t_dt, 'F_DT': f_dt, 'CTS': cts}
    return ApiRequest('domestic_stock.ksdinfo_forfeit', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_list_info(sht_cd, t_dt, f_dt, cts, tr_cont=''):
    """KIS domestic_stock.ksdinfo_list_info 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
sht_cd (str): 공백: 전체, 특정종목 조회시 : 종목코드
t_dt (str): ~ 일자
f_dt (str): 일자 ~
cts (str): 공백
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/list-info'
    logger = logging.getLogger(__name__)
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231010')")
        raise ValueError("t_dt is required. (e.g. '20231010')")
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20231001')")
        raise ValueError("f_dt is required. (e.g. '20231001')")
    tr_id = 'HHKDB669107C0'
    params = {'SHT_CD': sht_cd, 'T_DT': t_dt, 'F_DT': f_dt, 'CTS': cts}
    return ApiRequest('domestic_stock.ksdinfo_list_info', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_mand_deposit(t_dt, sht_cd, f_dt, cts, tr_cont=''):
    """KIS domestic_stock.ksdinfo_mand_deposit 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
t_dt (str): 조회 종료 일자 (예: '20230301')
sht_cd (str): 종목코드 (공백: 전체, 특정종목 조회시 : 종목코드)
f_dt (str): 조회 시작 일자 (예: '20230101')
cts (str): CTS (공백)
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/mand-deposit'
    logger = logging.getLogger(__name__)
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20230301')")
        raise ValueError("t_dt is required. (e.g. '20230301')")
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20230101')")
        raise ValueError("f_dt is required. (e.g. '20230101')")
    tr_id = 'HHKDB669110C0'
    params = {'T_DT': t_dt, 'SHT_CD': sht_cd, 'F_DT': f_dt, 'CTS': cts}
    return ApiRequest('domestic_stock.ksdinfo_mand_deposit', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_merger_split(cts, f_dt, t_dt, sht_cd, tr_cont=''):
    """KIS domestic_stock.ksdinfo_merger_split 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cts (str): 공백
f_dt (str): 일자 ~
t_dt (str): ~ 일자
sht_cd (str): 공백: 전체, 특정종목 조회시 : 종목코드
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/merger-split'
    logger = logging.getLogger(__name__)
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20230101')")
        raise ValueError("f_dt is required. (e.g. '20230101')")
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231231')")
        raise ValueError("t_dt is required. (e.g. '20231231')")
    tr_id = 'HHKDB669104C0'
    params = {'CTS': cts, 'F_DT': f_dt, 'T_DT': t_dt, 'SHT_CD': sht_cd}
    return ApiRequest('domestic_stock.ksdinfo_merger_split', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_paidin_capin(cts, gb1, f_dt, t_dt, sht_cd, tr_cont=''):
    """KIS domestic_stock.ksdinfo_paidin_capin 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cts (str): 공백
gb1 (str): 1(청약일별), 2(기준일별)
f_dt (str): 일자 ~
t_dt (str): ~ 일자
sht_cd (str): 공백(전체),  특정종목 조회시(종목코드)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/paidin-capin'
    logger = logging.getLogger(__name__)
    if not gb1:
        logger.error("gb1 is required. (e.g. '1')")
        raise ValueError("gb1 is required. (e.g. '1')")
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20230101')")
        raise ValueError("f_dt is required. (e.g. '20230101')")
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231231')")
        raise ValueError("t_dt is required. (e.g. '20231231')")
    tr_id = 'HHKDB669100C0'
    params = {'CTS': cts, 'GB1': gb1, 'F_DT': f_dt, 'T_DT': t_dt, 'SHT_CD': sht_cd}
    return ApiRequest('domestic_stock.ksdinfo_paidin_capin', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_pub_offer(sht_cd, cts, f_dt, t_dt, tr_cont=''):
    """KIS domestic_stock.ksdinfo_pub_offer 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
sht_cd (str): 공백: 전체, 특정종목 조회시 : 종목코드
cts (str): 공백
f_dt (str): 일자 ~
t_dt (str): ~ 일자
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/pub-offer'
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20230101')")
        raise ValueError("f_dt is required. (e.g. '20230101')")
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231231')")
        raise ValueError("t_dt is required. (e.g. '20231231')")
    tr_id = 'HHKDB669108C0'
    params = {'SHT_CD': sht_cd, 'CTS': cts, 'F_DT': f_dt, 'T_DT': t_dt}
    return ApiRequest('domestic_stock.ksdinfo_pub_offer', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_purreq(sht_cd, t_dt, f_dt, cts, tr_cont=''):
    """KIS domestic_stock.ksdinfo_purreq 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
sht_cd (str): 공백: 전체, 특정종목 조회시 : 종목코드
t_dt (str): ~ 일자
f_dt (str): 일자 ~
cts (str): 공백
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/purreq'
    logger = logging.getLogger(__name__)
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231010')")
        raise ValueError("t_dt is required. (e.g. '20231010')")
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20231001')")
        raise ValueError("f_dt is required. (e.g. '20231001')")
    tr_id = 'HHKDB669103C0'
    params = {'SHT_CD': sht_cd, 'T_DT': t_dt, 'F_DT': f_dt, 'CTS': cts}
    return ApiRequest('domestic_stock.ksdinfo_purreq', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_rev_split(sht_cd, cts, f_dt, t_dt, market_gb, tr_cont=''):
    """KIS domestic_stock.ksdinfo_rev_split 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
sht_cd (str): 공백: 전체, 특정종목 조회시 : 종목코드
cts (str): 공백
f_dt (str): 일자 ~
t_dt (str): ~ 일자
market_gb (str): 0:전체, 1:코스피, 2:코스닥
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/rev-split'
    logger = logging.getLogger(__name__)
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20230101')")
        raise ValueError("f_dt is required. (e.g. '20230101')")
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231231')")
        raise ValueError("t_dt is required. (e.g. '20231231')")
    if market_gb not in ['0', '1', '2']:
        logger.error("market_gb must be one of ['0', '1', '2'].")
        raise ValueError("market_gb must be one of ['0', '1', '2'].")
    tr_id = 'HHKDB669105C0'
    params = {'SHT_CD': sht_cd, 'CTS': cts, 'F_DT': f_dt, 'T_DT': t_dt, 'MARKET_GB': market_gb}
    return ApiRequest('domestic_stock.ksdinfo_rev_split', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def ksdinfo_sharehld_meet(cts, f_dt, t_dt, sht_cd, tr_cont=''):
    """KIS domestic_stock.ksdinfo_sharehld_meet 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cts (str): 공백
f_dt (str): 일자 ~
t_dt (str): ~ 일자
sht_cd (str): 공백: 전체,  특정종목 조회시 : 종목코드
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ksdinfo/sharehld-meet'
    logger = logging.getLogger(__name__)
    if not f_dt:
        logger.error("f_dt is required. (e.g. '20230101')")
        raise ValueError("f_dt is required. (e.g. '20230101')")
    if not t_dt:
        logger.error("t_dt is required. (e.g. '20231231')")
        raise ValueError("t_dt is required. (e.g. '20231231')")
    tr_id = 'HHKDB669111C0'
    params = {'CTS': cts, 'F_DT': f_dt, 'T_DT': t_dt, 'SHT_CD': sht_cd}
    return ApiRequest('domestic_stock.ksdinfo_sharehld_meet', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def market_cap(fid_input_price_2, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_input_iscd, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_vol_cnt, tr_cont=''):
    """KIS domestic_stock.market_cap 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_input_price_2 (str): 입력값 없을때 전체 (~ 가격)
fid_cond_mrkt_div_code (str): 시장구분코드 (J:KRX, NX:NXT)
fid_cond_scr_div_code (str): Unique key( 20174 )
fid_div_cls_code (str): 0: 전체,  1:보통주,  2:우선주
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200
fid_trgt_cls_code (str): 0 : 전체
fid_trgt_exls_cls_code (str): 0 : 전체
fid_input_price_1 (str): 입력값 없을때 전체 (가격 ~)
fid_vol_cnt (str): 입력값 없을때 전체 (거래량 ~)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/market-cap'
    if fid_cond_mrkt_div_code != 'J':
        raise ValueError('조건 시장 분류 코드 확인요망!!!')
    if fid_cond_scr_div_code != '20174':
        raise ValueError('조건 화면 분류 코드 확인요망!!!')
    if fid_div_cls_code not in ['0', '1', '2']:
        raise ValueError('분류 구분 코드 확인요망!!!')
    if fid_input_iscd not in ['0000', '0001', '1001', '2001']:
        raise ValueError('입력 종목코드 확인요망!!!')
    if fid_trgt_cls_code != '0':
        raise ValueError('대상 구분 코드 확인요망!!!')
    if fid_trgt_exls_cls_code != '0':
        raise ValueError('대상 제외 구분 코드 확인요망!!!')
    tr_id = 'FHPST01740000'
    params = {'fid_input_price_2': fid_input_price_2, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_div_cls_code': fid_div_cls_code, 'fid_input_iscd': fid_input_iscd, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_vol_cnt': fid_vol_cnt}
    return ApiRequest('domestic_stock.market_cap', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def market_time():
    """KIS domestic_stock.market_time 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
"""
    api_url = '/uapi/domestic-stock/v1/quotations/market-time'
    tr_id = 'HHMCM000002C0'
    params = {}
    return ApiRequest('domestic_stock.market_time', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def market_value(fid_trgt_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_input_option_1, fid_input_option_2, fid_rank_sort_cls_code, fid_blng_cls_code, fid_trgt_exls_cls_code, tr_cont=''):
    """KIS domestic_stock.market_value 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_trgt_cls_code (str): 0 : 전체
fid_cond_mrkt_div_code (str): 시장구분코드 (J:KRX, NX:NXT)
fid_cond_scr_div_code (str): Unique key( 20179 )
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200
fid_div_cls_code (str): 0: 전체, 1:관리종목, 2:투자주의, 3:투자경고, 4:투자위험예고, 5:투자위험, 6:보통주, 7:우선주
fid_input_price_1 (str): 입력값 없을때 전체 (가격 ~)
fid_input_price_2 (str): 입력값 없을때 전체 (~ 가격)
fid_vol_cnt (str): 입력값 없을때 전체 (거래량 ~)
fid_input_option_1 (str): 회계연도 입력 (ex 2023)
fid_input_option_2 (str): 0: 1/4분기 , 1: 반기, 2: 3/4분기, 3: 결산
fid_rank_sort_cls_code (str): '가치분석(23:PER, 24:PBR, 25:PCR, 26:PSR, 27: EPS, 28:EVA, 29: EBITDA, 30: EV/EBITDA, 31:EBITDA/금융비율'
fid_blng_cls_code (str): 0 : 전체
fid_trgt_exls_cls_code (str): 0 : 전체
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/market-value'
    if fid_trgt_cls_code not in ['0']:
        raise ValueError('대상 구분 코드 확인요망!!!')
    if fid_cond_mrkt_div_code not in ['J']:
        raise ValueError('조건 시장 분류 코드 확인요망!!!')
    if fid_cond_scr_div_code != '20179':
        raise ValueError('조건 화면 분류 코드 확인요망!!!')
    if fid_input_iscd not in ['0000', '0001', '1001', '2001']:
        raise ValueError('입력 종목코드 확인요망!!!')
    if fid_div_cls_code not in ['0', '1', '2', '3', '4', '5', '6', '7']:
        raise ValueError('분류 구분 코드 확인요망!!!')
    if fid_input_option_2 not in ['0', '1', '2', '3']:
        raise ValueError('입력 옵션2 확인요망!!!')
    if fid_rank_sort_cls_code not in ['23', '24', '25', '26', '27', '28', '29', '30', '31']:
        raise ValueError('순위 정렬 구분 코드 확인요망!!!')
    if fid_blng_cls_code not in ['0']:
        raise ValueError('소속 구분 코드 확인요망!!!')
    if fid_trgt_exls_cls_code not in ['0']:
        raise ValueError('대상 제외 구분 코드 확인요망!!!')
    tr_id = 'FHPST01790000'
    params = {'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_input_iscd': fid_input_iscd, 'fid_div_cls_code': fid_div_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_input_price_2': fid_input_price_2, 'fid_vol_cnt': fid_vol_cnt, 'fid_input_option_1': fid_input_option_1, 'fid_input_option_2': fid_input_option_2, 'fid_rank_sort_cls_code': fid_rank_sort_cls_code, 'fid_blng_cls_code': fid_blng_cls_code, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code}
    return ApiRequest('domestic_stock.market_value', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def mktfunds(fid_input_date_1=''):
    """KIS domestic_stock.mktfunds 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_input_date_1 (str): [입력날짜]"""
    api_url = '/uapi/domestic-stock/v1/quotations/mktfunds'
    tr_id = 'FHKST649100C0'
    params = {'FID_INPUT_DATE_1': fid_input_date_1}
    return ApiRequest('domestic_stock.mktfunds', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def near_new_highlow(fid_aply_rang_vol, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_input_cnt_1, fid_input_cnt_2, fid_prc_cls_code, fid_input_iscd, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_aply_rang_prc_1, fid_aply_rang_prc_2, tr_cont=''):
    """KIS domestic_stock.near_new_highlow 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_aply_rang_vol (str): 0: 전체, 100: 100주 이상
fid_cond_mrkt_div_code (str): 시장구분코드 (주식 J)
fid_cond_scr_div_code (str): Unique key(20187)
fid_div_cls_code (str): 0:전체, 1:관리종목, 2:투자주의, 3:투자경고
fid_input_cnt_1 (str): 괴리율 최소
fid_input_cnt_2 (str): 괴리율 최대
fid_prc_cls_code (str): 0:신고근접, 1:신저근접
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200, 4001: KRX100
fid_trgt_cls_code (str): 0: 전체
fid_trgt_exls_cls_code (str): 0:전체, 1:관리종목, 2:투자주의, 3:투자경고, 4:투자위험예고, 5:투자위험, 6:보통주, 7:우선주
fid_aply_rang_prc_1 (str): 가격 ~
fid_aply_rang_prc_2 (str): ~ 가격
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/near-new-highlow'
    if fid_aply_rang_vol not in ['0', '100']:
        raise ValueError('적용 범위 거래량 확인요망!!!')
    if fid_cond_mrkt_div_code != 'J':
        raise ValueError('조건 시장 분류 코드 확인요망!!!')
    if fid_cond_scr_div_code != '20187':
        raise ValueError('조건 화면 분류 코드 확인요망!!!')
    if fid_div_cls_code not in ['0', '1', '2', '3']:
        raise ValueError('분류 구분 코드 확인요망!!!')
    if fid_prc_cls_code not in ['0', '1']:
        raise ValueError('가격 구분 코드 확인요망!!!')
    if fid_input_iscd not in ['0000', '0001', '1001', '2001', '4001']:
        raise ValueError('입력 종목코드 확인요망!!!')
    if fid_trgt_cls_code != '0':
        raise ValueError('대상 구분 코드 확인요망!!!')
    if fid_trgt_exls_cls_code not in ['0', '1', '2', '3', '4', '5', '6', '7']:
        raise ValueError('대상 제외 구분 코드 확인요망!!!')
    tr_id = 'FHPST01870000'
    params = {'fid_aply_rang_vol': fid_aply_rang_vol, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_div_cls_code': fid_div_cls_code, 'fid_input_cnt_1': fid_input_cnt_1, 'fid_input_cnt_2': fid_input_cnt_2, 'fid_prc_cls_code': fid_prc_cls_code, 'fid_input_iscd': fid_input_iscd, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_aply_rang_prc_1': fid_aply_rang_prc_1, 'fid_aply_rang_prc_2': fid_aply_rang_prc_2}
    return ApiRequest('domestic_stock.near_new_highlow', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def news_title(fid_news_ofer_entp_code, fid_cond_mrkt_cls_code, fid_input_iscd, fid_titl_cntt, fid_input_date_1, fid_input_hour_1, fid_rank_sort_cls_code, fid_input_srno, tr_cont=''):
    """KIS domestic_stock.news_title 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_news_ofer_entp_code (str): 뉴스 제공 업체 코드
fid_cond_mrkt_cls_code (str): 조건 시장 구분 코드
fid_input_iscd (str): 입력 종목코드
fid_titl_cntt (str): 제목 내용
fid_input_date_1 (str): 입력 날짜
fid_input_hour_1 (str): 입력 시간
fid_rank_sort_cls_code (str): 순위 정렬 구분 코드
fid_input_srno (str): 입력 일련번호
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/news-title'
    tr_id = 'FHKST01011800'
    params = {'FID_NEWS_OFER_ENTP_CODE': fid_news_ofer_entp_code, 'FID_COND_MRKT_CLS_CODE': fid_cond_mrkt_cls_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_TITL_CNTT': fid_titl_cntt, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_HOUR_1': fid_input_hour_1, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_INPUT_SRNO': fid_input_srno}
    return ApiRequest('domestic_stock.news_title', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def order_cash(env_dv, ord_dv, cano, acnt_prdt_cd, pdno, ord_dvsn, ord_qty, ord_unpr, excg_id_dvsn_cd, sll_type='', cndt_pric=''):
    """KIS domestic_stock.order_cash 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (real:실전, demo:모의)
ord_dv (str): [필수] 매도매수구분 (buy:매수, sell:매도)
cano (str): [필수] 종합계좌번호 (종합계좌번호)
acnt_prdt_cd (str): [필수] 계좌상품코드 (상품유형코드)
pdno (str): [필수] 상품번호 (종목코드(6자리) , ETN의 경우 7자리 입력)
ord_dvsn (str): [필수] 주문구분
ord_qty (str): [필수] 주문수량
ord_unpr (str): [필수] 주문단가
excg_id_dvsn_cd (str): [필수] 거래소ID구분코드 (KRX)
sll_type (str): 매도유형 (매도주문 시) (01:일반매도,02:임의매매,05:대차매도)
cndt_pric (str): 조건가격 (스탑지정가호가 주문 시 사용)"""
    api_url = '/uapi/domestic-stock/v1/trading/order-cash'
    if env_dv == '' or env_dv is None:
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if ord_dv == '' or ord_dv is None:
        raise ValueError("ord_dv is required (e.g. 'buy:매수, sell:매도')")
    if cano == '' or cano is None:
        raise ValueError("cano is required (e.g. '종합계좌번호')")
    if acnt_prdt_cd == '' or acnt_prdt_cd is None:
        raise ValueError("acnt_prdt_cd is required (e.g. '상품유형코드')")
    if pdno == '' or pdno is None:
        raise ValueError("pdno is required (e.g. '종목코드(6자리) , ETN의 경우 7자리 입력')")
    if ord_dvsn == '' or ord_dvsn is None:
        raise ValueError("ord_dvsn is required (e.g. '')")
    if ord_qty == '' or ord_qty is None:
        raise ValueError("ord_qty is required (e.g. '')")
    if ord_unpr == '' or ord_unpr is None:
        raise ValueError("ord_unpr is required (e.g. '')")
    if excg_id_dvsn_cd == '' or excg_id_dvsn_cd is None:
        raise ValueError("excg_id_dvsn_cd is required (e.g. 'KRX')")
    if env_dv == 'real':
        if ord_dv == 'sell':
            tr_id = 'TTTC0011U'
        elif ord_dv == 'buy':
            tr_id = 'TTTC0012U'
        else:
            raise ValueError('ord_dv can only be sell or buy')
    elif env_dv == 'demo':
        if ord_dv == 'sell':
            tr_id = 'VTTC0011U'
        elif ord_dv == 'buy':
            tr_id = 'VTTC0012U'
        else:
            raise ValueError('ord_dv can only be sell or buy')
    else:
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'ORD_DVSN': ord_dvsn, 'ORD_QTY': ord_qty, 'ORD_UNPR': ord_unpr, 'EXCG_ID_DVSN_CD': excg_id_dvsn_cd, 'SLL_TYPE': sll_type, 'CNDT_PRIC': cndt_pric}
    return ApiRequest('domestic_stock.order_cash', api_url, tr_id, params, 'POST' if True else 'GET', env_dv, '')

def order_resv(cano, acnt_prdt_cd, pdno, ord_qty, ord_unpr, sll_buy_dvsn_cd, ord_dvsn_cd, ord_objt_cblc_dvsn_cd, rsvn_ord_end_dt=''):
    """KIS domestic_stock.order_resv 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (계좌번호 체계(8-2)의 앞 8자리)
acnt_prdt_cd (str): [필수] 계좌상품코드 (계좌번호 체계(8-2)의 뒤 2자리)
pdno (str): [필수] 종목코드(6자리)
ord_qty (str): [필수] 주문수량 (주0문주식수)
ord_unpr (str): [필수] 주문단가 (1주당 가격, 시장가/장전 시간외는 0 입력)
sll_buy_dvsn_cd (str): [필수] 매도매수구분코드 (01 : 매도, 02 : 매수)
ord_dvsn_cd (str): [필수] 주문구분코드 (00 : 지정가, 01 : 시장가, 02 : 조건부지정가, 05 : 장전 시간외)
ord_objt_cblc_dvsn_cd (str): [필수] 주문대상잔고구분코드 (10: 현금, 12~28: 각종 대출/상환코드)
rsvn_ord_end_dt (Optional[str]): 예약주문종료일자 (YYYYMMDD, 익영업일부터 최대 30일 이내)
현금 거래만 허용한다. 대출·신용 입력은 제거했다."""
    if ord_objt_cblc_dvsn_cd != '10':
        raise ValueError('예약주문은 현금(10)만 허용합니다.')
    api_url = '/uapi/domestic-stock/v1/trading/order-resv'
    if cano == '' or cano is None:
        raise ValueError("cano is required (e.g. '계좌번호 체계(8-2)의 앞 8자리')")
    if acnt_prdt_cd == '' or acnt_prdt_cd is None:
        raise ValueError("acnt_prdt_cd is required (e.g. '계좌번호 체계(8-2)의 뒤 2자리')")
    if pdno == '' or pdno is None:
        raise ValueError("pdno is required (e.g. '종목코드(6자리)')")
    if ord_qty == '' or ord_qty is None:
        raise ValueError("ord_qty is required (e.g. '주0문주식수')")
    if ord_unpr == '' or ord_unpr is None:
        raise ValueError("ord_unpr is required (e.g. '1주당 가격, 시장가/장전 시간외는 0 입력')")
    if sll_buy_dvsn_cd == '' or sll_buy_dvsn_cd is None:
        raise ValueError("sll_buy_dvsn_cd is required (e.g. '01 : 매도, 02 : 매수')")
    if ord_dvsn_cd == '' or ord_dvsn_cd is None:
        raise ValueError("ord_dvsn_cd is required (e.g. '00 : 지정가, 01 : 시장가, 02 : 조건부지정가, 05 : 장전 시간외')")
    if ord_objt_cblc_dvsn_cd == '' or ord_objt_cblc_dvsn_cd is None:
        raise ValueError("ord_objt_cblc_dvsn_cd is required (e.g. '10: 현금, 12~28: 각종 대출/상환코드')")
    tr_id = 'CTSC0008U'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'ORD_QTY': ord_qty, 'ORD_UNPR': ord_unpr, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'ORD_DVSN_CD': ord_dvsn_cd, 'ORD_OBJT_CBLC_DVSN_CD': ord_objt_cblc_dvsn_cd}
    if rsvn_ord_end_dt:
        params['RSVN_ORD_END_DT'] = rsvn_ord_end_dt
    return ApiRequest('domestic_stock.order_resv', api_url, tr_id, params, 'POST' if True else 'GET', 'real', '')

def order_resv_ccnl(rsvn_ord_ord_dt, rsvn_ord_end_dt, tmnl_mdia_kind_cd, cano, acnt_prdt_cd, prcs_dvsn_cd, cncl_yn, rsvn_ord_seq='', pdno='', sll_buy_dvsn_cd='', FK200='', NK200='', tr_cont=''):
    """KIS domestic_stock.order_resv_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
rsvn_ord_ord_dt (str): [필수] 예약주문시작일자
rsvn_ord_end_dt (str): [필수] 예약주문종료일자
tmnl_mdia_kind_cd (str): [필수] 단말매체종류코드 (ex. 00)
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 01)
prcs_dvsn_cd (str): [필수] 처리구분코드 (ex. 0)
cncl_yn (str): [필수] 취소여부 (ex. Y)
rsvn_ord_seq (str): 예약주문순번
pdno (str): 상품번호 (ex. 005930)
sll_buy_dvsn_cd (str): 매도매수구분코드 (ex. 01)
FK200 (str): 연속조회검색조건200
NK200 (str): 연속조회키200
tr_cont (str): 연속거래여부"""
    api_url = '/uapi/domestic-stock/v1/trading/order-resv-ccnl'
    if rsvn_ord_ord_dt == '':
        raise ValueError('rsvn_ord_ord_dt is required')
    if rsvn_ord_end_dt == '':
        raise ValueError('rsvn_ord_end_dt is required')
    if tmnl_mdia_kind_cd == '':
        raise ValueError("tmnl_mdia_kind_cd is required (e.g. '00')")
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '01')")
    if prcs_dvsn_cd == '':
        raise ValueError("prcs_dvsn_cd is required (e.g. '0')")
    if cncl_yn == '':
        raise ValueError("cncl_yn is required (e.g. 'Y')")
    tr_id = 'CTSC0004R'
    params = {'RSVN_ORD_ORD_DT': rsvn_ord_ord_dt, 'RSVN_ORD_END_DT': rsvn_ord_end_dt, 'TMNL_MDIA_KIND_CD': tmnl_mdia_kind_cd, 'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PRCS_DVSN_CD': prcs_dvsn_cd, 'CNCL_YN': cncl_yn, 'RSVN_ORD_SEQ': rsvn_ord_seq, 'PDNO': pdno, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('domestic_stock.order_resv_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def order_resv_rvsecncl(cano, acnt_prdt_cd, rsvn_ord_seq, rsvn_ord_orgno, rsvn_ord_ord_dt, ord_type, pdno='', ord_qty='', ord_unpr='', sll_buy_dvsn_cd='', ord_dvsn_cd='', ord_objt_cblc_dvsn_cd='10', rsvn_ord_end_dt='', ctal_tlno=''):
    """KIS domestic_stock.order_resv_rvsecncl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드
rsvn_ord_seq (str): [필수] 예약주문순번
rsvn_ord_orgno (str): [필수] 예약주문조직번호
rsvn_ord_ord_dt (str): [필수] 예약주문주문일자
ord_type (str): [필수] 주문구분 (ex. cancel:취소, modify:정정)
pdno (Optional[str]): 종목코드
ord_qty (Optional[str]): 주문수량
ord_unpr (Optional[str]): 주문단가
sll_buy_dvsn_cd (Optional[str]): 매도매수구분코드 (ex. 01:매도, 02:매수)
ord_dvsn_cd (Optional[str]): 주문구분코드 (ex. 00:지정가, 01:시장가, 02:조건부지정가, 05:장전 시간외)
ord_objt_cblc_dvsn_cd (Optional[str]): 주문대상잔고구분코드 (ex. 10 : 현금, 12 : 주식담보대출, ... 28 : 자기대주상환)
rsvn_ord_end_dt (Optional[str]): 예약주문종료일자
ctal_tlno (Optional[str]): 연락전화번호
현금 거래만 허용한다. 대출·신용 입력은 제거했다."""
    if ord_objt_cblc_dvsn_cd != '10':
        raise ValueError('예약주문은 현금(10)만 허용합니다.')
    api_url = '/uapi/domestic-stock/v1/trading/order-resv-rvsecncl'
    if cano == '' or cano is None:
        raise ValueError('cano is required')
    if acnt_prdt_cd == '' or acnt_prdt_cd is None:
        raise ValueError('acnt_prdt_cd is required')
    if rsvn_ord_seq == '' or rsvn_ord_seq is None:
        raise ValueError('rsvn_ord_seq is required')
    if rsvn_ord_orgno == '' or rsvn_ord_orgno is None:
        raise ValueError('rsvn_ord_orgno is required')
    if rsvn_ord_ord_dt == '' or rsvn_ord_ord_dt is None:
        raise ValueError('rsvn_ord_ord_dt is required')
    if ord_type == '' or ord_type is None:
        raise ValueError('ord_type is required')
    if ord_type == 'cancel':
        tr_id = 'CTSC0009U'
    elif ord_type == 'modify':
        tr_id = 'CTSC0013U'
    else:
        raise ValueError('ord_type can only be cancel or modify')
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'RSVN_ORD_SEQ': rsvn_ord_seq, 'RSVN_ORD_ORGNO': rsvn_ord_orgno, 'RSVN_ORD_ORD_DT': rsvn_ord_ord_dt}
    if pdno:
        params['PDNO'] = pdno
    if ord_qty:
        params['ORD_QTY'] = ord_qty
    if ord_unpr:
        params['ORD_UNPR'] = ord_unpr
    if sll_buy_dvsn_cd:
        params['SLL_BUY_DVSN_CD'] = sll_buy_dvsn_cd
    if ord_dvsn_cd:
        params['ORD_DVSN_CD'] = ord_dvsn_cd
    if ord_objt_cblc_dvsn_cd:
        params['ORD_OBJT_CBLC_DVSN_CD'] = ord_objt_cblc_dvsn_cd
    if rsvn_ord_end_dt:
        params['RSVN_ORD_END_DT'] = rsvn_ord_end_dt
    if ctal_tlno:
        params['CTAL_TLNO'] = ctal_tlno
    return ApiRequest('domestic_stock.order_resv_rvsecncl', api_url, tr_id, params, 'POST' if True else 'GET', 'real', '')

def order_rvsecncl(env_dv, cano, acnt_prdt_cd, krx_fwdg_ord_orgno, orgn_odno, ord_dvsn, rvse_cncl_dvsn_cd, ord_qty, ord_unpr, qty_all_ord_yn, excg_id_dvsn_cd, cndt_pric=''):
    """KIS domestic_stock.order_rvsecncl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드
krx_fwdg_ord_orgno (str): [필수] 한국거래소전송주문조직번호
orgn_odno (str): [필수] 원주문번호
ord_dvsn (str): [필수] 주문구분
rvse_cncl_dvsn_cd (str): [필수] 정정취소구분코드 (ex. 01:정정,02:취소)
ord_qty (str): [필수] 주문수량
ord_unpr (str): [필수] 주문단가
qty_all_ord_yn (str): [필수] 잔량전부주문여부 (ex. Y:전량, N:일부)
excg_id_dvsn_cd (str): [필수] 거래소ID구분코드 (ex. KRX: 한국거래소, NXT:대체거래소,SOR:SOR)
cndt_pric (Optional[str]): 조건가격"""
    api_url = '/uapi/domestic-stock/v1/trading/order-rvsecncl'
    if env_dv == '' or env_dv is None:
        raise ValueError("env_dv is required (e.g. 'real', 'demo')")
    if cano == '' or cano is None:
        raise ValueError('cano is required')
    if acnt_prdt_cd == '' or acnt_prdt_cd is None:
        raise ValueError('acnt_prdt_cd is required')
    if krx_fwdg_ord_orgno == '' or krx_fwdg_ord_orgno is None:
        raise ValueError('krx_fwdg_ord_orgno is required')
    if orgn_odno == '' or orgn_odno is None:
        raise ValueError('orgn_odno is required')
    if ord_dvsn == '' or ord_dvsn is None:
        raise ValueError('ord_dvsn is required')
    if rvse_cncl_dvsn_cd == '' or rvse_cncl_dvsn_cd is None:
        raise ValueError("rvse_cncl_dvsn_cd is required (e.g. '01', '02')")
    if ord_qty == '' or ord_qty is None:
        raise ValueError('ord_qty is required')
    if ord_unpr == '' or ord_unpr is None:
        raise ValueError('ord_unpr is required')
    if qty_all_ord_yn == '' or qty_all_ord_yn is None:
        raise ValueError("qty_all_ord_yn is required (e.g. 'Y', 'N')")
    if excg_id_dvsn_cd == '' or excg_id_dvsn_cd is None:
        raise ValueError("excg_id_dvsn_cd is required (e.g. 'KRX', 'NXT', 'SOR')")
    if env_dv == 'real':
        tr_id = 'TTTC0013U'
    elif env_dv == 'demo':
        tr_id = 'VTTC0013U'
    else:
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'KRX_FWDG_ORD_ORGNO': krx_fwdg_ord_orgno, 'ORGN_ODNO': orgn_odno, 'ORD_DVSN': ord_dvsn, 'RVSE_CNCL_DVSN_CD': rvse_cncl_dvsn_cd, 'ORD_QTY': ord_qty, 'ORD_UNPR': ord_unpr, 'QTY_ALL_ORD_YN': qty_all_ord_yn, 'EXCG_ID_DVSN_CD': excg_id_dvsn_cd}
    if cndt_pric:
        params['CNDT_PRIC'] = cndt_pric
    return ApiRequest('domestic_stock.order_rvsecncl', api_url, tr_id, params, 'POST' if True else 'GET', env_dv, '')

def overtime_exp_trans_fluct(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_div_cls_code, fid_input_price_1='', fid_input_price_2='', fid_input_vol_1=''):
    """KIS domestic_stock.overtime_exp_trans_fluct 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:주식)
fid_cond_scr_div_code (str): [필수] 조건 화면 분류 코드 (ex. 11186)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 0000:전체, 0001:코스피, 1001:코스닥)
fid_rank_sort_cls_code (str): [필수] 순위 정렬 구분 코드 (ex. 0:상승률, 1:상승폭, 2:보합, 3:하락률, 4:하락폭)
fid_div_cls_code (str): [필수] 분류 구분 코드 (ex. 0:전체, 1:관리종목, 2:투자주의, 3:투자경고, 4:투자위험예고, 5:투자위험, 6:보통주, 7:우선주)
fid_input_price_1 (str): 입력 가격1
fid_input_price_2 (str): 입력 가격2
fid_input_vol_1 (str): 입력 거래량"""
    api_url = '/uapi/domestic-stock/v1/ranking/overtime-exp-trans-fluct'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '11186')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '0000')")
    if fid_rank_sort_cls_code == '':
        raise ValueError("fid_rank_sort_cls_code is required (e.g. '0')")
    if fid_div_cls_code == '':
        raise ValueError("fid_div_cls_code is required (e.g. '0')")
    tr_id = 'FHKST11860000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_INPUT_VOL_1': fid_input_vol_1}
    return ApiRequest('domestic_stock.overtime_exp_trans_fluct', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def overtime_fluctuation(fid_cond_mrkt_div_code, fid_mrkt_cls_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_trgt_cls_code, fid_trgt_exls_cls_code, tr_cont=''):
    """KIS domestic_stock.overtime_fluctuation 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 시장구분코드 (J: 주식)
fid_mrkt_cls_code (str): 공백 입력
fid_cond_scr_div_code (str): Unique key(20234)
fid_input_iscd (str): 0000(전체), 0001(코스피), 1001(코스닥)
fid_div_cls_code (str): 1(상한가), 2(상승률), 3(보합),4(하한가),5(하락률)
fid_input_price_1 (str): 입력값 없을때 전체 (가격 ~)
fid_input_price_2 (str): 입력값 없을때 전체 (~ 가격)
fid_vol_cnt (str): 입력값 없을때 전체 (거래량 ~)
fid_trgt_cls_code (str): 공백 입력
fid_trgt_exls_cls_code (str): 공백 입력
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/overtime-fluctuation'
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20234')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20234')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0000')")
        raise ValueError("fid_input_iscd is required. (e.g. '0000')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '1')")
        raise ValueError("fid_div_cls_code is required. (e.g. '1')")
    tr_id = 'FHPST02340000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_MRKT_CLS_CODE': fid_mrkt_cls_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_VOL_CNT': fid_vol_cnt, 'FID_TRGT_CLS_CODE': fid_trgt_cls_code, 'FID_TRGT_EXLS_CLS_CODE': fid_trgt_exls_cls_code}
    return ApiRequest('domestic_stock.overtime_fluctuation', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def overtime_volume(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_trgt_cls_code, fid_trgt_exls_cls_code, tr_cont=''):
    """KIS domestic_stock.overtime_volume 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 시장구분코드 (J: 주식)
fid_cond_scr_div_code (str): Unique key(20235)
fid_input_iscd (str): 0000(전체), 0001(코스피), 1001(코스닥)
fid_rank_sort_cls_code (str): 0(매수잔량),  1(매도잔량), 2(거래량)
fid_input_price_1 (str): 가격 ~
fid_input_price_2 (str): ~ 가격
fid_vol_cnt (str): 거래량 ~
fid_trgt_cls_code (str): 공백
fid_trgt_exls_cls_code (str): 공백
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/overtime-volume'
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20235')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20235')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0000')")
        raise ValueError("fid_input_iscd is required. (e.g. '0000')")
    if not fid_rank_sort_cls_code:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '2')")
        raise ValueError("fid_rank_sort_cls_code is required. (e.g. '2')")
    tr_id = 'FHPST02350000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_VOL_CNT': fid_vol_cnt, 'FID_TRGT_CLS_CODE': fid_trgt_cls_code, 'FID_TRGT_EXLS_CLS_CODE': fid_trgt_exls_cls_code}
    return ApiRequest('domestic_stock.overtime_volume', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def pbar_tratio(fid_cond_mrkt_div_code, fid_input_iscd, fid_cond_scr_div_code, fid_input_hour_1=''):
    """KIS domestic_stock.pbar_tratio 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)
fid_cond_scr_div_code (str): [필수] 조건화면분류코드 (ex. 20113)
fid_input_hour_1 (str): 입력시간 (기본값: "")"""
    api_url = '/uapi/domestic-stock/v1/quotations/pbar-tratio'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '20113')")
    tr_id = 'FHPST01130000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_HOUR_1': fid_input_hour_1}
    return ApiRequest('domestic_stock.pbar_tratio', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def pension_inquire_balance(cano, acnt_prdt_cd, acca_dvsn_cd, inqr_dvsn, FK100='', NK100='', tr_cont=''):
    """KIS domestic_stock.pension_inquire_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. 12345678)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 29)
acca_dvsn_cd (str): [필수] 적립금구분코드 (ex. 00)
inqr_dvsn (str): [필수] 조회구분 (ex. 00)
FK100 (str): 연속조회검색조건100
NK100 (str): 연속조회키100
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/trading/pension/inquire-balance'
    if cano == '' or cano is None:
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '' or acnt_prdt_cd is None:
        raise ValueError("acnt_prdt_cd is required (e.g. '29')")
    if acca_dvsn_cd == '' or acca_dvsn_cd is None:
        raise ValueError("acca_dvsn_cd is required (e.g. '00')")
    if inqr_dvsn == '' or inqr_dvsn is None:
        raise ValueError("inqr_dvsn is required (e.g. '00')")
    tr_id = 'TTTC2208R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'ACCA_DVSN_CD': acca_dvsn_cd, 'INQR_DVSN': inqr_dvsn, 'CTX_AREA_FK100': FK100, 'CTX_AREA_NK100': NK100}
    return ApiRequest('domestic_stock.pension_inquire_balance', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def pension_inquire_daily_ccld(cano, acnt_prdt_cd, user_dvsn_cd, sll_buy_dvsn_cd, ccld_nccs_dvsn, inqr_dvsn_3, FK100='', NK100='', tr_cont=''):
    """KIS domestic_stock.pension_inquire_daily_ccld 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. 12345678)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 29)
user_dvsn_cd (str): [필수] 사용자구분코드 (ex. %%)
sll_buy_dvsn_cd (str): [필수] 매도매수구분코드 (ex. 00: 전체, 01: 매도, 02: 매수)
ccld_nccs_dvsn (str): [필수] 체결미체결구분 (ex. %%: 전체, 01: 체결, 02: 미체결)
inqr_dvsn_3 (str): [필수] 조회구분3 (ex. 00: 전체)
FK100 (str): 연속조회검색조건100
NK100 (str): 연속조회키100
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/trading/pension/inquire-daily-ccld'
    if cano == '':
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '29')")
    if user_dvsn_cd == '':
        raise ValueError("user_dvsn_cd is required (e.g. '%%')")
    if sll_buy_dvsn_cd == '':
        raise ValueError("sll_buy_dvsn_cd is required (e.g. '00: 전체, 01: 매도, 02: 매수')")
    if ccld_nccs_dvsn == '':
        raise ValueError("ccld_nccs_dvsn is required (e.g. '%%: 전체, 01: 체결, 02: 미체결')")
    if inqr_dvsn_3 == '':
        raise ValueError("inqr_dvsn_3 is required (e.g. '00: 전체')")
    tr_id = 'TTTC2201R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'USER_DVSN_CD': user_dvsn_cd, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'CCLD_NCCS_DVSN': ccld_nccs_dvsn, 'INQR_DVSN_3': inqr_dvsn_3, 'CTX_AREA_FK100': FK100, 'CTX_AREA_NK100': NK100}
    return ApiRequest('domestic_stock.pension_inquire_daily_ccld', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def pension_inquire_deposit(cano, acnt_prdt_cd, acca_dvsn_cd):
    """KIS domestic_stock.pension_inquire_deposit 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. 12345678)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 29)
acca_dvsn_cd (str): [필수] 적립금구분코드 (ex. 00)"""
    api_url = '/uapi/domestic-stock/v1/trading/pension/inquire-deposit'
    if cano == '':
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '29')")
    if acca_dvsn_cd == '':
        raise ValueError("acca_dvsn_cd is required (e.g. '00')")
    tr_id = 'TTTC0506R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'ACCA_DVSN_CD': acca_dvsn_cd}
    return ApiRequest('domestic_stock.pension_inquire_deposit', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def pension_inquire_present_balance(cano, acnt_prdt_cd, user_dvsn_cd, FK100='', NK100=''):
    """KIS domestic_stock.pension_inquire_present_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. '12345678')
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. '29')
user_dvsn_cd (str): [필수] 상품번호 (ex. '00')
FK100 (str): 연속조회검색조건100
NK100 (str): 연속조회키100"""
    api_url = '/uapi/domestic-stock/v1/trading/pension/inquire-present-balance'
    if cano == '':
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '29')")
    if user_dvsn_cd == '':
        raise ValueError("user_dvsn_cd is required (e.g. '00')")
    tr_id = 'TTTC2202R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'USER_DVSN_CD': user_dvsn_cd, 'CTX_AREA_FK100': FK100, 'CTX_AREA_NK100': NK100}
    return ApiRequest('domestic_stock.pension_inquire_present_balance', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def pension_inquire_psbl_order(cano, acnt_prdt_cd, pdno, acca_dvsn_cd, cma_evlu_amt_icld_yn, ord_unpr, ord_dvsn):
    """KIS domestic_stock.pension_inquire_psbl_order 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. 12345678)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 29)
pdno (str): [필수] 상품번호 (ex. 123456)
acca_dvsn_cd (str): [필수] 적립금구분코드 (ex. 00)
cma_evlu_amt_icld_yn (str): [필수] CMA평가금액포함여부 (ex. Y:포함, N:미포함)
ord_unpr (str): [필수] 주문단가
ord_dvsn (str): [필수] 주문구분 (ex. 00: 지정가, 01: 시장가)"""
    api_url = '/uapi/domestic-stock/v1/trading/pension/inquire-psbl-order'
    if cano == '':
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '29')")
    if pdno == '':
        raise ValueError("pdno is required (e.g. '123456')")
    if acca_dvsn_cd == '':
        raise ValueError("acca_dvsn_cd is required (e.g. '00')")
    if cma_evlu_amt_icld_yn == '':
        raise ValueError("cma_evlu_amt_icld_yn is required (e.g. 'Y:포함, N:미포함')")
    if ord_unpr == '':
        raise ValueError('ord_unpr is required')
    if ord_dvsn == '':
        raise ValueError("ord_dvsn is required (e.g. '00: 지정가, 01: 시장가')")
    tr_id = 'TTTC0503R'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'ACCA_DVSN_CD': acca_dvsn_cd, 'CMA_EVLU_AMT_ICLD_YN': cma_evlu_amt_icld_yn, 'ORD_UNPR': ord_unpr, 'ORD_DVSN': ord_dvsn}
    return ApiRequest('domestic_stock.pension_inquire_psbl_order', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def period_rights(inqr_dvsn, cano, acnt_prdt_cd, inqr_strt_dt, inqr_end_dt, cust_rncno25='', hmid='', rght_type_cd='', pdno='', prdt_type_cd='', NK100='', FK100='', tr_cont=''):
    """KIS domestic_stock.period_rights 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
inqr_dvsn (str): [필수] 조회구분 (ex. 03)
cano (str): [필수] 종합계좌번호 (ex. 12345678)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 01 or 22)
inqr_strt_dt (str): [필수] 조회시작일자 (ex. 20250101)
inqr_end_dt (str): [필수] 조회종료일자 (ex. 20250103)
cust_rncno25 (str): 고객실명확인번호25
hmid (str): 홈넷ID
rght_type_cd (str): 권리유형코드
pdno (str): 상품번호
prdt_type_cd (str): 상품유형코드
NK100 (str): 연속조회키100
FK100 (str): 연속조회검색조건100
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/trading/period-rights'
    if inqr_dvsn == '':
        raise ValueError("inqr_dvsn is required (e.g. '03')")
    if cano == '':
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '01' or '22')")
    if inqr_strt_dt == '':
        raise ValueError("inqr_strt_dt is required (e.g. '20250101')")
    if inqr_end_dt == '':
        raise ValueError("inqr_end_dt is required (e.g. '20250103')")
    tr_id = 'CTRGA011R'
    params = {'INQR_DVSN': inqr_dvsn, 'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'INQR_STRT_DT': inqr_strt_dt, 'INQR_END_DT': inqr_end_dt, 'CUST_RNCNO25': cust_rncno25, 'HMID': hmid, 'RGHT_TYPE_CD': rght_type_cd, 'PDNO': pdno, 'PRDT_TYPE_CD': prdt_type_cd, 'CTX_AREA_NK100': NK100, 'CTX_AREA_FK100': FK100}
    return ApiRequest('domestic_stock.period_rights', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def prefer_disparate_ratio(fid_vol_cnt, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_input_iscd, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_input_price_2, tr_cont=''):
    """KIS domestic_stock.prefer_disparate_ratio 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_vol_cnt (str): 입력값 없을때 전체 (거래량 ~)
fid_cond_mrkt_div_code (str): 시장구분코드 (J:KRX, NX:NXT)
fid_cond_scr_div_code (str): Unique key( 20177 )
fid_div_cls_code (str): 0: 전체
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200
fid_trgt_cls_code (str): 0 : 전체
fid_trgt_exls_cls_code (str): 0 : 전체
fid_input_price_1 (str): 입력값 없을때 전체 (가격 ~)
fid_input_price_2 (str): 입력값 없을때 전체 (~ 가격)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/prefer-disparate-ratio'
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20177')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20177')")
    if not fid_div_cls_code:
        logger.error("fid_div_cls_code is required. (e.g. '0')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0000')")
        raise ValueError("fid_input_iscd is required. (e.g. '0000')")
    if not fid_trgt_cls_code:
        logger.error("fid_trgt_cls_code is required. (e.g. '0')")
        raise ValueError("fid_trgt_cls_code is required. (e.g. '0')")
    if not fid_trgt_exls_cls_code:
        logger.error("fid_trgt_exls_cls_code is required. (e.g. '0')")
        raise ValueError("fid_trgt_exls_cls_code is required. (e.g. '0')")
    tr_id = 'FHPST01770000'
    params = {'fid_vol_cnt': fid_vol_cnt, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_div_cls_code': fid_div_cls_code, 'fid_input_iscd': fid_input_iscd, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_input_price_2': fid_input_price_2}
    return ApiRequest('domestic_stock.prefer_disparate_ratio', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def profit_asset_index(fid_cond_mrkt_div_code, fid_trgt_cls_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_input_option_1, fid_input_option_2, fid_rank_sort_cls_code, fid_blng_cls_code, fid_trgt_exls_cls_code, tr_cont=''):
    """KIS domestic_stock.profit_asset_index 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건 시장 분류 코드 (필수) (J:KRX, NX:NXT)
fid_trgt_cls_code (str): 대상 구분 코드 (필수)
fid_cond_scr_div_code (str): 조건 화면 분류 코드 (필수)
fid_input_iscd (str): 입력 종목코드 (필수)
fid_div_cls_code (str): 분류 구분 코드 (필수)
fid_input_price_1 (str): 입력 가격1 (필수)
fid_input_price_2 (str): 입력 가격2 (필수)
fid_vol_cnt (str): 거래량 수 (필수)
fid_input_option_1 (str): 입력 옵션1 (필수)
fid_input_option_2 (str): 입력 옵션2 (필수)
fid_rank_sort_cls_code (str): 순위 정렬 구분 코드 (필수)
fid_blng_cls_code (str): 소속 구분 코드 (필수)
fid_trgt_exls_cls_code (str): 대상 제외 구분 코드 (필수)
tr_cont (str): 연속 거래 여부 (옵션)"""
    api_url = '/uapi/domestic-stock/v1/ranking/profit-asset-index'
    if fid_cond_mrkt_div_code != 'J':
        raise ValueError('조건 시장 분류 코드 확인요망!!!')
    if fid_trgt_cls_code != '0':
        raise ValueError('대상 구분 코드 확인요망!!!')
    if fid_cond_scr_div_code != '20173':
        raise ValueError('조건 화면 분류 코드 확인요망!!!')
    if fid_input_iscd not in ['0000', '0001', '1001', '2001']:
        raise ValueError('입력 종목코드 확인요망!!!')
    if fid_div_cls_code != '0':
        raise ValueError('분류 구분 코드 확인요망!!!')
    if fid_input_option_1 != '2023':
        raise ValueError('입력 옵션1 확인요망!!!')
    if fid_input_option_2 not in ['0', '1', '2', '3']:
        raise ValueError('입력 옵션2 확인요망!!!')
    if fid_rank_sort_cls_code not in ['0', '1', '2', '3', '4', '5', '6']:
        raise ValueError('순위 정렬 구분 코드 확인요망!!!')
    if fid_blng_cls_code != '0':
        raise ValueError('소속 구분 코드 확인요망!!!')
    if fid_trgt_exls_cls_code != '0':
        raise ValueError('대상 제외 구분 코드 확인요망!!!')
    tr_id = 'FHPST01730000'
    params = {'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_input_iscd': fid_input_iscd, 'fid_div_cls_code': fid_div_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_input_price_2': fid_input_price_2, 'fid_vol_cnt': fid_vol_cnt, 'fid_input_option_1': fid_input_option_1, 'fid_input_option_2': fid_input_option_2, 'fid_rank_sort_cls_code': fid_rank_sort_cls_code, 'fid_blng_cls_code': fid_blng_cls_code, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code}
    return ApiRequest('domestic_stock.profit_asset_index', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def program_trade_by_stock(fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS domestic_stock.program_trade_by_stock 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX,NX:NXT,UN:통합)
fid_input_iscd (str): [필수] 종목코드 (ex. 123456)"""
    api_url = '/uapi/domestic-stock/v1/quotations/program-trade-by-stock'
    if fid_cond_mrkt_div_code == '':
        raise ValueError('fid_cond_mrkt_div_code is required (ex. J:KRX,NX:NXT,UN:통합)')
    if fid_input_iscd == '':
        raise ValueError('fid_input_iscd is required (ex. 123456)')
    tr_id = 'FHPPG04650101'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.program_trade_by_stock', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def program_trade_by_stock_daily(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1=''):
    """KIS domestic_stock.program_trade_by_stock_daily 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX,NX:NXT,UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)
fid_input_date_1 (str): [필수] 입력날짜 (초기값: "")"""
    api_url = '/uapi/domestic-stock/v1/quotations/program-trade-by-stock-daily'
    if fid_cond_mrkt_div_code == '':
        raise ValueError('fid_cond_mrkt_div_code is required (ex. J:KRX,NX:NXT,UN:통합)')
    if fid_input_iscd == '':
        raise ValueError('fid_input_iscd is required (ex. 123456)')
    tr_id = 'FHPPG04650201'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1}
    return ApiRequest('domestic_stock.program_trade_by_stock_daily', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def psearch_result(user_id, seq):
    """KIS domestic_stock.psearch_result 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
user_id (str): [필수] 사용자 HTS ID
seq (str): [필수] 사용자조건 키값 (종목조건검색 목록조회 API의 output인 'seq'을 이용)"""
    api_url = '/uapi/domestic-stock/v1/quotations/psearch-result'
    if user_id == '':
        raise ValueError('user_id is required')
    if seq == '':
        raise ValueError("seq is required (e.g. '종목조건검색 목록조회 API의 output인 'seq'을 이용')")
    tr_id = 'HHKST03900400'
    params = {'user_id': user_id, 'seq': seq}
    return ApiRequest('domestic_stock.psearch_result', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def psearch_title(user_id):
    """KIS domestic_stock.psearch_title 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
user_id (str): [필수] 사용자 HTS ID (ex. U:업종)"""
    api_url = '/uapi/domestic-stock/v1/quotations/psearch-title'
    if user_id == '':
        raise ValueError("user_id is required (e.g. 'U:업종')")
    tr_id = 'HHKST03900300'
    params = {'user_id': user_id}
    return ApiRequest('domestic_stock.psearch_title', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def quote_balance(fid_vol_cnt, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_div_cls_code, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_input_price_2, tr_cont=''):
    """KIS domestic_stock.quote_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_vol_cnt (str): 입력값 없을때 전체 (거래량 ~)
fid_cond_mrkt_div_code (str): 시장구분코드 (J:KRX, NX:NXT)
fid_cond_scr_div_code (str): Unique key( 20172 )
fid_input_iscd (str): 0000(전체) 코스피(0001), 코스닥(1001), 코스피200(2001)
fid_rank_sort_cls_code (str): 0: 순매수잔량순, 1:순매도잔량순, 2:매수비율순, 3:매도비율순
fid_div_cls_code (str): 0:전체
fid_trgt_cls_code (str): 0:전체
fid_trgt_exls_cls_code (str): 0:전체
fid_input_price_1 (str): 입력값 없을때 전체 (가격 ~)
fid_input_price_2 (str): 입력값 없을때 전체 (~ 가격)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/quote-balance'
    if fid_cond_mrkt_div_code != 'J':
        raise ValueError('조건 시장 분류 코드 확인요망!!!')
    if fid_cond_scr_div_code != '20172':
        raise ValueError('조건 화면 분류 코드 확인요망!!!')
    if fid_input_iscd not in ['0000', '0001', '1001', '2001']:
        raise ValueError('입력 종목코드 확인요망!!!')
    if fid_rank_sort_cls_code not in ['0', '1', '2', '3']:
        raise ValueError('순위 정렬 구분 코드 확인요망!!!')
    if fid_div_cls_code != '0':
        raise ValueError('분류 구분 코드 확인요망!!!')
    if fid_trgt_cls_code != '0':
        raise ValueError('대상 구분 코드 확인요망!!!')
    if fid_trgt_exls_cls_code != '0':
        raise ValueError('대상 제외 구분 코드 확인요망!!!')
    tr_id = 'FHPST01720000'
    params = {'fid_vol_cnt': fid_vol_cnt, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_input_iscd': fid_input_iscd, 'fid_rank_sort_cls_code': fid_rank_sort_cls_code, 'fid_div_cls_code': fid_div_cls_code, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_input_price_2': fid_input_price_2}
    return ApiRequest('domestic_stock.quote_balance', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def search_info(pdno, prdt_type_cd, tr_cont=''):
    """KIS domestic_stock.search_info 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
pdno (str): 상품번호 (예: '000660', 'KR4101SC0009', 'AAPL')
prdt_type_cd (str): 상품유형코드 (예: '300', '301', '512')
tr_cont (str): 연속 거래 여부 (기본값: 공백)"""
    api_url = '/uapi/domestic-stock/v1/quotations/search-info'
    logger = logging.getLogger(__name__)
    if not pdno:
        logger.error("pdno is required. (e.g. '000660')")
        raise ValueError("pdno is required. (e.g. '000660')")
    if not prdt_type_cd:
        logger.error("prdt_type_cd is required. (e.g. '300')")
        raise ValueError("prdt_type_cd is required. (e.g. '300')")
    tr_id = 'CTPF1604R'
    params = {'PDNO': pdno, 'PRDT_TYPE_CD': prdt_type_cd}
    return ApiRequest('domestic_stock.search_info', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def search_stock_info(prdt_type_cd, pdno, tr_cont=''):
    """KIS domestic_stock.search_stock_info 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
prdt_type_cd (str): 300: 주식, ETF, ETN, ELW  301 : 선물옵션  302 : 채권  306 : ELS'
pdno (str): 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/search-stock-info'
    logger = logging.getLogger(__name__)
    if not prdt_type_cd:
        logger.error("prdt_type_cd is required. (e.g. '300')")
        raise ValueError("prdt_type_cd is required. (e.g. '300')")
    if not pdno:
        logger.error("pdno is required. (e.g. '000660')")
        raise ValueError("pdno is required. (e.g. '000660')")
    tr_id = 'CTPF1002R'
    params = {'PRDT_TYPE_CD': prdt_type_cd, 'PDNO': pdno}
    return ApiRequest('domestic_stock.search_stock_info', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def short_sale(fid_aply_rang_vol, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_period_div_code, fid_input_cnt_1, fid_trgt_exls_cls_code, fid_trgt_cls_code, fid_aply_rang_prc_1, fid_aply_rang_prc_2, tr_cont=''):
    """KIS domestic_stock.short_sale 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_aply_rang_vol (str): FID 적용 범위 거래량
fid_cond_mrkt_div_code (str): 시장구분코드 (주식 J)
fid_cond_scr_div_code (str): Unique key(20482)
fid_input_iscd (str): 0000:전체, 0001:코스피, 1001:코스닥, 2001:코스피200, 4001: KRX100, 3003: 코스닥150
fid_period_div_code (str): 조회구분 (일/월) D: 일, M:월
fid_input_cnt_1 (str): 조회가간(일수): 조회구분(D) 0:1일, 1:2일, 2:3일, 3:4일, 4:1주일, 9:2주일, 14:3주일, 조회구분(M) 1:1개월, 2:2개월, 3:3개월
fid_trgt_exls_cls_code (str): 대상 제외 구분 코드
fid_trgt_cls_code (str): FID 대상 구분 코드
fid_aply_rang_prc_1 (str): FID 적용 범위 가격1
fid_aply_rang_prc_2 (str): FID 적용 범위 가격2
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/short-sale'
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        return None
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20482')")
        return None
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '0000')")
        return None
    if not fid_period_div_code:
        logger.error("fid_period_div_code is required. (e.g. 'D')")
        return None
    if not fid_input_cnt_1:
        logger.error("fid_input_cnt_1 is required. (e.g. '0')")
        return None
    tr_id = 'FHPST04820000'
    params = {'FID_APLY_RANG_VOL': fid_aply_rang_vol, 'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_PERIOD_DIV_CODE': fid_period_div_code, 'FID_INPUT_CNT_1': fid_input_cnt_1, 'FID_TRGT_EXLS_CLS_CODE': fid_trgt_exls_cls_code, 'FID_TRGT_CLS_CODE': fid_trgt_cls_code, 'FID_APLY_RANG_PRC_1': fid_aply_rang_prc_1, 'FID_APLY_RANG_PRC_2': fid_aply_rang_prc_2}
    return ApiRequest('domestic_stock.short_sale', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def top_interest_stock(fid_input_iscd_2, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_div_cls_code, fid_input_cnt_1, tr_cont=''):
    """KIS domestic_stock.top_interest_stock 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_input_iscd_2 (str): 000000 : 필수입력값
fid_cond_mrkt_div_code (str): 시장구분코드 (J:KRX, NX:NXT)
fid_cond_scr_div_code (str): Unique key(20180)
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200
fid_trgt_cls_code (str): 0 : 전체
fid_trgt_exls_cls_code (str): 0 : 전체
fid_input_price_1 (str): 입력값 없을때 전체 (가격 ~)
fid_input_price_2 (str): 입력값 없을때 전체 (~ 가격)
fid_vol_cnt (str): 입력값 없을때 전체 (거래량 ~)
fid_div_cls_code (str): 0: 전체 1: 관리종목 2: 투자주의 3: 투자경고 4: 투자위험예고 5: 투자위험 6: 보통주 7: 우선주
fid_input_cnt_1 (str): 순위검색 입력값(1: 1위부터, 10:10위부터)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/top-interest-stock'
    if not fid_input_iscd_2:
        logger.error("fid_input_iscd_2 is required. (e.g. '000000')")
        raise ValueError("fid_input_iscd_2 is required. (e.g. '000000')")
    if fid_cond_mrkt_div_code not in ['J']:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'J')")
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20180')")
        raise ValueError("fid_cond_scr_div_code is required. (e.g. '20180')")
    if fid_input_iscd not in ['0000', '0001', '1001', '2001']:
        logger.error("fid_input_iscd is required. (e.g. '0000', '0001', '1001', '2001')")
        raise ValueError("fid_input_iscd is required. (e.g. '0000', '0001', '1001', '2001')")
    if fid_div_cls_code not in ['0', '1', '2', '3', '4', '5', '6', '7']:
        logger.error("fid_div_cls_code is required. (e.g. '0', '1', '2', '3', '4', '5', '6', '7')")
        raise ValueError("fid_div_cls_code is required. (e.g. '0', '1', '2', '3', '4', '5', '6', '7')")
    tr_id = 'FHPST01800000'
    params = {'fid_input_iscd_2': fid_input_iscd_2, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_input_iscd': fid_input_iscd, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_input_price_2': fid_input_price_2, 'fid_vol_cnt': fid_vol_cnt, 'fid_div_cls_code': fid_div_cls_code, 'fid_input_cnt_1': fid_input_cnt_1}
    return ApiRequest('domestic_stock.top_interest_stock', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def traded_by_company(fid_trgt_exls_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_rank_sort_cls_code, fid_input_date_1, fid_input_date_2, fid_input_iscd, fid_trgt_cls_code, fid_aply_rang_vol, fid_aply_rang_prc_2, fid_aply_rang_prc_1, tr_cont=''):
    """KIS domestic_stock.traded_by_company 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_trgt_exls_cls_code (str): 0: 전체
fid_cond_mrkt_div_code (str): 시장구분코드 (J:KRX, NX:NXT)
fid_cond_scr_div_code (str): Unique key(20186)
fid_div_cls_code (str): 0:전체, 1:관리종목, 2:투자주의, 3:투자경고, 4:투자위험예고, 5:투자위험, 6:보통주, 7:우선주
fid_rank_sort_cls_code (str): 0:매도상위,1:매수상위
fid_input_date_1 (str): 기간~
fid_input_date_2 (str): ~기간
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200, 4001: KRX100
fid_trgt_cls_code (str): 0: 전체
fid_aply_rang_vol (str): 0: 전체, 100: 100주 이상
fid_aply_rang_prc_2 (str): ~ 가격
fid_aply_rang_prc_1 (str): 가격 ~
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/traded-by-company'
    if not fid_trgt_exls_cls_code:
        logger.error("fid_trgt_exls_cls_code is required. (e.g. '0')")
        return None
    if fid_cond_mrkt_div_code != 'J':
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'J')")
        return None
    if not fid_cond_scr_div_code:
        logger.error("fid_cond_scr_div_code is required. (e.g. '20186')")
        return None
    if fid_div_cls_code not in ['0', '1', '2', '3', '4', '5', '6', '7']:
        logger.error("fid_div_cls_code is required. (e.g. '0', '1', '2', '3', '4', '5', '6', '7')")
        return None
    if fid_rank_sort_cls_code not in ['0', '1']:
        logger.error("fid_rank_sort_cls_code is required. (e.g. '0', '1')")
        return None
    if not fid_input_date_1:
        logger.error('fid_input_date_1 is required.')
        return None
    if not fid_input_date_2:
        logger.error('fid_input_date_2 is required.')
        return None
    if fid_input_iscd not in ['0000', '0001', '1001', '2001', '4001']:
        logger.error("fid_input_iscd is required. (e.g. '0000', '0001', '1001', '2001', '4001')")
        return None
    if not fid_trgt_cls_code:
        logger.error("fid_trgt_cls_code is required. (e.g. '0')")
        return None
    if fid_aply_rang_vol not in ['0', '100']:
        logger.error("fid_aply_rang_vol is required. (e.g. '0', '100')")
        return None
    tr_id = 'FHPST01860000'
    params = {'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_div_cls_code': fid_div_cls_code, 'fid_rank_sort_cls_code': fid_rank_sort_cls_code, 'fid_input_date_1': fid_input_date_1, 'fid_input_date_2': fid_input_date_2, 'fid_input_iscd': fid_input_iscd, 'fid_trgt_cls_code': fid_trgt_cls_code, 'fid_aply_rang_vol': fid_aply_rang_vol, 'fid_aply_rang_prc_2': fid_aply_rang_prc_2, 'fid_aply_rang_prc_1': fid_aply_rang_prc_1}
    return ApiRequest('domestic_stock.traded_by_company', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def tradprt_byamt(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd):
    """KIS domestic_stock.tradprt_byamt 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT)
fid_cond_scr_div_code (str): [필수] 조건화면분류코드 (ex. 11119)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)"""
    api_url = '/uapi/domestic-stock/v1/quotations/tradprt-byamt'
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '11119')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    tr_id = 'FHKST111900C0'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_stock.tradprt_byamt', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def volume_power(fid_trgt_exls_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_trgt_cls_code, tr_cont=''):
    """KIS domestic_stock.volume_power 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_trgt_exls_cls_code (str): 0 : 전체
fid_cond_mrkt_div_code (str): 시장구분코드 (J:KRX, NX:NXT)
fid_cond_scr_div_code (str): Unique key( 20168 )
fid_input_iscd (str): 0000:전체, 0001:거래소, 1001:코스닥, 2001:코스피200
fid_div_cls_code (str): 0: 전체,  1: 보통주 2: 우선주
fid_input_price_1 (str): 입력값 없을때 전체 (가격 ~)
fid_input_price_2 (str): 입력값 없을때 전체 (~ 가격)
fid_vol_cnt (str): 입력값 없을때 전체 (거래량 ~)
fid_trgt_cls_code (str): 0 : 전체
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/ranking/volume-power'
    if not fid_trgt_exls_cls_code:
        logger.error("fid_trgt_exls_cls_code is required. (e.g. '0')")
        raise ValueError("fid_trgt_exls_cls_code is required. (e.g. '0')")
    if fid_cond_mrkt_div_code != 'J':
        logger.error("fid_cond_mrkt_div_code must be 'J'.")
        raise ValueError("fid_cond_mrkt_div_code must be 'J'.")
    if fid_cond_scr_div_code != '20168':
        logger.error("fid_cond_scr_div_code must be '20168'.")
        raise ValueError("fid_cond_scr_div_code must be '20168'.")
    if fid_input_iscd not in ['0000', '0001', '1001', '2001']:
        logger.error("fid_input_iscd must be one of ['0000', '0001', '1001', '2001'].")
        raise ValueError("fid_input_iscd must be one of ['0000', '0001', '1001', '2001'].")
    if fid_div_cls_code not in ['0', '1', '2']:
        logger.error("fid_div_cls_code must be one of ['0', '1', '2'].")
        raise ValueError("fid_div_cls_code must be one of ['0', '1', '2'].")
    if not fid_trgt_cls_code:
        logger.error("fid_trgt_cls_code is required. (e.g. '0')")
        raise ValueError("fid_trgt_cls_code is required. (e.g. '0')")
    tr_id = 'FHPST01680000'
    params = {'fid_trgt_exls_cls_code': fid_trgt_exls_cls_code, 'fid_cond_mrkt_div_code': fid_cond_mrkt_div_code, 'fid_cond_scr_div_code': fid_cond_scr_div_code, 'fid_input_iscd': fid_input_iscd, 'fid_div_cls_code': fid_div_cls_code, 'fid_input_price_1': fid_input_price_1, 'fid_input_price_2': fid_input_price_2, 'fid_vol_cnt': fid_vol_cnt, 'fid_trgt_cls_code': fid_trgt_cls_code}
    return ApiRequest('domestic_stock.volume_power', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def volume_rank(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_blng_cls_code, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_input_date_1, tr_cont=''):
    """KIS domestic_stock.volume_rank 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건 시장 분류 코드 ("J": KRX, "NX": NXT, "UN": 통합, "W": ELW)
fid_cond_scr_div_code (str): 조건 화면 분류 코드 ("20171")
fid_input_iscd (str): 입력 종목코드 ("0000": 전체, 기타: 업종코드)
fid_div_cls_code (str): 분류 구분 코드 ("0": 전체, "1": 보통주, "2": 우선주)
fid_blng_cls_code (str): 소속 구분 코드 ("0": 평균거래량, "1": 거래증가율, "2": 평균거래회전율, "3": 거래금액순, "4": 평균거래금액회전율)
fid_trgt_cls_code (str): 대상 구분 코드 (9자리, "1" or "0", 차례대로 증거금 30% 40% 50% 60% 100% 신용보증금 30% 40% 50% 60%)
fid_trgt_exls_cls_code (str): 대상 제외 구분 코드 (10자리, "1" or "0", 차례대로 투자위험/경고/주의 관리종목 정리매매 불성실공시 우선주 거래정지 ETF ETN 신용주문불가 SPAC)
fid_input_price_1 (str): 입력 가격1 (가격 ~, 전체 가격 대상 조회 시 공란)
fid_input_price_2 (str): 입력 가격2 (~ 가격, 전체 가격 대상 조회 시 공란)
fid_vol_cnt (str): 거래량 수 (거래량 ~, 전체 거래량 대상 조회 시 공란)
fid_input_date_1 (str): 입력 날짜1 (공란)
tr_cont (str): 연속 거래 여부"""
    api_url = '/uapi/domestic-stock/v1/quotations/volume-rank'
    if fid_cond_mrkt_div_code not in ['J', 'NX', 'UN', 'W']:
        raise ValueError('조건 시장 분류 코드 확인요망!!!')
    if fid_cond_scr_div_code != '20171':
        raise ValueError('조건 화면 분류 코드 확인요망!!!')
    if fid_input_iscd == '':
        raise ValueError('입력 종목코드 확인요망!!!')
    if fid_div_cls_code not in ['0', '1', '2']:
        raise ValueError('분류 구분 코드 확인요망!!!')
    if fid_blng_cls_code not in ['0', '1', '2', '3', '4']:
        raise ValueError('소속 구분 코드 확인요망!!!')
    tr_id = 'FHPST01710000'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_DIV_CLS_CODE': fid_div_cls_code, 'FID_BLNG_CLS_CODE': fid_blng_cls_code, 'FID_TRGT_CLS_CODE': fid_trgt_cls_code, 'FID_TRGT_EXLS_CLS_CODE': fid_trgt_exls_cls_code, 'FID_INPUT_PRICE_1': fid_input_price_1, 'FID_INPUT_PRICE_2': fid_input_price_2, 'FID_VOL_CNT': fid_vol_cnt, 'FID_INPUT_DATE_1': fid_input_date_1}
    return ApiRequest('domestic_stock.volume_rank', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)
