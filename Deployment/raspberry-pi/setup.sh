#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,13), "Python 3.11~3.13이 필요합니다"'
"$PYTHON" -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/python" -m pip install -r "$PROJECT_DIR/Deployment/requirements-runtime.lock"
echo "인증 파일을 별도 복사하고 chmod 600 적용 후 수동 실행부터 확인하세요. 서비스는 시작하지 않았습니다."
