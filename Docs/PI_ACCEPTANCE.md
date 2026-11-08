# 라즈베리파이 격리 검증과 결과 수집

2026-10-28 KST 실기기 검증을 완료했다. 확인된 장비·실행 경로·서비스는 PI_DEVICE.md, 실제 통과/미검증 근거는 Data/reports/pi-acceptance/report.md를 따른다. 아래는 앞으로 재검증할 때 사용하는 일반 절차다. 환경 수집 도구 자체는 인증·API·서비스를 시작하지 않는다.

```sh
cd /실제/PyTrading
.venv/bin/python Code/pi_validate.py --collect-only
.venv/bin/python Code/pi_validate.py
```

두 번째는 Data/device-validation의 격리 임시 원장에서 전체 자동 검증을 실행하고 환경 JSON·테스트 로그를 저장한다. Test와 Data/tests/fixtures의 공개 합성 입력을 함께 복사해야 한다. 원본 계좌·인증을 복사할 필요는 없다. 테스트용 Test 임시 폴더 쓰기 권한은 필요하며 서비스 자체는 Data만 쓰게 한다. Windows에서 도구를 실행한 결과는 Windows 검사로 표시한다. Linux 실행·ARM 실행·systemd 실행은 각각 별도 항목이다.

## 인증 없는 격리 systemd 시험

```sh
sh Deployment/raspberry-pi/validate-service.sh normal
systemctl status pytrading-validation
sudo systemctl restart pytrading-validation
sudo systemctl stop pytrading-validation
sh Deployment/raspberry-pi/validate-service.sh watchdog
journalctl -u pytrading-validation
```

기존 rule-trader와 다른 transient unit이며 합성 worker만 사용한다. 인증·주문·운용 계좌 접근과 디스크 채우기를 하지 않는다. watchdog 시험의 실패 종료는 기대 결과다. 실패한 transient unit이 남으면 상태·로그를 보존한 뒤 stop/reset-failed로 정리하고 재시험한다. 이 스크립트를 부팅 자동 시작 검증으로 해석하지 않는다.

## 실제 읽기 전용 daily 프로필

장비 정보·사용자·설치 경로·권한과 private 인증 파일 준비를 확인한 뒤 별도 Data 폴더를 지정한다.

```sh
export PYTRADING_SETTINGS=/실제/PyTrading/Config/settings-linux.json
export PYTRADING_DAILY_DIR=/실제/PyTrading/Data/device-validation/daily-observation
PYTRADING_PROFILE=daily sh Deployment/raspberry-pi/start.sh
```

Ctrl+C 정상 종료→다시 실행하여 대기 계획 복원과 중복 체결 방지를 확인한다. 같은 폴더로 두 번째 프로세스가 거부되는지 확인한다. 장전·정규장·장후 보고서와 정상 시세 수·누락·지연·중지 사유를 비교한다. 데이터 문제나 진입 창 상실을 신호 부재로 오해하지 않는다.

부팅 검증은 기존 rule-trader.service의 복사본 pytrading-daily-validation.service를 만든 뒤 실제 사용자·경로, daily 프로필과 위 격리 폴더 환경변수만 설정하여 수행한다. 기존 운용 unit을 덮어쓰지 않는다. enable 후 재부팅·시작·중지·재시작 로그를 보존하고 완료 후 검증 unit을 disable한다. 현재 장비에서는 사용자 허용 후 실제 재부팅까지 검증했다. 일반 배포에 재적용할 때는 대상 사용자·경로를 다시 확인한다.

통신 차단은 기기 전체 SSH를 끊기보다 격리 mock 오류 시험을 먼저 사용하고, 실제 연결 시험은 복구 접속 경로가 있을 때 제한적으로 수행한다. 지연·공간 경계·백업 복구는 테스트의 주입/모의 파일시스템으로 검사하며 기기 전체 저장 공간을 채우지 않는다. 실제 공간은 operations.json free_bytes로 확인한다.

## 수집할 근거

environment.json, offline-tests.txt, 격리 unit의 systemctl show/status·journalctl·부팅 ID, 격리 Data의 operations.json·observation-ledger.sqlite·daily 보고서를 보관한다. 인증 파일·cache의 토큰·계좌번호·환경변수 전체는 결과 묶음에 넣지 않는다. 관측 원장은 먼저 서비스를 중지하고 SQLite backup API로 복사한다. 복구 뒤 PAUSE_BUYS와 재시작 대조를 확인한다.

현재까지 확보한 ARM 휠의 제공 여부와 실제 Linux/ARM 실행은 별개다. 이 도구가 미래 기기에서 실행된 결과 파일이 생기기 전에는 실기기 통과라고 보고하지 않는다.
