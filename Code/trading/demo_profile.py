"""한정 모의 프로필의 단위와 상한을 검사한다. 파일 변경만으로 주문을 켜지 않는다."""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from paths import CONFIG_ROOT
from broker.product_policy import load_product_rules, validate_symbol


def load_demo_profile(path=None):
    """사용자는 더 엄격한 값만 지정할 수 있다. USD 금액·주·회·분 단위를 유지한다."""
    path = Path(path) if path else CONFIG_ROOT / "kis-demo-session.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("mode") != "kis_demo" or profile.get("environment") != "vps":
        raise ValueError("demo_profile_vps_required")
    if type(profile.get("enabled")) is not bool or profile.get("new_orders_allowed") is not False:
        raise ValueError("demo_profile_default_permission_invalid")
    if profile.get("order_type") != "LIMIT" or type(profile.get("quantity")) is not int or profile["quantity"] != 1:
        raise ValueError("demo_profile_one_share_limit_required")
    ceilings = {"maximum_concurrent_shares": 1, "maximum_buy_attempts": 2,
                "maximum_sell_attempts": 2, "maximum_cancel_attempts": 2,
                "maximum_active_minutes": 10}
    for name, ceiling in ceilings.items():
        value = profile.get(name)
        if type(value) is not int or not 1 <= value <= ceiling:
            raise ValueError("demo_profile_limit_out_of_range")
    try:
        budget = Decimal(str(profile["maximum_gross_buy_commitments_usd"]))
    except (InvalidOperation, KeyError):
        raise ValueError("demo_profile_budget_invalid") from None
    if not budget.is_finite() or not 0 < budget <= Decimal("500"):
        raise ValueError("demo_profile_budget_out_of_range")
    symbol = profile.get("symbol")
    rules = load_product_rules()
    validate_symbol(symbol, rules)
    if rules["verified_instruments"].get(symbol, {}).get("asset_type") != "stock":
        raise ValueError("demo_profile_stock_required")
    profile.setdefault("initial_reference", None)
    reference = profile["initial_reference"]
    if reference is not None:
        from datetime import date
        from trading.risk_ledger import amount
        if (not isinstance(reference, dict) or set(reference) != {"currency", "amount", "source", "confirmed_on"}
                or reference["currency"] != "USD" or reference["source"] != "user_confirmation"
                or amount(reference["amount"]) <= 0):
            raise ValueError("demo_profile_initial_reference_invalid")
        date.fromisoformat(reference["confirmed_on"])
    profile.setdefault("buying_power_service", "unknown")
    profile.setdefault("poll_seconds", 5)
    profile.setdefault("maximum_poll_count", 24)
    from trading.cash_service_policy import validate_service_setting
    validate_service_setting(profile["buying_power_service"])
    if type(profile["poll_seconds"]) is not int or not 2 <= profile["poll_seconds"] <= 30:
        raise ValueError("demo_profile_poll_interval_invalid")
    if type(profile["maximum_poll_count"]) is not int or not 1 <= profile["maximum_poll_count"] <= 60:
        raise ValueError("demo_profile_poll_count_invalid")
    if profile["poll_seconds"] * profile["maximum_poll_count"] > profile["maximum_active_minutes"] * 60:
        raise ValueError("demo_profile_poll_window_exceeds_activation")
    validate_trial_basis(profile)
    limits = {name: profile[name] for name in (*ceilings, "symbol", "quantity", "order_type", "maximum_gross_buy_commitments_usd", "buying_power_service", "poll_seconds", "maximum_poll_count", "initial_reference", "risk_basis", "risk_basis_authorized_on")}
    profile["limits_hash"] = hashlib.sha256(json.dumps(limits, sort_keys=True).encode()).hexdigest()
    return profile


def validate_trial_basis(profile):
    """일반/실계좌가 아닌 사용자가 허용한 고정 한정 모의 기준만 인정한다."""
    profile.setdefault("risk_basis", "official")
    profile.setdefault("risk_basis_authorized_on", None)
    if profile["risk_basis"] == "official":
        return
    if (profile["risk_basis"] != "user_designated_demo_trial"
            or profile["risk_basis_authorized_on"] != "2026-11-02"
            or profile.get("mode") != "kis_demo" or profile.get("environment") != "vps"
            or profile["quantity"] != 1 or profile["maximum_concurrent_shares"] != 1
            or Decimal(str(profile["maximum_gross_buy_commitments_usd"])) > 500
            or profile["maximum_buy_attempts"] > 2):
        raise ValueError("user_trial_basis_not_authorized_or_limits_invalid")
