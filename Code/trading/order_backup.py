"""주문·위험 JSON의 단일 SQLite 체크포인트 백업과 새 경로 격리 복원.

백업은 WAL 파일을 직접 복사하지 않고 SQLite backup API로 읽는다. 위험 원장은
같은 journal 행 안에 있어 주문 상태와 원자적으로 같은 시점에 포함된다.
"""

from contextlib import closing
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.runtime import acquire_run_lock
from paths import CODE_ROOT, CONFIG_ROOT


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_database(path):
    """원본을 변경하지 않고 SQLite 구조와 저장 상태를 읽는다."""
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("backup_integrity_failed")
        rows = connection.execute("SELECT body FROM journal WHERE id=1").fetchall()
        if len(rows) != 1:
            raise ValueError("backup_journal_missing")
        state = json.loads(rows[0][0])
    if not {"mode", "alias", "orders", "events", "account"} <= state.keys():
        raise ValueError("backup_schema_unknown")
    risk = state.get("risk_ledger")
    if risk and (
        risk.get("schema") != 1 or risk.get("account_fingerprint") != state.get("broker_identity")
    ):
        raise ValueError("backup_risk_identity_mismatch")
    return state


def flush_file(path):
    with path.open("r+b") as file:
        os.fsync(file.fileno())


def backup_orders(source, destination):
    """전체 bundle이 완성된 뒤에만 최종 이름으로 등록한다. 실패한 partial은 정상 백업이 아니다."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists() or destination == source or destination.is_relative_to(source):
        raise ValueError("backup_destination_exists_or_invalid")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(".partial-" + destination.name + "-" + uuid.uuid4().hex)
    temporary.mkdir(mode=0o700)
    database = temporary / "orders.sqlite"
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original, closing(
        sqlite3.connect(database)
    ) as copy:
        original.backup(copy)
    state = inspect_database(database)
    if state["mode"] != "internal" and not state.get("broker_identity"):
        raise ValueError("backup_account_identity_missing")
    manifest = {
        "schema": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": state["mode"],
        "alias": state["alias"],
        "account_fingerprint": state.get("broker_identity"),
        "risk_schema": state.get("risk_ledger", {}).get("schema"),
        "risk_checkpoint": state.get("risk_ledger", {})
        .get("last_evaluation", {})
        .get("checkpoint_hash"),
        "snapshot_phase": "single_atomic_journal_row",
        "database_sha256": file_hash(database),
        "code": {
            name: file_hash(CODE_ROOT / name)
            for name in ("trading/orders.py", "trading/risk_ledger.py", "trading/order_backup.py")
        },
        "settings": {
            name: file_hash(CONFIG_ROOT / name) for name in ("safety.json", "execution.json")
        },
    }
    metadata = temporary / "manifest.json"
    metadata.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    flush_file(database)
    flush_file(metadata)
    if destination.exists():
        raise ValueError("backup_destination_exists")
    os.replace(temporary, destination)
    return manifest


def validate_bundle(bundle, mode, alias, fingerprint):
    bundle = Path(bundle).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if manifest["schema"] != 1 or (
        manifest["mode"],
        manifest["alias"],
        manifest["account_fingerprint"],
    ) != (mode, alias, fingerprint):
        raise ValueError("restore_account_or_mode_mismatch")
    database = bundle / "orders.sqlite"
    if database.is_symlink() or file_hash(database) != manifest["database_sha256"]:
        raise ValueError("restore_hash_mismatch")
    state = inspect_database(database)
    if (state["mode"], state["alias"], state.get("broker_identity")) != (mode, alias, fingerprint):
        raise ValueError("restore_database_identity_mismatch")
    return manifest, state


def restore_orders(bundle, destination, mode, alias, fingerprint):
    """기존 원본을 덮어쓰지 않고 새 경로에 복원한다. 오래된 의도를 자동 재전송하지 않는다."""
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("restore_requires_new_destination")
    manifest, state = validate_bundle(bundle, mode, alias, fingerprint)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with acquire_run_lock(destination.with_suffix(".lock")):
        if destination.exists():
            raise ValueError("restore_destination_race")
        temporary = destination.with_name(".restore-partial-" + uuid.uuid4().hex + ".sqlite")
        with closing(
            sqlite3.connect(
                (Path(bundle).resolve() / "orders.sqlite").as_uri() + "?mode=ro", uri=True
            )
        ) as source, closing(sqlite3.connect(temporary)) as copy:
            source.backup(copy)
            unknown = []
            for identifier, order in state["orders"].items():
                if order["status"] in {"INTENT", "SENDING"}:
                    order["status"] = "UNKNOWN"
                    order["restore_review_required"] = True
                    unknown.append(identifier)
                if order.get("cancel_status") == "SENDING":
                    order["cancel_status"] = "UNKNOWN"
            state["restore_gate"] = {
                "status": "remote_reconciliation_required",
                "restored_at": datetime.now(timezone.utc).isoformat(),
                "backup_at": manifest["created_at"],
                "unknown_intents": unknown,
                "backup_sha256": manifest["database_sha256"],
            }
            state["account"] = None
            with copy:
                copy.execute(
                    "UPDATE journal SET body=? WHERE id=1", (json.dumps(state, allow_nan=False),)
                )
        inspect_database(temporary)
        flush_file(temporary)
        if destination.exists():
            raise ValueError("restore_destination_race")
        os.replace(temporary, destination)
    return state["restore_gate"]
