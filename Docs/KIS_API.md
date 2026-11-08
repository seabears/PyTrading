> 2026-10-27 전송 정책 변경: 요청 명세는 보존하지만 실계좌 및 원장 없는 직접 주문은 차단합니다. allow_trading=True만으로 주문할 수 없습니다. 현재 동작은 [주문 실행 문서](ORDER_EXECUTION.md)를 우선합니다.

# 현재 허용 상품: 주식·채권·ETF만

ETN을 포함해 그 외 상품은 사용 불허다. 선물·옵션·ELW 구현은 보존하고 전송·구독을 차단한다.
ETF와 ETN은 API를 공유하므로 API 함수 수는 변하지 않는다. 허용 API 219개도 허용 상품에만 사용할 수 있다.
공용 시세·주문·복수종목·실시간 구독과 기존 KIS 수집 경로에서 종목의 상품 종류를 검사한다.
현재 주식 30종목과 기존 주식·ETF 비교 종목은 등록했다. 새 주식·채권·ETF는 실제 종류 확인 후
Config/product-policy.json의 verified_instruments에 등록해야 한다. 미확인 종목은 차단한다.
현재 채권 개별 종목은 등록되지 않았으며, 등록 전에는 개별 채권 조회·주문이 차단된다.
일반 계좌·시장 통계 조회는 유지한다. 대출 삭제·현금 거래 제한·실주문 기본 차단도 유지한다.

# 선물·옵션·ELW 사용 불허

선물·옵션·ELW 구현은 삭제하지 않고 보존한다. 해당 상품의 REST 조회·주문과 실시간 구독은 불허한다.
국내주식 모듈에 포함된 ELW 시세 함수도 같은 제한을 적용한다.
전체 구현 323개 중 **허용 219개(REST 183개·실시간 36개), 불허 104개**다.
`allow_trading=True`로도 상품 불허를 해제할 수 없다. 요청 생성·합성 계약 검사는 계속 가능하다.
현재 상태는 [허용 여부가 표시된 전체 목록](KIS_API_CATALOG.md)과 Config/kis-api-catalog.json의 enabled에서 확인한다.
대출 전용 8개 API의 삭제와 현금 거래 제한은 그대로 유지한다.

# 대출 기능 제외 방침

사용자 요청으로 대출·신용융자·주식담보대출·대주 관련 8개 API를 삭제했다.
현재 구현 상품 함수는 323개(REST 260개, 실시간 63개)다.
예약주문은 현금 잔고 구분 10만 허용하고 대출일자·대여일자 입력은 제거했다.
현금주문의 대차매도(SLL_TYPE=05), 비어 있지 않은 LOAN_/CRDT_ 입력은 요청 생성·전송 전에 차단한다.
allow_trading=True를 설정해도 대출 제한은 해제되지 않는다.
정상 현금 매매·잔고·매수 가능 금액·증거금 조회는 유지한다.
공식 원본 명세와 이전 검증 보고서는 감사·비교 자료로 보존하며 실행 모듈로 사용하지 않는다.
Code/broker/kis_api/policy.py와 Test/broker/test_no_borrowing.py에서 제한과 검사를 확인할 수 있다.

아래 구현 이력의 338개 전체 목록 중 위 8개는 현재 사용 대상에서 제외됐다.

# KIS API 사용·수정 위치

Code/broker/kis_api에 공식 예제 332개와 포털 보완 6개를 합친 338개 요청 함수와 공통 전송부를 구현했다.
국내주식·해외주식·국내/해외선물옵션·장내채권·ELW·ETF/ETN을 포함한다.
이는 Config/kis-api-catalog.json에 기록한 공식 커밋의 예제 범위다.
공식 포털의 모든 신규 API·모든 계좌 권한까지 실접속 검증했다는 뜻은 아니다.
[함수 전체 목록·공식 근거](KIS_API_CATALOG.md).

## 실행 확인

프로젝트 루트의 CMD에서 실행한다.

```cmd
python Code/main.py --test api
python Code/main.py --test unit-api
python Code/main.py --test api-live
```

api는 인증·인터넷 없이 공식 요청 계약, HTTP 오류와 실시간 프레임을 검사하고 보고서·그래프를 만든다.
api-live는 기존 kis.env로 미국 AAPL 시세 3개와 실시간 호가만 확인한다. 계좌·주문 호출은 없다.
main.py의 기존 뉴스 비활성·30종목 관찰·내부 모의매매는 기존 연결을 사용한다.

## 시세 조회 코드

아래 코드는 Code 안의 도구에서 사용할 때의 import다.
별도 스크립트는 Code가 모듈 검색 경로에 있어야 한다.

```python
from broker.kis_api import KisApiClient, overseas_stock

client = KisApiClient.from_settings()
# 요청 만들기: 이 시점에는 인터넷·인증을 호출하지 않는다.
request = overseas_stock.price(auth="", excd="NAS", symb="AAPL")
# 명시적으로 한 페이지 전송한다. 토큰은 기존 24시간 재사용 규칙을 따른다.
response = client.execute(request)
current = response.rows("output")[0]
```

