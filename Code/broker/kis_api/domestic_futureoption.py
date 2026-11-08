# 현재 사용 불허: 구현은 보존하며 Config/kis-api-catalog.json의 enabled=false로 전송·구독을 차단한다.
"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def display_board_callput(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_mrkt_cls_code, fid_mtrt_cnt, fid_mrkt_cls_code1, fid_cond_mrkt_cls_code=''):
    """KIS domestic_futureoption.display_board_callput 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. O: 옵션)
fid_cond_scr_div_code (str): [필수] 조건 화면 분류 코드 (ex. 20503)
fid_mrkt_cls_code (str): [필수] 시장 구분 코드 (ex. CO: 콜옵션)
fid_mtrt_cnt (str): [필수] 만기 수 (ex. 202508)
fid_mrkt_cls_code1 (str): [필수] 시장 구분 코드 (ex. PO: 풋옵션)
fid_cond_mrkt_cls_code (str): 조건 시장 구분 코드"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'O')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '20503')")
    if fid_mrkt_cls_code == '':
        raise ValueError("fid_mrkt_cls_code is required (e.g. 'CO')")
    if fid_mtrt_cnt == '':
        raise ValueError("fid_mtrt_cnt is required (e.g. '202508')")
    if fid_mrkt_cls_code1 == '':
        raise ValueError("fid_mrkt_cls_code1 is required (e.g. 'PO')")
    tr_id = 'FHPIF05030100'
    api_url = '/uapi/domestic-futureoption/v1/quotations/display-board-callput'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_MRKT_CLS_CODE': fid_mrkt_cls_code, 'FID_MTRT_CNT': fid_mtrt_cnt, 'FID_MRKT_CLS_CODE1': fid_mrkt_cls_code1, 'FID_COND_MRKT_CLS_CODE': fid_cond_mrkt_cls_code}
    return ApiRequest('domestic_futureoption.display_board_callput', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def display_board_futures(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_cond_mrkt_cls_code):
    """KIS domestic_futureoption.display_board_futures 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. F)
fid_cond_scr_div_code (str): [필수] 조건 화면 분류 코드 (ex. 20503)
fid_cond_mrkt_cls_code (str): [필수] 조건 시장 구분 코드 (ex. MKI)"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'F')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '20503')")
    if fid_cond_mrkt_cls_code == '':
        raise ValueError("fid_cond_mrkt_cls_code is required (e.g. 'MKI')")
    tr_id = 'FHPIF05030200'
    api_url = '/uapi/domestic-futureoption/v1/quotations/display-board-futures'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_COND_MRKT_CLS_CODE': fid_cond_mrkt_cls_code}
    return ApiRequest('domestic_futureoption.display_board_futures', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def display_board_option_list(fid_cond_scr_div_code, fid_cond_mrkt_div_code='', fid_cond_mrkt_cls_code=''):
    """KIS domestic_futureoption.display_board_option_list 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_scr_div_code (str): [필수] 조건 화면 분류 코드 (ex. 509)
fid_cond_mrkt_div_code (str): 조건 시장 분류 코드
fid_cond_mrkt_cls_code (str): 조건 시장 구분 코드"""
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '509')")
    tr_id = 'FHPIO056104C0'
    api_url = '/uapi/domestic-futureoption/v1/quotations/display-board-option-list'
    params = {'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_COND_MRKT_CLS_CODE': fid_cond_mrkt_cls_code}
    return ApiRequest('domestic_futureoption.display_board_option_list', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def display_board_top(fid_cond_mrkt_div_code, fid_input_iscd, fid_cond_mrkt_div_code1='', fid_cond_scr_div_code='', fid_mtrt_cnt='', fid_cond_mrkt_cls_code=''):
    """KIS domestic_futureoption.display_board_top 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. F)
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 101V06)
fid_cond_mrkt_div_code1 (str): 조건 시장 분류 코드
fid_cond_scr_div_code (str): 조건 화면 분류 코드
fid_mtrt_cnt (str): 만기 수
fid_cond_mrkt_cls_code (str): 조건 시장 구분 코드"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'F')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '101V06')")
    tr_id = 'FHPIF05030000'
    api_url = '/uapi/domestic-futureoption/v1/quotations/display-board-top'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_COND_MRKT_DIV_CODE1': fid_cond_mrkt_div_code1, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_MTRT_CNT': fid_mtrt_cnt, 'FID_COND_MRKT_CLS_CODE': fid_cond_mrkt_cls_code}
    return ApiRequest('domestic_futureoption.display_board_top', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def exp_price_trend(fid_input_iscd, fid_cond_mrkt_div_code):
    """KIS domestic_futureoption.exp_price_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_input_iscd (str): [필수] 입력 종목코드 (ex. 101V06)
fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. F)"""
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '101V06')")
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'F')")
    tr_id = 'FHPIF05110100'
    api_url = '/uapi/domestic-futureoption/v1/quotations/exp-price-trend'
    params = {'FID_INPUT_ISCD': fid_input_iscd, 'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code}
    return ApiRequest('domestic_futureoption.exp_price_trend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_asking_price(fid_cond_mrkt_div_code, fid_input_iscd, env_dv):
    """KIS domestic_futureoption.inquire_asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] FID 조건 시장 분류 코드 (ex. F: 지수선물, JF: 주식선물)
