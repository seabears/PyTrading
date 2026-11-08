# 모의 위험 자료 판정과 한정 시험 준비

> 2026-11-01 정책 반영: 아래 내용은 과거 조사 이력이다. 현행 [금지 목록](PROHIBITED_OPERATIONS.md)과 [정책 구현 검증](POLICY_ENFORCEMENT.md)이 우선한다. 통합증거금 필드 설명은 읽기 전용 진단이며 사용·가입·활성화 권고가 아니다. integrated 설정은 거절하고 cash_only 설정만으로 승인하지 않는다. 사용자 확인 초기 가상 현금100000 USD는 이미 별도 기준으로 기록됐으므로 다시 요청하지 않는다. 현재 현금·NAV 및 계좌 미가입 상태와는 구분한다.

[검토용 AI 전달 보고]

- 전체 판정: **선행 조건 미충족**. 코드·합성 검사·실제 조회는 진행했고, 위험 근거가 부족해 모의 주문은 미실행.
- 작업 시각: 2026-10-29T23:04:51+09:00 ~ 2026-10-29T23:37:20+09:00 / 미국 거래일 2026-10-29.
- 해결한 차단 원인: 빈 체결 이력의 기존 비용은 해당 없음으로 처리. 주문가능액을 현금/NAV로 오인하지 않음. 공식 모의 output2 제한을 반영하고 미지원 조회를 제외. 프로필 한도·심볼·시간을 실제 실행 계층에서 검사. 실패 GET 상태/허용 오류 코드/재시도 근거 보존.
- 주요 변경: Code/trading/demo_readiness.py, demo_profile.py, demo_session.py; Code/kis_demo_session.py, kis_demo_execute.py; Code/broker/kis_readonly.py, kis_api/client.py; 관련 Test와 테스트 등록. 조회 전용 기본 유지. 명시 실행 진입점은 선행 검사 게이트이며, 실제 현금 공급기·체결후 정산을 포함한 전체 시험 러너는 미완성.
- 위험 자료: 주문가능액100000.00USD·빈 보유/예약·조회 범위 주문/체결0은 확인됨. 초기 자금·USD 체결현금/NAV·개별 체결ID/시각·자금 변동 원본은 미확인. foreign-margin, 결제기준잔고, 기간거래, 기간손익과 present output2는 확인한 공식 계약상 모의 미지원. 다른 모든 경로가 미지원이라는 뜻 아님.
- 초기 기준·비용: 초기금/NAV 등록 안 함. 2026-07-31~10-29 빈 이력만 검증. 기존 체결 비용 해당 없음, 미래 비용0 가정 안 함. 주문 전 기존1.003 예약 완충 유지, 체결 후 실제 비용·현금 대조 전 신규 매수 불허. 원본이 확보되기 전 기준 시점도 미확정.
- RiskLedger: 원본 계좌·모드·USD 기준·해시·기간·완전성 검사/조립과 합성 replay ingest 통과. 실제 ingest=false, new_orders_allowed=false. 실제 자금/정산 공급기와 자동 주문 시나리오는 미구현.
- 정규장 최신 확인: verified=True, 30종목, 정상1740건, 오류/누락0건, 완전 순회58회. 작업 시작 전을 포함한 당일 누적이며 모든 종목 공통 관측 범위는 2026-10-29T13:30:56.392216+00:00~2026-10-29T14:31:06.523484+00:00 UTC. 이는 기존 복구 도구를 읽은 결과로 도구 수정 없음. 증권사 체결 검증 아님.
- 실제 모의: 이번 작업 조회 스냅샷 2회·GET시도13건/성공12건. 최종GET7시도/성공6건, HTTP500/EGW00201 오류1회 뒤 기존2초 대기·1회 재시도로 회복. 실패 상태·허용 코드·시도 번호 보존. 매수0·매도0·취소0, 접수0·체결0·거절0·최종취소0. 각 주문 시나리오 미실행이며 성공0으로 통과 처리하지 않음.
- 종료: 조회 범위 계좌 미체결0·보유0, 시험 보유0·미체결0. 활성화false. Pi active/PID2281, 재시작0, 부팅disabled; 기존 halt=['repeated_collection_errors']. 운영 반영/재시작 없음.
- Windows: Python3.12.6, python Code/main.py --test all; 2026-10-29T14:31:06.504886+00:00~2026-10-29T14:31:26.406436+00:00 UTC, 651통과/0실패/0미실행. 로그 C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-140451\tests-windows.txt.
- ARM: aarch64/Python3.13.5, .venv/bin/python Code/main.py --test all; 2026-10-29T14:31:33.853479+00:00~2026-10-29T14:31:43.938908+00:00 UTC, 651통과/0실패/0미실행. 격리 경로 /opt/PyTrading; 로그 C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-140451\arm-tests.txt. 기능별 89통과. ARM 아카이브와 실제 실행 소스 해시 일치.
- 정책: 실계좌 주문0. 기존 Data·인증·계좌·계획·전략·한도 보존, SQLite 유지, 대출/불허 상품/FMP 차단 유지. 기존 운영 경로에 코드 배포 없음, 부팅·무인 반복 활성화 없음.
- 추가 공지: 10/29 공식 공지 확인. 11/10·11/13 응답 계좌필드 삭제 대상에 현재 해외주식 시험 API 없음. 요청 계좌번호와 인증/원장 지문 검증은 유지. 선물·옵션 사용 금지 유지.
- 사용자 최소 행동: KIS_INQUIRY.md를 고객센터에 직접 보내고 공식 API/앱/HTS 대체 자료·현금/NAV·초기금·비용·자금변동 정의 답변을 제공. 이번에는 문의문 작성만 했으며 외부 전송 안 함. 답변 없이 현재 금액을 임의 채택하거나 주문 활성화하면 안 됨.
- 근거: C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-140451\report.md / C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-140451\results.json / C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-140451\checks.png / C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-140451\actual-vps-20261029-143154-003298\responses-redacted.json / C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-140451\official-contracts.json / C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-140451\tested-code-hashes.json.
- 다음: 공식 답변으로 실제 자금·정산 원본 파서 구현, 원장 검산·중복/수동 사건 대조 후 제한 주문 러너 완성. 현재 상태에서 모의 주문 강행·실계좌 전환 금지.


