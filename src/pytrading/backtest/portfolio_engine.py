"""다중 종목 모멘텀 포트폴리오 백테스트 엔진."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math

from pytrading.backtest.metrics import (
    calculate_annual_returns,
    calculate_cagr,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    parse_trading_date,
)
from pytrading.backtest.models import EquityPoint
from pytrading.backtest.portfolio_models import (
    PortfolioBacktestConfig,
    PortfolioBacktestResult,
    PortfolioTrade,
)
from pytrading.stocks.models import StockCandle
from pytrading.strategies.indicators import simple_moving_average
from pytrading.strategies.sell import create_sell_signal
from pytrading.strategies.stock_selector import select_investment_targets


@dataclass
class _PortfolioPosition:
    symbol: str
    quantity: int
    entry_time: str
    entry_price: float
    entry_fee: float
    highest_price: float


class PortfolioBacktestEngine:
    """
    여러 종목을 주기적으로 평가해 최대 N종목에 동일 비중으로 투자한다.

    모든 선정·매도 판단은 당일 종가까지의 데이터로 수행하고 다음 거래일
    시가에 체결해 미래 정보 참조를 막는다.
    """

    strategy_name = "추세·모멘텀 포트폴리오"

    def __init__(self, config: PortfolioBacktestConfig | None = None):
        self.config = config or PortfolioBacktestConfig()

    def run(
        self,
        histories: Mapping[str, Sequence[StockCandle]],
    ) -> PortfolioBacktestResult:
        prepared = _prepare_histories(histories)
        all_dates = sorted({day for series in prepared.values() for day in series})
        if len(all_dates) < 2:
            raise ValueError("포트폴리오 백테스트에는 최소 2거래일이 필요합니다.")

        minimum_required = max(
            self.config.trend_window,
            self.config.momentum_window + 1,
            self.config.volatility_window + 1,
        )
        if len(all_dates) < minimum_required:
            raise ValueError(
                f"전략 계산에 최소 {minimum_required}거래일이 필요합니다. "
                f"현재 {len(all_dates)}거래일입니다."
            )

        cash = self.config.initial_cash
        positions: dict[str, _PortfolioPosition] = {}
        histories_to_date: dict[str, list[StockCandle]] = {
            symbol: [] for symbol in prepared
        }
        last_close: dict[str, float] = {}
        pending_sells: dict[str, str] = {}
        pending_buys: list[str] = []
        trades: list[PortfolioTrade] = []
        equity_curve: list[EquityPoint] = []
        total_fees = 0.0

        for day_index, trading_day in enumerate(all_dates):
            today = {
                symbol: series[trading_day]
                for symbol, series in prepared.items()
                if trading_day in series
            }

            # 전날 종가에 결정한 매도를 오늘 시가에 먼저 체결해 현금을 확보한다.
            for symbol, reason in list(pending_sells.items()):
                candle = today.get(symbol)
                position = positions.get(symbol)
                if candle is None or position is None:
                    continue
                cash, trade = self._sell(cash, position, candle.time, candle.open, reason)
                total_fees += trade.exit_fee
                trades.append(trade)
                positions.pop(symbol)
                pending_sells.pop(symbol)

            # 매도 후 평가자산을 기준으로 종목당 최대 비중을 계산한다.
            equity_at_open = cash + sum(
                position.quantity
                * (today[symbol].open if symbol in today else last_close.get(symbol, position.entry_price))
                for symbol, position in positions.items()
            )
            minimum_cash = equity_at_open * self.config.minimum_cash_rate
            target_value = (
                equity_at_open * (1.0 - self.config.minimum_cash_rate)
                / self.config.maximum_positions
            )

            for symbol in list(pending_buys):
                if len(positions) >= self.config.maximum_positions:
                    break
                candle = today.get(symbol)
                if candle is None or symbol in positions:
                    continue
                available_cash = max(0.0, cash - minimum_cash)
                budget = min(target_value, available_cash)
                cash, position, fee = self._buy(cash, symbol, candle, budget)
                if position is not None:
                    positions[symbol] = position
                    total_fees += fee
            pending_buys = []

            # 오늘 봉을 추가한 후 종가 기준 신호와 평가금액을 계산한다.
            for symbol, candle in today.items():
                histories_to_date[symbol].append(candle)
                last_close[symbol] = candle.close
                if symbol in positions:
                    positions[symbol].highest_price = max(
                        positions[symbol].highest_price,
                        candle.high,
                    )

            equity = cash + sum(
                position.quantity * last_close.get(symbol, position.entry_price)
                for symbol, position in positions.items()
            )
            equity_curve.append(EquityPoint(trading_day.isoformat(), equity))

            # 손절·트레일링 스톱·단기 추세 이탈은 다음 거래일 매도로 예약한다.
            for symbol, position in positions.items():
                candles = histories_to_date[symbol]
                if not candles:
                    continue
                exit_average = simple_moving_average(
                    candles,
                    self.config.exit_moving_average_window,
                )
                if exit_average is not None and candles[-1].close < exit_average:
                    pending_sells[symbol] = "청산 이동평균 이탈"
                    continue
                if create_sell_signal(
                    candles,
                    short_window=self.config.exit_moving_average_window,
                    long_window=self.config.trend_window,
                    entry_price=position.entry_price,
                    highest_price=position.highest_price,
                    stop_loss_rate=self.config.stop_loss_rate,
                    trailing_stop_rate=self.config.trailing_stop_rate,
                ):
                    pending_sells[symbol] = "손절·트레일링 또는 추세 하락"

            # 충분한 데이터가 쌓인 뒤 정해진 주기마다 투자 대상을 다시 선정한다.
            if (
                day_index + 1 >= minimum_required
                and (day_index + 1 - minimum_required) % self.config.rebalance_interval == 0
            ):
                targets = select_investment_targets(
                    histories_to_date,
                    long_window=self.config.trend_window,
                    momentum_window=self.config.momentum_window,
                    volume_window=self.config.volume_window,
                    minimum_average_trading_value=self.config.minimum_average_trading_value,
                    volatility_window=self.config.volatility_window,
                    maximum_annualized_volatility=self.config.maximum_annualized_volatility,
                    maximum_targets=self.config.maximum_positions,
                )
                target_set = set(targets)
                for symbol in positions:
                    if symbol not in target_set:
                        pending_sells[symbol] = "모멘텀 순위 제외"
                pending_buys = [
                    symbol
                    for symbol in targets
                    if symbol not in positions and symbol not in pending_sells
                ]

        # 마지막 날에도 남아 있는 포지션은 종가로 청산해 성과를 확정한다.
        last_day = all_dates[-1]
        for symbol, position in list(positions.items()):
            candle = prepared[symbol].get(last_day)
            raw_price = candle.close if candle else last_close[symbol]
            time = candle.time if candle else last_day.isoformat()
            cash, trade = self._sell(cash, position, time, raw_price, "백테스트 종료")
            total_fees += trade.exit_fee
            trades.append(trade)
        equity_curve[-1] = EquityPoint(last_day.isoformat(), cash)

        start_day = all_dates[0]
        elapsed_start_value = self.config.initial_cash
        total_return = (cash / elapsed_start_value - 1.0) * 100.0
        cagr = calculate_cagr(elapsed_start_value, cash, start_day, last_day)
        benchmark_return = _equal_weight_benchmark_return(prepared)
        benchmark_final = elapsed_start_value * (1.0 + benchmark_return / 100.0)
        benchmark_cagr = calculate_cagr(
            elapsed_start_value,
            benchmark_final,
            start_day,
            last_day,
        )
        wins = sum(1 for trade in trades if trade.profit > 0)
        validation_index = max(
            1,
            min(
                len(equity_curve) - 1,
                int(len(equity_curve) * (1.0 - self.config.validation_ratio)),
            ),
        )
        validation_base_point = equity_curve[validation_index - 1]
        validation_start_point = equity_curve[validation_index]
        validation_start_day = parse_trading_date(validation_base_point.time)
        validation_end_day = parse_trading_date(equity_curve[-1].time)
        validation_return = (
            (cash / validation_base_point.equity - 1.0) * 100.0
            if validation_base_point.equity > 0
            else 0.0
        )
        validation_cagr = calculate_cagr(
            validation_base_point.equity,
            cash,
            validation_start_day,
            validation_end_day,
        )
        maximum_drawdown = calculate_max_drawdown(equity_curve)

        return PortfolioBacktestResult(
            strategy_name=self.strategy_name,
            start_time=start_day.isoformat(),
            end_time=last_day.isoformat(),
            initial_cash=elapsed_start_value,
            final_equity=cash,
            total_return_rate=total_return,
            cagr_rate=cagr,
            benchmark_return_rate=benchmark_return,
            benchmark_cagr_rate=benchmark_cagr,
            max_drawdown_rate=maximum_drawdown,
            sharpe_ratio=calculate_sharpe_ratio(equity_curve),
            trade_count=len(trades),
            win_rate=(wins / len(trades) * 100.0) if trades else 0.0,
            total_fees=total_fees,
            target_cagr_rate=self.config.target_cagr_rate,
            maximum_allowed_drawdown_rate=self.config.maximum_allowed_drawdown_rate,
            target_achieved=(
                cagr >= self.config.target_cagr_rate
                and validation_cagr >= self.config.target_cagr_rate
                and maximum_drawdown >= -self.config.maximum_allowed_drawdown_rate
            ),
            validation_start_time=validation_start_point.time,
            validation_return_rate=validation_return,
            validation_cagr_rate=validation_cagr,
            annual_returns=calculate_annual_returns(equity_curve, elapsed_start_value),
            trades=trades,
            equity_curve=equity_curve,
        )

    def _buy(
        self,
        cash: float,
        symbol: str,
        candle: StockCandle,
        budget: float,
    ) -> tuple[float, _PortfolioPosition | None, float]:
        price = candle.open * (1.0 + self.config.slippage_rate)
        quantity = math.floor(budget / (price * (1.0 + self.config.commission_rate)))
        if quantity < 1:
            return cash, None, 0.0
        amount = quantity * price
        fee = amount * self.config.commission_rate
        return cash - amount - fee, _PortfolioPosition(
            symbol=symbol,
            quantity=quantity,
            entry_time=candle.time,
            entry_price=price,
            entry_fee=fee,
            highest_price=candle.high,
        ), fee

    def _sell(
        self,
        cash: float,
        position: _PortfolioPosition,
        time: str,
        raw_price: float,
        reason: str,
    ) -> tuple[float, PortfolioTrade]:
        price = raw_price * (1.0 - self.config.slippage_rate)
        amount = position.quantity * price
        exit_fee = amount * self.config.commission_rate
        net_proceeds = amount - exit_fee
        entry_cost = position.quantity * position.entry_price + position.entry_fee
        profit = net_proceeds - entry_cost
        return cash + net_proceeds, PortfolioTrade(
            symbol=position.symbol,
            entry_time=position.entry_time,
            exit_time=time,
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=price,
            entry_fee=position.entry_fee,
            exit_fee=exit_fee,
            profit=profit,
            return_rate=profit / entry_cost * 100.0,
            exit_reason=reason,
        )


def _prepare_histories(
    histories: Mapping[str, Sequence[StockCandle]],
) -> dict[str, dict[object, StockCandle]]:
    if len(histories) < 2:
        raise ValueError("포트폴리오 백테스트에는 최소 2종목이 필요합니다.")
    prepared: dict[str, dict[object, StockCandle]] = {}
    for symbol, candles in histories.items():
        if not candles:
            continue
        prepared[symbol.upper()] = {
            parse_trading_date(candle.time): candle for candle in candles
        }
    if len(prepared) < 2:
        raise ValueError("가격 데이터가 있는 종목이 최소 2개 필요합니다.")
    return prepared


def _equal_weight_benchmark_return(
    prepared: Mapping[str, Mapping[object, StockCandle]],
) -> float:
    """각 종목을 처음부터 끝까지 동일 비중 보유한 비교 수익률."""

    returns: list[float] = []
    for series in prepared.values():
        ordered = [series[day] for day in sorted(series)]
        if ordered and ordered[0].open > 0:
            returns.append(ordered[-1].close / ordered[0].open - 1.0)
    return sum(returns) / len(returns) * 100.0 if returns else 0.0
