"""보유 종목 추천 엔진의 실행 상태를 JSON으로 보관한다."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


DEFAULT_ADVISOR_STATE_PATH = (
    Path(__file__).resolve().parents[3] / "Portfolio" / "advisor_state.json"
)


@dataclass(frozen=True)
class AdvisorSymbolState:
    first_seen: str = ""
    observed_quantity: float = 0.0
    observed_average_price_usd: float = 0.0
    protected_quantity: float = 0.0
    protected_entry_price_usd: float = 0.0
    highest_price_usd: float = 0.0
    last_action: str = ""
    signal_streak: int = 0
    last_signal_date: str = ""


@dataclass(frozen=True)
class AdvisorState:
    version: int = 1
    symbols: dict[str, AdvisorSymbolState] = field(default_factory=dict)


def load_advisor_state(
    path: str | Path = DEFAULT_ADVISOR_STATE_PATH,
) -> AdvisorState:
    state_path = Path(path)
    if not state_path.exists():
        return AdvisorState()
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8-sig"))
        symbols = {
            symbol.upper(): AdvisorSymbolState(**values)
            for symbol, values in (payload.get("symbols") or {}).items()
        }
        return AdvisorState(
            version=int(payload.get("version") or 1),
            symbols=symbols,
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"추천 상태 파일을 읽을 수 없습니다: {state_path}") from exc


def save_advisor_state(
    state: AdvisorState,
    path: str | Path = DEFAULT_ADVISOR_STATE_PATH,
) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
