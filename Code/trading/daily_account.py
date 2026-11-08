"""고정 일봉 후보의 내부 모의 계좌. 확정 종가 신호와 이후 실제 관측 체결을 구분한다."""

import copy
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone

from broker.sessions import calendar_for, regular_session
from research.algorithm_study import make_features, signal
from strategy.engine import parse_timestamp, require_number
from trading.paper import PaperAccount
from trading.safety import begin_day, observe_loss, entry_limits


def session_after(day):
    calendar = calendar_for("US", int(day[:4]))
    schedule = calendar.schedule.loc[day:]
    return next(
        label.date().isoformat() for label in schedule.index if label.date().isoformat() > day
    )


def last_closed_day(now):
    schedule = calendar_for("US", now.year).schedule
    eligible = schedule[schedule["close"] <= now - timedelta(minutes=2)]
    return eligible.index[-1].date().isoformat()


class DailyAccount(PaperAccount):
    """전일 계획·현금·가상 체결을 한 파일에 함께 저장해 재시작 중복을 막는다."""

    def __init__(self, path, settings, candidate, *, process_started_at=None, maximum_trade_risk=0.0025):
        # 실행 시작은 저장 상태에서 복원하지 않는다. 재시작은 새 시작 시각으로 판단한다.
        from trading.daily_risk import validate_fraction, FROZEN_TRADE_RISK
        maximum_trade_risk = validate_fraction(maximum_trade_risk)
        super().__init__(path, settings, safety_policy={"maximum_trade_risk": maximum_trade_risk})
        self.internal_daily_risk_override = maximum_trade_risk != FROZEN_TRADE_RISK
        fingerprint = hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()
        if self.state.get("daily_candidate_hash", fingerprint) != fingerprint:
            raise ValueError("기존 일봉 계좌의 고정 후보와 다릅니다.")
        if path.exists() and "daily_candidate_hash" not in self.state:
            raise ValueError("다른 전략 계좌를 일봉 계좌로 사용할 수 없습니다.")
        self.state.setdefault("daily_candidate_hash", fingerprint)
        self.state.setdefault("pending_daily", [])
        self.state.setdefault("last_signal_day", None)
        self.state.setdefault("daily_reference_closes", {})
        self.candidate = candidate
        history = self.state.setdefault('daily_trade_risk_history', [])
        if not history or history[-1]['fraction'] != maximum_trade_risk:
            history.append({'at':datetime.now(timezone.utc).isoformat(),'fraction':maximum_trade_risk,
                            'scope':'internal_paper_override' if self.internal_daily_risk_override else 'frozen_default'})
        self.process_started_at = process_started_at or datetime.now(timezone.utc)
        if self.process_started_at.tzinfo is None or self.process_started_at.utcoffset() is None:
            raise ValueError("실행 시작 시각에는 시간대가 필요합니다.")

    def entry_timing(self, now):
        """초 단위 진입 창. 개장 300초 뒤 시작한 실행만 같은 정규장 끝까지 예외다.

        일봉 수집이 늦었다는 이유로 시작 시각을 갱신하지 않는다. 이전 거래일의
        늦은 시작도 다음 거래일로 이월하지 않으며 조기 종료는 거래소 달력을 따른다.
        이 정책은 신호가 있는 당일 계획에만 쓰며 가격·위험 검사를 대체하지 않는다.
        """
        session = regular_session("US", now)
        late_start = bool(
            session
            and session["start"] + timedelta(seconds=300) < self.process_started_at
            and self.process_started_at <= now < session["end"]
        )
        return {
            "policy": "open_300s_or_late_process_start_v1",
            "process_started_at": self.process_started_at.isoformat(),
            "session_id": session["id"] if session else None,
            "late_start_exception": late_start,
            "entry_window_open": bool(session and (
                (now - session["start"]).total_seconds() <= 300 or late_start
            )),
        }

    def plan_closed(self, series, proxy, now):
        """완료된 전 거래일 자료만 받는다. 누락 시 새 계획을 만들지 않고 보유 가격 관리는 계속한다."""
        required = last_closed_day(now)
        if self.state["last_signal_day"] == required:
            return False
        if (
            not proxy
            or proxy[-1]["date"] != required
            or any(not bars or bars[-1]["date"] != required for bars in series.values())
        ):
            raise ValueError("완료 거래일 자료가 누락되어 일봉 계획을 보류합니다.")
        before = copy.deepcopy(self.state)
        try:
            proxy_feature = make_features(proxy)[-1]
            market_up = (
                proxy_feature["ma200"] is not None
                and proxy_feature["close"] > proxy_feature["ma200"]
            )
            plans, entries = [], []
            execution_day = session_after(required)
            for key, bars in series.items():
                feature = make_features(bars)[-1]
                detail = signal(feature, self.candidate["family"], self.candidate["strategy"])
                position = self.state["positions"].get(key)
                if position:
                    # 보유 고점은 완료된 일봉에서만 갱신한다. 갱신된 보호선은 다음 정규장부터 적용된다.
                    position["daily_peak"] = max(position["daily_peak"], bars[-1]["high"])
                    position["daily_stop"] = max(
                        position["daily_stop"],
                        position["daily_peak"]
                        - self.candidate["risk"]["trailing_atr"] * feature["atr"],
                    )
                    days = calendar_for("US", now.year).schedule.loc[
                        position["entry_day"] : required
                    ]
                    if detail["exit"] or len(days) >= self.candidate["strategy"]["holding_days"]:
                        plans.append(
                            {
                                "id": required + ":SELL:" + key,
                                "symbol": key,
                                "side": "SELL",
                                "execution_day": execution_day,
                                "signal_day": required,
                            }
                        )
                elif detail["enter"] and (not self.candidate["market_filter"] or market_up):
                    entries.append(
                        {
                            "id": required + ":BUY:" + key,
                            "symbol": key,
                            "side": "BUY",
                            "execution_day": execution_day,
                            "signal_day": required,
                            "close": feature["close"],
                            "atr": feature["atr"],
                            "score": detail["score"],
                        }
                    )
            entries.sort(key=lambda item: (-item["score"], item["symbol"]))
            # 누락으로 집행하지 못한 이전 매도 계획은 다음 날에도 유지한다.
            present_exits = {item["symbol"] for item in plans}
            plans += [
                item
                for item in self.state["pending_daily"]
                if item["side"] == "SELL"
                and item["symbol"] in self.state["positions"]
                and item["symbol"] not in present_exits
            ]
            self.state["pending_daily"] = plans + entries
            self.state["daily_reference_closes"] = {
                key: bars[-1]["close"] for key, bars in series.items()
            }
            self.state["last_signal_day"] = required
            self.state["last_signal_observed_at"] = now.isoformat()
            self.save()
            return True
        except Exception:
            self.state = before
            raise

    def observe_quote(self, snapshot):
        """신선한 현재 호가만 쓴다. 늦게 시작한 실행의 당일 진입 예외도 소급 체결하지 않는다."""
        before = copy.deepcopy(self.state)
        try:
            result = self._observe_quote(snapshot)
            self.save()
            return result
        except Exception:
            self.state = before
            raise

    def plan_additional_closed(self, series, proxy, now):
        """장전 자동 목록이 늦게 준비되면 새 종목 신호만 추가한다. 기존 계획·체결은 재생성하지 않는다.

        장중 최초 선정은 관찰만 시작하고 다음 신호 날짜를 기다린다. 기존 종목의
        소비·취소된 매수 계획이나 보유 보호선을 다시 만들지 않는다.
        """
        required = last_closed_day(now)
        if self.state['last_signal_day'] != required:
            return []
        execution_day = session_after(required)
        schedule = calendar_for('US',now.year).schedule.loc[execution_day:execution_day]
        if now >= schedule.iloc[0]['open'].to_pydatetime():
            return []
        if not proxy or proxy[-1]['date'] != required or any(not bars or bars[-1]['date'] != required for bars in series.values()):
            raise ValueError('additional_daily_data_missing')
        before = copy.deepcopy(self.state)
        added = []
        try:
            known = set(self.state.get('daily_reference_closes',{}))
            proxy_feature = make_features(proxy)[-1]
            market_up = proxy_feature['ma200'] is not None and proxy_feature['close'] > proxy_feature['ma200']
            for key,bars in series.items():
                if key in known or key in self.state['positions']:
                    continue
                feature = make_features(bars)[-1]
                detail = signal(feature,self.candidate['family'],self.candidate['strategy'])
                self.state['daily_reference_closes'][key] = feature['close']
                if detail['enter'] and (not self.candidate['market_filter'] or market_up):
                    plan = {'id':required+':BUY:'+key,'symbol':key,'side':'BUY','execution_day':execution_day,
                            'signal_day':required,'close':feature['close'],'atr':feature['atr'],'score':detail['score']}
                    self.state['pending_daily'].append(plan);added.append(plan['id'])
            sells = [row for row in self.state['pending_daily'] if row['side']=='SELL']
            buys = sorted((row for row in self.state['pending_daily'] if row['side']=='BUY'),key=lambda row:(-row.get('score',0),row['symbol']))
            self.state['pending_daily'] = sells+buys
            self.save()
            return added
        except Exception:
            self.state = before
            raise

    def _observe_quote(self, snapshot):
        now = parse_timestamp(snapshot["now"])
        key = "US:" + snapshot["symbol"]
        session = regular_session("US", now)
        if not session:
            return {"action": "WAIT", "reason": "outside_regular_session"}
        day = session["id"].split(":", 1)[1]
        quote = snapshot.get("quote")
        if (
            not quote
            or not 0 <= (now - parse_timestamp(quote["available_at"])).total_seconds() <= 30
        ):
            return {"action": "WAIT", "reason": "stale_quote"}
        if self.state["last_processed_at"].get(key, "") >= snapshot["now"]:
            return {"action": "WAIT", "reason": "duplicate_observation"}
        bid, ask = require_number(quote["bid"]), require_number(quote["ask"])
        if bid > ask:
            raise ValueError("교차 호가")
        begin_day(self.state, "US", now, self.settings)
        self.state.setdefault("last_prices", {})[key] = bid
        self.state.setdefault("quote_times", {})[key] = quote["available_at"]
        observe_loss(self.state, "US", self.settings, self.safety_policy)
        self.state["last_processed_at"][key] = snapshot["now"]
        position = self.state["positions"].get(key)
        plans = [
            item
            for item in self.state["pending_daily"]
            if item["symbol"] == key and item["execution_day"] <= day
        ]
        exit_plan = next((item for item in plans if item["side"] == "SELL"), None)
        if position and (bid <= position["daily_stop"] or exit_plan):
            result = self._fill(
                key,
                "SELL",
                position["quantity"],
                bid,
                snapshot,
                "daily_stop" if not exit_plan else "daily_signal_exit",
            )
            result["daily_plan_id"] = exit_plan["id"] if exit_plan else None
            self.state["last_exit_at"][key] = snapshot["now"]
        elif position:
            return {"action": "HOLD", "reason": "daily_holding"}
        else:
            plan = next((item for item in plans if item["side"] == "BUY"), None)
            if snapshot.get('universe_entry_allowed') is False:
                # 선정 제외는 신규 매수 계획만 무효화한다. 위의 보유 손절·매도 경로는 그대로다.
                self.state['pending_daily'] = [item for item in self.state['pending_daily']
                    if not (item['symbol'] == key and item['side'] == 'BUY')]
                return {'action':'WAIT', 'reason':'universe_no_longer_eligible'}
            if not plan:
                return {"action": "WAIT", "reason": "no_daily_plan"}
            reason = None
            timing = self.entry_timing(now)
            if day != plan["execution_day"] or not timing["entry_window_open"]:
                reason = "missed_open_window"
            elif snapshot.get("operational_buy_block"):
                return {"action": "WAIT", "reason": "operations_buy_halt"}
            elif abs(ask / plan["close"] - 1) > 0.20:
                self.state.setdefault("corporate_action_suspicions", {})[key] = {
                    "at": snapshot["now"],
                    "previous_close": plan["close"],
                    "ask": ask,
                    "quantity_adjusted": False,
                }
                reason = "corporate_action_or_price_mismatch"
            elif abs(ask / plan["close"] - 1) > 0.03:
                reason = "entry_gap_cancelled"
            elif (ask - bid) / ((ask + bid) / 2) > 0.003:
                return {"action": "WAIT", "reason": "wide_spread"}
            last_exit = self.state["last_exit_at"].get(key)
            if last_exit:
                exit_day = (
                    parse_timestamp(last_exit)
                    .astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
                    .date()
                    .isoformat()
                )
                if len(calendar_for("US", now.year).schedule.loc[exit_day:day]) - 1 <= 3:
                    reason = "daily_cooldown"
            if reason:
                self.state["pending_daily"] = [
                    item for item in self.state["pending_daily"] if item["id"] != plan["id"]
                ]
                return {"action": "WAIT", "reason": reason, "entry_timing": timing}
            distance = plan["atr"] * self.candidate["risk"]["stop_atr"]
            unit_cost = (
                ask * (1 + self.settings["slippage_ratio"]) * (1 + self.settings["buy_cost_ratio"])
            )
            risk_strategy = {
                "stop_loss": min(0.99, (unit_cost - max(0.01, ask - distance)) / unit_cost)
            }
            safety_reason, quantity_cap, _ = entry_limits(
                self.state,
                snapshot,
                risk_strategy,
                self.settings,
                self.safety_policy,
                self.path,
                None,
            )
            maximum = self.settings["max_positions_per_market"]
            if safety_reason or len(self.state["positions"]) >= maximum:
                return {"action": "WAIT", "reason": "safety_" + (safety_reason or "positions_full")}
            quantity = min(
                math.floor(
                    min(
                        self.state["cash"]["US"],
                        self.settings["starting_cash"]["US"] * self.settings["allocation_fraction"],
                    )
                    / unit_cost
                ),
                math.floor(self.settings["starting_cash"]["US"] * self.safety_policy["maximum_trade_risk"] / distance),
                quantity_cap,
            )
            if quantity < 1:
                return {"action": "WAIT", "reason": "budget_below_one_share"}
            result = self._fill(key, "BUY", quantity, ask, snapshot, "frozen_daily_entry")
            result["daily_plan_id"] = plan["id"]
            result["entry_timing"] = timing
            result["paper_fill"]["entry_timing"] = timing
            position = self.state["positions"][key]
            position.update(
                daily_stop=max(0.01, ask - distance),
                daily_peak=ask,
                entry_day=day,
                signal_day=plan["signal_day"],
                observed_execution_at=snapshot["now"],
            )
        self.state["pending_daily"] = [
            item for item in self.state["pending_daily"] if item["symbol"] != key
        ]
        observe_loss(self.state, "US", self.settings, self.safety_policy)
        return result

    def _fill(self, key, side, quantity, reference, snapshot, reason):
        price = reference * (1 + self.settings["slippage_ratio"] * (1 if side == "BUY" else -1))
        fee = (
            quantity
            * price
            * self.settings["buy_cost_ratio" if side == "BUY" else "sell_cost_ratio"]
        )
        cash_flow = -(quantity * price + fee) if side == "BUY" else quantity * price - fee
        trade = {
            "market": "US",
            "symbol": key.split(":", 1)[1],
            "action": side,
            "quantity": quantity,
            "price": price,
            "fees": fee,
            "cash_flow": cash_flow,
            "at": snapshot["now"],
            "reason": reason,
            "quote_at": snapshot["quote"]["available_at"],
            "reference_price": reference,
            "mode": "internal_paper",
            "input_source": snapshot.get("source", "synthetic_or_unspecified"),
            "data_mode": snapshot.get("data_mode", "synthetic_or_unspecified"),
        }
        if side == "BUY":
            self.state["positions"][key] = {
                "market": "US",
                "symbol": trade["symbol"],
                "quantity": quantity,
                "average_cost": -cash_flow / quantity,
                "cost_basis": -cash_flow,
                "peak_bid_since_entry": reference,
                "entry_at": snapshot["now"],
            }
        else:
            position = self.state["positions"].pop(key)
            trade["realized_pnl"] = cash_flow - position["cost_basis"]
        self.state["cash"]["US"] += cash_flow
        self.state["trades"].append(trade)
        return {"action": side, "reason": reason, "paper_fill": trade}