fid_input_iscd (str): [필수] FID 입력 종목코드 (ex. 101W09)
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'F', 'JF')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '101W09')")
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real', 'demo')")
    if env_dv == 'real':
        tr_id = 'FHMIF10010000'
    elif env_dv == 'demo':
        tr_id = 'FHMIF10010000'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/domestic-futureoption/v1/quotations/inquire-asking-price'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_futureoption.inquire_asking_price', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_balance(env_dv, cano, acnt_prdt_cd, mgna_dvsn, excc_stat_cd, FK200='', NK200='', tr_cont=''):
    """KIS domestic_futureoption.inquire_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 03)
mgna_dvsn (str): [필수] 증거금 구분 (ex. 01:게시,02:유지)
excc_stat_cd (str): [필수] 정산상태코드 (ex. 1:정산,2:본정산)
FK200 (str): 연속조회검색조건200
NK200 (str): 연속조회키200
tr_cont (str): 연속거래여부"""
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '03')")
    if mgna_dvsn == '':
        raise ValueError("mgna_dvsn is required (e.g. '01' or '02')")
    if excc_stat_cd == '':
        raise ValueError("excc_stat_cd is required (e.g. '1' or '2')")
    if env_dv == 'real':
        tr_id = 'CTFO6118R'
    elif env_dv == 'demo':
        tr_id = 'VTFO6118R'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-balance'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'MGNA_DVSN': mgna_dvsn, 'EXCC_STAT_CD': excc_stat_cd, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('domestic_futureoption.inquire_balance', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_balance_settlement_pl(cano, acnt_prdt_cd, inqr_dt, FK200='', NK200='', tr_cont=''):
    """KIS domestic_futureoption.inquire_balance_settlement_pl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 03)
inqr_dt (str): [필수] 조회일자
FK200 (str): 연속조회검색조건200
NK200 (str): 연속조회키200
tr_cont (str): 연속거래여부"""
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError('acnt_prdt_cd is required')
    if inqr_dt == '':
        raise ValueError('inqr_dt is required')
    tr_id = 'CTFO6117R'
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-balance-settlement-pl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'INQR_DT': inqr_dt, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('domestic_futureoption.inquire_balance_settlement_pl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_balance_valuation_pl(cano, acnt_prdt_cd, mgna_dvsn, excc_stat_cd, FK200='', NK200='', tr_cont=''):
    """KIS domestic_futureoption.inquire_balance_valuation_pl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. 계좌번호 체계(8-2)의 앞 8자리)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 계좌번호 체계(8-2)의 뒤 2자리)
mgna_dvsn (str): [필수] 증거금구분 (ex. 01:개시, 02:유지)
excc_stat_cd (str): [필수] 정산상태코드 (ex. 1:정산, 2:본정산)
FK200 (str): 연속조회검색조건200 (ex. 연속조회검색조건200)
NK200 (str): 연속조회키200 (ex. 연속조회키200)
tr_cont (str): 연속거래여부"""
    if cano == '':
        raise ValueError("cano is required (e.g. '계좌번호 체계(8-2)의 앞 8자리')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '계좌번호 체계(8-2)의 뒤 2자리')")
    if mgna_dvsn == '':
        raise ValueError("mgna_dvsn is required (e.g. '01:개시, 02:유지')")
    if excc_stat_cd == '':
        raise ValueError("excc_stat_cd is required (e.g. '1:정산, 2:본정산')")
    tr_id = 'CTFO6159R'
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-balance-valuation-pl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'MGNA_DVSN': mgna_dvsn, 'EXCC_STAT_CD': excc_stat_cd, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('domestic_futureoption.inquire_balance_valuation_pl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_ccnl(env_dv, cano, acnt_prdt_cd, strt_ord_dt, end_ord_dt, sll_buy_dvsn_cd, ccld_nccs_dvsn, sort_sqn, pdno='', strt_odno='', mket_id_cd='', FK200='', NK200='', tr_cont=''):
    """KIS domestic_futureoption.inquire_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 03)
strt_ord_dt (str): [필수] 시작주문일자 (ex. 주문내역 조회 시작 일자, YYYYMMDD)
end_ord_dt (str): [필수] 종료주문일자 (ex. 주문내역 조회 마지막 일자, YYYYMMDD)
sll_buy_dvsn_cd (str): [필수] 매도매수구분코드 (ex. 00:전체, 01:매도, 02:매수)
ccld_nccs_dvsn (str): [필수] 체결미체결구분 (ex. 00:전체, 01:체결, 02:미체결)
sort_sqn (str): [필수] 정렬순서 (ex. AS:정순, DS:역순)
pdno (str, optional): 상품번호. Defaults to "".
strt_odno (str, optional): 시작주문번호. Defaults to "".
mket_id_cd (str, optional): 시장ID코드. Defaults to "".
FK200 (str, optional): 연속조회검색조건200. Defaults to "".
NK200 (str, optional): 연속조회키200. Defaults to "".
tr_cont (str, optional): 연속거래여부. Defaults to ""."""
    if not env_dv:
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    if not cano:
        raise ValueError('cano is required')
    if not acnt_prdt_cd:
        raise ValueError("acnt_prdt_cd is required (e.g. '03')")
    if not strt_ord_dt:
        raise ValueError("strt_ord_dt is required (e.g. '20220730')")
    if not end_ord_dt:
        raise ValueError("end_ord_dt is required (e.g. '20220830')")
    if not sll_buy_dvsn_cd:
        raise ValueError("sll_buy_dvsn_cd is required (e.g. '00')")
    if not ccld_nccs_dvsn:
        raise ValueError("ccld_nccs_dvsn is required (e.g. '00')")
    if not sort_sqn:
        raise ValueError("sort_sqn is required (e.g. 'AS' or 'DS')")
    if env_dv == 'real':
        tr_id = 'TTTO5201R'
    elif env_dv == 'demo':
        tr_id = 'VTTO5201R'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-ccnl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'STRT_ORD_DT': strt_ord_dt, 'END_ORD_DT': end_ord_dt, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'CCLD_NCCS_DVSN': ccld_nccs_dvsn, 'SORT_SQN': sort_sqn, 'PDNO': pdno, 'STRT_ODNO': strt_odno, 'MKET_ID_CD': mket_id_cd, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('domestic_futureoption.inquire_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_ccnl_bstime(cano, acnt_prdt_cd, ord_dt, fuop_tr_strt_tmd, fuop_tr_end_tmd, FK200='', NK200='', tr_cont=''):
    """KIS domestic_futureoption.inquire_ccnl_bstime 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 03)
ord_dt (str): [필수] 주문일자 (ex. 20250101)
fuop_tr_strt_tmd (str): [필수] 선물옵션거래시작시각 (ex. HHMMSS)
fuop_tr_end_tmd (str): [필수] 선물옵션거래종료시각 (ex. HHMMSS)
FK200 (str): 연속조회검색조건200
NK200 (str): 연속조회키200
tr_cont (str): 연속거래여부"""
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '03')")
    if ord_dt == '':
        raise ValueError("ord_dt is required (e.g. '20250101')")
    if fuop_tr_strt_tmd == '':
        raise ValueError("fuop_tr_strt_tmd is required (e.g. 'HHMMSS')")
    if fuop_tr_end_tmd == '':
        raise ValueError("fuop_tr_end_tmd is required (e.g. 'HHMMSS')")
    tr_id = 'CTFO5139R'
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-ccnl-bstime'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'ORD_DT': ord_dt, 'FUOP_TR_STRT_TMD': fuop_tr_strt_tmd, 'FUOP_TR_END_TMD': fuop_tr_end_tmd, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('domestic_futureoption.inquire_ccnl_bstime', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_daily_amount_fee(cano, acnt_prdt_cd, inqr_strt_day, inqr_end_day, FK200='', NK200='', tr_cont=''):
    """KIS domestic_futureoption.inquire_daily_amount_fee 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 03)
inqr_strt_day (str): [필수] 조회시작일 (ex. 20240401)
inqr_end_day (str): [필수] 조회종료일 (ex. 20240625)
FK200 (str): 연속조회검색조건200
NK200 (str): 연속조회키200
tr_cont (str): 연속거래여부"""
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError('acnt_prdt_cd is required')
    if inqr_strt_day == '':
        raise ValueError('inqr_strt_day is required')
    if inqr_end_day == '':
        raise ValueError('inqr_end_day is required')
    tr_id = 'CTFO6119R'
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-daily-amount-fee'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'INQR_STRT_DAY': inqr_strt_day, 'INQR_END_DAY': inqr_end_day, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('domestic_futureoption.inquire_daily_amount_fee', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_daily_fuopchartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2, fid_period_div_code, env_dv):
    """KIS domestic_futureoption.inquire_daily_fuopchartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] FID 조건 시장 분류 코드 (ex. F: 지수선물, O: 지수옵션)
fid_input_iscd (str): [필수] 종목코드 (ex. 101W09)
fid_input_date_1 (str): [필수] 조회 시작일자 (ex. 20250301)
fid_input_date_2 (str): [필수] 조회 종료일자 (ex. 20250810)
fid_period_div_code (str): [필수] 기간분류코드 (ex. D: 일봉, W: 주봉)
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'F: 지수선물, O: 지수옵션')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '101W09')")
    if fid_input_date_1 == '':
        raise ValueError("fid_input_date_1 is required (e.g. '20250301')")
    if fid_input_date_2 == '':
        raise ValueError("fid_input_date_2 is required (e.g. '20250810')")
    if fid_period_div_code == '':
        raise ValueError("fid_period_div_code is required (e.g. 'D: 일봉, W: 주봉')")
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
    if env_dv == 'real':
        tr_id = 'FHKIF03020100'
    elif env_dv == 'demo':
        tr_id = 'FHKIF03020100'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/domestic-futureoption/v1/quotations/inquire-daily-fuopchartprice'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2, 'FID_PERIOD_DIV_CODE': fid_period_div_code}
    return ApiRequest('domestic_futureoption.inquire_daily_fuopchartprice', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_deposit(cano, acnt_prdt_cd):
    """KIS domestic_futureoption.inquire_deposit 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 03)"""
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError('acnt_prdt_cd is required')
    tr_id = 'CTRP6550R'
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-deposit'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd}
    return ApiRequest('domestic_futureoption.inquire_deposit', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_ngt_balance(cano, acnt_prdt_cd, mgna_dvsn, excc_stat_cd, acnt_pwd='', FK200='', NK200='', tr_cont=''):
    """KIS domestic_futureoption.inquire_ngt_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. 계좌번호 체계(8-2)의 앞 8자리)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 계좌번호 체계(8-2)의 뒤 2자리)
