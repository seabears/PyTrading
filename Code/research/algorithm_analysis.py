"""알고리즘의 기록된 거래를 가격 손익·거래 비용·종목 기여로 분해한다.

전략을 다시 고르거나 거래를 바꾸지 않는다. 미청산 평가 손익과 완료 거래를 구분한다.
"""
from collections import defaultdict

from research.backtest import execution_price


def analyze(result, series, costs, spread):
    symbols = {symbol: {"closed_trades": 0, "realized_pnl": 0, "open_pnl": 0, "net_pnl": 0}
               for symbol in series}
    gross, spreads, slippage, fees = 0, 0, 0, 0
    reasons = defaultdict(lambda: {"trades": 0, "pnl": 0})
    holding_days = []
    from datetime import date
    for trade in result["trades"]:
        quantity = trade["quantity"]
        buy_reference = trade["entry_price"] / ((1 + spread / 2) * (1 + costs["slippage_ratio"]))
        sell_reference = trade["exit_price"] / ((1 - spread / 2) * (1 - costs["slippage_ratio"]))
        gross += quantity * (sell_reference - buy_reference)
        spreads += quantity * (buy_reference + sell_reference) * spread / 2
        slippage += quantity * (trade["entry_price"] - buy_reference * (1 + spread / 2)
                               + sell_reference * (1 - spread / 2) - trade["exit_price"])
        fees += trade["entry_cost"] - quantity * trade["entry_price"]
        fees += quantity * trade["exit_price"] * costs["sell_cost_ratio"]
        row = symbols[trade["symbol"]]
        row["closed_trades"] += 1
        row["realized_pnl"] += trade["pnl"]
        reasons[trade["reason"]]["trades"] += 1
        reasons[trade["reason"]]["pnl"] += trade["pnl"]
        holding_days.append((date.fromisoformat(trade["exit_date"]) - date.fromisoformat(trade["entry_date"])).days)
    end = result["curve"][-1]["date"]
    for symbol, position in result["positions"].items():
        last = next(bar for bar in reversed(series[symbol]) if bar["date"] <= end)
        marked = (position["quantity"] * execution_price(last["close"], "SELL", costs, spread)
                  * (1 - costs["sell_cost_ratio"]))
        symbols[symbol]["open_pnl"] = marked - position["cost"]
    for row in symbols.values():
        row["net_pnl"] = row["realized_pnl"] + row["open_pnl"]
    realized = sum(trade["pnl"] for trade in result["trades"])
    net = result["summary"]["final_equity"] - costs["starting_cash"]["US"]
    checks = {"closed_costs_reconcile": abs(gross - spreads - slippage - fees - realized) < 1e-6,
              "stock_contributions_reconcile": abs(sum(row["net_pnl"] for row in symbols.values()) - net) < 1e-6,
              "cash_nonnegative": result["summary"]["minimum_cash"] >= -1e-7,
              "position_limit": result["summary"]["maximum_positions"] <= costs["max_positions_per_market"]}
    if not all(checks.values()):
        raise ArithmeticError("거래·비용·종목 기여 검산 실패: " + str(checks))
    return {"closed_gross_price_pnl": gross, "closed_spread_cost": spreads,
            "closed_slippage_cost": slippage, "closed_fees": fees, "closed_net_pnl": realized,
            "net_pnl_including_open": net, "by_symbol": symbols, "exit_reasons": dict(reasons),
            "average_holding_calendar_days": sum(holding_days) / len(holding_days) if holding_days else None,
            "checks": checks}
