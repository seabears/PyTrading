## 최신 한정 모의 시험 결과 — 2026-10-29

실제 미국 정규장 복구 확인=true. 이번 보고서 기준 30종목 정상호가 420건, 정규장 전체 14회, 오류·누락0건이다. 시세 수집 서비스 PID2281과 부팅disabled, 기존 repeated_collection_errors 중지를 유지했다. 조회 검증기의 동시기록 시각 오경보만 수정·백업·반영했으며 서비스 재시작은 없었다.
실제 vps 인증과 계좌GET 조회는 성공했으나 최초 USD 순자산/체결현금/최종 비용/자금 사건 근거가 부족해 위험 원장 ingest와 실제 모의 주문은 중지했다. 주문가능100000 USD와 외화예수금표시0 USD를 초기 자금으로 채택하지 않았다. 기존 settlement_basis라는 출력 필드명은 호환성용이며 이 필드의 결제/체결 현금 정의가 검증됐다는 뜻이 아니다.
이번 최종 Windows/ARM 전체633개 검사 통과. 실제 모의 주문·취소·체결은 미실행이며 합성 검사로 대체하지 않는다. 새 Config/kis-demo-session.json은 enabled=false다.
최신 결과: C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\report.md, C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\results.json, C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-130207\handoff.md. 읽기 전용 실제 응답과 공식 고정 버전 근거도 같은 폴더에 있다. 아래 기존 본문은 각 작성 시점의 이력이다.

---

# KIS 모의계좌 읽기 전용 준비

이 도구는 주문·정정·취소를 전송하지 않는다. 기존 라즈베리파이 daily 서비스와 다른 원장을 사용한다. 실행해도 부팅 자동 시작을 등록하지 않는다.

## 인증과 실행

기존 Credentials/kis.env는 prod 시세용이다. 모의투자 키라고 추정해 재사용하지 않는다. Config/kis-preflight.json의 Windows credentials_file 기본값은 Credentials/kis_demo.env이며, 필드 형식은 README.md의 인증 파일 안내를 참고한다. Windows 외부 경로를 쓰려면 다음처럼 명시한다. 키·계좌번호를 채팅에 보내거나 Git에 넣지 않는다.

```cmd
cd /d C:\Projects\PyTrading
python Code\kis_preflight.py --env-file "Credentials/kis_demo.env"
```

파일에는 KIS_APP_KEY·KIS_APP_SECRET과 ACC_NO=앞8자리-뒤2자리 또는 KIS_ACCOUNT_NUMBER(8자리)·KIS_ACCOUNT_PRODUCT_CODE(2자리)가 필요하다. 모의 전용 도구는 항상 vps로 접속하며 KIS_ENVIRONMENT=vps는 선택 항목이다. 다른 환경을 명시하면 거절한다. 빈 예시를 그대로 실행할 수는 없다. 모의 계좌는 별도로 발급된 키·계좌여야 한다. 인증을 시도해도 계정이 맞는지 실제 서버 응답으로 확인되기 전에는 검증 성공이 아니다. 시세 파일과 같은 경로는 차단한다. 토큰은 Data/cache/kis/vps/readonly-인증지문.json에 분리 저장한다.

기본 조회 원장은 Data/execution/kis-demo-readonly/orders.sqlite다. 기본 내부 PaperAccount와 섞이지 않는다. 기존 ManagedKisAdapter를 enabled=False로 사용하고 API도 allow_trading=False다. 읽기 API 허용 목록, execute_managed 차단, 낮은 HTTP 함수의 GET/경로 검사를 별도로 적용한다. 토큰 발급 POST는 인증이며 상품 주문 POST와 구분한다.

## 확인 항목과 결과

주문 전체 이력 → 3거래소 잔고 → 주문가능 외화 → 현재잔고 → 주문 전체 이력을 순서대로 조회한다. 페이지 반복·누락·상한·누락 출력은 실패다. 양끝 이력의 내용이 다르면 스냅샷을 완료로 취급하지 않는다. 계좌 원문이 응답에 있으면 메모리에서 요청 계좌와 대조하고 보존 전에 제거한다. 읽기 검사에서는 유형 필드가 없는 주문을 지정가로 추정하지 않는다.

전체 보유·매도가능·원격 예약·로컬 미전송/접수 불명 예약을 구분한다. 원격에서 차감된 예약을 로컬에서 다시 차감하지 않는다. 수동 주문·다른 프로그램 주문·원주문 누락·불명 취소 자식 행은 검토 대상으로 남긴다. 주문가능 외화는 총현금이나 순자산이 아니다. 외화 예수금도 결제 기준으로만 표시하며 체결 기준 현금으로 자동 변환하지 않는다.

종료 코드 0은 오류 없이 검사가 끝났다는 뜻일 뿐 거래 승인 의미가 아니다. 2는 지정 인증 파일 없음, 3은 조회 완료 후 검토/미검증 항목 존재, 1은 조회·계약·설정 오류다. 보고서는 항상 new_orders_allowed=false다. Data/preflight/actual의 responses-redacted.json은 인증값·계좌 원문·자유문 오류를 제거한 실제 조회 응답, report.json은 검사 결과다. 합성 테스트 응답과 폴더를 분리한다. 실제 조회 실패 시 서버 오류 본문을 로그에 쓰지 않는다.

