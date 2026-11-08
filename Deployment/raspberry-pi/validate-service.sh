#!/bin/sh
# 기존 서비스와 별도의 합성 unit. 인증·원본 계좌·전체 저장 공간을 건드리지 않는다.
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
case "${1:-normal}" in
  normal) HANG=0 ;;
  watchdog) HANG=1 ;;
  *) echo "normal 또는 watchdog만 지원" >&2; exit 64 ;;
esac
sudo systemd-run --unit=pytrading-validation --service-type=notify \
  --property=User="$(id -un)" --property=WorkingDirectory="$ROOT_DIR" \
  --property=LimitCORE=0 --property=TimeoutStopSec=10 --property=WatchdogSec=10 --property=RuntimeMaxSec=60 --property=UMask=0077 \
  --setenv=PYTHONUTF8=1 --setenv=PYTHONDONTWRITEBYTECODE=1 --setenv=PYTRADING_TEST_HANG="$HANG" \
  "$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/Code/device_worker.py"
echo "systemctl status pytrading-validation 및 journalctl -u pytrading-validation으로 결과 확인"
echo "sudo systemctl stop pytrading-validation 으로 중지. 실제 daily 서비스는 시작하지 않았습니다."