## 공식 계약과 실제 결과 연결

확인일 2026-10-29. 공개 포털 상세 JSON 8종을 저장했고 공식 virtualTrId와 apiSummary/필드 설명을 대조했다. 기존 official-contracts.json의 ‘공개 예제에서 지원 미확인’을 그대로 미지원 판정으로 사용하지 않았다. 이번에는 명시적 모의 미지원 필드가 있는 경로만 그렇게 판정한다.

| 항목·필요한 값 | 공식 API·필드 / 단위·기준 | 모의 지원 근거 | 실제 확인 결과·판정 | 남은 조치 |
|---|---|---|---|---|
| 초기 USD 자금·순자산·기준 시점 | USD 자금 배정 원본 + USD NAV 구성 | 현재 확인한 계약에 초기 투자금의 확정 정의 없음 | **미확인**. 100000을 초기금으로 등록하지 않음. output3 총자산 집계는 USD NAV로 간주하지 않음 | 공식 초기 자금·통화별 순자산 필드/명세 또는 앱·HTS 내보내기 기준 확인 |
| 체결 기준 현금 | foreign-margin.frcr_dncl_amt1 외화예수금(USD 행); ‘예수금’만으로 체결현금 단정 불가 | foreign-margin TTTC2101R의 virtualTrId=모의투자 미지원 | 경로는 **공식적으로 미지원**, USD 체결현금 값·대체 경로는 **미확인** | KIS에 vps 체결현금 기준과 공식 대체 조회 요청 |
| 주문 가능 금액 | inquire-psamount VTTS3007R: ord_psbl_frcr_amt, ovrs_ord_psbl_amt; USD, AAPL 지정가500 조회 | 공식 VTTS3007R | **확인됨** 100000.00USD. 주문 여력이며 현금/NAV 아님 | 현금과 자금 배정 의미는 별도 확인 |
| 예수금 표시값과 차이 | inquire-present-balance VTRP6504R output2[USD].frcr_dncl_amt_2; 외화사용가능금액 | 공식 설명: 모의는 output3만 정상 출력 | 이전 0.000000은 보존. output2 정상 제공은 **공식적으로 미지원**. 차액100000을 실제 회계 차이로 해석하지 않음 | 0의 내부 산출 사유는 KIS 답변 필요. 이번에는 미지원 output2 재조회하지 않음 |
| 보유 수량·원가·원격 예약 | inquire-balance VTTS3012R; NASD/NYSE/AMEX 각각; ovrs_cblc_qty, ord_psbl_qty, frcr_pchs_amt1 | 공식 모의 3거래소 개별 조회 지침 | **확인됨**: 빈 보유·예약0. 실제 보유 원가 검산은 **미관측** | 최초 체결 뒤 잔고 증가·원가·잔여 예약 검증 |
| 주문·누적 체결 식별·금액 | inquire-ccnl VTTS3035R; ord_dt/odno, ft_ccld_qty/ft_ccld_amt3; 현지 조회일·주·주문통화 | 공식 모의 전종목/전상태·15행 페이지 | **확인됨**: 2026-07-31~10-29 전체 페이지 양끝 조회가 모두 빈 이력. 범위 전 이력 주장 안 함 | 실제 체결 시 누적 차분과 체결 중 변동 재검산 |
| 개별 체결 ID·시각 | ord_tmd는 주문 접수 시각이며 체결 시각 아님 | 현재 조회로 개별 체결 ID/시각 확인 안 됨 | **미확인**. 미지원으로 단정하지 않음 | 모의 체결 통보/공식 대체 내역의 ID·시간·중복키 계약 확인 |
| 기존 체결 비용 | 위 기간 체결0에 대한 적용 여부 | 완전·안정 이력 조회 범위에 한함 | **확인됨·해당 없음**. 비용0이라는 관측/가정이 아님 | 체결 발생 후에는 실제 확정 비용 원본 필요 |
| 향후 수수료·세금·확정 시점 | inquire-period-trans CTOS4001R dmst_frcr_fee1/frcr_fee1 등; inquire-period-profit TTTS3039R | 두 API virtualTrId=모의투자 미지원 | 해당 경로 **공식적으로 미지원**, 모의 비용 적용/대체 경로 **미확인** | 비용 적용률·매수/매도 과세·정산 시점·공식 앱/명세 대체 경로 문의 |
| 결제 예수금·정산 기준 | inquire-paymt-stdr-balance CTRP6010R; 현재잔고 설명은 미국 장후 정산 반영 시간 구분 | CTRP6010R 모의투자 미지원; 현재잔고 output2 역시 미지원 | 경로 **공식적으로 미지원**. 실전 설명을 모의 정산 보증으로 쓰지 않음 | 모의의 체결/결제 현금 대응 관계·갱신 시점 확인 |
| 입출금·배당·환전·수동 거래 | 자금 사건 ID/통화/금액/시각/종류와 전체 기간; period-trans 등 후보 | 확인한 거래내역 경로는 모의 미지원. 다른 모든 API/앱까지 미지원이라는 뜻 아님 | 자금 변동 원본 **미확인**. 수동 주문 이력은 조회 범위 내0, 현금 사건 없음은 주장 불가 | 공식 지원 이력 범위·기간·페이지·대체 내보내기 확인 |


