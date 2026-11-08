"""여러 종목이 한 자금을 공유하는 일봉 모의매매. 실시간 주문 코드와 독립이다.

수정 위치: candidate_rules()의 가설, rank_symbols()의 종가 신호.
당일 신호는 다음 거래일 시가에만 체결한다. 수익률을 보고 종목을 제외하지 않는다.
분할 보정 가격은 연구용 가상 단위이며 실제 주문 수량으로 사용하면 안 된다.
"""
import math
import statistics

from research.backtest import execution_price, summarize
from strategy.exits import PROFIT_EXIT_DEFAULTS, profit_exit_floor


def candidate_rules():
    """24개 후보를 사전 선언한다. 시험 결과를 본 뒤 후보를 늘리지 않는다."""
    return [{"family": family, "momentum_days": momentum_days, "trend_days": trend_days,
             "rebalance_days": rebalance_days, "maximum_positions": 3,
             "stop_loss": .08, "trailing_stop": .12, "minimum_holding_days": 5}
            for family in ("momentum", "risk_adjusted_momentum")
            for momentum_days in (20, 60, 120) for trend_days in (50, 100)
            for rebalance_days in (5, 20)]


def reversal_rules():
    """두 번째 수정: 추세 속 눌림과 큰 하락 뒤 반등을 구분한 24개 가설이다."""
    return [{"family": family, "momentum_days": momentum_days, "trend_days": trend_days,
             "rebalance_days": rebalance_days, "maximum_positions": 3,
             "stop_loss": .05, "trailing_stop": .08, "minimum_holding_days": 5}
            for family in ("pullback_rotation", "oversold_rotation")
            for momentum_days in (5, 10, 20) for trend_days in (50, 100)
            for rebalance_days in (1, 5)]


def rank_symbols(histories, rule):
    """전달받은 완료 봉만 사용한다. 양수 모멘텀·종가가 추세 평균 위인 종목을 고른다."""
    if rule.get("market_proxy"):
        proxy = histories[rule["market_proxy"]]
        if len(proxy) < 50:
            return []
        # 다섯 번째 가설: 시장 50일 추세 아래에서는 주식 신규 진입을 멈추고
        # 실제 인버스 ETF 하나만 평가한다. 추정한 지수 역수로 수익을 만들어내지 않는다.
        market_up = proxy[-1]["close"] > statistics.mean(bar["close"] for bar in proxy[-50:])
        excluded = {rule["market_proxy"], rule["defensive_symbol"]}
        histories = {symbol: history for symbol, history in histories.items()
                     if (symbol not in excluded if market_up else symbol == rule["defensive_symbol"])}
    ranking = []
    minimum = max(rule["momentum_days"] + 1, rule["trend_days"], 21)
    for symbol, history in histories.items():
        if len(history) < minimum:
            continue
        latest_close = history[-1]["close"]
        momentum = latest_close / history[-rule["momentum_days"] - 1]["close"] - 1
        trend_mean = statistics.mean(bar["close"] for bar in history[-rule["trend_days"]:])
        if rule["family"] == "pullback_rotation":
            if momentum >= -.03 or latest_close <= trend_mean:
                continue
        elif rule["family"] == "oversold_rotation":
            if momentum >= -.03 or latest_close >= trend_mean * .95:
                continue
        elif momentum <= 0 or latest_close <= trend_mean:
            continue
        daily_returns = [history[index]["close"] / history[index - 1]["close"] - 1
                         for index in range(len(history) - 20, len(history))]
        volatility = statistics.pstdev(daily_returns)
        if rule["family"] in {"pullback_rotation", "oversold_rotation"}:
            score = -momentum / max(volatility, .001)
        else:
            score = momentum if rule["family"] == "momentum" else momentum / max(volatility, .001)
        ranking.append((score, symbol))
    ranking.sort(key=lambda item: (-item[0], item[1]))
    return [symbol for score, symbol in ranking[:rule["maximum_positions"]]]


def common_dates(series, start, end):
    """휴장일 차이가 있는 원화·달러 시장은 호출 시 별도로 전달해야 한다."""
    date_sets = [{bar["date"] for bar in bars if start <= bar["date"] <= end} for bars in series.values()]
    return sorted(set.intersection(*date_sets)) if date_sets else []


