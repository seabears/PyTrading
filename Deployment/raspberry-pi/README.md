# Raspberry Pi OS 64비트 내부 모의 운용

현재 장비는 pytrading-pi(Raspberry Pi 5 약 8GB, Debian 13.4 aarch64, Python 3.13.5)로 확인했다. 실제 접속·설치 경로와 운영 명령은 Docs/PI_DEVICE.md를 따른다. 아래 trader·/opt/PyTrading은 일반 배포 예시다.

지원 범위는 CPython 3.11~3.13이다. Windows 3.12.6과 실제 ARM Linux 3.13.5에서 전체 541개를 통과했다. CPython 3.11 ARM64 휠 제공 확인은 실행 검사와 구분한다. 실제 재부팅·systemd·watchdog 검증 범위는 Data/reports/pi-acceptance/report.md를 따른다.

## 복사와 수동 실행

Code·Config·Deployment·Test·Docs를 복사하고 필요한 기존 Data는 서비스 종료 후 백업해 별도로 복사한다. 새 빈 가상 계좌로 시작할지 기존 내부 계좌를 이어받을지 명시적으로 결정한다. 실행 중인 상태 파일을 동시에 복사하지 않는다. 인증은 Git에 넣지 않고 별도 복사한다.

```sh
cd /opt/PyTrading
uname -m
python3 --version
PYTHON=python3 sh Deployment/raspberry-pi/setup.sh
mkdir -p Data Credentials
chmod 700 Credentials
chmod 600 Credentials/kis-market.env
.venv/bin/python Code/main.py --test all
sh Deployment/raspberry-pi/start.sh
```

모든 자동 테스트는 합성·오프라인이다. Linux에서 처음에는 위 검사를 실행하고 달력·잠금·fsync·정상 종료를 확인한다. research 그래프가 필요하면 `.venv/bin/python -m pip install -r Deployment/requirements-research.txt`를 추가한다.

Config/settings-linux.json은 Code 기준 ../Credentials/kis-market.env를 사용한다. Windows settings.json을 수정하지 않는다. 서비스 프로필은 earnings(기본), price(기존 단기 연구), daily(고정 일봉 모의)이며 모두 내부 가상 계좌다.

```sh
PYTRADING_PROFILE=daily sh Deployment/raspberry-pi/start.sh
.venv/bin/python Code/operations.py status daily
```

## 서비스 등록과 수동 시작

rule-trader.service의 User·WorkingDirectory·ExecStart·PYTRADING_SETTINGS·ReadWritePaths를 실제 값으로 바꾼다. Data는 해당 사용자에게만 쓰기 권한을 부여한다. 인증은 읽기만 가능하게 한다. 수동 실행을 먼저 종료한다.

```sh
sudo cp Deployment/raspberry-pi/rule-trader.service /etc/systemd/system/rule-trader.service
sudo systemctl daemon-reload
sudo systemctl start rule-trader
systemctl status rule-trader
journalctl -u rule-trader -f
sudo systemctl stop rule-trader
```

Type=notify/WatchdogSec=180으로 처리 진행이 멈추면 재시작 대상이 된다. 20초 뒤 재시작하며 10분 내 실패 시작 3회를 넘으면 중지해 오류를 확인해야 한다. SIGTERM은 상태 저장 경로를 마친 뒤 정상 종료한다. OS 실행 잠금 때문에 같은 내부 계좌를 두 프로세스가 변경할 수 없다. 비정상 종료 후 run.lock을 삭제할 필요가 없다.

journald.conf.example은 시스템 전체 로그 설정 예시다. 다른 서비스에도 영향을 주므로 필요할 때 관리자가 검토해 별도 drop-in으로 적용한다. 내부 파일 로그 회전·공간 감지·복구·매수 중지는 Docs/OPERATIONS_RUNBOOK.md를 따른다.

실기기 수용 검사는 최소한 재부팅 자동 시작, 인터넷 차단/복구, 인증 만료, 디스크 여유 경계, 서비스 중지/재시작, 두 프로세스 잠금, 장전→정규장→조기 종료, 관측 지연/저장 복구를 기록해야 한다. 시험을 위해 실제 계좌를 손상시키지 말고 별도 내부 계좌와 파일시스템 시험 환경을 사용한다.


격리 장애·부팅 검증과 결과 수집은 Docs/PI_ACCEPTANCE.md를 따른다. PYTRADING_DAILY_DIR로 기존 계좌와 분리한다.


부팅 자동 시작은 기본 비활성이다. 서비스 등록이나 수동 시작만으로 enable하지 않는다. 사용자가 별도로 요청한 경우에만 `sudo systemctl enable rule-trader`로 등록한다. 현재 장비의 실제 서비스 이름은 `pytrading-daily-validation`이며 부팅 시작은 disabled다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
