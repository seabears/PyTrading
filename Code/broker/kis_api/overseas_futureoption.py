# 현재 사용 불허: 구현은 보존하며 Config/kis-api-catalog.json의 enabled=false로 전송·구독을 차단한다.
"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def daily_ccnl(srs_cd, exch_cd, start_date_time, close_date_time, qry_tp, qry_cnt, qry_gap, index_key, tr_cont=''):
    """KIS overseas_futureoption.daily_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): 종목코드 (예: 6AM24)
exch_cd (str): 거래소코드 (예: CME)
start_date_time (str): 조회시작일시 (공백)
close_date_time (str): 조회종료일시 (예: 20240402)
qry_tp (str): 조회구분 (Q: 최초조회시, P: 다음키(INDEX_KEY) 입력하여 조회시)
qry_cnt (str): 요청개수 (예: 30, 최대 40)
qry_gap (str): 묶음개수 (공백, 분만 사용)
index_key (str): 이전조회KEY (공백)
tr_cont (str): 연속 거래 여부"""
    if not srs_cd:
        logger.error("srs_cd is required. (e.g. '6AM24')")
        raise ValueError("srs_cd is required. (e.g. '6AM24')")
    if not exch_cd:
        logger.error("exch_cd is required. (e.g. 'CME')")
        raise ValueError("exch_cd is required. (e.g. 'CME')")
    if not close_date_time:
        logger.error("close_date_time is required. (e.g. '20240402')")
        raise ValueError("close_date_time is required. (e.g. '20240402')")
    if not qry_tp:
        logger.error("qry_tp is required. (e.g. 'Q')")
        raise ValueError("qry_tp is required. (e.g. 'Q')")
    if not qry_cnt:
        logger.error("qry_cnt is required. (e.g. '30')")
        raise ValueError("qry_cnt is required. (e.g. '30')")
    tr_id = 'HHDFC55020100'
    api_url = '/uapi/overseas-futureoption/v1/quotations/daily-ccnl'
    params = {'SRS_CD': srs_cd, 'EXCH_CD': exch_cd, 'START_DATE_TIME': start_date_time, 'CLOSE_DATE_TIME': close_date_time, 'QRY_TP': qry_tp, 'QRY_CNT': qry_cnt, 'QRY_GAP': qry_gap, 'INDEX_KEY': index_key}
    return ApiRequest('overseas_futureoption.daily_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_asking_price(srs_cd, tr_cont=''):
    """KIS overseas_futureoption.inquire_asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): 종목코드
tr_cont (str): 연속 거래 여부"""
    if not srs_cd:
        logger.error("srs_cd is required. (e.g. 'EXAMPLE_SRS_CD')")
        raise ValueError("srs_cd is required. (e.g. 'EXAMPLE_SRS_CD')")
    tr_id = 'HHDFC86000000'
    api_url = '/uapi/overseas-futureoption/v1/quotations/inquire-asking-price'
    params = {'SRS_CD': srs_cd}
    return ApiRequest('overseas_futureoption.inquire_asking_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_ccld(cano, acnt_prdt_cd, ccld_nccs_dvsn, sll_buy_dvsn_cd, fuop_dvsn, ctx_area_fk200, ctx_area_nk200, tr_cont=''):
    """KIS overseas_futureoption.inquire_ccld 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ccld_nccs_dvsn (str): 01:전체 / 02:체결 / 03:미체결
sll_buy_dvsn_cd (str): %%:전체 / 01:매도 / 02:매수
fuop_dvsn (str): 00:전체 / 01:선물 / 02:옵션
ctx_area_fk200 (str): 연속조회검색조건200
ctx_area_nk200 (str): 연속조회키200
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '80012345')")
        raise ValueError("cano is required. (e.g. '80012345')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '08')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '08')")
    if not ccld_nccs_dvsn:
        logger.error("ccld_nccs_dvsn is required. (e.g. '01')")
        raise ValueError("ccld_nccs_dvsn is required. (e.g. '01')")
    if not sll_buy_dvsn_cd:
        logger.error("sll_buy_dvsn_cd is required. (e.g. '01')")
        raise ValueError("sll_buy_dvsn_cd is required. (e.g. '01')")
    if not fuop_dvsn:
        logger.error("fuop_dvsn is required. (e.g. '00')")
        raise ValueError("fuop_dvsn is required. (e.g. '00')")
    tr_id = 'OTFM3116R'
    api_url = '/uapi/overseas-futureoption/v1/trading/inquire-ccld'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'CCLD_NCCS_DVSN': ccld_nccs_dvsn, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'FUOP_DVSN': fuop_dvsn, 'CTX_AREA_FK200': ctx_area_fk200, 'CTX_AREA_NK200': ctx_area_nk200}
    return ApiRequest('overseas_futureoption.inquire_ccld', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_daily_ccld(cano, acnt_prdt_cd, strt_dt, end_dt, fuop_dvsn_cd, fm_pdgr_cd, crcy_cd, fm_item_ftng_yn, sll_buy_dvsn_cd, ctx_area_fk200, ctx_area_nk200, tr_cont=''):
    """KIS overseas_futureoption.inquire_daily_ccld 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
strt_dt (str): 시작일자(YYYYMMDD)
end_dt (str): 종료일자(YYYYMMDD)
fuop_dvsn_cd (str): 00:전체 / 01:선물 / 02:옵션
fm_pdgr_cd (str): 공란(Default)
crcy_cd (str): %%% : 전체 TUS: TOT_USD  / TKR: TOT_KRW KRW: 한국  / USD: 미국 EUR: EUR   / HKD: 홍콩 CNY: 중국  / JPY: 일본 VND: 베트남
fm_item_ftng_yn (str): "N"(Default)
sll_buy_dvsn_cd (str): %%: 전체 / 01 : 매도 / 02 : 매수
ctx_area_fk200 (str): 연속조회검색조건200
ctx_area_nk200 (str): 연속조회키200
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '80012345')")
        raise ValueError("cano is required. (e.g. '80012345')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '08')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '08')")
    if not strt_dt:
        logger.error("strt_dt is required. (e.g. '20221010')")
        raise ValueError("strt_dt is required. (e.g. '20221010')")
    if not end_dt:
        logger.error("end_dt is required. (e.g. '20221216')")
        raise ValueError("end_dt is required. (e.g. '20221216')")
    if fuop_dvsn_cd not in ['00', '01', '02']:
        logger.error("fuop_dvsn_cd is required. (e.g. '00', '01', '02')")
        raise ValueError("fuop_dvsn_cd is required. (e.g. '00', '01', '02')")
    if not crcy_cd:
        logger.error("crcy_cd is required. (e.g. '%%%',KRW, USD, EUR..)")
        raise ValueError("crcy_cd is required. (e.g. '%%%',KRW, USD, EUR..)")
    if not fm_item_ftng_yn:
        logger.error("fm_item_ftng_yn is required. (e.g. 'N')")
        raise ValueError("fm_item_ftng_yn is required. (e.g. 'N')")
    if not sll_buy_dvsn_cd:
        logger.error("sll_buy_dvsn_cd is required. (e.g. '%%')")
        raise ValueError("sll_buy_dvsn_cd is required. (e.g. '%%')")
    tr_id = 'OTFM3122R'
    api_url = '/uapi/overseas-futureoption/v1/trading/inquire-daily-ccld'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'STRT_DT': strt_dt, 'END_DT': end_dt, 'FUOP_DVSN_CD': fuop_dvsn_cd, 'FM_PDGR_CD': fm_pdgr_cd, 'CRCY_CD': crcy_cd, 'FM_ITEM_FTNG_YN': fm_item_ftng_yn, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'CTX_AREA_FK200': ctx_area_fk200, 'CTX_AREA_NK200': ctx_area_nk200}
    return ApiRequest('overseas_futureoption.inquire_daily_ccld', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_daily_order(cano, acnt_prdt_cd, strt_dt, end_dt, fm_pdgr_cd, ccld_nccs_dvsn, sll_buy_dvsn_cd, fuop_dvsn, ctx_area_fk200, ctx_area_nk200, tr_cont=''):
    """KIS overseas_futureoption.inquire_daily_order 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
strt_dt (str): 시작일자 (YYYYMMDD)
end_dt (str): 종료일자 (YYYYMMDD)
fm_pdgr_cd (str): FM상품군코드
ccld_nccs_dvsn (str): 체결미체결구분 (01:전체 / 02:체결 / 03:미체결)
sll_buy_dvsn_cd (str): 매도매수구분코드 (%%전체 / 01:매도 / 02:매수)
fuop_dvsn (str): 선물옵션구분 (00:전체 / 01:선물 / 02:옵션)
ctx_area_fk200 (str): 연속조회검색조건200
ctx_area_nk200 (str): 연속조회키200
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '08')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '08')")
    if not strt_dt:
        logger.error("strt_dt is required. (e.g. '20220101')")
        raise ValueError("strt_dt is required. (e.g. '20220101')")
    if not end_dt:
        logger.error("end_dt is required. (e.g. '20221214')")
        raise ValueError("end_dt is required. (e.g. '20221214')")
    if not ccld_nccs_dvsn:
        logger.error("ccld_nccs_dvsn is required. (e.g. '01')")
        raise ValueError("ccld_nccs_dvsn is required. (e.g. '01')")
    if not sll_buy_dvsn_cd:
        logger.error("sll_buy_dvsn_cd is required. (e.g. '%%')")
        raise ValueError("sll_buy_dvsn_cd is required. (e.g. '%%')")
    if not fuop_dvsn:
        logger.error("fuop_dvsn is required. (e.g. '00')")
        raise ValueError("fuop_dvsn is required. (e.g. '00')")
    tr_id = 'OTFM3120R'
    api_url = '/uapi/overseas-futureoption/v1/trading/inquire-daily-order'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'STRT_DT': strt_dt, 'END_DT': end_dt, 'FM_PDGR_CD': fm_pdgr_cd, 'CCLD_NCCS_DVSN': ccld_nccs_dvsn, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'FUOP_DVSN': fuop_dvsn, 'CTX_AREA_FK200': ctx_area_fk200, 'CTX_AREA_NK200': ctx_area_nk200}
    return ApiRequest('overseas_futureoption.inquire_daily_order', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_deposit(cano, acnt_prdt_cd, crcy_cd, inqr_dt, tr_cont=''):
    """KIS overseas_futureoption.inquire_deposit 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
crcy_cd (str): TUS: TOT_USD  / TKR: TOT_KRW KRW: 한국  / USD: 미국 EUR: EUR   / HKD: 홍콩 CNY: 중국  / JPY: 일본 VND: 베트남
inqr_dt (str): 조회일자 (YYYYMMDD 형식)
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '80012345')")
        raise ValueError("cano is required. (e.g. '80012345')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '08')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '08')")
    if not crcy_cd:
        logger.error("crcy_cd is required. (e.g. 'KRW')")
        raise ValueError("crcy_cd is required. (e.g. 'KRW')")
    if not inqr_dt:
        logger.error("inqr_dt is required. (e.g. '20221214')")
        raise ValueError("inqr_dt is required. (e.g. '20221214')")
    tr_id = 'OTFM1411R'
    api_url = '/uapi/overseas-futureoption/v1/trading/inquire-deposit'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'CRCY_CD': crcy_cd, 'INQR_DT': inqr_dt}
    return ApiRequest('overseas_futureoption.inquire_deposit', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_period_ccld(inqr_term_from_dt, inqr_term_to_dt, cano, acnt_prdt_cd, crcy_cd, whol_trsl_yn, fuop_dvsn, ctx_area_fk200, ctx_area_nk200, tr_cont=''):
    """KIS overseas_futureoption.inquire_period_ccld 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
inqr_term_from_dt (str): 조회기간FROM일자
inqr_term_to_dt (str): 조회기간TO일자
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
crcy_cd (str): '%%% : 전체 TUS: TOT_USD  / TKR: TOT_KRW KRW: 한국  / USD: 미국 EUR: EUR   / HKD: 홍콩 CNY: 중국  / JPY: 일본'
whol_trsl_yn (str): 전체환산여부
fuop_dvsn (str): 00:전체 / 01:선물 / 02:옵션
ctx_area_fk200 (str): 연속조회검색조건200
ctx_area_nk200 (str): 연속조회키200
tr_cont (str): 연속 거래 여부"""
    if not inqr_term_from_dt:
        logger.error("inqr_term_from_dt is required. (e.g. '20250601')")
        raise ValueError("inqr_term_from_dt is required. (e.g. '20250601')")
    if not inqr_term_to_dt:
        logger.error("inqr_term_to_dt is required. (e.g. '20250630')")
        raise ValueError("inqr_term_to_dt is required. (e.g. '20250630')")
    if not cano:
        logger.error("cano is required. (e.g. '80012345')")
        raise ValueError("cano is required. (e.g. '80012345')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '08')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '08')")
    if not crcy_cd:
        logger.error("crcy_cd is required. (e.g. '%%%')")
        raise ValueError("crcy_cd is required. (e.g. '%%%')")
    if not whol_trsl_yn:
        logger.error("whol_trsl_yn is required. (e.g. 'N')")
        raise ValueError("whol_trsl_yn is required. (e.g. 'N')")
    if not fuop_dvsn:
        logger.error("fuop_dvsn is required. (e.g. '00')")
        raise ValueError("fuop_dvsn is required. (e.g. '00')")
    tr_id = 'OTFM3118R'
    api_url = '/uapi/overseas-futureoption/v1/trading/inquire-period-ccld'
    params = {'INQR_TERM_FROM_DT': inqr_term_from_dt, 'INQR_TERM_TO_DT': inqr_term_to_dt, 'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'CRCY_CD': crcy_cd, 'WHOL_TRSL_YN': whol_trsl_yn, 'FUOP_DVSN': fuop_dvsn, 'CTX_AREA_FK200': ctx_area_fk200, 'CTX_AREA_NK200': ctx_area_nk200}
    return ApiRequest('overseas_futureoption.inquire_period_ccld', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_period_trans(inqr_term_from_dt, inqr_term_to_dt, cano, acnt_prdt_cd, acnt_tr_type_cd, crcy_cd, ctx_area_fk100, ctx_area_nk100, pwd_chk_yn, tr_cont=''):
    """KIS overseas_futureoption.inquire_period_trans 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
inqr_term_from_dt (str): 조회기간FROM일자 (예: '20220101')
inqr_term_to_dt (str): 조회기간TO일자 (예: '20221214')
cano (str): 계좌번호 체계(8-2)의 앞 8자리 (예: '80012345')
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리 (예: '08')
acnt_tr_type_cd (str): 계좌거래유형코드 (1: 전체, 2:입출금 , 3: 결제)
crcy_cd (str): 통화코드 ('%%%': 전체, 'TUS': TOT_USD, 'TKR': TOT_KRW, 'KRW': 한국, 'USD': 미국, 'EUR': EUR, 'HKD': 홍콩, 'CNY': 중국, 'JPY': 일본, 'VND': 베트남)
ctx_area_fk100 (str): 연속조회검색조건100
ctx_area_nk100 (str): 연속조회키100
pwd_chk_yn (str): 비밀번호체크여부
tr_cont (str): 연속 거래 여부"""
    if not inqr_term_from_dt:
        logger.error("inqr_term_from_dt is required. (e.g. '20220101')")
        raise ValueError("inqr_term_from_dt is required. (e.g. '20220101')")
    if not inqr_term_to_dt:
        logger.error("inqr_term_to_dt is required. (e.g. '20221214')")
        raise ValueError("inqr_term_to_dt is required. (e.g. '20221214')")
    if not cano:
        logger.error("cano is required. (e.g. '80012345')")
        raise ValueError("cano is required. (e.g. '80012345')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '08')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '08')")
    if not acnt_tr_type_cd:
        logger.error("acnt_tr_type_cd is required. (e.g. '%%')")
        raise ValueError("acnt_tr_type_cd is required. (e.g. '%%')")
    if not crcy_cd:
        logger.error("crcy_cd is required. (e.g. '%%%')")
        raise ValueError("crcy_cd is required. (e.g. '%%%')")
    tr_id = 'OTFM3114R'
    api_url = '/uapi/overseas-futureoption/v1/trading/inquire-period-trans'
    params = {'INQR_TERM_FROM_DT': inqr_term_from_dt, 'INQR_TERM_TO_DT': inqr_term_to_dt, 'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'ACNT_TR_TYPE_CD': acnt_tr_type_cd, 'CRCY_CD': crcy_cd, 'CTX_AREA_FK100': ctx_area_fk100, 'CTX_AREA_NK100': ctx_area_nk100, 'PWD_CHK_YN': pwd_chk_yn}
    return ApiRequest('overseas_futureoption.inquire_period_trans', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_price(srs_cd, tr_cont=''):
    """KIS overseas_futureoption.inquire_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): 종목코드 (예: CNHU24)
tr_cont (str): 연속 거래 여부"""
    if not srs_cd:
        logger.error("srs_cd is required. (e.g. 'CNHU24')")
        raise ValueError("srs_cd is required. (e.g. 'CNHU24')")
    tr_id = 'HHDFC55010000'
    api_url = '/uapi/overseas-futureoption/v1/quotations/inquire-price'
    params = {'SRS_CD': srs_cd}
    return ApiRequest('overseas_futureoption.inquire_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_psamount(cano, acnt_prdt_cd, ovrs_futr_fx_pdno, sll_buy_dvsn_cd, fm_ord_pric, ecis_rsvn_ord_yn, tr_cont=''):
    """KIS overseas_futureoption.inquire_psamount 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ovrs_futr_fx_pdno (str): 해외선물FX상품번호
sll_buy_dvsn_cd (str): 01 : 매도 / 02 : 매수
fm_ord_pric (str): FM주문가격
ecis_rsvn_ord_yn (str): 행사예약주문여부
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '80012345')")
        raise ValueError("cano is required. (e.g. '80012345')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '08')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '08')")
    if not ovrs_futr_fx_pdno:
        logger.error("ovrs_futr_fx_pdno is required. (e.g. '6AU22')")
        raise ValueError("ovrs_futr_fx_pdno is required. (e.g. '6AU22')")
    if sll_buy_dvsn_cd not in ['01', '02']:
        logger.error("sll_buy_dvsn_cd is required. (e.g. '01' or '02')")
        raise ValueError("sll_buy_dvsn_cd is required. (e.g. '01' or '02')")
    tr_id = 'OTFM3304R'
    api_url = '/uapi/overseas-futureoption/v1/trading/inquire-psamount'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'OVRS_FUTR_FX_PDNO': ovrs_futr_fx_pdno, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'FM_ORD_PRIC': fm_ord_pric, 'ECIS_RSVN_ORD_YN': ecis_rsvn_ord_yn}
    return ApiRequest('overseas_futureoption.inquire_psamount', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_time_futurechartprice(srs_cd, exch_cd, start_date_time, close_date_time, qry_tp, qry_cnt, qry_gap, index_key, tr_cont=''):
    """KIS overseas_futureoption.inquire_time_futurechartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): ex) CNHU24 ※ 종목코드 "포럼 > FAQ > 종목정보 다운로드(해외) - 해외지수선물" 참고
exch_cd (str): CME
start_date_time (str): 공백
close_date_time (str): ex) 20230823
qry_tp (str): Q : 최초조회시 , P : 다음키(INDEX_KEY) 입력하여 조회시
qry_cnt (str): 120 (조회갯수)
qry_gap (str): 5 (분간격)
index_key (str): 다음조회(QRY_TP를 P로 입력) 시, 이전 호출의 "output1 > index_key" 기입하여 조회
tr_cont (str): 연속 거래 여부"""
    if not srs_cd:
        logger.error("srs_cd is required. (e.g. 'BONU25')")
        raise ValueError("srs_cd is required. (e.g. 'BONU25')")
    if not exch_cd:
        logger.error("exch_cd is required. (e.g. 'EUREX')")
        raise ValueError("exch_cd is required. (e.g. 'EUREX')")
    if not close_date_time:
        logger.error("close_date_time is required. (e.g. '20250702')")
        raise ValueError("close_date_time is required. (e.g. '20250702')")
    if not qry_cnt:
        logger.error("qry_cnt is required. (e.g. '120')")
        raise ValueError("qry_cnt is required. (e.g. '120')")
    if not qry_gap:
        logger.error("qry_gap is required. (e.g. '1', '5', '10', '15', '30', '60')")
        raise ValueError("qry_gap is required. (e.g. '1', '5', '10', '15', '30', '60')")
    tr_id = 'HHDFC55020400'
    api_url = '/uapi/overseas-futureoption/v1/quotations/inquire-time-futurechartprice'
    params = {'SRS_CD': srs_cd, 'EXCH_CD': exch_cd, 'START_DATE_TIME': start_date_time, 'CLOSE_DATE_TIME': close_date_time, 'QRY_TP': qry_tp, 'QRY_CNT': qry_cnt, 'QRY_GAP': qry_gap, 'INDEX_KEY': index_key}
    return ApiRequest('overseas_futureoption.inquire_time_futurechartprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_time_optchartprice(srs_cd, exch_cd, qry_cnt, start_date_time='', close_date_time='', qry_gap='', qry_tp='', index_key='', tr_cont=''):
    """KIS overseas_futureoption.inquire_time_optchartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): [필수] 종목코드 (ex. OESU24 C5500)
exch_cd (str): [필수] 거래소코드 (ex. CME)
qry_cnt (str): [필수] 요청개수 (ex. 20)
start_date_time (str): 조회시작일시
close_date_time (str): 조회종료일시
qry_gap (str): 묶음개수
qry_tp (str): 조회구분
index_key (str): 이전조회KEY
tr_cont (str): 연속거래여부"""
    if srs_cd == '':
        raise ValueError("srs_cd is required (e.g. 'OESU24 C5500')")
    if exch_cd == '':
        raise ValueError("exch_cd is required (e.g. 'CME')")
    if qry_cnt == '':
        raise ValueError("qry_cnt is required (e.g. '20')")
    tr_id = 'HHDFO55020400'
    api_url = '/uapi/overseas-futureoption/v1/quotations/inquire-time-optchartprice'
    params = {'SRS_CD': srs_cd, 'EXCH_CD': exch_cd, 'QRY_CNT': qry_cnt, 'START_DATE_TIME': start_date_time, 'CLOSE_DATE_TIME': close_date_time, 'QRY_GAP': qry_gap, 'QRY_TP': qry_tp, 'INDEX_KEY': index_key}
    return ApiRequest('overseas_futureoption.inquire_time_optchartprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_unpd(cano, acnt_prdt_cd, fuop_dvsn, ctx_area_fk100, ctx_area_nk100, tr_cont=''):
    """KIS overseas_futureoption.inquire_unpd 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
fuop_dvsn (str): 00: 전체 / 01:선물 / 02: 옵션
ctx_area_fk100 (str): 연속조회검색조건100
ctx_area_nk100 (str): 연속조회키100
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '80012345')")
        raise ValueError("cano is required. (e.g. '80012345')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '08')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '08')")
    if fuop_dvsn not in ['00', '01', '02']:
        logger.error("fuop_dvsn is required. (e.g. '00')")
        raise ValueError("fuop_dvsn is required. (e.g. '00')")
    tr_id = 'OTFM1412R'
    api_url = '/uapi/overseas-futureoption/v1/trading/inquire-unpd'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'FUOP_DVSN': fuop_dvsn, 'CTX_AREA_FK100': ctx_area_fk100, 'CTX_AREA_NK100': ctx_area_nk100}
    return ApiRequest('overseas_futureoption.inquire_unpd', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def investor_unpd_trend(prod_iscd, bsop_date, upmu_gubun, cts_key, tr_cont=''):
    """KIS overseas_futureoption.investor_unpd_trend 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
prod_iscd (str): 금리 (GE, ZB, ZF,ZN,ZT), 금속(GC, PA, PL,SI, HG), 농산물(CC, CT,KC, OJ, SB, ZC,ZL, ZM, ZO, ZR, ZS, ZW), 에너지(CL, HO, NG, WBS), 지수(ES, NQ, TF, YM, VX), 축산물(GF, HE, LE), 통화(6A, 6B, 6C, 6E, 6J, 6N, 6S, DX)
bsop_date (str): 기준일(ex)20240513)
upmu_gubun (str): 0(수량), 1(증감)
cts_key (str): 공백
tr_cont (str): 연속 거래 여부"""
    if not prod_iscd:
        logger.error("prod_iscd is required. (e.g. 'ES')")
        raise ValueError("prod_iscd is required. (e.g. 'ES')")
    if not bsop_date:
        logger.error("bsop_date is required. (e.g. '20240624')")
        raise ValueError("bsop_date is required. (e.g. '20240624')")
    if not upmu_gubun:
        logger.error("upmu_gubun is required. (e.g. '0')")
        raise ValueError("upmu_gubun is required. (e.g. '0')")
    tr_id = 'HHDDB95030000'
    api_url = '/uapi/overseas-futureoption/v1/quotations/investor-unpd-trend'
    params = {'PROD_ISCD': prod_iscd, 'BSOP_DATE': bsop_date, 'UPMU_GUBUN': upmu_gubun, 'CTS_KEY': cts_key}
    return ApiRequest('overseas_futureoption.investor_unpd_trend', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def margin_detail(cano, acnt_prdt_cd, crcy_cd, inqr_dt, tr_cont=''):
    """KIS overseas_futureoption.margin_detail 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호 (8자리)
acnt_prdt_cd (str): 계좌상품코드 (2자리)
crcy_cd (str): 통화코드 ('TKR', 'TUS', 'USD', 'HKD', 'CNY', 'JPY', 'VND')
inqr_dt (str): 조회일자 (8자리, YYYYMMDD 형식)
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not crcy_cd:
        logger.error("crcy_cd is required. (e.g. 'USD')")
        raise ValueError("crcy_cd is required. (e.g. 'USD')")
    if not inqr_dt:
        logger.error("inqr_dt is required. (e.g. '20230701')")
        raise ValueError("inqr_dt is required. (e.g. '20230701')")
    tr_id = 'OTFM3115R'
    api_url = '/uapi/overseas-futureoption/v1/trading/margin-detail'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'CRCY_CD': crcy_cd, 'INQR_DT': inqr_dt}
    return ApiRequest('overseas_futureoption.margin_detail', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def market_time(fm_pdgr_cd, fm_clas_cd, fm_excg_cd, opt_yn, ctx_area_nk200, ctx_area_fk200, tr_cont=''):
    """KIS overseas_futureoption.market_time 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fm_pdgr_cd (str): FM상품군코드
fm_clas_cd (str): FM클래스코드
fm_excg_cd (str): FM거래소코드
opt_yn (str): 옵션여부
ctx_area_nk200 (str): 연속조회키200
ctx_area_fk200 (str): 연속조회검색조건200
tr_cont (str): 연속 거래 여부"""
    if not fm_excg_cd:
        logger.error("fm_excg_cd is required. (e.g. 'CME')")
        raise ValueError("fm_excg_cd is required. (e.g. 'CME')")
    if not opt_yn:
        logger.error("opt_yn is required. (e.g. 'N')")
        raise ValueError("opt_yn is required. (e.g. 'N')")
    tr_id = 'OTFM2229R'
    api_url = '/uapi/overseas-futureoption/v1/quotations/market-time'
    params = {'FM_PDGR_CD': fm_pdgr_cd, 'FM_CLAS_CD': fm_clas_cd, 'FM_EXCG_CD': fm_excg_cd, 'OPT_YN': opt_yn, 'CTX_AREA_NK200': ctx_area_nk200, 'CTX_AREA_FK200': ctx_area_fk200}
    return ApiRequest('overseas_futureoption.market_time', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def monthly_ccnl(srs_cd, exch_cd, start_date_time, close_date_time, qry_tp, qry_cnt, qry_gap, index_key, tr_cont=''):
    """KIS overseas_futureoption.monthly_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): 종목코드 (예: '6AM24')
exch_cd (str): 거래소코드 (예: 'CME')
start_date_time (str): 조회시작일시 (공백 허용)
close_date_time (str): 조회종료일시 (예: '20240402')
qry_tp (str): 조회구분 ('Q': 최초조회, 'P': 다음키 입력하여 조회)
qry_cnt (str): 요청개수 (예: '30', 최대 '40')
qry_gap (str): 묶음개수 (공백 허용)
index_key (str): 이전조회KEY (공백 허용)
tr_cont (str): 연속 거래 여부"""
    if not srs_cd:
        logger.error("srs_cd is required. (e.g. '6AM24')")
        raise ValueError("srs_cd is required. (e.g. '6AM24')")
    if not exch_cd:
        logger.error("exch_cd is required. (e.g. 'CME')")
        raise ValueError("exch_cd is required. (e.g. 'CME')")
    if not close_date_time:
        logger.error("close_date_time is required. (e.g. '20240402')")
        raise ValueError("close_date_time is required. (e.g. '20240402')")
    if not qry_tp:
        logger.error("qry_tp is required. ('Q' or 'P')")
        raise ValueError("qry_tp is required. ('Q' or 'P')")
    if not qry_cnt:
        logger.error("qry_cnt is required. (e.g. '30')")
        raise ValueError("qry_cnt is required. (e.g. '30')")
    tr_id = 'HHDFC55020300'
    api_url = '/uapi/overseas-futureoption/v1/quotations/monthly-ccnl'
    params = {'SRS_CD': srs_cd, 'EXCH_CD': exch_cd, 'START_DATE_TIME': start_date_time, 'CLOSE_DATE_TIME': close_date_time, 'QRY_TP': qry_tp, 'QRY_CNT': qry_cnt, 'QRY_GAP': qry_gap, 'INDEX_KEY': index_key}
    return ApiRequest('overseas_futureoption.monthly_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def opt_asking_price(srs_cd, tr_cont=''):
    """KIS overseas_futureoption.opt_asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): 종목명 (예: 'OTXM24 C22000')
