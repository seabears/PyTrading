"""별도 KIS 모의 시험의 추가 한도. 기존 주문/위험 검사를 대체하지 않는다.

기본 비활성이다. arm은 검증된 정규장 관측과 실제 RiskLedger 근거를 요구한다.
설정 파일이나 전역 서비스의 주문 허용 상태를 바꾸지 않는다.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from broker.sessions import regular_session
from strategy.engine import parse_timestamp
from trading.orders import ACTIVE, money
from trading.risk_ledger import RiskLedger
from trading.demo_profile import load_demo_profile
from trading.demo_accounting_cycle import prepare_pretrade


class LimitedDemoSession:
    """1종목·1주·누적 매수500USD·전송시도2회. 범위를 벗어나면 전송 전 차단한다."""

    def __init__(self, manager, adapter, session_id, symbol=None, profile=None):
        self.manager = manager
        self.adapter = adapter
        self.session_id = session_id
        self.limits = load_demo_profile(profile)
        self.symbol = self.limits["symbol"]
        if symbol is not None and symbol != self.symbol:
            raise ValueError("demo_profile_symbol_mismatch")
        symbol = self.symbol
        self.armed = False
        self.expires_at = None
        self.disarm()
        if manager.state["mode"] != "kis_demo" or adapter.api.market_client.environment != "vps":
            raise ValueError("demo_session_vps_required")
        if manager.state.get("replay_only"):
            raise ValueError("demo_session_replay_blocked")
        saved = manager.state.get("limited_demo_session")
        if saved is None:
            saved = {"id": session_id, "symbol": symbol, "buy_attempts": 0,
                     "cancel_attempts": 0, "sell_attempts": 0, "buy_commitments": {},
                     "order_ids": [], "contracts": {}, "state": "DISARMED"}
            manager.state["limited_demo_session"] = saved
        if saved["id"] != session_id or saved["symbol"] != symbol:
            raise ValueError("demo_session_store_scope_mismatch")
        if saved.get("limits_hash", self.limits["limits_hash"]) != self.limits["limits_hash"]:
            raise ValueError("demo_profile_changed_for_existing_session")
        self.state["limits_hash"] = self.limits["limits_hash"]
        self.state["state"] = "DISARMED"
        manager._save()

    @property
    def state(self):
        # reconcile는 manager.state를 복사본으로 교체한다. 과거 사전 참조를 재사용하지 않는다.
        return self.manager.state["limited_demo_session"]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.disarm()

    def arm(self, recovery, now=None):
        """확인 직후의 실제 관측과 계좌 위험 근거를 검사한 후 메모리에서만 활성화한다."""
        self.disarm()
        now = now or datetime.now(timezone.utc)
        session = regular_session("US", now)
        if not session or recovery.get("regular_recovery_verified") is not True:
            raise ValueError("demo_session_regular_recovery_required")
        if recovery.get("input_kind") != "live_observation" or not recovery.get("per_symbol"):
            raise ValueError("demo_session_observation_source_required")
        if not all(row.get("continuous") is True for row in recovery["per_symbol"].values()):
            raise ValueError("demo_session_all_symbols_required")
        if recovery.get("diagnostics") or not 0 <= (now - parse_timestamp(recovery["checked_at"])).total_seconds() <= 30:
            raise ValueError("demo_session_recovery_stale_or_incomplete")
        if not self.manager.ready:
            raise ValueError("demo_session_reconciliation_required")
        from trading.cash_service_policy import require_cash_only
        require_cash_only(self.manager)
        ledger = RiskLedger(self.manager)
        ledger.validate_snapshot(self.manager.state["account"])
        proof = ledger.context(now)
        from trading.demo_user_basis import require_execution_basis
        require_execution_basis(self.manager,now)
        if not proof.eligible:
            raise ValueError("demo_session_actual_risk_required")
        if any(order["status"] in ACTIVE for order in self.manager.state["orders"].values()):
            raise ValueError("demo_session_existing_active_orders_require_review")
        prior_expiry = self.state.get("expires_at")
        self.expires_at = (parse_timestamp(prior_expiry) if prior_expiry else
                           min(now + timedelta(minutes=self.limits["maximum_active_minutes"]), session["end"] - timedelta(seconds=60)))
        if self.expires_at <= now:
            raise ValueError("demo_session_insufficient_cleanup_time")
        self.state["risk_checkpoint"] = proof.checkpoint_hash
        self.state["last_armed_at"] = now.isoformat()
        self.state["expires_at"] = self.expires_at.isoformat()
        self.manager._save()
        # 파일에는 활성화를 저장하지 않는다. 재시작은 항상 차단 상태다.
        self.armed = True
        self.adapter.enabled = True
        self.adapter.api.allow_trading = True

    def prepare_reduction(self):
        """최초 허용 시간 안의 자기 체결 정리만 연다. 신규 매수 위험 승인을 만들지 않는다."""
        self.disarm()
        expiry = self.state.get("expires_at")
        now = datetime.now(timezone.utc)
        if (not expiry or now >= parse_timestamp(expiry) or not regular_session("US", now)
                or self.manager.state["mode"] != "kis_demo" or self.manager.state.get("replay_only")
                or self.adapter.api.market_client.environment != "vps"):
            raise ValueError("demo_reduction_scope_expired_or_invalid")
        own = self._own_orders()
        net = sum(order["filled"] * (1 if order["side"] == "BUY" else -1) for order in own)
        if not 0 < net <= self.limits["maximum_concurrent_shares"]:
            raise ValueError("demo_reduction_requires_own_fills")
        self.expires_at = parse_timestamp(expiry)
        self._reduction_only = True
        self.armed = True
        self.adapter.enabled = True
        self.adapter.api.allow_trading = True

    def disarm(self):
        """예외나 저장 실패가 있어도 메모리의 전송 허가부터 닫는다."""
        self.armed = False
        self._reduction_only = False
        self.adapter.enabled = False
        self.adapter.api.allow_trading = False

    def _guard(self):
        now = datetime.now(timezone.utc)
        if (not self.armed or not self.expires_at or now >= self.expires_at
                or not regular_session("US", now)):
            self.disarm()
            raise ValueError("demo_session_not_armed_or_expired")
        if self.manager.state["mode"] != "kis_demo" or self.adapter.api.market_client.environment != "vps":
            self.disarm()
            raise ValueError("demo_session_environment_changed")

    def _own_orders(self):
        return [self.manager.state["orders"][identifier] for identifier in self.state["order_ids"]]

    def create(self, identifier, side, quantity, price, stop_price, quote_at):
        """시험용 의도를 만든다. 가격 반올림·계좌 전체 위험 한도는 기존 관리자가 재검사한다."""
        self._guard()
        if self._reduction_only and side != "SELL":
            raise ValueError("demo_reduction_never_authorizes_buy")
        if side not in {"BUY", "SELL"} or type(quantity) is not int or quantity != self.limits["quantity"]:
            raise ValueError("demo_session_one_share_limit_only")
        if identifier in self.manager.state["orders"]:
            raise ValueError("demo_session_duplicate_intent_requires_review")
        own = self._own_orders()
        if any(order["status"] in {"SENDING", "UNKNOWN", "CANCEL_PENDING"} for order in own):
            raise ValueError("demo_session_unresolved_order")
        net = sum(order["filled"] * (1 if order["side"] == "BUY" else -1) for order in own)
        if side == "BUY":
            reserved = sum(order["quantity"] - order["filled"] for order in own
                           if order["side"] == "BUY" and order["status"] in ACTIVE)
            if net + reserved + quantity > self.limits["maximum_concurrent_shares"]:
                raise ValueError("demo_session_concurrent_share_limit")
            # 취소 후에도 이번 시험의 누적 매수 예산을 되돌리지 않는 보수적 한도다.
            committed = sum((money(value) for value in self.state["buy_commitments"].values()), Decimal(0))
            # 기존 OrderManager와 같은 0.3% 예약 완충을 한도 안에 포함한다.
            # 실제 수수료가 이 값으로 확정됐다고 기록하거나 위험 근거로 사용하지 않는다.
            if committed + money(price) * quantity * Decimal("1.003") > money(self.limits["maximum_gross_buy_commitments_usd"]):
                raise ValueError("demo_session_500_usd_limit")
            if self.state["buy_attempts"] >= self.limits["maximum_buy_attempts"]:
                raise ValueError("demo_session_buy_attempt_limit")
        else:
            reserved_sell = sum(order["quantity"] - order["filled"] for order in own
                                if order["side"] == "SELL" and order["status"] in ACTIVE)
            if quantity + reserved_sell > net:
                raise ValueError("demo_session_only_own_fills_may_be_sold")
        try:
            order = self.manager.create(identifier, self.symbol, side, quantity, price, stop_price, quote_at)
        except Exception:
            self.disarm()
            raise
        self.state["order_ids"].append(identifier)
        self.state["contracts"][identifier] = {
            key: order[key] for key in ("symbol", "side", "quantity", "price", "order_type")}
        if side == "BUY":
            self.state["buy_commitments"][identifier] = str(money(price) * quantity * Decimal("1.003"))
        try:
            self.manager._save()
        except Exception:
            self.disarm()
            raise
        return order

    def submit(self, identifier):
        """전송 시도 횟수를 먼저 영속 저장한다. 실패·응답 유실 때 같은 의도를 재전송하지 않는다."""
        self._guard()
        if identifier not in self.state["order_ids"]:
            raise ValueError("demo_session_foreign_order")
        order = self.manager.state["orders"][identifier]
        if self._reduction_only and order["side"] != "SELL":
            raise ValueError("demo_reduction_never_authorizes_buy")
        if any(order.get(key) != value for key, value in self.state["contracts"][identifier].items()):
            self.disarm()
            raise ValueError("demo_session_intent_contract_changed")
        if order["status"] != "INTENT" or order.get("session_transmission_attempted"):
            raise ValueError("demo_session_never_resend")
        key = "buy_attempts" if order["side"] == "BUY" else "sell_attempts"
        maximum = self.limits["maximum_buy_attempts" if key == "buy_attempts" else "maximum_sell_attempts"]
        if self.state[key] >= maximum:
            raise ValueError("demo_session_attempt_limit")
        if order["side"] == "BUY":
            try:
                # 미래 비용 자료를 요구하지 않고 현재 위험 근거·잔액·예약을 저장한다.
                prepare_pretrade(self.manager, identifier, self.limits)
            except Exception:
                self.disarm()
                raise
        order["session_transmission_attempted"] = True
        self.state[key] += 1
        try:
            self.manager._save()
            return self.manager.dispatch(identifier, self.adapter)
        except Exception:
            self.disarm()
            raise

    def cancel(self, identifier):
        """취소도 계좌/원주문/잔량 증거를 요구한다. 접수 불명 취소를 재전송하지 않는다."""
        now = datetime.now(timezone.utc)
        expiry = self.state.get("expires_at")
        if (not expiry or now > parse_timestamp(expiry) + timedelta(minutes=2)
                or not regular_session("US", now)
                or self.manager.state["mode"] != "kis_demo"
                or self.adapter.api.market_client.environment != "vps"
                or self.manager.state.get("replay_only")):
            raise ValueError("demo_session_cleanup_scope_expired")
        if identifier not in self.state["order_ids"] or self.state["cancel_attempts"] >= self.limits["maximum_cancel_attempts"]:
            raise ValueError("demo_session_cancel_scope_or_limit")
        order = self.manager.state["orders"][identifier]
        if order.get("session_cancel_attempted"):
            raise ValueError("demo_session_cancel_never_resend")
        if not self.manager.can_cancel(identifier):
            raise ValueError("demo_session_cancel_identity_unverified")
        order["session_cancel_attempted"] = True
        self.state["cancel_attempts"] += 1
        try:
            self.manager._save()
            # 신규 매수가 중지돼도 확인된 자기 주문 취소에만 일시적으로 전송을 허용한다.
            self.adapter.enabled = True
            self.adapter.api.allow_trading = True
            return self.manager.cancel(identifier, self.adapter)
        finally:
            self.disarm()

    def summary(self):
        """로컬 상태다. 원격 최종 확인과 동일하다고 표시하지 않는다."""
        own = self._own_orders()
        return {"armed": self.armed, "buy_attempts": self.state["buy_attempts"],
                "sell_attempts": self.state["sell_attempts"], "cancel_attempts": self.state["cancel_attempts"],
                "local_active_orders": sum(order["status"] in ACTIVE for order in own),
                "local_net_filled_shares": sum(order["filled"] * (1 if order["side"] == "BUY" else -1) for order in own),
                "remote_final_state_verified": False}
