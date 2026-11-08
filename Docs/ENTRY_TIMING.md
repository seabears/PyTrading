# 매수 타이밍 연구

프로젝트 루트에서 실행한다. 인증 파일·인터넷·실제 주문을 사용하지 않는다.

```cmd
python Code/main.py --test entry-timing
python Code/main.py --test unit-entry-timing
```

설정은 `Config/entry-timing.json`, 판단·측정은 `Code/research/entry_timing.py`, 자료 준비는 `Code/research/entry_inputs.py`, 보고서 실행은 `Code/tools/run_entry_timing.py`다.

최신 보고서와 그래프는 `Data/reports/entry-timing/`, 실행마다 보존하는 원본은 `Data/tests/results/entry-timing/`에 저장한다. 실행 전 조건·코드·자료 해시를 선언하고 연구 일지와 실험 레지스트리에 남긴다.

일봉은 동종 기업 최신 데이터 스냅샷의 28종목, 장중은 기존 운용 30종목의 저장 분봉을 사용한다. 수집 기간은 다르다. 새 자료 수집·운용 조건 변경은 하지 않는다.

8개 일봉 진입 방식과 6개 장중 진입 방식을 같은 돌파 사건에서 비교한다. 공통 매도 날짜/시각으로 진입 효과를 분리한다. 세 관측 길이·기본 비용·두 배 비용과 미체결을 모두 보존한다. 사건당 수익을 합산하거나 복리화하지 않는다. 계좌 수익률은 별도 공동 자금 백테스트로 검증해야 한다.

`*-audit.json`: 모든 후보와 중복·미성숙·누락·기간 경계 제외 사유.
`*-events.json`: 채택된 사건의 조건별 체결/취소·공통 종료 수익·같은 보유 길이 수익·MAE/MFE.
`summaries.json`: 전체 요약. `segments.json`: 기간·뉴욕 시간대별. `details.json`: 종목·연도별.
`coverage.json`: 실제 일봉·분봉 범위. `validation.json`: 조합 누락·중복 검사.

단위 검증은 다음 봉 체결, 현재 주문 봉의 미래 필드 차단, 확인·재확인·취소, 비용 현금 흐름, 같은 매도 시점, 미체결 포함, 데이터 경계, 분봉 누락·준비 시간, 일봉 신호의 미래 자료 독립성을 확인한다. 실전 수익성이나 실제 API 주문 체결을 보증하는 검증은 아니다.