mgna_dvsn (str): [필수] 증거금구분 (ex. 01:개시, 02:유지)
excc_stat_cd (str): [필수] 정산상태코드 (ex. 1:정산, 2:본정산)
acnt_pwd (str): 계좌비밀번호
FK200 (str): 연속조회검색조건200
NK200 (str): 연속조회키200
tr_cont (str): 연속거래여부"""
    if cano == '':
        raise ValueError("cano is required (e.g. '계좌번호 체계(8-2)의 앞 8자리')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '계좌번호 체계(8-2)의 뒤 2자리')")
    if mgna_dvsn == '':
        raise ValueError("mgna_dvsn is required (e.g. '01:개시, 02:유지')")
    if excc_stat_cd == '':
        raise ValueError("excc_stat_cd is required (e.g. '1:정산, 2:본정산')")
    tr_id = 'CTFN6118R'
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-ngt-balance'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'MGNA_DVSN': mgna_dvsn, 'EXCC_STAT_CD': excc_stat_cd, 'ACNT_PWD': acnt_pwd, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('domestic_futureoption.inquire_ngt_balance', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_ngt_ccnl(cano, acnt_prdt_cd, strt_ord_dt, end_ord_dt, sll_buy_dvsn_cd, ccld_nccs_dvsn, sort_sqn='', strt_odno='', pdno='', mket_id_cd='', fuop_dvsn_cd='', scrn_dvsn='', FK200='', NK200='', tr_cont=''):
    """KIS domestic_futureoption.inquire_ngt_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호 (ex. 계좌번호 체계(8-2)의 앞 8자리)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 계좌번호 체계(8-2)의 뒤 2자리)
