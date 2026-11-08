## 실제 상태 확인 — 2026-11-01T18:20:43.001971+09:00

읽기 전용 확인: 서비스 inactive/dead, 부팅disabled, 운영 설치 /opt/PyTrading. 마지막 정상 정규장 관측 2026-10-30T01:56:54.874390+09:00; process_stopped 2026-10-30T01:57:12.653393+09:00. 현재 매수 중지 repeated_collection_errors 유지. journal0행/종료시각 필드 공백으로 중지 원인은 미확정이며 정상 종료·오류·사용자 조작으로 단정하지 않는다. 서비스 시작·재시작·배포 없음. 이전 ‘active/복구 통과’ 본문은 각 시점의 이력이다. 실제 주문 시험 전 최신 정규장 관측이 다시 필요하다.

계좌 자료 취득 경로와 미확인 범위: [KIS_ACCOUNT_EVIDENCE.md](KIS_ACCOUNT_EVIDENCE.md). 새 보고서: C:\Projects\PyTrading\Data\reports\account-evidence20261101-181549\report.md.

---

## 최신 한정 모의 시험 결과 — 2026-10-29

실제 미국 정규장 복구 확인=true. 이번 보고서 기준 30종목 정상호가 420건, 정규장 전체 14회, 오류·누락0건이다. 시세 수집 서비스 PID2281과 부팅disabled, 기존 repeated_collection_errors 중지를 유지했다. 조회 검증기의 동시기록 시각 오경보만 수정·백업·반영했으며 서비스 재시작은 없었다.
실제 vps 인증과 계좌GET 조회는 성공했으나 최초 USD 순자산/체결현금/최종 비용/자금 사건 근거가 부족해 위험 원장 ingest와 실제 모의 주문은 중지했다. 주문가능100000 USD와 외화예수금표시0 USD를 초기 자금으로 채택하지 않았다. 기존 settlement_basis라는 출력 필드명은 호환성용이며 이 필드의 결제/체결 현금 정의가 검증됐다는 뜻이 아니다.
이번 최종 Windows/ARM 전체633개 검사 통과. 실제 모의 주문·취소·체결은 미실행이며 합성 검사로 대체하지 않는다. 새 Config/kis-demo-session.json은 enabled=false다.
최신 결과: C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\report.md, C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\results.json, C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\handoff.md. 읽기 전용 실제 응답과 공식 고정 버전 근거도 같은 폴더에 있다. 아래 기존 본문은 각 작성 시점의 이력이다.

---

# 운영 개발 현황 — 2026-10-27

판정에서 '검증됨'은 아래에 적은 범위만 뜻한다. 합성 장애 통과를 실제 Linux·증권사 체결 검증으로 바꾸지 않는다. 이전 운영 구현 단계의 기준은 470개였다. 이번 재검토의 시작 결과는 514개, 수정 후 전체 결과는 541개 통과다. 주문 수정 근거는 Data/reports/reconciliation-review이며, 최신 ARM 실기기·운영 근거는 Data/reports/pi-acceptance/report.md다.

|기능|판정|근거·검증 범위|
|---|---|---|
|KIS 시세·기본 실적 근거 차단·내부 계좌|구현 및 검증됨|Code/app/runner.py, strategy/engine.py, trading/paper.py. 이번 Windows 회귀·KIS 인증/장외 관측|
|실적 데이터 신뢰성·수익성|구현됐으나 미검증|news/earnings_validation.py, Data/earnings-audit/verified-events.json. 승인 사건 없음; 부족한 근거를 우회하지 않음|
|원자적 상태 저장·이전 세대·명시 복구|구현 및 검증됨|app/stateio.py, Test/app/test_operations.py. 저장 실패·손상·활성 잠금 합성 검사|
|반복 오류·공간 부족 매수 중지·보유 검사|구현 및 검증됨|app/operations.py, trading/paper.py. 신규 매수만 차단하는 합성 검사|
|실제 주기·호가 나이 계측|구현 및 검증됨|operations.json, cycle-metrics.jsonl, tools/quote_latency.py. 장외 HTTP 진단; 이번 격리 정규장 30종목 1회 관측 추가; 보유 종목 없음으로 보유 지연은 미검증|
|고정 일봉 지속 내부 모의 경로|구현 및 검증됨|Code/daily_paper.py, app/daily_service.py, trading/daily_account.py. 재시작 대기 계획·중복·놓친 시가·매도 유지 합성 검사 및 이번 실제 정규장 30종목 1회; 가상체결 0|
|일봉 정규장 가상 체결·수익성|구현됐으나 미검증|새 계좌 paper-daily-frozen. 실제 장중 관측 체결과 충분한 미래 거래 표본 필요|
|systemd·부팅 시작·watchdog·Linux 잠금|구현 및 검증됨|Pi 5 Debian 13 aarch64: 시작·중지·재시작·중복 잠금·watchdog·재시작 제한·실제 재부팅 자동 시작. Data/reports/pi-acceptance|
|ARM64 설치 의존성|구현 및 검증됨|실제 ARM Python 3.13.5에서 고정 14개 설치와 전체 541개 통과. CP311 휠 제공 확인과 구분|
|주문 의도·부분 체결·취소·응답 유실 복구|구현 및 검증됨|trading/orders.py, Test/app/test_operations.py, Test/broker/test_execution_guard.py. 합성 응답·로컬 SQLite 기준|
|KIS 모의 주문·계좌 전체 조회 어댑터|구현됐으나 미검증|broker/managed_kis.py, trading/reconciliation.py. 실제 모의투자 키·계좌 연결 없음|
|실계좌 자동 운용·주문 송신|미구현(의도적 차단)|prod·live 전송 모두 금지. 설정 environment=prod로 허가되지 않음|
|외부 알림 서비스|미구현|로컬 alerts.jsonl outbox만 제공. 외부 전송 없음|

