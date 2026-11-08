# 위험 평가 연결 구현과 실제 읽기 전용 실행

## 완료 범위

현금·예약 계산을 받아 실제로 위험 검사를 수행하는 경로를 RiskLedger.assess_observation에 연결했다. 자료가 부족하면 평가 자체를 생략하던 부분을 해소했다. 평가 구현·실제 모의계좌 조회 실행·SQLite 저장·검사·문서 완료. 실제 위험 근거가 모두 확보됐다는 뜻이나 주문 시험 완료는 아니다.

연결: Code/kis_demo_balance.py 및 DemoExecutionPort.refresh → review_cash → RiskLedger.assess_observation → demo_risk_assessment.py → 같은 SQLite risk_assessment_ledger.checkpoints/latest/days. RiskLedger.assessment는 저장된 평가를 원본 시각/계좌/모드/설정/주문/현금 모델과 다시 대조한다. 조회만으로 시각을 갱신하지 않으며 30초가 지난 자료는 재사용하지 않는다.

사용자 초기금100000 USD 기준과 실제 보유/체결 관측은 구분해 연결한다. 예산·투자 비중·기존 손실 한도·관측 기준 일일 손실·관측 낙폭을 계산한다. 누락 비용이면 해당 손익/낙폭을 None으로 두며 없는 수치를0으로 채우지 않는다. 미래 비용 경로와 정규장 시세는 별도 준비 상태다. 거래가 없는 범위의 과거 비용 해당 없음과 미래 비용 미확인을 구분한다.

일일 손실 한도를 넘으면 해당 미국 현지 날짜의 halted를 영속 보존한다. 회복·중복 통보·재시작으로 당일 중지를 해제하지 않는다. 현지 날짜 전환 시 새 날짜 기준을 만들고 과거 중지 이력은 유지한다. 모델 낙폭은 관측한 모델 값에 대한 수치이며 미관측 시간의 성과·전체 거래일 손실로 표현하지 않는다. 기존 운영 Pi repeated_collection_errors 등 다른 서비스의 중지는 건드리지 않는다.

계좌·원본/시각·현금 모델이 바뀐 경우 재검산이 필요하다. 저장 실패 시 새 평가/일별 상태를 롤백하고 주문 차단을 유지한다. 모델 평가만으로 주문용 RiskProof를 발급하지 않는다. 기존의 완전한 공식 RiskProof가 실제로 존재하고 같은 현금/NAV/보유 및 최신성 검사를 통과하면 이를 재사용하는 경로도 구현·합성 검사했다. 이는 verified=True를 수동 지정하는 경로가 아니다. 읽기 전용 실행은 위험 검사가 통과해도 new_orders_allowed=false다.

## 실제 계좌 실행 결과

시각: 2026-11-01T22:54:17.779095+09:00. 모의 서버 vps, 기존 인증 파일과 기본 읽기 전용 계좌 원장 사용.
모델 현금 100000.000000 / 모델 NAV 100000.000000 / API 외화 여력 100000.000000 USD. 조회 범위의 보유/주문/체결0건, 원격/로컬 예약0.

| 검사 | 판정 | 근거 |
|---|---|---|
| USD 현금·예약 | pass | model_cash_reservations_compared |
| 총 투자 한도 | pass | existing_policy_applied |
| 보유·대기 종목 수 | pass | existing_five_position_limit |
| 현재 API 여력 | pass | current_account_bound_api_capacity |
| 수동·불명 주문 | pass | manual_and_unresolved_orders_checked |
| 해당 원장의 수동·복원 중지 | pass | existing_pause_restore_gates_preserved |
| 발생 체결 비용 | pass | not_applicable_no_fills |
| 자금 변동 이력 완전성 | unknown | no_validated_complete_vps_cash_event_source |
| 연속 손실 대기 | pass | no_trades_in_model_scope |
| 관측 모델 일일 손실 | pass | observed_model_only_cash_flows_unverified |

합계: 9통과/0실패/1미확인. evaluation_complete=true, evidence_complete=false, risk_approved=false, new_orders_allowed=false. 평가를 끝내지 않은 것이 아니라 평가 결과가 근거 부족으로 보류다. 실제 저장 assessment_id=d331ddb0ad38b1035e1228ad73a0355d89007b80e658c939d8d316aaeac00707를 SQLite에서 직접 대조했다.

현재 모델 일일 손실률 0, 모델 관측 낙폭 0. 현금 기준은 user_designation이고 external_cash_flows_verified=false, full_day_coverage_verified=false다. 이를 실제 계좌의 검증된 성과나 전체 장중 MDD라고 표현하지 않는다. 별도 한정 시험 프로필의500 USD/1주/최대2회 매수 등 기존 제한은 변경하지 않았으며 일반 위험 원장의 금액 한도가 더 크더라도 시험 한도가 우선한다.

실제 GET9시도/7성공/2오류. HTTP500 오류 후 기존 제한 재시도로 회복. 이번 실행의 오류 KIS 세부 코드는 해당 감사 기록에 없어 미확인. 원문 자유문 오류를 출력하지 않았다. 모의 매수/매도/취소0, 실계좌 접속/주문0. 조회 성공을 체결 성공으로 표현하지 않는다.

