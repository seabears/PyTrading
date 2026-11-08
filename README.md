> 현재 내부 모의 운용·라즈베리파이·주문 차단 상태는 [현황](Docs/OPERATIONS_STATUS.md), [실행·복구](Docs/OPERATIONS_RUNBOOK.md), [배포](Deployment/raspberry-pi/README.md)를 참고하세요. 실계좌 주문은 전송하지 않습니다.

# 주식·채권·ETF만 허용

ETN과 나머지 상품은 불허한다. 공유 API도 종목 종류를 확인하며 미확인 종목을 차단한다.
[현재 허용 상품과 API 상태](Docs/KIS_API_SUMMARY.md).

# 선물·옵션·ELW: 코드 보존, 사용 불허

구현 330개 중 허용 226개·불허 104개. 선물·옵션·ELW 전송·구독을 차단한다.
[현재 API 상태](Docs/KIS_API_SUMMARY.md), [함수별 허용 여부](Docs/KIS_API_CATALOG.md).

# 대출 기능 제거

대출·신용·담보대출·대주 전용 API 8개를 제거했다. 공용 주문도 현금 거래만 허용한다.
현재 API는 330개다. [현금 거래 제한 안내](Docs/KIS_API.md), [현재 함수 목록](Docs/KIS_API_CATALOG.md).

# KIS 상품 API 추가

공식 예제·포털 대조를 통한 338개 요청 함수와 REST·실시간 전송부를 추가했다.
[사용·수정 안내](Docs/KIS_API.md), [전체 함수 목록](Docs/KIS_API_CATALOG.md).
`python Code/main.py --test api`로 인증 없이 검사하고,
`python Code/main.py --test api-live`로 미국 시세만 실제 확인한다.
주문 전송은 기본 차단이며 기존 자동매매 실행에 연결하지 않았다.

# 기본 연결: KIS

현재 실행: `python Code/main.py`. [KIS 인증·설정 안내](Docs/KIS_SETUP.md)를 먼저 확인하세요.
아래 토스 설명은 이전 연결 참고 자료입니다.

## 현재 종목과 새 데이터 (2026-10-22)

현재 실행은 요청한 미국 30종목이다. 알파벳은 GOOGL, 샌디스크는 SNDK다.
종목 목록은 Config/settings.json의 symbols, 거래소는 Config/kis.json에서 수정한다.
뉴스는 꺼져 있고 실제 주문 없이 내부 모의매매만 한다.

새 시세 수집: `python Code/main.py --test history`.
Data/history/daily와 minute에 KIS 시세를 저장한다. 시장 비교용 SPY는 매매 종목에 포함하지 않는다.
[새 데이터 사용 안내](Docs/DATA_REFRESH.md), [실제 수집·품질 보고서](Data/reports/data-refresh/report.md).
`--test strategies`를 새 KIS 자료와 연결했다. 아래의 17종목·뉴스·토스 연구 설명은 이전 구성이다.

# 현재 실행 위치

프로젝트 루트에서 `python Code/main.py`, 기능 선택은 `python Code/main.py --test`로 실행합니다.
폴더별 역할은 [폴더 구조](Docs/FOLDER_LAYOUT.md)를 참고하세요.
아래 `python main.py` 예시는 Code 폴더 안에서 실행하는 명령입니다.

# PyTrading: 국내·미국 룰 기반 모의매매

Windows에서 기능을 만들고 검증한 후 라즈베리파이로 옮기는 프로젝트다.
Python 3.9 이상, 표준 라이브러리만으로 실행한다. 딥러닝·LLM·실제 주문 기능은 없다.
설명 가능한 규칙과 한국어 주석, 사용자가 수정하기 쉬운 코드 구성을 우선한다.

## Windows 실행

CMD에서 실행한다. `Config/settings.json`은 프로젝트의 `Credentials/kis.env`를 기본으로 사용한다. 다른 위치의 파일은 아래 로컬 설정 방법으로 연결한다.
인증값 자체를 설정 JSON이나 코드에 복사하지 않는다.

```cmd
cd /d "C:\Projects\PyTrading\Code"
python main.py
```

인자 없이 계속 판단한다. 관찰 대상은 `../Config/settings.json`의 17개 종목이며, 전체 시세 검사 후 60초 대기,
뉴스 수집 간격은 600초다. Ctrl+C로 종료하며 다음 실행은 기존 모의 계좌를 복원한다.
휴장 중에는 WAIT가 정상이다. 뉴스 원문을 검토해 사건으로 등록하기 전에는 신규 모의 매수가 없다.

