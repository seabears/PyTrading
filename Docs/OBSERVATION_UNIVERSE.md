# 사용자 지정과 일별 자동 관찰 목록

기존 30종목은 현재 실행 설정 파일의 `symbols`에 그대로 보존한다. 이것이 **사용자 지정 목록**이다. 자동 검색 결과로 이 목록을 고치거나 삭제하지 않는다. Windows 기본 파일은 `Config/settings.json`이고 Pi에서 `PYTRADING_SETTINGS`를 지정했다면 해당 파일의 목록이 사용자 지정 목록이다.

## 추가·제외와 관리 전용 목록

매 미국 완료 거래일마다 공식 KIS 마스터와 거래대금 순위에서 새로운 후보를 찾는다. 일봉·시총·실제 호가 조건을 모두 통과하면 자동 목록에 추가하고, 다음 평가에서 미달·미확인·검색 범위 이탈이면 제외한다. 최대 300종목이며 같은 종목은 사용자 목록과 중복 관찰하지 않는다.

최종 관찰 대상은 **사용자 지정 + 당일 유효 자동 선정 + 보유·대기 계획·활성 주문의 관리 대상**이다. 자동 목록에서 빠졌다는 이유로 보유를 강제 매도하거나 잔고를 삭제하지 않는다. 보유의 기존 손절·전략 매도는 계속 검사한다. 제외된 종목의 신규 매수 계획은 무효화하고 자기 전략의 확인된 미체결 매수는 기존 안전한 취소 절차로 넘긴다. 확인되지 않은 주문을 임의로 취소하지 않는다.

일별 검색 실패·상태 손상·정책 변경·유효기간 만료 때 자동 종목은 신규 진입 대상에서 제외한다. 사용자 지정과 보유 관리, 기존 손실 제한과 수동 중지는 그대로 유지한다. 제외는 상품 확인 원본·일지·기존 계좌를 지우는 기능이 아니다.

## 기본 조건과 단위

`Config/universe.json`에서 설정한다. `enabled=false`이면 자동 선정만 중지하며 사용자 지정·기존 보유 관리는 유지한다. 설정 변경은 프로세스를 다시 시작할 때 읽는다.

|설정|기본값|의미|
|---|---:|---|
|minimum_price_usd|5|확정 종가 USD|
|minimum_market_cap_usd|2,000,000,000|공식 상장주수 shar × USD 현재가 last 계산값|
|minimum_turnover20_usd|20,000,000|20봉 종가×거래량 중앙값 근삿값|
|minimum_turnover5_usd|5,000,000|최근 5봉 각각의 종가×거래량 최소값|
|maximum_atr_ratio|0.08|기존 계산과 같은 14개 true range 단순평균/종가|
|maximum_spread_ratio|0.002|정규장 실제 호가 스프레드 중앙값 0.2% 이하|
|minimum_spread_samples|20|동일 정규장의 서로 다른 신선한 원천 호가 최소 표본|
|spread_sample_seconds|60|표본 간 최소 관측 간격(초)|
|maximum_auto_symbols|300|통과 종목을 20봉 거래대금 중앙값으로 정렬한 상한|
|ranking_per_exchange|300|거래소별 순위 검색 상한, 실제 수신 범위가 더 작을 수 있음|
|maximum_ranking_pages|5|키가 제공될 때만 허용되는 최대 조회 페이지|
|request_interval_seconds|1|별도 읽기 전용 수집기의 요청 간격(초)|
|retry_seconds|300|검색 실패 후 재시도 간격(초)|

최근 거래소 달력 60거래일 중 59개 이상 정상 일봉과 최신 완료 일봉이 필요하다. 거래 가능한 USD 주식(type=2)만 자동 후보로 등록한다. ETF·ETN·파생상품·상품 종류 미확인은 자동 검색에서 제외하며 기존 상품 금지 정책은 유지한다. 수정주가와 실시간 기준 종가 차이가 20%를 넘으면 기업행동/가격 불일치 검토로 제외한다. 이 검사는 기업행동 원인을 확정하거나 수량·원가를 자동 정정하지 않는다.

시총의 `tomv` 단위를 추측하지 않는다. `shar`×`last`는 상장 주식 기준 계산값이며 특히 ADR/복수 종류 주식의 발행사 전체 시총과 다를 수 있다. 거래대금도 실제 체결 금액 합계가 아닌 수정 종가×거래량 근삿값이다.

## 실제 검색 범위와 최초 준비 시간

NYSE·NASDAQ·NYSE American의 KIS 거래대금 순위(20일 조건)에서 최대 지정 범위를 읽은 뒤 공식 마스터와 교차한다. **미국 전체 상장 종목을 매일 전수 검사하는 것은 아니다.** 2026-11-05 실제 응답에서는 거래소별 100행과 `tr_cont=F`가 왔지만 다음 KEYB가 없었다. 이 경우 키를 임의로 만들거나 같은 페이지를 반복하지 않고 수신 범위만 사용하며 `next_cursor_not_provided`, `all_pages_reached=false`를 기록한다.

