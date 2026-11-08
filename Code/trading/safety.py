"""모의 계좌의 신규 매수 안전장치. 보유분의 유효한 가격 매도 신호는 차단하지 않는다.

일일 손실은 시장별 현지 거래일의 첫 유효 관측 직전 저장된 순청산 평가액 대비다.
공식 증권사 일일 손익이 아니며, 평가에 필요한 다른 보유 호가가 오래되면 신규 매수를 막는다.
"""
import json
import math
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from paths import CONFIG_ROOT
from strategy.engine import parse_timestamp, require_number


DEFAULT_SAFETY = {
    "enabled": True,
    "daily_loss_limit": .02,               # 일일 첫 관측 직전 평가 대비 손실 2%에서 당일 매수 중단.
    "maximum_trade_risk": .005,           # 진입 원가·초기 손절·매도 비용 기준 초기 자금의 0.5% 이내.
    "maximum_order_fraction": .10,        # 한 번의 매수 원가: 초기 시장 자금 10% 이내.
    "maximum_exposure_fraction": .50,     # 매입 원가 합계: 초기 시장 자금 50% 이내.
    "maximum_buys_per_day": 10,
    "consecutive_losses": 3,
    "loss_cooldown_minutes": 60,
    "portfolio_quote_max_age_seconds": 180,
    "maximum_quote_jump": .10,            # 같은 날 최근 5분 이내 관측보다 10% 급변 시 한 번 매수 보류.
    "quote_reference_seconds": 300,
}


def load_policy(overrides=None):
    path = CONFIG_ROOT / "safety.json"
    policy = dict(DEFAULT_SAFETY)
    if path.exists():
        policy.update(json.loads(path.read_text(encoding="utf-8-sig")))
    if overrides is not None:
        policy.update(overrides)
    if set(policy) != set(DEFAULT_SAFETY) or type(policy["enabled"]) is not bool:
        raise ValueError("안전장치 설정 이름·활성화 값을 확인하세요.")
    for name in ("daily_loss_limit", "maximum_trade_risk", "maximum_order_fraction", "maximum_exposure_fraction", "maximum_quote_jump"):
        if not 0 < require_number(policy[name]) < 1:
            raise ValueError("안전장치 비율은 0 초과 1 미만입니다.")
    for name in ("maximum_buys_per_day", "consecutive_losses", "loss_cooldown_minutes", "portfolio_quote_max_age_seconds", "quote_reference_seconds"):
        if type(policy[name]) is not int or policy[name] < 1:
            raise ValueError("안전장치 횟수·시간은 양의 정수입니다.")
    return policy


def local_day(market, now):
    return now.astimezone(ZoneInfo("America/New_York" if market == "US" else "Asia/Seoul")).date().isoformat()


def equity(state, market, costs):
    value = require_number(state["cash"][market], allow_zero=True)
    for key, position in state["positions"].items():
        if position["market"] == market:
            bid = require_number(state.get("last_prices", {}).get(key))
            value += position["quantity"] * bid * (1 - costs["slippage_ratio"]) * (1 - costs["sell_cost_ratio"])
    return value


def begin_day(state, market, now, costs):
    """재시작해도 같은 거래일의 기준과 중단 상태를 유지한다."""
    day = local_day(market, now)
    markets = state.setdefault("safety_days", {})
    if market not in markets or markets[market]["day"] != day:
        try:
            baseline = equity(state, market, costs)
            unavailable = False
        except (KeyError, TypeError, ValueError):
            baseline, unavailable = 0, True
        markets[market] = {"day": day, "baseline_equity": baseline,
                           "loss_halted": False, "valuation_unavailable": unavailable}


def observe_loss(state, market, costs, policy):
    guard = state["safety_days"][market]
    try:
        current = equity(state, market, costs)
    except (KeyError, TypeError, ValueError):
        guard["valuation_unavailable"] = True
        current = None
    baseline = guard["baseline_equity"]
    if guard.get("valuation_unavailable"):
        return {"day": guard["day"], "baseline_equity": baseline, "current_net_equity": current,
                "valuation_available": False, "daily_loss_halted": guard["loss_halted"]}
    loss = 1 - current / baseline if baseline > 0 else 1
    if policy["enabled"] and loss >= policy["daily_loss_limit"]:
        guard["loss_halted"] = True
    return {"day": guard["day"], "baseline_equity": baseline, "current_net_equity": current,
            "daily_loss_ratio": loss, "daily_loss_halted": guard["loss_halted"]}