def simulate_portfolio(series, market, rule, costs, spread_ratio, start, end, buy_and_hold=False):
    """종가 계획→다음 시가 교체→갭 손절→종가 평가. 각 구간은 현금으로 시작한다.

    각 종목 투자 예산은 초기 자금 10%, 최대 3종목이다. 빈 슬롯은 현금으로 남는다.
    보유가 계속되는 종목은 불필요하게 매도·재매수하지 않는다. 현금이 부족하면 수량을 줄인다.
    비교군은 같은 종목군을 총 30% 예산으로 동일 비중 단순 보유한다.
    """
    dates = common_dates(series, start, end)
    if not dates:
        raise ValueError("공통 시험 거래일이 없습니다.")
    indexed = {symbol: {bar["date"]: bar for bar in bars} for symbol, bars in series.items()}
    histories = {symbol: [bar for bar in bars if bar["date"] < start] for symbol, bars in series.items()}
    starting_cash = costs["starting_cash"][market]
    cash = starting_cash
    positions, trades, curve, decisions = {}, [], [], []
    pending_targets = list(series) if buy_and_hold else None
    maximum_positions = len(series) if buy_and_hold else rule["maximum_positions"]
    budget = starting_cash * costs["allocation_fraction"]
    if buy_and_hold:
        budget = budget * rule["maximum_positions"] / len(series)

    def sell(symbol, reference, day, reason):
        nonlocal cash
        position = positions.pop(symbol)
        price = execution_price(reference, "SELL", costs, spread_ratio)
        proceeds = position["quantity"] * price * (1 - costs["sell_cost_ratio"])
        cash += proceeds
        trades.append({"symbol": symbol, "entry_date": position["entry_date"], "exit_date": day,
                       "entry_price": position["price"], "exit_price": price,
                       "quantity": position["quantity"], "pnl": proceeds - position["cost"], "reason": reason})

    for index, day in enumerate(dates):
        if pending_targets is not None:
            for symbol in list(positions):
                # 여섯 번째 수정: 순위가 하루 바뀌었다고 즉시 회전하지 않는다.
                # 최소 보유는 순위 교체만 제한하며 갭 손절·위험 청산을 막지 않는다.
                if symbol not in pending_targets and index - positions[symbol]["entry_index"] >= rule.get("minimum_holding_days", 0):
                    sell(symbol, indexed[symbol][day]["open"], day, "rank_exit")
            for symbol in pending_targets:
                if symbol in positions or len(positions) >= maximum_positions:
                    continue
                bar = indexed[symbol][day]
                price = execution_price(bar["open"], "BUY", costs, spread_ratio)
                quantity = math.floor(min(budget, cash) / (price * (1 + costs["buy_cost_ratio"])))
                if quantity <= 0:
                    continue
                spent = quantity * price * (1 + costs["buy_cost_ratio"])
                cash -= spent
                positions[symbol] = {"quantity": quantity, "price": price, "cost": spent,
                                     "peak": bar["open"], "entry_date": day, "entry_index": index}
            pending_targets = None
        if not buy_and_hold:
            for symbol in list(positions):
                position = positions[symbol]
                bar = indexed[symbol][day]
                stop = max(position["price"] * (1 - rule["stop_loss"]), position["peak"] * (1 - rule["trailing_stop"]))
                reason = "gap_adjusted_stop"
                if rule.get("profit_exits"):
                    # 오늘 고가를 보기 전의 고점만 사용: 당일 고가→저가 순서를 상상하지 않는다.
                    proceeds_ratio = (1 - spread_ratio / 2) * (1 - costs["slippage_ratio"]) * (1 - costs["sell_cost_ratio"])
                    protected = profit_exit_floor(position["cost"] / position["quantity"], position["peak"],
                                                  proceeds_ratio, {**PROFIT_EXIT_DEFAULTS, **rule["profit_exits"]})
                    if protected and protected[0] > stop:
                        stop, reason = protected
                if bar["low"] <= stop:
                    sell(symbol, min(stop, bar["open"]), day, reason)
                else:
                    position["peak"] = max(position["peak"], bar["high"])
        if index == len(dates) - 1:
            for symbol in list(positions):
                sell(symbol, indexed[symbol][day]["close"], day, "period_end")
        for symbol in histories:
            histories[symbol].append(indexed[symbol][day])
        if not buy_and_hold and index < len(dates) - 1 and index % rule["rebalance_days"] == 0:
            pending_targets = rank_symbols(histories, rule)
            decisions.append({"signal_date": day, "execution_date": dates[index + 1], "targets": pending_targets[:]})
        marked = sum(position["quantity"] * execution_price(indexed[symbol][day]["close"], "SELL", costs, spread_ratio)
                     * (1 - costs["sell_cost_ratio"]) for symbol, position in positions.items())
        if cash < -1e-8:
            raise ArithmeticError("포트폴리오 현금이 음수입니다.")
        curve.append({"date": day, "equity": cash + marked, "cash": cash, "positions": len(positions)})
    return {"summary": summarize(curve, trades, starting_cash), "curve": curve,
            "trades": trades, "decisions": decisions}


