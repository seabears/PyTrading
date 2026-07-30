"""미래 참조를 방지하는 단일 종목 롱 전용 백테스트 엔진."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from pytrading.backtest.models import BacktestConfig, BacktestResult, EquityPoint, Trade
from pytrading.stocks.models import StockCandle
from pytrading.strategies.base import Signal, Strategy


@dataclass
class _OpenPosition:
    quantity: int
    entry_time: str
    entry_price: float
    entry_fee: float


class BacktestEngine:
    """
    한 종목을 전액 매수하거나 전량 매도하는 백테스트 엔진.

    전략이 종가로 만든 신호는 다음 거래일 시가에 체결한다. 마지막 날에도
    주식을 보유했다면 최종 손익 확정을 위해 마지막 종가에 강제 청산한다.
    """

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()

    def run(self, candles: Sequence[StockCandle], strategy: Strategy) -> BacktestResult:
        if len(candles) < 2:
            raise ValueError("백테스트에는 최소 2개의 캔들이 필요합니다.")

        cash = self.config.initial_cash
        position: _OpenPosition | None = None
        pending_signal = Signal.HOLD
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []
        total_fees = 0.0

        for index, candle in enumerate(candles):
            # 전날 종가에 확정된 신호를 오늘 시가에 체결한다.
            if pending_signal is Signal.BUY and position is None:
                cash, position, fee = self._buy(cash, candle)
                total_fees += fee
            elif pending_signal is Signal.SELL and position is not None:
                cash, trade = self._sell(cash, position, candle.time, candle.open)
                total_fees += trade.exit_fee
                trades.append(trade)
                position = None

            equity = cash + (position.quantity * candle.close if position else 0.0)
            equity_curve.append(EquityPoint(candle.time, equity))
            pending_signal = strategy.generate_signal(candles[: index + 1])

        # 미청산 포지션은 마지막 종가에 매도해 실현 손익으로 만든다.
        if position is not None:
            last = candles[-1]
            cash, trade = self._sell(cash, position, last.time, last.close)
            total_fees += trade.exit_fee
            trades.append(trade)
            equity_curve[-1] = EquityPoint(last.time, cash)

        total_return = (cash / self.config.initial_cash - 1.0) * 100.0
        benchmark_return = (candles[-1].close / candles[0].open - 1.0) * 100.0
        wins = sum(1 for trade in trades if trade.profit > 0)

        return BacktestResult(
            strategy_name=strategy.name,
            initial_cash=self.config.initial_cash,
            final_equity=cash,
            total_return_rate=total_return,
            benchmark_return_rate=benchmark_return,
            max_drawdown_rate=_maximum_drawdown(equity_curve),
            trade_count=len(trades),
            win_rate=(wins / len(trades) * 100.0) if trades else 0.0,
            total_fees=total_fees,
            trades=trades,
            equity_curve=equity_curve,
        )

    def _buy(self, cash: float, candle: StockCandle) -> tuple[float, _OpenPosition | None, float]:
        # 매수 슬리피지는 체결가를 불리하게 위로 조정한다.
        price = candle.open * (1.0 + self.config.slippage_rate)
        quantity = math.floor(cash / (price * (1.0 + self.config.commission_rate)))
        if quantity < 1:
            return cash, None, 0.0

        amount = quantity * price
        fee = amount * self.config.commission_rate
        return cash - amount - fee, _OpenPosition(quantity, candle.time, price, fee), fee

    def _sell(
        self, cash: float, position: _OpenPosition, time: str, raw_price: float
    ) -> tuple[float, Trade]:
        # 매도 슬리피지는 체결가를 불리하게 아래로 조정한다.
        price = raw_price * (1.0 - self.config.slippage_rate)
        amount = position.quantity * price
        fee = amount * self.config.commission_rate
        net_proceeds = amount - fee
        entry_cost = position.quantity * position.entry_price + position.entry_fee
        profit = net_proceeds - entry_cost
        return_rate = profit / entry_cost * 100.0
        return cash + net_proceeds, Trade(
            entry_time=position.entry_time,
            exit_time=time,
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=price,
            entry_fee=position.entry_fee,
            exit_fee=fee,
            profit=profit,
            return_rate=return_rate,
        )


def _maximum_drawdown(equity_curve: Sequence[EquityPoint]) -> float:
    """고점 대비 최대 하락률(MDD)을 음수 백분율로 계산한다."""

    peak = equity_curve[0].equity
    maximum_drawdown = 0.0
    for point in equity_curve:
        peak = max(peak, point.equity)
        drawdown = (point.equity / peak - 1.0) * 100.0
        maximum_drawdown = min(maximum_drawdown, drawdown)
    return maximum_drawdown
