# 내부 모의 운용과 복구

## Windows — CMD

Python 3.11/3.12를 지원 대상으로 잡고 이번 Windows 검사는 3.12로 실행했다. 이미 동작 중인 환경을 지우지 않는다. 새 환경을 만들 때:

```cmd
cd /d C:\Projects\PyTrading
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r Deployment\requirements-research.txt
.venv\Scripts\python.exe Code\main.py --test all
```

평소 실행은 세 프로필 중 하나를 선택한다. 같은 API 키의 여러 프로세스는 호출량이 합산되므로 처음에는 하나씩 운용한다.

```cmd
python Code\main.py
python Code\price_paper.py
python Code\daily_paper.py
```

|프로필|설정|계좌|
|---|---|---|
|기본 실적|settings.json·strategy.json|Data/paper-kis|
|기존 단기 가격 연구|strategy-price-research.json|Data/paper-price-research|
|고정 일봉 후보|fixed-trend-study.json candidate|Data/paper-daily-frozen|

기본 실적 근거 부족으로 WAIT가 발생하는 것은 정상이다. 기본 전략을 자동 교체하지 않았다. 단기 -7.56%·비용 두 배 -11.90%는 저장 과거 시험이며 검증된 실전 전략이 아니다. 이전 일봉 장기 양수도 새로운 실시간 수익 증거가 아니다.

작업 디렉터리와 관계없이 Config·Data는 Code의 형제 폴더다. 설정의 상대 경로는 Code 기준이다. Linux만 PYTRADING_SETTINGS로 별도 JSON을 지정한다. Windows settings.json의 인증 경로는 보존했다.

## 관측과 장애

operations.json: heartbeat_at(프로세스 진행), last_normal_observation_at(실제 신선한 정규장 호가), last_valid_quotes, 오류 횟수, free_bytes, buy_halts를 구분한다. 장외 heartbeat가 정상이어도 실제 시세가 정상 수집됐다는 뜻은 아니다.

cycle_seconds는 전체 조회·처리의 실측 시간, cycle_start_interval_seconds는 실제 주기 시작 간격이다. configured_wait_seconds는 조회가 끝난 뒤의 대기다. 다음 주기는 조회 시간+대기 시간이며 실제 운영에서는 지연이 더해질 수 있다. 보유를 우선하고 비보유 3종목 사이에도 다시 조회한다. 일봉 다운로드 중에도 보유 가격 보호를 재확인한다. 이 스케줄이 모든 통신 상황에서 특정 초 이하 지연을 보장하지 않는다.

KIS 요청은 15초 timeout, 조회는 한도 오류 시 제한적 재시도, 무효 토큰 GET은 한 번 갱신 후 재시도다. 주문은 이 경로로 재전송하지 않는다. 3회 연속 오류·오래된 장중 호가·공간 256MB 미만은 신규 매수를 중지한다. 정상 보유 가격 매도 판단은 유지한다. 실제 디스크 쓰기 실패나 손상된 권위 상태는 체결을 꾸미지 않고 실행을 중단한다. 기록할 수 없는데 정상 체결했다고 처리하지 않는다.

상태·진단:

```cmd
python Code\operations.py status daily
python Code\operations.py pause daily
python Code\main.py --test unit-operations
python Code\main.py --test operations-live
python Code\main.py --test quote-latency
python Code\main.py --test daily-live
```

마지막 세 명령은 실제 인증/조회와 별도 관측·모의 상태 저장을 한다. 실제 주문은 없다. quote-latency는 장외에도 HTTP 응답 지연만 진단하므로 장중 성능으로 해석하지 않는다.

## 로그·저장·복구

decisions.jsonl·cycle-metrics.jsonl은 각 8MB에 3세대, alerts.jsonl은 1MB에 2세대로 회전한다. 계좌 거래 원장과 일봉 근거 자료는 관측 로그처럼 임의로 삭제하지 않는다. 상태·계좌 및 확정 일봉 근거가 누적되므로 용량을 모니터링하고 서비스 중지 후 외부 저장소에 백업한다. PaperAccount는 fsync·원자적 교체·account.json.previous를 사용한다. 최근 백업의 일부 거래가 누락될 수 있으므로 과거로 되돌린 뒤 무조건 매매를 재개하면 안 된다.

Ctrl+C 또는 systemctl stop으로 종료한 뒤:

```cmd
python Code\operations.py restore daily
python Code\operations.py status daily
```

복구는 잠금을 요구하고 원본을 quarantined 파일로 보존한 뒤 정상 JSON/현금/원가 검산을 통과한 백업만 복구한다. PAUSE_BUYS를 생성한다. 마지막 거래·대기 계획을 검토하고 현재 시세 정상 관측을 확인한 다음 서비스를 끄고 `python Code/operations.py resume-after-review daily`를 실행한다. 근거 없는 실적 조건이나 위험 검사를 해제하지 않는다. 반복 오류 카운터가 남으면 먼저 정상 응답을 확인해야 한다.

외부 알림은 연결하지 않았다. alerts.jsonl은 향후 별도 전송기가 읽을 로컬 outbox다. 키·토큰·계좌번호를 기록하지 않는다.


## 관측 원장과 장비 수용 검사

일봉 프로필은 회전 텍스트 로그와 별개인 observation-ledger.sqlite에 일별 집계와 계획·체결 근거를 남긴다. DAILY_PAPER.md와 PI_ACCEPTANCE.md를 따른다. SQLite 복사 시 서비스를 중지하고 backup API를 사용한다. 실제 관측이 없는 날의 평가·낙폭은 0으로 채우지 않는다.


## 2026-10-28 라즈베리파이 실제 검증 갱신

기존 접근 불가/ARM 미검증 표시는 이전 단계 기록이다. trader-main-pi의 Debian 13.4 aarch64 Python 3.13.5에서 전체 541개 통과, Windows 3.12.6에서도 541개 재통과. 별도 daily 내부 모의 서비스가 실행 중이며 재부팅 자동 시작을 실측했다. PI_DEVICE.md와 Data/reports/pi-acceptance/report.md가 최신 상태다. KIS 실제 주문 응답 계약과 장기 수익성은 미검증으로 유지한다.


## 사용자 운영 설정 — 부팅 자동 시작 비활성

부팅 자동 시작 등록을 해제했다. 현재 내부 모의 실행은 유지하고 이후 부팅에서는 자동 실행하지 않는다. `sudo systemctl start pytrading-daily-validation`로 수동 시작한다. 사용자가 별도 설정을 요청하기 전에는 enable하지 않는다.


## 2026-10-28 KIS 모의계좌 사전 준비

근거 기반 위험 계산은 RISK_LEDGER.md, 주문·위험 SQLite 백업과 새 경로 복구는 ORDER_BACKUP.md, 주문을 보내지 않는 실제 조회 절차와 남은 외부 계약은 KIS_READINESS.md를 따른다. verified=True 사전으로 위험 검증을 통과시키지 않는다. 현재 기본 서비스는 기존 daily 내부 모의 경로를 유지한다. 부팅 시작은 disabled다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
