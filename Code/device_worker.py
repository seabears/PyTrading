"""systemd 장애 시험용 합성 작업자. 인증·시세·주문·기존 계좌 접근이 없다."""

import os
import signal
import time
from pathlib import Path
from datetime import datetime, timezone
from app.operations import OperationMonitor
from app.runner import stop_on_service_signal
from app.runtime import acquire_run_lock
from app.stateio import atomic_json
from paths import DATA_ROOT


def main():
    folder = DATA_ROOT / "device-validation/systemd-synthetic"
    folder.mkdir(parents=True, exist_ok=True)
    with acquire_run_lock(folder / "run.lock"):
        monitor = OperationMonitor(folder)
        previous = signal.signal(signal.SIGTERM, stop_on_service_signal)
        started = time.monotonic()
        try:
            while time.monotonic() - started < 45:
                monitor.save()
                atomic_json(
                    folder / "worker.json",
                    {
                        "mode": "synthetic_only",
                        "at": datetime.now(timezone.utc).isoformat(),
                        "orders_sent": 0,
                    },
                )
                if os.environ.get("PYTRADING_TEST_HANG") == "1":
                    time.sleep(45)  # 사용자 격리 unit의 watchdog이 종료하는지 확인한다.
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            atomic_json(
                folder / "worker.json",
                {
                    "mode": "synthetic_only",
                    "stopped_at": datetime.now(timezone.utc).isoformat(),
                    "orders_sent": 0,
                },
            )
            signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    main()
