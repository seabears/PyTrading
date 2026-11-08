"""장기 일봉 알고리즘을 같은 공동 자금으로 비교하는 연구용 재생기.

운용 엔진을 변경하지 않는다. 종가에서 신호를 정하고 다음 거래일 시가에만 체결한다.
당일 고가로 올린 추적 손절선은 다음 날부터 적용한다. 과거 일봉은 수정주가이며
수량은 연구용 가상 단위다. 실제 주문 수량으로 사용하면 안 된다.
"""
import math
from collections import Counter, defaultdict
from statistics import mean, pstdev

from research.backtest import execution_price

FAMILIES = ("ma_trend", "donchian", "trend_pullback", "bollinger_reversion",
            "momentum_rotation", "low_vol_trend")


def make_features(bars, extra_periods=None):
    """각 날짜까지의 자료만 사용한다. 미래 값을 바꾸면 이전 지표는 변하지 않는다.

    RSI2는 최근 2변화의 단순평균 방식(Cutler)이다. ATR14도 TR 단순평균이다.
    Wilder 평활 지표와 혼동하지 않는다. 고점·저점 돌파 기준은 당일을 제외한다.
    """
    extra_periods = extra_periods or {}
    if set(extra_periods) - {"ma", "high", "low"}:
        raise ValueError("추가 지표 종류는 ma/high/low입니다.")
    for periods in extra_periods.values():
        if any(type(period) is not int or not 2 <= period <= 252 for period in periods):
            raise ValueError("추가 지표 기간은 2~252 정수입니다.")
    features, closes, volumes, highs, lows, ranges = [], [], [], [], [], []
    previous_close = None
    for bar in bars:
        close = bar["close"]
        true_range = bar["high"] - bar["low"]
        if previous_close is not None:
            true_range = max(true_range, abs(bar["high"] - previous_close), abs(bar["low"] - previous_close))
        ranges.append(true_range)
        closes.append(close)
        volumes.append(bar["volume"])
        current = {"date": bar["date"], "close": close, "count": len(closes),
                   "atr": mean(ranges[-14:]) if len(ranges) >= 15 else None,
                   "prior_high55": max(highs[-55:]) if len(highs) >= 55 else None,
                   "prior_low20": min(lows[-20:]) if len(lows) >= 20 else None}
        for period in sorted({10, 20, 50, 200, *extra_periods.get("ma", [])}):
            current["ma" + str(period)] = mean(closes[-period:]) if len(closes) >= period else None
        for period in extra_periods.get("high", []):
            current["prior_high" + str(period)] = max(highs[-period:]) if len(highs) >= period else None
        for period in extra_periods.get("low", []):
            current["prior_low" + str(period)] = min(lows[-period:]) if len(lows) >= period else None
        for period in (63, 126):
            current["momentum" + str(period)] = close / closes[-period - 1] - 1 if len(closes) > period else None
        if len(closes) >= 21:
            returns = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - 20, len(closes))]
            current["volatility"] = pstdev(returns)
            deviation = pstdev(closes[-20:])
            current["zscore"] = (close - current["ma20"]) / deviation if deviation else 0
        else:
            current.update(volatility=None, zscore=None)
        if len(closes) >= 3:
            changes = [closes[-1] - closes[-2], closes[-2] - closes[-3]]
            gain = sum(max(change, 0) for change in changes)
            loss = sum(max(-change, 0) for change in changes)
            current["rsi2"] = 100 * gain / (gain + loss) if gain + loss else 50
        else:
            current["rsi2"] = None
        features.append(current)
        highs.append(bar["high"])
        lows.append(bar["low"])
        previous_close = close
    return features


