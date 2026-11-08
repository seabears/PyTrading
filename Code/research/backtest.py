"""봉을 순서대로 재생하는 연구 전용 모의매매. 미래 봉으로 신호를 계산하지 않는다.

수정 위치: entry_signal()은 진입 가설, simulate()는 체결·청산 순서,
candidate_rules()는 미리 정한 제한된 비교 후보다. 실시간 뉴스 전략과 별개다.
"""
import math
from strategy.engine import require_number


def validate_costs(costs):
    """수정한 모의 계좌 비용이 음수·무한대·과도한 비율이면 계산을 중단한다."""
    for market in ("KR", "US"):
        require_number(costs["starting_cash"][market])
    for name in ("allocation_fraction", "buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
        value = require_number(costs[name], allow_zero=name != "allocation_fraction")
        if value >= 1:
            raise ValueError("모의 계좌 비율은 1 미만이어야 합니다.")


def candidate_rules():
    """12개 기본 조합을 당일 청산·최대 5세션 보유로 비교한다. 모든 시도는 기록한다.

    2차 연구에서 비용 영향을 줄이기 위해 보유 방식을 추가했다. 이미 본 시험 기간의
    재사용은 보고서에서 별도로 표시하며, 양수가 나와도 새 검증으로 간주하지 않는다.
    """
    candidates = []
    for family in ("breakout", "pullback", "mean_reversion"):
        for lookback in (10, 20):
            for stop_loss in (0.01, 0.02):
                for hold_overnight in (False, True):
                    candidates.append({"family": family, "lookback": lookback,
                                       "volume_ratio": 1.5 if family == "breakout" else 1.0,
                                       "stop_loss": stop_loss, "trailing_stop": 0.02,
                                       "deviation": 0.01, "max_chase": 0.02,
                                       "hold_overnight": hold_overnight, "max_holding_sessions": 5})
    return candidates


def entry_signal(history, rule):
    """history에는 해당 시각까지 끝난 봉만 들어온다. 거래량도 이전 봉과 비교한다."""
    lookback = rule["lookback"]
    if len(history) < lookback + 1:
        return False
    previous = history[-lookback - 1:-1]
    latest = history[-1]
    average = sum(bar["close"] for bar in previous) / lookback
    average_volume = sum(bar["volume"] for bar in previous) / lookback
    if average_volume <= 0 or latest["volume"] < average_volume * rule["volume_ratio"]:
        return False
    if rule["family"] == "breakout":
        prior_high = max(bar["high"] for bar in previous)
        return prior_high < latest["close"] <= prior_high * (1 + rule["max_chase"])
    if rule["family"] == "pullback":
        return previous[-1]["close"] <= average < latest["close"]
    if rule["family"] == "mean_reversion":
        return latest["close"] < average * (1 - rule["deviation"])
    raise ValueError("알 수 없는 연구 전략 종류입니다.")


def exit_signal(history, rule):
    if len(history) < rule["lookback"] + 1:
        return False
    average = sum(bar["close"] for bar in history[-rule["lookback"] - 1:-1]) / rule["lookback"]
    if rule["family"] == "mean_reversion":
        return history[-1]["close"] >= average
    return history[-1]["close"] < average


def execution_price(reference, action, costs, spread_ratio):
    """과거 호가가 없으므로 스프레드·슬리피지는 불리한 방향의 고정 가정이다."""
    adjustment = (1 + spread_ratio / 2) * (1 + costs["slippage_ratio"])
    if action == "BUY":
        return reference * adjustment
    return reference * (1 - spread_ratio / 2) * (1 - costs["slippage_ratio"])


def summarize(curve, trades, starting_cash):
    equity = curve[-1]["equity"] if curve else starting_cash
    peak = starting_cash
    maximum_drawdown = 0.0
    for row in curve:
        peak = max(peak, row["equity"])
        maximum_drawdown = max(maximum_drawdown, 1 - row["equity"] / peak)
    wins = sum(trade["pnl"] > 0 for trade in trades)
    gross_gain = sum(max(0, trade["pnl"]) for trade in trades)
    gross_loss = -sum(min(0, trade["pnl"]) for trade in trades)
    return {"net_pnl": equity - starting_cash, "net_return": equity / starting_cash - 1,
            "max_drawdown": maximum_drawdown, "trades": len(trades),
            "win_rate": wins / len(trades) if trades else None,
            "profit_factor": gross_gain / gross_loss if gross_loss else None}


def simulate(sessions, rule, costs, spread_ratio):
    """다음 봉 시가 체결 → 기존 손절 → 현재 봉 종료 신호 순서다.

    당일 청산 또는 최대 보유 세션에서 청산한다. 청산 후 30분 재진입을 막는다.
    OHLC만으로 봉 안 경로를 모르므로 손절은 저가가 닿으면 체결된 것으로 보수 처리한다.
    고가로 높아진 추적 손절은 다음 봉부터 적용한다. 호가·체결 대기·수량은 미재현이다.
    """
    market = sessions[0]["market"] if sessions else "US"
    starting_cash = costs["starting_cash"][market]
    cash = starting_cash
    budget = starting_cash * costs["allocation_fraction"]
    trades, curve = [], []
    position = None
    pending_entry = pending_exit = False
    cooldown_bars = 0
    hold_overnight = rule.get("hold_overnight", False)

    def sell(reference, when, reason):
        nonlocal cash, position
        price = execution_price(reference, "SELL", costs, spread_ratio)
        proceeds = position["quantity"] * price * (1 - costs["sell_cost_ratio"])
        cash += proceeds
        trades.append({"entry_at": position["entry_at"], "exit_at": when,
                       "entry_price": position["price"], "exit_price": price,
                       "quantity": position["quantity"], "pnl": proceeds - position["cost"], "reason": reason})
        position = None

    for session_index, session in enumerate(sessions):
        pending_entry = False
        entry_limit = None
        if position:
            position["holding_sessions"] += 1
        bars = session["bars"]
        for index, bar in enumerate(bars):
            if pending_exit and position:
                sell(bar["open"], bar["start"], "prior_bar_exit_signal")
                cooldown_bars = 6
            if pending_entry and position is None and cooldown_bars == 0:
                price = execution_price(bar["open"], "BUY", costs, spread_ratio)
                quantity = math.floor(min(cash, budget) / (price * (1 + costs["buy_cost_ratio"])))
                if quantity > 0 and (entry_limit is None or price <= entry_limit):
                    cost = quantity * price * (1 + costs["buy_cost_ratio"])
                    cash -= cost
                    position = {"quantity": quantity, "price": price, "cost": cost,
                                "peak": bar["open"], "entry_at": bar["start"], "holding_sessions": 1}
            pending_entry = pending_exit = False
            if position:
                stop = max(position["price"] * (1 - rule["stop_loss"]),
                           position["peak"] * (1 - rule["trailing_stop"]))
                if bar["low"] <= stop:
                    sell(min(bar["open"], stop), bar["end"], "stop_or_trailing_gap_adjusted")
                    cooldown_bars = 6
                else:
                    position["peak"] = max(position["peak"], bar["high"])
            if index == len(bars) - 1 and position:
                if (not hold_overnight or session_index == len(sessions) - 1
                        or position["holding_sessions"] >= rule.get("max_holding_sessions", 5)):
                    sell(bar["close"], bar["end"], "session_end_or_holding_limit")
            # 종가로 계산한 신호는 같은 세션에 다음 봉이 있을 때만 사용한다.
            history = bars[:index + 1]
            if index < len(bars) - 1:
                if position:
                    # 2차 후보는 추세 진입 후 잦은 평균가격 청산을 줄이고 손절·보유 기한을 쓴다.
                    if not hold_overnight or rule["family"] == "mean_reversion":
                        pending_exit = exit_signal(history, rule)
                elif cooldown_bars == 0:
                    pending_entry = entry_signal(history, rule)
                    if pending_entry:
                        reference = max(previous["high"] for previous in history[-rule["lookback"] - 1:-1]) if rule["family"] == "breakout" else bar["close"]
                        # 다음 봉 시가가 갑자기 뛰면 신호 시점의 추격 한도로 매수를 취소한다.
                        entry_limit = reference * (1 + rule["max_chase"])
            if cooldown_bars > 0:
                cooldown_bars -= 1
            marked = 0.0
            if position:
                price = execution_price(bar["close"], "SELL", costs, spread_ratio)
                marked = position["quantity"] * price * (1 - costs["sell_cost_ratio"])
            curve.append({"at": bar["end"], "date": session["date"], "equity": cash + marked})
    return {"summary": summarize(curve, trades, starting_cash), "curve": curve, "trades": trades}


def buy_and_hold(sessions, costs, spread_ratio):
    """같은 초기 투자 비중으로 첫 시가 매수·마지막 종가 매도. 수량·비용도 동일 적용한다."""
    if not sessions:
        return 0.0
    starting = costs["starting_cash"][sessions[0]["market"]]
    entry = execution_price(sessions[0]["bars"][0]["open"], "BUY", costs, spread_ratio)
    quantity = math.floor(starting * costs["allocation_fraction"] / (entry * (1 + costs["buy_cost_ratio"])))
    spent = quantity * entry * (1 + costs["buy_cost_ratio"])
    exit_price = execution_price(sessions[-1]["bars"][-1]["close"], "SELL", costs, spread_ratio)
    proceeds = quantity * exit_price * (1 - costs["sell_cost_ratio"])
    return (proceeds - spent) / starting


def split_sessions(sessions, training_fraction=0.6, validation_fraction=0.2):
    """날짜순으로 분리한다. 세션과 보유를 분할 경계에 걸치지 않는다."""
    first = int(len(sessions) * training_fraction)
    second = int(len(sessions) * (training_fraction + validation_fraction))
    return {"training": sessions[:first], "validation": sessions[first:second], "test": sessions[second:]}


def compare_rules(sessions, costs, settings):
    """훈련 비교 → 검증 비교 → 후보 고정 → 최종 시험 1회. 시험 결과로 재선정하지 않는다."""
    splits = split_sessions(sessions, settings["training_fraction"], settings["validation_fraction"])
    trials = []
    for trial_id, rule in enumerate(candidate_rules(), 1):
        training = simulate(splits["training"], rule, costs, settings["assumed_spread_ratio"])["summary"]
        trials.append({"trial_id": trial_id, "rule": rule, "training": training})
    # 거래가 너무 적은 후보가 한 번의 운 좋은 체결만으로 선택되지 않도록 한다.
    ranked = sorted(trials, key=lambda trial: (
        trial["training"]["trades"] >= 10,
        trial["training"]["net_return"] - trial["training"]["max_drawdown"],
    ), reverse=True)
    finalists = ranked[:3]
    for trial in finalists:
        trial["validation"] = simulate(splits["validation"], trial["rule"], costs, settings["assumed_spread_ratio"])["summary"]
    selected = max(finalists, key=lambda trial: (
        trial["validation"]["trades"] >= 5,
        trial["validation"]["net_return"] - trial["validation"]["max_drawdown"],
    ))
    test = simulate(splits["test"], selected["rule"], costs, settings["assumed_spread_ratio"])
    stressed_costs = {**costs, "buy_cost_ratio": costs["buy_cost_ratio"] * 2,
                      "sell_cost_ratio": costs["sell_cost_ratio"] * 2,
                      "slippage_ratio": costs["slippage_ratio"] * 2}
    stress = simulate(splits["test"], selected["rule"], stressed_costs, settings["assumed_spread_ratio"] * 2)["summary"]
    benchmark = buy_and_hold(splits["test"], costs, settings["assumed_spread_ratio"])
    checks = {
        "sufficient_sessions": len(sessions) >= settings["minimum_sessions_per_symbol"],
        "training_positive": selected["training"]["net_return"] > 0,
        "validation_positive": selected["validation"]["net_return"] > 0,
        "test_positive": test["summary"]["net_return"] > 0,
        "test_beats_buy_and_hold": test["summary"]["net_return"] > benchmark,
        "sufficient_test_trades": test["summary"]["trades"] >= settings["minimum_test_trades_per_market"],
        "test_drawdown_within_limit": test["summary"]["max_drawdown"] <= settings["maximum_test_drawdown"],
        "double_cost_test_positive": stress["net_return"] > 0,
    }
    periods = {name: {"sessions": len(rows), "start": rows[0]["date"] if rows else None,
                      "end": rows[-1]["date"] if rows else None} for name, rows in splits.items()}
    return {"trials": trials, "selected_trial_id": selected["trial_id"], "selected_rule": selected["rule"],
            "periods": periods, "test": test, "double_cost_test": stress,
            "buy_and_hold_test_return": benchmark, "checks": checks,
            "verdict": "research_candidate_passed" if all(checks.values()) else "rejected"}
