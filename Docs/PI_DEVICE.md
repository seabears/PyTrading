## 내부 가상체결 위험 상향·ISRG 매수 — 2026-11-06T00:51:23.233171+09:00

사용자가 명시한 거래당 손절 손실 상한50%를 내부 PaperAccount에만 적용했다. Config/daily-paper-risk.json 사용, 기존 일일2%·종목당10%·총투자50%는 유지. KIS 모의/실계좌 한도·원장·고정 전략 신호는 그대로다. 현재 PID 4789로 계속 실행하며 내부 ISRG2주를 가상 취득원가 945.02722 USD, 손절선 430.99948로 관리 중. 실제 증권사 주문은 없다. MSFT는기존3%가격갭조건으로취소되어매수하지 않았다.

백업 /opt/PyTrading/Data/backups/internal-risk-20261105-155120. Windows/ARM 각각1091개통과·소스일치. 근거 C:\Projects\PyTrading\Data\reports\internal-risk20261105-154559\report.md. 아래 PID4431 기록은 이전 실행이다.

---

## 현재 기본 설정으로 관찰 재개 — 2026-11-05T23:53:11.369723+09:00

최신 설치 /opt/PyTrading의 내부 가상체결(internal_paper) 프로세스 PID 4431를 시작했다. 실제 시세 정상 90건, 조회 오류/누락/오래된 호가 각각0 확인. 자동 후보 75/159 검사 중. 수동 종료 전까지 계속 실행하며 부팅disabled 유지. 기존 systemd 구버전 서비스는 inactive로 남아 있으므로 이 서비스 상태만으로 최신 별도 프로세스의 실행 여부를 판단하지 않는다.

현재 상태 포인터 Data/operations/observer-latest.json, 세션 /opt/PyTrading/Data/operations/observer-20261105-145311. 실행 설정은 Config/settings-linux.json 및 Config/execution.json. 시세 인증은 기존 실제 사용 파일 경로로 연결만 수정했고 인증 내용/계좌/다른 모드의 원장은 보존했다. 현재 실행은 내부 가상체결이며 이전 KIS 모의 T 보유 관리 프로세스의 재개가 아니다. 증권사 모의/실계좌 주문을 전송하지 않는다.

근거: C:\Projects\PyTrading\Data\reports\observer-resume20261105-145751\report.md, C:\Projects\PyTrading\Data\reports\observer-resume20261105-145751\results.json. 아래 기록은 이전 시점의 이력이다.

---

## 재사용 수동 편입 메뉴 — 2026-11-05T00:54:36.621609+09:00

같은 최신설치에 Code/manage_positions.py 메뉴와 수동 편입 신청 API를 추가했다. `.venv/bin/python Code/manage_positions.py`에서 번호 선택 후 편입 입력. 실제 메뉴에 T1주 '이미 자동 관리 중' 표시·종료 확인. 신청 처리에는 기존 전략이 실행 중이어야 하고 실제 계좌 대조 뒤 처리한다. 현재PID5545, 종료예정 2026-11-05T06:00:00+09:00, bootdisabled 유지.

Windows/ARM1010개 통과·운영소스일치. T보호선20.56·비용대기/신규매수차단 보존. 자동매수201봉·55일돌파 규칙은 변경하지 않았다. 사용설명 [POSITION_ADOPTION.md](POSITION_ADOPTION.md), 상세근거 C:\Projects\PyTrading\Data\reports\manual-adoption-entry20261104-154613\report.md. 아래 기록은 작성시점 이력이다.

---

## T1주 자동 관리 연결 — 2026-11-05T00:37:38.322432+09:00

사용자 요청으로 기존 T 수동 모의1주를 고정 일봉 관리자로 연결했다. 현재보호선20.56 USD, 실제최근판단 HOLD/daily_holding 확인. 원주문·체결은 보존하고 관리 소유자와 보호 메타데이터만 이전했다. 비용대기와 신규매수차단 유지.

최신설치 /opt/PyTrading, 실행PID5255, 종료예정 2026-11-05T06:00:00+09:00. 부팅disabled 유지. 프로세스 종료 후에는 관측/자동매도가 멈추므로 이후 관리에는 다시 실행해야 한다. 사용 설명 [POSITION_ADOPTION.md](POSITION_ADOPTION.md), 실제근거 C:\Projects\PyTrading\Data\reports\position-adoption-entry20261104-152352\report.md. 아래 PID·수동보유 비관리 설명은 이전시점 이력이다.

---

