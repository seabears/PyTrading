"""일봉으로 비용을 견딜 수 있는 후보를 찾는다. 장중 전략 검증과 분리한다.

다음 날 시가 체결·갭 손절·정수 수량·비용은 분봉 연구와 같은 가정을 쓴다.
수정 위치: rules_for_round()의 가설, signal()의 진입 조건. 딥러닝은 쓰지 않는다.
"""
import math

from research.backtest import execution_price, summarize
from strategy.engine import parse_timestamp, require_number


def prepare_daily_bars(record):
    if record.get("interval") != "1d":
        raise ValueError("일봉 연구에는 1d 자료가 필요합니다.")
    currency = "KRW" if record["market"] == "KR" else "USD"
    bars = []
    seen = set()
    for candle in sorted(record["candles"], key=lambda row: parse_timestamp(row["timestamp"])):
        timestamp = parse_timestamp(candle["timestamp"])
        if timestamp in seen or candle.get("currency") != currency:
            raise ValueError("일봉에 중복 시각 또는 다른 통화가 있습니다.")
        seen.add(timestamp)
        bar = {name: require_number(candle[field], allow_zero=name == "volume") for name, field in
               (("open", "openPrice"), ("high", "highPrice"), ("low", "lowPrice"), ("close", "closePrice"), ("volume", "volume"))}
        if not bar["low"] <= bar["open"] <= bar["high"] or not bar["low"] <= bar["close"] <= bar["high"]:
            raise ValueError("일봉 가격 범위가 잘못됐습니다.")
        # 날짜는 API의 일봉 라벨을 사용한다. 실제 일중 시각이라고 해석하지 않는다.
        bar["date"] = candle["timestamp"][:10]
        bars.append(bar)
    return bars


def rules_for_round(round_name):
    """3개 수정 방향을 미리 정하고 훈련·검증에만 비교한다. 총 24개 가설이다."""
    candidates = []
    if round_name not in {"breakout", "trend_filter", "pullback"}:
        raise ValueError("지원하지 않는 연구 반복 단계입니다.")
    for lookback in (20, 40):
        for stop_loss in (0.03, 0.05):
            for holding_days in (10, 20):
                candidates.append({"family": "pullback" if round_name == "pullback" else "breakout",
                                   "lookback": lookback, "stop_loss": stop_loss, "trailing_stop": 0.08,
                                   "holding_days": holding_days, "volume_ratio": 1.0,
                                   "trend_filter": round_name != "breakout", "trend_days": 100,
                                   "max_chase": 0.03, "cooldown_days": 3})
    return candidates


def signal_details(history, rule):
    """조건별 값을 함께 반환한다. 차단 수는 검사 순서에 좌우되므로 독립 실패도 기록한다."""
    if len(history) < rule["lookback"] + 1:
        return {"passed": False, "conditions": {"history": False}, "values": {}}
    latest = history[-1]
    previous = history[-rule["lookback"] - 1:-1]
    mean = sum(bar["close"] for bar in previous) / len(previous)
    mean_volume = sum(bar["volume"] for bar in previous) / len(previous)
    conditions = {"history": True,
                  "volume": not rule.get("volume_filter", True) or (mean_volume > 0 and latest["volume"] >= mean_volume * rule["volume_ratio"])}
    values = {"volume_ratio": latest["volume"] / mean_volume if mean_volume > 0 else None,
              "fast_mean": mean}
    if rule["trend_filter"]:
        if len(history) < rule["trend_days"] + 1:
            conditions["trend"] = False
        else:
            long_mean = sum(bar["close"] for bar in history[-rule["trend_days"] - 1:-1]) / rule["trend_days"]
            values["long_mean"] = long_mean
            conditions["trend"] = latest["close"] > mean > long_mean
    else:
        conditions["trend"] = True
    if rule["family"] == "breakout":
        prior_high = max(bar["high"] for bar in previous)
        conditions["price_signal"] = prior_high < latest["close"]
        conditions["chase"] = latest["close"] <= prior_high * (1 + rule["max_chase"])
        values["breakout_distance"] = latest["close"] / prior_high - 1
    elif rule["family"] == "trend_follow":
        conditions["price_signal"] = latest["close"] > mean
        conditions["chase"] = True
    else:
        conditions["price_signal"] = previous[-1]["close"] <= mean < latest["close"]
        conditions["chase"] = True
    return {"passed": all(conditions.values()), "conditions": conditions, "values": values}


