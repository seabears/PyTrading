"""Project paths and provider settings."""
from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TOKEN_DIR = PROJECT_ROOT / "token"

KIS_ENV_PATH = Path(r"D:\00_env\.env")
TOSS_ENV_PATH = Path(r"D:\00_env\toss.env")

KIS_TOKEN_PATH = TOKEN_DIR / "token.dat"
TOSS_TOKEN_PATH = TOKEN_DIR / "toss_token.dat"
