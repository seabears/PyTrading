"""모든 매매 전략이 따르는 공통 인터페이스."""
from __future__ import annotations

from enum import Enum
from typing import Protocol, Sequence

from pytrading.stocks.models import StockCandle


class Signal(str, Enum):
    """전략이 백테스트 엔진에 전달하는 주문 방향."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Strategy(Protocol):
    """새 전략을 추가할 때 구현해야 하는 최소 인터페이스."""

    @property
    def name(self) -> str:
        """결과 보고서에 표시할 전략 이름."""

    def generate_signal(self, candles: Sequence[StockCandle]) -> Signal:
        """현재 시점까지 공개된 캔들만 사용해 신호를 반환한다."""