삼성전자·SK하이닉스·LG전자·마이크론·Apple·HP·Dell·Sony·Arm·엔비디아·
알파벳 GOOG/GOOGL·아마존·메타·마이크로소프트·테슬라·SpaceX가 설정돼 있다.
알파벳 두 주식 종류는 각각 판단한다. 뉴스 검색어와 회사 이름 필터도 전 종목에 설정했다.
관찰 17종목이 모두 매수되는 것은 아니다. 기존 조건과 시장별 최대 5종목 보유 제한을 적용한다.
종목 추가·삭제는 `../Config/settings.json`의 symbols를 수정하고 재시작한다.
뉴스 수집도 추가하려면 `../Config/news-queries.json`과 `../Config/news-filter.json`의 company_aliases를 함께 수정한다.

## 폴더 구조

```text
PyTrading/
  Code/
    main.py                   지속 실행·--test 진입점
    ../Config/                   종목·전략·실행 설정
                          뉴스·증권사·판단·모의 계좌·실행 코드
    tools/                    기능 실행·연구·그래프 도구
    tests/                    기능별 자동 테스트 코드
    Docs/                     사용·개발 안내
    ../Deployment/               라즈베리파이 서비스 예시
    ../Credentials/              로컬 인증 파일 보관 (Git 제외)
  Data/
    history/                  실제 시세·지표·캐시
    paper/                    모의 계좌·뉴스·판단·손익
    confirmed-events.json     검토된 확정 뉴스
    tests/fixtures/           기능 실행용 합성 입력
    tests/results/            테스트·연구 결과·그래프
    reports/                  이전·구조 변경 검증 보고서
    cache/plots/              그래프 캐시
```

Windows 개발 중 라즈베리파이 서비스 파일을 실행할 필요는 없다.
실제 인증 파일·계좌 기록을 테스트 입력으로 사용하지 않는다.

## 기능별 직접 실행

```cmd
python main.py --test
```

메뉴의 1~17번은 기능을 직접 실행하고 입력·결과를 보여준다. 9번은 지표, 10번은 사업군,
11번은 조건 분석, 12~15번은 포트폴리오·순차 선택·방어 탐색, 16번은 장기 평가, 17번은 매도 보호 비교다. 18번은 자동 검증이다.

`python main.py --test indicators`로 코스피·SPY·VIX·한국 3년 국채를 실제 수집해
기존 일봉 규칙에 추가했을 때의 차이를 확인한다. [지표 연구 안내](Docs/INDICATORS.md)를 참고한다.

`python main.py --test peers`로 설정된 17개 종목 중 상장일·자료 기준을 통과한 종목에
고정 규칙을 비교 적용한다. 회사 목록은 `../Config/peers.json`, [비교 방법](Docs/PEERS.md)에 있다.

`python main.py --test diagnostics`로 진입 차단·손실 청산을 보고서로 만들고 7개 조건의
효과를 비교한다. [조건 분석 안내](Docs/DIAGNOSTICS.md)를 참고한다.

| 실행 명령 | 실행 내용 |
| --- | --- |
| `python main.py --test news` | 실제 뉴스 수집·제목 후보 분류, 결과 파일 저장 |
| `python main.py --test broker` | 토스 인증·시세 한 번 조회. 인증 파일 필요 |
| `python main.py --test strategy` | 합성 시세로 판단만 실행. 조건 통과 여부·계산값 표시 |
| `python main.py --test paper` | 합성 체결로 모의 계좌 실행. 현금·보유·손익·복원 표시 |
| `python main.py --test settings` | 설정 로드·경로 해석 결과 표시. 인증값은 읽지 않음 |
| `python main.py --test runner` | 실제 시세·뉴스·판단을 한 주기만 연결. 별도 모의 계좌 사용 |
| `python main.py --test backtest` | 실제 과거 분봉 수집·가격 거래량 규칙 24개 비교·기간 분리 모의매매 |
| `python main.py --test research` | 별도 3년 일봉에서 3단계 수정·검증 반복, 규칙 고정 후 역사 시험 |

