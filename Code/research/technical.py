"""장중·일봉 전략의 비용 포함 재생. 두 전략의 계좌와 보유 기간을 섞지 않는다.

종가 신호는 다음 봉 시가에서 체결한다. 고점·ATR 갱신은 당일 손절 검사 뒤에 한다.
갭 손실, 정수 수량, 위험 예산, 최대 투자금액, 일일 신규 진입 중단 조건을 적용한다.
"""
import math
from collections import Counter
from statistics import mean, stdev
from research.backtest import execution_price, summarize
from strategy.technical import signal_details


def performance(curve, trades, starting_cash):
    """Sharpe는 장중 봉 개수가 아닌 일별 계좌 수익률, 무위험 수익률 0%로 계산한다."""
    summary = summarize(curve, trades, starting_cash)
    daily = {}
    for row in curve:
        daily[row["date"]] = row["equity"]
    daily_returns = []
    previous = starting_cash
    for equity in daily.values():
        daily_returns.append(equity / previous - 1)
        previous = equity
    volatility = stdev(daily_returns) if len(daily_returns) >= 2 else 0
    gains = [trade["pnl"] for trade in trades if trade["pnl"] > 0]
    losses = [-trade["pnl"] for trade in trades if trade["pnl"] < 0]
    summary.update(sharpe=mean(daily_returns) / volatility * math.sqrt(252) if volatility else None,
                   sharpe_days=len(daily_returns), average_win=mean(gains) if gains else None,
                   average_loss=mean(losses) if losses else None,
                   payoff_ratio=mean(gains) / mean(losses) if gains and losses else None,
                   expectancy=mean([trade["pnl"] for trade in trades]) if trades else None)
    return summary


def position_size(cash, initial_cash, reference, atr, risk, costs, spread):
    """ATR 손절 폭 기준 위험 예산과 총 투자금액 상한 중 더 작은 수량을 쓴다.

    갭 하락·체결 비용은 손실을 예산보다 크게 만들 수 있어 손실 보장으로 해석하지 않는다.
    """
    distance = atr * risk["stop_atr"]
    if distance <= 0:
        return 0
    price = execution_price(reference, "BUY", costs, spread)
    unit_cost = price * (1 + costs["buy_cost_ratio"])
    by_risk = math.floor(cash * risk["risk_per_trade"] / distance)
    by_capital = math.floor(min(cash, initial_cash * costs["allocation_fraction"]) / unit_cost)
    return max(0, min(by_risk, by_capital))


