#!/bin/sh
# 경로는 스크립트 위치에서 계산한다. 기존 Windows 설정은 수정하지 않는다.
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
export PYTHONUTF8=1
export PYTHONDONTWRITEBYTECODE=1
export PYTRADING_SETTINGS="${PYTRADING_SETTINGS:-$PROJECT_DIR/Config/settings-linux.json}"
case "${PYTRADING_PROFILE:-earnings}" in
  earnings) ENTRY=main.py ;;
  price) ENTRY=price_paper.py ;;
  daily) ENTRY=daily_paper.py ;;
  *) echo "지원하지 않는 내부 모의 프로필" >&2; exit 64 ;;
esac
exec "$PROJECT_DIR/.venv/bin/python" -u -B "$PROJECT_DIR/Code/$ENTRY"
