"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def inquire_component_stock_price(fid_cond_mrkt_div_code, fid_input_iscd, fid_cond_scr_div_code):
    """KIS etfetn.inquire_component_stock_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건시장분류코드 (ex. J: 주식/ETF/ETN)
fid_input_iscd (str): [필수] 입력종목코드 (ex. 123456)
fid_cond_scr_div_code (str): [필수] 조건화면분류코드 (ex. 11216)"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J: 주식/ETF/ETN')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '11216')")
    tr_id = 'FHKST121600C0'
    api_url = '/uapi/etfetn/v1/quotations/inquire-component-stock-price'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code}
    return ApiRequest('etfetn.inquire_component_stock_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_price(fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS etfetn.inquire_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 123456)"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX, NX:NXT, UN:통합')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    tr_id = 'FHPST02400000'
    api_url = '/uapi/etfetn/v1/quotations/inquire-price'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('etfetn.inquire_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def nav_comparison_daily_trend(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2):
    """KIS etfetn.nav_comparison_daily_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건시장분류코드 (ex. J:주식)
fid_input_iscd (str): [필수] 입력종목코드 (ex. 123456)
fid_input_date_1 (str): [필수] 조회시작일자 (ex. 20240101)
fid_input_date_2 (str): [필수] 조회종료일자 (ex. 20240220)"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:주식')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if fid_input_date_1 == '':
        raise ValueError("fid_input_date_1 is required (e.g. '20240101')")
    if fid_input_date_2 == '':
        raise ValueError("fid_input_date_2 is required (e.g. '20240220')")
    tr_id = 'FHPST02440200'
    api_url = '/uapi/etfetn/v1/quotations/nav-comparison-daily-trend'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2}
    return ApiRequest('etfetn.nav_comparison_daily_trend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def nav_comparison_time_trend(fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code):
    """KIS etfetn.nav_comparison_time_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건시장분류코드 (ex. E)
fid_input_iscd (str): [필수] 입력종목코드 (ex. 123456)
fid_hour_cls_code (str): [필수] 시간구분코드 (ex. 60:1분,180:3분,...,7200:120분)"""
    if fid_cond_mrkt_div_code == '' or fid_cond_mrkt_div_code is None:
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'E')")
    if fid_input_iscd == '' or fid_input_iscd is None:
        raise ValueError("fid_input_iscd is required (e.g. '123456')")
    if fid_hour_cls_code == '' or fid_hour_cls_code is None:
        raise ValueError("fid_hour_cls_code is required (e.g. '60:1분,180:3분,...,7200:120분')")
    tr_id = 'FHPST02440100'
    api_url = '/uapi/etfetn/v1/quotations/nav-comparison-time-trend'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_HOUR_CLS_CODE': fid_hour_cls_code}
    return ApiRequest('etfetn.nav_comparison_time_trend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def nav_comparison_trend(fid_cond_mrkt_div_code, fid_input_iscd):
    """KIS etfetn.nav_comparison_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J)
fid_input_iscd (str): [필수] 입력 종목코드"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J')")
    if fid_input_iscd == '':
        raise ValueError('fid_input_iscd is required')
    tr_id = 'FHPST02440000'
    api_url = '/uapi/etfetn/v1/quotations/nav-comparison-trend'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('etfetn.nav_comparison_trend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')


def inquire_asking_price(fid_input_iscd, fid_cond_mrkt_div_code="J"):
    """ETF 호가. 6자리 종목코드와 시장 구분 J를 사용한다."""
    if len(fid_input_iscd) != 6 or not fid_input_iscd.isdigit() or fid_cond_mrkt_div_code != "J":
        raise ValueError("ETF 종목은 6자리 숫자, 시장 구분은 J여야 합니다.")
    return ApiRequest("etfetn.inquire_asking_price", "/uapi/etfetn/v1/quotations/inquire-asking-price", "FHPST02400200", {"FID_COND_MRKT_DIV_CODE": fid_cond_mrkt_div_code, "FID_INPUT_ISCD": fid_input_iscd})