tr_cont (str): 연속 거래 여부"""
    if not srs_cd:
        logger.error("srs_cd is required. (e.g. 'OTXM24 C22000')")
        raise ValueError("srs_cd is required. (e.g. 'OTXM24 C22000')")
    tr_id = 'HHDFO86000000'
    api_url = '/uapi/overseas-futureoption/v1/quotations/opt-asking-price'
    params = {'SRS_CD': srs_cd}
    return ApiRequest('overseas_futureoption.opt_asking_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def opt_daily_ccnl(srs_cd, exch_cd, qry_cnt, start_date_time='', close_date_time='', qry_gap='', qry_tp='', index_key='', tr_cont=''):
    """KIS overseas_futureoption.opt_daily_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): [필수] 종목코드 (ex. OESU24 C5500)
exch_cd (str): [필수] 거래소코드 (ex. CME)
qry_cnt (str): [필수] 요청개수 (ex. 20)
start_date_time (str): 조회시작일시
close_date_time (str): 조회종료일시
qry_gap (str): 묶음개수
qry_tp (str): 조회구분
index_key (str): 이전조회KEY
tr_cont (str): 연속거래여부"""
    if srs_cd == '' or srs_cd is None:
        raise ValueError("srs_cd is required (e.g. 'OESU24 C5500')")
    if exch_cd == '' or exch_cd is None:
        raise ValueError("exch_cd is required (e.g. 'CME')")
    if qry_cnt == '' or qry_cnt is None:
        raise ValueError("qry_cnt is required (e.g. '20')")
    tr_id = 'HHDFO55020100'
    api_url = '/uapi/overseas-futureoption/v1/quotations/opt-daily-ccnl'
    params = {'SRS_CD': srs_cd, 'EXCH_CD': exch_cd, 'QRY_CNT': qry_cnt, 'START_DATE_TIME': start_date_time, 'CLOSE_DATE_TIME': close_date_time, 'QRY_GAP': qry_gap, 'QRY_TP': qry_tp, 'INDEX_KEY': index_key}
    return ApiRequest('overseas_futureoption.opt_daily_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def opt_detail(srs_cd):
    """KIS overseas_futureoption.opt_detail 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): [필수] 종목명"""
    if srs_cd == '':
        raise ValueError("srs_cd is required (e.g. 'C5500')")
    tr_id = 'HHDFO55010100'
    api_url = '/uapi/overseas-futureoption/v1/quotations/opt-detail'
    params = {'SRS_CD': srs_cd}
    return ApiRequest('overseas_futureoption.opt_detail', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def opt_monthly_ccnl(srs_cd, exch_cd, qry_cnt, start_date_time='', close_date_time='', qry_gap='', qry_tp='', index_key='', tr_cont=''):
    """KIS overseas_futureoption.opt_monthly_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): [필수] 종목코드 (ex. OESU24 C5500)