def resolve_strategy(family, overrides=None):
    """이전 12개 실험의 기본값을 유지하면서 한 항목씩 조정할 수 있게 한다."""
    if family not in FAMILIES:
        raise ValueError("알 수 없는 일봉 알고리즘입니다.")
    policy = {"fast_ma": 50, "slow_ma": 200, "breakout_days": 55, "exit_days": 20,
              "rotation_days": {"momentum_rotation": 5, "low_vol_trend": 21}.get(family),
              "holding_days": 10 if family in {"trend_pullback", "bollinger_reversion"} else 126}
    if overrides:
        if set(overrides) - set(policy):
            raise ValueError("알 수 없는 전략 조정 항목입니다.")
        policy.update(overrides)
    for name in ("fast_ma", "slow_ma", "breakout_days", "exit_days", "holding_days"):
        if type(policy[name]) is not int or not 2 <= policy[name] <= 252:
            raise ValueError("전략 기간은 2~252 정수입니다.")
    if policy["fast_ma"] >= policy["slow_ma"]:
        raise ValueError("단기 평균은 장기 평균보다 짧아야 합니다.")
    rotation = policy["rotation_days"]
    if rotation is not None and (family not in {"momentum_rotation", "low_vol_trend"}
            or type(rotation) is not int or not 1 <= rotation <= 63):
        raise ValueError("회전 주기는 회전 전략에서만 1~63 거래일입니다.")
    if family in {"momentum_rotation", "low_vol_trend"} and rotation is None:
        raise ValueError("회전 전략에는 회전 주기가 필요합니다.")
    return policy


def signal(feature, family, strategy_config=None):
    """매수 가능 여부·우선순위·전략 매도를 반환한다. 지표가 부족하면 매수하지 않는다."""
    policy = resolve_strategy(family, strategy_config)
    required_count = max(201, policy["slow_ma"] + 1)
    if family == "donchian":
        required_count = max(required_count, policy["breakout_days"] + 1, policy["exit_days"] + 1)
    if feature["count"] < required_count or not feature["atr"] or not feature["volatility"]:
        return {"enter": False, "exit": False, "score": 0}
    close = feature["close"]
    uptrend = close > feature["ma" + str(policy["slow_ma"])]
    momentum = feature["momentum63"]
    score = momentum / max(feature["volatility"], .001)
    if family == "ma_trend":
        fast = feature["ma" + str(policy["fast_ma"])]
        slow = feature["ma" + str(policy["slow_ma"])]
        enter = close > fast > slow and momentum > 0
        exit_signal = close < fast
    elif family == "donchian":
        enter = close > feature["prior_high" + str(policy["breakout_days"])]
        exit_signal = close < feature["prior_low" + str(policy["exit_days"])]
    elif family == "trend_pullback":
        enter = uptrend and feature["ma50"] > feature["ma200"] and feature["rsi2"] < 10
        exit_signal = feature["rsi2"] > 60 or close > feature["ma10"]
        score = -feature["rsi2"]
    elif family == "bollinger_reversion":
        enter = uptrend and feature["zscore"] < -2
        exit_signal = close >= feature["ma20"]
        score = -feature["zscore"]
    elif family == "momentum_rotation":
        enter = uptrend and feature["momentum126"] > 0
        exit_signal = not enter
        score = feature["momentum126"] / max(feature["volatility"], .001)
    else:
        enter = uptrend and momentum > 0
        exit_signal = not enter
        score = 1 / max(feature["volatility"], .001)
    return {"enter": enter, "exit": exit_signal, "score": score}


def summarize(curve, trades, initial):
    """미청산 포지션의 가상 매도 비용을 포함한 일별 평가액으로 성과를 계산한다."""
    peak, drawdown = initial, 0
    for point in curve:
        peak = max(peak, point["equity"])
        drawdown = max(drawdown, 1 - point["equity"] / peak)
    profits = [trade["pnl"] for trade in trades]
    gains = sum(max(pnl, 0) for pnl in profits)
    losses = -sum(min(pnl, 0) for pnl in profits)
    initial_by_year, final_by_year = {}, {}
    previous = initial
    for point in curve:
        year = point["date"][:4]
        initial_by_year.setdefault(year, previous)
        final_by_year[year] = point["equity"]
        previous = point["equity"]
    return {"net_return": curve[-1]["equity"] / initial - 1,
            "final_equity": curve[-1]["equity"], "max_drawdown": drawdown,
            "trades": len(trades), "realized_pnl": sum(profits),
            "win_rate": sum(pnl > 0 for pnl in profits) / len(profits) if profits else None,
            "profit_factor": gains / losses if losses else None,
            "average_exposure": mean(point["exposure"] for point in curve),
            "minimum_cash": min(point["cash"] for point in curve),
            "maximum_positions": max(point["positions"] for point in curve),
            "year_returns": {year: final / initial_by_year[year] - 1 for year, final in final_by_year.items()}}