strt_ord_dt (str): [필수] 시작주문일자
end_ord_dt (str): [필수] 종료주문일자 (ex. 조회하려는 마지막 일자 다음일자로 조회 (ex. 20221011 까지의 내역을 조회하고자 할 경우, 20221012로 종료주문일자 설정))
sll_buy_dvsn_cd (str): [필수] 매도매수구분코드 (ex. 공란:default, 00:전체, 01:매도, 02:매수)
ccld_nccs_dvsn (str): [필수] 체결미체결구분 (ex. 00:전체, 01:체결, 02:미체결)
sort_sqn (str): 정렬순서 (ex. 공란:default(DS:정순, 그외:역순))
strt_odno (str): 시작주문번호 (ex. 공란:default)
pdno (str): 상품번호 (ex. 공란:default)
mket_id_cd (str): 시장ID코드 (ex. 공란:default)
fuop_dvsn_cd (str): 선물옵션구분코드 (ex. 공란:전체, 01:선물, 02:옵션)
scrn_dvsn (str): 화면구분 (ex. 02(Default))
FK200 (str): 연속조회검색조건200 (ex. 공란:최초 조회시, 이전 조회 Output CTX_AREA_FK200값:다음페이지 조회시(2번째부터))
NK200 (str): 연속조회키200 (ex. 공란:최초 조회시, 이전 조회 Output CTX_AREA_NK200값:다음페이지 조회시(2번째부터))
tr_cont (str): 연속거래여부"""
    if cano == '' or cano is None:
        raise ValueError("cano is required (e.g. '계좌번호 체계(8-2)의 앞 8자리')")
    if acnt_prdt_cd == '' or acnt_prdt_cd is None:
        raise ValueError("acnt_prdt_cd is required (e.g. '계좌번호 체계(8-2)의 뒤 2자리')")
    if strt_ord_dt == '' or strt_ord_dt is None:
        raise ValueError('strt_ord_dt is required')
    if end_ord_dt == '' or end_ord_dt is None:
        raise ValueError("end_ord_dt is required (e.g. '조회하려는 마지막 일자 다음일자로 조회 (ex. 20221011 까지의 내역을 조회하고자 할 경우, 20221012로 종료주문일자 설정)')")
    if sll_buy_dvsn_cd == '' or sll_buy_dvsn_cd is None:
        raise ValueError("sll_buy_dvsn_cd is required (e.g. '공란:default, 00:전체, 01:매도, 02:매수')")
    if ccld_nccs_dvsn == '' or ccld_nccs_dvsn is None:
        raise ValueError("ccld_nccs_dvsn is required (e.g. '00:전체, 01:체결, 02:미체결')")
    tr_id = 'STTN5201R'
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-ngt-ccnl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'STRT_ORD_DT': strt_ord_dt, 'END_ORD_DT': end_ord_dt, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'CCLD_NCCS_DVSN': ccld_nccs_dvsn, 'SORT_SQN': sort_sqn, 'STRT_ODNO': strt_odno, 'PDNO': pdno, 'MKET_ID_CD': mket_id_cd, 'FUOP_DVSN_CD': fuop_dvsn_cd, 'SCRN_DVSN': scrn_dvsn, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('domestic_futureoption.inquire_ngt_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_price(fid_cond_mrkt_div_code, fid_input_iscd, env_dv):
    """KIS domestic_futureoption.inquire_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] FID 조건 시장 분류 코드 (ex. F: 지수선물, O: 지수옵션)