## 로그 기능 반영 — 2026-11-05T00:11:27.254636+09:00

같은 최신 설치 /opt/PyTrading에 토큰 최근100건·미국 거래일/종목별 로그를 반영했다. Windows/ARM964개 통과·소스일치. 기존PID1963는 정상종료했고 현재전략PID4236(timeout4235)로 재개했다. 기존계좌·T1주·주문/계획·비용대기·부팅disabled를 보존한다. 종료예정 2026-11-05T06:00:00+09:00.

토큰로그 /opt/PyTrading/Data/logs/token-refresh.json(다음 실제발급부터 생성). 판단로그 /opt/PyTrading/Data/execution-accounts/kis_demo/paper-daily-frozen/logs/decisions/US-2026-11-04/종목.jsonl. 실제30파일/60건 확인. 설명은 [OPERATIONS_LOGS.md](OPERATIONS_LOGS.md), 상세근거 C:\Projects\PyTrading\Data\reports\audit-logs-entry20261104-150308\report.md. 중지는 `kill -TERM 4236`. 아래 PID와 설치 상태는 작성시점의 이력이다.

---

## 최신 장전 수동 실행 — 2026-11-04T22:48:01.893850+09:00

사용자 요청으로 최신 검증 설치 /opt/PyTrading의 기존 고정 일봉 전략을 kis_demo 모드로 수동 시작했다. 자식 PID 1963, timeout PID 1962. 개장 11/04 23:30 KST, 이번 실행은 11/05 06:00 KST 정규장 종료까지 예정. 부팅 등록은 변경하지 않았다.

실제 시작 시각은 개장 전이므로 기존 개장 후5분 진입 창이 적용된다. 11/03 확정 일봉으로 계산한 오늘 계획0건, 지표 준비29종목/SPCX100봉으로 부족1종목. 현재 장전 대기만 확인했으며 오늘 정규장 관측은 미검증이다.

같은 설치의 기존 증권사 주문 원장에는 T 수동 시험 매수체결1주가 보존돼 있다. 비용 미확정 차단을 유지하며 이 보유를 일봉 전략 소유로 바꾸거나 자동매도하지 않았다. 기존 pytrading-daily-validation.service는 inactive/dead/disabled이며 켜진 것은 별도 전략 프로세스다. 예전 ~/CMD 스크립트가 가리키는 20261102 설치와 혼동하지 않는다.

이번 세션: /opt/PyTrading/Data/operations/preopen-20261104-134607. 관측 계좌: /opt/PyTrading/Data/execution-accounts/kis_demo/paper-daily-frozen. 중지는 `kill -TERM 1963`. 전역 설정·Data·인증을 덮어쓰지 않았다. 상세 근거: C:\Projects\PyTrading\Data\reports\preopen-strategy20261104-134607\report.md.

---

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

# pytrading-pi 현재 내부 모의 운영

최신 확인: 2026-10-28 KST. SSH `ssh pytrading-pi`, 사용자 trader. Raspberry Pi 5 약 8GB, Debian 13.4 aarch64, Python 3.13.5. 설치 `/opt/PyTrading`. Windows 소스는 C:/Projects/PyTrading이며 장비와 자동 동기화되지 않는다.

현재 pytrading-daily-validation.service가 고정 일봉 후보의 별도 내부 모의 계좌를 지속 관측한다. 실제 주문은 전송하지 않는다. 부팅 자동 시작·실제 재부팅 복구는 시험했고, 이후 사용자 요청으로 자동 시작 등록을 해제했다. 현재 부팅 시작은 disabled이며 수동 시작만 사용한다. 전체 541개 검사 통과. 수익성 검증은 진행 중이다.

```sh
systemctl status pytrading-daily-validation
journalctl -u pytrading-daily-validation -f
sudo systemctl stop pytrading-daily-validation
sudo systemctl start pytrading-daily-validation
sudo systemctl restart pytrading-daily-validation
sudo systemctl disable --now pytrading-daily-validation
```

내부 계좌와 보고서: 설치 경로의 Data/device-validation/daily-observation. 인증은 Credentials/kis-market.env (600, trader 소유), 내용은 출력하거나 공유하지 않는다. 재배포 시 이 파일과 Data를 덮어쓰지 않는다. 현재 장비 전용 unit은 Deployment/raspberry-pi/pytrading-daily-validation.service다. 일반 rule-trader.service는 배포 예시로 보존한다.

