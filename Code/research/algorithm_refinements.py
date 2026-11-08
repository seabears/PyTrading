"""기준 전략에서 한 항목만 바꾸는 실험 계획과 개발·검증 기반 선정을 관리한다."""
import copy
from research.algorithm_study import resolve_strategy

RISK_KEYS = {"stop_atr", "trailing_atr"}
STRATEGY_KEYS = {"breakout_days", "exit_days", "fast_ma", "slow_ma", "holding_days", "rotation_days"}


def build_variants(plan, base_settings):
    """조합 전수 탐색 대신 기준값의 이웃만 비교한다. 각 변경은 정확히 한 항목이다."""
    variants = []
    for family, axes in plan["families"].items():
        strategy = resolve_strategy(family)
        base = {"name": family + "__base", "family": family, "parent": None,
                "strategy": strategy, "risk": {key: base_settings[key] for key in RISK_KEYS},
                "market_filter": True, "change": "baseline"}
        variants.append(base)
        for key, values in axes.items():
            if key not in RISK_KEYS | STRATEGY_KEYS | {"market_filter"}:
                raise ValueError("알 수 없는 조정 항목: " + key)
            if not isinstance(values, list) or not values or len(values) != len(set(values)):
                raise ValueError("조정값은 비어 있지 않은 중복 없는 목록이어야 합니다.")
            original = base["risk"][key] if key in RISK_KEYS else base["market_filter"] if key == "market_filter" else strategy[key]
            for value in values:
                if value == original:
                    raise ValueError("기준값과 같은 변경을 중복 실험하지 않습니다.")
                variant = copy.deepcopy(base)
                variant.update(name=family + "__" + key + "_" + str(value).lower().replace(".", "p"),
                               parent=base["name"], change=f"{key}: {original} -> {value}")
                if key in RISK_KEYS:
                    if type(value) not in (int, float) or not 0 < value < 20:
                        raise ValueError("ATR 배수는 0 초과 20 미만이어야 합니다.")
                    variant["risk"][key] = value
                elif key == "market_filter":
                    if type(value) is not bool:
                        raise ValueError("시장 필터는 true/false입니다.")
                    variant["market_filter"] = value
                else:
                    variant["strategy"][key] = value
                    resolve_strategy(family, variant["strategy"])
                variants.append(variant)
    if not variants or len({variant["name"] for variant in variants}) != len(variants):
        raise ValueError("빈 실험 또는 중복 실험 이름입니다.")
    return variants


def feature_periods(variants):
    """사용할 기간만 추가 계산한다. 지표 계산은 항상 해당 날짜까지의 가격으로 한다."""
    return {"ma": sorted({value for variant in variants for key, value in variant["strategy"].items() if key in {"fast_ma", "slow_ma"}}),
            "high": sorted({variant["strategy"]["breakout_days"] for variant in variants}),
            "low": sorted({variant["strategy"]["exit_days"] for variant in variants})}


def select_variant(results, variants, plan):
    """평가 기간은 읽지 않는다. 비용에 약한 계열과 한 값에서만 좋은 후보를 거른다."""
    threshold = plan["minimum_family_stress_positive_fraction"]
    if type(threshold) not in (int, float) or not 0 < threshold <= 1:
        raise ValueError("계열 안정 비율은 0 초과 1 이하여야 합니다.")
    fractions = {}
    for family in {variant["family"] for variant in variants}:
        names = [variant["name"] for variant in variants if variant["family"] == family]
        fractions[family] = sum(results[name]["validation"]["double_cost"]["summary"]["net_return"] > 0
                                for name in names) / len(names)
    checks, eligible = {}, []
    for variant in variants:
        name = variant["name"]
        stages = results[name]
        development = stages["development"]["base"]["summary"]
        dev_stress = stages["development"]["double_cost"]["summary"]
        validation = stages["validation"]["base"]["summary"]
        stress = stages["validation"]["double_cost"]["summary"]
        policy = plan["selection"]
        passed = {"development_positive": development["net_return"] > 0,
                  "development_stress_positive": dev_stress["net_return"] > 0,
                  "validation_positive": validation["net_return"] > 0,
                  "validation_stress_positive": stress["net_return"] > 0,
                  "validation_sample": validation["trades"] >= policy["minimum_validation_trades"],
                  "validation_drawdown": max(validation["max_drawdown"], stress["max_drawdown"]) <= policy["maximum_validation_drawdown"],
                  "validation_profit_factor": validation["profit_factor"] is not None and validation["profit_factor"] >= policy["minimum_validation_profit_factor"],
                  "validation_stress_profit_factor": stress["profit_factor"] is not None and stress["profit_factor"] > 1,
                  "validation_positive_years": sum(value > 0 for value in validation["year_returns"].values()) >= policy["minimum_positive_validation_years"],
                  "family_stability": fractions[variant["family"]] >= threshold}
        checks[name] = passed
        if all(passed.values()):
            eligible.append(name)
    selected = max(eligible, key=lambda name: results[name]["validation"]["double_cost"]["summary"]["net_return"]
                   - 2 * results[name]["validation"]["double_cost"]["summary"]["max_drawdown"]) if eligible else None
    return {"selected": selected, "eligible": eligible, "checks": checks,
            "family_validation_stress_positive_fraction": fractions,
            "evaluation_used_for_selection": False, "cash_when_none": True}
