"""같은 일봉 돌파 기회·배분에 보호 매도만 바꾸는 연구 전용 공동 계좌.

진행 순서: 전일 손절선의 시가 갭 청산 → 전일 계획 매수 → 봉 안 손절 →
미리 정한 보유 만료 종가 청산 → 다음 날 손절선 갱신 → 종가 평가·다음 매수 계획.
당일 고가로 높인 손절선은 반드시 다음 거래일부터 사용한다.
"""
import math
from collections import Counter
from statistics import mean

from research.backtest import execution_price


VARIANTS = [
    {"name": "hold20", "stop": None, "trail": None},
    {"name": "fixed3", "stop": "percent", "stop_ratio": .03, "trail": None},
    {"name": "fixed5", "stop": "percent", "stop_ratio": .05, "trail": None},
    {"name": "atr25", "stop": "atr", "stop_atr": 2.5, "trail": None},
    {"name": "atr25_trail3", "stop": "atr", "stop_atr": 2.5, "trail": "atr", "trail_atr": 3},
    {"name": "fixed3_trail4", "stop": "percent", "stop_ratio": .03, "trail": "percent", "trail_ratio": .04},
]


def initial_stop(reference, atr, variant):
    if variant["stop"] is None:
        return None
    distance = reference * variant["stop_ratio"] if variant["stop"] == "percent" else atr * variant["stop_atr"]
    return max(0, reference - distance)


def next_stop(previous_stop, peak, atr, variant):
    if variant["trail"] is None:
        return previous_stop
    candidate = peak * (1 - variant["trail_ratio"]) if variant["trail"] == "percent" else peak - atr * variant["trail_atr"]
    return max(previous_stop, candidate)


def execution(reference, action, quantity, costs, spread):
    """체결 가격과 수수료를 분리한다. 스프레드와 슬리피지의 중복 차감을 막는다."""
    quote = reference * (1 + spread / 2 if action == "BUY" else 1 - spread / 2)
    price = execution_price(reference, action, costs, spread)
    fee = price * quantity * costs["buy_cost_ratio" if action == "BUY" else "sell_cost_ratio"]
    return {"reference": reference, "quote": quote, "price": price, "quantity": quantity, "fee": fee}


def trade_result(position, closing, day, reason):
    opening = position["fill"]
    quantity = opening["quantity"]
    gross = quantity * (closing["reference"] - opening["reference"])
    spread = quantity * (opening["quote"] - opening["reference"] + closing["reference"] - closing["quote"])
    slippage = quantity * (opening["price"] - opening["quote"] + closing["quote"] - closing["price"])
    fees = opening["fee"] + closing["fee"]
    received = quantity * closing["price"] - closing["fee"]
    pnl = received - position["cost"]
    if not math.isclose(pnl, gross - spread - slippage - fees, abs_tol=1e-7):
        raise ArithmeticError("거래 가격 손익·비용 분해 불일치")
    return {"symbol": position["symbol"], "signal_date": position["signal_date"],
            "entry_date": position["entry_date"], "exit_date": day, "quantity": quantity,
            "entry": opening, "exit": closing, "entry_cost": position["cost"],
            "gross_pnl": gross, "spread_cost": spread, "slippage_cost": slippage,
            "fees": fees, "pnl": pnl, "net_return": pnl / position["cost"], "reason": reason}


def summarize(curve, trades, initial, open_pnl):
    peak, drawdown = initial, 0
    monthly_start, monthly_final, annual_start, annual_final = {}, {}, {}, {}
    previous = initial
    for point in curve:
        peak = max(peak, point["equity"])
        drawdown = max(drawdown, 1 - point["equity"] / peak)
        month, year = point["date"][:7], point["date"][:4]
        monthly_start.setdefault(month, previous)
        annual_start.setdefault(year, previous)
        monthly_final[month], annual_final[year] = point["equity"], point["equity"]
        previous = point["equity"]
    monthly = {month: equity / monthly_start[month] - 1 for month, equity in monthly_final.items()}
    profits = [trade["pnl"] for trade in trades]
    gains, losses = sum(max(value, 0) for value in profits), -sum(min(value, 0) for value in profits)
    realized = sum(profits)
    if not math.isclose(initial + realized + open_pnl, curve[-1]["equity"], abs_tol=1e-6):
        raise ArithmeticError("완료·미청산 손익과 계좌 평가 불일치")
    return {"net_return": curve[-1]["equity"] / initial - 1, "final_equity": curve[-1]["equity"],
        "max_drawdown": drawdown, "trades": len(trades), "realized_pnl": realized, "open_net_pnl": open_pnl,
        "win_rate": mean(value > 0 for value in profits) if profits else None,
        "profit_factor": gains / losses if losses else None,
        "worst_trade": min((trade["net_return"] for trade in trades), default=None),
        "worst_month": min(monthly.values()), "worst_month_date": min(monthly, key=monthly.get),
        "negative_months": sum(value < 0 for value in monthly.values()), "months": len(monthly),
        "average_exposure": mean(point["exposure"] for point in curve),
        "maximum_positions": max(point["positions"] for point in curve), "minimum_cash": min(point["cash"] for point in curve),
        "closed_gross_pnl": sum(trade["gross_pnl"] for trade in trades),
        "closed_spread_cost": sum(trade["spread_cost"] for trade in trades),
        "closed_slippage_cost": sum(trade["slippage_cost"] for trade in trades),
        "closed_fees": sum(trade["fees"] for trade in trades),
        "exit_reasons": dict(Counter(trade["reason"] for trade in trades)),
        "year_returns": {year: equity / annual_start[year] - 1 for year, equity in annual_final.items()},
        "month_returns": monthly}


