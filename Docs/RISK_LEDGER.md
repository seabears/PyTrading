## 최신 한정 모의 시험 결과 — 2026-10-29

실제 미국 정규장 복구 확인=true. 이번 보고서 기준 30종목 정상호가 420건, 정규장 전체 14회, 오류·누락0건이다. 시세 수집 서비스 PID2281과 부팅disabled, 기존 repeated_collection_errors 중지를 유지했다. 조회 검증기의 동시기록 시각 오경보만 수정·백업·반영했으며 서비스 재시작은 없었다.
실제 vps 인증과 계좌GET 조회는 성공했으나 최초 USD 순자산/체결현금/최종 비용/자금 사건 근거가 부족해 위험 원장 ingest와 실제 모의 주문은 중지했다. 주문가능100000 USD와 외화예수금표시0 USD를 초기 자금으로 채택하지 않았다. 기존 settlement_basis라는 출력 필드명은 호환성용이며 이 필드의 결제/체결 현금 정의가 검증됐다는 뜻이 아니다.
이번 최종 Windows/ARM 전체633개 검사 통과. 실제 모의 주문·취소·체결은 미실행이며 합성 검사로 대체하지 않는다. 새 Config/kis-demo-session.json은 enabled=false다.
최신 결과: C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\report.md, C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\results.json, C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\handoff.md. 읽기 전용 실제 응답과 공식 고정 버전 근거도 같은 폴더에 있다. 아래 기존 본문은 각 작성 시점의 이력이다.

---

# 근거 기반 위험 원장

Code/trading/risk_ledger.py의 RiskLedger는 주문 원장 journal JSON의 risk_ledger에 상태를 보존한다. 주문과 위험을 별도 DB로 나누지 않아 백업 시 한 번의 SQLite 체크포인트로 함께 복사된다. 초기 기준·전체 사건 집합·일별 중지·최종 평가·원본 지문·코드/설정 버전을 남긴다. verified=True 사전은 더 이상 정상화 근거로 받지 않는다.

## 계산과 거래 단위

USD 금액은 Decimal 소수 6자리 HALF_EVEN으로 계산한다. 입력은 문자열/정수, NaN·무한대·float는 거절한다. 외부 잔고 대조 허용차는 1센트다. 이 허용차는 미확인 비용을 임의로 보정하는 허가가 아니다. 원가 배분 잔차는 마지막 잔량에 남겨 비용을 잃지 않는다.

초기 투자 기준은 등록 시점의 순자산으로 고정한다. 이후 입출금으로 위험 한도 기준을 자동 확대하지 않는다. 총현금, 순 주문가능 금액, 순자산, 투자 노출을 구분한다. 보유 평가가 없거나 오래됐으면 신규 매수를 승인하지 않는다. 기존 주문당 10%·총노출 50%·최대 5종목·일일 손실 2%·연속 손실 3회/60분 등 Config/safety.json 한도는 유지한다. 기본 daily 내부 계좌의 별도 0.25% 위험 예산은 바꾸지 않는다.

매수 비용은 취득 원가에 포함한다. 이동평균 원가로 부분 매도에 배분하고, 매도 대금에서 최종 매도 비용을 뺀 뒤 실현손익을 계산한다. 동일 종목이 무보유→보유→무보유가 되는 한 구간을 청산 거래 1건으로 정의한다. 여러 부분 매도는 각각 실현손익에 반영하되 마지막 수량이 0일 때만 연속 손실을 한 번 집계한다. 음수 손익이면 연속 손실 +1, 0 이상이면 연속 손실을 초기화한다. 대기 만료 후에도 새 신선한 평가가 있어야 매수를 재검토한다.

입출금은 외부 자본 변동으로 분리한다. 배당은 배당 수익, 비거래 계좌 비용(scope=account)은 별도 비용으로 구분한다. 체결 비용은 각 체결의 fees_final=true 근거가 필요하다. 배분이 불명인 사후 비용·정정은 검토 대상으로 남겨 신규 매수를 막는다. 입금을 수익이나 손실 회복으로 처리하지 않는다.

일별 기준은 America/New_York 날짜를 사용한다. 새 날에는 직전 정상 평가를 이월하며 첫 날은 등록 시점부터의 부분 구간임을 명시한다. 외부 입출금을 뺀 순자산 변화로 일일 손실을 계산하고, 하루 중 한도에 도달하면 회복해도 당일 중지 상태를 유지한다. 관측 사이 손실을 알 수 있다고 주장하지 않는다.

## 근거 계약과 검산