실제 첫 연결 검사에서는 공식 USD 주식 분류 6,222개, 거래소별 순위 100행, 사용자 지정·비주식 제외 후 후보 159개를 확인했다. 159개는 조건을 모두 통과한 최종 관찰 목록이 아니다. 1종목(GOOG)의 최신 일봉·상세 시세 경로를 실제 검산했고 정규장 호가 20개 전체 수집은 아직 하지 않았다.

최초 실행에는 일봉 준비와 실제 정규장 20표본 누적이 필요하다. 표본 간 최소 간격만으로도 19분 이상이며 다종목 순회 때문에 실제 시간은 더 길다. 준비 중에는 사용자 지정만 운영하고 자동 종목을 미리 통과시키지 않는다. 같은 마지막 정규장 표본은 다음 장전 평가에서 재사용할 수 있다. 장외 시세·과거 일봉으로 실제 호가 표본을 채우지 않는다.

## 고정 일봉 전략과의 연결

기존 고정 Donchian 규칙·201봉 지표 준비 조건·비용·위험 한도는 바꾸지 않는다. 사용자 종목 계획 준비 뒤 장전 자동 목록이 완성되면 새 종목의 전일 확정 신호만 추가 계산한다. 이미 소비·취소된 계획은 재생성하지 않는다. 장중에 처음 준비된 자동 종목은 관찰부터 시작하고, 기존 일봉 계획이나 개장 진입 창을 되살리지 않는다. 다음 완료 일봉 계획에서 정식 평가한다.

자동 선정은 매수 신호나 주문 허가가 아니다. 신규 매수는 전략과 위험 검사를 통과해야 하고 실제 전송 직전에도 현재 목록을 재확인한다. 선정 범위가 달라지므로 기존 30종목 고정 연구와 이후 운용 결과를 동일 표본으로 비교하지 않는다. 관측 원장에 목록 변경과 설정·소스 버전을 기록한다.

## 실행과 확인

일반 실행과 고정 일봉 지속 실행에서 수집기가 함께 동작한다. 별도 인자를 추가할 필요가 없다. 기존 체결 방식 선택을 그대로 따르며 아래 실행을 모의 주문 활성화 명령으로 해석하지 않는다.

Windows CMD, 프로젝트 루트:

```cmd
python Code\daily_paper.py
python Code\watchlist.py
python Code\main.py --test unit-universe
python Code\main.py --test all
```

`main.py`는 기존 일반 전략, `daily_paper.py`는 기존 고정 일봉 전략을 실행한다. 두 전략의 계좌와 실행 설정은 기존 분리를 유지한다. 같은 프로그램을 이중 실행하지 않는다. `watchlist.py`는 인증·계좌·주문을 호출하지 않는 상태 확인이다.

Pi에서는 기존 설치 폴더에서 기존 Linux 설정을 선택한다:

```sh
PYTRADING_SETTINGS="$PWD/Config/settings-linux.json" .venv/bin/python Code/daily_paper.py
PYTRADING_SETTINGS="$PWD/Config/settings-linux.json" .venv/bin/python Code/watchlist.py
```

설치별 실제 Linux 설정 위치가 다르면 기존 실행에 사용한 파일 경로를 사용한다. `execution.json`·인증 경로·부팅 설정을 이 기능이 바꾸지 않는다. 이번 개발은 서비스를 시작·재시작하거나 주문을 전송하지 않았다.

기록 위치:

- `Data/universe/selection.json`: 현재 자동 선정, 추가·제외 사유와 검색 범위
- `Data/universe/status.json`: 수집 단계·오류·진행 수
- `Data/universe/history/<완료 일봉 날짜>/`: 변경 이전 목록을 포함한 시각별 판정 이력
- `Data/universe/sources/`: 공식 마스터 원본 ZIP·분류·일봉·허용 필드 상세 시세
- `Data/universe/spreads/`: 제한된 실제 호가 표본
- `Data/universe/verified-stocks.json`: 보유·미체결 관리에도 필요한 상품 분류 근거

## 공식 계약 근거

확인일 2026-11-05. 원본 계약 저장본은 `Data/specs/kis-api/portal-contracts/`에 보존돼 있다.

- [KIS 공식 해외 종목 마스터](https://github.com/koreainvestment/open-trading-api/blob/main/stocks_info/overseas_stock_code.py): 24열·stock type=2·USD·상품 구분 필드.
- [KIS 공식 거래대금 순위](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/trade_pbmn/trade_pbmn.py): HHDFS76320010, NDAY=5, KEYB·연속 조회. 실제 키 미제공은 별도 읽기 전용 응답 근거에 기록했다.
- [KIS 공식 현재가 상세 필드](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/price_detail/chk_price_detail.py): HHDFS76200200의 shar, last, curr, base, e_ordyn. 저장 포털 예제와 실제 응답의 거래 가능 값은 `매매 가능`이었다.
