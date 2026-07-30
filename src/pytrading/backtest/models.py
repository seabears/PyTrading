"""백테스트 설정과 결과 데이터 모델."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BacktestConfig:
    """금액과 거래 비용 관련 설정."""

    initial_cash: float = 10_000_000.0
    commission_rate: float = 0.00015
    slippage_rate: float = 0.0005

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("초기 자금은 0보다 커야 합니다.")
        if self.commission_rate < 0 or self.slippage_rate < 0:
            raise ValueError("수수료와 슬리피지는 0 이상이어야 합니다.")


@dataclass(frozen=True)
class Trade:
    """매수부터 매도까지 완료된 한 번의 거래."""

    entry_time: str
    exit_time: str
    quantity: int
    entry_price: float
    exit_price: float
    entry_fee: float
    exit_fee: float
    profit: float
    return_rate: float


@dataclass(frozen=True)
class EquityPoint:
    """날짜별 현금과 보유 주식을 합친 평가 자산."""

    time: str
    equity: float


@dataclass(frozen=True)
class BacktestResult:
    """전략 비교와 보고서 작성에 필요한 핵심 성과."""

    strategy_name: str
    initial_cash: float
    final_equity: float
    total_return_rate: float
    benchmark_return_rate: float
    max_drawdown_rate: float
    trade_count: int
    win_rate: float
    total_fees: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)
