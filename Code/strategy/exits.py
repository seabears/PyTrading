"""수익이 난 뒤 매도 기준을 올린다. 미래 가격이나 뉴스는 사용하지 않는다.

unit_cost는 매수 비용을 포함한 1주 원가, proceeds_ratio는 매도 후 남는 비율이다.
반환 가격은 매도 신호 기준이다. 갭·체결 지연으로 실제 손실이 날 수 있다.
"""
import math


PROFIT_EXIT_DEFAULTS = {
    "breakeven_trigger": .03,     # 비용 차감 고점 수익 3%부터 원가 보호 활성화. 0이면 끔.
    "profit_lock_trigger": .05,   # 비용 차감 고점 수익 5%부터 이익 일부 보호. 0이면 끔.
    "profit_keep_ratio": .5,      # 고점에서 생긴 순이익의 50%를 보호하는 기준.
    "exit_profit_buffer": .002,  # 원가 보호 기준에 순이익 0.2% 여유를 더함.
    "exit_sell_cost_ratio": .003, # 직접 신호 평가의 매도 비용 가정. 모의 계좌는 실제 설정 사용.
}


def validate_profit_exits(settings):
    for name in PROFIT_EXIT_DEFAULTS:
        value = settings[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value < 1:
            raise ValueError(f"{name}: 0 이상 1 미만의 비율이어야 합니다.")
    if settings["profit_lock_trigger"] and not 0 < settings["profit_keep_ratio"] < 1:
        raise ValueError("이익 보호 비율은 0 초과 1 미만이어야 합니다.")
    if settings["breakeven_trigger"] and settings["exit_profit_buffer"] >= settings["breakeven_trigger"]:
        raise ValueError("원가 보호 여유는 활성화 수익보다 작아야 합니다.")


def profit_exit_floor(unit_cost, observed_peak, proceeds_ratio, settings):
    """이미 관찰한 고점으로만 보호 가격을 계산한다. 아직 활성화되지 않으면 None.

    고점의 순수익이 10%이고 보호 비율이 50%라면 순수익 5%에 해당하는
    가격을 기준으로 삼는다. 현재 수익률이 줄어도 고점 기록은 내려가지 않는다.
    """
    validate_profit_exits(settings)
    if not all(math.isfinite(value) and value > 0 for value in (unit_cost, observed_peak, proceeds_ratio)) or proceeds_ratio > 1:
        raise ValueError("원가·고점·매도 후 잔존 비율을 확인하세요.")
    peak_net_return = observed_peak * proceeds_ratio / unit_cost - 1
    floors = []
    if settings["breakeven_trigger"] and peak_net_return >= settings["breakeven_trigger"]:
        floors.append((unit_cost * (1 + settings["exit_profit_buffer"]) / proceeds_ratio, "breakeven_protection"))
    if settings["profit_lock_trigger"] and peak_net_return >= settings["profit_lock_trigger"]:
        floors.append((unit_cost * (1 + peak_net_return * settings["profit_keep_ratio"]) / proceeds_ratio, "profit_lock"))
    return max(floors, key=lambda item: item[0]) if floors else None
