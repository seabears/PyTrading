"""매수·매도 규칙이 함께 사용하는 기술 지표 계산."""
from __future__ import annotations

from collections.abc import Sequence
from statistics import fmean

from pytrading.stocks.models import StockCandle


def simple_moving_average(candles: Sequence[StockCandle], window: int) -> float | None:
    """최근 window개 종가의 단순 이동평균을 반환한다."""

    if window < 1:
        raise ValueError("이동평균 기간은 1 이상이어야 합니다.")
    if len(candles) < window:
        return None
    return fmean(candle.close for candle in candles[-window:])


def moving_average_cross_values(
    candles: Sequence[StockCandle],
    short_window: int,
    long_window: int,
) -> tuple[float, float, float, float] | None:
    """직전 봉과 현재 봉의 단기·장기 이동평균을 계산한다."""

    if short_window < 1:
        raise ValueError("단기 이동평균 기간은 1 이상이어야 합니다.")
    if long_window <= short_window:
        raise ValueError("장기 이동평균 기간은 단기 기간보다 커야 합니다.")
    if len(candles) <= long_window:
        return None

    closes = [candle.close for candle in candles]
    return (
        fmean(closes[-short_window - 1 : -1]),
        fmean(closes[-short_window:]),
        fmean(closes[-long_window - 1 : -1]),
        fmean(closes[-long_window:]),
    )
