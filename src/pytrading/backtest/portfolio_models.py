"""다중 종목 포트폴리오 백테스트 설정과 결과 모델."""
from __future__ import annotations

from dataclasses import dataclass, field

from pytrading.backtest.models import EquityPoint


@dataclass(frozen=True)
class PortfolioBacktestConfig:
    """가격·거래량 기반 모멘텀 포트폴리오의 기본 설정."""

    initial_cash: float = 10_000_000.0
    commission_rate: float = 0.00015
    slippage_rate: float = 0.0005
    maximum_positions: int = 5
    minimum_cash_rate: float = 0.05
    rebalance_interval: int = 20
    trend_window: int = 200
    momentum_window: int = 126
    volume_window: int = 20
    volatility_window: int = 20
    exit_moving_average_window: int = 20
    minimum_average_trading_value: float = 0.0
    maximum_annualized_volatility: float = 0.60
    stop_loss_rate: float = 0.05
    trailing_stop_rate: float = 0.07
    target_cagr_rate: float = 10.0
    maximum_allowed_drawdown_rate: float = 15.0
    validation_ratio: float = 0.30

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("초기 자금은 0보다 커야 합니다.")
        if self.maximum_positions < 1:
            raise ValueError("최대 보유 종목 수는 1 이상이어야 합니다.")
        for name, value in (
            ("리밸런싱 주기", self.rebalance_interval),
            ("추세 기간", self.trend_window),
            ("모멘텀 기간", self.momentum_window),
            ("거래량 기간", self.volume_window),
            ("변동성 기간", self.volatility_window),
            ("청산 이동평균 기간", self.exit_moving_average_window),
        ):
            if value < 1:
                raise ValueError(f"{name}은 1 이상이어야 합니다.")
        if self.trend_window <= self.exit_moving_average_window:
            raise ValueError("추세 기간은 청산 이동평균 기간보다 길어야 합니다.")
        for name, value in (
            ("수수료율", self.commission_rate),
            ("슬리피지율", self.slippage_rate),
            ("최소 현금 비중", self.minimum_cash_rate),
            ("손절률", self.stop_loss_rate),
            ("트레일링 스톱률", self.trailing_stop_rate),
        ):
            if not 0 <= value < 1:
                raise ValueError(f"{name}은 0 이상 1 미만이어야 합니다.")
        if self.maximum_annualized_volatility <= 0:
            raise ValueError("최대 연환산 변동성은 0보다 커야 합니다.")
        if self.minimum_average_trading_value < 0:
            raise ValueError("최소 평균 거래대금은 0 이상이어야 합니다.")
        if self.target_cagr_rate < 0:
            raise ValueError("목표 CAGR은 0 이상이어야 합니다.")
        if self.maximum_allowed_drawdown_rate <= 0:
            raise ValueError("허용 MDD는 0보다 커야 합니다.")
        if not 0 < self.validation_ratio < 1:
            raise ValueError("검증 구간 비율은 0보다 크고 1보다 작아야 합니다.")


@dataclass(frozen=True)
class PortfolioTrade:
    """포트폴리오에서 완료된 종목별 거래."""

    symbol: str
    entry_time: str
    exit_time: str
    quantity: int
    entry_price: float
    exit_price: float
    entry_fee: float
    exit_fee: float
    profit: float
    return_rate: float
    exit_reason: str


@dataclass(frozen=True)
class PortfolioBacktestResult:
    """연 10% 목표와 위험을 함께 판단하는 포트폴리오 성과."""

    strategy_name: str
    start_time: str
    end_time: str
    initial_cash: float
    final_equity: float
    total_return_rate: float
    cagr_rate: float
    benchmark_return_rate: float
    benchmark_cagr_rate: float
    max_drawdown_rate: float
    sharpe_ratio: float
    trade_count: int
    win_rate: float
    total_fees: float
    target_cagr_rate: float
    maximum_allowed_drawdown_rate: float
    target_achieved: bool
    validation_start_time: str
    validation_return_rate: float
    validation_cagr_rate: float
    annual_returns: dict[int, float] = field(default_factory=dict)
    trades: list[PortfolioTrade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)
