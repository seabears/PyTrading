"""운영체제와 무관하게 사용하는 프로젝트 경로 설정."""
from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Raspberry Pi와 Windows에서 같은 코드를 쓰도록 모든 경로를 환경변수로 덮어쓸 수 있다.
TOKEN_DIR = Path(os.getenv("PYTRADING_TOKEN_DIR", str(PROJECT_ROOT / "token")))
KIS_ENV_PATH = Path(os.getenv("PYTRADING_KIS_ENV", str(PROJECT_ROOT / ".env")))
TOSS_ENV_PATH = Path(os.getenv("PYTRADING_TOSS_ENV", str(PROJECT_ROOT / ".toss.env")))

KIS_TOKEN_PATH = TOKEN_DIR / "token.dat"
TOSS_TOKEN_PATH = TOKEN_DIR / "toss_token.dat"