def replay(bars, market, family, settings, risk, costs, spread, regime_provider, require_up_market=False, warmup=None):
    """각 종목의 독립 연구 계좌. 공동 자금 포트폴리오 수익으로 합산하지 않는다."""
    initial = costs["starting_cash"][market]
    cash, position = initial, None
    history = list(warmup or [])
    trades, curve, signals = [], [], []
    diagnostics = Counter()
    pending_entry, pending_exit = None, False
    cooldown_until = 0
    previous_day = None
    day_initial_equity = initial
    halted = False

    def sell(reference, bar, reason, index, at_open=False):
        nonlocal cash, position, cooldown_until
        price = execution_price(reference, "SELL", costs, spread)
        proceeds = position["quantity"] * price * (1 - costs["sell_cost_ratio"])
        cash += proceeds
        trades.append({"signal_time": position["signal_time"], "entry_time": position["entry_time"],
            "exit_time": bar.get("start", bar["time"]) if at_open else bar["time"],
            "entry_date": position["entry_time"][:10], "exit_date": bar["date"],
            "signal_bar_index": position["signal_bar_index"], "entry_bar_index": position["entry_index"],
            "quantity": position["quantity"], "entry_price": position["entry_price"], "exit_price": price,
            "entry_cost": position["cost"], "pnl": proceeds - position["cost"], "reason": reason})
        position = None
        cooldown_until = index + risk["cooldown_bars"] + 1

    for index, bar in enumerate(bars):
        new_day = bar["date"] != previous_day
        if new_day:
            previous_day = bar["date"]
            day_initial_equity = curve[-1]["equity"] if curve else initial
            halted = False
            if family == "vwap_volume":
                history = []
        if pending_exit and position:
            sell(bar["open"], bar, "signal_exit_next_open", index, at_open=True)
        pending_exit = False
        if pending_entry and position is None and not halted and index >= cooldown_until:
            gap = abs(bar["open"] / pending_entry["close"] - 1)
            if gap <= risk["maximum_entry_gap"]:
                quantity = position_size(cash, initial, bar["open"], pending_entry["atr"], risk, costs, spread)
                if quantity:
                    price = execution_price(bar["open"], "BUY", costs, spread)
                    cost = quantity * price * (1 + costs["buy_cost_ratio"])
                    cash -= cost
                    position = {"quantity": quantity, "cost": cost, "entry_price": price,
                        "entry_time": bar.get("start", bar["time"]), "signal_time": pending_entry["time"],
                        "signal_bar_index": pending_entry["index"], "entry_index": index,
                        "peak": bar["open"], "atr": pending_entry["atr"],
                        "trailing_stop": bar["open"] - risk["trailing_atr"] * pending_entry["atr"],
                        "fixed_stop": price - risk["stop_atr"] * pending_entry["atr"]}
                else:
                    diagnostics["budget_too_small"] += 1
            else:
                diagnostics["entry_gap_cancelled"] += 1
        pending_entry = None
        if position:
            # 손절 검사에는 이전 완성 봉까지의 고점·ATR만 사용한다.
            stop = max(position["fixed_stop"], position["trailing_stop"])
            if bar["low"] <= stop:
                sell(min(bar["open"], stop), bar, "gap_adjusted_atr_stop", index)
        history.append(bar)
        if family == "ma_momentum":
            maximum_history = max(settings["slow"], settings["momentum_period"] + 1, settings["atr_period"] + 1)
            history = history[-maximum_history:]
        regime = regime_provider.at(bar["date"])
        diagnostics["regime_" + regime] += 1
        detail = signal_details(history, family, settings, regime, require_up_market)
        if position:
            position["peak"] = max(position["peak"], bar["high"])
            if detail["values"]["atr"]:
                position["atr"] = detail["values"]["atr"]
            # ATR이 커져도 이미 올린 추적 손절선을 다시 낮추지 않는다.
            position["trailing_stop"] = max(position["trailing_stop"], position["peak"] - risk["trailing_atr"] * position["atr"])
            pending_exit = detail["exit"] or index - position["entry_index"] + 1 >= settings["maximum_holding_bars"]
        marked = 0
        if position:
            marked = position["quantity"] * execution_price(bar["close"], "SELL", costs, spread) * (1 - costs["sell_cost_ratio"])
        equity = cash + marked
        if equity <= day_initial_equity * (1 - risk["daily_loss_limit"]):
            halted = True
            diagnostics["daily_loss_halt"] += 1
        session_end = family == "vwap_volume" and (index == len(bars) - 1 or bars[index + 1]["date"] != bar["date"])
        period_end = index == len(bars) - 1
        if position and (session_end or period_end):
            sell(bar["close"], bar, "session_end" if session_end else "period_end", index)
            pending_exit = False
            equity = cash
        if not position and not halted and index >= cooldown_until and not session_end and not period_end:
            if detail["enter"]:
                pending_entry = {"close": bar["close"], "atr": detail["values"]["atr"], "time": bar["time"], "index": index}
                signals.append({"time": bar["time"], "values": detail["values"]})
            else:
                diagnostics.update("blocked_" + name for name, passed in detail["conditions"].items() if not passed)
        curve.append({"time": bar["time"], "date": bar["date"], "equity": equity})
    return {"summary": performance(curve, trades, initial), "curve": curve, "trades": trades,
            "signals": signals, "diagnostics": dict(diagnostics)}


def buy_and_hold(bars, market, costs, spread):
    initial = costs["starting_cash"][market]
    price = execution_price(bars[0]["open"], "BUY", costs, spread)
    quantity = math.floor(initial * costs["allocation_fraction"] / (price * (1 + costs["buy_cost_ratio"])))
    invested = quantity * price * (1 + costs["buy_cost_ratio"])
    cash = initial - invested
    curve = [{"time": bar["time"], "date": bar["date"], "equity": cash + quantity * execution_price(bar["close"], "SELL", costs, spread) * (1 - costs["sell_cost_ratio"])} for bar in bars]
    pnl = curve[-1]["equity"] - initial
    trades = [{"pnl": pnl}] if quantity else []
    return {"summary": performance(curve, trades, initial), "curve": curve}
