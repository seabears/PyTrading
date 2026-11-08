"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def avg_unit(inqr_strt_dt, inqr_end_dt, pdno, prdt_type_cd, vrfc_kind_cd, NK30='', FK100='', tr_cont=''):
    """KIS domestic_bond.avg_unit 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
inqr_strt_dt (str): 조회 시작 일자 (예: '20230101')
inqr_end_dt (str): 조회 종료 일자 (예: '20230131')
pdno (str): 상품번호, 공백: 전체, 특정종목 조회시 : 종목코드
prdt_type_cd (str): 상품유형코드 (예: '302')
vrfc_kind_cd (str): 검증종류코드 (예: '00')
NK30 (str): 연속조회키30, 공백 허용
FK100 (str): 연속조회검색조건100, 공백 허용
tr_cont (str): 연속 거래 여부"""
    if not inqr_strt_dt:
        logger.error("inqr_strt_dt is required. (e.g. '20230101')")
        raise ValueError("inqr_strt_dt is required. (e.g. '20230101')")
    if not inqr_end_dt:
        logger.error("inqr_end_dt is required. (e.g. '20230131')")
        raise ValueError("inqr_end_dt is required. (e.g. '20230131')")
    if not prdt_type_cd:
        logger.error("prdt_type_cd is required. (e.g. '302')")
        raise ValueError("prdt_type_cd is required. (e.g. '302')")
    if not vrfc_kind_cd:
        logger.error("vrfc_kind_cd is required. (e.g. '00')")
        raise ValueError("vrfc_kind_cd is required. (e.g. '00')")
    tr_id = 'CTPF2005R'
    api_url = '/uapi/domestic-bond/v1/quotations/avg-unit'
    params = {'INQR_STRT_DT': inqr_strt_dt, 'INQR_END_DT': inqr_end_dt, 'PDNO': pdno, 'PRDT_TYPE_CD': prdt_type_cd, 'VRFC_KIND_CD': vrfc_kind_cd, 'CTX_AREA_NK30': NK30, 'CTX_AREA_FK100': FK100}
    return ApiRequest('domestic_bond.avg_unit', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def buy(cano, acnt_prdt_cd, pdno, ord_qty2, bond_ord_unpr, samt_mket_ptci_yn, bond_rtl_mket_yn, idcr_stfno='', mgco_aptm_odno='', ord_svr_dvsn_cd='', ctac_tlno=''):
    """KIS domestic_bond.buy 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호 (8자리)
acnt_prdt_cd (str): 계좌상품코드 (2자리)
pdno (str): 상품번호 (12자리)
ord_qty2 (str): 주문수량2 (19자리)
bond_ord_unpr (str): 채권주문단가 (182자리)
samt_mket_ptci_yn (str): 소액시장참여여부 ('Y' or 'N')
bond_rtl_mket_yn (str): 채권소매시장여부 ('Y' or 'N')
idcr_stfno (str, optional): 유치자직원번호 (6자리). Defaults to "".
mgco_aptm_odno (str, optional): 운용사지정주문번호 (12자리). Defaults to "".
ord_svr_dvsn_cd (str, optional): 주문서버구분코드. Defaults to "".
ctac_tlno (str, optional): 연락전화번호. Defaults to ""."""
    tr_id = 'TTTC0952U'
    api_url = '/uapi/domestic-bond/v1/trading/buy'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'ORD_QTY2': ord_qty2, 'BOND_ORD_UNPR': bond_ord_unpr, 'SAMT_MKET_PTCI_YN': samt_mket_ptci_yn, 'BOND_RTL_MKET_YN': bond_rtl_mket_yn, 'IDCR_STFNO': idcr_stfno, 'MGCO_APTM_ODNO': mgco_aptm_odno, 'ORD_SVR_DVSN_CD': ord_svr_dvsn_cd, 'CTAC_TLNO': ctac_tlno}
    return ApiRequest('domestic_bond.buy', api_url, tr_id, params, 'POST' if True else 'GET', 'real', '')