fid_input_iscd (str): [필수] FID 입력 종목코드 (ex. 101W09)
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'F', 'O')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '101W09')")
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real', 'demo')")
    if env_dv == 'real':
        tr_id = 'FHMIF10000000'
    elif env_dv == 'demo':
        tr_id = 'FHMIF10000000'
    else:
        raise ValueError('env_dv can only be real or demo')
    api_url = '/uapi/domestic-futureoption/v1/quotations/inquire-price'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_futureoption.inquire_price', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_psbl_ngt_order(cano, acnt_prdt_cd, pdno, prdt_type_cd, sll_buy_dvsn_cd, unit_price, ord_dvsn_cd):
    """KIS domestic_futureoption.inquire_psbl_ngt_order 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드
pdno (str): [필수] 상품번호
prdt_type_cd (str): [필수] 상품유형코드 (ex. 301:선물옵션)
sll_buy_dvsn_cd (str): [필수] 매도매수구분코드 (ex. 01:매도, 02:매수)
unit_price (str): [필수] 주문가격1
ord_dvsn_cd (str): [필수] 주문구분코드 (ex. 01:지정가, 02:시장가, 03:조건부, 04:최유리, 10:지정가(IOC), 11:지정가(FOK), 12:시장가(IOC), 13:시장가(FOK), 14:최유리(IOC), 15:최유리(FOK))"""
    if cano == '' or cano is None:
        raise ValueError('cano is required')
    if acnt_prdt_cd == '' or acnt_prdt_cd is None:
        raise ValueError('acnt_prdt_cd is required')
    if pdno == '' or pdno is None:
        raise ValueError('pdno is required')
    if prdt_type_cd == '' or prdt_type_cd is None:
        raise ValueError("prdt_type_cd is required (e.g. '301')")
    if sll_buy_dvsn_cd == '' or sll_buy_dvsn_cd is None:
        raise ValueError("sll_buy_dvsn_cd is required (e.g. '01', '02')")
    if unit_price == '' or unit_price is None:
        raise ValueError('unit_price is required')
    if ord_dvsn_cd == '' or ord_dvsn_cd is None:
        raise ValueError("ord_dvsn_cd is required (e.g. '01', '02', '03', '04', '10', '11', '12', '13', '14', '15')")
    tr_id = 'STTN5105R'
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-psbl-ngt-order'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'PRDT_TYPE_CD': prdt_type_cd, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'UNIT_PRICE': unit_price, 'ORD_DVSN_CD': ord_dvsn_cd}
    return ApiRequest('domestic_futureoption.inquire_psbl_ngt_order', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def inquire_psbl_order(env_dv, cano, acnt_prdt_cd, pdno, sll_buy_dvsn_cd, unit_price, ord_dvsn_cd):
    """KIS domestic_futureoption.inquire_psbl_order 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 03)
pdno (str): [필수] 상품번호 (ex. 선물 6자리, 옵션 9자리)
sll_buy_dvsn_cd (str): [필수] 매도매수구분코드 (ex. 01:매도,02:매수)
unit_price (str): [필수] 주문가격1
ord_dvsn_cd (str): [필수] 주문구분코드"""
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '03')")
    if pdno == '':
        raise ValueError("pdno is required (e.g. '101W09')")
    if sll_buy_dvsn_cd == '':
        raise ValueError("sll_buy_dvsn_cd is required (e.g. '01' or '02')")
    if unit_price == '':
        raise ValueError('unit_price is required')
    if ord_dvsn_cd == '':
        raise ValueError('ord_dvsn_cd is required')
    if env_dv == 'real':
        tr_id = 'TTTO5105R'
    elif env_dv == 'demo':
        tr_id = 'VTTO5105R'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/domestic-futureoption/v1/trading/inquire-psbl-order'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'UNIT_PRICE': unit_price, 'ORD_DVSN_CD': ord_dvsn_cd}
    return ApiRequest('domestic_futureoption.inquire_psbl_order', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, '')

