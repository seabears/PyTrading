"""위험 원장 합성 입력. 실제 KIS 자료나 검증 결과가 아니다."""

from datetime import datetime, timezone, timedelta
from trading.risk_ledger import RiskLedger, digest


def evidence(manager, at=None, **changes):
    at = at or datetime.now(timezone.utc)
    value = {
        "account_fingerprint": manager.state["broker_identity"],
        "mode": "kis_demo",
        "source_kind": "synthetic",
        "as_of": at.isoformat(),
        "window_start": (at - timedelta(seconds=10)).isoformat(),
        "complete": {key: True for key in ("cash", "balances", "fills", "cash_events", "quotes")},
        "source_times": {
            key: at.isoformat() for key in ("cash", "balances", "fills", "cash_events", "quotes")
        },
        "source_hashes": {"fixture": digest({"fixture": "not_actual_kis"})},
        "code_version": "synthetic-test",
        "config_version": "synthetic-test",
        "cash": "10000",
        "buying_power": "10000",
        "net_asset_value": "10000",
        "positions": {},
        "position_costs": {},
        "quotes": {},
        "fills": [],
        "cash_events": [],
    }
    value.update(changes)
    return value


def managed_order(manager, identifier, symbol="AAPL", side="BUY", quantity=2):
    manager.state["orders"][identifier] = {
        "id": identifier,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": "80" if side == "SELL" else "100",
        "order_type": "LIMIT",
        "status": "FILLED",
        "filled": quantity,
        "notional": str(quantity * 100),
        "broker_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def execution(identifier, order, at, quantity, notional, fees="0", symbol="AAPL", side="BUY"):
    return {
        "id": identifier,
        "order_id": order,
        "at": at.isoformat(),
        "quantity": quantity,
        "notional": str(notional),
        "fees": str(fees),
        "fees_final": True,
        "symbol": symbol,
        "side": side,
    }


def seed_risk(manager, positions=None, cash="10000", source_kind="synthetic"):
    """기존 회귀 조건의 보유도 빈 기준 이후의 관리 매수 근거로 재현한다."""
    manager.state.setdefault("broker_identity", "test-account-fingerprint")
    positions = positions or {}
    now = datetime.now(timezone.utc)
    baseline = now - timedelta(seconds=3)
    if source_kind == "kis_vps":
        # 합성 계좌 상태 파서다. 실제 KIS 계약 확인으로 표시하지 않는다.
        from Test.trading.cash_policy_fixtures import confirm_cash_only
        confirm_cash_only(manager, at=baseline)
    starting = str(int(cash) + sum(positions.values()) * 100)
    RiskLedger(manager).ingest(
        evidence(
            manager,
            baseline,
            cash=starting,
            buying_power=starting,
            net_asset_value=starting,
            source_kind=source_kind,
        ),
        now=baseline,
    )
    fills = []
    for symbol, quantity in positions.items():
        identifier = "basis-" + symbol
        managed_order(manager, identifier, symbol, quantity=quantity)
        fills.append(
            execution(
                identifier,
                identifier,
                now - timedelta(seconds=2),
                quantity,
                quantity * 100,
                symbol=symbol,
            )
        )
    proof = RiskLedger(manager).ingest(
        evidence(
            manager,
            now,
            cash=cash,
            buying_power=cash,
            source_kind=source_kind,
            net_asset_value=str(int(cash) + sum(positions.values()) * 100),
            positions=positions,
            position_costs={key: str(value * 100) for key, value in positions.items()},
            fills=fills,
            quotes={key: {"at": now.isoformat(), "price": "100"} for key in positions},
        ),
        now=now,
    )
    return proof


def snapshot(proof):
    return {
        **proof.values(),
        "cash": proof.buying_power,
        "positions": proof.positions,
        "position_costs": proof.position_costs,
        "exposure": proof.exposure,
        "as_of": proof.as_of,
        "risk_checkpoint_hash": proof.checkpoint_hash,
        "risk_account_fingerprint": proof.account_fingerprint,
    }