exch_cd (str): [필수] 거래소코드 (ex. CME)
qry_cnt (str): [필수] 요청개수 (ex. 20)
start_date_time (str): 조회시작일시 (ex. "")
close_date_time (str): 조회종료일시 (ex. "")
qry_gap (str): 묶음개수 (ex. "")
qry_tp (str): 조회구분 (ex. "")
index_key (str): 이전조회KEY (ex. "")
tr_cont (str): 연속거래여부 (ex. "")"""
    if srs_cd == '':
        raise ValueError("srs_cd is required (e.g. 'OESU24 C5500')")
    if exch_cd == '':
        raise ValueError("exch_cd is required (e.g. 'CME')")
    if qry_cnt == '':
        raise ValueError("qry_cnt is required (e.g. '20')")
    tr_id = 'HHDFO55020300'
    api_url = '/uapi/overseas-futureoption/v1/quotations/opt-monthly-ccnl'
    params = {'SRS_CD': srs_cd, 'EXCH_CD': exch_cd, 'QRY_CNT': qry_cnt, 'START_DATE_TIME': start_date_time, 'CLOSE_DATE_TIME': close_date_time, 'QRY_GAP': qry_gap, 'QRY_TP': qry_tp, 'INDEX_KEY': index_key}
    return ApiRequest('overseas_futureoption.opt_monthly_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def opt_price(srs_cd):
    """KIS overseas_futureoption.opt_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): [필수] 종목코드"""
    if srs_cd == '':
        raise ValueError('srs_cd is required')
    tr_id = 'HHDFO55010000'
    api_url = '/uapi/overseas-futureoption/v1/quotations/opt-price'
    params = {'SRS_CD': srs_cd}
    return ApiRequest('overseas_futureoption.opt_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def opt_tick_ccnl(srs_cd, exch_cd, qry_cnt, start_date_time='', close_date_time='', qry_gap='', qry_tp='', index_key='', tr_cont=''):
    """KIS overseas_futureoption.opt_tick_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): [필수] 종목코드 (ex. OESU24 C5500)
