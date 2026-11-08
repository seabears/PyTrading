"""영속 주문 상태 기계. 전송 불명 주문은 재전송하지 않고 증권사 대조를 요구한다."""

import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING

from broker.product_policy import load_product_rules, validate_symbol
from strategy.engine import parse_timestamp
from trading.safety import load_policy
from broker.kis_api.client import KisOrderRejected

ACTIVE = {"INTENT", "SENDING", "UNKNOWN", "ACCEPTED", "PARTIAL", "CANCEL_PENDING"}


def money(value):
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("금액은 유한한 0 이상이어야 합니다.")
    return result


def limit_price(value, side):
    """이번 미국 지정가 경로는 $1 이상·센트 단위만 지원한다. 매수 내림·매도 올림."""
    price = money(value)
    if price < 1 or side not in {"BUY", "SELL"}:
        raise ValueError("미지원 가격 범위·주문 방향")
    return price.quantize(Decimal(".01"), rounding=ROUND_FLOOR if side == "BUY" else ROUND_CEILING)


class OrderManager:
    def __init__(self, path, mode="internal", account_alias="research"):
        if mode not in {"internal", "kis_demo", "live"}:
            raise ValueError("실행 모드 오류")
        path.parent.mkdir(parents=True, exist_ok=True)
        from app.runtime import acquire_run_lock

        self._lock = acquire_run_lock(path.with_suffix(".lock"))
        try:
            self.connection = sqlite3.connect(path, timeout=5)
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)"
            )
            row = self.connection.execute("SELECT body FROM journal WHERE id=1").fetchone()
            self.state = (
                json.loads(row[0])
                if row
                else {
                    "mode": mode,
                    "alias": account_alias,
                    "orders": {},
                    "events": [],
                    "account": None,
                }
            )
            if self.state["mode"] != mode or self.state["alias"] != account_alias:
                self.connection.close()
                raise ValueError("계좌·실행 모드가 다른 상태 파일입니다.")
            self._cancel_verified = {}
            self.ready = False  # 재시작마다 원격 현금·잔고·주문 내역을 다시 확인한다.
            for order in self.state["orders"].values():
                if order.get("cancel_status") == "SENDING":
                    order["cancel_status"] = "UNKNOWN"
                if order["status"] == "SENDING":
                    order["status"] = "UNKNOWN"
            self.policy = load_policy()
            self._save()
        except Exception:
            if hasattr(self, "connection"):
                self.connection.close()
            self._lock.close()
            raise

    def close(self):
        self.connection.close()
        self._lock.close()

    def _save(self):
        try:
            with self.connection:
                self.connection.execute(
                    "INSERT OR REPLACE INTO journal VALUES(1, ?)",
                    (json.dumps(self.state, allow_nan=False),),
                )
        except Exception:
            self.ready = False
            raise

    def record_reconcile_failure(self, reason):
        """신규 주문을 중지하고 민감한 응답 원문 대신 제한된 원인 코드만 저장한다."""
        import re

        self.ready = False
        code = reason if re.fullmatch(r"[a-z_]{1,80}", str(reason)) else "reconciliation_failed"
        self.state["last_reconcile_error"] = {
            "code": code,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def _verified_events(self, events):
        """배치 전체 식별자를 검사한다. 중복·수동 주문은 신규 주문 허가 근거가 아니다."""
        from trading.order_contract import broker_key, validate_identity

        known = {}
        errors = []
        remote = {}
        duplicates = set()
        for order in self.state["orders"].values():
            if order.get("broker_id"):
                key = broker_key(order["broker_id"])
                if key in known:
                    raise ValueError("duplicate_local_identifier")
                known[key] = order
        for event in events:
            key = broker_key(event.get("broker_id"))
            if key in remote:
                duplicates.add(key)
            remote[key] = event
        verified = {}
        for key, event in remote.items():
            if key in duplicates:
                errors.append("duplicate_order_identifier")
                continue
            if key not in known:
                errors.append("untracked_remote_order")
                continue
            try:
                validate_identity(known[key], event, self.state)
                if (
                    type(event["filled"]) is not int
                    or not 0 <= event["filled"] <= known[key]["quantity"]
                ):
                    raise ValueError("fill_quantity_invalid")
                money(event["notional"])
                if event["status"] not in {
                    "ACCEPTED",
                    "PARTIAL",
                    "FILLED",
                    "CANCELLED",
                    "REJECTED",
                }:
                    raise ValueError("remote_status_unknown")
                if event["filled"] < known[key]["filled"]:
                    raise ValueError("stale_cumulative_history")
                verified[key] = (known[key], event)
            except (ValueError, KeyError, TypeError) as error:
                errors.append(str(error))
        return verified, errors

    def verify_cancellations(self, events, *, complete):
        """완전한 조회에서 확인된 원주문에만 30초 유효한 취소 증거를 만든다."""
        self._cancel_verified = {}
        if not complete:
            raise ValueError("history_incomplete")
        verified, errors = self._verified_events(events)
        if "account_or_mode_mismatch" in errors:
            return
        now = datetime.now(timezone.utc).isoformat()
        for order, event in verified.values():
            if event["status"] in {"ACCEPTED", "PARTIAL"} and event["quantity"] > event["filled"]:
                self._cancel_verified[order["id"]] = {
                    "at": now,
                    "remaining": event["quantity"] - event["filled"],
                    "broker_id": event["broker_id"],
                    "filled": event["filled"],
                }

    def can_cancel(self, identifier, *, allow_sending=False):
        """신규 매수 중지와 별개로 계좌·원주문·잔량이 확인된 취소만 허용한다."""
        order = self.state["orders"].get(identifier)
        proof = getattr(self, "_cancel_verified", {}).get(identifier)
        if not order or not proof or not order.get("broker_id") or self.state["mode"] == "live":
            return False
        if order["status"] == "CANCEL_PENDING":
            if not (allow_sending and order.get("cancel_status") == "SENDING"):
                return False
        elif order["status"] not in {"ACCEPTED", "PARTIAL", "UNKNOWN"}:
            return False
        return (
            proof["remaining"] > 0
            and 0
            <= (datetime.now(timezone.utc) - parse_timestamp(proof["at"])).total_seconds()
            <= 30
        )

    def cancellation_quantity(self, identifier):
        """검증된 원격 잔량을 사용해 부분 체결 직후의 과도한 취소 요청을 막는다."""
        if not self.can_cancel(identifier, allow_sending=True):
            raise ValueError("cancel_identity_unverified")
        return self._cancel_verified[identifier]["remaining"]

    def reconcile(self, snapshot, broker_orders, *, complete):
        """전체 주문·계좌를 검사한 뒤 한 번에 저장한다. 중간 체결의 일부 반영을 막는다."""
        import copy

        self.ready = False
        before = copy.deepcopy(self.state)
        self._cancel_verified = {}
        try:
            if not complete:
                raise ValueError("history_incomplete")
            self.verify_cancellations(broker_orders, complete=True)
            verified, errors = self._verified_events(broker_orders)
            if errors:
                raise ValueError(errors[0])
            required = {
                "cash",
                "positions",
                "position_costs",
                "initial",
                "exposure",
                "as_of",
                "daily_loss_ratio",
                "consecutive_losses",
                "last_loss_at",
            }
            if not required <= snapshot.keys():
                raise ValueError("account_snapshot_incomplete")
            import math

            money(snapshot["cash"])
            money(snapshot["exposure"])
            if money(snapshot["initial"]) <= 0 or not math.isfinite(
                float(snapshot["daily_loss_ratio"])
            ):
                raise ValueError("account_risk_invalid")
            if (
                type(snapshot["consecutive_losses"]) is not int
                or snapshot["consecutive_losses"] < 0
            ):
                raise ValueError("account_risk_invalid")
            if any(type(value) is not int or value < 0 for value in snapshot["positions"].values()):
                raise ValueError("position_quantity_invalid")
            found = {order["id"] for order, event in verified.values()}
            for order in self.state["orders"].values():
                if order["status"] in ACTIVE - {"INTENT"} and order["id"] not in found:
                    raise ValueError("remote_order_missing")
            # 전체 계약 검증 후 복사본에 적용하고 한 번만 영속 저장한다.
            self.state = copy.deepcopy(before)
            for old, event in verified.values():
                if event["filled"] < old["filled"]:
                    raise ValueError("stale_cumulative_history")
                self.update(
                    old["id"],
                    **{key: event[key] for key in ("event_id", "filled", "notional", "status")},
                    persist=False,
                    update_account=False
                )
                current = self.state["orders"][old["id"]]
                cancel_id = current.get("cancel_broker_id")
                if cancel_id and current["status"] == "CANCEL_PENDING":
                    from trading.order_contract import broker_key

                    rejected = [
                        item
                        for item in event.get("linked_cancellations", [])
                        if broker_key(item["broker_id"]) == broker_key(cancel_id)
                        and item["status"] == "REJECTED"
                    ]
                    if rejected:
                        current.update(status=event["status"], cancel_status="REJECTED")
            self.state["account"] = copy.deepcopy(snapshot)
            self.state.pop("last_reconcile_error", None)
            if self.state.get("restore_gate"):
                from trading.risk_ledger import RiskLedger, local_day

                RiskLedger(self).validate_snapshot(snapshot)
                proof = self.state["risk_ledger"]["last_evaluation"]
                gate = self.state["restore_gate"]
                if (
                    proof["source_kind"] != "kis_vps"
                    or snapshot.get("remote_history_start", "99999999")
                    > local_day(gate["backup_at"]).replace("-", "")
                    or parse_timestamp(proof["as_of"]) <= parse_timestamp(gate["restored_at"])
                ):
                    raise ValueError("restore_history_not_proven")
                self.state["restore_history"] = gate
                del self.state["restore_gate"]
            self._save()
            self.ready = True
        except Exception as error:
            self.state = before
            self.record_reconcile_failure(str(error))
            raise

    def cancel(self, identifier, adapter):
        """사전 검사 → 의도 저장 → 전송 → 접수 순서로 처리하며 불명 결과는 재전송하지 않는다."""
        from broker.kis_api.client import KisPreflightError

        if not self.can_cancel(identifier):
            raise ValueError("cancel_identity_unverified")
        order = self.state["orders"][identifier]
        previous = order["status"]
        request = dict(order, cancel_quantity=self.cancellation_quantity(identifier))
        try:
            prepare = getattr(adapter, "prepare_cancel", None)
            if callable(prepare):
                prepare(request)
        except Exception:
            self.ready = False
            order["cancel_status"] = "NOT_SENT"
            self._save()
            raise
        order.update(
            status="CANCEL_PENDING",
            cancel_status="SENDING",
            cancel_quantity=request["cancel_quantity"],
            cancel_broker_id=None,
            cancel_attempted_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            self._save()
        except Exception:
            order.update(status=previous, cancel_status="NOT_SENT")
            raise
        try:
            acknowledgement = adapter.cancel(request)
        except KisPreflightError:
            order.update(status=previous, cancel_status="NOT_SENT")
            self._save()
            raise
        except KisOrderRejected:
            order.update(status=previous, cancel_status="REJECTED")
            self._cancel_verified.pop(identifier, None)
            self._save()
            raise
        except Exception:
            order["cancel_status"] = "UNKNOWN"
            self.ready = False
            self._cancel_verified.pop(identifier, None)
            self._save()
            raise
        if isinstance(acknowledgement, str):
            order["cancel_broker_id"] = acknowledgement
        order["cancel_status"] = "ACCEPTED"
        self._cancel_verified.pop(identifier, None)
        self._save()

    def create(self, identifier, symbol, side, quantity, price, stop_price, quote_at):
        """동일 신호 ID 재호출은 기존 의도를 반환한다. 다른 내용이면 오류다."""
        validate_symbol(symbol, load_product_rules())
        if load_product_rules()["verified_instruments"][symbol]["asset_type"] != "stock":
            raise ValueError("이번 자동 주문 범위는 주식뿐입니다.")
        if type(quantity) is not int or quantity < 1:
            raise ValueError("정수 1주 이상만 지원합니다.")
        request = {
            "id": identifier,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": "LIMIT",
            "price": str(limit_price(price, side)),
            "stop_price": str(money(stop_price)),
            "quote_at": quote_at,
        }
        if identifier in self.state["orders"]:
            old = self.state["orders"][identifier]
            if any(old[key] != value for key, value in request.items()):
                raise ValueError("같은 의도 ID의 주문 내용이 다릅니다.")
            return old
        self._risk(request)
        order = {
            **request,
            "status": "INTENT",
            "filled": 0,
            "notional": "0",
            "broker_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.state["orders"][identifier] = order
        self._save()
        return order

    def _risk(self, order):
        if not self.ready:
            if order["side"] == "SELL":
                from trading.execution_observation import validate_reduction
                validate_reduction(self, order)
                return
            raise ValueError("재시작 대조 전 신규 주문 금지")
        if self.state.get("restore_gate"):
            raise ValueError("restored_ledger_requires_remote_reconciliation")
        now = datetime.now(timezone.utc)
        account = self.state["account"]
        if not 0 <= (now - parse_timestamp(account["as_of"])).total_seconds() <= 30:
            raise ValueError("계좌 스냅샷이 오래됐습니다.")
        if not 0 <= (now - parse_timestamp(order["quote_at"])).total_seconds() <= 30:
            raise ValueError("주문 호가가 오래됐습니다.")
        others = [
            item
            for item in self.state["orders"].values()
            if item["id"] != order["id"] and item["status"] in ACTIVE
        ]
        if any(item["status"] in {"UNKNOWN", "SENDING"} for item in others):
            raise ValueError("불명 주문 대조 필요")
        remaining = order["quantity"] - order.get("filled", 0)
        if order["side"] == "SELL":
            from trading.order_contract import broker_key

            remote_ids = set(account.get("broker_reserved_ids", []))
            reserved = sum(
                item["quantity"] - item["filled"]
                for item in others
                if item["side"] == "SELL"
                and item["symbol"] == order["symbol"]
                and (not item.get("broker_id") or broker_key(item["broker_id"]) not in remote_ids)
            )
            if remaining + reserved > account.get("sellable", account["positions"]).get(
                order["symbol"], 0
            ):
                raise ValueError("매도 가능 수량 초과")
            return
        # 매수 한도는 API 주문가능액으로 독립 계산한다. 손익 원장 현금은 사용하지 않는다.
        from trading.buying_power import assess_buying_power
        cost = Decimal(remaining) * money(order["price"]) * Decimal("1.003")
        budget = assess_buying_power(account, self.state["orders"].values(),
                                    current_id=order["id"], order_cost=str(cost))
        if not budget["within_buying_power"]:
            raise ValueError("주문 가능 금액·종목 한도 초과")
        if self.state["mode"] == "kis_demo":
            from trading.cash_service_policy import require_cash_only
            require_cash_only(self)
            from trading.risk_ledger import RiskLedger, local_day

            from trading.cash_service_policy import require_usd_funding
            require_usd_funding(self, order)
            from trading.demo_user_basis import require_execution_basis
            require_execution_basis(self,order=order)
        from pathlib import Path

        if (
            Path(self.connection.execute("PRAGMA database_list").fetchone()[2]).parent
            / "PAUSE_BUYS"
        ).exists():
            raise ValueError("운영자 매수 중지")
        policy = self.policy
        if Decimal(str(account["daily_loss_ratio"])) >= Decimal(str(policy["daily_loss_limit"])):
            raise ValueError("일일 손실 한도")
        if account["consecutive_losses"] >= policy["consecutive_losses"] and (
            not account["last_loss_at"]
            or (now - parse_timestamp(account["last_loss_at"])).total_seconds()
            < policy["loss_cooldown_minutes"] * 60
        ):
            raise ValueError("연속 손실 대기")
        initial = money(account["initial"])
        price, stop = money(order["price"]), money(order["stop_price"])
        if not 0 < stop < price:
            raise ValueError("매수 손절 기준 누락")
        cost = Decimal(remaining) * price * Decimal("1.003")
        reserve = sum(
            Decimal(item["quantity"] - item["filled"]) * money(item["price"]) * Decimal("1.003")
            for item in others
            if item["side"] == "BUY"
        )
        risk = Decimal(order["quantity"]) * (price * Decimal("1.003") - stop * Decimal(".997"))
        if cost > initial * money(policy["maximum_order_fraction"]):
            raise ValueError("주문 가능 금액·종목 한도 초과")
        if cost + reserve + money(account["exposure"]) > initial * money(
            policy["maximum_exposure_fraction"]
        ) or risk > initial * money(policy["maximum_trade_risk"]):
            raise ValueError("총 투자·손실 위험 한도 초과")
        positions = {symbol for symbol, quantity in account["positions"].items() if quantity}
        positions.update(item["symbol"] for item in others if item["side"] == "BUY")
        if len(positions | {order["symbol"]}) > 5:
            raise ValueError("보유 종목 수 초과")
        # 시장 현지 거래일 기준으로 의도 수를 보수적으로 제한한다.
        from zoneinfo import ZoneInfo

        day = now.astimezone(ZoneInfo("America/New_York")).date()
        buys = sum(
            item["side"] == "BUY"
            and item["id"] != order["id"]
            and parse_timestamp(item["created_at"]).astimezone(ZoneInfo("America/New_York")).date()
            == day
            for item in self.state["orders"].values()
        )
        if buys >= policy["maximum_buys_per_day"]:
            raise ValueError("일일 매수 한도")

    def dispatch(self, identifier, adapter):
        order = self.state["orders"][identifier]
        if order["status"] != "INTENT":
            raise ValueError("이미 전송했거나 상태 불명인 주문은 재전송할 수 없습니다.")
        if self.state["mode"] == "live":
            raise ValueError("이번 버전은 실계좌 전송을 허용하지 않습니다.")
        self._risk(order)
        order["status"] = "SENDING"
        self._save()  # 전송 직전 종료도 UNKNOWN으로 복원한다.
        try:
            identifier_on_broker = adapter.submit(dict(order))
            if not isinstance(identifier_on_broker, str) or not identifier_on_broker:
                raise ValueError("접수 번호 누락")
            order["broker_id"] = identifier_on_broker
            order["status"] = "ACCEPTED"
            self._save()
        except KisOrderRejected:
            order["status"] = "REJECTED"
            self._save()
            raise
        except Exception:
            order["status"] = "UNKNOWN"
            self.ready = False
            self._save()
            raise

    def update(
        self, identifier, event_id, filled, notional, status, *, persist=True, update_account=True
    ):
        """증권사 누적 체결을 사용한다. 역순·중복 통보는 이중 체결로 더하지 않는다."""
        order = self.state["orders"][identifier]
        event_key = identifier + ":" + event_id
        if event_key in self.state["events"]:
            return
        if type(filled) is not int or not 0 <= filled <= order["quantity"]:
            self.ready = False
            raise ValueError("체결 수량 불일치")
        if status not in {"ACCEPTED", "PARTIAL", "FILLED", "CANCELLED", "REJECTED"}:
            raise ValueError("미지원 원격 상태")
        if filled < order["filled"]:
            return
        value = money(notional)
        if value < money(order["notional"]) or (
            filled == order["filled"] and value != money(order["notional"])
        ):
            self.ready = False
            raise ValueError("누적 체결 금액 충돌")
        if status == "FILLED" and filled != order["quantity"]:
            raise ValueError("완료 수량 불일치")
        account = self.state["account"]
        delta_quantity, delta_value = filled - order["filled"], value - money(order["notional"])
        if account and delta_quantity and update_account:
            self.ready = False  # 새 현금·체결 비용을 조회한 뒤 다음 주문을 허용한다.
            symbol = order["symbol"]
            old_quantity = account["positions"].get(symbol, 0)
            old_cost = money(account["position_costs"].get(symbol, 0))
            if order["side"] == "BUY":
                account["cash"] = str(money(account["cash"]) - delta_value)
                account["positions"][symbol] = old_quantity + delta_quantity
                account["position_costs"][symbol] = str(old_cost + delta_value)
            else:
                if delta_quantity > old_quantity:
                    self.ready = False
                    raise ValueError("체결 매도가 보유를 초과했습니다.")
                account["cash"] = str(money(account["cash"]) + delta_value)
                account["positions"][symbol] = old_quantity - delta_quantity
                account["position_costs"][symbol] = str(
                    old_cost * Decimal(old_quantity - delta_quantity) / old_quantity
                )
            account["exposure"] = str(
                sum(money(value) for value in account["position_costs"].values())
            )
        if persist and delta_quantity:
            getattr(self, "_cancel_verified", {}).pop(identifier, None)
        order.update(filled=filled, notional=str(value))
        if filled == order["quantity"]:
            order["status"] = "FILLED"
        elif order["status"] == "CANCEL_PENDING" and status in {"ACCEPTED", "PARTIAL"}:
            pass  # 일반 접수·부분 체결 조회만으로 취소 요청의 결과를 확정하지 않는다.
        elif order["status"] not in {"FILLED", "CANCELLED", "REJECTED"}:
            order["status"] = status
        self.state["events"].append(event_key)
        if order["status"] in {"CANCELLED", "FILLED"} and order.get("cancel_status"):
            order["cancel_status"] = (
                "CONFIRMED" if order["status"] == "CANCELLED" else "FILLED_DURING_CANCEL"
            )
        if persist:
            self._save()

    def bind_unknown(self, identifier, broker_id, history):
        """운영자가 완전한 원격 이력에서 식별한 접수 번호만 연결한다. 자동 재주문은 하지 않는다."""
        order = self.state["orders"][identifier]
        from trading.order_contract import validate_identity, broker_key

        candidate = dict(order, broker_id=broker_id)
        matches = []
        for row in history:
            if broker_key(row.get("broker_id")) == broker_key(broker_id):
                validate_identity(candidate, row, self.state)
                matches.append(row)
        if order["status"] != "UNKNOWN" or len(matches) != 1:
            raise ValueError("불명 주문과 원격 이력이 유일하게 일치하지 않습니다.")
        if any(item.get("broker_id") == broker_id for item in self.state["orders"].values()):
            raise ValueError("이미 연결된 원격 주문 번호")
        order["broker_id"] = broker_id
        self._save()
