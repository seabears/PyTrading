"""원자적 상태 저장과 명시적 복구. 손상된 상태를 자동 초기화하지 않는다."""
import json
import os
from pathlib import Path
import shutil
import tempfile


def atomic_json(path, value, backup=False):
    """임시 파일을 fsync 후 교체한다. 기존 정상 JSON 한 세대를 별도로 보존한다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    if backup and path.exists():
        previous = path.read_bytes()
        json.loads(previous)  # 깨진 원본을 정상 백업 위에 복사하지 않는다.
        backup_path = path.with_suffix(path.suffix + ".previous")
        _replace_bytes(backup_path, previous)
    _replace_bytes(path, encoded)


def _replace_bytes(path, data):
    descriptor, name = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def rotate_log(path, maximum_bytes=8_000_000, generations=3):
    """계좌가 아닌 관측 로그만 크기를 제한한다. 실행 잠금 안에서 호출한다."""
    path = Path(path)
    if not path.exists() or path.stat().st_size < maximum_bytes:
        return
    for index in range(generations, 0, -1):
        source = path if index == 1 else path.with_name(path.name + f".{index - 1}")
        target = path.with_name(path.name + f".{index}")
        if source.exists():
            os.replace(source, target)


def restore_paper(path):
    """서비스를 끄고 잠금을 잡은 뒤 사용. 원본은 격리 보존하고 검산된 백업만 복구한다."""
    from app.runtime import acquire_run_lock
    from trading.paper import PaperAccount
    path = Path(path)
    with acquire_run_lock(path.parent / "run.lock"):
        backup = path.with_suffix(path.suffix + ".previous")
        state = json.loads(backup.read_text(encoding="utf-8"))
        # 별도 임시 디렉터리에서 같은 검산기를 사용한다.
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "account.json"
            candidate.write_bytes(backup.read_bytes())
            PaperAccount(candidate, state["settings"])
        if path.exists():
            from datetime import datetime, timezone
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            shutil.copy2(path, path.with_name(path.name + ".quarantined-" + stamp))
        _replace_bytes(path, backup.read_bytes())
        # 복구 계좌는 운영자가 확인할 때까지 신규 매수를 중지한다.
        (path.parent / "PAUSE_BUYS").write_text("restored_state_requires_review\n", encoding="utf-8")
