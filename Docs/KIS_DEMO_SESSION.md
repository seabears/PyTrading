# KIS 한정 모의 시험 결과

판정: **선행 조건 미충족**. 실제 비용·자금 변동·초기 현금/NAV 근거 부족.

## 실제 관측과 주문의 구분

조회 결과: risk_sources_blocked; 조회 페이지 7개. 주문가능 USD 100000.00, 외화예수금 표시 USD 0.000000. 두 값을 초기 기준 자금/체결 기준 현금으로 채택하지 않았다.
정규장 관측은 운영 SQLite의 실제 이벤트를 한정 조회로 수집했다. 장외 주기/합성 검사/이전 거래일 기록을 통과 표본으로 사용하지 않았다. source event hash와 종목별 지연/간격, 정규장 순회 원본은 actual-latest.json에 있다. 오류 이벤트는 삭제하지 않았다.
모의/실 주문 전송은 모두0건이다. 시험 계층은 기본 비활성이고 별도 조회 진입점에는 주문 활성화 인자가 없다. 위험 근거 부족 상태에서 전송 경로를 연결하지 않았다.

## 새 구현과 검사 범위

한정 시험 모듈은 기존 영속 주문 의도/dispatch/취소 관리자를 호출한다. 추가 한도는 단일종목/지정가1주/보유1주/매수최대2시도/누적500USD/정리 매도·취소 각최대2시도/최초활성화부터10분으로 고정한다. 기존0.3% 예약 완충도500USD 안에 포함하며 실제 수수료로 간주하지 않는다. 엄격한 기존 계좌 전체 위험 검사를 통과해야 하며, 합성/재생 위험 근거는 실제 주문 자격이 아니다.
응답 유실 뒤 재전송 금지, 주문 대조의 state 복사 후 카운터 보존, 타 주문 취소/기존 보유 매도 금지, 신규 매수 중지 후 확인된 자기 주문 취소, 만료·재시작 시 차단을 합성 검사했다. 외부 KIS 실제 응답을 합성 성공으로 표현하지 않는다.
읽기 도구는 vps 호스트의 인증POST와 허용된 계좌GET만 실제 HTTP 경계에서 허용한다. 조회 후 API 주문 허가를 false로 닫고 원장을 종료한다. 본 실행에서 사용된 코드 해시는 results.json에 있다.

## 검사 로그

- C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\baseline-windows.txt
- C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\tests-windows.txt
- C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\arm-tests.txt
- C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\related-tests.txt
- C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\actual-latest.json

Windows 시작 기준은 이번에 606개를 실행했다. 최종 Windows 633개, ARM 633개 통과다. ARM 격리 위치는 /opt/PyTrading이며 인증/운영 계좌는 복사하지 않았다. 실제 주문 관련 항목은 미실행이다.

## 공식 계약 근거 — 2026-10-29 22:12:47 KST