## 남은 외부 근거와 별도 실제 실행 조건

- 현재 위험 평가의 미확인 항목: 모델 최초 등록 이후 입출금·환전·배당 등 완전한 자금 사건 자료. 주문 이력에 행이 없다는 사실로 자금 변동이 없었다고 인증하지 않는다. 이전 cash_risk_review의 current_approved_risk_checkpoint_missing은 공식 RiskProof 미발급을 뜻하는 참고 정보이며, 이번 새 평가 실행의 실패나 미구현 항목은 아니다.
- 향후 체결 최종 수수료·세금을 확인할 모의 지원 자료/경로. 현재 체결0이므로 기존 체결 비용은 해당 없음으로 처리했고 미래 비용0으로 승인하지 않는다. 일반 정산 시점 설명은 첨부 문서에 있으나 모의 적용·개별 최종 비용 취득 경로를 대신하지 않는다.
- 실제 주문 시험 전 최신 정규장 시세와 계좌 대조, 한정 활성화 등 별도 절차. 이번 단계는 조회/평가이며 정규장 호가나 모의 체결 시험을 실행하지 않았다.

사용자에게 초기금이나 통합증거금 가입 상태를 다시 묻지 않는다. 일반적인 구현 선택을 사용자에게 넘기지 않는다. 제공되지 않은 자료의 포맷을 추정한 운영 파서, 합성 사건, 가짜 비용/자금 이력, 자동 승인 입력은 만들지 않았다. 기존 완전 근거의 검산·평가 재사용 경로는 실행 가능한 코드와 테스트로 준비됐다.

## 실제 검사 및 소스 일치

Windows Python3.12.6: 2026-11-01T22:55:56.269784+09:00~2026-11-01T22:56:11.248109+09:00, 765통과/0실패/0미실행.
ARM Python3.13.5/aarch64: 2026-11-01T22:56:50.403314+09:00~2026-11-01T22:57:00.341493+09:00, 765통과/0실패/0미실행.
두 환경 명령: Code/main.py --test all. ARM 검사 경로 /opt/PyTrading. 실제 ARM에서 합성 입력으로 검사했으며 외부 체결 검증이 아니다. 최종 Code/Config/Test 267파일이 일치한다. 실제 조회에 사용한 Code/Config와 최종 파일도 일치한다.

추가15개 검사는 계산 가능한 평가 수행, 완전 근거 재사용, 다른 현금 근거 거절, 위험 승인 분리, 일일 손실 중지·재시작·날짜 전환, 미확정 비용의 None 유지, 투자/예약 초과, 수동/불명 주문, PAUSE/복원 중지, 설정/주문 변경, 오래된/다른 계좌/저장되지 않은 입력, 저장 실패 롤백, 모델 관측 낙폭을 다룬다.

첫 ARM 실행은 합성 fixture의 검사 시각이 근거 생성보다 앞서1개 실패했다. 실제 유효시간 조건을 완화하지 않고 fixture에서 생성 완료 후 검사 시각을 취하도록 수정했다. 당시 Windows/ARM 로그와 소스는 before-clock-fixture-fix-*에 보존했다. 이후 최종 전체 검사 통과. 중간 Windows763개 통과 로그도 interim-763-*에 보존했다.

## 운영과 보존

운영 Pi 배포/시작/재시작/enable/기존 매수 중지 해제 없음. 현재 서비스 상태는 이번에 조회하지 않았다. ARM은 별도 경로에서 검사했다. Config/전략/위험 한도/상품·신용·대출·FMP 정책 변경 없음. 통합증거금 가입 상태 검사 없음.
원장 백업 C:\Projects\PyTrading\Data\backups\risk-evaluation\20261101-135409.sqlite, SQLite integrity_check=ok. 기존 기준/주문/관측과 미커밋 작업 보존. 새 평가 체크포인트를 같은 원장에 추가했으며 기존 Data/Credentials를 초기화하거나 운영 장비에 덮어쓰지 않았다. 코드 백업 C:\Projects\PyTrading\Data\reports\risk-evaluation20261101-225144\before-source.tar.gz.

## 실행 방법

Windows CMD:

    cd /d C:\Projects\PyTrading
    python Code/kis_demo_balance.py
    python Code/main.py --test all

읽기 전용 실행 결과의 risk_assessment.controls에서 검사별 pass/fail/unknown, decision과 준비 항목을 확인한다. 평가가 있어도 주문은 전송하지 않는다. ARM 재현은 격리 검사 경로에서 `.venv/bin/python Code/main.py --test all`이다. 운영 Pi 반영은 하지 않았다.

변경 파일: Code/kis_demo_balance.py, Code/tools/test_features.py, Code/trading/demo_port.py, Code/trading/demo_risk_assessment.py, Code/trading/risk_ledger.py, Test/trading/test_demo_risk_assessment.py.
근거: results.json, actual-vps/results.json 및 responses-redacted.json, tests-windows.txt, arm-tests.txt, tested-source-hashes.json, checks.png.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