exch_cd (str): [필수] 거래소코드 (ex. CME)
qry_cnt (str): [필수] 요청개수 (ex. 20)
start_date_time (str): 조회시작일시
close_date_time (str): 조회종료일시
qry_gap (str): 묶음개수
qry_tp (str): 조회구분
index_key (str): 이전조회KEY
tr_cont (str): 연속거래여부"""
    if srs_cd == '':
        raise ValueError("srs_cd is required (e.g. 'OESU24 C5500')")
    if exch_cd == '':
        raise ValueError("exch_cd is required (e.g. 'CME')")
    if qry_cnt == '':
        raise ValueError("qry_cnt is required (e.g. '20')")
    tr_id = 'HHDFO55020200'
    api_url = '/uapi/overseas-futureoption/v1/quotations/opt-tick-ccnl'
    params = {'SRS_CD': srs_cd, 'EXCH_CD': exch_cd, 'QRY_CNT': qry_cnt, 'START_DATE_TIME': start_date_time, 'CLOSE_DATE_TIME': close_date_time, 'QRY_GAP': qry_gap, 'QRY_TP': qry_tp, 'INDEX_KEY': index_key}
    return ApiRequest('overseas_futureoption.opt_tick_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def opt_weekly_ccnl(srs_cd, exch_cd, qry_cnt, start_date_time='', close_date_time='', qry_gap='', qry_tp='', index_key='', tr_cont=''):
    """KIS overseas_futureoption.opt_weekly_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): [필수] 종목코드 (ex. OESU24 C5500)
