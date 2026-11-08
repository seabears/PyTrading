# KIS 모의 잔고 → 관측 원장 연결

## 실행

Windows CMD:

    cd /d C:\Projects\PyTrading
    %USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe Code/kis_demo_balance.py

기본 인증 파일은 프로젝트의 Credentials/kis_demo.env다. --env-file로 다른 경로를 지정할 수 있다. 현재 작업에서 Pi 운영 경로에 배포하거나 서비스를 시작하지 않았다.

기본 원장: Data/execution/kis-demo-balance/orders.sqlite. 기존 전략/실계좌/모의 시험 원장과 별개이며 계좌·환경 지문을 검증한다. --store와 --output은 Data 내부만 허용한다. 실행 위치에 따라 저장 루트가 바뀌지 않는다. 실제 주문·취소 옵션은 없다. 토큰은 기존 vps 캐시를 재사용한다.

## 연결한 데이터와 연결하지 않은 값

NASD/NYSE/AMEX 전체 잔고 페이지, 모의에서 지원하는 체결기준현재잔고 output3, AAPL/500 USD 조건의 주문가능액을 읽는다. GET3종류와 vps 인증POST 외의 HTTP는 차단한다. 현재 실제 최신 응답으로 보유0개, USD 주문가능액100000을 저장했다. 이는 현재 현금100000을 확인했다는 뜻이 아니다.

계좌·모드·원본 해시·실제 관측 시각(30초)·전체 페이지·중복 보유·수량/금액을 검산한 뒤 기존 RiskLedger.record_unsettled_observation에 연결한다. 같은 캡처 재수신은 동일 ID로 중복 저장하지 않는다. 과거 응답을 읽은 현재 시각으로 바꾸지 않는다. 다른 계좌/실전/미완료 페이지/충돌 중복/NaN/저장 실패는 주문 승인으로 이어지지 않는다.

동일 보유가 거래소 조회에 중복 반환되면 같은 계약/금액인지 대조한 뒤 한 번만 합산한다. 다른 잔고 구분은 자동 합산하지 않는다. 보유의 매입금액·평가액은 요청/응답 통화 USD에 연결된다. output3 총자산금액·외화평가총액 등의 값은 공식 필드 이름과 함께 저장하되 단위 통화는 None으로 둔다. 통화/환산 기준을 확인하지 않고 USD NAV나 현금으로 쓰지 않는다. 미지원 output2는 현금으로 사용하지 않는다.

원장은 risk_observations에 출처 해시/시각/계좌 지문/집계값/부족 근거를 보존한다. execution_cash_usd, net_asset_value_usd, final_costs_usd, realized_pnl_after_cost는 미확정(None), risk_approved와 new_orders_allowed는false다. 기존 승인용 RiskProof/계좌 스냅샷/초기 기준을 만들지 않으며 위험 한도나 통합증거금 차단을 우회하지 않는다.

기존 DemoExecutionPort.refresh에도 이 관측 연결을 추가했다. 기존 위험 원본 검산은 계속 별도 요구하며 기본 실적/가격/일봉 전략을 교체하지 않는다. 이 단계는 ‘실제 조회 자료의 관측 원장 연결 완료’이며 ‘USD 현금/NAV 위험 승인 완료’가 아니다.

## 검증과 실제 실행

Windows Python3.12.6, ARM aarch64/Python3.13.5 각각722개 통과. 계좌 불일치·해시 변조·낡은/미래 캡처·페이지 누락/반복·중복 보유 충돌·미지원 output2·저장 실패·재시작 보존·금지 HTTP·거래소 설정 전달을 포함한다. 최종 소스258파일 일치.

실제 vps GET 총9건: 첫 실행은 거래소 설정 누락으로 4건 조회 후 저장 전 실패, 수정 후5건 조회해 별도 SQLite 저장 성공. 실패 자료를 지우지 않았다. 실제 주문/취소/실계좌 호출0. 저장값을 프로세스 종료 후 SQLite 읽기로 재검산했다. 최초 원문 확인시각 2026-11-01T10:07:55.627555+00:00, 저장시각 2026-11-01T10:07:55.671513+00:00. 이후 보고 시각을 최신 계좌 상태로 바꿔 쓰지 않는다.

근거: C:\Projects\PyTrading\Data\reports\balance-ledger-link20261101-190222\report.md, C:\Projects\PyTrading\Data\reports\balance-ledger-link20261101-190222\results.json, C:\Projects\PyTrading\Data\reports\balance-ledger-link20261101-190222\actual-vps-retry\responses-redacted.json.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
