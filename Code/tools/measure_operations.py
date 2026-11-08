"""실제 시세 조회 1회 주기를 별도 관측 계좌에 기록한다. 주문은 없고 지속 실행하지 않는다."""
import json
from pathlib import Path
from app.runner import main as run
from paths import DATA_ROOT


def main():
    folder = DATA_ROOT / "observations/operations-probe"
    from broker.diagnostic import diagnostic_scope
    with diagnostic_scope():
        run([], settings_override={"watch": False, "output_dir": folder})
    print("실제 1회 관측:", folder / "operations.json")


if __name__ == "__main__":
    main()
