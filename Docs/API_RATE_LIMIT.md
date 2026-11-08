# 토스 REST 명세 정합성 수정

공식 REST 명세 버전 1.2.24, 2026-10-13 확인.
출처: https://openapi.tossinvest.com/openapi-docs/latest/openapi.json
호출 한도 가이드: https://developers.tossinvest.com/docs#heading-rate-limits

| 항목 | 수정 결과 |
|---|---|
| 호출 제한 | AUTH, MARKET_INFO, MARKET_DATA, MARKET_DATA_CHART, MARKET_INDICATOR_CHART 각각 관리 |
| 서버 현재 한도 | 정상·429 응답의 X-RateLimit-Limit 반영 |
| 남은 여유와 충전 시간 | Remaining이 1 이하이면 Reset만큼 선제 대기 |
| 429 | Retry-After·Reset 이상 대기, 1·2·4초 지수 백오프와 jitter 적용, GET 한 번만 재시도 |
| 인증 429 | 일반 인증 실패의 60초 간격과 분리, AUTH 그룹 대기 안내 적용 |
| 토큰 | Bearer·양의 정수 expires_in 검증, 짧은 정상 수명 허용, 대기 후 만료 재검사 |
| 국내 코드 | 숫자만 강제하던 제한을 없애 영문·숫자 6자리 지원 |
| 호가 미제공 | 스펙상 timestamp=null·빈 호가는 quote_unavailable로 WAIT |
| 개별 응답 오류 | 해당 종목의 형식 오류가 다른 종목 관찰을 종료하지 않도록 처리 |

분봉 종료 시각, 200개 조회 제한, inclusive nextBefore, 시간대 URL 인코딩,
OAuth form-urlencoded 요청, Bearer 헤더, 국채 일봉 요청은 기존 구현과 명세가 일치한다.

요청 주기에는 한도 대비 10% 여유를 둔다. 초기 한도는 공식 가이드 값이나 현재 응답 헤더가 우선한다.
호가·봉은 캐시하지 않는다. 같은 시장의 거래시간만 30초 재사용한다.
다른 프로세스가 같은 클라이언트로 보낸 요청은 직접 계산할 수 없으므로 서버 헤더와 429를 따른다.
클라이언트는 현재 프로그램처럼 단일 실행 흐름에서 사용한다. 다중 스레드 공유는 지원하지 않는다.

## 검증

전체 자동 테스트 187개 통과. 실제 HTTP 대신 가짜 응답과 가짜 시계를 사용했다.
공식 명세 발췌 파일과 그룹 매핑·요청 필드·nullable 응답 계약을 비교했다.
실제 계정 인증·API 정상화·투자 수익은 이번 변경에서 미검증.
원본 모의 계좌·과거 시세를 변경하거나 실제 토큰을 발급하지 않았다.

![검증한 그룹별 기본 요청 간격](../Data/reports/toss-spec/pacing.png)

기존 실행을 Ctrl+C로 종료하고 프로젝트 루트에서 `python Code/main.py`로 재시작한다.
실행 인자는 추가하지 않는다.
