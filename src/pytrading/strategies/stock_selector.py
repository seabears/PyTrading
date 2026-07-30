"""여러 종목의 과거 데이터에서 투자할 종목을 고르는 함수."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from statistics import fmean
from statistics import pstdev

from pytrading.stocks.models import StockCandle


def select_investment_targets(
    histories: Mapping[str, Sequence[StockCandle]],
    *,
    long_window: int = 20,
    momentum_window: int = 20,
    volume_window: int = 20,
    minimum_average_volume: float = 0,
    minimum_average_trading_value: float = 0,
    volatility_window: int = 20,
    maximum_annualized_volatility: float | None = None,
    maximum_targets: int = 10,
) -> list[str]:
    """
    추세·모멘텀·거래량 조건을 만족하는 종목을 투자 후보로 반환한다.

    선택 규칙:
    1. 지표 계산에 필요한 과거 데이터가 충분해야 한다.
    2. 현재 종가가 장기 이동평균보다 높아야 한다.
    3. 최근 모멘텀(기간 수익률)이 양수여야 한다.
    4. 최근 평균 거래량·거래대금이 설정한 최솟값 이상이어야 한다.
    5. 설정한 최대 연환산 변동성을 초과하면 제외한다.
    6. 통과 종목을 모멘텀이 높은 순서로 정렬한다.
    """

    _validate_positive("장기 이동평균 기간", long_window)
    _validate_positive("모멘텀 기간", momentum_window)
    _validate_positive("평균 거래량 기간", volume_window)
    _validate_positive("변동성 기간", volatility_window)
    _validate_positive("최대 투자 대상 수", maximum_targets)
    if minimum_average_volume < 0 or minimum_average_trading_value < 0:
        raise ValueError("최소 평균 거래량과 거래대금은 0 이상이어야 합니다.")
    if maximum_annualized_volatility is not None and maximum_annualized_volatility <= 0:
        raise ValueError("최대 연환산 변동성은 0보다 커야 합니다.")

    required_count = max(long_window, momentum_window + 1, volume_window)
    if maximum_annualized_volatility is not None:
        required_count = max(required_count, volatility_window + 1)
    scored_targets: list[tuple[str, float]] = []

    for symbol, candles in histories.items():
        if len(candles) < required_count:
            continue

        recent_close = candles[-1].close
        long_average = fmean(candle.close for candle in candles[-long_window:])
        average_volume = fmean(candle.volume for candle in candles[-volume_window:])
        average_trading_value = fmean(
            candle.close * candle.volume for candle in candles[-volume_window:]
        )
        momentum_base = candles[-momentum_window - 1].close

        # 가격과 거래량이 비정상인 데이터는 투자 후보에서 제외한다.
        if (
            recent_close <= 0
            or momentum_base <= 0
            or average_volume < minimum_average_volume
            or average_trading_value < minimum_average_trading_value
        ):
            continue

        momentum = recent_close / momentum_base - 1.0
        if maximum_annualized_volatility is not None:
            recent = candles[-volatility_window - 1 :]
            daily_returns = [
                recent[index].close / recent[index - 1].close - 1.0
                for index in range(1, len(recent))
                if recent[index - 1].close > 0
            ]
            annualized_volatility = pstdev(daily_returns) * math.sqrt(252)
            if annualized_volatility > maximum_annualized_volatility:
                continue

        if recent_close > long_average and momentum > 0:
            scored_targets.append((symbol.upper(), momentum))

    scored_targets.sort(key=lambda item: (-item[1], item[0]))
    return [symbol for symbol, _ in scored_targets[:maximum_targets]]


def _validate_positive(name: str, value: int) -> None:
    if value < 1:
        raise ValueError(f"{name}은 1 이상이어야 합니다.")
