# 첫 모의 주문의 사전/사후 검증 흐름

## 완료 범위와 현재 판정

사전 기준 저장 → 주문 의도/접수 → 체결·잔고 관측 → 비용 확정 → 현금 대조 흐름을 기존 실행부에 연결했다. 코드·합성 통합 실행·Windows/ARM 전체 검사·실제 읽기 전용 대조·문서를 완료했다. 실제 증권사 주문은 실행하지 않았다.

실제 계좌 읽기 확인 2026-11-01T23:34:09.634313+09:00: 모델 현금100000.000000 USD, API 외화 주문가능액100000.000000 USD, 해당 조회 범위 보유/주문/체결0. 초기 현금 모델의 user_designation 출처와 최초 등록 시각을 보존했다. API 주문가능액을 공식 현금/NAV로 복사하지 않았다.

새 order_accounting_plan의 사전 차단 항목은 cash_movement_coverage다. 아직 발생하지 않은 주문의 최종 비용은 사전 필수 자료가 아니다(future_final_cost_is_pretrade_requirement=false). 현재 발생 체결 비용은 해당 없음이다. 자금 사건 원본 미확인이라는 기존 독립된 조건은 삭제·우회하지 않았다. 이 조건을 조용히 면제해야만 첫 주문을 보낼 수 있는 코드로 바꾸지 않았다.

## 실제 구현

1. LimitedDemoSession.submit에서 BUY 전송 시도 전에 prepare_pretrade를 호출한다. 승인된 현재 RiskLedger와 계좌 스냅샷·호가 시각·프로필 범위·1주 지정가·기존 USD 현금 및 API 여력·비용 완충1.003을 검사하고 같은 SQLite에 사전 기준을 저장한다. 현재 현금/보유, 원래 위험 체크포인트, 기존 체결/자금 사건 ID, 고정 주문 계약과 프로필/정책 해시를 보존한다. 미래 체결 금액·미래 비용은 만들어 넣지 않는다.
2. 저장 실패면 전송 함수 호출0회다. 사전 기록이 이미 있거나 주문이 불명 상태면 재전송하지 않는다. KIS 관리 전송 직전에도 validate_pretrade로 계좌·프로필·계약·시각·위험 체크포인트를 검사한다. 기존 HTTP 간격 대기 후 정책 재검사에서도 적용된다. 실전 주문·계좌 모드·상품/신용/대출 검사는 유지한다.
3. observe_settlement 재조회가 이미 확인된 비용을 None으로 덮어쓰던 문제를 수정했다. 같은 누적 수량/금액은 확정 비용을 보존한다. 추가 부분 체결로 누적 값이 바뀌면 비용을 미확정으로 되돌린다.
4. apply_verified_costs는 기존 RiskLedger가 원본 체결 ID/수량/금액/최종 비용으로 검산한 자료만 정산 관측에 연결한다. source_kind=kis_vps 및 계좌/최신성/검산 이슈 검사를 유지하고, 주문별 누적 수량·금액이 맞아야 비용을 가져온다. 모델·수동 verified·추정 비용·가짜 개별 체결을 확정값으로 사용하지 않는다. 현재 실제 모의 응답에 해당 원본이 없어 실제 비용을 가져오지는 않았다.
5. DemoExecutionPort.refresh는 실제 대조 후 비용 가져오기, 현금 모델/위험 평가 재계산, posttrade 관측을 수행한다. 비용이 미확정이면 SETTLEMENT_PENDING이며 추가 매수를 막는다. 기존 확인된 자기 보유 축소/취소 경로는 유지한다. 수량 불일치·조회 누락·중복 식별자는 REVIEW로 남긴다.
6. 사후 현금 검산은 현재 검증된 현금-사전 현금을 실제 체결 대금-최종 비용+확인된 자금 사건 합계와 대조한다. API 여력으로 현금 차이를 대신하지 않는다. 자금 사건은 투자 손익과 합치지 않는다. 원래 시험 밖의 새 체결은 검토 대상으로 기록한다.
7. LimitedDemoRunner는 평잔고와 비용 확정만으로 DONE 처리하지 않는다. posttrade=RECONCILED이고 실제/예상 현금 차액이 일치해야 완료다. 비용은 끝났어도 현금 근거가 없으면 CASH_RECONCILIATION_PENDING으로 남기고 전체 완료로 보고하지 않는다.

사후 단계: BASELINE_OBSERVED / ORDER_PENDING / HOLDING / SETTLEMENT_PENDING / CASH_RECONCILIATION_PENDING / RECONCILED / REVIEW. 단계는 계좌 전체 자동 매매 허가가 아니며 기존 500 USD·1주·최대2회 BUY 등 한정 시험 제한이 우선한다.

## 실행한 검사

| 환경 | 시각 KST | 통과 | 실패 | 미실행 | 성격 |
|---|---|---:|---:|---:|---|
| Windows Python3.12.6 | 2026-11-01T23:33:15.240303+09:00 ~ 2026-11-01T23:33:32.863845+09:00 | 781 | 0 | 0 | 전체 합성 회귀 |
| ARM Python3.13.5/aarch64 | 2026-11-01T23:34:04.791891+09:00 ~ 2026-11-01T23:34:15.008877+09:00 | 781 | 0 | 0 | 격리 장비 전체 합성 회귀 |