정확한 실제 검사 범위와 시점별 관측 수는 Data/reports/pi-acceptance/report.md와 results.json을 따른다. 로그인/네트워크 전체 차단과 저장 공간 채우기는 시험하지 않았다. 합성 검사와 실제 API 관측을 구분한다.

## 부팅 시작 정책

부팅 자동 시작은 기본으로 사용하지 않는다. 현재 실행은 유지하고 재부팅하면 자동 실행되지 않는다. 직접 실행하려면 `sudo systemctl start pytrading-daily-validation`을 사용한다. 사용자가 별도로 원할 때만 `sudo systemctl enable pytrading-daily-validation`로 부팅 시작을 등록한다.


## 라즈베리파이 홈 CMD 원클릭 조회

홈 디렉터리 CMD 폴더의 상태 확인·실시간 로그·부팅 설정 확인 아이콘을 더블클릭한다. 조회 전용이며 서비스와 부팅 설정을 변경하지 않는다. 실제 경로는 /home/trader/CMD다. 실행 허용 안내가 나오면 실행을 허용한다. 실시간 로그 창 닫기는 관측 프로세스를 중지하지 않는다. SSH 전용 환경에서는 아이콘을 실행할 GUI가 없으므로 기존 명령을 사용한다.


## 최신 인증 파일 전달 — 2026-10-28

사용자 허용 후 Windows kis.env는 기존 Linux 설정에 맞춰 Credentials/kis-market.env로, kis_demo.env는 Credentials/kis_demo.env로 복사했다. 두 파일의 원본 일치, 소유자 trader, 권한 600을 확인했다. 상위 폴더는 700이며 이전 파일은 Credentials/.backups 아래에 비공개 보존했다. 인증 내용·해시는 보고서에 넣지 않았다.

전송 시 서비스 PID와 active/disabled 상태는 변경하지 않았다. 실행 중인 프로세스는 시작 때 읽은 인증을 사용하므로 새 파일은 다음 실행 때 읽는다. 모의 파일을 전달한 것만으로 KIS 모의 주문이나 실계좌 주문이 활성화되지는 않는다. 인증 경로/파일을 공개 저장소나 결과 묶음에 넣지 않는다.


## 2026-10-29 시세 장애 복구 반영

기존 인증 백업은 Pi에서 HTTP403, 현재 인증은 읽기 전용 호가 조회 성공. 인증 실패의 종목별 60초 대기 반복을 공통 비차단 재시도로 변경했다. 오류 단계·실제 시간·정규장 공백 감지를 추가했다. Windows/격리 Pi ARM 전체 599개 검사 통과. 기존 계좌/원장/인증을 보존해 운영 코드 5개만 반영하고 내부 모의 서비스를 수동 시작했다. 부팅 disabled, 기존 repeated_collection_errors 중지는 유지한다. 정규장 전이므로 실제 정규장 10분·전체3회 회복은 미검증이다. 자세한 근거와 다음 장 검증/롤백은 Docs/QUOTE_RECOVERY.md 및 Data/reports/quote-recovery/report.md를 따른다.


## 2026-11-02 별도 KIS 모의시험 준비

전용 설치 /home/trader/PyTrading-demo/20261102-123527, 수동 실행 ~/CMD/kis-demo-run.sh, 조회 ~/CMD/kis-demo-check.sh, 결과 ~/CMD/kis-demo-results.sh. ARM 전체801개 통과, 실제 모의계좌 읽기 전용 조회와 시세 전용 AAPL 호가 조회 성공. 주문0건. 기존 서비스 inactive/dead, MainPID0, 부팅disabled 확인; 변경 없음. 상세: [PI_DEMO_TRIAL.md](PI_DEMO_TRIAL.md). 정규장 관측과 실제 모의주문/체결은 아직 미검증.


## 2026-11-02 공통 체결 모드 최종 설치

최종설치 /home/trader/PyTrading-strategies/20261102-142640; 홈CMD/execution-mode.sh로 선택, strategy-run.sh로 기존고정일봉 수동실행, strategy-status.sh로선택확인. 현재 internal_paper, 전략프로세스 미시작, 기존서비스 inactive/dead/disabled 유지. Windows·격리ARM·최종설치 각각849개 통과. 실제읽기전용 최초모의진입근거는 Windows/Pi 모두 통과, 실제주문/체결미실행. KIS모의는 사용자 지정 초기금 모델이며 공식현금/NAV/과거자금변동검증과 구분한다. 후속 신규진입은 정산근거가 필요하며 실계좌전송은 잠금. 상세: [EXECUTION_MODES.md](EXECUTION_MODES.md).

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
