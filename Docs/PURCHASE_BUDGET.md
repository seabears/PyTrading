# 매수 한도와 현금·손익 장부 분리

## 최종 동작

매수 한도는 inquire-psamount.output.ovrs_ord_psbl_amt를 사용한다. 현금/NAV 장부를 이 계산의 입력으로 요구하지 않는다. 현재 실제 API 주문가능액 100000.000000 USD, 로컬 미반영 예약 0 USD, 추가 주문 한도 100000.000000 USD를 확인했다.

원격 주문 대조에서 확인된 미체결 주문은 API 한도에서 이미 반영된 것으로 처리해 다시 차감하지 않는다. 아직 API에 반영되지 않은 로컬 INTENT 및 접수 후 원격 대조 전 주문만 차감한다. SENDING/UNKNOWN은 먼저 대조해야 하므로 신규 주문을 막는다. 자신의 현재 주문은 중복 예약하지 않는다. 부분 체결 잔량과 CANCEL_PENDING도 원주문 식별로 처리한다. 비용 예약 완충1.003과 종목/투자/손실 한도는 그대로 유지한다.

## 코드 연결

Code/trading/buying_power.py: 매수 한도 전용 계산과 API 캡처 검증. API 계좌 지문·해시·실제 시각(30초)과 현재 프로세스의 검산 연결을 요구한다. 현금/NAV와 금액이 같을 필요는 없다.

OrderManager._risk 및 KIS 전송 직전 검사는 새 계산을 사용한다. 정상화된 주문 스냅샷에 buying_power_usd와 buying_power_evidence를 넣는다. 기존 cash 키는 호환용 주문 여력 별칭이며 장부 현금이 아니다. RiskLedger.validate_snapshot은 최신 API 증거가 있으면 주문가능액이 이전 손익 체크포인트의 한도와 같아야 한다는 조건을 제거하고, 대신 API 자체의 계좌/해시/시각을 검사한다. 증거 없는 구버전 입력은 기존 검사를 유지한다.

손익 체크포인트의 현금·노출·일일손실·연속손실은 바꾸지 않는다. API 한도가9000으로 바뀌어도 손익 원장 현금10000을9000으로 덮어쓰지 않는 회귀 검사에 통과했다. 미체결 접수/취소 자체를 손익으로 계산하지 않는다.

DemoExecutionPort와 읽기 전용 Code/kis_demo_balance.py 결과의 purchase_budget에 API 한도와 로컬 예약 내역을 출력한다. API 주문가능액은 매수 한도에, user_cash_account는 현금/손익 계산에 각각 연결돼 있다.

## 다른 제한

이 계산의 통과는 주문 실행 승인이 아니다. 통합 여력 사용 금지·USD 현금 상한·계좌/원주문 대조·최신 시세·상품/대출/신용/FMP 정책과 손실 검증을 유지한다. 현재 신규 주문false, 실제 주문0, 운영 Pi 시작/배포/재시작 없음. 사용자 지정 현금 장부와 기존 계좌/인증/계획을 초기화하지 않았다.

## 실제 검사

Windows/ARM 각각741통과/0실패/0미실행. 새11개 검사는 API 값이 현금 장부와 달라도 계산됨, 원격 예약 이중 차감 방지, 로컬 예약 차감, 부분 체결·취소 대기, 불명 주문, 누락/오래된 API 증거, 변조·재시작 바인딩 손실, 기존 손실 제한을 포함한다.

실제 모의 GET8회 시도/성공7/오류1, 저장 결과의 API 한도/추가 주문 한도100000 USD. 실제 주문/매도/취소/실계좌 조회0건. 합성 검사와 실제 읽기 조회를 구분한다. 최종263개 파일 소스 일치.

CMD 실행:

    cd /d C:\Projects\PyTrading
    python Code/kis_demo_balance.py
    python Code/main.py --test all

근거: C:\Projects\PyTrading\Data\reports\purchase-limit20261101-202037\report.md, C:\Projects\PyTrading\Data\reports\purchase-limit20261101-202037\results.json, C:\Projects\PyTrading\Data\reports\purchase-limit20261101-202037\actual-vps\results.json.


## 후속 정책: 가입 상태 검사 제거 (2026-11-01)

통합증거금 가입 상태는 주문 자격으로 요구하지 않는다. USD 현금·모든 미체결 예약·비용 완충1.003과 API 주문가능액 범위는 신규 주문 생성 및 전송 직전에 검사한다. 가입 상태를 확인한 것으로 기록하지 않는다. 이 정책 변경은 현재 위험 근거를 완성하거나 실제 주문을 승인한 것이 아니다. 최신 검증: C:\Projects\PyTrading\Data\reports\usd-funding-policy20261101-221157\report.md

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