def replay(series, features, proxy_features, family, market_filter, costs, settings, start, end, strategy_config=None):
    """30종목의 상장·지표 준비 시점을 개별 처리한다. 신규 상장이 전체 기간을 줄이지 않는다.

    하루 순서: 전날 계획 매도 → 기존 보유 갭 손절 → 전날 계획 매수 → 봉 안 손절
    → 종가 평가 → 다음 날 계획. 당일 손절로 생긴 현금을 이미 지난 시가에 투자하지 않는다.
    데이터가 없는 보유는 이전 평가를 유지하고 별도 횟수를 기록한다. 가짜 시세를 만들지 않는다.
    """
    if family not in FAMILIES:
        raise ValueError("지원하지 않는 알고리즘입니다.")
    strategy_policy = resolve_strategy(family, strategy_config)
    indexed = {symbol: {bar["date"]: bar for bar in bars} for symbol, bars in series.items()}
    feature_index = {symbol: {row["date"]: row for row in rows} for symbol, rows in features.items()}
    days = sorted(day for day in proxy_features if start <= day <= end)
    if not days:
        raise ValueError("평가 기간에 SPY 기준 거래일이 없습니다.")
    initial = costs["starting_cash"]["US"]
    cash = initial
    positions, pending_entries, pending_exits, last_exits, marks = {}, [], {}, {}, {}
    curve, trades, decisions = [], [], []
    diagnostics = Counter()
    spread = settings["spread_ratio"]
    rotation_days = strategy_policy["rotation_days"]
    holding_limit = strategy_policy["holding_days"]

    def sell(symbol, reference, day, reason, index):
        nonlocal cash
        position = positions.pop(symbol)
        price = execution_price(reference, "SELL", costs, spread)
        received = position["quantity"] * price * (1 - costs["sell_cost_ratio"])
        cash += received
        last_exits[symbol] = index
        trades.append({"symbol": symbol, "signal_date": position["signal_date"],
                       "entry_date": position["entry_date"], "exit_date": day,
                       "quantity": position["quantity"], "entry_cost": position["cost"],
                       "entry_price": position["price"], "exit_price": price,
                       "pnl": received - position["cost"], "reason": reason})

    for index, day in enumerate(days):
        for symbol, reason in pending_exits.items():
            if symbol in positions and day in indexed[symbol]:
                sell(symbol, indexed[symbol][day]["open"], day, reason, index)
            elif symbol in positions:
                diagnostics["missing_planned_exit_bar"] += 1
        # 시세 누락으로 실행하지 못한 매도 계획은 실제 자료가 생길 때까지 유지한다.
        pending_exits = {symbol: reason for symbol, reason in pending_exits.items() if symbol in positions}
        for symbol in list(positions):
            bar = indexed[symbol].get(day)
            if bar and bar["open"] <= positions[symbol]["stop"]:
                sell(symbol, bar["open"], day, "gap_stop", index)
        for plan in pending_entries:
            symbol = plan["symbol"]
            bar = indexed[symbol].get(day)
            if not bar or symbol in positions or len(positions) >= costs["max_positions_per_market"]:
                diagnostics["entry_missing_held_or_full"] += 1
                continue
            if abs(bar["open"] / plan["close"] - 1) > settings["maximum_entry_gap"]:
                diagnostics["entry_gap_cancelled"] += 1
                continue
            if index - last_exits.get(symbol, -10000) <= settings["cooldown_days"]:
                diagnostics["cooldown"] += 1
                continue
            price = execution_price(bar["open"], "BUY", costs, spread)
            unit_cost = price * (1 + costs["buy_cost_ratio"])
            stop_distance = plan["atr"] * settings["stop_atr"]
            budget = min(cash, initial * costs["allocation_fraction"])
            quantity = min(math.floor(budget / unit_cost),
                           math.floor(initial * settings["risk_per_trade"] / stop_distance))
            if quantity <= 0:
                diagnostics["budget_below_one_share"] += 1
                continue
            spent = quantity * unit_cost
            cash -= spent
            positions[symbol] = {"quantity": quantity, "price": price, "cost": spent,
                                 "entry_date": day, "entry_index": index, "signal_date": plan["signal_date"],
                                 "peak": bar["open"], "stop": max(0, bar["open"] - stop_distance)}
        pending_entries = []
        for symbol in list(positions):
            bar = indexed[symbol].get(day)
            position = positions[symbol]
            if not bar:
                diagnostics["held_missing_daily_bar"] += 1
                continue
            if bar["low"] <= position["stop"]:
                sell(symbol, min(bar["open"], position["stop"]), day, "atr_stop", index)
                continue
            position["peak"] = max(position["peak"], bar["high"])
            feature = feature_index[symbol][day]
            position["stop"] = max(position["stop"], position["peak"] - settings["trailing_atr"] * feature["atr"])
        for symbol in positions:
            bar = indexed[symbol].get(day)
            if bar:
                marks[symbol] = bar["close"]
        marked = sum(position["quantity"] * execution_price(marks[symbol], "SELL", costs, spread)
                     * (1 - costs["sell_cost_ratio"]) for symbol, position in positions.items())
        if cash < -1e-7 or len(positions) > costs["max_positions_per_market"]:
            raise ArithmeticError("공동 계좌 자금·보유 제한 위반입니다.")
        curve.append({"date": day, "equity": cash + marked, "cash": cash,
                      "positions": len(positions), "exposure": marked / initial})
        proxy = proxy_features[day]
        market_up = proxy["ma200"] is not None and proxy["close"] > proxy["ma200"]
        candidates = []
        for symbol in series:
            feature = feature_index[symbol].get(day)
            if feature is None:
                continue
            detail = signal(feature, family, strategy_policy)
            if symbol in positions:
                age = index - positions[symbol]["entry_index"] + 1
                if detail["exit"] or age >= holding_limit:
                    pending_exits[symbol] = "signal_exit" if detail["exit"] else "holding_limit"
            if detail["enter"] and (not market_filter or market_up):
                candidates.append({"symbol": symbol, "score": detail["score"], "atr": feature["atr"],
                                   "close": feature["close"], "signal_date": day})
        candidates.sort(key=lambda plan: (-plan["score"], plan["symbol"]))
        rebalance = rotation_days is None or index % rotation_days == 0
        if rebalance:
            if rotation_days:
                targets = {plan["symbol"] for plan in candidates[:costs["max_positions_per_market"]]}
                for symbol in positions:
                    if symbol not in targets:
                        pending_exits.setdefault(symbol, "rank_or_market_exit")
            pending_entries = [plan for plan in candidates if plan["symbol"] not in positions]
            if index < len(days) - 1:
                decisions.append({"signal_date": day, "execution_date": days[index + 1],
                                  "entries": [plan["symbol"] for plan in pending_entries],
                                  "exits": dict(pending_exits)})
    summary = summarize(curve, trades, initial)
    summary["open_positions"] = len(positions)
    return {"summary": summary, "curve": curve, "trades": trades, "decisions": decisions,
            "positions": positions, "diagnostics": dict(diagnostics)}


def benchmark(proxy_bars, costs, settings, start, end):
    """SPY를 최대 투자 한도(기본 50%)만큼 단순 보유한다. 나머지는 무이자 현금이다."""
    bars = [bar for bar in proxy_bars if start <= bar["date"] <= end]
    initial = costs["starting_cash"]["US"]
    fraction = min(1, costs["allocation_fraction"] * costs["max_positions_per_market"])
    price = execution_price(bars[0]["open"], "BUY", costs, settings["spread_ratio"])
    quantity = math.floor(initial * fraction / (price * (1 + costs["buy_cost_ratio"])))
    cash = initial - quantity * price * (1 + costs["buy_cost_ratio"])
    curve = []
    for bar in bars:
        marked = quantity * execution_price(bar["close"], "SELL", costs, settings["spread_ratio"]) * (1 - costs["sell_cost_ratio"])
        curve.append({"date": bar["date"], "equity": cash + marked, "cash": cash,
                      "positions": int(quantity > 0), "exposure": marked / initial})
    return {"summary": summarize(curve, [], initial), "curve": curve}
