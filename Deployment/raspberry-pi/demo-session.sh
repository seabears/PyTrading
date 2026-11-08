#!/usr/bin/env bash
# 기존 운영 서비스를 건드리지 않는 수동 한정 모의시험 도구.
set -euo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PYTRADING_SETTINGS="$ROOT/Config/settings-linux.json"
mkdir -p "$ROOT/Data/locks"
# 조회와 시험을 동시에 시작해 같은 계좌를 서로 다른 스냅샷으로 검사하지 않는다.
exec 9>"$ROOT/Data/locks/demo-launch.lock"
if ! flock -n 9; then
  echo '이미 조회 또는 시험이 실행 중입니다. 중복 실행하지 않습니다.'
  exit 4
fi
case "${1:-}" in
  check)
    "$ROOT/.venv/bin/python" -X utf8 Code/kis_demo_balance.py --env-file "$ROOT/Credentials/kis_demo.env"
    ;;
  run)
    echo 'KIS 모의 서버 한정 시험: AAPL 1주, 총매수500 USD, 매수최대2회.'
    echo '정규장 시세 관측과 계좌 검사를 통과한 뒤에만 주문합니다. 실계좌 주문은 금지합니다.'
    "$ROOT/.venv/bin/python" -X utf8 Code/kis_demo_session.py --env-file "$ROOT/Credentials/kis_demo.env" --execute
    ;;
  results)
    "$ROOT/.venv/bin/python" -X utf8 - <<'PY'
import json
from pathlib import Path
base=Path('Data/reports')
for category,name in [('kis-demo-session','result.json'),('kis-demo-balance','results.json')]:
    files=sorted((base/category).glob('*/'+name),key=lambda p:p.stat().st_mtime)
    if not files:
        print(category+': 실행 기록 없음');continue
    path=files[-1];data=json.loads(path.read_text(encoding='utf-8'))
    fields=['phase','recorded_at','ledger_connected','trial_basis_eligible','buy_requests','sell_requests','cancel_requests','final_order_activation','final_remote_account_snapshot_verified']
    print(str(path.resolve()))
    print(json.dumps({key:data[key] for key in fields if key in data},ensure_ascii=False,indent=2))
PY
    ;;
  *) echo '사용법: demo-session.sh check | run | results'; exit 2 ;;
esac
