"""한정 모의 시험의 접수→취소→매수→매도 상태 기계.

Port는 전체 조회·위험 검산·현재 호가를 제공한다. 이 모듈은 직접 HTTP를
보내지 않는다. 의도 ID와 단계는 주문과 같은 SQLite에 저장하며, 재시작은
항상 재조회부터 시작한다. UNKNOWN/SENDING은 자동 재전송하지 않는다.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
import time

from trading.orders import ACTIVE, money
from strategy.engine import parse_timestamp


class LimitedDemoRunner:
    def __init__(self, session, port, *, stop_requested=None):
        self.session = session
        self.manager = session.manager
        self.port = port
        self.stop_requested = stop_requested or (lambda: False)
        self.manager.state.setdefault("demo_workflow", {
            "phase": "NEW", "steps": [], "cancel_probe": "not_started",
            "entry": "not_started", "exit": "not_started", "completed": False,
            "session_id": session.session_id})
        if self.state["session_id"] != session.session_id:
            raise ValueError("workflow_session_mismatch")

    @property
    def state(self):
        return self.manager.state["demo_workflow"]

    def transition(self, phase, reason):
        """전송 전에 전이 의도를 영속화한다. 자유문 서버 오류는 저장하지 않는다."""
        self.state["phase"] = phase
        self.state["steps"].append({"at": datetime.now(timezone.utc).isoformat(),
                                    "phase": phase, "reason": reason})
        self.manager._save()

    def order(self, role):
        return self.manager.state["orders"].get(self.session.session_id + ":" + role)

    def send(self, role, side, price, quote):
        """동일 역할을 두 번 만들거나 전송하지 않는다. 손절은 기존 주문 위험 검사에 전달한다."""
        identifier = self.session.session_id + ":" + role
        if identifier in self.manager.state["orders"]:
            raise ValueError("workflow_intent_already_exists_no_resend")
        if side == "BUY":
            self.session.arm(self.port.recovery())
        else:
            # 비용이 미확정이어도 확인된 시험 보유만 줄인다. 위험 승인은 열지 않는다.
            self.session.prepare_reduction()
        stop = (money(price) * Decimal("0.98")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        self.session.create(identifier, side, self.session.limits["quantity"], price, str(stop), quote["at"])
        self.session.submit(identifier)

    def step(self):
        """한 번의 전체 원격 대조 뒤 최대 한 번의 전송만 수행한다."""
        observation = self.port.refresh()
        phase = self.state["phase"]
        if self.stop_requested():
            self.transition("REVIEW", "operator_stop_cleanup_required")
            return False
        own = self.session._own_orders()
        if any(order["status"] in {"UNKNOWN", "SENDING"} for order in own):
            self.transition("REVIEW", "ambiguous_order_reconcile_without_resend")
            return False
        if phase in {"DONE", "REVIEW"}:
            return False
        net = sum(order["filled"] * (1 if order["side"] == "BUY" else -1) for order in own)
        if net < 0 or net > self.session.limits["maximum_concurrent_shares"]:
            raise ValueError("workflow_trial_position_mismatch")
        if phase == "NEW":
            if own:
                self.transition("REVIEW", "existing_trial_intent_requires_review")
                return False
            if not observation["new_orders_allowed"]:
                self.transition("REVIEW", "account_risk_not_eligible")
                return False
            quote = self.port.quote()
            probe = (money(quote["bid"]) * Decimal("0.98")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            budget = money(self.session.limits["maximum_gross_buy_commitments_usd"])
            # 취소된 주문도 누적 예산에 남는다. 두 번의 매수 여력이 없으면 취소 시험을 생략한다.
            if (probe + money(quote["ask"])) * Decimal("1.003") <= budget and self.session.limits["maximum_buy_attempts"] >= 2:
                self.transition("PROBE_PENDING", "cancel_probe_intent")
                self.send("probe", "BUY", str(probe), quote)
            else:
                self.state["cancel_probe"] = "skipped_cumulative_budget_or_attempt_limit"
                self.transition("ENTRY_PENDING", "single_buy_intent")
                self.send("entry", "BUY", quote["ask"], quote)
            return True
        if phase == "PROBE_PENDING":
            order = self.order("probe")
            if not order:
                self.transition("REVIEW", "probe_intent_absent_no_retry")
                return False
            if net:
                self.state["cancel_probe"] = "filled_before_cancel"
                self.transition("EXIT_READY", "probe_filled_no_additional_buy")
            elif order["status"] in {"CANCELLED", "REJECTED"}:
                self.state["cancel_probe"] = order["status"].lower()
                self.transition("ENTRY_READY", "probe_terminal")
            elif self.manager.can_cancel(order["id"]):
                self.transition("PROBE_CANCELLING", "verified_cancel_request")
                self.session.cancel(order["id"])
            return True
        if phase == "PROBE_CANCELLING":
            order = self.order("probe")
            if net:
                self.state["cancel_probe"] = "filled_during_cancel"
                self.transition("EXIT_READY", "cancel_race_fill_no_additional_buy")
            elif order["status"] == "CANCELLED":
                self.state["cancel_probe"] = "cancelled"
                self.transition("ENTRY_READY", "final_cancel_confirmed")
            elif order.get("cancel_status") in {"REJECTED", "NOT_SENT", "UNKNOWN"}:
                self.transition("REVIEW", "cancel_not_final_requires_review")
                return False
            return True
        if phase == "ENTRY_READY":
            if not observation["new_orders_allowed"]:
                self.transition("REVIEW", "risk_not_requalified_after_cancel")
                return False
            quote = self.port.quote()
            self.transition("ENTRY_PENDING", "entry_intent")
            self.send("entry", "BUY", quote["ask"], quote)
            return True
        if phase == "ENTRY_PENDING":
            order = self.order("entry")
            if not order:
                self.transition("REVIEW", "entry_intent_absent_no_retry")
                return False
            if net:
                self.state["entry"] = "filled"
                self.transition("EXIT_READY", "actual_own_fill_confirmed")
            elif order["status"] in {"REJECTED", "CANCELLED"}:
                self.transition("REVIEW", "entry_not_filled")
                return False
            return True
        if phase == "EXIT_READY":
            if net != self.session.limits["quantity"]:
                self.transition("REVIEW", "trial_holding_not_confirmed")
                return False
            quote = self.port.quote()
            self.transition("EXIT_PENDING", "reduce_trial_position_only")
            self.send("exit", "SELL", quote["bid"], quote)
            return True
        if phase == "EXIT_PENDING":
            order = self.order("exit")
            if order and order["status"] == "FILLED" and net == 0:
                self.state["exit"] = "filled"
                accounting = observation.get("posttrade", {})
                self.state["completed"] = (observation.get("settlement_complete") is True
                    and accounting.get("phase") == "RECONCILED"
                    and accounting.get("actual_cash_delta_usd") is not None
                    and accounting.get("cash_delta_matches") is True)
                self.transition("DONE" if self.state["completed"] else "REVIEW",
                                "round_trip_and_settlement_confirmed" if self.state["completed"] else
                                "flat_but_cash_reconciliation_pending" if observation.get("settlement_complete") else "flat_but_final_costs_pending")
                return False
            return True
        raise ValueError("workflow_phase_unknown")

    def run(self):
        """시간·조회 횟수를 제한하고 종료 전에 원격 최종 상태를 다시 확인한다."""
        deadline = time.monotonic() + self.session.limits.get("maximum_active_minutes", 10) * 60
        if hasattr(self.port, "set_deadline"):
            self.port.set_deadline(deadline, self.stop_requested)
        try:
            for _ in range(self.session.limits["maximum_poll_count"]):
                if time.monotonic() >= deadline:
                    self.transition("REVIEW", "activation_wall_clock_limit_reached")
                    break
                if not self.step():
                    break
                self.port.wait(self.session.limits["poll_seconds"])
            else:
                self.transition("REVIEW", "bounded_poll_limit_reached")
        except Exception:
            # 전송 유실을 포함해 자동 재주문하지 않는다. 원문 예외는 로그에 저장하지 않는다.
            self.transition("REVIEW", "execution_failed_reconcile_required")
        finally:
            self.session.disarm()
            self.cleanup()
        return dict(self.state)

    def cleanup(self):
        """조회로 확인한 자기 미체결만 한 번 취소한다. 최종 확인 실패를 성공으로 쓰지 않는다."""
        self.state["final_remote_verified"] = False
        if hasattr(self.port, "set_deadline"):
            self.port.set_deadline(time.monotonic() + 120, lambda: False)
        try:
            self.port.refresh()
            for order in self.session._own_orders():
                if order["status"] in ACTIVE and not order.get("session_cancel_attempted") and self.manager.can_cancel(order["id"]):
                    self.session.cancel(order["id"])
                    self.port.refresh()
            self.state["final_remote_verified"] = True
            summary = self.session.summary()
            self.state["remaining_open_orders"] = summary["local_active_orders"]
            self.state["remaining_shares"] = summary["local_net_filled_shares"]
            if summary["local_active_orders"] or summary["local_net_filled_shares"]:
                self.state["completed"] = False
                self.state["phase"] = "REVIEW"
        except Exception:
            self.state["completed"] = False
            self.state["phase"] = "REVIEW"
        finally:
            self.session.disarm()
            self.manager._save()