def inquire_time_fuopchartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code, fid_pw_data_incu_yn, fid_fake_tick_incu_yn, fid_input_date_1, fid_input_hour_1):
    """KIS domestic_futureoption.inquire_time_fuopchartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): [필수] FID 조건 시장 분류 코드 (ex. F: 지수선물, O: 지수옵션)
fid_input_iscd (str): [필수] FID 입력 종목코드 (ex. 101T12)
fid_hour_cls_code (str): [필수] FID 시간 구분 코드 (ex. 30: 30초, 60: 1분)
fid_pw_data_incu_yn (str): [필수] FID 과거 데이터 포함 여부 (ex. Y:과거, N: 당일)
fid_fake_tick_incu_yn (str): [필수] FID 허봉 포함 여부 (ex. N)
fid_input_date_1 (str): [필수] FID 입력 날짜1 (ex. 20230901)
fid_input_hour_1 (str): [필수] FID 입력 시간1 (ex. 100000)"""
    if fid_cond_mrkt_div_code == '':
        raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'F: 지수선물, O: 지수옵션')")
    if fid_input_iscd == '':
        raise ValueError("fid_input_iscd is required (e.g. '101T12')")
    if fid_hour_cls_code == '':
        raise ValueError("fid_hour_cls_code is required (e.g. '30: 30초, 60: 1분')")
    if fid_pw_data_incu_yn == '':
        raise ValueError("fid_pw_data_incu_yn is required (e.g. 'Y:과거, N: 당일')")
    if fid_fake_tick_incu_yn == '':
        raise ValueError("fid_fake_tick_incu_yn is required (e.g. 'N')")
    if fid_input_date_1 == '':
        raise ValueError("fid_input_date_1 is required (e.g. '20230901')")
    if fid_input_hour_1 == '':
        raise ValueError("fid_input_hour_1 is required (e.g. '100000')")
    tr_id = 'FHKIF03020200'
    api_url = '/uapi/domestic-futureoption/v1/quotations/inquire-time-fuopchartprice'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_HOUR_CLS_CODE': fid_hour_cls_code, 'FID_PW_DATA_INCU_YN': fid_pw_data_incu_yn, 'FID_FAKE_TICK_INCU_YN': fid_fake_tick_incu_yn, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_HOUR_1': fid_input_hour_1}
    return ApiRequest('domestic_futureoption.inquire_time_fuopchartprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def ngt_margin_detail(cano, acnt_prdt_cd, mgna_dvsn_cd):
    """KIS domestic_futureoption.ngt_margin_detail 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 03)
mgna_dvsn_cd (str): [필수] 증거금 구분코드 (ex. 01:위탁, 02:유지)"""
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '03')")
    if mgna_dvsn_cd == '':
        raise ValueError("mgna_dvsn_cd is required (e.g. '01:위탁, 02:유지')")
    tr_id = 'CTFN7107R'
    api_url = '/uapi/domestic-futureoption/v1/trading/ngt-margin-detail'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'MGNA_DVSN_CD': mgna_dvsn_cd}
    return ApiRequest('domestic_futureoption.ngt_margin_detail', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def order(env_dv, ord_dv, ord_prcs_dvsn_cd, cano, acnt_prdt_cd, sll_buy_dvsn_cd, shtn_pdno, ord_qty, unit_price, nmpr_type_cd, krx_nmpr_cndt_cd, ord_dvsn_cd, ctac_tlno='', fuop_item_dvsn_cd=''):
    """KIS domestic_futureoption.order 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
ord_dv (str): [필수] 매도매수구분 (ex. day:주간, night:야간)
ord_prcs_dvsn_cd (str): [필수] 주문처리구분코드 (ex. 02:주문전송)
cano (str): [필수] 종합계좌번호 (ex. 계좌번호 체계(8-2)의 앞 8자리)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 계좌번호 체계(8-2)의 뒤 2자리)
sll_buy_dvsn_cd (str): [필수] 매도매수구분코드 (ex. 01:매도, 02:매수)
shtn_pdno (str): [필수] 단축상품번호 (ex. 종목번호, 선물 6자리 (예: 101W09), 옵션 9자리 (예: 201S03370))
ord_qty (str): [필수] 주문수량
unit_price (str): [필수] 주문가격1 (ex. 시장가나 최유리 지정가인 경우 0으로 입력)
nmpr_type_cd (str): [필수] 호가유형코드 (ex. 01:지정가, 02:시장가, 03:조건부, 04:최유리)
krx_nmpr_cndt_cd (str): [필수] 한국거래소호가조건코드 (ex. 0:없음, 3:IOC, 4:FOK)
ord_dvsn_cd (str): [필수] 주문구분코드 (ex. 01:지정가, 02:시장가, 03:조건부, 04:최유리, 10:지정가(IOC), 11:지정가(FOK), 12:시장가(IOC), 13:시장가(FOK), 14:최유리(IOC), 15:최유리(FOK))
ctac_tlno (str): 연락전화번호 (ex. 고객의 연락 가능한 전화번호)
fuop_item_dvsn_cd (str): 선물옵션종목구분코드 (ex. 공란(Default))"""
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real', 'demo')")
    if ord_dv == '':
        raise ValueError("ord_dv is required (e.g. 'day', 'night')")
    if ord_prcs_dvsn_cd == '':
        raise ValueError("ord_prcs_dvsn_cd is required (e.g. '02')")
    if cano == '':
        raise ValueError("cano is required (e.g. '계좌번호 체계(8-2)의 앞 8자리')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '계좌번호 체계(8-2)의 뒤 2자리')")
    if sll_buy_dvsn_cd == '':
        raise ValueError("sll_buy_dvsn_cd is required (e.g. '01', '02')")
    if shtn_pdno == '':
        raise ValueError("shtn_pdno is required (e.g. '101W09', '201S03370')")
    if ord_qty == '':
        raise ValueError('ord_qty is required')
    if unit_price == '':
        raise ValueError("unit_price is required (e.g. '0')")
    if nmpr_type_cd == '':
        raise ValueError("nmpr_type_cd is required (e.g. '01', '02', '03', '04')")
    if krx_nmpr_cndt_cd == '':
        raise ValueError("krx_nmpr_cndt_cd is required (e.g. '0', '3', '4')")
    if ord_dvsn_cd == '':
        raise ValueError("ord_dvsn_cd is required (e.g. '01', '02', '03', '04', '10', '11', '12', '13', '14', '15')")
    if env_dv == 'real':
        if ord_dv == 'day':
            tr_id = 'TTTO1101U'
        elif ord_dv == 'night':
            tr_id = 'STTN1101U'
        else:
            raise ValueError("ord_dv can only be 'day' or 'night'")
    elif env_dv == 'demo':
        if ord_dv == 'day':
            tr_id = 'VTTO1101U'
        else:
            raise ValueError("ord_dv can only be 'day' for demo environment")
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/domestic-futureoption/v1/trading/order'
    params = {'ORD_PRCS_DVSN_CD': ord_prcs_dvsn_cd, 'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'SHTN_PDNO': shtn_pdno, 'ORD_QTY': ord_qty, 'UNIT_PRICE': unit_price, 'NMPR_TYPE_CD': nmpr_type_cd, 'KRX_NMPR_CNDT_CD': krx_nmpr_cndt_cd, 'ORD_DVSN_CD': ord_dvsn_cd, 'CTAC_TLNO': ctac_tlno, 'FUOP_ITEM_DVSN_CD': fuop_item_dvsn_cd}
    return ApiRequest('domestic_futureoption.order', api_url, tr_id, params, 'POST' if True else 'GET', env_dv, '')

def order_rvsecncl(env_dv, day_dv, ord_prcs_dvsn_cd, cano, acnt_prdt_cd, rvse_cncl_dvsn_cd, orgn_odno, ord_qty, unit_price, nmpr_type_cd, krx_nmpr_cndt_cd, rmn_qty_yn, ord_dvsn_cd, fuop_item_dvsn_cd=''):
    """KIS domestic_futureoption.order_rvsecncl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
day_dv (str): [필수] 주야간구분 (ex. day:주간, night:야간)
ord_prcs_dvsn_cd (str): [필수] 주문처리구분코드 (ex. 02)
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드
rvse_cncl_dvsn_cd (str): [필수] 정정취소구분코드 (ex. 01:정정, 02:취소)
orgn_odno (str): [필수] 원주문번호
ord_qty (str): [필수] 주문수량 (ex. 0:전량, 그 외는 수량)
unit_price (str): [필수] 주문가격1 (ex 0:시장가/최유리, 그 외 가격)
nmpr_type_cd (str): [필수] 호가유형코드 (ex. 01:지정가, 02:시장가, 03:조건부, 04:최유리)
krx_nmpr_cndt_cd (str): [필수] 한국거래소호가조건코드 (ex. 0:취소/없음, 3:IOC, 4:FOK)
rmn_qty_yn (str): [필수] 잔여수량여부 (ex. Y:전량, N:일부)
ord_dvsn_cd (str): [필수] 주문구분코드
fuop_item_dvsn_cd (str): 선물옵션종목구분코드"""
    if env_dv == 'real':
        if day_dv == 'day':
            tr_id = 'TTTO1103U'
        elif day_dv == 'night':
            tr_id = 'STTN1103U'
        else:
            raise ValueError("day_dv can only be 'day' or 'night'")
    elif env_dv == 'demo':
        if day_dv == 'day':
            tr_id = 'VTTO1103U'
        else:
            raise ValueError("day_dv can only be 'day' for demo environment")
    else:
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    api_url = '/uapi/domestic-futureoption/v1/trading/order-rvsecncl'
    params = {'ORD_PRCS_DVSN_CD': ord_prcs_dvsn_cd, 'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'RVSE_CNCL_DVSN_CD': rvse_cncl_dvsn_cd, 'ORGN_ODNO': orgn_odno, 'ORD_QTY': ord_qty, 'UNIT_PRICE': unit_price, 'NMPR_TYPE_CD': nmpr_type_cd, 'KRX_NMPR_CNDT_CD': krx_nmpr_cndt_cd, 'RMN_QTY_YN': rmn_qty_yn, 'ORD_DVSN_CD': ord_dvsn_cd, 'FUOP_ITEM_DVSN_CD': fuop_item_dvsn_cd}
    return ApiRequest('domestic_futureoption.order_rvsecncl', api_url, tr_id, params, 'POST' if True else 'GET', env_dv, '')


def margin_rate(bass_dt, bast_id="", ctx_area_nk200="", tr_cont=""):
    """선물옵션 증거금률. bass_dt는 YYYYMMDD, bast_id는 공백, 다음 커서는 ctx_area_nk200이다."""
    from datetime import datetime
    datetime.strptime(bass_dt, "%Y%m%d")
    parameters = {"BASS_DT": bass_dt, "BAST_ID": bast_id, "CTX_AREA_NK200": ctx_area_nk200}
    return ApiRequest("domestic_futureoption.margin_rate", "/uapi/domestic-futureoption/v1/quotations/margin-rate", "TTTO6032R", parameters, continuation=tr_cont)