def simulate_walk_forward(series, market, costs, spread_ratio, start, end, selection_days=21, strict_selection=False, rules_override=None):
    """최근 훈련 63일·검증 21일로 선택하고 다음 21일만 운용한다.

    세 번째 가설: 긴 상승장에서 고른 고정 규칙 대신 과거 자료만으로 국면에 대응한다.
    후보가 모두 손실이면 현금으로 쉰다. 구간 경계는 비용을 내고 청산한다.
    선택 간격은 사전에 고정한다. 이후 구간 결과로 간격을 고르지 않는다.
    """
    dates = common_dates(series, start, end)
    all_dates = common_dates(series, "1900-01-01", end)
    starting_cash = costs["starting_cash"][market]
    capital = starting_cash
    curve, trades, selections = [], [], []
    rules = rules_override or candidate_rules() + reversal_rules()
    for first in range(0, len(dates), selection_days):
        segment = dates[first:first + selection_days]
        past_dates = [day for day in all_dates if day < segment[0]]
        if len(past_dates) < 184:
            raise ValueError("순차 선택에 필요한 예열·훈련·검증 표본이 없습니다.")
        training_dates = past_dates[-84:-21]
        validation_dates = past_dates[-21:]
        # 최장 신호 120일 + 훈련·검증 84일보다 긴 240일을 남긴다.
        # 수년 자료에서 매 후보마다 전체 과거를 복사하지 않아도 신호 값은 동일하다.
        window_start = past_dates[-240] if len(past_dates) >= 240 else past_dates[0]
        past_series = {symbol: [bar for bar in bars if window_start <= bar["date"] < segment[0]] for symbol, bars in series.items()}
        benchmark = simulate_portfolio(past_series, market, rules[0], costs, spread_ratio,
                                       validation_dates[0], validation_dates[-1], True)["summary"] if strict_selection else None
        stressed_costs = {**costs, **{key: costs[key] * 2 for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
        trials = []
        for trial_number, rule in enumerate(rules, 1):
            training = simulate_portfolio(past_series, market, rule, costs, spread_ratio, training_dates[0], training_dates[-1])["summary"]
            validation = simulate_portfolio(past_series, market, rule, costs, spread_ratio, validation_dates[0], validation_dates[-1])["summary"]
            # 적은 거래의 운 좋은 수익을 피한다. 후보 없음이면 시장에 진입하지 않는다.
            eligible = training["net_return"] > 0 and validation["net_return"] > 0 and validation["trades"] >= 3
            stress = None
            if strict_selection:
                stress = simulate_portfolio(past_series, market, rule, stressed_costs, spread_ratio * 2,
                                            validation_dates[0], validation_dates[-1])["summary"]
                eligible = eligible and stress["net_return"] > 0 and validation["net_return"] > benchmark["net_return"] and validation["max_drawdown"] <= .05
            trials.append({"trial_number": trial_number, "rule": rule, "training": training, "validation": validation,
                           "validation_double_cost": stress, "eligible": eligible})
        eligible = [trial for trial in trials if trial["eligible"]]
        chosen = max(eligible, key=lambda trial: trial["validation"]["net_return"] - trial["validation"]["max_drawdown"]) if eligible else None
        selections.append({"selected_at": past_dates[-1], "start": segment[0], "end": segment[-1],
                           "selected": chosen, "trials": trials})
        if chosen is None:
            curve.extend({"date": day, "equity": capital, "cash": capital, "positions": 0} for day in segment)
            continue
        segment_costs = {**costs, "starting_cash": {**costs["starting_cash"], market: capital}}
        execution_series = {symbol: [bar for bar in bars if window_start <= bar["date"] <= segment[-1]] for symbol, bars in series.items()}
        result = simulate_portfolio(execution_series, market, chosen["rule"], segment_costs, spread_ratio, segment[0], segment[-1])
        curve.extend(result["curve"])
        trades.extend(result["trades"])
        capital = result["curve"][-1]["equity"]
    return {"summary": summarize(curve, trades, starting_cash), "curve": curve,
            "trades": trades, "selections": selections}


def replay_selected_rules(series, market, costs, spread_ratio, selections):
    """규칙 선택을 바꾸지 않고 체결 비용만 스트레스 처리한다."""
    starting_cash = costs["starting_cash"][market]
    capital = starting_cash
    curve, trades = [], []
    for selection in selections:
        if selection["selected"] is None:
            curve.extend({"date": day, "equity": capital, "cash": capital, "positions": 0}
                         for day in common_dates(series, selection["start"], selection["end"]))
            continue
        segment_costs = {**costs, "starting_cash": {**costs["starting_cash"], market: capital}}
        result = simulate_portfolio(series, market, selection["selected"]["rule"], segment_costs, spread_ratio,
                                    selection["start"], selection["end"])
        curve.extend(result["curve"])
        trades.extend(result["trades"])
        capital = curve[-1]["equity"]
    return {"summary": summarize(curve, trades, starting_cash), "curve": curve, "trades": trades}


def stress_recorded_trades(trades, starting_cash, original_costs, stressed_costs, original_spread, stressed_spread):
    """체결 날짜·수량을 고정해 순수 비용 증가 영향을 분리한다. 실제 재운용과 구분한다."""
    profit = 0.0
    for trade in trades:
        buy_reference = trade["entry_price"] / ((1 + original_spread / 2) * (1 + original_costs["slippage_ratio"]))
        sell_reference = trade["exit_price"] / ((1 - original_spread / 2) * (1 - original_costs["slippage_ratio"]))
        spent = trade["quantity"] * execution_price(buy_reference, "BUY", stressed_costs, stressed_spread) * (1 + stressed_costs["buy_cost_ratio"])
        received = trade["quantity"] * execution_price(sell_reference, "SELL", stressed_costs, stressed_spread) * (1 - stressed_costs["sell_cost_ratio"])
        profit += received - spent
    return {"net_pnl": profit, "net_return": profit / starting_cash, "trades": len(trades)}
