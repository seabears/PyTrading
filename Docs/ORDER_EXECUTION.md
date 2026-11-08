# 주문 상태 관리와 전송 경계

기본은 내부 모의다. Code/trading/orders.py의 OrderManager는 SQLite 원장·프로세스 잠금을 사용하고, 각 모드·계좌 별칭을 검산한다. Config/execution.json에 internal/kis-demo/live 저장 위치를 구분해 두었지만 기본 main.py는 기존 PaperAccount를 사용하며 이 파일의 모드를 바꿔도 증권사 주문 서비스를 시작하지 않는다. 자동 실계좌 서비스는 제공하지 않는다.

원장 상태: INTENT → SENDING(전송 전에 영속 저장) → ACCEPTED → PARTIAL → FILLED/CANCELLED/REJECTED. 응답 유실·전송 직후 종료는 UNKNOWN이다. UNKNOWN/SENDING은 재전송 금지이며 재시작 시 현금·잔고·주문 전체 페이지 조회를 대조하기 전 신규 주문을 허용하지 않는다. 조회에 주문이 안 보인다는 이유만으로 미접수라고 간주하지 않는다.

수신은 누적 체결 수량·누적 금액·사건 ID를 사용한다. 중복/역순을 더하지 않으며 누적 값 충돌·수량 초과는 대조 실패다. 취소 접수는 CANCEL_PENDING이며 최종 취소 응답 전까지 잔여 수량을 예약한다. 늦은 체결이 취소와 경합해도 누적 체결을 반영하고 완료 상태를 되돌리지 않는다. 체결 후에는 새 원격 현금·비용을 대조한 뒤 다음 주문을 허용한다.

미확인 주문은 운영자가 전체 이력에서 식별한 접수 번호를 bind_unknown으로 연결한 다음 다시 reconcile한다. 종목·방향·수량·가격의 유일한 일치를 확인하고, 자동으로 유사한 주문을 추정해 새 주문을 내지 않는다. 실제 접수 번호를 찾을 수 없으면 중지 상태를 유지한다.

미국 주식 정수 주·USD 지정가만 이번 실행 어댑터가 지원한다. $1 미만·소수 수량·시장가·미확인 상품은 차단한다. 매수 지정가는 센트 내림, 매도는 센트 올림으로 처리한다. 이는 지원 범위를 좁힌 정책이며 미국 모든 상품의 최소 호가 단위가 항상 센트라는 주장이 아니다. 주문 수량 예약·주문 가능 외화·최대 주문 10%·총 투자 50%·최대 5종목·일일 손실·연속 손실·일일 매수 수·초기 손절 위험을 전송 직전에 다시 검사한다.

## KIS 모의투자 준비

broker/managed_kis.py는 기존 공식 요청 생성기와 KisApiClient를 사용한다. create_demo_api는 별도 kis-demo.env를 명시적으로 읽고 vps/orders-인증지문.json에 토큰을 저장한다. 주문 계좌번호는 어댑터 메모리에만 전달하며 원장·로그에 남기지 않는다. 기본 전송 enabled=False다. 시세 prod 토큰은 cache/kis/prod/market-token.json으로 분리하며 기존 정상 토큰은 동일 키/환경일 때만 원본을 보존해 이관한다.

모의 키가 없으므로 이번에는 실제 vps 주문·잔고·현금·체결 통보를 확인하지 않았다. 합성 응답만 검증했다. normalize_snapshot에 필요한 초기 자금·일일 손실·연속 손실의 검증된 위험 원장도 필요하며 verified 플래그만 근거 없이 붙이지 않는다. 없으면 자동 중지한다. 매수가능 외화는 주문 한도로 쓰고 예수금 전체/공식 순자산과 같다고 주장하지 않는다. 정상화되지 않은 처리 상태·지원 범위 불명·페이지 상한은 조회 성공으로 취급하지 않는다.

모의 주문 파이프라인은 synchronize(manager, adapter, risk_context, start, end, symbol, price) → manager.create(고유 신호 ID, ...) → manager.dispatch(...). 조회·잔고·자금 대조에 실패하면 중지한다. 현재 전략 서비스가 이 파이프라인을 자동 호출하지 않으므로 모의투자 외부 계약 검증 후 별도 연결 작업이 필요하다. 주식 서비스 이외의 대출·신용·대주·미확인 상품·ETN·선물·옵션·ELW 차단을 우회하지 않는다.

## 공식 문서 확인 — 2026-10-27