기능 실행 결과는 ../Data/tests/results에 저장하며 지속 실행 계좌와 분리한다.
토스나 전체 연결 실행 전에는 같은 인증키를 쓰는 지속 실행을 종료한다.
strategy·paper는 합성 데이터이며 실제 투자 성과가 아니다. 실제 주문은 제출하지 않는다.

## 자동 검증

직접 실행과 예상 결과를 비교하는 자동 검증은 구분한다.

```cmd
python main.py --test all
python main.py --test unit-news
```

all은 전체 자동 검증, unit-뉴스/기능 이름은 해당 기능의 자동 검증이다.
예: unit-broker, unit-strategy, unit-paper, unit-settings, unit-runner.
과거 모의매매 자동 검증은 unit-research다. 메뉴의 18번에서도 자동 검증을 선택한다.
자동 검증은 인터넷·실제 인증키를 사용하지 않는다.

상세 입력·결과·저장 위치는 [기능 실행·검증 안내](Docs/TESTING.md),
확인된 결과와 미검증 범위·그래프는 [검증 기록](Docs/VALIDATION.md)에 있다.
실제 과거 시세 연구의 기준과 한계는 [과거 모의매매 안내](Docs/BACKTEST.md)에 있다.
반복 연구의 단계·기록·한계는 [반복 수정·검증 안내](Docs/RESEARCH_CYCLES.md)에 있다.

## 코드 수정 위치

| 바꿀 내용 | 파일·함수 |
| --- | --- |
| 뉴스 검색·제목 후보 분류 | `news/collector.py`: NEWS_QUERIES, CANDIDATE_RULES |
| 뉴스 출처·회사 이름·사건 선별 | `../Config/news-filter.json`, `news/filtering.py` |
| 검토 사건 등록 | `news/review.py`: approve_candidate |
| 토스 시세·5분봉 합성 | `broker/toss.py`: collect_snapshot, aggregate_five_minute_bars |
| 전략 기본값·매수 조건·매도 순서 | `strategy/engine.py`: DEFAULT_CONFIG, build_entry_conditions, evaluate |
| 모의 체결·비용·계좌 상태 | `trading/paper.py`: PaperAccount |
| 전체 반복 흐름·기록 | `app/runner.py`: main, record_decision |
| 설정 검사·실행 잠금 | `app/runtime.py` |

수정한 기능의 테스트부터 실행하고 전체 테스트로 연결을 확인한다.
전략값은 settings.json의 strategy_config에 별도 JSON 경로를 지정해 기본값을 덮어쓸 수도 있다.
설정의 상대 경로는 **프로젝트 루트 기준**이며 변경 후 재시작한다.
기존 모의 계좌의 자금·비용 설정을 바꾸려면 output_dir을 새 폴더로 지정한다.

## 뉴스와 판단 흐름

Google News RSS에서 허용 출처로 검색 범위를 좁힌 뒤 종목별 결과를 최대 50개 가져온다.
출처 도메인·언론사 이름, 회사 이름, 최근 발행 시각, 사건 종류를 검사한다.
추측·주가 전망·단순 지분 변동 기사를 제외하고 선정 후보만 저장한다.
전체 선정·제외 이유도 보고서에 남긴다. [뉴스 선별 기준](Docs/NEWS_FILTER.md)을 참고한다.
저장 대상은 제목·언론사·기사 링크·발행 시각·최초 발견 시각이며 본문 자동 검증은 없다.
제목 키워드는 실적 전망·계약·자사주·회계 문제의 **후보**만 분류한다.
사람이 원문을 확인하고 등록한 사건만 매매 근거로 사용한다.

```cmd
python -m src.news.review
```

원문을 직접 검토한 경우에만 실제 후보 ID·원문 주소·검토 메모로 등록한다.

```cmd
python -m src.news.review --candidate-id "후보_ID" --kind earnings_guidance_raised --evidence-url "https://원문주소" --note "해당 회사 공식 발표에서 실적 전망 상향 확인"
```

