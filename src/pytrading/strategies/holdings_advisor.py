"""투자 유형별로 현재 보유 종목의 단계형 매매 의견을 만든다."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
import math
from statistics import fmean, pstdev

from pytrading.data.advisor_state import AdvisorState, AdvisorSymbolState
from pytrading.data.holdings_loader import (
    Holding,
    HoldingsPortfolio,
    InvestmentStyle,
)
from pytrading.stocks.models import StockCandle


class AdviceAction(str, Enum):
    SELL_REVIEW = "전량매도 검토"
    REDUCE_50 = "50% 축소"
    REDUCE_25 = "25% 축소"
    WATCH = "주의"
    ADD = "추가매수"
    HOLD = "보유"
    REVIEW = "수동검토"


@dataclass(frozen=True)
class HoldingsAdviceConfig:
    """단계형 보유 종목 전략의 조정 가능한 값."""

    short_window: int = 20
    medium_window: int = 60
    long_window: int = 200
    momentum_window: int = 63
    long_momentum_window: int = 126
    volatility_window: int = 20
    atr_window: int = 14
    rsi_window: int = 14
    confirmation_days: int = 3
    long_confirmation_days: int = 10
    base_stop_loss_rate: float = 0.10
    maximum_stop_loss_rate: float = 0.15
    maximum_annualized_volatility: float = 0.60
    rebalance_band_percent: float = 2.0
    maximum_order_cash_rate: float = 0.25
    maximum_order_account_rate: float = 0.02

    def __post_init__(self) -> None:
        windows = (
            self.short_window,
            self.medium_window,
            self.long_window,
            self.momentum_window,
            self.long_momentum_window,
            self.volatility_window,
            self.atr_window,
            self.rsi_window,
            self.confirmation_days,
            self.long_confirmation_days,
        )
        if any(window < 1 for window in windows):
            raise ValueError("모든 분석 기간은 1 이상이어야 합니다.")
        if not self.short_window < self.medium_window < self.long_window:
            raise ValueError("이동평균 기간은 단기 < 중기 < 장기 순서여야 합니다.")
        if not 0 < self.base_stop_loss_rate <= self.maximum_stop_loss_rate < 1:
            raise ValueError("손절률 범위가 올바르지 않습니다.")
        if self.maximum_annualized_volatility <= 0:
            raise ValueError("최대 연환산 변동성은 0보다 커야 합니다.")
        if not 0 <= self.rebalance_band_percent < 100:
            raise ValueError("리밸런싱 허용 폭이 올바르지 않습니다.")
        if not 0 < self.maximum_order_cash_rate <= 1:
            raise ValueError("1회 현금 사용 한도는 0 초과 1 이하여야 합니다.")
        if not 0 < self.maximum_order_account_rate <= 1:
            raise ValueError("1회 계좌 사용 한도는 0 초과 1 이하여야 합니다.")


@dataclass(frozen=True)
class HoldingAdvice:
    symbol: str
    name: str
    investment_style: InvestmentStyle
    action: AdviceAction
    as_of: str
    current_price_usd: float | None
    return_rate: float | None
    current_weight_percent: float
    suggested_quantity: float
    suggested_amount_usd: float
    reasons: tuple[str, ...]
    previous_action: str = ""
    signal_streak: int = 1


@dataclass(frozen=True)
class HoldingsAdviceResult:
    advices: list[HoldingAdvice]
    estimated_portfolio_value_usd: float
    available_cash_usd: float = 0.0
    remaining_cash_usd: float = 0.0
    updated_state: AdvisorState = field(default_factory=AdvisorState)


@dataclass(frozen=True)
class _Metrics:
    current_price: float
    return_rate: float
    short_average: float
    medium_average: float
    long_average: float
    momentum: float
    long_momentum: float
    volatility: float
    rsi: float
    atr_rate: float
    below_medium: bool
    below_long: bool
    below_long_persistent: bool
    above_long: bool


def analyze_holdings(
    portfolio: HoldingsPortfolio,
    histories: Mapping[str, Sequence[StockCandle]],
    config: HoldingsAdviceConfig | None = None,
    *,
    available_cash_usd: float = 0.0,
    advisor_state: AdvisorState | None = None,
) -> HoldingsAdviceResult:
    """보유 목록, 일봉, 이전 상태로 전략별 단계형 의견을 계산한다."""

    if available_cash_usd < 0 or not math.isfinite(available_cash_usd):
        raise ValueError("추가 투자 가능 현금은 0 이상의 유한수여야 합니다.")
    settings = config or HoldingsAdviceConfig()
    previous_state = advisor_state or AdvisorState()
    normalized_histories = {
        symbol.upper(): sorted(candles, key=lambda candle: candle.time)
        for symbol, candles in histories.items()
        if candles
    }
    current_values = {
        holding.symbol: _estimated_current_value(holding, normalized_histories)
        for holding in portfolio.holdings
    }
    securities_value = sum(current_values.values())
    account_value = securities_value + available_cash_usd
    if account_value <= 0:
        raise ValueError("계좌 평가금액은 0보다 커야 합니다.")

    remaining_cash = available_cash_usd
    updated_symbols = dict(previous_state.symbols)
    advices: list[HoldingAdvice] = []
    for holding in portfolio.holdings:
        candles = normalized_histories.get(holding.symbol, [])
        prior = previous_state.symbols.get(holding.symbol)
        symbol_state = _prepare_symbol_state(holding, candles, prior)
        per_order_budget = min(
            remaining_cash,
            available_cash_usd * settings.maximum_order_cash_rate,
            account_value * settings.maximum_order_account_rate,
        )
        advice = _analyze_holding(
            holding,
            candles,
            symbol_state,
            current_values[holding.symbol],
            account_value,
            per_order_budget,
            settings,
        )
        streak = _signal_streak(prior, advice.action, advice.as_of)
        advice = replace(
            advice,
            previous_action=prior.last_action if prior else "",
            signal_streak=streak,
        )
        updated_symbols[holding.symbol] = replace(
            symbol_state,
            last_action=advice.action.value,
            signal_streak=streak,
            last_signal_date=advice.as_of,
        )
        if advice.action == AdviceAction.ADD:
            remaining_cash = max(0.0, remaining_cash - advice.suggested_amount_usd)
        advices.append(advice)

    priority = {
        AdviceAction.SELL_REVIEW: 0,
        AdviceAction.REDUCE_50: 1,
        AdviceAction.REDUCE_25: 2,
        AdviceAction.WATCH: 3,
        AdviceAction.ADD: 4,
        AdviceAction.HOLD: 5,
        AdviceAction.REVIEW: 6,
    }
    advices.sort(key=lambda item: (priority[item.action], -item.current_weight_percent))
    return HoldingsAdviceResult(
        advices=advices,
        estimated_portfolio_value_usd=securities_value,
        available_cash_usd=available_cash_usd,
        remaining_cash_usd=remaining_cash,
        updated_state=AdvisorState(
            version=previous_state.version,
            symbols=updated_symbols,
        ),
    )


def _analyze_holding(
    holding: Holding,
    candles: Sequence[StockCandle],
    state: AdvisorSymbolState,
    current_value: float,
    account_value: float,
    buy_budget: float,
    config: HoldingsAdviceConfig,
) -> HoldingAdvice:
    current_weight = current_value / account_value
    required_count = max(
        config.long_window + config.long_confirmation_days - 1,
        config.long_momentum_window + 1,
        config.volatility_window + 1,
        config.atr_window + 1,
        config.rsi_window + 1,
    )
    if len(candles) < required_count:
        return _review_advice(holding, candles, current_weight, required_count)

    metrics = _calculate_metrics(holding, candles, config)
    if holding.investment_style == InvestmentStyle.CORE:
        return _analyze_core(
            holding,
            candles[-1].time,
            metrics,
            current_weight,
            account_value,
            buy_budget,
            config,
        )
    if holding.investment_style == InvestmentStyle.TACTICAL:
        return _analyze_tactical(
            holding,
            candles[-1].time,
            metrics,
            state,
            current_weight,
            account_value,
            buy_budget,
            config,
        )
    return _analyze_income(
        holding,
        candles[-1].time,
        metrics,
        current_weight,
        account_value,
        config,
    )


def _analyze_core(
    holding: Holding,
    as_of: str,
    metrics: _Metrics,
    current_weight: float,
    account_value: float,
    buy_budget: float,
    config: HoldingsAdviceConfig,
) -> HoldingAdvice:
    if (
        metrics.below_long_persistent
        and metrics.medium_average < metrics.long_average
        and metrics.long_momentum < 0
    ):
        return _action_advice(
            holding,
            AdviceAction.REDUCE_50,
            as_of,
            metrics,
            current_weight,
            _percentage_quantity(holding.quantity, 0.50),
            ("200일선 10일 이탈", "60일선 < 200일선", f"6개월 {metrics.long_momentum:+.1%}"),
        )
    if metrics.below_long_persistent:
        return _action_advice(
            holding,
            AdviceAction.REDUCE_25,
            as_of,
            metrics,
            current_weight,
            _percentage_quantity(holding.quantity, 0.25),
            ("200일선 10일 이탈",),
        )
    overweight = current_weight * 100.0 > holding.maximum_weight_percent
    if overweight:
        excess = (
            holding.quantity * metrics.current_price
            - account_value * holding.maximum_weight_percent / 100.0
        ) / metrics.current_price
        quantity = min(
            _percentage_quantity(holding.quantity, 0.25),
            _sell_quantity(holding.quantity, excess),
        )
        return _action_advice(
            holding,
            AdviceAction.REDUCE_25,
            as_of,
            metrics,
            current_weight,
            quantity,
            (
                f"비중 {current_weight:.1%} > 상한 "
                f"{holding.maximum_weight_percent:.0f}%",
                "1회 최대 25% 축소",
            ),
        )
    if metrics.below_medium:
        return _action_advice(
            holding,
            AdviceAction.WATCH,
            as_of,
            metrics,
            current_weight,
            0.0,
            ("60일선 3일 이탈", "장기 핵심은 즉시 매도하지 않음"),
        )
    healthy = (
        metrics.above_long
        and metrics.medium_average > metrics.long_average
        and metrics.momentum > 0
        and 45 <= metrics.rsi < 70
    )
    return _add_or_hold(
        holding,
        as_of,
        metrics,
        current_weight,
        account_value,
        buy_budget,
        healthy,
        config,
        ("200일 상승", "60일선 > 200일선", f"3개월 {metrics.momentum:+.1%}"),
    )


def _analyze_tactical(
    holding: Holding,
    as_of: str,
    metrics: _Metrics,
    state: AdvisorSymbolState,
    current_weight: float,
    account_value: float,
    buy_budget: float,
    config: HoldingsAdviceConfig,
) -> HoldingAdvice:
    if state.protected_quantity > 0 and state.protected_entry_price_usd > 0:
        stop_rate = min(
            config.maximum_stop_loss_rate,
            max(config.base_stop_loss_rate, metrics.atr_rate * 2.0),
        )
        stop_price = state.protected_entry_price_usd * (1.0 - stop_rate)
        if metrics.current_price <= stop_price:
            return _action_advice(
                holding,
                AdviceAction.SELL_REVIEW,
                as_of,
                metrics,
                current_weight,
                min(holding.quantity, state.protected_quantity),
                (f"신규 매수분 손절선 -{stop_rate:.1%}", "기존 보유분에는 미적용"),
            )
    if (
        metrics.below_long_persistent
        and metrics.medium_average < metrics.long_average
        and metrics.momentum < 0
    ):
        escalate_to_exit = (
            state.last_action == AdviceAction.REDUCE_50.value
            and state.signal_streak >= 2
        )
        return _action_advice(
            holding,
            (
                AdviceAction.SELL_REVIEW
                if escalate_to_exit
                else AdviceAction.REDUCE_50
            ),
            as_of,
            metrics,
            current_weight,
            (
                holding.quantity
                if escalate_to_exit
                else _percentage_quantity(holding.quantity, 0.50)
            ),
            (
                "200일선 10일 이탈",
                "60일선 < 200일선",
                f"3개월 {metrics.momentum:+.1%}",
                (
                    "50% 축소 신호 3회 확인"
                    if escalate_to_exit
                    else "첫 단계는 50% 축소"
                ),
            ),
        )
    if metrics.below_long and metrics.momentum < 0:
        return _action_advice(
            holding,
            AdviceAction.REDUCE_50,
            as_of,
            metrics,
            current_weight,
            _percentage_quantity(holding.quantity, 0.50),
            ("200일선 3일 이탈", f"3개월 {metrics.momentum:+.1%}"),
        )
    weak_reasons: list[str] = []
    if metrics.below_medium:
        weak_reasons.append("60일선 3일 이탈")
    if metrics.momentum < 0:
        weak_reasons.append(f"3개월 {metrics.momentum:+.1%}")
    if metrics.volatility > config.maximum_annualized_volatility:
        weak_reasons.append(f"변동성 {metrics.volatility:.1%}")
    if current_weight * 100.0 > holding.maximum_weight_percent:
        weak_reasons.append(
            f"비중 {current_weight:.1%} > 상한 {holding.maximum_weight_percent:.0f}%"
        )
    if weak_reasons:
        return _action_advice(
            holding,
            AdviceAction.REDUCE_25,
            as_of,
            metrics,
            current_weight,
            _percentage_quantity(holding.quantity, 0.25),
            tuple(weak_reasons),
        )
    healthy = (
        metrics.above_long
        and metrics.short_average > metrics.medium_average
        and metrics.momentum > 0
        and 45 <= metrics.rsi < 70
        and metrics.volatility <= config.maximum_annualized_volatility
    )
    return _add_or_hold(
        holding,
        as_of,
        metrics,
        current_weight,
        account_value,
        buy_budget,
        healthy,
        config,
        ("200일 상승", "20일선 > 60일선", f"3개월 {metrics.momentum:+.1%}"),
    )


def _analyze_income(
    holding: Holding,
    as_of: str,
    metrics: _Metrics,
    current_weight: float,
    account_value: float,
    config: HoldingsAdviceConfig,
) -> HoldingAdvice:
    if current_weight * 100.0 > holding.maximum_weight_percent:
        return _action_advice(
            holding,
            AdviceAction.REDUCE_25,
            as_of,
            metrics,
            current_weight,
            _percentage_quantity(holding.quantity, 0.25),
            (
                f"비중 {current_weight:.1%} > 상한 "
                f"{holding.maximum_weight_percent:.0f}%",
            ),
        )
    if metrics.below_long_persistent and metrics.long_momentum < 0:
        return _action_advice(
            holding,
            AdviceAction.REDUCE_25,
            as_of,
            metrics,
            current_weight,
            _percentage_quantity(holding.quantity, 0.25),
            ("200일선 10일 이탈", f"6개월 {metrics.long_momentum:+.1%}"),
        )
    if metrics.below_medium:
        return _action_advice(
            holding,
            AdviceAction.WATCH,
            as_of,
            metrics,
            current_weight,
            0.0,
            ("60일선 3일 이탈", "배당 유지 여부 확인"),
        )
    target_gap = holding.target_weight_percent - current_weight * 100.0
    reason = (
        "배당 데이터 검증 전 추가매수 보류"
        if target_gap > config.rebalance_band_percent
        else "배당형 목표 비중 범위"
    )
    return _action_advice(
        holding,
        AdviceAction.HOLD,
        as_of,
        metrics,
        current_weight,
        0.0,
        (reason,),
    )


def _add_or_hold(
    holding: Holding,
    as_of: str,
    metrics: _Metrics,
    current_weight: float,
    account_value: float,
    buy_budget: float,
    healthy: bool,
    config: HoldingsAdviceConfig,
    healthy_reasons: tuple[str, ...],
) -> HoldingAdvice:
    target_gap = holding.target_weight_percent - current_weight * 100.0
    if healthy and target_gap > config.rebalance_band_percent and buy_budget > 0:
        target_value = account_value * holding.target_weight_percent / 100.0
        current_value = holding.quantity * metrics.current_price
        amount = min(max(0.0, target_value - current_value), buy_budget)
        quantity = _buy_quantity(amount / metrics.current_price)
        if quantity > 0:
            return _action_advice(
                holding,
                AdviceAction.ADD,
                as_of,
                metrics,
                current_weight,
                quantity,
                healthy_reasons
                + (
                    f"현금 한도 ${buy_budget:,.0f}",
                    f"목표 {holding.target_weight_percent:.0f}%",
                ),
            )
    hold_reasons = ["매도 조건 없음"]
    if healthy and buy_budget <= 0:
        hold_reasons.append("추가 투자 현금 없음")
    elif healthy and target_gap <= config.rebalance_band_percent:
        hold_reasons.append(f"목표 {holding.target_weight_percent:.0f}% 범위")
    elif metrics.rsi >= 70:
        hold_reasons.append(f"RSI {metrics.rsi:.1f} 과열")
    else:
        hold_reasons.append("추가매수 조건 미충족")
    return _action_advice(
        holding,
        AdviceAction.HOLD,
        as_of,
        metrics,
        current_weight,
        0.0,
        tuple(hold_reasons),
    )


def _calculate_metrics(
    holding: Holding,
    candles: Sequence[StockCandle],
    config: HoldingsAdviceConfig,
) -> _Metrics:
    current_price = candles[-1].close
    return _Metrics(
        current_price=current_price,
        return_rate=current_price / holding.average_price_usd - 1.0,
        short_average=_moving_average(candles, config.short_window),
        medium_average=_moving_average(candles, config.medium_window),
        long_average=_moving_average(candles, config.long_window),
        momentum=current_price / candles[-config.momentum_window - 1].close - 1.0,
        long_momentum=(
            current_price / candles[-config.long_momentum_window - 1].close - 1.0
        ),
        volatility=_annualized_volatility(candles, config.volatility_window),
        rsi=_rsi(candles, config.rsi_window),
        atr_rate=_average_true_range(candles, config.atr_window) / current_price,
        below_medium=_confirmed_relative_to_average(
            candles, config.medium_window, config.confirmation_days, above=False
        ),
        below_long=_confirmed_relative_to_average(
            candles, config.long_window, config.confirmation_days, above=False
        ),
        below_long_persistent=_confirmed_relative_to_average(
            candles,
            config.long_window,
            config.long_confirmation_days,
            above=False,
        ),
        above_long=_confirmed_relative_to_average(
            candles, config.long_window, config.confirmation_days, above=True
        ),
    )


def _prepare_symbol_state(
    holding: Holding,
    candles: Sequence[StockCandle],
    previous: AdvisorSymbolState | None,
) -> AdvisorSymbolState:
    as_of = candles[-1].time if candles else ""
    current_price = candles[-1].close if candles else holding.average_price_usd
    if previous is None:
        return AdvisorSymbolState(
            first_seen=as_of,
            observed_quantity=holding.quantity,
            observed_average_price_usd=holding.average_price_usd,
        )

    protected_quantity = previous.protected_quantity
    protected_entry = previous.protected_entry_price_usd
    highest_price = previous.highest_price_usd
    added_quantity = holding.quantity - previous.observed_quantity
    if added_quantity > 1e-9:
        current_cost = holding.quantity * holding.average_price_usd
        previous_cost = (
            previous.observed_quantity * previous.observed_average_price_usd
        )
        added_cost = max(0.0, current_cost - previous_cost)
        added_price = (
            added_cost / added_quantity if added_cost > 0 else holding.average_price_usd
        )
        total_protected_cost = protected_quantity * protected_entry + added_cost
        protected_quantity += added_quantity
        protected_entry = total_protected_cost / protected_quantity
        highest_price = max(highest_price, current_price, added_price)
    elif added_quantity < -1e-9:
        protected_quantity = min(protected_quantity, holding.quantity)
        if protected_quantity <= 0:
            protected_entry = 0.0
            highest_price = 0.0
    elif protected_quantity > 0:
        highest_price = max(highest_price, current_price)

    return replace(
        previous,
        observed_quantity=holding.quantity,
        observed_average_price_usd=holding.average_price_usd,
        protected_quantity=protected_quantity,
        protected_entry_price_usd=protected_entry,
        highest_price_usd=highest_price,
    )


def _signal_streak(
    previous: AdvisorSymbolState | None,
    action: AdviceAction,
    as_of: str,
) -> int:
    if previous is None or previous.last_action != action.value:
        return 1
    if previous.last_signal_date == as_of:
        return max(1, previous.signal_streak)
    return previous.signal_streak + 1


def _review_advice(
    holding: Holding,
    candles: Sequence[StockCandle],
    current_weight: float,
    required_count: int,
) -> HoldingAdvice:
    current_price = candles[-1].close if candles else None
    return HoldingAdvice(
        symbol=holding.symbol,
        name=holding.name,
        investment_style=holding.investment_style,
        action=AdviceAction.REVIEW,
        as_of=candles[-1].time if candles else "",
        current_price_usd=current_price,
        return_rate=(
            (current_price / holding.average_price_usd - 1.0) * 100.0
            if current_price is not None
            else None
        ),
        current_weight_percent=current_weight * 100.0,
        suggested_quantity=0.0,
        suggested_amount_usd=0.0,
        reasons=(f"데이터 {len(candles)}/{required_count}일",),
    )


def _action_advice(
    holding: Holding,
    action: AdviceAction,
    as_of: str,
    metrics: _Metrics,
    current_weight: float,
    quantity: float,
    reasons: tuple[str, ...],
) -> HoldingAdvice:
    return HoldingAdvice(
        symbol=holding.symbol,
        name=holding.name,
        investment_style=holding.investment_style,
        action=action,
        as_of=as_of,
        current_price_usd=metrics.current_price,
        return_rate=metrics.return_rate * 100.0,
        current_weight_percent=current_weight * 100.0,
        suggested_quantity=quantity,
        suggested_amount_usd=quantity * metrics.current_price,
        reasons=reasons,
    )


def _estimated_current_value(
    holding: Holding,
    histories: Mapping[str, Sequence[StockCandle]],
) -> float:
    candles = histories.get(holding.symbol)
    price = candles[-1].close if candles else holding.average_price_usd
    return holding.quantity * price


def _moving_average(candles: Sequence[StockCandle], window: int) -> float:
    return fmean(candle.close for candle in candles[-window:])


def _confirmed_relative_to_average(
    candles: Sequence[StockCandle],
    window: int,
    days: int,
    *,
    above: bool,
) -> bool:
    for offset in range(days):
        end = len(candles) - offset
        close = candles[end - 1].close
        average = fmean(candle.close for candle in candles[end - window : end])
        if (close > average) is not above:
            return False
    return True


def _annualized_volatility(candles: Sequence[StockCandle], window: int) -> float:
    recent = candles[-window - 1 :]
    returns = [
        recent[index].close / recent[index - 1].close - 1.0
        for index in range(1, len(recent))
    ]
    return pstdev(returns) * math.sqrt(252)


def _average_true_range(candles: Sequence[StockCandle], window: int) -> float:
    recent = candles[-window - 1 :]
    true_ranges = []
    for index in range(1, len(recent)):
        candle = recent[index]
        previous_close = recent[index - 1].close
        true_ranges.append(
            max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        )
    return fmean(true_ranges)


def _rsi(candles: Sequence[StockCandle], window: int) -> float:
    recent = candles[-window - 1 :]
    changes = [
        recent[index].close - recent[index - 1].close
        for index in range(1, len(recent))
    ]
    average_gain = fmean(max(change, 0.0) for change in changes)
    average_loss = fmean(max(-change, 0.0) for change in changes)
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100.0 - 100.0 / (1.0 + relative_strength)


def _percentage_quantity(quantity: float, rate: float) -> float:
    return _sell_quantity(quantity, quantity * rate)


def _sell_quantity(holding_quantity: float, raw_quantity: float) -> float:
    if raw_quantity <= 0:
        return 0.0
    if float(holding_quantity).is_integer():
        return float(min(int(holding_quantity), max(1, math.ceil(raw_quantity))))
    return min(holding_quantity, max(0.0001, round(raw_quantity, 4)))


def _buy_quantity(raw_quantity: float) -> float:
    return float(max(0, math.floor(raw_quantity)))