def inquire_asking_price(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS domestic_bond.inquire_asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 시장 분류 코드 (B 입력)
fid_input_iscd (str): 채권종목코드 (ex KR2033022D33)
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'B')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'B')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. 'KR2033022D33')")
        raise ValueError("fid_input_iscd is required. (e.g. 'KR2033022D33')")
    tr_id = 'FHKBJ773401C0'
    api_url = '/uapi/domestic-bond/v1/quotations/inquire-asking-price'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_bond.inquire_asking_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_balance(cano, acnt_prdt_cd, inqr_cndt, pdno, buy_dt, FK200='', NK200='', tr_cont=''):
    """KIS domestic_bond.inquire_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호
acnt_prdt_cd (str): 계좌상품코드
inqr_cndt (str): 조회조건 (00: 전체, 01: 상품번호단위)
pdno (str): 상품번호 (공백 허용)
buy_dt (str): 매수일자 (공백 허용)
FK200 (str): 연속조회검색조건200
NK200 (str): 연속조회키200
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    logger = logging.getLogger(__name__)
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not inqr_cndt:
        logger.error("inqr_cndt is required. (e.g. '00')")
        raise ValueError("inqr_cndt is required. (e.g. '00')")
    tr_id = 'CTSC8407R'
    api_url = '/uapi/domestic-bond/v1/trading/inquire-balance'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'INQR_CNDT': inqr_cndt, 'PDNO': pdno, 'BUY_DT': buy_dt, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('domestic_bond.inquire_balance', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_ccnl(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS domestic_bond.inquire_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (예: 'B')
fid_input_iscd (str): 입력종목코드 (예: 'KR2033022D33')
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'B')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'B')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. 'KR2033022D33')")
        raise ValueError("fid_input_iscd is required. (e.g. 'KR2033022D33')")
    tr_id = 'FHKBJ773403C0'
    api_url = '/uapi/domestic-bond/v1/quotations/inquire-ccnl'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_bond.inquire_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_daily_ccld(cano, acnt_prdt_cd, inqr_strt_dt, inqr_end_dt, sll_buy_dvsn_cd, sort_sqn_dvsn, pdno, nccs_yn, ctx_area_nk200, ctx_area_fk200, tr_cont=''):
    """KIS domestic_bond.inquire_daily_ccld 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호
acnt_prdt_cd (str): 계좌상품코드
inqr_strt_dt (str): 조회시작일자 (1주일 이내)
inqr_end_dt (str): 조회종료일자 (조회 당일)
sll_buy_dvsn_cd (str): 매도매수구분코드 (%(전체), 01(매도), 02(매수))
sort_sqn_dvsn (str): 정렬순서구분 (01(주문순서), 02(주문역순))
pdno (str): 상품번호
nccs_yn (str): 미체결여부 (N(전체), C(체결), Y(미체결))
ctx_area_nk200 (str): 연속조회키200
ctx_area_fk200 (str): 연속조회검색조건200
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not inqr_strt_dt:
        logger.error("inqr_strt_dt is required. (e.g. '20230101')")
        raise ValueError("inqr_strt_dt is required. (e.g. '20230101')")
    if not inqr_end_dt:
        logger.error("inqr_end_dt is required. (e.g. '20230107')")
        raise ValueError("inqr_end_dt is required. (e.g. '20230107')")
    if not sll_buy_dvsn_cd in ['%', '01', '02']:
        logger.error("sll_buy_dvsn_cd is required. (e.g. '01')")
        raise ValueError("sll_buy_dvsn_cd is required. (e.g. '01')")
    if not sort_sqn_dvsn in ['01', '02']:
        logger.error("sort_sqn_dvsn is required. (e.g. '01')")
        raise ValueError("sort_sqn_dvsn is required. (e.g. '01')")
    if not nccs_yn in ['N', 'C', 'Y']:
        logger.error("nccs_yn is required. (e.g. 'N')")
        raise ValueError("nccs_yn is required. (e.g. 'N')")
    tr_id = 'CTSC8013R'
    api_url = '/uapi/domestic-bond/v1/trading/inquire-daily-ccld'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'INQR_STRT_DT': inqr_strt_dt, 'INQR_END_DT': inqr_end_dt, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'SORT_SQN_DVSN': sort_sqn_dvsn, 'PDNO': pdno, 'NCCS_YN': nccs_yn, 'CTX_AREA_NK200': ctx_area_nk200, 'CTX_AREA_FK200': ctx_area_fk200}
    return ApiRequest('domestic_bond.inquire_daily_ccld', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_daily_itemchartprice(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS domestic_bond.inquire_daily_itemchartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건 시장 구분 코드 (필수)
fid_input_iscd (str): 입력 종목코드 (필수)
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'B')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'B')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. 'KR2033022D33')")
        raise ValueError("fid_input_iscd is required. (e.g. 'KR2033022D33')")
    tr_id = 'FHKBJ773701C0'
    api_url = '/uapi/domestic-bond/v1/quotations/inquire-daily-itemchartprice'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_bond.inquire_daily_itemchartprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_daily_price(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS domestic_bond.inquire_daily_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (예: 'B')
fid_input_iscd (str): 입력종목코드 (예: 'KR2033022D33')
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    logger = logging.getLogger(__name__)
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'B')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'B')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. 'KR2033022D33')")
        raise ValueError("fid_input_iscd is required. (e.g. 'KR2033022D33')")
    tr_id = 'FHKBJ773404C0'
    api_url = '/uapi/domestic-bond/v1/quotations/inquire-daily-price'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_bond.inquire_daily_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_price(fid_cond_mrkt_div_code, fid_input_iscd, tr_cont=''):
    """KIS domestic_bond.inquire_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): 조건시장분류코드 (예: 'B')
fid_input_iscd (str): 입력종목코드 (예: 'KR2033022D33')
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'B')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'B')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. 'KR2033022D33')")
        raise ValueError("fid_input_iscd is required. (e.g. 'KR2033022D33')")
    tr_id = 'FHKBJ773400C0'
    api_url = '/uapi/domestic-bond/v1/quotations/inquire-price'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd}
    return ApiRequest('domestic_bond.inquire_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_psbl_order(cano, acnt_prdt_cd, pdno, bond_ord_unpr, tr_cont=''):
    """KIS domestic_bond.inquire_psbl_order 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호 (필수)
