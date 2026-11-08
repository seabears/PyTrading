"""주문과 같은 SQLite 체크포인트에 보존하는 근거 기반 USD 위험 원장.

금액은 Decimal 소수 6자리, HALF_EVEN으로 계산한다. 외부 보고 금액은 센트로
표시하지만 집계 도중 센트 반올림을 반복하지 않는다. 기존 보유의 원가·과거
손실을 추측하지 않는다. 완전한 전방 기록이 없는 계좌는 매수 자격을 얻지 못한다.
"""

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from zoneinfo import ZoneInfo

from strategy.engine import parse_timestamp

PRECISION = Decimal("0.000001")
TOLERANCE = Decimal("0.01")


def amount(value, signed=False):
    """USD 금액은 6자리 고정 소수로 처리한다. NaN·무한대·부동소수 입력은 거절한다."""
    if isinstance(value, (float, bool)):
        raise ValueError("decimal_string_required")
    number = Decimal(str(value))
    if not number.is_finite() or (not signed and number < 0):
        raise ValueError("invalid_money")
    return number.quantize(PRECISION, rounding=ROUND_HALF_EVEN)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def local_day(stamp):
    return parse_timestamp(stamp).astimezone(ZoneInfo("America/New_York")).date().isoformat()


@dataclass(frozen=True)
class RiskProof:
    account_fingerprint: str
    checkpoint_hash: str
    as_of: str
    initial: str
    daily_loss_ratio: str
    consecutive_losses: int
    last_loss_at: str | None
    eligible: bool
    positions: dict
    position_costs: dict
    buying_power: str
    exposure: str

    def values(self):
        return dict(
            initial=self.initial,
            daily_loss_ratio=self.daily_loss_ratio,
            consecutive_losses=self.consecutive_losses,
            last_loss_at=self.last_loss_at,
        )