- [미국 주문 공식 예제](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/order/order.py): 실전 매수 TTTT1002U, 매도 TTTT1006U. 모의 매수 VTTT1002U, 매도 VTTT1001U. 모의는 지정가 00만 지원하는 범위로 제한했다.
- [체결 내역 공식 예제](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_ccnl/inquire_ccnl.py): TTTS3035R/VTTS3035R. 모의는 종목·주문번호 검색 제약에 맞춰 전종목/전체 상태로 조회한다.
- [미체결 공식 예제](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_nccs/inquire_nccs.py): 현재 예제의 env_dv 인자와 달리 TR 구현은 실전만 명시한다. 모의 지원을 단순 V 치환으로 주장하지 않고 전체 주문체결 조회에서 상태를 대조한다.
- [정정취소 공식 예제](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/order_rvsecncl/order_rvsecncl.py), [KIS 공식 개발자센터](https://apiportal.koreainvestment.com/): 계좌 계약별 지원과 최신 공지를 외부 검증 전에 다시 확인한다.

공식 공지의 계정별 최신 호출 한도를 이번 공개 조회만으로 확정하지 못했다. 실행 간격은 계약 한도 보장이 아니며 읽기 API의 한도 오류를 제한적으로 대기/재시도한다. 주문 POST는 응답 유실을 재전송하지 않는다. 모의 환경은 기존 클라이언트의 더 느린 간격을 유지한다.

## 실거래 전환과 중지

이번 버전은 live/prod의 주문·취소를 코드에서 금지한다. allow_trading=True, environment=prod, JSON 변경만으로 해제되지 않는다. 같은 클래스의 낮은 HTTP 경로도 차단한다. 실전 TR ID 요청 명세 생성은 보존한다.

실거래 전 필요한 것은 ARM 실기기 장기 운영, 실제 vps 계약·수수료·부분 체결·응답 유실 복구 검증, 위험 원장/수동 거래 대조, 거래 가능 종목·호가 단위 확인, 충분한 새 기간의 모의 성과, 명시적 별도 실거래 활성화 변경 검토다. 이 조건을 이번 합성 테스트로 충족했다고 주장하지 않는다.

중지는 신규 매수 PAUSE_BUYS와 별개로 원격 미체결 주문을 먼저 조회한다. 서비스를 끄는 것만으로 증권사 주문이 취소되지 않는다. 기존 원장은 삭제하지 않고 미체결·체결·잔고를 확인한다. UNKNOWN은 임의 파일 편집으로 INTENT로 되돌리지 않는다. SQLite 원장은 서비스 종료 후 WAL까지 일관된 SQLite backup API로 백업하고, 복구 시에는 모든 미완료 주문을 불명 상태로 재대조해야 한다. 아직 주문 원장 자동 백업 복구 CLI는 제공하지 않으며 내부 PaperAccount 복구 명령으로 대신하지 않는다.


주문 원장은 접속 환경·앱 키·계좌·상품코드의 SHA256 지문도 대조하므로 동일 별칭의 다른 증권사 계좌로 교체할 수 없다. 지문 원문이나 계좌번호를 저장·출력하지 않는다.


## 재검토 후 변경

주문 불변 필드·원자적 대조·원격/로컬 예약 분리·취소 권한과 전송 단계 구분은 [최신 수정 문서](RECONCILIATION_REVIEW.md)를 따른다. ready=False라는 이유만으로 확인된 원주문의 안전한 취소까지 막지 않는다.


## 2026-10-28 KIS 모의계좌 사전 준비

근거 기반 위험 계산은 RISK_LEDGER.md, 주문·위험 SQLite 백업과 새 경로 복구는 ORDER_BACKUP.md, 주문을 보내지 않는 실제 조회 절차와 남은 외부 계약은 KIS_READINESS.md를 따른다. verified=True 사전으로 위험 검증을 통과시키지 않는다. 현재 기본 서비스는 기존 daily 내부 모의 경로를 유지한다. 부팅 시작은 disabled다.


## 2026-10-28 실제 모의계좌 읽기 확인

Windows kis_demo.env의 ACC_NO 결합형으로 실제 vps 조회가 성공했다. 상품 GET 응답 7페이지, 주문 0건. 비용/자금 변동·위험 평가·실제 체결/취소는 미검증이며 주문 허용은 false다. Data/reports/demo-connection/report.md 참고. 기존 모의 파일 없음 문구는 당시 이력이다.


## 사전/사후 주문 회계 연결 (2026-11-01)

첫 주문 전 기준을 저장하고 전송 직전에 대조한다. 아직 발생하지 않은 주문의 최종 비용은 사전 요구가 아니다. 체결 후 미확정 비용은 추가 매수를 중지하고, 확인된 보유의 축소/취소는 별도로 유지한다. 비용·현금 검산이 끝나야 전체 완료로 처리한다. 현재 자료의 사전 승인 조건을 면제하거나 실제 주문을 전송한 것은 아니다. 실행 결과와 제한은 [PREPOST_ORDER.md](PREPOST_ORDER.md) 및 C:\Projects\PyTrading\Data\reports\prepost-order20261101-232756\results.json를 따른다.


## 2026-11-02 한정 시험 기준 갱신

사용자가 사용자 지정100000 USD와 최신 빈 계좌·여력을 비교하는 최초 체결 전 한정 모의시험을 승인했다. 실제 자료 생성→RiskLedger 입력→주문 전 대조를 연결했다. 공식 현금/NAV·과거 자금 변동은 미검증 표시를 유지한다. 기본 주문 차단과 운영 서비스 설정은 유지한다. 실행/종료/비용 미확정 처리: [DEMO_USER_BASIS.md](DEMO_USER_BASIS.md). 이 항목은 기존 엄격한 공식 자료 판정을 한정 시험에만 구분 적용하며 일반 자동매매 승인을 뜻하지 않는다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