공통 명령 Code/main.py --test all. ARM 경로 /opt/PyTrading. 최종 Code/Config/Test 269파일과 실제 읽기 실행 코드가 일치한다. 추가16개 회귀와 관련 기존 검사를 통과했다. 최초 관련66개 실행은 새 합성 fixture가 다른 누적 체결에 같은 event_id를 사용한1오류로 실패했다. 실제 중복 방지 검사는 유지하고 fixture 사건 ID를 수정했다. 당시 로그 initial-failed-related-launcher.txt 보존, 이후 관련68개 통과와 중간 전체780개 통과 로그도 보존했다. 마지막 현금 차액 경계 추가 후 전체781개 최종 통과.

합성 첫 BUY 검사는 실제 OrderManager→LimitedDemoSession→ManagedKisAdapter→TrialKisApi의 전송 경계를 모의 HTTP 응답으로 실행했다. 사전 SQLite 저장/미래 비용 자료 없이1주 접수/실패 시 전송0을 확인했다. 합성 왕복은 10000 USD 기준, 매수100·매도105·수수료 각각0.5, 최종10004 USD/순변동+4를 계산하고 원장 대조했다. 합성 수치이며 실제 수익이나 실제 모의계좌 체결이 아니다.

추가 부분 체결 시 비용 재확인, 확정 비용의 중복 관측 보존, 비용만 확정/현금 미검산이면 미완료, 현금 차액 불일치면 REVIEW, 재시작은 자동 재무장/재전송 금지, 오래된 호가·계좌 변경·계약 변경·승인 변경·저장 실패를 검증했다. 기존 취소/체결 경합·응답 유실·조회 누락·상품 제한 검사도 전체 회귀에 포함됐다.

## 실제 조회 및 미실행

실제 vps GET9시도/7성공/2HTTP500 후 기존 제한 재시도로 회복. HTTP 세부 공급자 코드는 기존 감사 로그에 없어 미확인으로 남겼다. 실제 모의 BUY/SELL/CANCEL0, 실계좌 주문/접속0. 실제 위험 평가 9pass/0fail/1unknown이며 미확인은 자금 사건 완전성이다. 미래 최종 비용 경로는 사후 정산 준비 자료로 별도 미확인이다.

현재 자금 사건 자료가 없는 이유는 기존 주문/체결 조회가 입출금·배당·환전 전체 사건의 원본이 아니고, 공식 문서상 해당 모의 조회 경로가 제한되기 때문이다. 자금 사건 공급 자료를 만들거나 없었다고 가정하지 않았다. 새 코드를 합성으로 실행할 수 있다는 것과 현재 실제 계좌가 위험 승인을 통과했다는 것은 다르다. 현재 new_orders_allowed=false다.

정규장 시세 확인·실제 주문 접수/취소/체결·최종 비용의 실제 응답은 이번에 실행하지 않았다. 같은 공식 미지원 API를 재호출하거나 거부된 실제 주문 진입점을 다른 경로로 재시도하지 않았다. 가입 상태나 초기금을 사용자에게 다시 묻지 않았다. 일반 구현 작업은 추가 질문 없이 완료했다. 현재 근거로 실제 주문만 남았다고 보고할 수는 없다.

## 운영·보존·실행

운영 Pi 배포/시작/재시작/부팅enable/기존 repeated_collection_errors 중지 해제 없음. 현재 서비스 상태는 이번에 조회하지 않았다. ARM은 별도 격리 폴더다. Config/기존 전략/위험 한도/상품·대출·신용·FMP 정책 변경 없음. 계좌·인증·원본 자료·계획·SQLite·미커밋 작업 보존. SQLite integrity_check=ok 및 기존 초기 기준/주문/모든 과거 관측 보존을 직접 대조했다.

원장 백업: C:\Projects\PyTrading\Data\backups\prepost-order\20261101-143403.sqlite. 코드 백업: C:\Projects\PyTrading\Data\reports\prepost-order20261101-232756\before-source.tar.gz. 결과 폴더에 계좌 전체를 복사하지 않았다. 운영 배포가 없어 운영 롤백은 필요하지 않다. 코드 롤백은 백업을 별도 경로에서 대조하고 기존 계좌/운영 상태에 덮어쓰지 않는다.

Windows CMD:

    cd /d C:\Projects\PyTrading
    python Code/kis_demo_balance.py
    python Code/main.py --test all

읽기 전용 결과 order_accounting_plan에서 사전 차단과 사후 요구를 확인한다. 이 명령은 실제 주문을 보내지 않는다. ARM 재현은 격리 경로에서 `.venv/bin/python Code/main.py --test all`이다.

변경 파일: Code/broker/kis_api/client.py, Code/kis_demo_balance.py, Code/tools/test_features.py, Code/trading/demo_account.py, Code/trading/demo_accounting_cycle.py, Code/trading/demo_port.py, Code/trading/demo_runner.py, Code/trading/demo_session.py, Test/trading/test_demo_accounting_cycle.py, Test/trading/test_demo_runner.py, Test/trading/test_demo_session.py. 현재 요청에서 수행 가능한 코드와 검사/읽기 대조는 마쳤으며, 없는 외부 자료를 수집했다고 표시하지 않는다.
근거: results.json, actual-vps/results.json/responses-redacted.json, tests-windows.txt, arm-tests.txt, tested-source-hashes.json, checks.png.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