## 확인된 공식 계약 — 2026-10-28

- [KIS 주문체결 이력](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_ccnl/chk_inquire_ccnl.py): 모의는 전종목·양방향·전체 상태 조회이며 기간은 현지 날짜 기준이다. 원주문·수량·미체결·취소 구분을 사용한다.
- [KIS 잔고](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_balance/chk_inquire_balance.py): 전체 보유와 주문가능 수량, 외화매입금액은 서로 다른 필드다.
- [KIS 현재잔고](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_present_balance/inquire_present_balance.py): CTRP6504R/VTRP6504R, 외화/미국/전체 조회를 명시한다. output2의 통화별 예수금과 총자산 관련 출력은 기준을 구분한다.
- [KIS 매수가능 외화](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_psamount/chk_inquire_psamount.py): 주문가능 금액을 한도로 표시한다.
- [KIS 일별거래내역](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_period_trans/inquire_period_trans.py): 공개 예제는 CTOS4001R이고 모의 TR을 명시하지 않는다. 실전 전용 함수를 단순 V 치환해 모의에서 지원한다고 주장하지 않았다. 신용/대출 경로를 추가하지 않았다.

공식 예제만으로 실제 계좌의 처리상태 문자열·취소 자식 행 반환·부분 체결 식별·최종 비용과 모든 입출금 내역의 모의 지원을 확정하지 못했다. 따라서 현재 읽기 도구는 execution_fee_and_cash_movement_history_not_proven을 기록하며 위험 승인이나 주문 자격을 주지 않는다. 수수료를 0으로 가정해 통과시키지 않는다. 모의 계좌에서 실제 조회한 사실도 실제 주문 접수·부분 체결·취소 검증과 다르다.

## 이후 주문 연결 전 조건

모의투자 인증 확인, 실제 응답 계약과 완전한 비용/자금 변동 원본 확보, 기존 보유의 초기 원가/기준 확정, 수동 거래와 타 프로그램 분리, 복구 후 과거 시점부터의 원격 재대조, 위험 원장 정상 평가가 필요하다. 현재 모의 주문과 실주문 전송은 이번 도구에서 모두 막혀 있다. 기존 prod/live 송신 차단과 상품·대출·FMP 정책은 바꾸지 않았다.

Linux는 기본으로 Config/kis-preflight-linux.json의 ../Credentials/kis_demo.env를 사용한다. Windows 인증 경로 변경으로 기존 Pi 시세 인증이나 서비스 설정을 바꾸지 않는다.


## 사전/사후 주문 회계 연결 (2026-11-01)

첫 주문 전 기준을 저장하고 전송 직전에 대조한다. 아직 발생하지 않은 주문의 최종 비용은 사전 요구가 아니다. 체결 후 미확정 비용은 추가 매수를 중지하고, 확인된 보유의 축소/취소는 별도로 유지한다. 비용·현금 검산이 끝나야 전체 완료로 처리한다. 현재 자료의 사전 승인 조건을 면제하거나 실제 주문을 전송한 것은 아니다. 실행 결과와 제한은 [PREPOST_ORDER.md](PREPOST_ORDER.md) 및 C:\Projects\PyTrading\Data\reports\prepost-order20261101-232756\results.json를 따른다.


## 한정 모의시험의 사용자 기준 허용 (2026-11-02)

사용자가 명시적으로 선택한 "한정 모의시험 기준으로 진행"을 적용한다. 기존100000 USD를 사용자 지정 현금 기준으로 보존하고 실제 최신 외화 여력·빈 보유·빈 체결·미체결 대조를 결합한다. 공식 현금/NAV 또는 과거 자금 이력을 검증했다고 표시하지 않는다. 일반/실계좌 위험 승인과 구분한 user_designated_demo_trial 근거이며, 500 USD·1주·최대2회 BUY의 기존 한도는 유지한다. 첫 체결 후 추가 매수는 차단하고 확인된 자기 보유 정리·취소만 허용한다. 이 선택은 실제 주문 자동 실행/실계좌 허가/부팅 활성화가 아니다. 원장/정책/계좌가 바뀌거나 재시작/만료하면 재조회한다. 기존 손실/복원/수동 중지는 면제하지 않는다.


## 2026-11-02 한정 시험 기준 갱신

사용자가 사용자 지정100000 USD와 최신 빈 계좌·여력을 비교하는 최초 체결 전 한정 모의시험을 승인했다. 실제 자료 생성→RiskLedger 입력→주문 전 대조를 연결했다. 공식 현금/NAV·과거 자금 변동은 미검증 표시를 유지한다. 기본 주문 차단과 운영 서비스 설정은 유지한다. 실행/종료/비용 미확정 처리: [DEMO_USER_BASIS.md](DEMO_USER_BASIS.md). 이 항목은 기존 엄격한 공식 자료 판정을 한정 시험에만 구분 적용하며 일반 자동매매 승인을 뜻하지 않는다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
