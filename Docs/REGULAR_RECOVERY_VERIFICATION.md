## 최신 한정 모의 시험 결과 — 2026-10-29

실제 미국 정규장 복구 확인=true. 이번 보고서 기준 30종목 정상호가 420건, 정규장 전체 14회, 오류·누락0건이다. 시세 수집 서비스 PID2281과 부팅disabled, 기존 repeated_collection_errors 중지를 유지했다. 조회 검증기의 동시기록 시각 오경보만 수정·백업·반영했으며 서비스 재시작은 없었다.
실제 vps 인증과 계좌GET 조회는 성공했으나 최초 USD 순자산/체결현금/최종 비용/자금 사건 근거가 부족해 위험 원장 ingest와 실제 모의 주문은 중지했다. 주문가능100000 USD와 외화예수금표시0 USD를 초기 자금으로 채택하지 않았다. 기존 settlement_basis라는 출력 필드명은 호환성용이며 이 필드의 결제/체결 현금 정의가 검증됐다는 뜻이 아니다.
이번 최종 Windows/ARM 전체633개 검사 통과. 실제 모의 주문·취소·체결은 미실행이며 합성 검사로 대체하지 않는다. 새 Config/kis-demo-session.json은 enabled=false다.
최신 결과: C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\report.md, C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\results.json, C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\handoff.md. 읽기 전용 실제 응답과 공식 고정 버전 근거도 같은 폴더에 있다. 아래 기존 본문은 각 작성 시점의 이력이다.

---

# 실제 정규장 복구 검증 — 2026-10-29 21:50 KST

## 판정

**미완료: regular_recovery_verified=false. 손익·위험 원장 연결은 선행 조건 미충족으로 시작하지 않았다.**
현재 미국 현지 거래일은 2026-10-29이며 정규장 전이다. 도구 종료 코드는 0이지만 복구 성공이 아니다.
거래소 달력상 오늘 정규장 시작은 한국시간 22:30이다. 원장의 오늘 정규장 시도/정상/오류는 모두 0건이며, 전체 30종목의 정규장 신선도·연속성·관측 간격은 미관측이다.
0건을 정상 운용·무손실로 표시하지 않았다. 이전 10/27 정상 기록과 10/28 실패 기록은 이번 통과 표본으로 쓰지 않았다.

## 실제 원장 및 서비스 근거

- SSH pytrading-pi, 설치 /opt/PyTrading.
- pytrading-daily-validation.service: active, PID 2281, 자동 재시작0. 이번 작업 중 재시작하지 않았다. 부팅 disabled와 repeated_collection_errors 중지를 유지한다.
- 프로세스 시작: 2026-10-29T12:26:50.635940+00:00; 이번 도구가 읽은 당일 SQLite 이벤트 738개.
- 정규장 정상 호가 0건, 오류·누락·오래된 호가 합계 0건. 정규장 자료가 없어 지연·간격 최대값은 null이다.
- 실제 정규장 전체 순회 0회. 장외 순회 23회는 별도 제외했다. 장외 1~2초 주기를 정규장 성능으로 재사용하지 않는다.
- 당일 시작 이벤트 1개, 제어 이벤트 0개. 시작 이전 미관측 시간은 연속 가동으로 추정하지 않는다. systemd NRestarts=0만으로 전체 중단 이력이 없다고 주장하지 않는다.
- 원본 근거: 운영 observation-ledger.sqlite events의 일관된 읽기 스냅샷. 날짜별 집계와 시작/종료 이벤트를 함께 확인했다. 조회 자료와 소스 지문은 results.json에 보존했다. DB·계좌·계획을 수정하지 않았다.

## 이번 코드 변경

Code/tools/verify_quote_recovery.py를 읽기 전용으로 보완했다. 운영 시세 수집기·전략·위험 한도는 변경하지 않았다.

1. 종목마다 600초 이상의 관측 폭, 최소 3개 정상 표본, 간격 최대180초, 첫 관측 지연과 최신 관측 나이180초 이내를 확인한다. 한 종목의 긴 공백을 다른 종목의 정상 표본이 가리지 못한다.
2. 원본 quote.available_at으로 호가 지연을 다시 계산하고 저장된 age와 대조한다. 오래된 호가가 숫자 필드만으로 통과하지 않는다.
3. cycle 종료 시각과 실측 duration으로 정규장에 완전히 포함되는 순회만 추출하고, 각 순회 구간의 실제 전체 대상 관측을 확인한다. 별도 regular_cycles에 duration/시작 간격/관측 종목 수를 출력한다.
4. 기존 metrics에는 UTC 시작 시각이 없어 종료−duration으로 시작을 추론한다. SQLite 관측 매칭에는 기록 오버헤드 1초 허용을 명시했다. 시작 시각은 정확한 실측 UTC 시작으로 표현하지 않는다. 순회 근거가 없거나 누락된 경우 false다.
5. 최신 프로세스 자료와 당일 전체 오류·시작·종료·후처리 실패 이력을 분리해 출력한다. 재시작 이전 오류를 지워 통과시키지 않는다. 같은 날 오류가 있으면 추가 검토 대상으로 남긴다.
6. 종료코드0과 regular_recovery_verified를 구분한다. 어떤 결과에서도 new_orders_allowed=false다.

