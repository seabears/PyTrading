# 동종 기업 데이터와 산업군 시험

같은 룰이 비슷한 사업을 하는 기업에서도 유지되는지 확인합니다.
정상 실행의 관찰 종목과 매매 규칙을 자동 교체하지 않습니다. 실제 주문은 없습니다.

## 실행

CMD에서 프로젝트 폴더로 이동합니다.

```cmd
cd /d C:\Projects\PyTrading
python Code\main.py --test industry-history
python Code\main.py --test industry-peers
python Code\main.py --test industry-continuous
```

첫 명령은 KIS 인증·인터넷을 사용해 28동종 기업+SPY의 새 일봉 스냅샷을 받습니다.
둘째는 저장한 자료로 6규칙을 산업군·개별 종목·세 기간·두 비용 조건에서 1,296회 비교합니다.
셋째는 기준 규칙만 2020년부터 계좌 초기화 없이 72회 추가 시험합니다.
새 수집이 필요 없으면 첫 명령을 생략합니다. `--test`만 실행해 메뉴에서 고를 수도 있습니다.

자동 검증은 `python Code/main.py --test unit-industry-peers` 또는 전체 `--test all`입니다.
정상 실행과 같은 인증 파일·토큰 캐시를 재사용하지만 인증값·토큰은 결과에 기록하지 않습니다.

## 산업군과 설정

`Config/industry-peers.json`에서 산업군과 종목을 관리합니다.

|산업군|기업|
|---|---|
|통신|T, VZ, TMUS|
|반도체 설계|NVDA, AMD, AVGO, QCOM, MRVL|
|기업용 클라우드·IT|MSFT, IBM, ORCL|
|대형 제약|JNJ, LLY, MRK, ABBV|
|넷리스 리츠|O, NNN, ADC|
|온라인 광고|GOOGL, META, PINS, SNAP|
|자동차|TSLA, GM, F|
|종합 에너지|CVX, XOM, SHEL|

공식 GICS 분류가 아니라 IR·공시의 사업 성격을 참고한 연구용 그룹입니다.
같은 그룹이어도 수익 구조는 다릅니다. 분류 출처·차이는 설정과 보고서에 기록합니다.
산업군에 없는 기존 종목을 성과 때문에 매매 목록에서 삭제한 것은 아닙니다.

`Config/industry-study.json`에서 기간·6규칙·기준 규칙·표본 표시 기준을 관리합니다.
`breakout_trailing35`는 이전 연구에서 고른 기준을 그대로 적용합니다.
이번 산업군 결과를 본 후 산업군마다 규칙을 다시 선택하지 않습니다.

## 쌓이는 자료

- `Data/industry-peers/datasets/수집시각/`: 매번 새 일봉·원본 응답·공개 마스터·수집 manifest.
- `Data/industry-peers/datasets/latest.json`: 마지막으로 완전히 수집한 스냅샷 위치.
- `Data/tests/results/industry-peers/실험시각/`: 1,296개 거래·계좌 곡선·진단·비용 분해·종목 기여.
- `Data/tests/results/industry-continuous/실험시각/`: 72개 연속 시험의 거래·평가·연도별 손익.
- `Data/research/experiments/registry.jsonl`: 선언·개별 시작·완료·실패를 추가 기록.
- `Docs/RESEARCH_LOG.md`: 사람이 읽는 누적 연구 일지.
- `Data/reports/industry-peers/report.md`: 최신 비교 보고서와 그래프.

기존 `Data/history`를 지우거나 새 종목의 부족한 자료를 합성하지 않습니다.
수집이 일부 실패하면 이전 latest 포인터는 유지하며 실패 스냅샷의 manifest를 남깁니다.
공식 KIS 마스터에서 USD 일반 주식(type=2)인 신규 기업만 상품 확인 목록에 추가합니다.
SPY는 이미 허용된 ETF로 확인합니다. 대출·파생상품·ETN 차단과 운용 종목 목록은 유지합니다.

## 비교 단위

산업군마다 별도 1만 USD 계좌를 주고 종목당 초기 현금 최대 10%, 최대 3개를 보유합니다.
8개 계좌의 수익률을 더해 하나의 실제 계좌 수익처럼 표시하지 않습니다.
종목별 시험은 별도 1만 USD에 최대 1개·초기 현금 10%를 투자하므로 현금 비중이 큽니다.
그룹의 참고군은 초기 투자 한도 30%를 그룹 기업에 균등 보유합니다. 평균 노출은 전략과 다릅니다.

기본 비용은 검증용 가정이며 실제 증권사 요율이 아닙니다. 두 배 비용에는 스프레드도 포함합니다.
배당 현금이 빠져 있어 리츠·통신의 전체 투자 수익과 특히 차이가 날 수 있습니다.
수정주가의 가상 정수 수량·일봉 종가 MDD·현재 종목 소급 선택·과거 자료 재사용의 한계도 있습니다.
신규 기업 13개는 이번 연구에 새로 수집한 기업이지 완전히 독립된 시장·기간이라는 뜻은 아닙니다.
SHEL 관측은 2022년부터이며 이전 코드를 연결하지 않았습니다. 관측 시작을 상장일로 단정하지 않습니다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
