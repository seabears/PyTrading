"""과거 캔들과 보유 가격으로 매도 신호를 만드는 함수."""
from __future__ import annotations

from collections.abc import Sequence

from pytrading.stocks.models import StockCandle
from pytrading.strategies.indicators import moving_average_cross_values


def create_sell_signal(
    candles: Sequence[StockCandle],
    *,
    short_window: int = 5,
    long_window: int = 20,
    entry_price: float | None = None,
    highest_price: float | None = None,
    stop_loss_rate: float = 0.05,
    trailing_stop_rate: float = 0.07,
) -> bool:
    """
    이동평균 하향 돌파, 고정 손절, 트레일링 스톱 중 하나를 확인한다.

    entry_price를 전달하면 매수가 대비 stop_loss_rate 하락 시 매도한다.
    highest_price를 전달하면 보유 중 최고가 대비 trailing_stop_rate 하락 시 매도한다.
    두 가격을 전달하지 않으면 이동평균 하향 돌파만 사용한다.
    """

    _validate_rate("손절률", stop_loss_rate)
    _validate_rate("트레일링 스톱률", trailing_stop_rate)
    if not candles:
        return False

    current_close = candles[-1].close
    if entry_price is not None:
        if entry_price <= 0:
            raise ValueError("매수 가격은 0보다 커야 합니다.")
        if current_close <= entry_price * (1.0 - stop_loss_rate):
            return True

    if highest_price is not None:
        if highest_price <= 0:
            raise ValueError("보유 중 최고가는 0보다 커야 합니다.")
        if current_close <= highest_price * (1.0 - trailing_stop_rate):
            return True

    averages = moving_average_cross_values(candles, short_window, long_window)
    if averages is None:
        return False
    previous_short, current_short, previous_long, current_long = averages
    return previous_short >= previous_long and current_short < current_long


def _validate_rate(name: str, value: float) -> None:
    if not 0 <= value < 1:
        raise ValueError(f"{name}은 0 이상 1 미만이어야 합니다.")
