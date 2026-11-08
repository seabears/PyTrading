"""설정 파일과 실행 잠금. 라즈베리파이와 Windows에서 같은 실행 코드를 쓴다."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from broker.toss import parse_symbol
from paths import PROJECT_ROOT, CONFIG_ROOT

SETTINGS_PATH = CONFIG_ROOT / "settings.json"
PATH_SETTINGS = {"env_file", "news_queries", "events_file", "paper_settings", "strategy_config", "output_dir", "broker_config"}
SETTING_NAMES = PATH_SETTINGS | {"symbols", "watch", "interval", "collect_news", "news_interval"}


def load_run_settings(path: Path = SETTINGS_PATH, project_root: Path = PROJECT_ROOT) -> dict:
    """설정의 상대 경로는 프로젝트 기준이다. Config 하위 파일도 같은 기준을 쓴다."""
    # Linux 서비스는 별도 설정 파일을 선택한다. 상대 경로 해석은 Code 기준을 유지한다.
    if path == SETTINGS_PATH and os.environ.get("PYTRADING_SETTINGS"):
        path = Path(os.environ["PYTRADING_SETTINGS"]).expanduser()
        if not path.is_absolute():
            path = (project_root / path).resolve()
    settings = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(settings, dict):
        raise ValueError("settings.json은 JSON 객체여야 합니다.")
    # 이전 토스 설정도 읽을 수 있게 broker·broker_config만 선택 항목으로 둔다.
    required_names = SETTING_NAMES - {"broker_config"}
    allowed_names = SETTING_NAMES | {"broker"}
    missing_names = required_names - set(settings)
    unknown_names = set(settings) - allowed_names
    if missing_names or unknown_names:
        raise ValueError("settings.json의 설정 이름과 필수 항목을 확인하세요.")
    settings.setdefault("broker", "toss")
    settings.setdefault("broker_config", str(CONFIG_ROOT / "kis.json"))
    if settings["broker"] not in {"kis", "toss"}:
        raise ValueError("broker는 kis 또는 toss여야 합니다.")
    for name in ("watch", "collect_news"):
        if type(settings[name]) is not bool:
            raise ValueError("지속 실행·뉴스 수집 설정은 true 또는 false여야 합니다.")
    for name, minimum in (("interval", 30), ("news_interval", 300)):
        if type(settings[name]) is not int or settings[name] < minimum:
            raise ValueError("시세 간격은 30초 이상, 뉴스 간격은 300초 이상이어야 합니다.")
    symbols = settings["symbols"]
    if not isinstance(symbols, list) or not symbols or not all(isinstance(value, str) for value in symbols):
        raise ValueError("관찰 종목은 비어 있지 않은 문자열 배열이어야 합니다.")
    try:
        settings["symbols"] = [parse_symbol(value) for value in symbols]
    except argparse.ArgumentTypeError:
        raise ValueError("관찰 종목은 KR:005930 또는 US:AAPL 형식이어야 합니다.") from None
    for name in PATH_SETTINGS:
        value = settings[name]
        if value is None and name in {"news_queries", "paper_settings", "strategy_config"}:
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError("파일·폴더 설정은 비어 있지 않은 경로여야 합니다.")
        target = Path(value).expanduser()
        settings[name] = target if target.is_absolute() else (project_root / target).resolve()
    return settings


class AlreadyRunningError(OSError):
    """같은 결과 폴더를 다른 실행이 사용하고 있다."""


def acquire_run_lock(path: Path):
    """OS 잠금은 프로세스 종료·전원 차단 시 풀린다. 파일 존재 여부로 판단하지 않는다.

    잠금 파일을 지우면 실행 중 다른 파일을 잠그는 경합이 생길 수 있어 그대로 둔다.
    Linux는 flock, Windows는 첫 바이트 잠금을 사용하며 열린 파일을 유지해야 한다.
    """
    file = path.open("a+b")
    try:
        if path.stat().st_size == 0:
            file.write(b"0")
            file.flush()
        file.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return file
    except OSError:
        file.close()
        raise AlreadyRunningError("같은 모의 계좌가 실행 중입니다. 먼저 기존 실행을 종료하세요.") from None


def release_run_lock(file) -> None:
    """닫으면 OS 잠금이 해제된다. 잠금 파일은 삭제하지 않는다."""
    file.close()