공식 소스 고정 commit 3a9be59a3ed8745720dc3aa9d584bdf3b7830362. 파일별 URL/해시는 official-contracts.json과 official-contracts/에 보존했다.
미국 모의 매수 VTTT1002U, 매도 VTTT1001U, 지정가00 지원은 [공식 주문 예제](https://github.com/koreainvestment/open-trading-api/blob/3a9be59a3ed8745720dc3aa9d584bdf3b7830362/examples_llm/overseas_stock/order/order.py)에서 확인했다. 원주문 연결/취소02/취소가격0은 [공식 취소 예제](https://github.com/koreainvestment/open-trading-api/blob/3a9be59a3ed8745720dc3aa9d584bdf3b7830362/examples_llm/overseas_stock/order_rvsecncl/order_rvsecncl.py)를 따른다.
모의 이력 VTTS3035R의 전종목/전체상태/현지날짜/페이지 조건은 [공식 주문 이력](https://github.com/koreainvestment/open-trading-api/blob/3a9be59a3ed8745720dc3aa9d584bdf3b7830362/examples_llm/overseas_stock/inquire_ccnl/inquire_ccnl.py)과 대조했다. 실제 지원/빈 결과의 완전성은 실제 조회를 했을 때만 별도 주장한다.
현금 의미에 주의한다. API 이름은 체결기준현재잔고이고 frcr_dncl_amt_2의 공식 필드명은 외화예수금액2다. 이 필드만으로 완전한 체결현금 또는 결제기준 현금이라고 단정하지 않는다. 주문가능금액은 자금 한도이며 최초 순자산과 다르다. [공식 현재잔고 필드](https://github.com/koreainvestment/open-trading-api/blob/3a9be59a3ed8745720dc3aa9d584bdf3b7830362/examples_llm/overseas_stock/inquire_present_balance/chk_inquire_present_balance.py), [공식 주문가능 필드](https://github.com/koreainvestment/open-trading-api/blob/3a9be59a3ed8745720dc3aa9d584bdf3b7830362/examples_llm/overseas_stock/inquire_psamount/chk_inquire_psamount.py).
일별거래내역 [공식 예제](https://github.com/koreainvestment/open-trading-api/blob/3a9be59a3ed8745720dc3aa9d584bdf3b7830362/examples_llm/overseas_stock/inquire_period_trans/inquire_period_trans.py)는 CTOS4001R만 제시하며 모의 TR을 확정하지 않는다. 이것만으로 미지원이라고 단정하지도, 임의 V 치환을 시도하지도 않았다. 기존 토큰1분/보수적REST간격/호출제한백오프를 유지한다. 최신 계정별 구체 한도는 공식 포털·실제 제한 응답을 우선한다.

## 보존·배포·롤백

시세 수집 서비스는 변경/재시작하지 않았다. 읽기 전용 검증 도구1개만 동시기록 시각 경계 보완 후 백업·반영했다. 백업=/opt/PyTrading/Data/backups/demo-verifier-20261029-134136. Windows 신규 모듈과 테스트·프로필만 추가했다. Data/Credentials/기존 계좌/신호/대기 계획을 덮어쓰지 않았다. before/에는 이번 변경 관련 로컬 코드 이력을 보존했고, 신규 파일은 자동 실행부에 연결하지 않았다. 사용 중인 기존 Pi 복구 백업은 이전 문서의 Data/backups/regular-verifier-20261029-125012와 quote-recovery-20261029-122649에 그대로 있다. 이번 시험 준비 코드를 비활성화하려면 신규 진입점을 실행하지 않고 Config/kis-demo-session.json enabled=false를 유지한다. 서비스나 계좌 복원이 필요한 변경은 수행하지 않았다.

## 실행 방법

Windows CMD: cd /d C:\Projects\PyTrading 후 python Code\main.py --test all.
Pi: ssh pytrading-pi 후 cd /opt/PyTrading, PYTRADING_SETTINGS=$PWD/Config/settings-linux.json .venv/bin/python Code/tools/verify_quote_recovery.py --folder Data/device-validation/daily-observation.
실제 계좌 읽기 도구는 python Code\kis_demo_session.py --recovery-file <최신실제관측JSON> --output <Data내결과폴더> 이며 읽기 전용이다. 종료코드3은 조회 후 미확인 위험 근거로 차단됐다는 뜻이다. 주문 실행 기능이 활성화된 명령이 아니다.

## 검토용 전달문

[검토용 AI 전달 보고]

- 전체 판정: 선행 조건 미충족. 실제 비용·자금 변동·초기 현금/NAV 근거 부족. 구현/합성 검사 완료와 실제 주문 시험 완료는 구분한다.
- 작업 시각: 2026-10-29 22:02:07 KST ~ 2026-10-29 22:44:52 KST. 미국 현지 거래일 2026-10-29. 실제 관측 스냅샷 기준 2026-10-29 22:44:47 KST.
- 구현·운영 반영: Code/trading/demo_session.py(1종목·1주·500USD·매수2회·고정10분·재전송금지·취소정리), Code/trading/demo_readiness.py(미확인 현금/초기NAV/비용/자금 사건 차단), Code/kis_demo_session.py(vps 읽기 전용 진입점), Config/kis-demo-session.json(enabled=false), 시험 관련 회귀26개 및 관측 시각 회귀1개 추가. 기존 OrderManager/RiskLedger/ManagedKisAdapter 재사용. 시세 수집 서비스는 변경/재시작하지 않았다. 읽기 전용 검증 도구1개만 동시기록 시각 경계 보완 후 백업·반영했다. 백업=/opt/PyTrading/Data/backups/demo-verifier-20261029-134136. Windows 코드와 ARM 검사본 해시 일치=True, 운영 기존5개 코드와 Windows 일치=True. 버전은 results.json의 versions, 공식 계약 고정 버전은 3a9be59a3ed8745720dc3aa9d584bdf3b7830362.
- 정규장 복구: 모든 종목의 공통 정상 관측 기간: 2026-10-29 22:30:56 KST ~ 2026-10-29 22:44:36 KST, 공통 폭 819.864265초.  regular_recovery_verified=true; 대상 30종목, 정상 420건, 조회오류 0건, 누락 0건, 오래된 호가 0건, age 불일치 0건. 종목별 최소 관측 폭 822.903964초, 최대 종목별 간격 64.477535초, 최대 호가 지연 13.843713초. 전체 순회 14회. 순회 시간/시작 간격 전체 목록은 results.json regular_observation에 기록. null은 미관측이다. 당일 프로세스 시작 1회, 제어 이벤트 0개; 상세 이력은 results.json day_history와 actual-latest.json. 오류/중단 자료 삭제나 재시작으로 검증 구간을 변경하지 않았다.
- 위험 원장: 실제 ingest 미완료, 초기 기준 자금/시점 미확정. 조회 결과: risk_sources_blocked; 조회 페이지 7개. 주문가능 USD 100000.00, 외화예수금 표시 USD 0.000000. 두 값을 초기 기준 자금/체결 기준 현금으로 채택하지 않았다. 기존 RiskLedger 검사는 삭제하거나 우회하지 않았다. 원본 비용·자금 사건의 모의 지원 계약 및 완전성이 확인되지 않아 fees=0/입출금없음/verified=True를 사용하지 않았다.
- 실제 모의 주문: 허용 환경은 vps뿐이며 실제 계좌 연결 확인=True. 매수0·매도0·취소0 요청, 시험 접수0·체결0·거절0·최종취소0건. 이 0은 전송하지 않은 시험 범위의 수치이며 외부 계좌의 전체 거래가0이라는 의미가 아니다. 실제 부분 체결·취소 경합·응답 유실은 미관측이다.
- 종료 상태: 이번 시험의 원격 미체결=0, 잔여 보유=0주(null은 원격 미조회). 주문 활성화=false. 기존 서비스 active, PID 2281, NRestarts 0, 부팅 disabled. 기존 buy_halts=['repeated_collection_errors'] 유지. 무인 반복 매매/부팅 활성화 없음.
- 검사 결과: Windows 최종 633개 통과/0실패, 17.759초; ARM 최종 633개 통과/0실패, 8.847초. 두 환경 모두 실제 명령 Code/main.py --test all. Windows 시각 2026-10-29T13:40:11.779101+00:00 ~ 2026-10-29T13:40:31.191737+00:00; ARM 시각 2026-10-29T13:40:26.071490+00:00 ~ 2026-10-29T13:40:36.307028+00:00 (UTC, KST=+9h). ARM 경로 /opt/PyTrading. 실제 모의 주문 검사는 미실행이며 자동 검사 개수로 대체하지 않는다. 로그 절대경로: C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\tests-windows.txt; C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\arm-tests.txt; C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\related-tests.txt.
- 정책 보존: 실계좌 주문 전송0건. 기존 Data/Credentials/계좌/대기계획 초기화·덮어쓰기 없음. 전략·기존 위험 한도·상품 제한·신용/대출 금지·FMP 제외 정책 유지. 결과 폴더에 계좌 DB나 인증 파일을 복사하지 않았다.
- 미완료 사항: 실제 비용·자금 변동·초기 현금/NAV 근거 부족. 위험 입력의 원본 출처, USD 기준 초기 NAV·현금, 최종 체결 비용, 입출금/배당/환전/수동 거래 전체 이력을 검증해야 한다. 공개 CTOS4001R 예제만으로 모의 지원을 확정하거나 V로 추측 치환하지 않는다. 한정 주문 제어는 구현/합성 검사했지만 실제 주문 시나리오 자동 실행과 최종 잔고 청산은 외부 위험 근거가 확보된 다음에 연결해야 한다.
- 근거 파일: C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\report.md; C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\results.json; C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\checks.png; C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\handoff.md; C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\actual-latest.json; C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\official-contracts.json. 실제 API 결과: C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\actual-vps-20261029-134203-153808\result.json.
- 다음 단계: 현재 관측 상태와 미확인 위험 원본을 대조할 수 있다. 정규장 복구와 실제 위험 근거가 모두 확인되기 전에는 시험 매수·주문 활성화·실계좌 전송을 진행하면 안 된다. 기존 검토 AI는 위 원본/로그/버전으로 판정 가능하며 과거 검사 개수를 이번 결과로 재사용하지 말 것.


그래프: C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207/checks.png

## 실제 관측 중 확인한 검증 도구 오경보와 수정

13:36:11.692445 UTC에 검사를 시작한 뒤, SQLite 스냅샷을 읽는 동안 기록된 정상 관측12개를 미래 이벤트로 오인한 사례를 확인했다. 해당 행은 조회오류 없이 호가 나이0.8~3.9초였으며 실제 미래 시세를 사용한 것이 아니다. 읽기 완료 시각을 평가 상한으로 사용하도록 수정했다. 수정 전 재현1개 실패, 수정 후 관련8개 통과, 최종 Windows/ARM 전체633개 통과다.
원장 행·이전 poll 결과를 삭제하지 않았다. snapshot-race-before.txt, snapshot-race-after.txt, verifier-deployment-and-race.json에 재현·원본 시각·반영 상태를 남겼다. 서비스 PID2281/재시작0/부팅disabled를 유지했고 위험 기준은 완화하지 않았다.


실제 API 감사: 인증POST 성공 1건, 계좌GET 성공 7건, 계좌GET 실패 후 재시도 1건. 실패 당시 HTTP 상태·provider code는 이 감사 래퍼에 보존되지 않아 미확인이다. 기존 코드에서 GET 재시도는 호출 제한 경로이며 이를 통해 회복한 것으로 추론하지만 정확한 코드를 단정하지 않는다. 최종 전체 페이지와 양끝 주문 이력의 동일성은 확인했다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
