"""새 시험 원장과 명시적 이어받기 원장을 구분한다. 자동 재전송은 하지 않는다."""
import json
import sqlite3
from pathlib import Path

from paths import DATA_ROOT


def session_store(profile, stamp):
    """Config.resume_store가 있을 때만 기존 SQLite를 연다. 다른 모드·경로·별칭은 거절한다."""
    base = (DATA_ROOT / "execution/kis-demo-session").resolve()
    resume = profile.get("resume_store")
    if resume is None:
        return base / stamp / "orders.sqlite", "demo-session-" + stamp, stamp
    store = Path(resume).resolve()
    if not store.is_relative_to(base) or not store.is_file() or store.suffix != ".sqlite":
        raise ValueError("resume_store_outside_trial_root_or_missing")
    connection = sqlite3.connect(store.as_uri() + "?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT body FROM journal WHERE id=1").fetchone()
        if row is None:
            raise ValueError("resume_trial_state_missing")
        state = json.loads(row[0])
    finally:
        connection.close()
    session_id = state.get("limited_demo_session", {}).get("id")
    if (state.get("mode") != "kis_demo" or not session_id
            or state.get("alias") != "demo-session-" + session_id):
        raise ValueError("resume_trial_scope_mismatch")
    return store, state["alias"], session_id
