# 기능별 테스트 방법

프로젝트 루트에서 CMD로 실행한다. 실행 파일은 main.py 하나이며 --test만 테스트 옵션으로 사용한다.
PowerShell이나 테스트용 실제 인증키는 필요 없다.

## 자동 검증

```cmd
python main.py --test
```

기능 직접 실행 메뉴가 열린다. 7번은 과거 분봉, 8번은 반복 일봉 연구, 9번은 지표, 10번은 사업군,
11번은 조건 분석, 12번은 포트폴리오, 13번은 순차 선택, 14번은 엄격 순차 선택,
15번은 인버스 방어 탐색, 16번은 장기 평가, 17번은 매도 보호 비교, 18번은 자동 검증이다.
바로 자동 검증하려면 --test 뒤에 unit-기능 이름을 지정한다.

| 실행 명령 | 검증 내용 | 현재 개수 |
| --- | --- | ---: |
| `python main.py --test unit-news` | 한·영 분류, RSS 출처, 회사·사건·시각·추측 필터, 캐시 갱신, 검토·정정 | 23 |
| `python main.py --test unit-broker` | 가짜 인증값, 오류 메시지, env 파일 형식, 1분→5분봉, 거래 시간·휴장 | 21 |
| `python main.py --test unit-strategy` | 매수 조건, 손절·악재·추적 손절·원가 보호·이익 보호, 미래 정보·입력 오류 차단 | 24 |
| `python main.py --test unit-paper` | 가상 예산, 수수료·슬리피지, 보호 매도·현금 보존, 복원·중복 방지 | 13 |
| `python main.py --test unit-settings` | 설정 검사, OS 잠금, 별도 프로세스 강제 종료 후 잠금 해제 | 5 |
| `python main.py --test unit-runner` | 무인 지속 실행, 인증 재시도, 뉴스 오류 중 손절, 재생·정상 종료, 확인 도구 | 20 |
| `python main.py --test unit-research` | 체결·비용·기간 분리·지표·사업군·차단·공동 자금·순차 선택·장기 연도별 성과·고가 선행 사용 차단 | 63 |
| `python main.py --test all` | 위 기능 전체 | 169 |

통과하면 마지막에 `OK`, 실패하면 실패한 테스트 이름과 원인이 나온다. 실패 시 종료 코드는 1이다.
자동 테스트는 합성 입력과 모의 응답을 사용하며 인터넷·실제 계좌·주문 API를 호출하지 않는다.
테스트 임시 파일은 별도 폴더에 만들고 정상 종료 시 제거한다.

## 뉴스 실제 수집만 확인

```cmd
python main.py --test news
```

../Config/settings.json의 종목과 ../Config/news-queries.json의 검색어로 공개 Google News RSS를 요청한다.
허용 출처로 검색을 좁히고 종목별 수집·선정·제외 개수와 이유를 출력한다.
선정 후보는 `../Data/tests/results/live-news.json`, 전체 설명·링크는 `live-news-report.json`에 저장한다.
실제 실행의 뉴스·계좌 상태를 바꾸지 않는다. 선정 0건은 기준을 통과한 기사가 없다는 뜻이다.
실패는 오류 메시지와 종료 코드 1로 구분한다. [선별 기준](NEWS_FILTER.md)을 참고한다.
이 테스트는 수집 경로 확인이며 본문이나 호재·악재 판정 정확도를 검증하지 않는다.

## 토스 인증·시세 연결만 확인

```cmd
python main.py --test broker
```

지정한 env 파일을 읽어 인증하고 종목별 거래 시간·호가·완성 봉 개수를 확인한다.
같은 키를 쓰는 `python main.py` 실행은 먼저 종료한다. 토스 토큰 재발급이 다른 실행에 영향을 줄 수 있다.
휴장 중에는 휴장 메시지가 정상이며, 호가·캔들 검증은 거래 시간에 다시 해야 한다.
실제 계좌 보유 조회·주문·모의 계좌 변경은 수행하지 않는다. 인증값·토큰은 출력하지 않는다.

## 합성 시세로 전체 매매 흐름 확인

```cmd
python main.py --test paper
```

실제 연결 없이 각 시장에서 BUY→HOLD→SELL(stop_loss)→WAIT 순서를 확인한다.
결과는 매번 `../Data/tests/results/replay-날짜-시각/`의 새 폴더에 저장한다.
매 단계의 현금·보유 종목·평가액·실현 손익과 저장 계좌 복원 결과를 출력한다.
account.json·decisions.jsonl·summary.md를 확인한다. 실제 실행 계좌와 결과가 섞이지 않는다.
입력은 `../Data/tests/fixtures/demo_replay.json`, 공통 단위 테스트 입력은 `tests/sample_data.py`다.
이 결과는 체결·비용·상태 동작 확인이며 실제 전략 성과가 아니다.

matplotlib가 설치돼 있으면 프로젝트 루트에서 결과 그래프를 선택적으로 생성할 수 있다.

```cmd
python -B -X utf8 -m tools.plot_results "../Data/tests/results/확인할_결과폴더"
```

## 판단 기능만 직접 실행

```cmd
python main.py --test strategy
```

합성 입력으로 돌파·거래량 조건, 거래량 부족, 보유 유지, 가격 하락 사례를 실행한다.
시장별 BUY/WAIT/HOLD/SELL과 이유·조건 통과 여부·계산값을 보여준다.
설정의 strategy_config가 있으면 적용한다. 결과는 ../Data/tests/results/strategy.json에 저장한다.
원래 입력과 가상 계좌·실제 실행 계좌는 변경하지 않는다.
기본 설정에서는 BUY→WAIT→HOLD→SELL이며 전략값을 바꾸면 결과도 달라질 수 있다.

## 설정 기능만 직접 실행

```cmd
python main.py --test settings
```

종목·주기·파일 경로가 실제로 어떻게 해석되는지 표시한다.
인증 파일의 존재 여부만 확인하며 인증값은 읽거나 출력하지 않는다.

## 전체 연결을 한 번만 실행

```cmd
python main.py --test runner
```

현재 설정으로 토스 실제 시세·검토된 사건·판단·모의 계좌·뉴스 수집을 한 주기 실행한 뒤 종료한다.
인증 파일과 인터넷이 필요하다. 동일 키를 쓰는 지속 실행은 먼저 종료한다.
계좌·뉴스·판단 결과는 ../Data/tests/results/once-날짜-시각의 별도 폴더에 저장한다.
지속 실행 계좌와 보유 상태를 읽거나 변경하지 않는다. 실제 주문은 제출하지 않는다.
휴장 중이면 WAIT이며 새로운 모의 계좌로 시작하므로 실제 보유에 대한 판단이 아니다.

## 개발 순서

수정할 기능의 자동 테스트 → 전체 자동 테스트 → 필요한 기능의 실제 연결 확인 → 지속 실행 순서로 진행한다.
외부 연결 확인은 자동 테스트와 구분해 수동으로 실행한다.
라즈베리파이 이식은 Windows에서 이 흐름을 확인한 뒤 진행한다.