exch_cd (str): [필수] 거래소코드 (ex. CME)
qry_cnt (str): [필수] 요청개수 (ex. 20)
start_date_time (str): 조회시작일시
close_date_time (str): 조회종료일시
qry_gap (str): 묶음개수
qry_tp (str): 조회구분
index_key (str): 이전조회KEY
tr_cont (str): 연속거래여부"""
    if srs_cd == '':
        raise ValueError("srs_cd is required (e.g. 'OESU24 C5500')")
    if exch_cd == '':
        raise ValueError("exch_cd is required (e.g. 'CME')")
    if qry_cnt == '':
        raise ValueError("qry_cnt is required (e.g. '20')")
    tr_id = 'HHDFO55020000'
    api_url = '/uapi/overseas-futureoption/v1/quotations/opt-weekly-ccnl'
    params = {'SRS_CD': srs_cd, 'EXCH_CD': exch_cd, 'QRY_CNT': qry_cnt, 'START_DATE_TIME': start_date_time, 'CLOSE_DATE_TIME': close_date_time, 'QRY_GAP': qry_gap, 'QRY_TP': qry_tp, 'INDEX_KEY': index_key}
    return ApiRequest('overseas_futureoption.opt_weekly_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def order(cano, acnt_prdt_cd, ovrs_futr_fx_pdno, sll_buy_dvsn_cd, fm_lqd_ustl_ccld_dt, fm_lqd_ustl_ccno, pric_dvsn_cd, fm_limit_ord_pric, fm_stop_ord_pric, fm_ord_qty, fm_lqd_lmt_ord_pric, fm_lqd_stop_ord_pric, ccld_cndt_cd, cplx_ord_dvsn_cd, ecis_rsvn_ord_yn, fm_hdge_ord_scrn_yn):
    """KIS overseas_futureoption.order 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ovrs_futr_fx_pdno (str): 해외선물FX상품번호
