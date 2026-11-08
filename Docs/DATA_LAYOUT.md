# 코드·데이터 분리

실행은 `C:\Projects\PyTrading\Code`에서 `python main.py`로 한다.

| 경로 | 내용 |
| --- | --- |
| Code/src, tools, tests | 실행·연구·테스트 코드 |
| Config | 종목·전략·실행 설정 |
| Data/history | 실제 시세·지표 캐시·시험 사용 기록 |
| Data/paper | 모의 계좌·판단 로그·뉴스 후보·현황 |
| Data/confirmed-events.json | 검토된 확정 뉴스 |
| Data/tests/fixtures | 기능 실행용 합성 입력 |
| Data/tests/results | 기능·과거 연구 결과·보고서·그래프 |
| Data/reports | 이전·폴더 정리 검증 보고서 |
| Data/cache/plots | 그래프 캐시 |

경로는 paths.py에서 PROJECT_ROOT, DATA_ROOT, RESULTS_ROOT, FIXTURES_ROOT로 구분한다.
settings.json의 상대 경로는 Code 기준이다. Data 경로에는 ../Data를 사용한다.
Data 전체는 Git에서 제외한다. 두 폴더를 함께 라즈베리파이에 복사하고 인증 경로를 수정한다.
과거 연구의 소스 사본·본문은 당시 기록을 보존한다. 실행용 latest.json 포인터만 새 위치를 가리킨다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
