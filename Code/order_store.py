"""주문·위험 SQLite 백업/새 경로 복구/위험 근거 재생. 실제 API나 주문은 호출하지 않는다."""

import argparse
import json
from pathlib import Path

from trading.order_backup import backup_orders, restore_orders


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    backup = actions.add_parser("backup")
    backup.add_argument("--source", type=Path, required=True)
    backup.add_argument("--destination", type=Path, required=True)
    restore = actions.add_parser("restore")
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--destination", type=Path, required=True)
    restore.add_argument("--mode", choices=["internal", "kis_demo", "live"], required=True)
    restore.add_argument("--alias", required=True)
    restore.add_argument(
        "--fingerprint", default=None, help="계좌 원문이 아닌 비밀이 제거된 계좌 지문"
    )
    status = actions.add_parser("risk-status")
    status.add_argument("--source", type=Path, required=True)
    ingest = actions.add_parser("risk-replay")
    ingest.add_argument("--store", type=Path, required=True)
    ingest.add_argument("--evidence", type=Path, required=True)
    ingest.add_argument("--alias", required=True)
    arguments = parser.parse_args()
    try:
        if arguments.action == "backup":
            result = backup_orders(arguments.source, arguments.destination)
        elif arguments.action == "restore":
            result = restore_orders(
                arguments.backup,
                arguments.destination,
                arguments.mode,
                arguments.alias,
                arguments.fingerprint,
            )
        elif arguments.action == "risk-status":
            from trading.order_backup import inspect_database

            state = inspect_database(arguments.source)
            result = {
                "mode": state["mode"],
                "account_fingerprint": state.get("broker_identity"),
                "replay_only": state.get("replay_only", False),
                "restore_gate": state.get("restore_gate"),
                "risk": state.get("risk_ledger", {}).get("last_evaluation"),
                "last_failure": state.get("risk_ledger", {}).get("last_failure"),
            }
        else:
            from trading.orders import OrderManager
            from trading.risk_ledger import RiskLedger

            # 파일 입력은 과거 재생으로만 취급한다. 실시간 KIS 검증 자격을 얻지 않는다.
            evidence = json.loads(arguments.evidence.read_text(encoding="utf-8"))
            evidence["source_kind"] = "synthetic"
            from trading.order_backup import inspect_database
            from strategy.engine import parse_timestamp

            if arguments.store.exists() and not inspect_database(arguments.store).get(
                "replay_only"
            ):
                raise ValueError("risk_replay_requires_separate_replay_store")
            manager = OrderManager(arguments.store, "kis_demo", arguments.alias)
            try:
                manager.state["replay_only"] = True
                manager.state["broker_identity"] = evidence["account_fingerprint"]
                RiskLedger(manager).ingest(evidence, now=parse_timestamp(evidence["as_of"]))
                result = manager.state["risk_ledger"]["last_evaluation"]
            finally:
                manager.close()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception:
        parser.exit(
            1,
            "원장 작업 실패. 기존 파일을 보존했습니다. 경로·계좌 지문·무결성과 문서를 확인하세요.\n",
        )


if __name__ == "__main__":
    main()
