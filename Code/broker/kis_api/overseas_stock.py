"""상품별 KIS 요청 함수. params와 TR ID 선택을 수정하는 위치를 함수별로 분리했다.

공식 예제 고정 커밋 2077773a69a428daf63e148182511f068cc45de3의 요청 계약에서 생성했다.
각 함수는 전송 명세만 반환한다. 응답과 네트워크 처리는 client.py에 있다.
"""
import logging
from .models import ApiRequest, Subscription
logger = logging.getLogger(__name__)

def algo_ordno(cano, acnt_prdt_cd, trad_dt, FK200='', NK200='', tr_cont=''):
    """KIS overseas_stock.algo_ordno 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 종합계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 01)
trad_dt (str): [필수] 거래일자
FK200 (str): 연속조회검색조건200
NK200 (str): 연속조회키200
tr_cont (str): 연속거래여부"""
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '01')")
    if trad_dt == '':
        raise ValueError('trad_dt is required')
    tr_id = 'TTTS6058R'
    api_url = '/uapi/overseas-stock/v1/trading/algo-ordno'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'TRAD_DT': trad_dt, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('overseas_stock.algo_ordno', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def daytime_order(order_dv, cano, acnt_prdt_cd, ovrs_excg_cd, pdno, ord_qty, ovrs_ord_unpr, ctac_tlno, mgco_aptm_odno, ord_svr_dvsn_cd, ord_dvsn):
    """KIS overseas_stock.daytime_order 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
order_dv (str): 주문구분 buy(매수) / sell(매도)
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ovrs_excg_cd (str): NASD:나스닥 / NYSE:뉴욕 / AMEX:아멕스
pdno (str): 종목코드
ord_qty (str): 해외거래소 별 최소 주문수량 및 주문단위 확인 필요
ovrs_ord_unpr (str): 소수점 포함, 1주당 가격 * 시장가의 경우 1주당 가격을 공란으로 비우지 않음 "0"으로 입력
ctac_tlno (str): " "
mgco_aptm_odno (str): " "
ord_svr_dvsn_cd (str): "0"
ord_dvsn (str): [미국 매수/매도 주문]  00 : 지정가  * 주간거래는 지정가만 가능"""
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not ovrs_excg_cd:
        logger.error("ovrs_excg_cd is required. (e.g. 'NASD')")
        raise ValueError("ovrs_excg_cd is required. (e.g. 'NASD')")
    if not pdno:
        logger.error("pdno is required. (e.g. 'AAPL')")
        raise ValueError("pdno is required. (e.g. 'AAPL')")
    if not ord_qty:
        logger.error("ord_qty is required. (e.g. '10')")
        raise ValueError("ord_qty is required. (e.g. '10')")
    if not ovrs_ord_unpr:
        logger.error("ovrs_ord_unpr is required. (e.g. '150.00')")
        raise ValueError("ovrs_ord_unpr is required. (e.g. '150.00')")
    if not ord_svr_dvsn_cd:
        logger.error("ord_svr_dvsn_cd is required. (e.g. '0')")
        raise ValueError("ord_svr_dvsn_cd is required. (e.g. '0')")
    if not ord_dvsn:
        logger.error("ord_dvsn is required. (e.g. '00')")
        raise ValueError("ord_dvsn is required. (e.g. '00')")
    if order_dv == 'buy':
        tr_id = 'TTTS6036U'
    elif order_dv == 'sell':
        tr_id = 'TTTS6037U'
    else:
        logger.error("Invalid order_dv. (e.g. 'buy' or 'sell')")
        raise ValueError("Invalid order_dv. (e.g. 'buy' or 'sell')")
    api_url = '/uapi/overseas-stock/v1/trading/daytime-order'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'OVRS_EXCG_CD': ovrs_excg_cd, 'PDNO': pdno, 'ORD_QTY': ord_qty, 'OVRS_ORD_UNPR': ovrs_ord_unpr, 'CTAC_TLNO': ctac_tlno, 'MGCO_APTM_ODNO': mgco_aptm_odno, 'ORD_SVR_DVSN_CD': ord_svr_dvsn_cd, 'ORD_DVSN': ord_dvsn}
    return ApiRequest('overseas_stock.daytime_order', api_url, tr_id, params, 'POST' if True else 'GET', 'real', '')

def daytime_order_rvsecncl(cano, acnt_prdt_cd, ovrs_excg_cd, pdno, orgn_odno, rvse_cncl_dvsn_cd, ord_qty, ovrs_ord_unpr, ctac_tlno, mgco_aptm_odno, ord_svr_dvsn_cd):
    """KIS overseas_stock.daytime_order_rvsecncl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ovrs_excg_cd (str): NASD:나스닥 / NYSE:뉴욕 / AMEX:아멕스
pdno (str): 종목코드
orgn_odno (str): 정정 또는 취소할 원주문번호
rvse_cncl_dvsn_cd (str): 01 : 정정, 02 : 취소
ord_qty (str): 주문수량
ovrs_ord_unpr (str): 소수점 포함, 1주당 가격
ctac_tlno (str): 연락전화번호
mgco_aptm_odno (str): 운용사지정주문번호
ord_svr_dvsn_cd (str): 주문서버구분코드"""
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not ovrs_excg_cd:
        logger.error("ovrs_excg_cd is required. (e.g. 'NASD')")
        raise ValueError("ovrs_excg_cd is required. (e.g. 'NASD')")
    if not pdno:
        logger.error("pdno is required. (e.g. 'AAPL')")
        raise ValueError("pdno is required. (e.g. 'AAPL')")
    if not orgn_odno:
        logger.error("orgn_odno is required. (e.g. '1234567890')")
        raise ValueError("orgn_odno is required. (e.g. '1234567890')")
    if rvse_cncl_dvsn_cd not in ['01', '02']:
        logger.error("rvse_cncl_dvsn_cd is required. (e.g. '01' or '02')")
        raise ValueError("rvse_cncl_dvsn_cd is required. (e.g. '01' or '02')")
    if not ord_qty:
        logger.error("ord_qty is required. (e.g. '100')")
        raise ValueError("ord_qty is required. (e.g. '100')")
    if not ovrs_ord_unpr:
        logger.error("ovrs_ord_unpr is required. (e.g. '150.00')")
        raise ValueError("ovrs_ord_unpr is required. (e.g. '150.00')")
    if not ord_svr_dvsn_cd:
        logger.error("ord_svr_dvsn_cd is required. (e.g. '0')")
        raise ValueError("ord_svr_dvsn_cd is required. (e.g. '0')")
    tr_id = 'TTTS6038U'
    api_url = '/uapi/overseas-stock/v1/trading/daytime-order-rvsecncl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'OVRS_EXCG_CD': ovrs_excg_cd, 'PDNO': pdno, 'ORGN_ODNO': orgn_odno, 'RVSE_CNCL_DVSN_CD': rvse_cncl_dvsn_cd, 'ORD_QTY': ord_qty, 'OVRS_ORD_UNPR': ovrs_ord_unpr, 'CTAC_TLNO': ctac_tlno, 'MGCO_APTM_ODNO': mgco_aptm_odno, 'ORD_SVR_DVSN_CD': ord_svr_dvsn_cd}
    return ApiRequest('overseas_stock.daytime_order_rvsecncl', api_url, tr_id, params, 'POST' if True else 'GET', 'real', '')

