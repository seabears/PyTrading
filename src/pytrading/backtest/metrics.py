"""단일·포트폴리오 백테스트가 공유하는 성과 지표 계산."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
import math
from statistics import fmean, pstdev

from pytrading.backtest.models import EquityPoint


def parse_trading_date(value: str) -> date:
    """KIS와 CSV에서 사용하는 대표 날짜 형식을 date로 변환한다."""

    for date_format in ("%Y%m%d", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value[:19], date_format).date()
        except ValueError:
            continue
    raise ValueError(f"지원하지 않는 거래 날짜 형식입니다: {value}")


def calculate_cagr(initial_value: float, final_value: float, start: date, end: date) -> float:
    """시작·종료 자산으로 연복리수익률(CAGR)을 계산한다."""

    elapsed_years = (end - start).days / 365.25
    if initial_value <= 0 or final_value < 0 or elapsed_years <= 0:
        return 0.0
    return ((final_value / initial_value) ** (1.0 / elapsed_years) - 1.0) * 100.0


def calculate_max_drawdown(equity_curve: Sequence[EquityPoint]) -> float:
    """고점 대비 최대 하락률(MDD)을 음수 백분율로 계산한다."""

    if not equity_curve:
        return 0.0
    peak = equity_curve[0].equity
    maximum_drawdown = 0.0
    for point in equity_curve:
        peak = max(peak, point.equity)
        if peak > 0:
            maximum_drawdown = min(
                maximum_drawdown,
                (point.equity / peak - 1.0) * 100.0,
            )
    return maximum_drawdown


def calculate_sharpe_ratio(equity_curve: Sequence[EquityPoint]) -> float:
    """무위험수익률 0% 가정으로 일간 수익률의 연환산 샤프지수를 계산한다."""

    daily_returns = [
        equity_curve[index].equity / equity_curve[index - 1].equity - 1.0
        for index in range(1, len(equity_curve))
        if equity_curve[index - 1].equity > 0
    ]
    if len(daily_returns) < 2:
        return 0.0
    volatility = pstdev(daily_returns)
    if volatility == 0:
        return 0.0
    return fmean(daily_returns) / volatility * math.sqrt(252)


def calculate_annual_returns(
    equity_curve: Sequence[EquityPoint],
    initial_value: float,
) -> dict[int, float]:
    """각 연도의 첫 기준 자산 대비 연말 수익률을 계산한다."""

    annual_returns: dict[int, float] = {}
    previous_year_end = initial_value
    values_by_year: dict[int, list[float]] = {}
    for point in equity_curve:
        year = parse_trading_date(point.time).year
        values_by_year.setdefault(year, []).append(point.equity)

    for year in sorted(values_by_year):
        year_end = values_by_year[year][-1]
        annual_returns[year] = (
            (year_end / previous_year_end - 1.0) * 100.0
            if previous_year_end > 0
            else 0.0
        )
        previous_year_end = year_end
    return annual_returns