정상화된 입력에는 계좌/환경 지문, as_of, window_start, 각 원본의 source_times, 완전성, source_hashes, 버전, 현금·주문가능 금액·순자산·보유·원가·현재 가격·체결·자금 사건이 필요하다. 알 수 없는 필드와 계좌/인증 원문 필드는 저장하지 않는다. 각 조회·가격은 평가 시점보다 미래가 아니고 현재 기준 30초 이내여야 한다. 조회 창이 직전 체크포인트와 이어져야 한다. 원본 필드가 제공되지 않는 KIS 응답을 추정해 이 계약에 맞추지 않는다.

체결의 id와 order_id는 불변이어야 한다. 이미 본 동일 사건은 재계산에서 한 번만 사용하고, 같은 ID의 수정·누락·원수량 초과·수동 체결·동일 시각의 순서 불명 매수/매도는 중지한다. 현금 수지·보유 수량·비용 포함 원가·평가액을 대조한다. 기존 보유나 초기 이력이 있으면 초기 기준과 미확인 원가/손익을 분리하고 임의 인수하지 않는다. 설정 정책이 바뀌면 검토 전 새 자격을 주지 않는다.

RiskLedger.ingest(evidence)는 계산 라이브러리 경로다. 자동 공급기가 없는 실제 비용·자금 변동을 수동 boolean으로 검증 처리하지 않는다. 저장된 평가로부터 RiskProof를 생성하고 주문용 현금·수량·원가·지문·체크포인트와 다시 비교한다. 합성/재생 원본은 실제 주문 허가 근거가 아니며 재생 원장은 전송을 영구 차단한다. 기존 보유의 검증된 매도/취소 경로는 신규 매수 위험 중지와 구분한다.

## 실행 명령

```cmd
cd /d C:\Projects\PyTrading
python Code\main.py --test unit-readiness
python Code\order_store.py risk-replay --store Data\replay-execution\demo.sqlite --evidence Data\tests\fixtures\risk-evidence-baseline.json --alias replay-demo
python Code\order_store.py risk-status --source Data\replay-execution\demo.sqlite
```

risk-replay는 파일을 과거 합성 재생으로만 취급하고 실제 거래 원장에는 적용하지 않는다. 새 경로나 기존 replay_only 원장만 사용하며 시간은 입력 당시 시각이다. 제공 예시는 가상 입력이며 실제 계좌 근거가 아니다. risk-status는 읽기 전용이다. 실제 모의계좌의 위험 근거 공급·최종 비용 검증은 KIS_READINESS.md의 외부 검증 조건을 따른다.

재생 결과의 eligible는 입력 계산의 검산 결과일 뿐 실제 계좌 검증이나 송신 허가를 뜻하지 않는다. replay_only와 source_kind=synthetic 때문에 실제 전송은 별도로 차단한다. fees에는 수수료·세금 등 그 체결에 귀속되는 최종 총비용을 포함해야 한다.


## 현금·예약·비용 검산 연결 (2026-11-01)

읽기 전용 계좌 관측과 사용자 지정 현금 모델을 RiskLedger의 미확정 관측으로 연결했다. 이는 승인된 RiskProof가 아니다. 가입 상태 자료는 요구하지 않는다. 비용 해당 없음/미확정/확정을 구분하고 원격/로컬 예약을 검산한다. 실행과 현재 남은 조건은 [DEMO_CASH_REVIEW.md](DEMO_CASH_REVIEW.md) 및 C:\Projects\PyTrading\Data\reports\cash-risk-review20261101-223416\results.json를 따른다. 기존 승인 검사나 자금 사건 완전성 검사를 우회하지 않는다.


## 실행 가능한 위험 평가 연결 (2026-11-01)

부분 근거의 위험 평가를 RiskLedger.assess_observation/assessment에 연결했다. 계산 가능한 한도·손실 검사는 수행하며 자료가 없는 검사는 unknown으로 보존한다. evaluation_complete와 evidence_complete 및 RiskProof 승인은 서로 다르다. 실제 실행과 최종 검사는 [RISK_ASSESSMENT.md](RISK_ASSESSMENT.md)와 C:\Projects\PyTrading\Data\reports\risk-evaluation20261101-225144\results.json를 따른다. 기존 완전 근거는 검산 후 재사용하며 모델만으로 공식 근거를 인증하지 않는다.


## 체결 후 정산 연결 개발 (2026-11-03)

정산 원본 소비·비용/자금 사건 대조·후속 위험 재평가와 읽기 전용 상태 명령을 추가했다. 실제 KIS 정산 자료 공급기는 기본 미연결이며 운영 반복 체결 완료로 표시하지 않는다. 최신 범위와 사용법은 [STRATEGY_POSTTRADE.md](STRATEGY_POSTTRADE.md)를 따른다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