def signal(history, rule):
    """끝난 일봉의 종가·거래량으로 다음 날 신호만 계산한다."""
    return signal_details(history, rule)["passed"]


def simulate_daily(bars, market, rule, costs, spread_ratio, warmup=None, entry_filter=None):
    """종가 신호 → 다음 날 시가 체결 → 이전 고점 기준 손절 → 당일 종가 기록.

    warmup은 이전 구간의 가격만 제공한다. 구간 자금·보유는 이월하지 않으며 warmup에
    거래하거나 성과를 합산하지 않는다. 손절은 봉 내 경로를 몰라 보수적으로 처리한다.
    """
    starting = costs["starting_cash"][market]
    budget = starting * costs["allocation_fraction"]
    cash = starting
    position = None
    pending = False
    entry_limit = None
    cooldown = 0
    history = list(warmup or [])
    trades, curve = [], []
    filter_checks, filter_blocks = 0, 0
    diagnostics = {"eligible_days": 0, "position_days": 0, "cooldown_days": 0, "last_day": 0,
                   "independent_failures": {}, "first_blocks": {}, "orders_planned": 0,
                   "gap_cancellations": 0, "cash_cancellations": 0, "entries": 0}
    signal_date = None

    def count_block(reason):
        diagnostics["first_blocks"][reason] = diagnostics["first_blocks"].get(reason, 0) + 1

    def sell(reference, date, reason, stop_type=None, gap_through_stop=False):
        nonlocal cash, position, cooldown
        price = execution_price(reference, "SELL", costs, spread_ratio)
        proceeds = position["quantity"] * price * (1 - costs["sell_cost_ratio"])
        cash += proceeds
        trades.append({"entry_date": position["entry_date"], "exit_date": date,
                       "quantity": position["quantity"], "entry_price": position["price"],
                       "exit_price": price, "pnl": proceeds - position["cost"], "reason": reason,
                       "entry_cost": position["cost"], "signal_date": position["signal_date"],
                       "stop_type": stop_type, "gap_through_stop": gap_through_stop})
        position = None
        cooldown = rule["cooldown_days"]

    for index, bar in enumerate(bars):
        if pending and not position and cooldown == 0:
            price = execution_price(bar["open"], "BUY", costs, spread_ratio)
            quantity = math.floor(min(cash, budget) / (price * (1 + costs["buy_cost_ratio"])))
            if quantity > 0 and price <= entry_limit:
                cost = quantity * price * (1 + costs["buy_cost_ratio"])
                cash -= cost
                position = {"quantity": quantity, "price": price, "cost": cost,
                            "peak": bar["open"], "entry_index": index, "entry_date": bar["date"], "signal_date": signal_date}
                diagnostics["entries"] += 1
            elif quantity <= 0:
                diagnostics["cash_cancellations"] += 1
            else:
                diagnostics["gap_cancellations"] += 1
        pending = False
        if position:
            fixed_stop = position["price"] * (1 - rule["stop_loss"])
            trailing_stop = position["peak"] * (1 - rule["trailing_stop"])
            stop = max(fixed_stop, trailing_stop)
            if bar["low"] <= stop:
                sell(min(bar["open"], stop), bar["date"], "gap_adjusted_stop",
                     "trailing_stop" if trailing_stop > fixed_stop else "fixed_stop", bar["open"] < stop)
            else:
                position["peak"] = max(position["peak"], bar["high"])
        if position and (index == len(bars) - 1 or index - position["entry_index"] + 1 >= rule["holding_days"]):
            sell(bar["close"], bar["date"], "holding_limit_or_period_end")
        history.append(bar)
        if not position and cooldown == 0 and index < len(bars) - 1:
            diagnostics["eligible_days"] += 1
            detail = signal_details(history, rule)
            pending = detail["passed"]
            for name, passed in detail["conditions"].items():
                if not passed:
                    diagnostics["independent_failures"][name] = diagnostics["independent_failures"].get(name, 0) + 1
            if not pending:
                # 가격 신호가 없는 날을 거래량 차단으로 오해하지 않도록 가격부터 집계한다.
                for name in ("history", "price_signal", "volume", "trend", "chase"):
                    if detail["conditions"].get(name) is False:
                        count_block(name)
                        break
            # 외부 지표는 신규 진입만 제한한다. 자료 누락이 기존 포지션의 손절을 막지 않는다.
            if pending and entry_filter is not None:
                filter_checks += 1
                pending = entry_filter(bar["date"])
                if not pending:
                    filter_blocks += 1
                    count_block("external_indicator")
            if pending:
                reference = max(row["high"] for row in history[-rule["lookback"] - 1:-1]) if rule["family"] == "breakout" else bar["close"]
                entry_limit = reference * (1 + rule["max_chase"])
                signal_date = bar["date"]
                diagnostics["orders_planned"] += 1
        elif index == len(bars) - 1:
            diagnostics["last_day"] += 1
        elif position:
            diagnostics["position_days"] += 1
        else:
            diagnostics["cooldown_days"] += 1
        if cooldown > 0:
            cooldown -= 1
        marked = 0.0
        if position:
            price = execution_price(bar["close"], "SELL", costs, spread_ratio)
            marked = position["quantity"] * price * (1 - costs["sell_cost_ratio"])
        curve.append({"date": bar["date"], "equity": cash + marked})
    return {"summary": summarize(curve, trades, starting), "curve": curve, "trades": trades,
            "entry_filter_checks": filter_checks, "entry_filter_blocks": filter_blocks, "diagnostics": diagnostics}