Test/app/test_regular_verifier.py의 회귀 7개를 전체 검사에 등록했다. 수정 전 잘못 통과한 사례는 희박한 종목별 관측, 누락된 순회 근거, 원본과 다른 age, 재시작 전 실패, 일부 종목의 짧은 관측 폭이다. 최초 검사에서는 합성 임시 SQLite 연결 미종료로 Windows 정리 오류도 발견했으며 명시적 close로 수정했다. 해당 과정은 regression-before.txt/after.txt에 구분해 남겼다.

## 이번 실행 검사 결과

|환경·구분|이번 실행 결과|근거|
|---|---|---|
|Windows 시작 기준 전체|599개 통과 / 12.835초|baseline-windows.txt|
|Windows 변경 후 전체|606개 통과 / 13.8초|tests-windows.txt|
|Pi ARM 격리 전체|606개 통과 / 8.794초|arm-tests.txt|
|새 합성 회귀|7개 통과|regression-after.txt|
|실제 운영 원장 조회|성공, 복구 판정 false|deployment-and-actual.json.txt, results.json|
|실제 정규장10분·전체3회|미검증 — 아직 정규장 전|오늘 정규장 자료0건|
|이번 실제 KIS API 계좌 조회|미실행 — 선행 복구 미확인|이전 성공 결과를 이번 결과로 사용하지 않음|
|실제 손익·위험 원장 연결|미진행 — 선행 복구 미확인|임의 기준/비용/verified 값 없음|
|실제 주문·체결|미검증·전송0건|계좌/주문 송신 경로 변경 없음|

Windows Python3.12.6, ARM Debian13.4 aarch64/Python3.13.5. ARM은 운영과 다른 regular-verification-20261029 경로에서 검사했다. 과거 599개 결과를 이번 실행 결과로 복사하지 않았다. 전체 자동 검사는 네트워크 연결을 차단한 기존 진입점을 사용했다.

## 운영 반영·보존·롤백

조회 도구 1개만 백업 후 원자 교체했다. 서비스 PID와 상태가 반영 전후 일치했으며 관측 구간을 재시작으로 잘라내지 않았다.
백업: /opt/PyTrading/Data/backups/regular-verifier-20261029-125012
rollback.sh는 sh -n 통과했으며 조회 도구만 복원하고 서비스를 재시작하지 않는다. 기존 Data·Credentials·계좌·대기 계획·SQLite는 덮어쓰지 않았다. 설정·상품·신용/대출 금지·FMP 제외 정책도 유지한다.
Git 시작/종료 상태는 git-before.txt와 git-after.txt에 남긴다. 이전 미커밋 변경을 되돌리거나 커밋하지 않았다.

## 다음 확인 절차

22:30 개장 후 실제 관측이 누적된 뒤, 예를 들어 22:45 이후 아래 명령으로 확인한다. 시간이 지났다는 이유만으로 통과시키지 않는다. 자동 확인 예약은 새로 만들지 않았다.

```sh
ssh pytrading-pi
cd /opt/PyTrading
systemctl status pytrading-daily-validation --no-pager
PYTRADING_SETTINGS=$PWD/Config/settings-linux.json .venv/bin/python Code/tools/verify_quote_recovery.py --folder Data/device-validation/daily-observation
```

regular_recovery_verified, per_symbol의 continuous·span·maximum_interval·latest_observation_age, regular_cycles의 complete·seconds·start_interval_seconds 및 day_history를 함께 확인한다. 오류 발생 시 삭제나 임의 재시작으로 구간을 숨기지 말고 안전한 오류 분류로 조사한다. 기존 매수 중지는 자동 해제하지 않는다.

Windows CMD 전체 회귀:

```cmd
cd /d C:\Projects\PyTrading
python Code\main.py --test all
```

Windows와 Pi 설정 파일은 각각 유지한다. Pi 운영 데이터의 복구 판정은 해당 Pi 원장을 대상으로 실행한다.

## 손익·위험 원장 연결의 남은 조건

이번에는 복구 미확인으로 실제 모의계좌 조회·변환·ingest를 실행하지 않았다. 복구 확인 후 기존 ReadOnlyKisApi/ManagedKisAdapter와 RiskLedger를 재사용한다.
기존 주문가능100000 USD와 결제예수금0 USD는 과거 응답이며 이번 재조회 값이 아니다. 이를 초기 순자산으로 임의 채택하지 않는다.
최초 기준 자금/시점, 체결기준 현금과 결제예수금/주문가능금액/순자산 차이, 원가/예약, 고유 체결식별자/시각/최종 비용, 입출금/배당/환전, 수동·타프로그램 거래 및 전체 페이지 완전성 근거가 필요하다. 공식 모의 지원이 없거나 자료가 부족하면 구체적인 미확인 항목으로 남기고 위험 승인과 신규 주문은 계속 차단한다.
수수료0·입출금없음·verified=True·내부 가상계좌 손익 복사로 통과시키지 않는다. 실제 조회/실제 응답 재생/합성 검사를 별도 출처로 유지한다. 주문·체결 승인과 장기 수익성 검증은 이번 복구 판정과 별개다.

그래프: C:\Projects\PyTrading\Data\reports\regular-recovery\20261029-124439/checks.png

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