계좌 조회도 같은 방식이다. 함수의 cano(8자리 계좌번호)·acnt_prdt_cd(2자리 상품 코드)를
호출자가 제공해야 한다. 실제 번호를 코드 저장소·예제·로그에 저장하지 않는다.
REST 응답은 원본 JSON을 payload로 보존하며 rows("output1") 등으로 객체/배열을 읽는다.
호출별 응답 필드·날짜·가격 단위·통화는 공식 목록의 링크에서 확인한다.

## 실시간 수신

```python
from broker.kis_api import KisApiClient, overseas_stock_ws
from broker.kis_api.websocket import open_stream

client = KisApiClient.from_settings()
with open_stream(client) as stream:
    stream.send(overseas_stock_ws.asking_price("1", "DNASAAPL"))
    for event in stream.events(maximum_messages=10, timeout=10):
        if event.kind == "data":
            print(event.rows)  # 예시는 시세만 출력한다. 체결통보에는 계좌 개인정보가 포함될 수 있다.
    stream.send(overseas_stock_ws.asking_price("2", "DNASAAPL"))
```

등록/해제, PINGPONG, 복수 레코드, 암호화 체결통보(AES-CBC/PKCS7)를 처리한다.
암호화 키는 메모리에만 둔다. 연결 종료 시 세션을 버린다.
자동 재연결·누락 복구는 하지 않는다. 재접속 후 REST 잔고·미체결 대조가 별도 필요하다.
실시간 지원 시장·구독 한도·무료/유료/지연 시세는 공식 계약과 계좌 권한에 따라 다르다.

## 주문 API

상품별 order/order_cash/order_rvsecncl 등의 함수도 요청을 만든다.
KisApiClient 기본값 allow_trading=False에서는 인증하기 전에 주문 전송을 차단한다.
사용자가 별도로 allow_trading=True를 명시한 클라이언트만 전송할 수 있다.
이 옵션은 현재 main.py에는 연결하지 않았으며 실주문·모의 서버 주문도 시험하지 않았다.
주문 전송은 중복 방지를 위해 자동 재시도하지 않는다. 응답 유실은 KisOrderStateUnknown으로 알린다.
이 예외가 나면 다시 주문하기 전에 체결·미체결 조회로 주문 상태를 확인해야 한다.
원자적인 주문 상태 저장·운용 중복 방지·잔고 동기화는 전략 실행 계층에서 별도로 구현해야 한다.

## 연속조회·실전/모의

한 번 execute하면 한 페이지를 반환한다. response.has_more와 continuation을 확인하고
API별 CTX_AREA_FK/NK·KEYB 등 응답 커서를 다음 요청에 직접 전달한다.
서로 다른 API의 커서를 추측해 자동 조합하거나 재귀적으로 무한 조회하지 않는다.
env_dv가 있는 함수는 real/demo를 설정하고 클라이언트의 prod/vps와 일치시킨다.
env_dv가 없는 함수는 실전 요청으로 생성한다. 해당 API의 모의 지원을 추정하지 않는다.
미국 모의 매도 TR은 공식 인자 설명에 따라 VTTT1001U로 명시 보정했다.

## 코드·자료 배치

- Code/broker/kis_api/*상품*.py: 입력 검사·TR 선택·파라미터 이름. API별 수정 위치.
- Code/broker/kis_api/client.py: 인증 공유·HTTP·호출 한도·주문 응답 유실 처리.
- Code/broker/kis_api/websocket.py: 실시간 연결·프레임·복호화.
- Code/broker/kis_api/models.py: 요청·응답·구독 자료형.
- Config/kis-api-catalog.json: 공식 경로·TR ID·출처의 허용 목록.
- Test/broker/test_kis_api.py: 합성 계약·전송·실시간 검사.
- Data/tests/fixtures/kis-api-vectors.json: 공식 코드와 대조한 입력/기대값 468개.
- Data/specs/kis-api: 공식 고정 커밋의 원본 예제와 SHA-256 근거. 실행 모듈로 import하지 않는다.
- Data/reports/kis-api: 검증 보고서·그래프·선택 실행한 실제 연결 결과.

실시간 기능의 의존성은 Deployment/requirements.txt에 있다.
공식 예제에 라이선스 파일이 확인되지 않아 임의의 오픈소스 라이선스를 부여하지 않았다.
원본과 고정 커밋을 기록하고, 변환한 요청 코드와 공식 구현과 다른 보정을 명시했다.

## 공식 포털 교차 확인 (2026-10-23)

공개 메뉴 338개(인증 3개 포함)의 경로를 전부 대조했고 누락 0개다.
상품 함수 338개는 REST 275개와 실시간 63개다. 함수 수와 포털 경로 수는
일부 예제의 별도 분기·동일 경로 때문에 일대일로 대응하지 않는다.
최신 실시간 출력은 Config/kis-websocket-schemas.json의 필드 순서를 따른다.
해외 호가 HDFSASP0는 예제 16필드 대신 포털·실응답의 71필드를 적용했다.
포털에만 있던 VI 통보 3개, 선물옵션 증거금률, ETF 호가, 해외 복수종목 조회를 추가했다.
야간 선물옵션 정정은 STTN1103U, 해외옵션 분봉은 HHDFO55020400으로 보정했다.

2026-10-28 사용자 요청으로 제공 종료 대상 국내 재무 API 7종을 함수·카탈로그·합성 입력에서 삭제했다. 원천 공지 시행일은 2026-11-11 16:00 KST다. 기존 미국 daily 관측은 해당 API를 사용하지 않는다.