def benchmark_daily(bars, market, costs, spread_ratio):
    first = execution_price(bars[0]["open"], "BUY", costs, spread_ratio)
    starting = costs["starting_cash"][market]
    quantity = math.floor(starting * costs["allocation_fraction"] / (first * (1 + costs["buy_cost_ratio"])))
    cost = quantity * first * (1 + costs["buy_cost_ratio"])
    last = execution_price(bars[-1]["close"], "SELL", costs, spread_ratio)
    return (quantity * last * (1 - costs["sell_cost_ratio"]) - cost) / starting


def develop_rules(training, validation, market, costs, settings):
    """반복 수정은 여기서만 한다. 함수에는 최종 시험 가격을 전달하지 않는다."""
    rounds = []
    all_finalists = []
    for round_name in settings["rounds"]:
        trials = []
        for rule in rules_for_round(round_name):
            result = simulate_daily(training, market, rule, costs, settings["assumed_spread_ratio"])
            trials.append({"rule": rule, "training": result["summary"]})
        ranked = sorted(trials, key=lambda trial: (
            trial["training"]["trades"] >= settings["minimum_training_trades"],
            trial["training"]["net_return"] - trial["training"]["max_drawdown"],
        ), reverse=True)
        finalists = ranked[:3]
        for candidate in finalists:
            result = simulate_daily(validation, market, candidate["rule"], costs,
                                    settings["assumed_spread_ratio"], warmup=training)
            candidate["validation"] = result["summary"]
            all_finalists.append(candidate)
        rounds.append({"round": round_name, "trials": trials})
    selected = max(all_finalists, key=lambda trial: (
        trial["training"]["net_return"] > 0 and trial["validation"]["net_return"] > 0,
        trial["validation"]["trades"] >= settings["minimum_validation_trades"],
        trial["validation"]["net_return"] - trial["validation"]["max_drawdown"],
    ))
    return {"rounds": rounds, "selected": selected}