sll_buy_dvsn_cd (str): 01 : 매도 02 : 매수
fm_lqd_ustl_ccld_dt (str): 빈칸 (hedge청산만 이용)
fm_lqd_ustl_ccno (str): 빈칸 (hedge청산만 이용)
pric_dvsn_cd (str): 1.지정, 2. 시장, 3. STOP, 4 S/L
fm_limit_ord_pric (str): 지정가인 경우 가격 입력 * 시장가, STOP주문인 경우, 빈칸("") 입력
fm_stop_ord_pric (str): STOP 주문 가격 입력 * 시장가, 지정가인 경우, 빈칸("") 입력
fm_ord_qty (str): FM주문수량
fm_lqd_lmt_ord_pric (str): 빈칸 (hedge청산만 이용)
fm_lqd_stop_ord_pric (str): 빈칸 (hedge청산만 이용)
ccld_cndt_cd (str): 일반적으로 6 (EOD, 지정가)  GTD인 경우 5, 시장가인 경우만 2
cplx_ord_dvsn_cd (str): 0 (hedge청산만 이용)
ecis_rsvn_ord_yn (str): N
fm_hdge_ord_scrn_yn (str): N"""
    if not cano:
        logger.error("cano is required. (e.g. '81012345')")
        raise ValueError("cano is required. (e.g. '81012345')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '08')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '08')")
    if not ovrs_futr_fx_pdno:
        logger.error("ovrs_futr_fx_pdno is required. (e.g. '1AALN25 C10.0')")
        raise ValueError("ovrs_futr_fx_pdno is required. (e.g. '1AALN25 C10.0')")
    if not sll_buy_dvsn_cd:
        logger.error("sll_buy_dvsn_cd is required. (e.g. '02')")
        raise ValueError("sll_buy_dvsn_cd is required. (e.g. '02')")
    if not pric_dvsn_cd:
        logger.error("pric_dvsn_cd is required. (e.g. '1')")
        raise ValueError("pric_dvsn_cd is required. (e.g. '1')")
    if not fm_ord_qty:
        logger.error("fm_ord_qty is required. (e.g. '1')")
        raise ValueError("fm_ord_qty is required. (e.g. '1')")
    if not ccld_cndt_cd:
        logger.error("ccld_cndt_cd is required. (e.g. '6')")
        raise ValueError("ccld_cndt_cd is required. (e.g. '6')")
    tr_id = 'OTFM3001U'
    api_url = '/uapi/overseas-futureoption/v1/trading/order'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'OVRS_FUTR_FX_PDNO': ovrs_futr_fx_pdno, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'FM_LQD_USTL_CCLD_DT': fm_lqd_ustl_ccld_dt, 'FM_LQD_USTL_CCNO': fm_lqd_ustl_ccno, 'PRIC_DVSN_CD': pric_dvsn_cd, 'FM_LIMIT_ORD_PRIC': fm_limit_ord_pric, 'FM_STOP_ORD_PRIC': fm_stop_ord_pric, 'FM_ORD_QTY': fm_ord_qty, 'FM_LQD_LMT_ORD_PRIC': fm_lqd_lmt_ord_pric, 'FM_LQD_STOP_ORD_PRIC': fm_lqd_stop_ord_pric, 'CCLD_CNDT_CD': ccld_cndt_cd, 'CPLX_ORD_DVSN_CD': cplx_ord_dvsn_cd, 'ECIS_RSVN_ORD_YN': ecis_rsvn_ord_yn, 'FM_HDGE_ORD_SCRN_YN': fm_hdge_ord_scrn_yn}
    return ApiRequest('overseas_futureoption.order', api_url, tr_id, params, 'POST' if True else 'GET', 'real', '')

def order_rvsecncl(cano, ord_dv, acnt_prdt_cd, orgn_ord_dt, orgn_odno, fm_limit_ord_pric, fm_stop_ord_pric, fm_lqd_lmt_ord_pric, fm_lqd_stop_ord_pric, fm_hdge_ord_scrn_yn, fm_mkpr_cvsn_yn):
    """KIS overseas_futureoption.order_rvsecncl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
