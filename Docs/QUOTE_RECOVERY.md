# 라즈베리파이 시세 수집 장애 조사와 복구

검사일: 2026-10-29 KST. Windows Python 3.12.6, Pi Debian 13.4 aarch64 / Python 3.13.5.

## 결론과 원인 근거

운영 코드 반영 후 내부 모의 서비스 active/running, 부팅 disabled다. 주문·정정·취소는 전송하지 않았다.
현재 인증으로 Pi의 인증과 AAPL 호가 GET·정규화가 성공했다. 이전 인증 백업은 현재 인증과 다르며, 같은 Pi의 1회 인증 재현에서 HTTP 403으로 거절됐다.
당시 실행 프로세스는 파일 교체 전에 시작했으며 시작 때 읽은 인증을 계속 사용한다. 과거 인증 거절과 새 인증 정상 동작이 장애의 직접적인 설명에 부합한다.
단, 당시 프로세스 메모리·HTTP 원문이 보존되지 않아 이전 백업과 실행 메모리의 완전한 일치, 거절의 세부 사유와 발생 시점은 확정할 수 없다. 파일 전송 자체를 원인으로 단정하지 않는다.

인증 실패를 합성 재현하면 30종목에서 60초 대기가 29번 발생했다. 이는 기존 약 1740초 순회와 일치하는 코드 경로다. 수정 후 발급 간격 60초는 유지하되 같은 프로세스의 후속 요청은 즉시 대기 상태를 반환한다. 공통 네트워크/서버 장애도 60초간 재호출하지 않는다. HTTP 타임아웃 15초와 기존 요청 간격은 유지한다.

## 수정과 보존

- broker/kis.py: 안전한 단계·분류·HTTP 상태·허용 오류 코드, 인증/시세/전체 시간, 비차단 공통 재시도. 자유문 서버 메시지와 예외 내용은 저장하지 않는다.
- app/daily_service.py: 조회→정규화→감시 저장→계좌 처리→원장→JSONL 단계를 구분하고 실패한 이번 요청의 실제 시간을 기록한다. SQLite 보조 실패가 원래 오류를 덮지 않는다. 계좌/저장 실패 시 메모리에서도 신규 매수를 즉시 차단한다.
- app/operations.py: 프로세스 heartbeat와 quote_health 분리. 정규장 시작/마지막 정상 호가로부터 180초 공백이면 regular_quote_outage로 신규 매수 중지. 장외·휴장 오경보 없음. 신선한 호가가 돌아오면 이 사유만 해제한다.
- trading/observation_journal.py: 각 관측의 오류와 시간 자료를 SQLite에 보존. 회전된 JSONL과 독립적이다.
- tools/verify_quote_recovery.py: 읽기 전용 정규장 판정 도구. 현재 미국 현지 거래일·최신 프로세스·600초·전체 종목 3회·오류 없음·180초 초과 공백 없음·최신성으로 판정한다. 주문 자격을 부여하지 않는다.

계좌·대기 계획·원본 데이터·Credentials는 배포하지 않았다. 운영 시작 전 account와 Credentials 해시 일치를 메모리에서 검증했다. 원장의 기존 이벤트 4111개를 보존하고 후속 실제 이벤트만 추가했다. 전략 donchian__trailing_atr_3p5, 비용·위험·상품·대출 금지·FMP 제외 설정은 변경하지 않았다.
기존 repeated_collection_errors 중지는 보존했다. 관측 복구가 확인돼도 자동으로 이 중지나 손실/수동 중지를 해제하지 않는다.

## 실제 검사

|구분|이번 실행 결과|자료|
|---|---|---|
|Windows 수정 전 전체|589개 통과, 16.268초|baseline-tests.txt|
|새 회귀 6개 수정 전|2실패·3오류·1통과|도구 실행 결과; 60초 대기 29회 재현|
|Windows 최종 전체|599개 통과, 12.417초|windows-tests.txt|
|Pi ARM 최종 전체|599개 통과, 8.666초|arm-tests.txt, 별도 quote-recovery-20261029|
|ARM 최초 격리 실행|테스트 fixture 미복사로 32오류 → 자료 보완 후 통과|격리 배포 자료 문제이며 시세 서버 응답 검사가 아님|
|현재 인증 실제 Pi 시세 GET|성공, 정규화 가능, 인증 포함 약 1.995초|initial-pi.txt|
|이전 인증 실제 Pi 인증|HTTP 403, 약 0.066초|previous-auth-probe.txt|
|운영 반영·기동|active/running, disabled, 자동 재시작 0|deployment.txt, runtime-*.txt|
|정규장 전체 3회·10분|미검증 — 현재 정규장 전|results.json, 관측 표본 없음|
|KIS 모의/실 주문·체결|미검증·이번 전송 0건|주문 API 연결 없음|

