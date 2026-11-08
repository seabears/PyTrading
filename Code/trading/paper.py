"""모의 계좌와 거래 비용. 실제 주문 코드를 포함하지 않는다.

같은 입력을 두 번 처리하지 않으며, 계좌 상태와 모의 거래를 한 JSON에 함께 저장한다.
체결 가정은 낙관적인 가설이다: 신호 시점 호가에 설정한 슬리피지·비용을 적용한다.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

from strategy.engine import DEFAULT_CONFIG, evaluate, parse_timestamp, require_number, load_config
from trading.safety import load_policy, begin_day, observe_loss, entry_limits, validate_account_state

PAPER_DEFAULTS = {
    "starting_cash": {"KR": 10_000_000.0, "US": 10_000.0},  # 가상 자금. 실제 계좌와 무관.
    "allocation_fraction": 0.1,       # 해당 시장 초기 가상 자금의 종목별 투자 비중.
    "max_positions_per_market": 5,
    "buy_cost_ratio": 0.001,         # 수수료 등 비용의 검증용 가정. 실제 요율이 아니다.
    "sell_cost_ratio": 0.002,
    "slippage_ratio": 0.001,         # 불리한 방향으로 0.1% 가격 차이를 가정.
}


def initial_state(settings: dict) -> dict:
    return {"version": 1, "cash": copy.deepcopy(settings["starting_cash"]),
            "positions": {}, "last_processed_at": {}, "last_entry_signal_bar": {},
            "last_exit_at": {}, "trades": []}


class PaperAccount:
    """동시 실행 잠금을 획득한 호출자만 사용한다. 파일을 임의로 초기화하지 않는다."""

    def __init__(self, path: Path, settings: dict | None = None, safety_policy: dict | None = None):
        self.path = path
        self.safety_policy = load_policy(safety_policy)
        self.settings = copy.deepcopy(PAPER_DEFAULTS)
        if settings:
            if set(settings) - set(self.settings):
                raise ValueError("알 수 없는 모의 계좌 설정입니다.")
            self.settings.update(settings)
        for market in ("KR", "US"):
            self.settings["starting_cash"][market] = require_number(self.settings["starting_cash"][market])
        for name in ("allocation_fraction", "buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
            value = require_number(self.settings[name], allow_zero=True)
            if value >= 1 or (name == "allocation_fraction" and value == 0):
                raise ValueError("모의 계좌 비율은 0 이상 1 미만이어야 합니다.")
            self.settings[name] = value
        maximum = self.settings["max_positions_per_market"]
        if type(maximum) is not int or maximum < 1:
            raise ValueError("최대 보유 종목 수는 양의 정수여야 합니다.")
        self.state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else initial_state(self.settings)
        if self.state.get("version") != 1:
            raise ValueError("지원하지 않는 모의 계좌 버전입니다.")
        # 설정 변경이 기존 계좌의 자금을 바꾸지는 않는다. 초기값 비교를 기록한다.
        if "settings" in self.state and self.state["settings"] != self.settings:
            raise ValueError("기존 모의 계좌와 설정이 다릅니다. 별도 출력 폴더를 사용하세요.")
        self.state["settings"] = copy.deepcopy(self.settings)
        if self.state.get('execution_mode') in {'kis_demo','live','disabled'}:
            from trading.execution import validate_projection
            validate_projection(path,self.state,self.settings)
        else:
            validate_account_state(self.state, self.settings)

    def save(self) -> None:
        """임시 파일 작성 후 교체해서 저장 중 프로그램이 종료돼도 원본을 유지한다."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        from app.stateio import atomic_json
        atomic_json(self.path, self.state, backup=True)


    def evaluate_snapshot(self, snapshot: dict, strategy_config: dict | None = None) -> dict:
        """변경할 작은 상태만 복사한다. 저장·계산 실패 시 메모리도 이전 상태로 복원한다."""
        previous = self.state
        self.state = dict(previous)
        for name in ("cash", "last_processed_at", "last_entry_signal_bar", "last_exit_at", "last_prices", "quote_times", "quote_reference"):
            if name in previous:
                self.state[name] = dict(previous[name])
        for name in ("positions", "safety_days"):
            if name in previous:
                self.state[name] = copy.deepcopy(previous[name])
        self.state["trades"] = list(previous["trades"])
        try:
            return self._evaluate_snapshot(snapshot, strategy_config)
        except Exception:
            self.state = previous
            raise

    def _evaluate_snapshot(self, snapshot: dict, strategy_config: dict | None = None) -> dict:
        """모의 상태를 넣어 판단하고, BUY/SELL이면 가상 거래를 원자적으로 기록한다."""
        prepared = copy.deepcopy(snapshot)
        market, symbol = prepared["market"], prepared["symbol"]
        key = market + ":" + symbol
        now = parse_timestamp(prepared["now"])
        previous = self.state["last_processed_at"].get(key)
        if previous and now <= parse_timestamp(previous):
            return {"action": "WAIT", "reason": "already_processed_snapshot", "market": market,
                    "symbol": symbol, "as_of": prepared["now"], "mode": "paper"}

        position = self.state["positions"].get(key)
        quote = prepared.get("quote")
        maximum_quote_age = (strategy_config or {}).get("max_quote_age_seconds", DEFAULT_CONFIG["max_quote_age_seconds"])
        # 오래된 호가로 고점을 갱신하면 추적 손절이 잘못 작동할 수 있다.
        quote_is_valid = False
        if quote:
            try:
                age = (now - parse_timestamp(quote["available_at"])).total_seconds()
                bid = require_number(quote["bid"])
                ask = require_number(quote["ask"])
                quote_is_valid = 0 <= age <= maximum_quote_age and bid <= ask
            except (KeyError, TypeError, ValueError, OverflowError):
                return {"action": "WAIT", "reason": "invalid_quote", "market": market,
                        "symbol": symbol, "as_of": prepared["now"], "mode": "paper"}
        previous_quote = self.state.get("quote_reference", {}).get(key)
        safety_observed = quote_is_valid and prepared.get("regular_session_open") is True
        if safety_observed:
            begin_day(self.state, market, now, self.settings)
            self.state.setdefault("quote_times", {})[key] = quote["available_at"]
            self.state.setdefault("quote_reference", {})[key] = {"at": prepared["now"], "mid": (bid + ask) / 2}
        if position and safety_observed:
            position["peak_bid_since_entry"] = max(position["peak_bid_since_entry"], bid)
            self.state.setdefault("last_prices", {})[key] = bid

        safety_metrics = observe_loss(self.state, market, self.settings, self.safety_policy) if safety_observed else {}
        same_market_count = sum(item["market"] == market for item in self.state["positions"].values())
        budget = min(self.state["cash"][market],
                     self.settings["starting_cash"][market] * self.settings["allocation_fraction"])
        prepared["position"] = copy.deepcopy(position)
        if position:
            # 원가에는 매수 비용이 이미 포함됐다. 매도 비용·슬리피지는 따로 반영한다.
            prepared["position"]["sell_proceeds_ratio"] = ((1 - self.settings["slippage_ratio"])
                                                          * (1 - self.settings["sell_cost_ratio"]))
        prepared["risk_budget_available"] = budget > 0 and same_market_count < self.settings["max_positions_per_market"]
        prepared["last_entry_signal_bar"] = self.state["last_entry_signal_bar"].get(key)
        prepared["last_exit_at"] = self.state["last_exit_at"].get(key)
        decision = evaluate(prepared, strategy_config)
        decision["mode"] = "paper"
        decision.setdefault("metrics", {})["safety"] = safety_metrics
        maximum_quantity = math.inf
        if not position and decision['action'] != 'SELL' and prepared.get('universe_entry_allowed') is False:
            decision.update(action='WAIT', reason='universe_no_longer_eligible')
        if decision["action"] == "BUY" and prepared.get("operational_buy_block"):
            decision.update(action="WAIT", reason="operations_buy_halt")
        if decision["action"] == "BUY":
            reason, maximum_quantity, safety_metrics = entry_limits(self.state, prepared, load_config(strategy_config),
                self.settings, self.safety_policy, self.path, previous_quote)
            decision["metrics"]["safety"] = safety_metrics
            if reason:
                legacy_budget_below_share = budget < ask * (1 + self.settings["slippage_ratio"]) * (1 + self.settings["buy_cost_ratio"])
                decision.update(action="WAIT", reason="paper_budget_below_one_share"
                    if reason == "risk_or_exposure_limit" and legacy_budget_below_share else "safety_" + reason)
        self.state["last_processed_at"][key] = prepared["now"]

        trade = None
        if decision["action"] == "BUY" and quote_is_valid and not position:
            price = ask * (1 + self.settings["slippage_ratio"])
            unit_cost = price * (1 + self.settings["buy_cost_ratio"])
            quantity = min(math.floor(budget / unit_cost), maximum_quantity)  # 초기 버전은 양 시장 모두 정수 주식 수량.
            if quantity < 1:
                decision.update(action="WAIT", reason="paper_budget_below_one_share")
            else:
                cost = quantity * unit_cost
                self.state["cash"][market] -= cost
                self.state["positions"][key] = {
                    "market": market, "symbol": symbol, "quantity": quantity,
                    "average_cost": unit_cost, "peak_bid_since_entry": bid,
                    "entry_at": prepared["now"], "cost_basis": cost,
                }
                self.state.setdefault("last_prices", {})[key] = bid
                self.state["last_entry_signal_bar"][key] = prepared["bars"][-1]["end"]
                trade = {"action": "BUY", "quantity": quantity, "price": price,
                         "fees": quantity * price * self.settings["buy_cost_ratio"], "cash_flow": -cost}
        elif decision["action"] == "SELL" and quote_is_valid and position:
            price = bid * (1 - self.settings["slippage_ratio"])
            quantity = position["quantity"]
            fees = quantity * price * self.settings["sell_cost_ratio"]
            proceeds = quantity * price - fees
            self.state["cash"][market] += proceeds
            trade = {"action": "SELL", "quantity": quantity, "price": price, "fees": fees,
                     "cash_flow": proceeds, "realized_pnl": proceeds - position["cost_basis"]}
            del self.state["positions"][key]
            self.state["last_exit_at"][key] = prepared["now"]
        if trade:
            trade.update(market=market, symbol=symbol, at=prepared["now"], reason=decision["reason"])
            trade.update(quote_at=prepared["quote"]["available_at"],
                         reference_price=ask if trade["action"] == "BUY" else bid,
                         input_source=prepared.get("source", "unspecified"),
                         data_mode=prepared.get("data_mode", "unspecified"))
            self.state["trades"].append(trade)
            decision["paper_fill"] = trade
        if safety_observed:
            observe_loss(self.state, market, self.settings, self.safety_policy)
        self.save()
        return decision

    def summary(self) -> dict:
        """KRW와 USD를 합산하지 않고 시장별 평가·실현 손익을 반환한다."""
        summaries = {}
        for market in ("KR", "US"):
            cash = self.state["cash"][market]
            positions = [item for item in self.state["positions"].values() if item["market"] == market]
            marked_value = sum(item["quantity"] * self.state.get("last_prices", {}).get(
                market + ":" + item["symbol"], item["average_cost"]) for item in positions)
            equity = cash + marked_value
            starting = self.settings["starting_cash"][market]
            summaries[market] = {"currency": "KRW" if market == "KR" else "USD", "cash": cash,
                                 "equity_at_last_quote": equity, "pnl_at_last_quote": equity - starting,
                                 "return_at_last_quote": equity / starting - 1,
                                 "position_count": len(positions),
                                 "realized_pnl": sum(t.get("realized_pnl", 0) for t in self.state["trades"] if t["market"] == market)}
        return summaries