ord_dv (str): 주문구분 (0:정정, 1:취소)
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
orgn_ord_dt (str): 원 주문 시 출력되는 ORD_DT 값을 입력 (현지거래일)
orgn_odno (str): 정정/취소시 주문번호(ODNO) 8자리를 문자열처럼 "0"을 포함해서 전송 (원 주문 시 출력된 ODNO 값 활용) (ex. ORGN_ODNO : 00360686)
fm_limit_ord_pric (str): OTFM3002U(해외선물옵션주문정정)만 사용
fm_stop_ord_pric (str): OTFM3002U(해외선물옵션주문정정)만 사용
fm_lqd_lmt_ord_pric (str): OTFM3002U(해외선물옵션주문정정)만 사용
fm_lqd_stop_ord_pric (str): OTFM3002U(해외선물옵션주문정정)만 사용
fm_hdge_ord_scrn_yn (str): N
fm_mkpr_cvsn_yn (str): OTFM3003U(해외선물옵션주문취소)만 사용  ※ FM_MKPR_CVSN_YN 항목에 'Y'로 설정하여 취소주문을 접수할 경우, 주문 취소확인이 들어오면 원장에서 시장가주문을 하나 또 내줌"""
    if not cano:
        logger.error("cano is required. (e.g. '81012345')")
        raise ValueError("cano is required. (e.g. '81012345')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '08')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '08')")
    if not orgn_ord_dt:
        logger.error("orgn_ord_dt is required. (e.g. '20250630')")
        raise ValueError("orgn_ord_dt is required. (e.g. '20250630')")
    if not orgn_odno:
        logger.error("orgn_odno is required. (e.g. '00360686')")
        raise ValueError("orgn_odno is required. (e.g. '00360686')")
    if ord_dv == '0':
        tr_id = 'OTFM3002U'
    elif ord_dv == '1':
        tr_id = 'OTFM3003U'
    else:
        logger.error("ord_dv is required. (e.g. '0' or '1')")
        raise ValueError("ord_dv is required. (e.g. '0' or '1')")
    api_url = '/uapi/overseas-futureoption/v1/trading/order-rvsecncl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'ORGN_ORD_DT': orgn_ord_dt, 'ORGN_ODNO': orgn_odno, 'FM_LIMIT_ORD_PRIC': fm_limit_ord_pric, 'FM_STOP_ORD_PRIC': fm_stop_ord_pric, 'FM_LQD_LMT_ORD_PRIC': fm_lqd_lmt_ord_pric, 'FM_LQD_STOP_ORD_PRIC': fm_lqd_stop_ord_pric, 'FM_HDGE_ORD_SCRN_YN': fm_hdge_ord_scrn_yn, 'FM_MKPR_CVSN_YN': fm_mkpr_cvsn_yn}
    logger.info('Calling API with parameters: %s', params)
    return ApiRequest('overseas_futureoption.order_rvsecncl', api_url, tr_id, params, 'POST' if True else 'GET', 'real', '')

def search_contract_detail(qry_cnt, tr_cont='', **kwargs):
    """KIS overseas_futureoption.search_contract_detail 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
qry_cnt (str): 입력한 코드 개수
tr_cont (str): 연속 거래 여부"""
    if not 1 <= int(qry_cnt) <= 32:
        logger.error("qry_cnt is required. (e.g. '1' ~ '32')")
        raise ValueError("qry_cnt is required. (e.g. '1' ~ '32')")
    tr_id = 'HHDFC55200000'
    api_url = '/uapi/overseas-futureoption/v1/quotations/search-contract-detail'
    params = {'QRY_CNT': qry_cnt}
    for i in range(1, 33):
        srs_key = f'srs_cd_{i:02d}'
        api_key = f'SRS_CD_{i:02d}'
        params[api_key] = kwargs.get(srs_key, '')
    return ApiRequest('overseas_futureoption.search_contract_detail', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def search_opt_detail(qry_cnt, srs_cd_01, srs_cd_02='', srs_cd_03='', srs_cd_04='', srs_cd_05='', srs_cd_06='', srs_cd_07='', srs_cd_08='', srs_cd_09='', srs_cd_10='', srs_cd_11='', srs_cd_12='', srs_cd_13='', srs_cd_14='', srs_cd_15='', srs_cd_16='', srs_cd_17='', srs_cd_18='', srs_cd_19='', srs_cd_20='', srs_cd_21='', srs_cd_22='', srs_cd_23='', srs_cd_24='', srs_cd_25='', srs_cd_26='', srs_cd_27='', srs_cd_28='', srs_cd_29='', srs_cd_30=''):
    """KIS overseas_futureoption.search_opt_detail 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
