"""터미널 위치와 무관한 공통 경로. Code에는 파이썬 코드만 둔다.

설정은 Config, 문서는 Docs, 인증 예시는 Credentials, 테스트 코드는 Test,
실제 시세·모의 계좌·테스트 입력과 결과는 Data에 저장한다.
"""
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent
# 기존 함수의 project_root 인자는 상대 파일 경로를 Code 기준으로 해석한다.
PROJECT_ROOT = CODE_ROOT
REPOSITORY_ROOT = CODE_ROOT.parent
CONFIG_ROOT = REPOSITORY_ROOT / "Config"
TEST_ROOT = REPOSITORY_ROOT / "Test"
DATA_ROOT = REPOSITORY_ROOT / "Data"
RESULTS_ROOT = DATA_ROOT / "tests" / "results"
FIXTURES_ROOT = DATA_ROOT / "tests" / "fixtures"
