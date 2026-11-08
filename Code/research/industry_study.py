"""동종 기업을 고정 규칙으로 비교하는 보조 계산. 새로운 매매 규칙은 만들지 않는다."""
import math
from research.algorithm_study import summarize
from research.backtest import execution_price


def group_benchmark(series, days, costs, settings, start, end):
    """같은 초기 투자 한도를 기업마다 균등 배분한다. 시세가 없으면 현금을 남긴다."""
    initial = costs["starting_cash"]["US"]
    fraction = min(1, costs["allocation_fraction"] * costs["max_positions_per_market"])
    per_symbol = initial * fraction / len(series)
    indexed = {symbol: {bar["date"]: bar for bar in bars} for symbol, bars in series.items()}
    cash, positions, attempted, marks = initial, {}, set(), {}
    curve = []
    for day in sorted(day for day in days if start <= day <= end):
        for symbol in series:
            bar = indexed[symbol].get(day)
            if bar is None:
                continue
            if symbol not in attempted:
                price = execution_price(bar["open"], "BUY", costs, settings["spread_ratio"])
                quantity = math.floor(per_symbol / (price * (1 + costs["buy_cost_ratio"])))
                cash -= quantity * price * (1 + costs["buy_cost_ratio"])
                positions[symbol] = quantity
                attempted.add(symbol)
            marks[symbol] = bar["close"]
        marked = sum(quantity * execution_price(marks[symbol], "SELL", costs, settings["spread_ratio"])
                     * (1 - costs["sell_cost_ratio"]) for symbol, quantity in positions.items())
        curve.append({"date": day, "equity": cash + marked, "cash": cash,
                      "positions": sum(quantity > 0 for quantity in positions.values()), "exposure": marked / initial})
    if not curve:
        raise ValueError("비교 기간의 거래일이 없습니다.")
    return {"summary": summarize(curve, [], initial), "curve": curve}


def peer_statistics(rows, new_symbols, minimum_trades):
    """새로 수집한 종목과 기존 종목을 나눠 집계한다. 적은 거래도 숨기지 않는다."""
    output = {}
    for scope in ("all", "new", "existing"):
        selected = [row for row in rows if scope == "all" or
                    (row["symbol"] in new_symbols if scope == "new" else row["symbol"] not in new_symbols)]
        enough = [row for row in selected if row["base"]["trades"] >= minimum_trades]
        output[scope] = {"stocks": len(selected), "enough_sample_stocks": len(enough),
                         "positive_base": sum(row["base"]["net_return"] > 0 for row in selected),
                         "positive_double_cost": sum(row["double_cost"]["net_return"] > 0 for row in selected),
                         "positive_both_with_enough_sample": sum(row["base"]["net_return"] > 0
                             and row["double_cost"]["net_return"] > 0 for row in enough),
                         "no_closed_trades": sum(row["base"]["trades"] == 0 for row in selected)}
    return output