qry_cnt (str): [필수] 요청개수 (ex. SRS_CD_N 개수)
srs_cd_01 (str): [필수] 종목코드1
srs_cd_02 (Optional[str]): 종목코드2
srs_cd_03 (Optional[str]): 종목코드3
srs_cd_04 (Optional[str]): 종목코드4
srs_cd_05 (Optional[str]): 종목코드5
srs_cd_06 (Optional[str]): 종목코드6
srs_cd_07 (Optional[str]): 종목코드7
srs_cd_08 (Optional[str]): 종목코드8
srs_cd_09 (Optional[str]): 종목코드9
srs_cd_10 (Optional[str]): 종목코드10
srs_cd_11 (Optional[str]): 종목코드11
srs_cd_12 (Optional[str]): 종목코드12
srs_cd_13 (Optional[str]): 종목코드13
srs_cd_14 (Optional[str]): 종목코드14
srs_cd_15 (Optional[str]): 종목코드15
srs_cd_16 (Optional[str]): 종목코드16
srs_cd_17 (Optional[str]): 종목코드17
srs_cd_18 (Optional[str]): 종목코드18
srs_cd_19 (Optional[str]): 종목코드19
srs_cd_20 (Optional[str]): 종목코드20
srs_cd_21 (Optional[str]): 종목코드21
srs_cd_22 (Optional[str]): 종목코드22
srs_cd_23 (Optional[str]): 종목코드23
srs_cd_24 (Optional[str]): 종목코드24
srs_cd_25 (Optional[str]): 종목코드25
srs_cd_26 (Optional[str]): 종목코드26
srs_cd_27 (Optional[str]): 종목코드27
srs_cd_28 (Optional[str]): 종목코드28
srs_cd_29 (Optional[str]): 종목코드29
srs_cd_30 (Optional[str]): 종목코드30"""
    if qry_cnt == '':
        raise ValueError("qry_cnt is required (e.g. 'SRS_CD_N 개수')")
    if srs_cd_01 == '':
        raise ValueError('srs_cd_01 is required')
    tr_id = 'HHDFO55200000'
    api_url = '/uapi/overseas-futureoption/v1/quotations/search-opt-detail'
    params = {'QRY_CNT': qry_cnt, 'SRS_CD_01': srs_cd_01}
    if srs_cd_02:
        params['SRS_CD_02'] = srs_cd_02
    if srs_cd_03:
        params['SRS_CD_03'] = srs_cd_03
    if srs_cd_04:
        params['SRS_CD_04'] = srs_cd_04
    if srs_cd_05:
        params['SRS_CD_05'] = srs_cd_05
    if srs_cd_06:
        params['SRS_CD_06'] = srs_cd_06
    if srs_cd_07:
        params['SRS_CD_07'] = srs_cd_07
    if srs_cd_08:
        params['SRS_CD_08'] = srs_cd_08
    if srs_cd_09:
        params['SRS_CD_09'] = srs_cd_09
    if srs_cd_10:
        params['SRS_CD_10'] = srs_cd_10
    if srs_cd_11:
        params['SRS_CD_11'] = srs_cd_11
    if srs_cd_12:
        params['SRS_CD_12'] = srs_cd_12
    if srs_cd_13:
        params['SRS_CD_13'] = srs_cd_13
    if srs_cd_14:
        params['SRS_CD_14'] = srs_cd_14
    if srs_cd_15:
        params['SRS_CD_15'] = srs_cd_15
    if srs_cd_16:
        params['SRS_CD_16'] = srs_cd_16
    if srs_cd_17:
        params['SRS_CD_17'] = srs_cd_17
    if srs_cd_18:
        params['SRS_CD_18'] = srs_cd_18
    if srs_cd_19:
        params['SRS_CD_19'] = srs_cd_19
    if srs_cd_20:
        params['SRS_CD_20'] = srs_cd_20
    if srs_cd_21:
        params['SRS_CD_21'] = srs_cd_21
    if srs_cd_22:
        params['SRS_CD_22'] = srs_cd_22
    if srs_cd_23:
        params['SRS_CD_23'] = srs_cd_23
    if srs_cd_24:
        params['SRS_CD_24'] = srs_cd_24
    if srs_cd_25:
        params['SRS_CD_25'] = srs_cd_25
    if srs_cd_26:
        params['SRS_CD_26'] = srs_cd_26
    if srs_cd_27:
        params['SRS_CD_27'] = srs_cd_27
    if srs_cd_28:
        params['SRS_CD_28'] = srs_cd_28
    if srs_cd_29:
        params['SRS_CD_29'] = srs_cd_29
    if srs_cd_30:
        params['SRS_CD_30'] = srs_cd_30
    return ApiRequest('overseas_futureoption.search_opt_detail', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def stock_detail(srs_cd, tr_cont=''):
    """KIS overseas_futureoption.stock_detail 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): ex) CNHU24 ※ 종목코드 "포럼 > FAQ > 종목정보 다운로드(해외) - 해외지수선물" 참고
tr_cont (str): 연속 거래 여부"""
    if not srs_cd:
        logger.error("srs_cd is required. (e.g. '6AU22')")
        raise ValueError("srs_cd is required. (e.g. '6AU22')")
    tr_id = 'HHDFC55010100'
    api_url = '/uapi/overseas-futureoption/v1/quotations/stock-detail'
    params = {'SRS_CD': srs_cd}
    return ApiRequest('overseas_futureoption.stock_detail', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def tick_ccnl(srs_cd, exch_cd, start_date_time, close_date_time, qry_tp, qry_cnt, qry_gap, index_key, tr_cont=''):
    """KIS overseas_futureoption.tick_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): 종목코드 (예: '6AM24')
exch_cd (str): 거래소코드 (예: 'CME')
start_date_time (str): 조회시작일시 (공백 허용)
close_date_time (str): 조회종료일시 (예: '20240402')
qry_tp (str): 조회구분 ('Q': 최초조회, 'P': 다음키 입력하여 조회)
qry_cnt (str): 요청개수 (예: '30', 최대 '40')
qry_gap (str): 묶음개수 (공백 허용)
index_key (str): 이전조회KEY (공백 허용)
tr_cont (str): 연속 거래 여부"""
    if not srs_cd:
        logger.error("srs_cd is required. (e.g. '6AM24')")
        raise ValueError("srs_cd is required. (e.g. '6AM24')")
    if not exch_cd:
        logger.error("exch_cd is required. (e.g. 'CME')")
        raise ValueError("exch_cd is required. (e.g. 'CME')")
    if not close_date_time:
        logger.error("close_date_time is required. (e.g. '20240402')")
        raise ValueError("close_date_time is required. (e.g. '20240402')")
    if not qry_tp:
        logger.error("qry_tp is required. ('Q' or 'P')")
        raise ValueError("qry_tp is required. ('Q' or 'P')")
    if not qry_cnt:
        logger.error("qry_cnt is required. (e.g. '30')")
        raise ValueError("qry_cnt is required. (e.g. '30')")
    tr_id = 'HHDFC55020200'
    api_url = '/uapi/overseas-futureoption/v1/quotations/tick-ccnl'
    params = {'SRS_CD': srs_cd, 'EXCH_CD': exch_cd, 'START_DATE_TIME': start_date_time, 'CLOSE_DATE_TIME': close_date_time, 'QRY_TP': qry_tp, 'QRY_CNT': qry_cnt, 'QRY_GAP': qry_gap, 'INDEX_KEY': index_key}
    return ApiRequest('overseas_futureoption.tick_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def weekly_ccnl(srs_cd, exch_cd, start_date_time, close_date_time, qry_tp, qry_cnt, qry_gap, index_key, tr_cont=''):
    """KIS overseas_futureoption.weekly_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
srs_cd (str): 종목코드, 예) 6AM24
exch_cd (str): 거래소코드, 예) CME
start_date_time (str): 조회시작일시, 공백
close_date_time (str): 조회종료일시, 예) 20240402
qry_tp (str): 조회구분, Q : 최초조회시 , P : 다음키(INDEX_KEY) 입력하여 조회시
qry_cnt (str): 요청개수, 예) 30 (최대 40)
qry_gap (str): 묶음개수, 공백 (분만 사용)
index_key (str): 이전조회KEY, 공백
tr_cont (str): 연속 거래 여부"""
    if not srs_cd:
        logger.error("srs_cd is required. (e.g. '6AM24')")
        raise ValueError("srs_cd is required. (e.g. '6AM24')")
    if not exch_cd:
        logger.error("exch_cd is required. (e.g. 'CME')")
        raise ValueError("exch_cd is required. (e.g. 'CME')")
    if not close_date_time:
        logger.error("close_date_time is required. (e.g. '20240402')")
        raise ValueError("close_date_time is required. (e.g. '20240402')")
    if not qry_cnt:
        logger.error("qry_cnt is required. (e.g. '30')")
        raise ValueError("qry_cnt is required. (e.g. '30')")
    tr_id = 'HHDFC55020000'
    api_url = '/uapi/overseas-futureoption/v1/quotations/weekly-ccnl'
    params = {'SRS_CD': srs_cd, 'EXCH_CD': exch_cd, 'START_DATE_TIME': start_date_time, 'CLOSE_DATE_TIME': close_date_time, 'QRY_TP': qry_tp, 'QRY_CNT': qry_cnt, 'QRY_GAP': qry_gap, 'INDEX_KEY': index_key}
    return ApiRequest('overseas_futureoption.weekly_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)