## 검증 순서와 미구현 범위

조회 → 계좌/페이지/양끝 상태 대조 → 공식 지원 및 현금 기준 확인 → 원본 정규화/해시/기간 검사 → RiskLedger ingest → 계좌 스냅샷 검산 → 한정 주문이다. 이번 실행은 공식 USD 현금/NAV·자금 사건 원본 단계에서 멈췄다. 빈 이력의 기존 비용 ‘해당 없음’은 미래 수수료0 또는 입출금 없음의 증명이 아니다. 체결 없는 초기 기준을 설정하더라도 검증한 최초 시점 이후만 추적해야 하며, 현재는 그 기준조차 등록하지 않았다.

합성 전용 원본 입력은 replay 원장만 허용하고 실제 주문을 못 한다. 실제 입력에는 인증된 캡처 공급기가 필요하며 JSON의 verified 값으로 승인할 수 없다. 현재 resolve_available_sources는 모의 미지원 현금 경로를 호출하지 않는다. 공식 지원 라벨만 바뀌어도 자동 승인하지 않는다. 실제 현금/정산 공급기와 제한된 접수→취소→왕복체결 러너는 미구현이며, 명시 진입점을 전체 주문 기능 완료로 표현하지 않는다.

기존 비용 예약 완충1.003은 최종 비용률이 아니다. 새 비용모델 최적화나 기존 위험 한도 변경은 하지 않았다. RiskLedger 금액은 기존 Decimal 0.000001 HALF_EVEN, 주문가격 기존 센트 규칙 유지. 최종 비용이 미확정인 체결의 손익은 확정값으로 만들지 않는다. 현재 비용 API 미지원이므로 체결후 안전한 정산/잔여보유 관리 계약부터 확보해야 한다.