추가한 10개 합성 검사는 인증 실패와 회복, 30종목 공통 인증/연결 장애, 이번 실패 경과 시간, 안전한 오류 필드, 정규장 공백/장외 예외, SQLite 보조 실패, 재시작 중지·관측 상태 보존을 다룬다. 기존 대기 계획·중복 체결·복원·주문 식별·취소·권한 검사는 전체 회귀에 포함했다. 실제 계좌 비용이나 손익을 합성 자료로 보충하지 않았다.

## 수정 전후 실제 관측 비교

검토 시점 10/28 정규장 49시도/49오류/정상0 → 이번 재확인 누적 61시도/61오류/정상0. 수정 전 완료 순회 약1740초, 시작 간격1800초.
이번 시작 이후 정규장 정상 관측 0건, 오류/누락 0건, 완전 순회 0회, 정상 관측 폭 0초. 모두 정규장 미관측 상태이며 '정상·손실0' 판정이 아니다.
현재 프로세스의 장외 실제 순회 시간은 [16.827601976000096, 1.7874799210003403, 1.8798820949996298]초다. 최초 순회에는 전일 일봉 준비가 포함된다. 장외에는 호가 GET을 하지 않으므로 과거 정규장 29분과 직접적인 성능 개선 비율로 비교하지 않는다. 수정 후 정규장 순회 시간·호가 지연 비교는 다음 장의 실제 자료가 필요하다.

## 백업·롤백

Pi 백업: /opt/PyTrading/Data/backups/quote-recovery-20261029-122649.
운영 SQLite는 backup API로 일관되게 보존했다. account/operations 및 변경 전 코드도 보존했다. private 권한이며 인증 파일은 백업 묶음에 추가하지 않았다.
해당 폴더의 rollback.sh는 sh -n 통과. 실행하면 서비스를 중지하고 이전 코드만 복원한다. Data·Credentials를 덮어쓰지 않으며 자동 시작/enable도 하지 않는다. 상태 복원을 별도로 해야 할 때는 먼저 서비스 중지, 원본 보존 및 기존 복구 절차를 적용한다.

## 다음 실제 정규장 확인

한국시간 10/29 22:30 이후 서비스가 실행 중인지 확인하고 최소 10분 이상 관측한다. 정규장 데이터 장애나 다른 중지를 무시하고 거래를 만들지 않는다.

```sh
ssh pytrading-pi
cd /opt/PyTrading
systemctl status pytrading-daily-validation --no-pager
PYTRADING_SETTINGS=$PWD/Config/settings-linux.json .venv/bin/python Code/tools/verify_quote_recovery.py --folder Data/device-validation/daily-observation
```

regular_recovery_verified=true일 때만 이번 프로세스의 실제 정규장 관측 기준 통과다. 서비스가 꺼져 있으면 sudo systemctl start pytrading-daily-validation으로 수동 시작한다. enable은 하지 않는다. 정지: sudo systemctl stop pytrading-daily-validation.

Windows 전체 회귀(CMD):

```cmd
cd /d C:\Projects\PyTrading
python Code\main.py --test all
```

도구 파일 경로 직접 실행의 import 경로 오류는 실제 명령 검사에서 발견해 수정했고, Pi에서 문서의 명령으로 종료 코드 0을 확인했다(documented-command.txt). 서비스 재시작 없이 조회 도구만 반영했다. 최종 운영 코드 5개와 Windows 코드의 해시 일치도 확인했다.

## 위험 원장 연결 전 남은 조건

현재 모의계좌 읽기 조회 성공은 주문/체결/취소 검증이 아니다. 모의계좌의 초기 기준 확정, 완전한 수수료·현금 이동·배당·입출금 근거, 수동 거래 대조, 최신 잔고·주문가능금액·순자산의 의미 차이 확인이 필요하다. 현재 내부 가상계좌 손익을 KIS 계좌로 복사하거나 verified=True를 지정하지 않는다. 실제 부분 체결·취소 경합의 응답 계약은 외부 모의 주문 단계 전 별도 확인 대상이다. 장기 20거래일·청산30건 수익성 평가는 관측 진행 중이다.

공식 근거 확인일 2026-10-29: [KIS 공식 샘플/토큰 1분 간격 안내](https://github.com/koreainvestment/open-trading-api), [KIS 공식 API 포털](https://apiportal.koreainvestment.com/docs). 호출 한도를 우회하거나 모의 계좌 인증을 prod 시세에 혼용하지 않는다.

그래프: Data/reports/quote-recovery/checks.png


## 2026-10-29 정규장 판정 보완 — 21:50 KST

서비스 재시작 없이 조회 도구만 보완했다. 현재 정규장 전이며 복구 미확인, 손익·위험 원장 연결은 시작하지 않았다. 이번 Windows/ARM 전체606개 검사 통과. 장외 순회 제외·종목별 연속성·실제 전체 순회·당일 이전 오류를 함께 판정한다. 최신 상세는 Docs/REGULAR_RECOVERY_VERIFICATION.md 및 Data/reports/regular-recovery/20261029-124439/report.md를 따른다. 과거 보고서는 이력이다. 부팅 disabled와 기존 매수 중지는 유지한다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