def entry_limits(state, snapshot, strategy, costs, policy, account_path, previous_quote=None):
    """매수 판단에 필요한 평가·시세 신선도·횟수·손실·수량 상한을 반환한다."""
    now = parse_timestamp(snapshot["now"])
    market, symbol = snapshot["market"], snapshot["symbol"]
    key = market + ":" + symbol
    metrics = {"enabled": policy["enabled"]}
    if not policy["enabled"]:
        return None, math.inf, metrics
    if (Path(account_path).parent / "PAUSE_BUYS").exists():
        return "manual_buy_pause", 0, metrics
    day = local_day(market, now)
    guard = state["safety_days"][market]
    if guard.get("valuation_unavailable"):
        return "valuation_unavailable", 0, {**metrics, "day": day, "valuation_available": False}
    current_equity = equity(state, market, costs)
    baseline = guard["baseline_equity"]
    loss = 1 - current_equity / baseline if baseline > 0 else 1
    if loss >= policy["daily_loss_limit"]:
        guard["loss_halted"] = True
    metrics.update(day=day, baseline_equity=baseline, current_net_equity=current_equity,
                   daily_loss_ratio=loss, daily_loss_halted=guard["loss_halted"])
    if guard["loss_halted"]:
        return "daily_loss_halt", 0, metrics
    same_day = [trade for trade in state["trades"] if trade["market"] == market and local_day(market, parse_timestamp(trade["at"])) == day]
    buy_count = sum(trade["action"] == "BUY" for trade in same_day)
    metrics["buys_today"] = buy_count
    if buy_count >= policy["maximum_buys_per_day"]:
        return "daily_buy_limit", 0, metrics
    sells = [trade for trade in same_day if trade["action"] == "SELL"]
    streak = 0
    for trade in reversed(sells):
        if trade["realized_pnl"] >= 0:
            break
        streak += 1
    metrics["consecutive_losses"] = streak
    if streak >= policy["consecutive_losses"]:
        until = parse_timestamp(sells[-1]["at"]) + timedelta(minutes=policy["loss_cooldown_minutes"])
        metrics["loss_pause_until"] = until.isoformat()
        if now < until:
            return "consecutive_loss_pause", 0, metrics
    for held_key, position in state["positions"].items():
        if position["market"] != market:
            continue
        timestamp = state.get("quote_times", {}).get(held_key)
        if not timestamp or not 0 <= (now - parse_timestamp(timestamp)).total_seconds() <= policy["portfolio_quote_max_age_seconds"]:
            return "portfolio_quote_unavailable", 0, metrics
    current_mid = (float(snapshot["quote"]["bid"]) + float(snapshot["quote"]["ask"])) / 2
    if previous_quote and local_day(market, parse_timestamp(previous_quote["at"])) == day:
        age = (now - parse_timestamp(previous_quote["at"])).total_seconds()
        jump = abs(current_mid / previous_quote["mid"] - 1)
        metrics["quote_jump_ratio"] = jump
        if 0 < age <= policy["quote_reference_seconds"] and jump > policy["maximum_quote_jump"]:
            return "abrupt_quote_change", 0, metrics
    initial = costs["starting_cash"][market]
    committed = sum(position["cost_basis"] for position in state["positions"].values() if position["market"] == market)
    remaining_exposure = max(0, initial * policy["maximum_exposure_fraction"] - committed)
    budget_cap = min(initial * policy["maximum_order_fraction"], remaining_exposure)
    ask = float(snapshot["quote"]["ask"])
    unit_cost = ask * (1 + costs["slippage_ratio"]) * (1 + costs["buy_cost_ratio"])
    # 실제 가격 손절과 같은 평균 원가 기준이다. 갭 손실의 상한을 보장하지 않는다.
    stop_bid = unit_cost * (1 - strategy["stop_loss"])
    stop_received = stop_bid * (1 - costs["slippage_ratio"]) * (1 - costs["sell_cost_ratio"])
    risk_per_share = max(unit_cost - stop_received, 1e-12)
    remaining_daily_loss = max(0, baseline * policy["daily_loss_limit"] - (baseline - current_equity))
    maximum_quantity = min(math.floor(budget_cap / unit_cost), math.floor(min(initial * policy["maximum_trade_risk"], remaining_daily_loss) / risk_per_share))
    metrics.update(remaining_exposure_budget=remaining_exposure, maximum_quantity=maximum_quantity,
                   risk_per_share_at_stop=risk_per_share, maximum_trade_risk_amount=initial * policy["maximum_trade_risk"])
    if maximum_quantity < 1:
        return "risk_or_exposure_limit", 0, metrics
    return None, maximum_quantity, metrics


def validate_account_state(state, costs):
    """손상된 저장 파일을 새 계좌로 초기화하지 않는다."""
    if not isinstance(state.get("positions"), dict) or not isinstance(state.get("trades"), list):
        raise ValueError("모의 계좌의 보유·거래 기록 형식 오류")
    for market in ("KR", "US"):
        cash = require_number(state["cash"][market], allow_zero=True)
        flows = sum(float(trade["cash_flow"]) for trade in state["trades"] if trade["market"] == market)
        if not math.isclose(cash, costs["starting_cash"][market] + flows, abs_tol=.001, rel_tol=1e-10):
            raise ValueError("모의 계좌 현금과 거래 기록 불일치")
    for key, position in state["positions"].items():
        if position["market"] not in {"KR", "US"} or key != position["market"] + ":" + position["symbol"]:
            raise ValueError("모의 계좌 종목 식별 오류")
        quantity = require_number(position["quantity"])
        if int(quantity) != quantity:
            raise ValueError("모의 계좌 수량은 양의 정수여야 합니다.")
        cost = require_number(position["cost_basis"])
        if not math.isclose(cost, quantity * require_number(position["average_cost"]), abs_tol=.001, rel_tol=1e-10):
            raise ValueError("모의 계좌 수량·원가 불일치")
    for market, guard in state.get("safety_days", {}).items():
        if market not in {"KR", "US"} or type(guard["loss_halted"]) is not bool:
            raise ValueError("저장된 일일 손실 중단 상태 오류")
        require_number(guard["baseline_equity"], allow_zero=True)
        date.fromisoformat(guard["day"])
