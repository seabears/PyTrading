"""상태 조회·매수 중지·검토 후 재개·내부 모의 계좌 백업 복구. 실제 주문은 없다."""
import sys
sys.dont_write_bytecode = True
import argparse
import json
import shutil

from app.runtime import acquire_run_lock
from app.stateio import atomic_json, restore_paper
from paths import DATA_ROOT

PROFILES = {"earnings": "paper-kis", "price": "paper-price-research", "daily": "paper-daily-frozen"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "pause", "resume-after-review", "restore"))
    parser.add_argument("profile", choices=PROFILES, default="earnings", nargs="?")
    args = parser.parse_args()
    folder = DATA_ROOT / PROFILES[args.profile]
    folder.mkdir(parents=True, exist_ok=True)
    if args.action == "status":
        path = folder / "operations.json"
        print(path.read_text(encoding="utf-8") if path.exists() else "아직 운용 관측 기록이 없습니다.")
        print("수동 매수 중지:", (folder / "PAUSE_BUYS").exists())
    elif args.action == "pause":
        # 실행 중에도 원자적 파일 생성으로 새 매수만 막을 수 있다.
        (folder / "PAUSE_BUYS").write_text("operator_pause\n", encoding="utf-8")
        from trading.observation_journal import control_event
        control_event(folder, "operator_pause")
    elif args.action == "restore":
        restore_paper(folder / "account.json")
        from trading.observation_journal import control_event
        control_event(folder, "state_restored_buys_paused")
    else:
        with acquire_run_lock(folder / "run.lock"):
            if shutil.disk_usage(folder).free < 256_000_000:
                raise ValueError("공간 부족이 해결되지 않았습니다.")
            path = folder / "operations.json"
            state = json.loads(path.read_text(encoding="utf-8"))
            if any(count >= 3 for count in state["errors"].values()):
                raise ValueError("서비스를 다시 관측해 정상 응답을 확인한 뒤 중지하고 재개하세요.")
            from trading.observation_journal import control_event
            control_event(folder, "resume_after_review")
            state["buy_halts"] = []
            atomic_json(path, state)
            (folder / "PAUSE_BUYS").unlink(missing_ok=True)
            print("검토 후 매수 중지를 해제했습니다. 데이터·위험·실적 조건 검사는 유지됩니다.")


if __name__ == "__main__":
    main()