기존 Git 이동·삭제 표시와 새 파일은 모두 현재 작업으로 보존했다. Git 관련 실행 환경 변수가 간섭해 첫 명령이 실패했으나 해당 변수만 제거한 읽기 전용 subprocess에서 상태를 확인했다. 저장된 git-status.txt 참고. 커밋·리셋·데이터/인증 삭제는 수행하지 않았다.


## 이번 재검토

추가 경계 두 사례를 먼저 재현해 실패를 보존했고 정식 회귀 검사와 수정 결과는 Data/reports/reconciliation-review에 저장한다. 일봉 관측 원장과 장비 결과 수집 도구를 보강했다. 그 단계 당시 장비 접근은 불가했다. 이후 실제 장비 검사 결과는 아래 2026-10-28 갱신과 PI_DEVICE.md를 따른다.


## 2026-10-28 라즈베리파이 실제 검증 갱신

기존 접근 불가/ARM 미검증 표시는 이전 단계 기록이다. trader-main-pi의 Debian 13.4 aarch64 Python 3.13.5에서 전체 541개 통과, Windows 3.12.6에서도 541개 재통과. 별도 daily 내부 모의 서비스가 실행 중이며 재부팅 자동 시작을 실측했다. PI_DEVICE.md와 Data/reports/pi-acceptance/report.md가 최신 상태다. KIS 실제 주문 응답 계약과 장기 수익성은 미검증으로 유지한다.


## 사용자 운영 설정 — 부팅 자동 시작 비활성

부팅 자동 시작 등록을 해제했다. 현재 내부 모의 실행은 유지하고 이후 부팅에서는 자동 실행하지 않는다. `sudo systemctl start pytrading-daily-validation`로 수동 시작한다. 사용자가 별도 설정을 요청하기 전에는 enable하지 않는다.


## 2026-10-28 KIS 모의계좌 사전 준비

근거 기반 위험 계산은 RISK_LEDGER.md, 주문·위험 SQLite 백업과 새 경로 복구는 ORDER_BACKUP.md, 주문을 보내지 않는 실제 조회 절차와 남은 외부 계약은 KIS_READINESS.md를 따른다. verified=True 사전으로 위험 검증을 통과시키지 않는다. 현재 기본 서비스는 기존 daily 내부 모의 경로를 유지한다. 부팅 시작은 disabled다.


최신 준비 단계: Windows/ARM 전체 582개 통과. 기존 서비스 active/running·부팅 disabled, 운영 소스 130개 시작 시점과 일치. 새 도구는 Windows와 별도 ARM 검증 경로에만 추가했으며 기존 daily 운영 소스에는 덮어쓰지 않았다. 실제 vps 조회·최종 비용/자금 원본 연결·실제 체결은 미검증이다.


## 2026-10-28 실제 모의계좌 읽기 확인

Windows kis_demo.env의 ACC_NO 결합형으로 실제 vps 조회가 성공했다. 상품 GET 응답 7페이지, 주문 0건. 비용/자금 변동·위험 평가·실제 체결/취소는 미검증이며 주문 허용은 false다. Data/reports/demo-connection/report.md 참고. 기존 모의 파일 없음 문구는 당시 이력이다.


## 2026-10-29 시세 장애 복구 반영

기존 인증 백업은 Pi에서 HTTP403, 현재 인증은 읽기 전용 호가 조회 성공. 인증 실패의 종목별 60초 대기 반복을 공통 비차단 재시도로 변경했다. 오류 단계·실제 시간·정규장 공백 감지를 추가했다. Windows/격리 Pi ARM 전체 599개 검사 통과. 기존 계좌/원장/인증을 보존해 운영 코드 5개만 반영하고 내부 모의 서비스를 수동 시작했다. 부팅 disabled, 기존 repeated_collection_errors 중지는 유지한다. 정규장 전이므로 실제 정규장 10분·전체3회 회복은 미검증이다. 자세한 근거와 다음 장 검증/롤백은 Docs/QUOTE_RECOVERY.md 및 Data/reports/quote-recovery/report.md를 따른다.


## 2026-10-29 정규장 판정 보완 — 21:50 KST

서비스 재시작 없이 조회 도구만 보완했다. 현재 정규장 전이며 복구 미확인, 손익·위험 원장 연결은 시작하지 않았다. 이번 Windows/ARM 전체606개 검사 통과. 장외 순회 제외·종목별 연속성·실제 전체 순회·당일 이전 오류를 함께 판정한다. 최신 상세는 Docs/REGULAR_RECOVERY_VERIFICATION.md 및 Data/reports/regular-recovery/20261029-124439/report.md를 따른다. 과거 보고서는 이력이다. 부팅 disabled와 기존 매수 중지는 유지한다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
