#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PYTRADING_SETTINGS="$ROOT/Config/settings-linux.json"
exec "$ROOT/.venv/bin/python" -X utf8 Code/daily_paper.py