acnt_prdt_cd (str): 계좌상품코드 (필수)
pdno (str): 채권종목코드(ex KR2033022D33)
bond_ord_unpr (str): 채권주문단가 (필수)
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    if not cano:
        logger.error("cano is required. (e.g. '1234567890')")
        raise ValueError("cano is required. (e.g. '1234567890')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not pdno:
        logger.error("pdno is required. (e.g. 'KR2033022D33')")
        raise ValueError("pdno is required. (e.g. 'KR2033022D33')")
    if not bond_ord_unpr:
        logger.error("bond_ord_unpr is required. (e.g. '1000')")
        raise ValueError("bond_ord_unpr is required. (e.g. '1000')")
    tr_id = 'TTTC8910R'
    api_url = '/uapi/domestic-bond/v1/trading/inquire-psbl-order'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'BOND_ORD_UNPR': bond_ord_unpr}
    return ApiRequest('domestic_bond.inquire_psbl_order', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_psbl_rvsecncl(cano, acnt_prdt_cd, ord_dt, odno, ctx_area_fk200, ctx_area_nk200, tr_cont=''):
    """KIS domestic_bond.inquire_psbl_rvsecncl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호 (예: '12345678')
acnt_prdt_cd (str): 계좌상품코드 (예: '01')
ord_dt (str): 주문일자 (예: '20230101')
odno (str): 주문번호 (예: '0000000001')
ctx_area_fk200 (str): 연속조회검색조건200 (예: '조건값')
ctx_area_nk200 (str): 연속조회키200 (예: '키값')
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    tr_id = 'CTSC8035R'
    api_url = '/uapi/domestic-bond/v1/trading/inquire-psbl-rvsecncl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'ORD_DT': ord_dt, 'ODNO': odno, 'CTX_AREA_FK200': ctx_area_fk200, 'CTX_AREA_NK200': ctx_area_nk200}
    return ApiRequest('domestic_bond.inquire_psbl_rvsecncl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def issue_info(pdno, prdt_type_cd, tr_cont=''):
    """KIS domestic_bond.issue_info 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
pdno (str): 채권 종목번호(ex. KR6449111CB8)
prdt_type_cd (str): Unique key(302)
tr_cont (str): 연속 거래 여부"""
    logger = logging.getLogger(__name__)
    if not pdno:
        logger.error("pdno is required. (e.g. 'KR6449111CB8')")
        raise ValueError("pdno is required. (e.g. 'KR6449111CB8')")
    if not prdt_type_cd:
        logger.error("prdt_type_cd is required. (e.g. '302')")
        raise ValueError("prdt_type_cd is required. (e.g. '302')")
    tr_id = 'CTPF1101R'
    api_url = '/uapi/domestic-bond/v1/quotations/issue-info'
    params = {'PDNO': pdno, 'PRDT_TYPE_CD': prdt_type_cd}
    return ApiRequest('domestic_bond.issue_info', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def order_rvsecncl(cano, acnt_prdt_cd, pdno, orgn_odno, ord_qty2, bond_ord_unpr, qty_all_ord_yn, rvse_cncl_dvsn_cd, mgco_aptm_odno='', ord_svr_dvsn_cd='0', ctac_tlno=''):
    """KIS domestic_bond.order_rvsecncl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호
acnt_prdt_cd (str): 계좌상품코드
pdno (str): 상품번호
orgn_odno (str): 원주문번호
ord_qty2 (str): 주문수량2
bond_ord_unpr (str): 채권주문단가
qty_all_ord_yn (str): 잔량전부주문여부
rvse_cncl_dvsn_cd (str): 정정취소구분코드
mgco_aptm_odno (str, optional): 운용사지정주문번호. Defaults to "".
ord_svr_dvsn_cd (str, optional): 주문서버구분코드. Defaults to "0".
ctac_tlno (str, optional): 연락전화번호. Defaults to ""."""
    tr_id = 'TTTC0953U'
    api_url = '/uapi/domestic-bond/v1/trading/order-rvsecncl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'ORGN_ODNO': orgn_odno, 'ORD_QTY2': ord_qty2, 'BOND_ORD_UNPR': bond_ord_unpr, 'QTY_ALL_ORD_YN': qty_all_ord_yn, 'RVSE_CNCL_DVSN_CD': rvse_cncl_dvsn_cd, 'MGCO_APTM_ODNO': mgco_aptm_odno, 'ORD_SVR_DVSN_CD': ord_svr_dvsn_cd, 'CTAC_TLNO': ctac_tlno}
    return ApiRequest('domestic_bond.order_rvsecncl', api_url, tr_id, params, 'POST' if True else 'GET', 'real', '')

def search_bond_info(pdno, prdt_type_cd, tr_cont=''):
    """KIS domestic_bond.search_bond_info 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
pdno (str): 상품번호 (필수)
prdt_type_cd (str): 상품유형코드 (필수)
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    logger = logging.getLogger(__name__)
    if not pdno:
        logger.error("pdno is required. (e.g. 'KR2033022D33')")
        raise ValueError("pdno is required. (e.g. 'KR2033022D33')")
    if not prdt_type_cd:
        logger.error("prdt_type_cd is required. (e.g. '302')")
        raise ValueError("prdt_type_cd is required. (e.g. '302')")
    tr_id = 'CTPF1114R'
    api_url = '/uapi/domestic-bond/v1/quotations/search-bond-info'
    params = {'PDNO': pdno, 'PRDT_TYPE_CD': prdt_type_cd}
    return ApiRequest('domestic_bond.search_bond_info', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def sell(cano, acnt_prdt_cd, ord_dvsn, pdno, ord_qty2, bond_ord_unpr, sprx_yn, samt_mket_ptci_yn, sll_agco_opps_sll_yn, bond_rtl_mket_yn, buy_dt='', buy_seq='', mgco_aptm_odno='', ord_svr_dvsn_cd='0', ctac_tlno=''):
    """KIS domestic_bond.sell 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호
acnt_prdt_cd (str): 계좌상품코드
ord_dvsn (str): 주문구분
pdno (str): 상품번호
ord_qty2 (str): 주문수량2
bond_ord_unpr (str): 채권주문단가
sprx_yn (str): 분리과세여부
samt_mket_ptci_yn (str): 소액시장참여여부
sll_agco_opps_sll_yn (str): 매도대행사반대매도여부
bond_rtl_mket_yn (str): 채권소매시장여부
buy_dt (str, optional): 매수일자. Defaults to "".
buy_seq (str, optional): 매수순번. Defaults to "".
mgco_aptm_odno (str, optional): 운용사지정주문번호. Defaults to "".
ord_svr_dvsn_cd (str, optional): 주문서버구분코드. Defaults to "0".
ctac_tlno (str, optional): 연락전화번호. Defaults to ""."""
    tr_id = 'TTTC0958U'
    api_url = '/uapi/domestic-bond/v1/trading/sell'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'ORD_DVSN': ord_dvsn, 'PDNO': pdno, 'ORD_QTY2': ord_qty2, 'BOND_ORD_UNPR': bond_ord_unpr, 'SPRX_YN': sprx_yn, 'BUY_DT': buy_dt, 'BUY_SEQ': buy_seq, 'SAMT_MKET_PTCI_YN': samt_mket_ptci_yn, 'SLL_AGCO_OPPS_SLL_YN': sll_agco_opps_sll_yn, 'BOND_RTL_MKET_YN': bond_rtl_mket_yn, 'MGCO_APTM_ODNO': mgco_aptm_odno, 'ORD_SVR_DVSN_CD': ord_svr_dvsn_cd, 'CTAC_TLNO': ctac_tlno}
    return ApiRequest('domestic_bond.sell', api_url, tr_id, params, 'POST' if True else 'GET', 'real', '')
