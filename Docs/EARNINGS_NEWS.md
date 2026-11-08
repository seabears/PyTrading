# 실적 발표 뉴스 활용

> 2026-10-25 변경: 원문·발표 전 예상치 검증을 필수로 강화했다. 미검증 제목은 매매에 쓰지 않으며 현재 검증 통과 사건은 없다. [검증 결과와 수집 계획](EARNINGS_DATA_PLAN.md)을 먼저 확인한다.

현재 30종목의 실적 뉴스를 독립적으로 수집해 모의 매매에 사용한다. 일반 뉴스 설정은 그대로 꺼져 있다.

프로젝트 루트의 CMD에서:

```cmd
python Code/main.py
python Code/main.py --test earnings
python Code/main.py --test unit-earnings
python Code/main.py --test earnings-live
```

earnings는 합성 입력으로 모의 매수→매도를 확인한다. earnings-live는 AAPL/MSFT/NVDA 실제 RSS 수집만 확인하며 증권사 인증·주문을 호출하지 않는다.

`Config/strategy.json`의 `earnings_enabled`: true이면 실적 호재가 신규 매수의 필수 조건이다. false로 바꾸면 다음 실행에서 이 기능을 끈다. 기존 `news_enabled`는 일반 확정 뉴스의 독립 스위치다.

`Config/earnings.json`: 회사 이름·허용 출처·기사 유효 시간(시간)·순회 후 대기 시간(초)·수집 만료 시간(초)을 수정한다. 현재 30종목과 기존 한국 종목의 이름이 들어 있다. 종목 추가 시 `Config/settings.json`과 이 파일의 `company_aliases`를 함께 수정한다.

호재: 제목에 명시된 예상 상회 또는 회사 전망 상향 + 기존 돌파·거래량·호가·예산 조건을 모두 만족해야 모의 매수한다. 호재가 없거나 수집 중·실패 상태이면 신규 매수를 대기한다.

악재: 예상 하회·회사 전망 하향은 신규 매수 제한, 보유 중에는 모의 매도에 사용한다. 방향 충돌은 신규 매수만 막고 가격 규칙으로 보유를 관리한다. 전망 하향은 실적 호조보다 우선한다. 가격 손절·이익 보호는 뉴스 처리 전에 검사한다.

기사 제목·RSS 출처 메타데이터 기반 모의 신호이며 확인된 공시가 아니다. 회사 발표 원문·수치·컨센서스는 자동 확인하지 않는다. `confirmed`와 `source_verified`는 false로 보존한다. 실적 증가만으로 호재를 만들지 않는다.

현재 기본 출력 위치:

- `Data/paper-kis/earnings-news.json`: 중복 제거된 실적 캐시·출처 수집 상태.
- `Data/paper-kis/earnings-events.jsonl`: 최초 수신 사건 이력. 장애 재시도 중 중복 가능성이 있어 event_id와 available_at으로 중복 제거한다.
- `Data/paper-kis/earnings-reports/`: 종목별 최신 수집·분류·제외 이유.
- `Data/paper-kis/decisions.jsonl`: 실제로 모의 판단에 제공된 실적 사건과 판단 결과.

수집은 백그라운드에서 실행하며 시세 검사를 막지 않는다. 기사 발행 시각과 최초 수신 시각을 구분해 저장한다. 종료 시 수집을 중단한다. 다음 시작에서 캐시를 읽되 만료·출처·회사·제목 조건을 다시 검사한다.

기존 분봉에는 당시 실적 수신 이력이 없어 실적 전략 백테스트를 거절한다. 과거 가격만 재생하려면 연구용 별도 설정에서 earnings_enabled를 false로 지정해야 한다. 실적 기능의 수익성은 아직 검증하지 않았다.

구현: `Code/news/earnings.py` 분류, `earnings_service.py` 수집·캐시, `Code/strategy/engine.py` 판단, `Code/app/runner.py` 실행 연결. 최신 [검증 보고서](../Data/reports/earnings-feature/report.md).