def foreign_margin(cano, acnt_prdt_cd, tr_cont=''):
    """KIS overseas_stock.foreign_margin 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호 (필수)
acnt_prdt_cd (str): 계좌상품코드 (필수)
tr_cont (str): 연속 거래 여부 (기본값: "")"""
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    tr_id = 'TTTC2101R'
    api_url = '/uapi/overseas-stock/v1/trading/foreign-margin'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd}
    return ApiRequest('overseas_stock.foreign_margin', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_algo_ccnl(cano, acnt_prdt_cd, ord_dt='', ord_gno_brno='', odno='', ttlz_icld_yn='', NK200='', FK200='', tr_cont=''):
    """KIS overseas_stock.inquire_algo_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): [필수] 계좌번호
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 01)
ord_dt (str): 주문일자
ord_gno_brno (str): 주문채번지점번호
odno (str): 주문번호 (ex. 지정가주문번호 TTTC6058R에서 조회된 주문번호 입력)
ttlz_icld_yn (str): 집계포함여부
NK200 (str): 연속조회키200
FK200 (str): 연속조회조건200
tr_cont (str): 연속거래여부"""
    if cano == '':
        raise ValueError('cano is required')
    if acnt_prdt_cd == '':
        raise ValueError('acnt_prdt_cd is required')
    tr_id = 'TTTS6059R'
    api_url = '/uapi/overseas-stock/v1/trading/inquire-algo-ccnl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'ORD_DT': ord_dt, 'ORD_GNO_BRNO': ord_gno_brno, 'ODNO': odno, 'TTLZ_ICLD_YN': ttlz_icld_yn, 'CTX_AREA_NK200': NK200, 'CTX_AREA_FK200': FK200}
    return ApiRequest('overseas_stock.inquire_algo_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_balance(cano, acnt_prdt_cd, ovrs_excg_cd, tr_crcy_cd, FK200='', NK200='', env_dv='real', tr_cont=''):
    """KIS overseas_stock.inquire_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ovrs_excg_cd (str): [모의] NASD : 나스닥 NYSE : 뉴욕  AMEX : 아멕스  [실전] NASD : 미국전체 NAS : 나스닥 NYSE : 뉴욕  AMEX : 아멕스  [모의/실전 공통] SEHK : 홍콩 SHAA : 중국상해 SZAA : 중국심천 TKSE : 일본 HASE : 베트남 하노이 VNSE : 베트남 호치민
tr_crcy_cd (str): USD : 미국달러 HKD : 홍콩달러 CNY : 중국위안화 JPY : 일본엔화 VND : 베트남동
FK200 (str): 공란 : 최초 조회시 이전 조회 Output CTX_AREA_FK200값 : 다음페이지 조회시(2번째부터)
NK200 (str): 공란 : 최초 조회시 이전 조회 Output CTX_AREA_NK200값 : 다음페이지 조회시(2번째부터)
env_dv (str): 실전모의구분 (real:실전, demo:모의)
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '810XXXXX')")
        raise ValueError("cano is required. (e.g. '810XXXXX')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not ovrs_excg_cd:
        logger.error("ovrs_excg_cd is required. (e.g. 'NASD')")
        raise ValueError("ovrs_excg_cd is required. (e.g. 'NASD')")
    if not tr_crcy_cd:
        logger.error("tr_crcy_cd is required. (e.g. 'USD')")
        raise ValueError("tr_crcy_cd is required. (e.g. 'USD')")
    if env_dv == 'real':
        tr_id = 'TTTS3012R'
    elif env_dv == 'demo':
        tr_id = 'VTTS3012R'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/overseas-stock/v1/trading/inquire-balance'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'OVRS_EXCG_CD': ovrs_excg_cd, 'TR_CRCY_CD': tr_crcy_cd, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('overseas_stock.inquire_balance', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_ccnl(cano, acnt_prdt_cd, pdno, ord_strt_dt, ord_end_dt, sll_buy_dvsn, ccld_nccs_dvsn, sort_sqn, ord_dt, ord_gno_brno, odno, ovrs_excg_cd='', NK200='', FK200='', env_dv='real', tr_cont=''):
    """KIS overseas_stock.inquire_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
pdno (str): 전종목일 경우 "%" 입력 ※ 모의투자계좌의 경우 ""(전체 조회)만 가능
ord_strt_dt (str): YYYYMMDD 형식 (현지시각 기준)
ord_end_dt (str): YYYYMMDD 형식 (현지시각 기준)
sll_buy_dvsn (str): 00 : 전체  01 : 매도  02 : 매수 ※ 모의투자계좌의 경우 "00"(전체 조회)만 가능
ccld_nccs_dvsn (str): 00 : 전체  01 : 체결  02 : 미체결 ※ 모의투자계좌의 경우 "00"(전체 조회)만 가능
ovrs_excg_cd (str): 전종목일 경우 "%" 입력 NASD : 미국시장 전체(나스닥, 뉴욕, 아멕스) NYSE : 뉴욕 AMEX : 아멕스 SEHK : 홍콩  SHAA : 중국상해 SZAA : 중국심천 TKSE : 일본 HASE : 베트남 하노이 VNSE : 베트남 호치민 ※ 모의투자계좌의 경우 ""(전체 조회)만 가능
sort_sqn (str): DS : 정순 AS : 역순  ※ 모의투자계좌의 경우 정렬순서 사용불가(Default : DS(정순))
ord_dt (str): "" (Null 값 설정)
ord_gno_brno (str): "" (Null 값 설정)
odno (str): "" (Null 값 설정) ※ 주문번호로 검색 불가능합니다. 반드시 ""(Null 값 설정) 바랍니다.
NK200 (str): 공란 : 최초 조회시 이전 조회 Output CTX_AREA_NK200값 : 다음페이지 조회시(2번째부터)
FK200 (str): 공란 : 최초 조회시 이전 조회 Output CTX_AREA_FK200값 : 다음페이지 조회시(2번째부터)
env_dv (str): 실전모의구분 (real:실전, demo:모의)
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '810XXXXX')")
        raise ValueError("cano is required. (e.g. '810XXXXX')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not ord_strt_dt:
        logger.error("ord_strt_dt is required. (e.g. '20211027')")
        raise ValueError("ord_strt_dt is required. (e.g. '20211027')")
    if not ord_end_dt:
        logger.error("ord_end_dt is required. (e.g. '20211027')")
        raise ValueError("ord_end_dt is required. (e.g. '20211027')")
    if not sll_buy_dvsn:
        logger.error("sll_buy_dvsn is required. (e.g. '00')")
        raise ValueError("sll_buy_dvsn is required. (e.g. '00')")
    if not ccld_nccs_dvsn:
        logger.error("ccld_nccs_dvsn is required. (e.g. '00')")
        raise ValueError("ccld_nccs_dvsn is required. (e.g. '00')")
    if not sort_sqn:
        logger.error("sort_sqn is required. (e.g. 'DS')")
        raise ValueError("sort_sqn is required. (e.g. 'DS')")
    if env_dv == 'real':
        tr_id = 'TTTS3035R'
    elif env_dv == 'demo':
        tr_id = 'VTTS3035R'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/overseas-stock/v1/trading/inquire-ccnl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'ORD_STRT_DT': ord_strt_dt, 'ORD_END_DT': ord_end_dt, 'SLL_BUY_DVSN': sll_buy_dvsn, 'CCLD_NCCS_DVSN': ccld_nccs_dvsn, 'OVRS_EXCG_CD': ovrs_excg_cd, 'SORT_SQN': sort_sqn, 'ORD_DT': ord_dt, 'ORD_GNO_BRNO': ord_gno_brno, 'ODNO': odno, 'CTX_AREA_NK200': NK200, 'CTX_AREA_FK200': FK200}
    return ApiRequest('overseas_stock.inquire_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_nccs(cano, acnt_prdt_cd, ovrs_excg_cd, sort_sqn, FK200, NK200, env_dv='real', tr_cont=''):
    """KIS overseas_stock.inquire_nccs 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ovrs_excg_cd (str): NASD : 나스닥 NYSE : 뉴욕  AMEX : 아멕스 SEHK : 홍콩 SHAA : 중국상해 SZAA : 중국심천 TKSE : 일본 HASE : 베트남 하노이 VNSE : 베트남 호치민  * NASD 인 경우만 미국전체로 조회되며 나머지 거래소 코드는 해당 거래소만 조회됨 * 공백 입력 시 다음조회가 불가능하므로, 반드시 거래소코드 입력해야 함
sort_sqn (str): DS : 정순 그외 : 역순  [header tr_id: TTTS3018R] ""(공란)
FK200 (str): 공란 : 최초 조회시 이전 조회 Output CTX_AREA_FK200값 : 다음페이지 조회시(2번째부터)
NK200 (str): 공란 : 최초 조회시 이전 조회 Output CTX_AREA_NK200값 : 다음페이지 조회시(2번째부터)
env_dv (str): 실전모의구분 (real:실전, demo:모의)
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '810XXXXX')")
        raise ValueError("cano is required. (e.g. '810XXXXX')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not ovrs_excg_cd:
        logger.error("ovrs_excg_cd is required. (e.g. 'NYSE')")
        raise ValueError("ovrs_excg_cd is required. (e.g. 'NYSE')")
    if not sort_sqn:
        logger.error("sort_sqn is required. (e.g. 'DS')")
        raise ValueError("sort_sqn is required. (e.g. 'DS')")
    tr_id = 'TTTS3018R'
    api_url = '/uapi/overseas-stock/v1/trading/inquire-nccs'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'OVRS_EXCG_CD': ovrs_excg_cd, 'SORT_SQN': sort_sqn, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('overseas_stock.inquire_nccs', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_paymt_stdr_balance(cano, acnt_prdt_cd, bass_dt, wcrc_frcr_dvsn_cd, inqr_dvsn_cd, tr_cont=''):
    """KIS overseas_stock.inquire_paymt_stdr_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호
acnt_prdt_cd (str): 계좌상품코드
bass_dt (str): 기준일자
wcrc_frcr_dvsn_cd (str): 원화외화구분코드 (01: 원화기준, 02: 외화기준)
inqr_dvsn_cd (str): 조회구분코드 (00: 전체, 01: 일반, 02: 미니스탁)
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not bass_dt:
        logger.error("bass_dt is required. (e.g. '20230630')")
        raise ValueError("bass_dt is required. (e.g. '20230630')")
    if not wcrc_frcr_dvsn_cd:
        logger.error("wcrc_frcr_dvsn_cd is required. (e.g. '01')")
        raise ValueError("wcrc_frcr_dvsn_cd is required. (e.g. '01')")
    if not inqr_dvsn_cd:
        logger.error("inqr_dvsn_cd is required. (e.g. '00')")
        raise ValueError("inqr_dvsn_cd is required. (e.g. '00')")
    tr_id = 'CTRP6010R'
    api_url = '/uapi/overseas-stock/v1/trading/inquire-paymt-stdr-balance'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'BASS_DT': bass_dt, 'WCRC_FRCR_DVSN_CD': wcrc_frcr_dvsn_cd, 'INQR_DVSN_CD': inqr_dvsn_cd}
    return ApiRequest('overseas_stock.inquire_paymt_stdr_balance', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_period_profit(cano, acnt_prdt_cd, ovrs_excg_cd, natn_cd, crcy_cd, pdno, inqr_strt_dt, inqr_end_dt, wcrc_frcr_dvsn_cd, FK200, NK200, tr_cont=''):
    """KIS overseas_stock.inquire_period_profit 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ovrs_excg_cd (str): 공란 : 전체,  NASD : 미국, SEHK : 홍콩, SHAA : 중국, TKSE : 일본, HASE : 베트남
natn_cd (str): 공란(Default)
crcy_cd (str): 공란 : 전체 USD : 미국달러, HKD : 홍콩달러, CNY : 중국위안화,  JPY : 일본엔화, VND : 베트남동
pdno (str): 공란 : 전체
inqr_strt_dt (str): YYYYMMDD
inqr_end_dt (str): YYYYMMDD
wcrc_frcr_dvsn_cd (str): 01 : 외화, 02 : 원화
FK200 (str): 연속조회검색조건200
NK200 (str): 연속조회키200
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not ovrs_excg_cd:
        logger.error("ovrs_excg_cd is required. (e.g. 'NASD')")
        raise ValueError("ovrs_excg_cd is required. (e.g. 'NASD')")
    if not crcy_cd:
        logger.error("crcy_cd is required. (e.g. 'USD')")
        raise ValueError("crcy_cd is required. (e.g. 'USD')")
    if not inqr_strt_dt:
        logger.error("inqr_strt_dt is required. (e.g. '20230101')")
        raise ValueError("inqr_strt_dt is required. (e.g. '20230101')")
    if not inqr_end_dt:
        logger.error("inqr_end_dt is required. (e.g. '20231231')")
        raise ValueError("inqr_end_dt is required. (e.g. '20231231')")
    if not wcrc_frcr_dvsn_cd:
        logger.error("wcrc_frcr_dvsn_cd is required. (e.g. '01')")
        raise ValueError("wcrc_frcr_dvsn_cd is required. (e.g. '01')")
    tr_id = 'TTTS3039R'
    api_url = '/uapi/overseas-stock/v1/trading/inquire-period-profit'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'OVRS_EXCG_CD': ovrs_excg_cd, 'NATN_CD': natn_cd, 'CRCY_CD': crcy_cd, 'PDNO': pdno, 'INQR_STRT_DT': inqr_strt_dt, 'INQR_END_DT': inqr_end_dt, 'WCRC_FRCR_DVSN_CD': wcrc_frcr_dvsn_cd, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('overseas_stock.inquire_period_profit', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_period_trans(cano, acnt_prdt_cd, erlm_strt_dt, erlm_end_dt, ovrs_excg_cd, pdno, sll_buy_dvsn_cd, FK100, NK100, tr_cont=''):
    """KIS overseas_stock.inquire_period_trans 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 종합계좌번호
acnt_prdt_cd (str): 계좌상품코드
erlm_strt_dt (str): 등록시작일자 (예: 20240420)
erlm_end_dt (str): 등록종료일자 (예: 20240520)
ovrs_excg_cd (str): 해외거래소코드
pdno (str): 상품번호
sll_buy_dvsn_cd (str): 매도매수구분코드 (00: 전체, 01: 매도, 02: 매수)
FK100 (str): 연속조회검색조건100
NK100 (str): 연속조회키100
tr_cont (str): 연속 거래 여부
현금 거래만 허용한다. 대출·신용 입력은 제거했다."""
    if not cano:
        logger.error("cano is required. (e.g. '12345678')")
        raise ValueError("cano is required. (e.g. '12345678')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not erlm_strt_dt:
        logger.error("erlm_strt_dt is required. (e.g. '20240420')")
        raise ValueError("erlm_strt_dt is required. (e.g. '20240420')")
    if not erlm_end_dt:
        logger.error("erlm_end_dt is required. (e.g. '20240520')")
        raise ValueError("erlm_end_dt is required. (e.g. '20240520')")
    if not ovrs_excg_cd:
        logger.error("ovrs_excg_cd is required. (e.g. 'NAS')")
        raise ValueError("ovrs_excg_cd is required. (e.g. 'NAS')")
    if not sll_buy_dvsn_cd:
        logger.error("sll_buy_dvsn_cd is required. (e.g. '00')")
        raise ValueError("sll_buy_dvsn_cd is required. (e.g. '00')")
    tr_id = 'CTOS4001R'
    api_url = '/uapi/overseas-stock/v1/trading/inquire-period-trans'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'ERLM_STRT_DT': erlm_strt_dt, 'ERLM_END_DT': erlm_end_dt, 'OVRS_EXCG_CD': ovrs_excg_cd, 'PDNO': pdno, 'SLL_BUY_DVSN_CD': sll_buy_dvsn_cd, 'LOAN_DVSN_CD': '', 'CTX_AREA_FK100': FK100, 'CTX_AREA_NK100': NK100}
    return ApiRequest('overseas_stock.inquire_period_trans', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_present_balance(cano, acnt_prdt_cd, wcrc_frcr_dvsn_cd, natn_cd, tr_mket_cd, inqr_dvsn_cd, env_dv='real', tr_cont=''):
    """KIS overseas_stock.inquire_present_balance 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
wcrc_frcr_dvsn_cd (str): 01 : 원화  02 : 외화
natn_cd (str): 000 전체 840 미국 344 홍콩 156 중국 392 일본 704 베트남
tr_mket_cd (str): [Request body NATN_CD 000 설정] 00 : 전체  [Request body NATN_CD 840 설정] 00 : 전체 01 : 나스닥(NASD) 02 : 뉴욕거래소(NYSE) 03 : 미국(PINK SHEETS) 04 : 미국(OTCBB) 05 : 아멕스(AMEX)  [Request body NATN_CD 156 설정] 00 : 전체 01 : 상해B 02 : 심천B 03 : 상해A 04 : 심천A  [Request body NATN_CD 392 설정] 01 : 일본  [Request body NATN_CD 704 설정] 01 : 하노이거래 02 : 호치민거래소  [Request body NATN_CD 344 설정] 01 : 홍콩 02 : 홍콩CNY 03 : 홍콩USD
inqr_dvsn_cd (str): 00 : 전체  01 : 일반해외주식  02 : 미니스탁
env_dv (str): 실전모의구분 (real:실전, demo:모의)
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '810XXXXX')")
        raise ValueError("cano is required. (e.g. '810XXXXX')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not wcrc_frcr_dvsn_cd:
        logger.error("wcrc_frcr_dvsn_cd is required. (e.g. '01')")
        raise ValueError("wcrc_frcr_dvsn_cd is required. (e.g. '01')")
    if not natn_cd:
        logger.error("natn_cd is required. (e.g. '000')")
        raise ValueError("natn_cd is required. (e.g. '000')")
    if not tr_mket_cd:
        logger.error("tr_mket_cd is required. (e.g. '00')")
        raise ValueError("tr_mket_cd is required. (e.g. '00')")
    if not inqr_dvsn_cd:
        logger.error("inqr_dvsn_cd is required. (e.g. '00')")
        raise ValueError("inqr_dvsn_cd is required. (e.g. '00')")
    if env_dv == 'real':
        tr_id = 'CTRP6504R'
    elif env_dv == 'demo':
        tr_id = 'VTRP6504R'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/overseas-stock/v1/trading/inquire-present-balance'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'WCRC_FRCR_DVSN_CD': wcrc_frcr_dvsn_cd, 'NATN_CD': natn_cd, 'TR_MKET_CD': tr_mket_cd, 'INQR_DVSN_CD': inqr_dvsn_cd}
    return ApiRequest('overseas_stock.inquire_present_balance', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_psamount(cano, acnt_prdt_cd, ovrs_excg_cd, ovrs_ord_unpr, item_cd, env_dv='real', tr_cont=''):
    """KIS overseas_stock.inquire_psamount 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ovrs_excg_cd (str): NASD : 나스닥 / NYSE : 뉴욕 / AMEX : 아멕스 SEHK : 홍콩 / SHAA : 중국상해 / SZAA : 중국심천 TKSE : 일본 / HASE : 하노이거래소 / VNSE : 호치민거래소
ovrs_ord_unpr (str): 해외주문단가 (23.8) 정수부분 23자리, 소수부분 8자리
item_cd (str): 종목코드
env_dv (str): 실전모의구분 (real:실전, demo:모의)
tr_cont (str): 연속 거래 여부"""
    if not cano:
        logger.error("cano is required. (e.g. '81019777')")
        raise ValueError("cano is required. (e.g. '81019777')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not ovrs_excg_cd:
        logger.error("ovrs_excg_cd is required. (e.g. 'NASD')")
        raise ValueError("ovrs_excg_cd is required. (e.g. 'NASD')")
    if not ovrs_ord_unpr:
        logger.error("ovrs_ord_unpr is required. (e.g. '1.4')")
        raise ValueError("ovrs_ord_unpr is required. (e.g. '1.4')")
    if not item_cd:
        logger.error("item_cd is required. (e.g. 'QQQ')")
        raise ValueError("item_cd is required. (e.g. 'QQQ')")
    if env_dv == 'real':
        tr_id = 'TTTS3007R'
    elif env_dv == 'demo':
        tr_id = 'VTTS3007R'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/overseas-stock/v1/trading/inquire-psamount'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'OVRS_EXCG_CD': ovrs_excg_cd, 'OVRS_ORD_UNPR': ovrs_ord_unpr, 'ITEM_CD': item_cd}
    return ApiRequest('overseas_stock.inquire_psamount', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def market_cap(excd, vol_rang, keyb='', auth='', tr_cont=''):
    """KIS overseas_stock.market_cap 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
keyb (str): NEXT KEY BUFF (ex. "")
auth (str): 사용자권한정보 (ex. "")
tr_cont (str): 연속거래여부 (ex. "")"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄')")
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상')")
    tr_id = 'HHDFS76350100'
    api_url = '/uapi/overseas-stock/v1/ranking/market-cap'
    params = {'EXCD': excd, 'VOL_RANG': vol_rang, 'KEYB': keyb, 'AUTH': auth}
    return ApiRequest('overseas_stock.market_cap', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def new_highlow(excd, minx, vol_rang, gubn, gubn2, keyb='', auth='', tr_cont=''):
    """KIS overseas_stock.new_highlow 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
minx (str): [필수] N분전콤보값 (ex. 0:1분전, 1:2분전, 2:3분전, 3:5분전, 4:10분전, 5:15분전, 6:20분전, 7:30분전, 8:60분전, 9:120분전)
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
gubn (str): [필수] 신고/신저 구분 (ex. 0:신저,1:신고)
gubn2 (str): [필수] 일시돌파/돌파 구분 (ex. 0:일시돌파0, 1:돌파유지1)
keyb (str): NEXT KEY BUFF
auth (str): 사용자권한정보
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NYS')")
    if minx == '':
        raise ValueError("minx is required (e.g. '0')")
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0')")
    if gubn == '':
        raise ValueError("gubn is required (e.g. '1')")
    if gubn2 == '':
        raise ValueError("gubn2 is required (e.g. '1')")
    tr_id = 'HHDFS76300000'
    api_url = '/uapi/overseas-stock/v1/ranking/new-highlow'
    params = {'EXCD': excd, 'MINX': minx, 'VOL_RANG': vol_rang, 'GUBN': gubn, 'GUBN2': gubn2, 'KEYB': keyb, 'AUTH': auth}
    return ApiRequest('overseas_stock.new_highlow', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def order(cano, acnt_prdt_cd, ovrs_excg_cd, pdno, ord_qty, ovrs_ord_unpr, ord_dv, ctac_tlno, mgco_aptm_odno, ord_svr_dvsn_cd, ord_dvsn, env_dv='real'):
    """KIS overseas_stock.order 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ovrs_excg_cd (str): NASD : 나스닥 NYSE : 뉴욕 AMEX : 아멕스 SEHK : 홍콩 SHAA : 중국상해 SZAA : 중국심천 TKSE : 일본 HASE : 베트남 하노이 VNSE : 베트남 호치민
pdno (str): 종목코드
ord_qty (str): 주문수량 (해외거래소 별 최소 주문수량 및 주문단위 확인 필요)
ovrs_ord_unpr (str): 1주당 가격 * 시장가의 경우 1주당 가격을 공란으로 비우지 않음 "0"으로 입력
ord_dv (str): 주문구분 (buy: 매수, sell: 매도)
ctac_tlno (str):
mgco_aptm_odno (str):
ord_svr_dvsn_cd (str): "0"(Default)
ord_dvsn (str): [Header tr_id TTTT1002U(미국 매수 주문)] 00 : 지정가 32 : LOO(장개시지정가) 34 : LOC(장마감지정가) * 모의투자 VTTT1002U(미국 매수 주문)로는 00:지정가만 가능  [Header tr_id TTTT1006U(미국 매도 주문)] 00 : 지정가 31 : MOO(장개시시장가) 32 : LOO(장개시지정가) 33 : MOC(장마감시장가) 34 : LOC(장마감지정가) * 모의투자 VTTT1001U(미국 매도 주문)로는 00:지정가만 가능  [Header tr_id TTTS1001U(홍콩 매도 주문)] 00 : 지정가 50 : 단주지정가 * 모의투자 VTTS1001U(홍콩 매도 주문)로는 00:지정가만 가능  [그외 tr_id] 제거
env_dv (str): 실전모의구분 (real:실전, demo:모의)
미국 모의 매도 TR은 공식 인자 설명의 VTTT1001U를 적용한다. 샘플의 단순 V 치환과 다르다."""
    if not cano:
        logger.error("cano is required. (e.g. '810XXXXX')")
        raise ValueError("cano is required. (e.g. '810XXXXX')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not ovrs_excg_cd:
        logger.error("ovrs_excg_cd is required. (e.g. 'NASD')")
        raise ValueError("ovrs_excg_cd is required. (e.g. 'NASD')")
    if not pdno:
        logger.error("pdno is required. (e.g. 'AAPL')")
        raise ValueError("pdno is required. (e.g. 'AAPL')")
    if not ord_qty:
        logger.error("ord_qty is required. (e.g. '1')")
        raise ValueError("ord_qty is required. (e.g. '1')")
    if not ovrs_ord_unpr:
        logger.error("ovrs_ord_unpr is required. (e.g. '145.00')")
        raise ValueError("ovrs_ord_unpr is required. (e.g. '145.00')")
    if not ord_dv:
        logger.error("ord_dv is required. (e.g. 'buy' or 'sell')")
        raise ValueError("ord_dv is required. (e.g. 'buy' or 'sell')")
    if not ord_svr_dvsn_cd:
        logger.error("ord_svr_dvsn_cd is required. (e.g. '0')")
        raise ValueError("ord_svr_dvsn_cd is required. (e.g. '0')")
    if not ord_dvsn:
        logger.error("ord_dvsn is required. (e.g. '00')")
        raise ValueError("ord_dvsn is required. (e.g. '00')")
    if ord_dv == 'buy':
        if ovrs_excg_cd in ('NASD', 'NYSE', 'AMEX'):
            tr_id = 'TTTT1002U'
        elif ovrs_excg_cd == 'SEHK':
            tr_id = 'TTTS1002U'
        elif ovrs_excg_cd == 'SHAA':
            tr_id = 'TTTS0202U'
        elif ovrs_excg_cd == 'SZAA':
            tr_id = 'TTTS0305U'
        elif ovrs_excg_cd == 'TKSE':
            tr_id = 'TTTS0308U'
        elif ovrs_excg_cd in ('HASE', 'VNSE'):
            tr_id = 'TTTS0311U'
        else:
            logger.error("ovrs_excg_cd is required. (e.g. 'NASD', 'NYSE', 'AMEX', 'SEHK', 'SHAA', 'SZAA', 'TKSE', 'HASE', 'VNSE')")
            raise ValueError("ovrs_excg_cd is required. (e.g. 'NASD', 'NYSE', 'AMEX', 'SEHK', 'SHAA', 'SZAA', 'TKSE', 'HASE', 'VNSE')")
        sll_type = ''
    elif ord_dv == 'sell':
        if ovrs_excg_cd in ('NASD', 'NYSE', 'AMEX'):
            tr_id = 'TTTT1006U'
        elif ovrs_excg_cd == 'SEHK':
            tr_id = 'TTTS1001U'
        elif ovrs_excg_cd == 'SHAA':
            tr_id = 'TTTS1005U'
        elif ovrs_excg_cd == 'SZAA':
            tr_id = 'TTTS0304U'
        elif ovrs_excg_cd == 'TKSE':
            tr_id = 'TTTS0307U'
        elif ovrs_excg_cd in ('HASE', 'VNSE'):
            tr_id = 'TTTS0310U'
        else:
            logger.error("ovrs_excg_cd is required. (e.g. 'NASD', 'NYSE', 'AMEX', 'SEHK', 'SHAA', 'SZAA', 'TKSE', 'HASE', 'VNSE')")
            raise ValueError("ovrs_excg_cd is required. (e.g. 'NASD', 'NYSE', 'AMEX', 'SEHK', 'SHAA', 'SZAA', 'TKSE', 'HASE', 'VNSE')")
        sll_type = '00'
    else:
        logger.error("ord_dv is required. (e.g. 'buy' or 'sell')")
        raise ValueError("ord_dv is required. (e.g. 'buy' or 'sell')")
    if env_dv == 'demo':
        tr_id = 'V' + tr_id[1:]
    elif env_dv != 'real':
        logger.error("env_dv can only be 'real' or 'demo'")
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/overseas-stock/v1/trading/order'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'OVRS_EXCG_CD': ovrs_excg_cd, 'PDNO': pdno, 'ORD_QTY': ord_qty, 'OVRS_ORD_UNPR': ovrs_ord_unpr, 'CTAC_TLNO': ctac_tlno, 'MGCO_APTM_ODNO': mgco_aptm_odno, 'SLL_TYPE': sll_type, 'ORD_SVR_DVSN_CD': ord_svr_dvsn_cd, 'ORD_DVSN': ord_dvsn}
    if env_dv == 'demo' and ord_dv == 'sell' and (ovrs_excg_cd in {'NASD', 'NYSE', 'AMEX'}):
        tr_id = 'VTTT1001U'
    return ApiRequest('overseas_stock.order', api_url, tr_id, params, 'POST' if True else 'GET', env_dv, '')

def order_resv(env_dv, ord_dv, cano, acnt_prdt_cd, pdno, ovrs_excg_cd, ft_ord_qty, ft_ord_unpr3, sll_buy_dvsn_cd='', rvse_cncl_dvsn_cd='', prdt_type_cd='', ord_svr_dvsn_cd='', rsvn_ord_rcit_dt='', ord_dvsn='', ovrs_rsvn_odno='', algo_ord_tmd_dvsn_cd=''):
    """KIS overseas_stock.order_resv 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
ord_dv (str): [필수] 매도매수구분 (ex. usBuy:미국매수, usSell:미국매도, asia:아시아)
cano (str): [필수] 종합계좌번호 (ex. 12345678)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 01)
pdno (str): [필수] 상품번호
ovrs_excg_cd (str): [필수] 해외거래소코드 (ex. NASD:나스닥, NYSE:뉴욕, AMEX:아멕스, SEHK:홍콩, SHAA:상해, SZAA:심천, TKSE:일본, HASE:하노이, VNSE:호치민)
ft_ord_qty (str): [필수] FT주문수량
ft_ord_unpr3 (str): [필수] FT주문단가3
sll_buy_dvsn_cd (Optional[str]): 매도매수구분코드 (ex. 아시아인경우만 사용, 01:매도,02:매수)
rvse_cncl_dvsn_cd (Optional[str]): 정정취소구분코드 (ex. 아시아인경우만 사용, 00:매도/매수)
prdt_type_cd (Optional[str]): 상품유형코드 (ex. 아시아인경우만 사용)
ord_svr_dvsn_cd (Optional[str]): 주문서버구분코드 (ex. 0)
rsvn_ord_rcit_dt (Optional[str]): 예약주문접수일자 (ex. 아시아인경우만 사용)
ord_dvsn (Optional[str]): 주문구분 (ex. 미국 매수/매도인 경우만 사용)
ovrs_rsvn_odno (Optional[str]): 해외예약주문번호 (ex. 아이사인 경우만 사용)
algo_ord_tmd_dvsn_cd (Optional[str]): 알고리즘주문시간구분코드 (ex. TWAP, VWAP 주문에서만 사용, 02로 고정)"""
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    if ord_dv == '':
        raise ValueError("ord_dv is required (e.g. 'usBuy', 'usSell', 'asia')")
    if cano == '':
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '01')")
    if pdno == '':
        raise ValueError('pdno is required')
    if ovrs_excg_cd == '':
        raise ValueError("ovrs_excg_cd is required (e.g. 'NASD', 'NYSE', 'AMEX', 'SEHK', 'SHAA', 'SZAA', 'TKSE', 'HASE', 'VNSE')")
    if ft_ord_qty == '':
        raise ValueError('ft_ord_qty is required')
    if ft_ord_unpr3 == '':
        raise ValueError('ft_ord_unpr3 is required')
    if env_dv == 'real':
        if ord_dv == 'usBuy':
            tr_id = 'TTTT3014U'
        elif ord_dv == 'usSell':
            tr_id = 'TTTT3016U'
        elif ord_dv == 'asia':
            tr_id = 'TTTS3013U'
        else:
            raise ValueError("ord_dv can only be 'usBuy', 'usSell' or 'asia'")
    elif env_dv == 'demo':
        if ord_dv == 'usBuy':
            tr_id = 'VTTT3014U'
        elif ord_dv == 'usSell':
            tr_id = 'VTTT3016U'
        elif ord_dv == 'asia':
            tr_id = 'VTTS3013U'
        else:
            raise ValueError("ord_dv can only be 'usBuy', 'usSell' or 'asia'")
    else:
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    api_url = '/uapi/overseas-stock/v1/trading/order-resv'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'PDNO': pdno, 'OVRS_EXCG_CD': ovrs_excg_cd, 'FT_ORD_QTY': ft_ord_qty, 'FT_ORD_UNPR3': ft_ord_unpr3}
    if sll_buy_dvsn_cd:
        params['SLL_BUY_DVSN_CD'] = sll_buy_dvsn_cd
    if rvse_cncl_dvsn_cd:
        params['RVSE_CNCL_DVSN_CD'] = rvse_cncl_dvsn_cd
    if prdt_type_cd:
        params['PRDT_TYPE_CD'] = prdt_type_cd
    if ord_svr_dvsn_cd:
        params['ORD_SVR_DVSN_CD'] = ord_svr_dvsn_cd
    if rsvn_ord_rcit_dt:
        params['RSVN_ORD_RCIT_DT'] = rsvn_ord_rcit_dt
    if ord_dvsn:
        params['ORD_DVSN'] = ord_dvsn
    if ovrs_rsvn_odno:
        params['OVRS_RSVN_ODNO'] = ovrs_rsvn_odno
    if algo_ord_tmd_dvsn_cd:
        params['ALGO_ORD_TMD_DVSN_CD'] = algo_ord_tmd_dvsn_cd
    return ApiRequest('overseas_stock.order_resv', api_url, tr_id, params, 'POST' if True else 'GET', env_dv, '')

def order_resv_ccnl(env_dv, nat_dv, cano, acnt_prdt_cd, rsvn_ord_rcit_dt, ovrs_rsvn_odno):
    """KIS overseas_stock.order_resv_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
env_dv (str): [필수] 실전모의구분 (ex. real:실전, demo:모의)
nat_dv (str): [필수] 국가구분 (ex. us:미국)
cano (str): [필수] 종합계좌번호 (ex. 12345678)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 01)
rsvn_ord_rcit_dt (str): [필수] 해외주문접수일자
ovrs_rsvn_odno (str): [필수] 해외예약주문번호 (ex. 해외주식_예약주문접수 API Output ODNO(주문번호) 참고)"""
    if env_dv == '':
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    if nat_dv == '':
        raise ValueError("nat_dv is required (e.g. 'us')")
    if cano == '':
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '01')")
    if rsvn_ord_rcit_dt == '':
        raise ValueError('rsvn_ord_rcit_dt is required')
    if ovrs_rsvn_odno == '':
        raise ValueError('ovrs_rsvn_odno is required')
    if env_dv == 'real':
        if nat_dv == 'us':
            tr_id = 'TTTT3017U'
        else:
            raise ValueError("nat_dv can only be 'us'")
    elif env_dv == 'demo':
        if nat_dv == 'us':
            tr_id = 'VTTT3017U'
        else:
            raise ValueError("nat_dv can only be 'us'")
    else:
        raise ValueError("env_dv is required (e.g. 'real' or 'demo')")
    api_url = '/uapi/overseas-stock/v1/trading/order-resv-ccnl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'RSVN_ORD_RCIT_DT': rsvn_ord_rcit_dt, 'OVRS_RSVN_ODNO': ovrs_rsvn_odno}
    return ApiRequest('overseas_stock.order_resv_ccnl', api_url, tr_id, params, 'POST' if True else 'GET', env_dv, '')

def order_resv_list(nat_dv, cano, acnt_prdt_cd, inqr_strt_dt, inqr_end_dt, inqr_dvsn_cd, ovrs_excg_cd, prdt_type_cd='', FK200='', NK200='', tr_cont=''):
    """KIS overseas_stock.order_resv_list 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
nat_dv (str): [필수] 국가구분코드 (ex. us:미국, asia:아시아)
cano (str): [필수] 종합계좌번호 (ex. 12345678)
acnt_prdt_cd (str): [필수] 계좌상품코드 (ex. 01)
inqr_strt_dt (str): [필수] 조회시작일자 (ex. 20250101)
inqr_end_dt (str): [필수] 조회종료일자 (ex. 20251231)
inqr_dvsn_cd (str): [필수] 조회구분코드 (ex. 00:전체, 01:일반해외주식, 02:미니스탁)
ovrs_excg_cd (str): [필수] 해외거래소코드 (ex. NASD:나스닥, NYSE:뉴욕, AMEX:아멕스, SEHK:홍콩, SHAA:상해, SZAA:심천, TKSE:일본, HASE:하노이, VNSE:호치민)
prdt_type_cd (str): 상품유형코드
FK200 (str): 연속조회검색조건200
NK200 (str): 연속조회키200
tr_cont (str): 연속거래여부"""
    if nat_dv == '':
        raise ValueError("nat_dv is required (e.g. 'us' or 'asia')")
    if cano == '':
        raise ValueError("cano is required (e.g. '12345678')")
    if acnt_prdt_cd == '':
        raise ValueError("acnt_prdt_cd is required (e.g. '01')")
    if inqr_strt_dt == '':
        raise ValueError("inqr_strt_dt is required (e.g. '20250101')")
    if inqr_end_dt == '':
        raise ValueError("inqr_end_dt is required (e.g. '20251231')")
    if inqr_dvsn_cd == '':
        raise ValueError("inqr_dvsn_cd is required (e.g. '00')")
    if ovrs_excg_cd == '':
        raise ValueError("ovrs_excg_cd is required (e.g. 'NASD')")
    if nat_dv == 'us':
        tr_id = 'TTTT3039R'
    elif nat_dv == 'asia':
        tr_id = 'TTTS3014R'
    else:
        raise ValueError("nat_dv can only be 'us' or 'asia'")
    api_url = '/uapi/overseas-stock/v1/trading/order-resv-list'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'INQR_STRT_DT': inqr_strt_dt, 'INQR_END_DT': inqr_end_dt, 'INQR_DVSN_CD': inqr_dvsn_cd, 'OVRS_EXCG_CD': ovrs_excg_cd, 'PRDT_TYPE_CD': prdt_type_cd, 'CTX_AREA_FK200': FK200, 'CTX_AREA_NK200': NK200}
    return ApiRequest('overseas_stock.order_resv_list', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def order_rvsecncl(cano, acnt_prdt_cd, ovrs_excg_cd, pdno, orgn_odno, rvse_cncl_dvsn_cd, ord_qty, ovrs_ord_unpr, mgco_aptm_odno, ord_svr_dvsn_cd, env_dv='real'):
    """KIS overseas_stock.order_rvsecncl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
cano (str): 계좌번호 체계(8-2)의 앞 8자리
acnt_prdt_cd (str): 계좌번호 체계(8-2)의 뒤 2자리
ovrs_excg_cd (str): NASD : 나스닥  NYSE : 뉴욕  AMEX : 아멕스 SEHK : 홍콩 SHAA : 중국상해 SZAA : 중국심천 TKSE : 일본 HASE : 베트남 하노이 VNSE : 베트남 호치민
pdno (str): 상품번호
orgn_odno (str): 정정 또는 취소할 원주문번호 (해외주식_주문 API ouput ODNO  or 해외주식 미체결내역 API output ODNO 참고)
rvse_cncl_dvsn_cd (str): 01 : 정정  02 : 취소
ord_qty (str): 주문수량
ovrs_ord_unpr (str): 취소주문 시, "0" 입력
mgco_aptm_odno (str): 운용사지정주문번호
ord_svr_dvsn_cd (str): "0"(Default)
env_dv (str): 실전모의구분 (real:실전, demo:모의)"""
    if not cano:
        logger.error("cano is required. (e.g. '810XXXXX')")
        raise ValueError("cano is required. (e.g. '810XXXXX')")
    if not acnt_prdt_cd:
        logger.error("acnt_prdt_cd is required. (e.g. '01')")
        raise ValueError("acnt_prdt_cd is required. (e.g. '01')")
    if not ovrs_excg_cd:
        logger.error("ovrs_excg_cd is required. (e.g. 'NYSE')")
        raise ValueError("ovrs_excg_cd is required. (e.g. 'NYSE')")
    if not pdno:
        logger.error("pdno is required. (e.g. 'BA')")
        raise ValueError("pdno is required. (e.g. 'BA')")
    if not orgn_odno:
        logger.error("orgn_odno is required. (e.g. '30135009')")
        raise ValueError("orgn_odno is required. (e.g. '30135009')")
    if not rvse_cncl_dvsn_cd:
        logger.error("rvse_cncl_dvsn_cd is required. (e.g. '01')")
        raise ValueError("rvse_cncl_dvsn_cd is required. (e.g. '01')")
    if not ord_qty:
        logger.error("ord_qty is required. (e.g. '1')")
        raise ValueError("ord_qty is required. (e.g. '1')")
    if not ovrs_ord_unpr:
        logger.error("ovrs_ord_unpr is required. (e.g. '226.00')")
        raise ValueError("ovrs_ord_unpr is required. (e.g. '226.00')")
    if env_dv == 'real':
        tr_id = 'TTTT1004U'
    elif env_dv == 'demo':
        tr_id = 'VTTT1004U'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/overseas-stock/v1/trading/order-rvsecncl'
    params = {'CANO': cano, 'ACNT_PRDT_CD': acnt_prdt_cd, 'OVRS_EXCG_CD': ovrs_excg_cd, 'PDNO': pdno, 'ORGN_ODNO': orgn_odno, 'RVSE_CNCL_DVSN_CD': rvse_cncl_dvsn_cd, 'ORD_QTY': ord_qty, 'OVRS_ORD_UNPR': ovrs_ord_unpr, 'MGCO_APTM_ODNO': mgco_aptm_odno, 'ORD_SVR_DVSN_CD': ord_svr_dvsn_cd}
    return ApiRequest('overseas_stock.order_rvsecncl', api_url, tr_id, params, 'POST' if True else 'GET', env_dv, '')

def price_fluct(excd, gubn, minx, vol_rang, keyb='', auth='', tr_cont=''):
    """KIS overseas_stock.price_fluct 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
gubn (str): [필수] 급등/급락구분 (ex. 0:급락, 1:급등)
minx (str): [필수] N분전콤보값 (ex. 0:1분전, 1:2분전, 2:3분전, 3:5분전, 4:10분전, 5:15분전, 6:20분전, 7:30분전, 8:60분전, 9:120분전)
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
keyb (str): NEXT KEY BUFF
auth (str): 사용자권한정보
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NAS')")
    if gubn == '':
        raise ValueError("gubn is required (e.g. '0' or '1')")
    if minx == '':
        raise ValueError("minx is required (e.g. '0')")
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0')")
    tr_id = 'HHDFS76260000'
    api_url = '/uapi/overseas-stock/v1/ranking/price-fluct'
    params = {'EXCD': excd, 'GUBN': gubn, 'MINX': minx, 'VOL_RANG': vol_rang, 'KEYB': keyb, 'AUTH': auth}
    return ApiRequest('overseas_stock.price_fluct', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def trade_growth(excd, nday, vol_rang, auth='', keyb='', tr_cont=''):
    """KIS overseas_stock.trade_growth 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
nday (str): [필수] N일자값 (ex. 0:당일, 1:2일, 2:3일, 3:5일, 4:10일, 5:20일전, 6:30일, 7:60일, 8:120일, 9:1년)
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
auth (str): 사용자권한정보
keyb (str): NEXT KEY BUFF
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NYS')")
    if nday == '':
        raise ValueError("nday is required (e.g. '0')")
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0')")
    tr_id = 'HHDFS76330000'
    api_url = '/uapi/overseas-stock/v1/ranking/trade-growth'
    params = {'EXCD': excd, 'NDAY': nday, 'VOL_RANG': vol_rang, 'AUTH': auth, 'KEYB': keyb}
    return ApiRequest('overseas_stock.trade_growth', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def trade_pbmn(excd, nday, vol_rang, auth='', keyb='', prc1='', prc2='', tr_cont=''):
    """KIS overseas_stock.trade_pbmn 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
nday (str): [필수] N일자값 (ex. 0:당일, 1:2일, 2:3일, 3:5일, 4:10일, 5:20일전, 6:30일, 7:60일, 8:120일, 9:1년)
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
auth (str): 사용자권한정보
keyb (str): NEXT KEY BUFF
prc1 (str): 현재가 필터범위 시작
prc2 (str): 현재가 필터범위 끝
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄')")
    if nday == '':
        raise ValueError("nday is required (e.g. '0:당일, 1:2일, 2:3일, 3:5일, 4:10일, 5:20일전, 6:30일, 7:60일, 8:120일, 9:1년')")
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상')")
    tr_id = 'HHDFS76320010'
    api_url = '/uapi/overseas-stock/v1/ranking/trade-pbmn'
    params = {'EXCD': excd, 'NDAY': nday, 'VOL_RANG': vol_rang, 'AUTH': auth, 'KEYB': keyb, 'PRC1': prc1, 'PRC2': prc2}
    return ApiRequest('overseas_stock.trade_pbmn', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def trade_turnover(excd, nday, vol_rang, keyb='', auth='', tr_cont=''):
    """KIS overseas_stock.trade_turnover 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
nday (str): [필수] N분전콤보값 (ex. 0:당일, 1:2일전, 2:3일전, 3:5일전, 4:10일전, 5:20일전, 6:30일전, 7:60일전, 8:120일전, 9:1년전)
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
keyb (str): NEXT KEY BUFF
auth (str): 사용자권한정보
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄')")
    if nday == '':
        raise ValueError("nday is required (e.g. '0:당일, 1:2일전, 2:3일전, 3:5일전, 4:10일전, 5:20일전, 6:30일전, 7:60일전, 8:120일전, 9:1년전')")
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상')")
    tr_id = 'HHDFS76340000'
    api_url = '/uapi/overseas-stock/v1/ranking/trade-turnover'
    params = {'EXCD': excd, 'NDAY': nday, 'VOL_RANG': vol_rang, 'KEYB': keyb, 'AUTH': auth}
    return ApiRequest('overseas_stock.trade_turnover', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def trade_vol(excd, nday, vol_rang, keyb='', auth='', prc1='', prc2='', tr_cont=''):
    """KIS overseas_stock.trade_vol 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
nday (str): [필수] N분전콤보값 (ex. 0:당일, 1:2일전, 2:3일전, 3:5일전, 4:10일전, 5:20일전, 6:30일전, 7:60일전, 8:120일전, 9:1년전)
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
keyb (str): NEXT KEY BUFF (ex. "")
auth (str): 사용자권한정보 (ex. "")
prc1 (str): 가격 필터 시작 (ex. "")
prc2 (str): 가격 필터 종료 (ex. "")
tr_cont (str): 연속거래여부 (ex. "")"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄')")
    if nday == '':
        raise ValueError("nday is required (e.g. '0:당일, 1:2일전, 2:3일전, 3:5일전, 4:10일전, 5:20일전, 6:30일전, 7:60일전, 8:120일전, 9:1년전')")
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상')")
    tr_id = 'HHDFS76310010'
    api_url = '/uapi/overseas-stock/v1/ranking/trade-vol'
    params = {'EXCD': excd, 'NDAY': nday, 'VOL_RANG': vol_rang, 'KEYB': keyb, 'AUTH': auth, 'PRC1': prc1, 'PRC2': prc2}
    return ApiRequest('overseas_stock.trade_vol', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def updown_rate(excd, nday, gubn, vol_rang, auth='', keyb='', tr_cont=''):
    """KIS overseas_stock.updown_rate 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
nday (str): [필수] N일자값 (ex. 0:당일, 1:2일, 2:3일, 3:5일, 4:10일, 5:20일전, 6:30일, 7:60일, 8:120일, 9:1년)
gubn (str): [필수] 상승율/하락율 구분 (ex. 0:하락율, 1:상승율)
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
auth (str): 사용자권한정보
keyb (str): NEXT KEY BUFF
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄')")
    if nday == '':
        raise ValueError("nday is required (e.g. '0:당일, 1:2일, 2:3일, 3:5일, 4:10일, 5:20일전, 6:30일, 7:60일, 8:120일, 9:1년')")
    if gubn == '':
        raise ValueError("gubn is required (e.g. '0:하락율, 1:상승율')")
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상')")
    tr_id = 'HHDFS76290000'
    api_url = '/uapi/overseas-stock/v1/ranking/updown-rate'
    params = {'EXCD': excd, 'NDAY': nday, 'GUBN': gubn, 'VOL_RANG': vol_rang, 'AUTH': auth, 'KEYB': keyb}
    return ApiRequest('overseas_stock.updown_rate', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def volume_power(excd, nday, vol_rang, auth='', keyb='', tr_cont=''):
    """KIS overseas_stock.volume_power 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
nday (str): [필수] N일자값 (ex. 0:당일, 1:2일, 2:3일, 3:5일, 4:10일, 5:20일전, 6:30일, 7:60일, 8:120일, 9:1년)
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
auth (str): 사용자권한정보
keyb (str): NEXT KEY BUFF
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'HKS')")
    if nday == '':
        raise ValueError("nday is required (e.g. '0')")
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0')")
    tr_id = 'HHDFS76280000'
    api_url = '/uapi/overseas-stock/v1/ranking/volume-power'
    params = {'EXCD': excd, 'NDAY': nday, 'VOL_RANG': vol_rang, 'AUTH': auth, 'KEYB': keyb}
    return ApiRequest('overseas_stock.volume_power', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def volume_surge(excd, minx, vol_rang, keyb='', auth='', tr_cont=''):
    """KIS overseas_stock.volume_surge 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
minx (str): [필수] N분전콤보값 (ex. 0:1분전, 1:2분전, 2:3분전, 3:5분전, 4:10분전, 5:15분전, 6:20분전, 7:30분전, 8:60분전, 9:120분전)
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
keyb (str): NEXT KEY BUFF
auth (str): 사용자권한정보
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NYS')")
    if minx == '':
        raise ValueError("minx is required (e.g. '0')")
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0')")
    tr_id = 'HHDFS76270000'
    api_url = '/uapi/overseas-stock/v1/ranking/volume-surge'
    params = {'EXCD': excd, 'MINX': minx, 'VOL_RANG': vol_rang, 'KEYB': keyb, 'AUTH': auth}
    return ApiRequest('overseas_stock.volume_surge', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def brknews_title(fid_news_ofer_entp_code, fid_cond_scr_div_code, fid_cond_mrkt_cls_code='', fid_input_iscd='', fid_titl_cntt='', fid_input_date_1='', fid_input_hour_1='', fid_rank_sort_cls_code='', fid_input_srno=''):
    """KIS overseas_stock.brknews_title 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_news_ofer_entp_code (str): [필수] 뉴스제공업체코드 (ex. 0:전체조회)
fid_cond_scr_div_code (str): [필수] 조건화면분류코드 (ex. 11801)
fid_cond_mrkt_cls_code (str): 조건시장구분코드
fid_input_iscd (str): 입력종목코드
fid_titl_cntt (str): 제목내용
fid_input_date_1 (str): 입력날짜1
fid_input_hour_1 (str): 입력시간1
fid_rank_sort_cls_code (str): 순위정렬구분코드
fid_input_srno (str): 입력일련번호"""
    if fid_news_ofer_entp_code == '':
        raise ValueError("fid_news_ofer_entp_code is required (e.g. '0')")
    if fid_cond_scr_div_code == '':
        raise ValueError("fid_cond_scr_div_code is required (e.g. '11801')")
    tr_id = 'FHKST01011801'
    api_url = '/uapi/overseas-price/v1/quotations/brknews-title'
    params = {'FID_NEWS_OFER_ENTP_CODE': fid_news_ofer_entp_code, 'FID_COND_SCR_DIV_CODE': fid_cond_scr_div_code, 'FID_COND_MRKT_CLS_CODE': fid_cond_mrkt_cls_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_TITL_CNTT': fid_titl_cntt, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_HOUR_1': fid_input_hour_1, 'FID_RANK_SORT_CLS_CODE': fid_rank_sort_cls_code, 'FID_INPUT_SRNO': fid_input_srno}
    return ApiRequest('overseas_stock.brknews_title', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def countries_holiday(trad_dt, NK='', FK='', tr_cont=''):
    """KIS overseas_stock.countries_holiday 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
trad_dt (str): 기준일자(YYYYMMDD)
ctx_area_nk (str): 공백으로 입력
ctx_area_fk (str): 공백으로 입력
tr_cont (str): 연속 거래 여부"""
    if not trad_dt:
        logger.error("trad_dt is required. (e.g. '20250131')")
        raise ValueError("trad_dt is required. (e.g. '20250131')")
    tr_id = 'CTOS5011R'
    api_url = '/uapi/overseas-stock/v1/quotations/countries-holiday'
    params = {'TRAD_DT': trad_dt, 'CTX_AREA_NK': NK, 'CTX_AREA_FK': FK}
    return ApiRequest('overseas_stock.countries_holiday', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def dailyprice(auth, excd, symb, gubn, bymd, modp, env_dv='real', tr_cont=''):
    """KIS overseas_stock.dailyprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
auth (str): 사용자권한정보 (예: "")
excd (str): 거래소코드 (예: "NAS")
symb (str): 종목코드 (예: "TSLA")
gubn (str): 일/주/월구분 (예: "0")
bymd (str): 조회기준일자(YYYYMMDD) (예: "20230101")
modp (str): 수정주가반영여부 (예: "0")
env_dv (str): 실전모의구분 (real:실전, demo:모의)
tr_cont (str): 연속 거래 여부"""
    logger = logging.getLogger(__name__)
    if not excd:
        logger.error("excd is required. (e.g. 'NAS')")
        raise ValueError("excd is required. (e.g. 'NAS')")
    if not symb:
        logger.error("symb is required. (e.g. 'TSLA')")
        raise ValueError("symb is required. (e.g. 'TSLA')")
    if not gubn:
        logger.error("gubn is required. (e.g. '0')")
        raise ValueError("gubn is required. (e.g. '0')")
    if not modp:
        logger.error("modp is required. (e.g. '0')")
        raise ValueError("modp is required. (e.g. '0')")
    if env_dv == 'real' or env_dv == 'demo':
        tr_id = 'HHDFS76240000'
    else:
        logger.error("env_dv can only be 'real' or 'demo'")
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/overseas-price/v1/quotations/dailyprice'
    params = {'AUTH': auth, 'EXCD': excd, 'SYMB': symb, 'GUBN': gubn, 'BYMD': bymd, 'MODP': modp}
    return ApiRequest('overseas_stock.dailyprice', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def industry_price(excd, auth='', tr_cont=''):
    """KIS overseas_stock.industry_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
auth (str): 사용자권한정보
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NYS', 'NAS', 'AMS', 'HKS', 'SHS', 'SZS', 'HSX', 'HNX', 'TSE')")
    tr_id = 'HHDFS76370100'
    api_url = '/uapi/overseas-price/v1/quotations/industry-price'
    params = {'EXCD': excd, 'AUTH': auth}
    return ApiRequest('overseas_stock.industry_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def industry_theme(excd, icod, vol_rang, auth='', keyb='', tr_cont=''):
    """KIS overseas_stock.industry_theme 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
icod (str): [필수] 업종코드
vol_rang (str): [필수] 거래량조건 (ex. 0:전체, 1:1백주이상, 2:1천주이상, 3:1만주이상, 4:10만주이상, 5:100만주이상, 6:1000만주이상)
auth (str): 사용자권한정보
keyb (str): NEXT KEY BUFF
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NAS')")
    if icod == '':
        raise ValueError('icod is required')
    if vol_rang == '':
        raise ValueError("vol_rang is required (e.g. '0')")
    tr_id = 'HHDFS76370000'
    api_url = '/uapi/overseas-price/v1/quotations/industry-theme'
    params = {'EXCD': excd, 'ICOD': icod, 'VOL_RANG': vol_rang, 'AUTH': auth, 'KEYB': keyb}
    return ApiRequest('overseas_stock.industry_theme', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_asking_price(auth, excd, symb, tr_cont=''):
    """KIS overseas_stock.inquire_asking_price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
auth (str): 사용자권한정보
excd (str): 거래소코드 (예: NYS, NAS, AMS, 등)
symb (str): 종목코드 (예: TSLA)
tr_cont (str): 연속 거래 여부"""
    if not excd:
        logger.error("excd is required. (e.g. 'NAS')")
        raise ValueError("excd is required. (e.g. 'NAS')")
    if not symb:
        logger.error("symb is required. (e.g. 'TSLA')")
        raise ValueError("symb is required. (e.g. 'TSLA')")
    tr_id = 'HHDFS76200100'
    api_url = '/uapi/overseas-price/v1/quotations/inquire-asking-price'
    params = {'AUTH': auth, 'EXCD': excd, 'SYMB': symb}
    return ApiRequest('overseas_stock.inquire_asking_price', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def quot_inquire_ccnl(excd, tday, symb, auth='', keyb='', tr_cont=''):
    """KIS overseas_stock.quot_inquire_ccnl 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
excd (str): [필수] 거래소명 (ex. NYS:뉴욕, NAS:나스닥, AMS:아멕스, HKS:홍콩, SHS:상해, SZS:심천, HSX:호치민, HNX:하노이, TSE:도쿄)
tday (str): [필수] 당일전일구분 (ex. 0:전일, 1:당일)
symb (str): [필수] 종목코드 (ex. 해외종목코드)
auth (str): 사용자권한정보
keyb (str): NEXT KEY BUFF
tr_cont (str): 연속거래여부"""
    if excd == '':
        raise ValueError("excd is required (e.g. 'NAS')")
    if tday == '':
        raise ValueError("tday is required (e.g. '0' or '1')")
    if symb == '':
        raise ValueError("symb is required (e.g. 'TSLA')")
    tr_id = 'HHDFS76200300'
    api_url = '/uapi/overseas-price/v1/quotations/inquire-ccnl'
    params = {'EXCD': excd, 'TDAY': tday, 'SYMB': symb, 'AUTH': auth, 'KEYB': keyb}
    return ApiRequest('overseas_stock.quot_inquire_ccnl', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_daily_chartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2, fid_period_div_code, env_dv='real', tr_cont=''):
    """KIS overseas_stock.inquire_daily_chartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): N: 해외지수, X 환율, I: 국채, S:금선물
fid_input_iscd (str): 종목코드 ※ 해외주식 마스터 코드 참조  (포럼 > FAQ > 종목정보 다운로드(해외) > 해외지수)  ※ 해당 API로 미국주식 조회 시, 다우30, 나스닥100, S&P500 종목만 조회 가능합니다. 더 많은 미국주식 종목 시세를 이용할 시에는, 해외주식기간별시세 API 사용 부탁드립니다.
fid_input_date_1 (str): 시작일자(YYYYMMDD)
fid_input_date_2 (str): 종료일자(YYYYMMDD)
fid_period_div_code (str): D:일, W:주, M:월, Y:년
env_dv (str): 실전모의구분 (real:실전, demo:모의)
tr_cont (str): 연속 거래 여부"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'N')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'N')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. '.DJI')")
        raise ValueError("fid_input_iscd is required. (e.g. '.DJI')")
    if not fid_input_date_1:
        logger.error("fid_input_date_1 is required. (e.g. '20220401')")
        raise ValueError("fid_input_date_1 is required. (e.g. '20220401')")
    if not fid_input_date_2:
        logger.error("fid_input_date_2 is required. (e.g. '20220613')")
        raise ValueError("fid_input_date_2 is required. (e.g. '20220613')")
    if not fid_period_div_code:
        logger.error("fid_period_div_code is required. (e.g. 'D')")
        raise ValueError("fid_period_div_code is required. (e.g. 'D')")
    if env_dv == 'real' or env_dv == 'demo':
        tr_id = 'FHKST03030100'
    else:
        raise ValueError("env_dv can only be 'real' or 'demo'")
    api_url = '/uapi/overseas-price/v1/quotations/inquire-daily-chartprice'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_INPUT_DATE_1': fid_input_date_1, 'FID_INPUT_DATE_2': fid_input_date_2, 'FID_PERIOD_DIV_CODE': fid_period_div_code}
    return ApiRequest('overseas_stock.inquire_daily_chartprice', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def inquire_search(auth, excd, co_yn_pricecur, co_st_pricecur, co_en_pricecur, co_yn_rate, co_st_rate, co_en_rate, co_yn_valx, co_st_valx, co_en_valx, co_yn_shar, co_st_shar, co_en_shar, co_yn_volume, co_st_volume, co_en_volume, co_yn_amt, co_st_amt, co_en_amt, co_yn_eps, co_st_eps, co_en_eps, co_yn_per, co_st_per, co_en_per, keyb, tr_cont=''):
    """KIS overseas_stock.inquire_search 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
auth (str): "" (Null 값 설정)
excd (str): NYS : 뉴욕, NAS : 나스닥,  AMS : 아멕스  HKS : 홍콩, SHS : 상해 , SZS : 심천 HSX : 호치민, HNX : 하노이 TSE : 도쿄
co_yn_pricecur (str): 해당조건 사용시(1), 미사용시 필수항목아님
co_st_pricecur (str): 단위: 각국통화(JPY, USD, HKD, CNY, VND)
co_en_pricecur (str): 단위: 각국통화(JPY, USD, HKD, CNY, VND)
co_yn_rate (str): 해당조건 사용시(1), 미사용시 필수항목아님
co_st_rate (str): %
co_en_rate (str): %
co_yn_valx (str): 해당조건 사용시(1), 미사용시 필수항목아님
co_st_valx (str): 단위: 천
co_en_valx (str): 단위: 천
co_yn_shar (str): 해당조건 사용시(1), 미사용시 필수항목아님
co_st_shar (str): 단위: 천
co_en_shar (str): 단위: 천
co_yn_volume (str): 해당조건 사용시(1), 미사용시 필수항목아님
co_st_volume (str): 단위: 주
co_en_volume (str): 단위: 주
co_yn_amt (str): 해당조건 사용시(1), 미사용시 필수항목아님
co_st_amt (str): 단위: 천
co_en_amt (str): 단위: 천
co_yn_eps (str): 해당조건 사용시(1), 미사용시 필수항목아님
co_st_eps (str):
co_en_eps (str):
co_yn_per (str): 해당조건 사용시(1), 미사용시 필수항목아님
co_st_per (str):
co_en_per (str):
keyb (str): "" 공백 입력
tr_cont (str): 연속 거래 여부"""
    if not excd:
        logger.error("excd is required. (e.g. 'NAS')")
        raise ValueError("excd is required. (e.g. 'NAS')")
    tr_id = 'HHDFS76410000'
    api_url = '/uapi/overseas-price/v1/quotations/inquire-search'
    params = {'AUTH': auth, 'EXCD': excd, 'CO_YN_PRICECUR': co_yn_pricecur, 'CO_ST_PRICECUR': co_st_pricecur, 'CO_EN_PRICECUR': co_en_pricecur, 'CO_YN_RATE': co_yn_rate, 'CO_ST_RATE': co_st_rate, 'CO_EN_RATE': co_en_rate, 'CO_YN_VALX': co_yn_valx, 'CO_ST_VALX': co_st_valx, 'CO_EN_VALX': co_en_valx, 'CO_YN_SHAR': co_yn_shar, 'CO_ST_SHAR': co_st_shar, 'CO_EN_SHAR': co_en_shar, 'CO_YN_VOLUME': co_yn_volume, 'CO_ST_VOLUME': co_st_volume, 'CO_EN_VOLUME': co_en_volume, 'CO_YN_AMT': co_yn_amt, 'CO_ST_AMT': co_st_amt, 'CO_EN_AMT': co_en_amt, 'CO_YN_EPS': co_yn_eps, 'CO_ST_EPS': co_st_eps, 'CO_EN_EPS': co_en_eps, 'CO_YN_PER': co_yn_per, 'CO_ST_PER': co_st_per, 'CO_EN_PER': co_en_per, 'KEYB': keyb}
    return ApiRequest('overseas_stock.inquire_search', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_time_indexchartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code, fid_pw_data_incu_yn, tr_cont=''):
    """KIS overseas_stock.inquire_time_indexchartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
fid_cond_mrkt_div_code (str): N 해외지수 X 환율 KX 원화환율
fid_input_iscd (str): 종목번호(ex. TSLA)
fid_hour_cls_code (str): 0: 정규장, 1: 시간외
fid_pw_data_incu_yn (str): Y/N
tr_cont (str): 연속 거래 여부"""
    if not fid_cond_mrkt_div_code:
        logger.error("fid_cond_mrkt_div_code is required. (e.g. 'N')")
        raise ValueError("fid_cond_mrkt_div_code is required. (e.g. 'N')")
    if not fid_input_iscd:
        logger.error("fid_input_iscd is required. (e.g. 'SPX')")
        raise ValueError("fid_input_iscd is required. (e.g. 'SPX')")
    if not fid_hour_cls_code:
        logger.error("fid_hour_cls_code is required. (e.g. '0')")
        raise ValueError("fid_hour_cls_code is required. (e.g. '0')")
    if not fid_pw_data_incu_yn:
        logger.error("fid_pw_data_incu_yn is required. (e.g. 'Y')")
        raise ValueError("fid_pw_data_incu_yn is required. (e.g. 'Y')")
    tr_id = 'FHKST03030200'
    api_url = '/uapi/overseas-price/v1/quotations/inquire-time-indexchartprice'
    params = {'FID_COND_MRKT_DIV_CODE': fid_cond_mrkt_div_code, 'FID_INPUT_ISCD': fid_input_iscd, 'FID_HOUR_CLS_CODE': fid_hour_cls_code, 'FID_PW_DATA_INCU_YN': fid_pw_data_incu_yn}
    return ApiRequest('overseas_stock.inquire_time_indexchartprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def inquire_time_itemchartprice(auth, excd, symb, nmin, pinc, next, nrec, fill, keyb, tr_cont=''):
    """KIS overseas_stock.inquire_time_itemchartprice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
auth (str): "" 공백으로 입력
excd (str): NYS : 뉴욕 NAS : 나스닥 AMS : 아멕스  HKS : 홍콩 SHS : 상해  SZS : 심천 HSX : 호치민 HNX : 하노이 TSE : 도쿄   ※ 주간거래는 최대 1일치 분봉만 조회 가능 BAY : 뉴욕(주간) BAQ : 나스닥(주간) BAA : 아멕스(주간)
symb (str): 종목코드(ex. TSLA)
nmin (str): 분단위(1: 1분봉, 2: 2분봉, ...)
pinc (str): 0:당일 1:전일포함 ※ 다음조회 시 반드시 "1"로 입력
next (str): 처음조회 시, "" 공백 입력 다음조회 시, "1" 입력
nrec (str): 레코드요청갯수 (최대 120)
fill (str): "" 공백으로 입력
keyb (str): 처음 조회 시, "" 공백 입력 다음 조회 시, 이전 조회 결과의 마지막 분봉 데이터를 이용하여, 1분 전 혹은 n분 전의 시간을 입력  (형식: YYYYMMDDHHMMSS, ex. 20241014140100)
tr_cont (str): 연속 거래 여부"""
    if not excd:
        logger.error("excd is required. (e.g. 'NAS')")
        raise ValueError("excd is required. (e.g. 'NAS')")
    if not symb:
        logger.error("symb is required. (e.g. 'TSLA')")
        raise ValueError("symb is required. (e.g. 'TSLA')")
    if not nmin:
        logger.error("nmin is required. (e.g. '5')")
        raise ValueError("nmin is required. (e.g. '5')")
    if not pinc:
        logger.error("pinc is required. (e.g. '1')")
        raise ValueError("pinc is required. (e.g. '1')")
    if not nrec or int(nrec) > 120:
        logger.error("nrec is required. (e.g. '120', 최대120개)")
        raise ValueError("nrec is required. (e.g. '120', 최대120개)")
    tr_id = 'HHDFS76950200'
    api_url = '/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice'
    params = {'AUTH': auth, 'EXCD': excd, 'SYMB': symb, 'NMIN': nmin, 'PINC': pinc, 'NEXT': next, 'NREC': nrec, 'FILL': fill, 'KEYB': keyb}
    return ApiRequest('overseas_stock.inquire_time_itemchartprice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def news_title(info_gb='', class_cd='', nation_cd='', exchange_cd='', symb='', data_dt='', data_tm='', cts='', tr_cont=''):
    """KIS overseas_stock.news_title 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
info_gb (str): [필수] 뉴스구분
class_cd (str): [필수] 중분류
nation_cd (str): [필수] 국가코드 (ex. 공백:전체, CN:중국, HK:홍콩, US:미국)
exchange_cd (str): [필수] 거래소코드
symb (str): [필수] 종목코드
data_dt (str): [필수] 조회일자
data_tm (str): [필수] 조회시간
cts (str): [필수] 다음키
tr_cont (str): [필수] 연속거래여부"""
    tr_id = 'HHPSTH60100C1'
    api_url = '/uapi/overseas-price/v1/quotations/news-title'
    params = {'INFO_GB': info_gb, 'CLASS_CD': class_cd, 'NATION_CD': nation_cd, 'EXCHANGE_CD': exchange_cd, 'SYMB': symb, 'DATA_DT': data_dt, 'DATA_TM': data_tm, 'CTS': cts}
    return ApiRequest('overseas_stock.news_title', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def period_rights(rght_type_cd, inqr_dvsn_cd, inqr_strt_dt, inqr_end_dt, pdno='', prdt_type_cd='', NK50='', FK50='', tr_cont=''):
    """KIS overseas_stock.period_rights 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
rght_type_cd (str): [필수] 권리유형코드 (%%:전체, 01:유상, 02:무상, 03:배당, 11:합병,14:액면분할, 15:액면병합, 17:감자, 54:WR청구,61:원리금상환, 71:WR소멸, 74:배당옵션, 75:특별배당, 76:ISINCODE변경, 77:실권주청약)
inqr_dvsn_cd (str): [필수] 조회구분코드 (02:현지기준일, 03:청약시작일, 04:청약종료일)
inqr_strt_dt (str): [필수] 조회시작일자 (20250101)
inqr_end_dt (str): [필수] 조회종료일자 (20250131)
pdno (str): 상품번호
prdt_type_cd (str): 상품유형코드
NK50 (str): 연속조회키50
FK50 (str): 연속조회검색조건50
tr_cont (str): 연속거래여부"""
    if rght_type_cd == '':
        raise ValueError("rght_type_cd is required (e.g. '%%:전체, 01:유상, 02:무상, 03:배당, 11:합병,14:액면분할, 15:액면병합, 17:감자, 54:WR청구,61:원리금상환, 71:WR소멸, 74:배당옵션, 75:특별배당, 76:ISINCODE변경, 77:실권주청약')")
    if inqr_dvsn_cd == '':
        raise ValueError("inqr_dvsn_cd is required (e.g. '02:현지기준일, 03:청약시작일, 04:청약종료일')")
    if inqr_strt_dt == '':
        raise ValueError("inqr_strt_dt is required (e.g. '20250101')")
    if inqr_end_dt == '':
        raise ValueError("inqr_end_dt is required (e.g. '20250131')")
    tr_id = 'CTRGT011R'
    api_url = '/uapi/overseas-price/v1/quotations/period-rights'
    params = {'RGHT_TYPE_CD': rght_type_cd, 'INQR_DVSN_CD': inqr_dvsn_cd, 'INQR_STRT_DT': inqr_strt_dt, 'INQR_END_DT': inqr_end_dt, 'PDNO': pdno, 'PRDT_TYPE_CD': prdt_type_cd, 'CTX_AREA_NK50': NK50, 'CTX_AREA_FK50': FK50}
    return ApiRequest('overseas_stock.period_rights', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def price(auth, excd, symb, env_dv='real', tr_cont=''):
    """KIS overseas_stock.price 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
auth (str): 사용자권한정보
excd (str): 거래소코드 (예: "NAS")
symb (str): 종목코드 (예: "AAPL")
env_dv (str): 실전모의구분 (real:실전, demo:모의)
tr_cont (str): 연속 거래 여부"""
    logger = logging.getLogger(__name__)
    if not excd:
        logger.error("excd is required. (e.g. 'NAS')")
        raise ValueError("excd is required. (e.g. 'NAS')")
    if not symb:
        logger.error("symb is required. (e.g. 'AAPL')")
        raise ValueError("symb is required. (e.g. 'AAPL')")
    if env_dv == 'real' or env_dv == 'demo':
        tr_id = 'HHDFS00000300'
    else:
        logger.error("Invalid env_dv value: %s. Must be 'real' or 'demo'.", env_dv)
        raise ValueError("env_dv must be 'real' or 'demo'")
    api_url = '/uapi/overseas-price/v1/quotations/price'
    params = {'AUTH': auth, 'EXCD': excd, 'SYMB': symb}
    return ApiRequest('overseas_stock.price', api_url, tr_id, params, 'POST' if False else 'GET', env_dv, tr_cont)

def price_detail(auth, excd, symb, tr_cont=''):
    """KIS overseas_stock.price_detail 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
auth (str): 사용자권한정보
excd (str): 거래소명 (예: HKS, NYS, NAS, AMS, TSE, SHS, SZS, SHI, SZI, HSX, HNX, BAY, BAQ, BAA)
symb (str): 종목코드
tr_cont (str): 연속 거래 여부"""
    if not excd:
        logger.error("excd is required. (e.g. 'NAS')")
        raise ValueError("excd is required. (e.g. 'NAS')")
    if not symb:
        logger.error("symb is required. (e.g. 'TSLA')")
        raise ValueError("symb is required. (e.g. 'TSLA')")
    tr_id = 'HHDFS76200200'
    api_url = '/uapi/overseas-price/v1/quotations/price-detail'
    params = {'AUTH': auth, 'EXCD': excd, 'SYMB': symb}
    return ApiRequest('overseas_stock.price_detail', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def rights_by_ice(ncod, symb, st_ymd='', ed_ymd=''):
    """KIS overseas_stock.rights_by_ice 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
ncod (str): [필수] 국가코드 (ex. CN:중국,HK:홍콩,US:미국,JP:일본,VN:베트남)
symb (str): [필수] 종목코드
st_ymd (str): 일자시작일 (ex. 미입력시 3개월전)
ed_ymd (str): 일자종료일 (ex. 미입력시 3개월후)"""
    if ncod == '':
        raise ValueError("ncod is required (e.g. 'CN:중국,HK:홍콩,US:미국,JP:일본,VN:베트남')")
    if symb == '':
        raise ValueError('symb is required')
    tr_id = 'HHDFS78330900'
    api_url = '/uapi/overseas-price/v1/quotations/rights-by-ice'
    params = {'NCOD': ncod, 'SYMB': symb, 'ST_YMD': st_ymd, 'ED_YMD': ed_ymd}
    return ApiRequest('overseas_stock.rights_by_ice', api_url, tr_id, params, 'POST' if False else 'GET', 'real', '')

def search_info(prdt_type_cd, pdno, tr_cont=''):
    """KIS overseas_stock.search_info 요청을 만든다. 네트워크 전송은 하지 않는다.

입력 설명은 공식 예제의 계약을 따른다. 거래소·종목·계좌 값은 호출자가 명시한다.
prdt_type_cd (str): 512  미국 나스닥 / 513  미국 뉴욕 / 529  미국 아멕스  515  일본 501  홍콩 / 543  홍콩CNY / 558  홍콩USD 507  베트남 하노이 / 508  베트남 호치민 551  중국 상해A / 552  중국 심천A
pdno (str): 예) AAPL (애플)
tr_cont (str): 연속 거래 여부"""
    if not prdt_type_cd:
        logger.error("prdt_type_cd is required. (e.g. '512')")
        raise ValueError("prdt_type_cd is required. (e.g. '512')")
    if not pdno:
        logger.error("pdno is required. (e.g. 'AAPL')")
        raise ValueError("pdno is required. (e.g. 'AAPL')")
    tr_id = 'CTPF1702R'
    api_url = '/uapi/overseas-price/v1/quotations/search-info'
    params = {'PRDT_TYPE_CD': prdt_type_cd, 'PDNO': pdno}
    return ApiRequest('overseas_stock.search_info', api_url, tr_id, params, 'POST' if False else 'GET', 'real', tr_cont)

def multprice(symbols):
    """해외 복수종목 시세. symbols는 [(거래소, 티커)] 목록이며 한 번에 1~10개다.

    시세 거래소 NAS/NYS/AMS와 주문 거래소 NASD/NYSE/AMEX는 서로 다르다.
    """
    if not isinstance(symbols, (list, tuple)) or not 1 <= len(symbols) <= 10:
        raise ValueError('복수 시세는 1~10종목을 지정하세요.')
    parameters = {'AUTH': '', 'NREC': str(len(symbols))}
    for index, item in enumerate(symbols, 1):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError('각 종목은 (거래소, 티커) 형식이어야 합니다.')
        exchange, symbol = item
        if exchange not in {'HKS', 'NYS', 'NAS', 'AMS', 'TSE', 'SHS', 'SZS', 'SHI', 'SZI', 'HSX', 'HNX', 'BAY', 'BAQ', 'BAA'} or not isinstance(symbol, str) or (not symbol.strip()):
            raise ValueError('지원 거래소·종목코드를 확인하세요.')
        parameters[f'EXCD_{index:02d}'] = exchange
        parameters[f'SYMB_{index:02d}'] = symbol
    return ApiRequest('overseas_stock.multprice', '/uapi/overseas-price/v1/quotations/multprice', 'HHDFS76220000', parameters)
