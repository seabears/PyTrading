# 계좌 실행 경로 장애 진단

2026-11-03. 이번 수정은 장애 원인 구분을 보완한다. 실제 KIS 정산 자료 공급기 연결이나 정규장 주문·체결 검증을 완료한 문서가 아니다.

## 확인 방법

새 코드가 반영된 설치 경로에서 Windows CMD는 `python Code\execution_status.py`, Pi Linux 셸은 `.venv/bin/python Code/execution_status.py`를 실행한다. 현재 선택한 모드의 로컬 원장을 읽기 전용으로 확인하며 실제 API·주문은 사용하지 않는다. 다른 계좌를 조회하거나 저장된 승인으로 주문을 허용하지 않는다.

`last_broker_failure`에 최근 안전한 장애 원인을 표시한다. 원본은 증권사 주문 SQLite의 `journal.body.broker_last_failure`와 최근 100건의 `broker_failure_history`다. 이 운영 진단 기록의 제한은 주문/체결/위험 원장을 삭제하는 기능이 아니다. 실패한 판단의 `broker_error`도 decisions.jsonl에 전달한다. 로컬 원장 자체가 저장되지 않으면 같은 안전한 JSON을 표준 출력에 남기며 `secondary_code=diagnostic_storage_failed`로 표시한다. 이 경우 원장의 과거 오류만 보지 말고 콘솔/systemd 로그도 확인한다.

현재 운영 Pi에 새 코드를 배포하지 않았다면 이 필드가 없을 수 있다. 필드 부재는 정상 운용 확인이 아니며, 이번 작업에서 기존 서비스 상태를 현재 시각으로 재조회하거나 시작하지 않는다.

## 단계와 확인 위치

|stage|의미|우선 확인|
|---|---|---|
|authentication|모의 계좌 인증 또는 인증 캐시 저장|모의/실전 인증 분리, 파일 권한, 토큰 만료와 허용 IP; 토큰을 무조건 삭제하지 않음|
|history_query_initial / history_query_final|전체 주문 이력 양끝 조회|HTTP 상태·허용 오류 코드, 조회 범위/페이지·통신|
|balances_query / buying_power_query / present_balance_query|보유·외화 여력·집계 조회|모의 지원 계약·통화·HTTP/업무 오류|
|history_normalization|주문 원문을 내부 계약으로 변환|필수 필드·주문 유형·취소 자식 행·수량 형식|
|snapshot_validation / account_contract|계좌·주문·보유의 완전성/일치|수동 주문, 누락/중복 식별자, 다른 계좌, 양끝 조회 사이 변화|
|settlement_observation / balance_linkage|누적 체결/보유 관측 기록|SQLite 저장, 원주문 계약, 수량·예약 대조|
|cash_model_update / risk_review / risk_ingest|모델 현금/위험 검산|미확정 비용, 자금 변동, 손실 중지, 기준/원본 시각|
|position_projection / daily_plan_linkage|확인된 자기 보유와 계획의 연결|소유 전략·수량·현재 원가·정확한 계획 ID|
|account_projection_storage|전략 투영 account.json 저장|디스크 여유·경로·쓰기 권한; 실패 시 메모리 투영 복구|
|intent_creation / intent_storage / order_transmission|주문 의도 검산·저장·전송|위험 자격·원장 상태; 불명 상태에서는 재주문 금지|
|cancel_preflight / cancel_transmission|취소 사전 검사/전송|NOT_SENT와 UNKNOWN/접수/거절 구분, 최신 원주문·잔량 대조|

`category`는 API/인증·HTTP·호출 제한·연결·응답 JSON·계약 대조·SQLite·투영 파일 저장 등을 구분한다. `http_status`와 `provider_code`는 실제 예외에 있는 허용값만 표시하며, 없는 값을 추정하지 않는다. 계좌 GET의 HTTP 오류에 실제 상태를 연결했고 JSON 디코딩 실패와 네트워크 실패도 구분했다. `elapsed_seconds`와 `step_seconds`는 이번 처리/단계 시작 이후의 시간이며 이전 성공 요청의 시간을 재사용하지 않는다.

오류 자유문·서버 msg1·응답 본문·URL·헤더·계좌번호·인증키·토큰·파일 경로는 진단에 넣지 않는다. 알려진 내부 오류 코드만 보존한다. 따라서 모르는 오류는 구체적인 단계와 일반 분류를 남기며 자유문을 노출하지 않는다. 저장 장애를 기록하다가 다시 실패해도 원래 오류의 단계/분류/HTTP 상태를 유지한다.

## 자료 부족과 장애의 구분

정산 공급기가 없는 것은 정상 조회 성공과 별개인 미구현 상태다. `settlement_provider_last_observation`은 마지막 전체 계좌 관측 당시 공급기 configured/connected/as_of/reason을 보여준다. configured=true는 콜백이 있다는 뜻이며 공식 자료 검증이나 주문 승인 자체가 아니다. 필드가 없으면 미확인(null)이다. 도구를 지금 읽었다고 as_of를 현재로 바꾸지 않는다.

수수료·세금·자금 변동의 실제 원본은 여전히 미연결이다. 비용 0이나 사용자 초기금으로 누락 자료를 채우지 않는다. 정산 공급기가 잘못된 자료를 주면 진단을 남기고 신규 매수를 차단한다. 공급기 부재/비용 대기 중에도 현재 계좌/수량이 검증된 기존 보유의 보호 매도와 취소는 별도 감소 전용 경로를 유지한다.

정규장 정상 호가 540건/오류0인 과거 기록은 시세 관측 근거일 뿐 주문·체결·비용 후 성과 검증이 아니다. 개장 후 5분을 놓친 CVX/LLY 계획은 소급 집행하지 않는다. 정산 공급기·최신 정규장 관측·실제 모의 체결은 각각 별도 미완료 항목으로 남는다.

## 검사

`python Code/main.py --test unit-readiness` 및 전체 `python Code/main.py --test all`. 실제 API가 아닌 합성 HTTP/임시 SQLite 검사다. 최신 수치와 로그·ARM 소스 일치·변경 전 재현은 Data/reports/broker-diagnostics/latest.json이 가리키는 보고서에 기록한다. 운영 배포·서비스 재시작·부팅 enable·실제 주문은 포함하지 않는다.
