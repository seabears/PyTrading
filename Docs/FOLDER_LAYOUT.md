# 프로젝트 폴더 구조

| 폴더 | 용도 |
|---|---|
| Code | main.py, paths.py, app·broker·news·strategy·trading·research·tools 파이썬 코드 |
| Config | 관찰 종목, 뉴스 검색어, 매매·연구 설정 JSON |
| Credentials | 인증 파일 예시와 안내 (실제 인증 파일은 기존 외부 경로 사용) |
| Docs | 사용 설명서와 분석 문서 |
| Test | 기능별 자동 검증 코드 |
| Data | 수집 자료, 모의 계좌, 테스트 입력·결과, 보고서·그래프 |
| Deployment | 라즈베리파이 실행 스크립트와 서비스 설정 |

프로젝트 루트에서 `python Code/main.py`로 계속 실행한다.
기능 선택은 `python Code/main.py --test`, 전체 자동 검증은 `python Code/main.py --test all`이다.
Code 폴더 안에서는 기존처럼 `python main.py`로 실행할 수 있다.

관찰 종목은 Config/settings.json의 symbols, 사업군 연구 종목은 Config/peers.json에서 수정한다.
설정 JSON 안의 상대 경로는 Code를 기준으로 해석한다. 예: ../Config/paper.json, ../Data/paper.
실제 인증 경로 Credentials/toss.env와 기존 모의 계좌·시세 자료는 유지한다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