매매 판단은 확정 긍정 사건, 완성 5분봉의 과거 20봉 최고가 돌파, 거래량 2배,
호가 차이·추격 가격 한도·투자 예산·중복 진입 조건을 함께 검사한다.
보유 중에는 손절·추적 손절·원가 보호·이익 보호를 먼저 검사하고 확정 악재·평균가격 이탈을 검사한다.
비용 차감 고점 수익 3%부터 원가 보호, 5%부터 고점 순이익 50% 보호가 켜진다.
설정은 `../Config/strategy.json`, 계산·비교 방법은 [매도 보호 안내](Docs/EXITS.md)에 있다.
`python main.py --test exits`로 기존 장기 자료에서 매도 조건을 비교한다. 보호 가격보다 낮게 체결될 수 있다.
수치와 사건 분류는 초기 가설이며 실제 수익성이 검증된 기준이 아니다.
등록 시각부터 사건을 사용하며 과거 관찰 일지에 현재 뉴스를 소급 적용하지 않는다.

`../Data/paper/account.json`은 가상 자금·보유·거래의 기준 기록이다.
`decisions.jsonl`에는 당시 입력·판단·계좌 평가액, `summary.md`에는 시장별 현황이 있다.
KRW와 USD를 합산하거나 실제 계좌에서 자금을 읽지 않는다.
체결은 신호 시점 호가에 가정한 비용·슬리피지를 반영하며 주문 지연·부분 체결은 재현하지 않는다.
`run.lock`은 종료 후에도 남고 OS 잠금만 해제되므로 실행 중 삭제하지 않는다.

## 이후 라즈베리파이 이식

Windows 검증 후 폴더 전체를 옮기고 env_file 경로를 라즈베리파이에 맞게 수정한다.
[이식 안내](../Deployment/raspberry-pi/README.md)에 실행·자동 시작 방법을 정리했다.
토스 허용 IP는 실제 실행 장치의 네트워크 공인 IP와 일치해야 한다.

공식 API 자료: [토스 개발자 문서](https://developers.tossinvest.com/).
다운로드한 API 문서 사본과 PowerShell 실행 도우미는 제거했다.

코드와 데이터 위치는 [폴더 분리 안내](Docs/DATA_LAYOUT.md)를 참고한다. Code와 Data를 함께 보관·이식한다.


## 현재 운용 엔진으로 백테스트

`python Code/main.py --test engine-backtest`로 저장 KIS 분봉을 공동 계좌에 재생합니다.
실행·가정·결과 읽는 법은 [운용 엔진 백테스트](Docs/ENGINE_BACKTEST.md)를 참고하세요.


## 다양한 알고리즘 실험

`python Code/main.py --test algorithms`로 12개 고정 일봉 가설을 72회 비교하고 누적 기록합니다.
[실행·수정·기록 안내](Docs/ALGORITHM_STUDY.md), [연구 일지](Docs/RESEARCH_LOG.md).


## 한 항목씩 조정하는 추가 실험

`python Code/main.py --test refinements`로 주변 설정을 비교합니다.
[조정 범위·선정·기록 안내](Docs/ALGORITHM_REFINEMENTS.md). 기존 운용 설정은 변경하지 않습니다.


## 동종 산업군 확장

`python Code/main.py --test industry-history`로 시세를 누적하고, `--test industry-peers`와 `--test industry-continuous`로 비교합니다.
[수집·설정·기록 안내](Docs/INDUSTRY_STUDY.md).

매수 타이밍 연구: [실행·측정 방식](Docs/ENTRY_TIMING.md), [최신 보고서와 그래프](Data/reports/entry-timing/report.md).

## 인증 파일과 로컬 설정

- `Credentials/`에 시세용 `kis.env`(Windows) 또는 `kis-market.env`(Pi), 모의계좌용 `kis_demo.env`를 각각 보관한다.
- 각 파일에는 `APP_KEY`와 `APP_SECRET`을 설정한다. 계좌 조회가 필요한 파일에는 `ACC_NO`도 설정한다. 실제 값은 로컬 파일에만 입력한다.
- 기존 외부 경로를 계속 사용하려면 `Config/settings.json`의 복사본을 `Credentials/settings-windows.local.json`에 두고 복사본의 `env_file`을 수정한다. 다른 상대 경로는 기존과 동일하게 `Code/` 기준이다.
- 모의계좌 조회 도구는 `--env-file`로 모의 인증 파일을 지정할 수 있다. Pi 연결 도구는 `PYTRADING_PI_HOST` 또는 로컬 SSH 설정의 `pytrading-pi` 별칭을 사용한다.

프로젝트 루트의 CMD에서 로컬 설정을 지정해 실행한다.

```cmd
set "PYTRADING_SETTINGS=%CD%\Credentials\settings-windows.local.json"
python Code\main.py
```
