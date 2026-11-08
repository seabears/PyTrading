# KIS 새 시세 수집

현재 관찰 종목은 Config/settings.json의 symbols, 거래소는 Config/kis.json에서 수정한다.
이번 목록은 미국 30종목이며 알파벳은 GOOGL, 샌디스크는 SNDK다.

CMD에서 `python Code/main.py --test history`로 새 수집을 실행한다.
2018-01-01부터 미국 현지 전일까지 일봉과 API가 제공하는 최근 분봉을 조회한다.
시장 비교용 SPY를 추가하므로 저장 종목 수는 31개다. 실주문은 하지 않는다.
모든 종목에 유효 자료가 있어야 기존 Data/history를 교체한다. 그 외 폴더는 지우지 않는다.

- Data/history/daily/US-AAPL.json: 수정주가 요청 일봉, 배당 재투자 가격 아님.
- Data/history/minute/US-AAPL.json: 실제 제공 최근 1분봉. 장기 분봉 확보를 보장하지 않음.
- Data/history/raw: 인증정보 없는 요청 파라미터와 원본 시세 응답.
- Data/history/manifest.json: 실제 범위, 건수, 중단 이유, 파일 해시.
- Data/reports/data-refresh: 수집 보고서와 그래프.

collection_complete는 API 제공 종료 여부, requested_period_reached는 요청 시작일까지
도달했는지를 뜻한다. page_limit와 api_no_progress는 미완료다.
상장 전 데이터와 누락 봉을 임의 생성하지 않는다. 전체 거래일 누락 검사는 별도 필요하다.
이전 연구 보고서는 이전 시세 기준이다. `--test strategies`는 새 KIS 경로와 연결했다. 그 외 예전 Toss 전용 연구 메뉴는
경로·출처가 달라 새 자료와 바로 호환되지 않는다. peers.json은 이전 연구의 고정 종목군이다. 새 자료의 수집 성공은 전략의 수익성 검증이 아니다.

수집 중 중단하면 다음 history 실행에서 같은 요청 날짜의 정상 저장 파일을 재사용한다.
오류 OHLC 봉은 원본 raw와 각 기록의 rejected에 남기며 분석 candles에서 제외한다.
