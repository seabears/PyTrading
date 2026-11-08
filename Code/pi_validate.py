"""장비 정보와 격리된 오프라인 검증 결과를 수집한다. API·서비스·운용 계좌를 시작하지 않는다."""

import sys

sys.dont_write_bytecode = True
import argparse
import json
import os
import platform
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def collect_environment():
    metadata = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "os": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "executable": sys.executable,
        "project_root": str(ROOT),
        "ram_bytes": None,
        "model": None,
        "arm_device_verified": False,
    }
    if platform.system() == "Linux":
        try:
            metadata["ram_bytes"] = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        except (ValueError, OSError):
            pass
        model = Path("/proc/device-tree/model")
        if model.exists():
            metadata["model"] = model.read_text().strip("\x00\n")
        metadata["arm_device_verified"] = (
            platform.machine() in {"aarch64", "arm64"} and metadata["model"] is not None
        )
    metadata["free_bytes"] = shutil.disk_usage(ROOT / "Data").free
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--collect-only", action="store_true", help="전체 검증 없이 환경 정보만 수집"
    )
    args = parser.parse_args()
    parent = ROOT / "Data/device-validation"
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    destination.mkdir()
    metadata = collect_environment()
    metadata["tests_run"] = False
    metadata["systemd_runtime_tested"] = False
    if not args.collect_only:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        # 테스트의 임시 원장은 별도 폴더에만 생성한다. 전체 검증 진입점은 실제 socket을 차단한다.
        with tempfile.TemporaryDirectory(prefix="offline-", dir=destination) as temporary:
            environment["TMPDIR"] = temporary
            environment["TEMP"] = temporary
            environment["TMP"] = temporary
            result = subprocess.run(
                [sys.executable, str(ROOT / "Code/main.py"), "--test", "all"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                timeout=300,
            )
            (destination / "offline-tests.txt").write_bytes(result.stdout + result.stderr)
            metadata.update(tests_run=True, test_exit_code=result.returncode)
    if platform.system() == "Linux" and shutil.which("systemctl"):
        result = subprocess.run(
            [
                "systemctl",
                "show",
                "rule-trader",
                "--property=LoadState,ActiveState,SubState,ExecMainStatus,User,WorkingDirectory",
            ],
            capture_output=True,
            timeout=10,
            text=True,
        )
        # 환경 변수·ExecStart·인증 파일 내용은 수집하지 않는다.
        metadata["service_readonly_status"] = result.stdout.strip()
    (destination / "environment.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    print("결과 폴더:", destination)
    if metadata.get("test_exit_code", 0):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