def replay(series, features, days, opportunities, variant, costs, policy, start, end):
    """공동 현금·정수 수량·최대 보유 제한. 손절 차이에 따른 자금 경쟁도 보존한다."""
    indexed = {symbol: {bar["date"]: bar for bar in bars} for symbol, bars in series.items()}
    feature_index = {symbol: {row["date"]: row for row in rows} for symbol, rows in features.items()}
    selected_days = [(index, day) for index, day in enumerate(days) if start <= day <= end]
    initial = costs["starting_cash"]["US"]
    cash, positions, marks, pending = initial, {}, {}, []
    trades, curve, entries = [], [], []
    diagnostics = Counter()

    def sell(symbol, reference, day, reason):
        nonlocal cash
        position = positions.pop(symbol)
        fill = execution(reference, "SELL", position["fill"]["quantity"], costs, policy["spread_ratio"])
        cash += fill["price"] * fill["quantity"] - fill["fee"]
        trades.append(trade_result(position, fill, day, reason))

    for index, day in selected_days:
        for symbol in list(positions):
            bar, stop = indexed[symbol].get(day), positions[symbol]["stop"]
            if bar and stop is not None and bar["open"] <= stop:
                sell(symbol, bar["open"], day, "gap_stop")
        for plan in pending:
            symbol = plan["symbol"]
            bar = indexed[symbol].get(day)
            if bar is None:
                diagnostics["missing_entry_bar"] += 1
                continue
            if symbol in positions or len(positions) >= costs["max_positions_per_market"]:
                diagnostics["held_or_full"] += 1
                continue
            if bar["open"] < plan["level"] or bar["open"] > plan["close"] * (1 + policy["maximum_entry_gap"]):
                diagnostics["gap_or_breakout_cancel"] += 1
                continue
            # 모든 매도 조건에 같은 수량 공식을 쓴다. 손절 폭에 맞춰 수량을 바꾸지 않는다.
            unit_fill = execution(bar["open"], "BUY", 1, costs, policy["spread_ratio"])
            unit_cost = unit_fill["price"] + unit_fill["fee"]
            budget = min(cash, initial * costs["allocation_fraction"])
            quantity = min(math.floor(budget / unit_cost), math.floor(initial * policy["risk_budget"] / (plan["atr"] * 2.5)))
            if quantity <= 0:
                diagnostics["insufficient_budget"] += 1
                continue
            fill = execution(bar["open"], "BUY", quantity, costs, policy["spread_ratio"])
            spent = fill["price"] * quantity + fill["fee"]
            cash -= spent
            positions[symbol] = {"symbol": symbol, "signal_date": plan["date"], "entry_date": day,
                "entry_index": index, "fill": fill, "cost": spent, "peak": bar["open"],
                "stop": initial_stop(bar["open"], plan["atr"], variant)}
            entries.append({"symbol": symbol, "signal_date": plan["date"], "entry_date": day,
                            "reference": bar["open"], "quantity": quantity})
        pending = []
        for symbol in list(positions):
            bar, position = indexed[symbol].get(day), positions[symbol]
            if bar is None:
                diagnostics["held_missing_bar"] += 1
                continue
            if position["stop"] is not None and bar["low"] <= position["stop"]:
                sell(symbol, min(bar["open"], position["stop"]), day, "intraday_stop")
                continue
            if index - position["entry_index"] + 1 >= policy["holding_sessions"]:
                # 보유 기한은 진입 때 확정된다. 당일 종가를 본 뒤 청산을 결정하지 않는다.
                sell(symbol, bar["close"], day, "holding20_close")
                continue
            position["peak"] = max(position["peak"], bar["high"])
            position["stop"] = next_stop(position["stop"], position["peak"], feature_index[symbol][day]["atr"], variant)
        marked, open_pnl = 0, 0
        for symbol, position in positions.items():
            if day in indexed[symbol]:
                marks[symbol] = indexed[symbol][day]["close"]
            fill = execution(marks[symbol], "SELL", position["fill"]["quantity"], costs, policy["spread_ratio"])
            value = fill["price"] * fill["quantity"] - fill["fee"]
            marked += value
            open_pnl += value - position["cost"]
        if cash < -1e-7 or len(positions) > costs["max_positions_per_market"]:
            raise ArithmeticError("공동 자금·보유 한도 위반")
        curve.append({"date": day, "equity": cash + marked, "cash": cash,
                      "positions": len(positions), "exposure": marked / initial})
        plans = [plan for plan in opportunities.get(day, []) if plan["symbol"] not in positions]
        pending = sorted(plans, key=lambda plan: (-plan["score"], plan["symbol"]))
    if not curve:
        raise ValueError("평가 기간 거래일이 없습니다.")
    summary = summarize(curve, trades, initial, open_pnl)
    summary["open_positions"] = len(positions)
    return {"summary": summary, "curve": curve, "trades": trades, "entries": entries,
            "positions": positions, "diagnostics": dict(diagnostics)}