## 실제 실행과 코드 보존

실제 조회와 실행게이트는 Windows 최종 소스에서 수행했고 ARM은 동일 Code/Config/Test 아카이브 전체를 검사했다. tested-code-hashes.json에서 해시를 보존했다. Pi 운영 서비스 소스는 배포·수정하지 않았으며 계좌 데이터 덮어쓰기 없음. 변경 전 파일은 C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-140451\before에 보관했다. 필요시 해당 파일만 비교·복원하고 새 원장/보고서를 지우지 말 것. 이번 단계는 운영 배포가 없어 Pi 롤백 대상 없음.

기준 Windows633개 통과는 이번 작업의 baseline-windows.txt에 기록. 최종651개 통과와 구분한다. 개발 중 지원 범위 밖인 기본 python3.9로 한 번 실행해 import 실패했고, 지정 Python3.12로 다시 실행했다. 최종 검사는 위에 기록한 실제 결과다. ARM 합성 자동 검사는 실제 장비에서 수행했지만 실제 vps 조회는 Windows에서 수행했다. 실제 체결·부분체결·취소 경합·잔고/현금 변동은 미관측. 그래프는 검사·조회/차단 상태이며 성과 그래프가 아니다.

## 실행법

CMD: cd /d C:\Projects\PyTrading

지원 Python 명시: %USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe Code/main.py --test all

조회 전용: 위 Python으로 Code/kis_demo_session.py --recovery-file <최신Pi검증JSON> --env-file Credentials/kis_demo.env --output <Data하위새폴더> --contracts-folder "C:\Projects\PyTrading\Data\reports\kis-demo-session20261029-140451\official-contracts"

명시 시험 게이트: Code/kis_demo_execute.py --execute-limited-demo 와 동일 인자. 현재는 자료 부족으로 exit3이며 주문을 보내지 않는다. enabled 변경으로 해결 안 됨. 향후 실제 러너 구현·검증 전에는 이 명령을 실제 주문 시험 완료 기능으로 간주하지 말 것. 실제 실행 인자/시각은 actual-gate-meta.json에 보존.

Pi 관측 확인: cd /opt/PyTrading 후 PYTRADING_SETTINGS=$PWD/Config/settings-linux.json .venv/bin/python Code/tools/verify_quote_recovery.py --folder Data/device-validation/daily-observation

Pi 격리 검사: cd /opt/PyTrading 후 .venv/bin/python Code/main.py --test all. 인증 파일이 없는 합성 검사 경로이다. 자동 enable 또는 운영 재시작 명령 없음.

## 고객센터 문의

KIS_INQUIRY.md에 한 번에 보낼 문안을 저장했다. 사용자가 추가 공식 자료가 없음을 확인했으므로 임의 값 보충 없이 대기한다. 외부 발송하지 않았다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
