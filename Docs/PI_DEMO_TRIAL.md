# Raspberry Pi 한정 모의시험 수동 실행

준비 확인: 2026-11-02T12:37:10.439732+00:00. 설치 `/home/trader/PyTrading-demo/20261102-123527`, 장치 pytrading-pi, 사용자 trader, aarch64 Python3.13.5.

## 실행

Windows CMD에서 연결한다.

```cmd
ssh pytrading-pi
```

Pi의 Linux 셸에서 오늘 2026-11-02 **23:30 KST 이후** 다음을 실행한다.

```sh
~/CMD/kis-demo-run.sh
```

이 명령은 실제 KIS 모의 서버 주문 시험을 시작한다. 정규장 시세를30종목 각각10분·전체3회 이상 확인한 뒤 최신 계좌/위험 대조를 통과해야 주문한다. 장외에서는 주문 없이 종료한다. AAPL1주/동시1주/비용예약 포함 총매수500 USD/매수시도2회/활성10분/지정가 한도다. 첫 체결 뒤 추가매수는 중지하고 확인된 자기 보유만 매도한다. 실계좌 주문은 차단한다.

조회만 실행하거나 결과만 확인하려면 다음을 사용한다.

```sh
~/CMD/kis-demo-check.sh
~/CMD/kis-demo-results.sh
```

조회 검사는 주문·정정·취소를 전송하지 않는다. 조회/주문시험 실행 중에는 공통 OS 잠금으로 두 번째 실행을 거절한다. 결과 확인도 잠금을 공유한다. 실행은 SSH 창을 열어둔 채 수동으로 진행한다. SSH 단절·Ctrl+C·오류 후에는 미체결/잔여보유가 정리됐다고 추정하지 말고 결과 및 계좌를 대조한 뒤 재실행한다. 자동 재시작·무인 반복·부팅 등록은 없다.

## 결과 경로

- 주문 시험: `/home/trader/PyTrading-demo/20261102-123527/Data/reports/kis-demo-session/<실행폴더>/result.json`
- 실제 시세: `/home/trader/PyTrading-demo/20261102-123527/Data/reports/demo-today-quotes/<실행폴더>`
- 읽기 전용: `/home/trader/PyTrading-demo/20261102-123527/Data/reports/kis-demo-balance/<실행폴더>/results.json`
- 전용 SQLite: `/home/trader/PyTrading-demo/20261102-123527/Data/execution` 아래. 기존 운영 계좌 원장을 복사하지 않았다.

코드의 종료 상태 completed만으로 가정하지 말고 미체결/잔여보유/최종 비용·현금 대조를 확인한다. 최종 비용이 미확정이면 review_required를 유지한다. 결과 파일에는 원문 인증을 넣지 않는다. 인증은 이 설치의 Credentials에 권한600, 폴더700으로 보관하고 시세prod와 계좌vps를 분리한다.

## 실제 확인 범위

이 설치에서 전체 자동검사801통과, Linux경로 검사·쉘 문법·장외 차단·읽기 전용 계좌조회·결과조회·중복잠금 검사 통과. 실제 모의계좌 원장 연결/한정 후보 판정 통과. Pi에서 별도prod AAPL호가GET 성공. 실제 정규장 연속 관측과 실제 주문/체결은 아직 미실행이다.

첫 전체 검사에서는 PYTRADING_SETTINGS 환경변수 때문에 기본 settings.json 비교 테스트1개가 실패했다. 기본 전체검사는 환경변수를 제거해801개 통과했고, Linux 설정 선택은 별도 실경로 검사와 실제 조회로 확인했다. 실패 로그를 보존했다. 검사를 삭제하거나 기대값을 바꾸지 않았다.

기존 운영 설치와 서비스는 변경하지 않았다. 이번 조회 시 기존 서비스 inactive/dead, MainPID0, 부팅disabled다. 기존 repeated_collection_errors 중지와 운영Data/인증/전략/위험한도는 유지한다. Windows와 Pi의 Code/Config/Test274파일이 직전검사소스와 일치한다. 이번 추가분은 Deployment/raspberry-pi/demo-session.sh와 홈CMD 실행파일 및 문서다.

## 복구와 보존

전용 설치이므로 운영 서비스에 롤백할 변경은 없다. 실행 파일이 잘못되면 사용을 중지하고 경로를 검토한다. 원장을 초기화하거나 다른 새 설치에서 자동 재시도하지 않는다. 체결/미체결이 있으면 같은 계좌 전체 이력을 먼저 조회한다. 원장 백업은 기존 SQLite backup 도구를 사용하고 활성 원장을 덮어쓰지 않는다. 인증 복사 전 시험 설치 안의 사본은 Credentials/.before-current-copy에 비공개 보존했다. 기존 운영 인증은 건드리지 않았다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