class RiskLedger:
    """입력 검산 → 기존 사건과 병합 → 전량 재계산 → 한 번 저장 순서로 처리한다."""

    def __init__(self, manager):
        self.manager = manager

    def _identity(self):
        identity = self.manager.state.get("broker_identity")
        if self.manager.state["mode"] != "kis_demo" or not identity:
            raise ValueError("risk_account_unbound")
        return identity

    def ingest(self, evidence, now=None):
        """완전성·시각·관리 주문·자금 수지를 검산한다. 실패 근거도 영속 중지로 남긴다."""
        now = now or datetime.now(timezone.utc)
        self.manager.ready = False
        before = copy.deepcopy(self.manager.state)
        if self.manager.state.get("risk_ledger",{}).get("last_evaluation",{}).get("source_kind") in {"user_designated_demo_trial","user_designated_strategy_demo"}:
            raise ValueError("trial_basis_requires_explicit_official_migration")
        try:
            allowed = {
                "account_fingerprint",
                "mode",
                "source_kind",
                "as_of",
                "window_start",
                "complete",
                "source_times",
                "source_hashes",
                "code_version",
                "config_version",
                "cash",
                "buying_power",
                "net_asset_value",
                "positions",
                "position_costs",
                "quotes",
                "fills",
                "cash_events",
            }
            if set(evidence) != allowed:
                raise ValueError("risk_evidence_schema_unknown")
            for quote in evidence["quotes"].values():
                if set(quote) != {"at", "price"}:
                    raise ValueError("risk_quote_schema_unknown")
            for event in evidence["fills"]:
                if set(event) != {
                    "id",
                    "order_id",
                    "at",
                    "quantity",
                    "notional",
                    "fees",
                    "fees_final",
                    "symbol",
                    "side",
                }:
                    raise ValueError("risk_fill_schema_unknown")
            for event in evidence["cash_events"]:
                if (
                    not {"id", "at", "kind", "amount"}
                    <= set(event)
                    <= {"id", "at", "kind", "amount", "scope"}
                ):
                    raise ValueError("risk_cash_event_schema_unknown")
            identity = self._identity()
            if evidence["account_fingerprint"] != identity or evidence["mode"] != "kis_demo":
                raise ValueError("risk_account_mismatch")
            cash_policy_hash = None
            if evidence["source_kind"] == "kis_vps":
                from trading.cash_service_policy import require_cash_only
                cash_policy_hash = digest(require_cash_only(self.manager, now))
            if evidence["source_kind"] not in {"kis_vps", "synthetic"}:
                raise ValueError("risk_source_unknown")
            for field in ("cash", "balances", "fills", "cash_events", "quotes"):
                if evidence["complete"].get(field) is not True:
                    raise ValueError("risk_evidence_incomplete")
                source_at = parse_timestamp(evidence["source_times"][field])
                if not 0 <= (now - source_at).total_seconds() <= 30 or source_at > parse_timestamp(
                    evidence["as_of"]
                ):
                    raise ValueError("risk_source_timestamp_invalid")
            if not 0 <= (now - parse_timestamp(evidence["as_of"])).total_seconds() <= 30:
                raise ValueError("risk_evidence_stale")
            if (
                not 0
                <= (
                    parse_timestamp(evidence["as_of"]) - parse_timestamp(evidence["window_start"])
                ).total_seconds()
            ):
                raise ValueError("risk_window_invalid")
            if not isinstance(evidence["source_hashes"], dict) or not evidence["source_hashes"]:
                raise ValueError("risk_original_evidence_missing")
            if any(
                not isinstance(value, str)
                or len(value) != 64
                or any(c not in "0123456789abcdef" for c in value)
                for value in evidence["source_hashes"].values()
            ):
                raise ValueError("risk_source_hash_invalid")
            risk = copy.deepcopy(before.get("risk_ledger"))
            if risk is None or "baseline" not in risk:
                # 첫 투자 기준과 그 이전의 미확인 손익을 구분한다. 기존 보유는 자동 인수하지 않는다.
                risk = {
                    "schema": 1,
                    "account_fingerprint": identity,
                    "mode": "kis_demo",
                    "baseline": copy.deepcopy(evidence),
                    "policy_hash": digest(self.manager.policy),
                    "fills": {},
                    "cash_events": {},
                    "days": {},
                    "checkpoints": [],
                    "issues": [],
                }
                if evidence["positions"] or evidence["fills"] or evidence["cash_events"]:
                    risk["issues"].append("initial_history_or_holdings_require_review")
            if risk["policy_hash"] != digest(self.manager.policy):
                raise ValueError("risk_policy_changed_requires_review")
            if risk["account_fingerprint"] != identity:
                raise ValueError("risk_account_mismatch")
            if risk["checkpoints"] and parse_timestamp(evidence["window_start"]) > parse_timestamp(
                risk["checkpoints"][-1]["as_of"]
            ):
                raise ValueError("risk_history_gap")
            if risk["checkpoints"] and parse_timestamp(evidence["as_of"]) < parse_timestamp(
                risk["checkpoints"][-1]["as_of"]
            ):
                raise ValueError("risk_checkpoint_out_of_order")
            for group in ("fills", "cash_events"):
                received = {}
                for event in evidence[group]:
                    identifier = event["id"]
                    if not isinstance(identifier, str) or not identifier or identifier in received:
                        raise ValueError("duplicate_risk_event")
                    if (
                        not parse_timestamp(evidence["window_start"])
                        <= parse_timestamp(event["at"])
                        <= parse_timestamp(evidence["as_of"])
                    ):
                        raise ValueError("risk_event_outside_window")
                    received[identifier] = copy.deepcopy(event)
                for identifier, previous in risk[group].items():
                    if (
                        parse_timestamp(previous["at"]) >= parse_timestamp(evidence["window_start"])
                        and identifier not in received
                    ):
                        raise ValueError("risk_history_event_missing")
                for identifier, event in received.items():
                    if identifier in risk[group] and risk[group][identifier] != event:
                        raise ValueError("risk_event_revision_requires_review")
                    risk[group][identifier] = event
            evaluation = self._calculate(risk, evidence, now)
            evaluation["usd_funding_policy_hash"] = cash_policy_hash
            risk["last_evaluation"] = evaluation
            risk["checkpoints"].append(
                {
                    "as_of": evidence["as_of"],
                    "hash": digest(evidence),
                    "source_hashes": evidence["source_hashes"],
                    "code_version": evidence["code_version"],
                    "config_version": evidence["config_version"],
                    "source_kind": evidence["source_kind"],
                }
            )
            risk.pop("last_failure", None)
            self.manager.state["risk_ledger"] = risk
            self.manager._save()
            return self.context(now)
        except Exception as error:
            self.manager.state = before
            risk = self.manager.state.setdefault(
                "risk_ledger", {"schema": 1, "account_fingerprint": before.get("broker_identity")}
            )
            risk["last_failure"] = {
                "at": now.isoformat(),
                "code": (
                    str(error)
                    if str(error).replace("_", "").isalpha()
                    else "risk_validation_failed"
                ),
            }
            self.manager._save()
            raise

    def _calculate(self, risk, evidence, now):
        baseline = risk["baseline"]
        cash = amount(baseline["cash"])
        initial = amount(baseline["net_asset_value"])
        if initial <= 0:
            raise ValueError("initial_capital_not_positive")
        issues = list(risk["issues"])
        lots, episodes, closed = {}, {}, []
        realized, fees, external_flow, dividend = (Decimal(0) for _ in range(4))
        day = local_day(evidence["as_of"])
        daily_realized, daily_flow, daily_fees = (Decimal(0) for _ in range(3))
        events = [(row["at"], identifier, "fill", row) for identifier, row in risk["fills"].items()]
        events += [
            (row["at"], identifier, "cash", row) for identifier, row in risk["cash_events"].items()
        ]
        if len({(stamp, identifier) for stamp, identifier, _, _ in events}) != len(events):
            raise ValueError("ambiguous_risk_event_order")
        executions_by_time = {}
        for stamp, identifier, kind, event in events:
            if kind == "fill":
                key = (parse_timestamp(stamp), event["symbol"])
                sides = executions_by_time.setdefault(key, set())
                sides.add(event["side"])
                if len(sides) > 1:
                    raise ValueError("ambiguous_execution_sequence")
        for stamp, identifier, kind, event in sorted(
            events, key=lambda item: (parse_timestamp(item[0]), item[1])
        ):
            if parse_timestamp(stamp) <= parse_timestamp(baseline["as_of"]):
                issues.append("pre_baseline_event_requires_review")
                continue
            if kind == "cash":
                value = amount(event["amount"], signed=True)
                event_kind = event["kind"]
                if event_kind in {"DEPOSIT", "WITHDRAWAL"}:
                    if (event_kind == "DEPOSIT" and value <= 0) or (
                        event_kind == "WITHDRAWAL" and value >= 0
                    ):
                        raise ValueError("cash_flow_direction_invalid")
                    external_flow += value
                    if local_day(stamp) == day:
                        daily_flow += value
                elif event_kind == "DIVIDEND":
                    dividend += value
                elif event_kind == "FEE":
                    if event.get("scope") != "account":
                        issues.append("fee_allocation_requires_review")
                    if value > 0:
                        raise ValueError("fee_direction_invalid")
                    fees -= value
                    if local_day(stamp) == day:
                        daily_fees -= value
                else:
                    issues.append("cash_correction_requires_review")
                cash += value
                continue
            order = self.manager.state["orders"].get(event["order_id"])
            if not order or (event["symbol"], event["side"]) != (order["symbol"], order["side"]):
                raise ValueError("manual_or_unmatched_execution")
            quantity = event["quantity"]
            if type(quantity) is not int or quantity <= 0:
                raise ValueError("risk_quantity_invalid")
            if event["fees_final"] is not True:
                raise ValueError("execution_cost_unknown")
            value, fee = amount(event["notional"]), amount(event["fees"])
            limit_notional = amount(order["price"]) * quantity
            if (event["side"] == "BUY" and value > limit_notional + TOLERANCE) or (
                event["side"] == "SELL" and value < limit_notional - TOLERANCE
            ):
                raise ValueError("execution_violates_limit_contract")
            if value <= 0:
                raise ValueError("execution_notional_invalid")
            fees += fee
            if local_day(stamp) == day:
                daily_fees += fee
            symbol = event["symbol"]
            position = lots.setdefault(symbol, {"quantity": 0, "cost": Decimal(0)})
            if event["side"] == "BUY":
                if not position["quantity"]:
                    episodes[symbol] = {"pnl": Decimal(0), "first_at": stamp}
                position["quantity"] += quantity
                position["cost"] += value + fee
                cash -= value + fee
            elif event["side"] == "SELL":
                if quantity > position["quantity"]:
                    raise ValueError("risk_sell_without_basis")
                # 이동평균 원가: 부분 매도 비용을 6자리로 배분하고 마지막 잔량에 차이를 남긴다.
                cost = (
                    position["cost"]
                    if quantity == position["quantity"]
                    else (position["cost"] * quantity / position["quantity"]).quantize(
                        PRECISION, rounding=ROUND_HALF_EVEN
                    )
                )
                pnl = value - fee - cost
                position["quantity"] -= quantity
                position["cost"] -= cost
                cash += value - fee
                realized += pnl
                if local_day(stamp) == day:
                    daily_realized += pnl
                episodes[symbol]["pnl"] += pnl
                if not position["quantity"]:
                    closed.append(
                        {"symbol": symbol, "closed_at": stamp, "pnl": str(episodes[symbol]["pnl"])}
                    )
                    del episodes[symbol]
            else:
                raise ValueError("risk_side_invalid")
        # 같은 원주문의 여러 부분 체결을 중복 합산하거나 원수량을 넘기지 못하게 한다.
        for order_id in {row["order_id"] for row in risk["fills"].values()}:
            total = sum(
                row["quantity"] for row in risk["fills"].values() if row["order_id"] == order_id
            )
            if total > self.manager.state["orders"][order_id]["quantity"]:
                raise ValueError("execution_exceeds_original_quantity")
        actual_positions = evidence["positions"]
        expected_positions = {
            key: value["quantity"] for key, value in lots.items() if value["quantity"]
        }
        for symbol, position in lots.items():
            if (
                position["quantity"]
                and abs(amount(evidence["position_costs"].get(symbol, "-1")) - position["cost"])
                > TOLERANCE
            ):
                issues.append("position_cost_basis_mismatch")
        if actual_positions != expected_positions:
            issues.append("unexplained_position_or_initial_holdings")
        if abs(cash - amount(evidence["cash"])) > TOLERANCE:
            issues.append("unexplained_cash_movement")
        marked, exposure = Decimal(0), Decimal(0)
        for symbol, quantity in actual_positions.items():
            if type(quantity) is not int or quantity <= 0:
                raise ValueError("risk_position_quantity_invalid")
            quote = evidence["quotes"][symbol]
            if not 0 <= (now - parse_timestamp(quote["at"])).total_seconds() <= 30:
                raise ValueError("risk_valuation_stale")
            if parse_timestamp(quote["at"]) > parse_timestamp(evidence["as_of"]):
                raise ValueError("risk_quote_after_snapshot")
            marked += quantity * amount(quote["price"])
            exposure += lots.get(symbol, {}).get("cost", Decimal(0))
        nav = amount(evidence["cash"]) + marked
        if abs(nav - amount(evidence["net_asset_value"])) > TOLERANCE:
            issues.append("net_asset_value_mismatch")
        buying_power = amount(evidence["buying_power"])
        if buying_power > amount(evidence["cash"]) + TOLERANCE:
            issues.append("buying_power_exceeds_supported_cash_basis")
        consecutive, last_loss = 0, None
        for trade in closed:
            if amount(trade["pnl"], signed=True) < 0:
                consecutive += 1
                last_loss = trade["closed_at"]
            else:
                consecutive = 0
        # 각 현지 날짜의 첫 기준은 직전 정상 평가. 첫 날은 등록 시점 기준임을 명시한다.
        day_state = risk["days"].setdefault(
            day,
            {
                "baseline_equity": risk.get("last_evaluation", {}).get(
                    "net_asset_value", str(initial)
                ),
                "baseline_flow": risk.get("last_evaluation", {}).get("external_flow", "0"),
                "baseline_at": risk.get("last_evaluation", {}).get("as_of", baseline["as_of"]),
                "halted": False,
                "basis": "previous_observation_or_enrollment",
            },
        )
        adjusted_pnl = (
            nav
            - amount(day_state["baseline_equity"])
            - (external_flow - amount(day_state["baseline_flow"], signed=True))
        )
        day_basis = amount(day_state["baseline_equity"])
        loss_ratio = max(Decimal(0), -adjusted_pnl / day_basis) if day_basis else Decimal(1)
        if loss_ratio >= Decimal(str(self.manager.policy["daily_loss_limit"])):
            day_state["halted"] = True
        day_state.update(
            as_of=evidence["as_of"], loss_ratio=str(loss_ratio), adjusted_pnl=str(adjusted_pnl)
        )
        cooling_down = (
            consecutive >= self.manager.policy["consecutive_losses"]
            and last_loss is not None
            and (now - parse_timestamp(last_loss)).total_seconds()
            < self.manager.policy["loss_cooldown_minutes"] * 60
        )
        return {
            "as_of": evidence["as_of"],
            "checkpoint_hash": digest(evidence),
            "initial": str(initial),
            "cash_balance": str(amount(evidence["cash"])),
            "buying_power": str(buying_power),
            "net_asset_value": str(nav),
            "exposure": str(exposure),
            "unrealized_pnl": str(marked - exposure),
            "realized_pnl_after_cost": str(realized),
            "fees": str(fees),
            "external_flow": str(external_flow),
            "dividend_income": str(dividend),
            "daily_realized_after_cost": str(daily_realized),
            "daily_fees": str(daily_fees),
            "daily_external_flow": str(daily_flow),
            "daily_loss_ratio": str(loss_ratio),
            "day_halted": day_state["halted"],
            "consecutive_losses": consecutive,
            "last_loss_at": last_loss,
            "closed_trades": closed,
            "issues": sorted(set(issues)),
            "source_kind": evidence["source_kind"],
            "positions": actual_positions,
            "position_costs": {
                key: str(value["cost"]) for key, value in lots.items() if value["quantity"]
            },
            "consecutive_loss_cooldown": cooling_down,
            "eligible": not issues and not day_state["halted"] and not cooling_down,
            "baseline_scope": "forward_from_enrollment",
        }

    def assess_observation(self, review, now=None):
        """현금 관측을 위험 평가에 연결한다. 부분 근거도 평가하되 누락 자료를 승인하지 않는다."""
        from trading.demo_risk_assessment import assess_observation
        return assess_observation(self.manager, review, now)

    def assessment(self, now=None):
        """영속 평가를 원본 시각·계좌·설정·주문과 대조해 조회한다. RiskProof와 구분한다."""
        from trading.demo_risk_assessment import latest_assessment
        return latest_assessment(self.manager, now)

    def record_unsettled_observation(self, observation):
        """실제 계좌의 확인 가능한 수량·여력·비용 대기를 기록한다. 위험 승인은 별도다.

        현금/정산이 부족한 경우에도 실제 조회 근거를 버리지 않는다. 이 기록을
        context() 또는 신규 주문의 RiskProof로 사용하지 않으며 PnL은 미확정이다.
        """
        identity = self._identity()
        if observation.get("account_fingerprint") != identity or observation.get("mode") != "kis_demo":
            raise ValueError("unsettled_observation_account_mismatch")
        now = datetime.now(timezone.utc)
        if not 0 <= (now - parse_timestamp(observation["as_of"])).total_seconds() <= 30:
            raise ValueError("unsettled_observation_stale")
        if not observation.get("source_hashes"):
            raise ValueError("unsettled_observation_sources_missing")
        for value in observation["source_hashes"].values():
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("unsettled_observation_source_hash_invalid")
        record = copy.deepcopy(observation)
        record.update(risk_approved=False, execution_cash_usd=None, net_asset_value_usd=None,
                      realized_pnl_after_cost=None, final_costs_usd=None)
        # 완전한 검산의 checkpoints와 구분하며 주문과 같은 SQLite 백업에 포함한다.
        records = self.manager.state.setdefault("risk_observations", {})
        identifier = digest(observation)
        previous = records.get(identifier)
        if previous is not None and previous != record:
            raise ValueError("unsettled_observation_revision")
        records[identifier] = record
        try:
            self.manager._save()
        except Exception:
            self.manager.ready = False
            self.manager._execution_observation_valid = False
            raise
        return identifier

    def context(self, now=None):
        now = now or datetime.now(timezone.utc)
        risk = self.manager.state.get("risk_ledger", {})
        value = risk.get("last_evaluation")
        if value and value.get('source_kind')=='user_designated_strategy_demo':
            from trading.strategy_model_basis import context
            return context(self.manager,now)
        if value and value.get("source_kind") == "user_designated_demo_trial":
            from trading.demo_user_basis import trial_context
            return trial_context(self.manager,now)
        if not value or risk.get("last_failure"):
            raise ValueError("risk_evaluation_unavailable")
        if value.get("source_kind") == "kis_vps":
            from trading.cash_service_policy import require_cash_only
            if digest(require_cash_only(self.manager, now)) != value.get("usd_funding_policy_hash"):
                raise ValueError("usd_funding_policy_changed_requires_risk_recheck")
        if risk.get("account_fingerprint") != self._identity():
            raise ValueError("risk_account_mismatch")
        if not 0 <= (now - parse_timestamp(value["as_of"])).total_seconds() <= 30:
            raise ValueError("risk_evaluation_stale")
        return RiskProof(
            risk["account_fingerprint"],
            value["checkpoint_hash"],
            value["as_of"],
            value["initial"],
            value["daily_loss_ratio"],
            value["consecutive_losses"],
            value["last_loss_at"],
            value["eligible"],
            copy.deepcopy(value["positions"]),
            copy.deepcopy(value["position_costs"]),
            value["buying_power"],
            value["exposure"],
        )

    def validate_snapshot(self, snapshot):
        """저장된 평가와 주문용 스냅샷이 일치해야 한다. 수동 검증 플래그는 받지 않는다."""
        proof = self.context()
        if not proof.eligible or snapshot.get("risk_checkpoint_hash") != proof.checkpoint_hash:
            raise ValueError("risk_snapshot_not_proven")
        if snapshot.get("risk_account_fingerprint") != proof.account_fingerprint:
            raise ValueError("risk_snapshot_account_mismatch")
        if (
            snapshot["positions"] != proof.positions
            or snapshot["position_costs"] != proof.position_costs
        ):
            raise ValueError("risk_snapshot_inventory_changed")
        if "buying_power_evidence" in snapshot:
            from trading.buying_power import validate_api_buying_power
            validate_api_buying_power(self.manager, snapshot)
        elif amount(snapshot["cash"]) != amount(proof.buying_power):
            raise ValueError("risk_snapshot_money_changed")
        if amount(snapshot["exposure"]) != amount(proof.exposure):
            raise ValueError("risk_snapshot_money_changed")
        for key, expected in proof.values().items():
            if key == "last_loss_at":
                matches = snapshot.get(key) == expected
            else:
                matches = key in snapshot and Decimal(str(snapshot[key] or 0)) == Decimal(
                    str(expected or 0)
                )
            if not matches:
                raise ValueError("risk_snapshot_values_changed")
