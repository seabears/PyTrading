"""일봉 연구의 시장·변동성·금리 필터. 수정 위치는 ../Config/indicators.json.

코스피/SPY는 시장 추세, VIX는 미국 옵션 내재 변동성, 한국 3년 국채는 수익률(%)이다.
날짜 라벨을 실제 발표 시각으로 간주하지 않는다. 모든 지표를 2일 이상 지연해 사용한다.
이 지연은 시차 누수를 줄이는 연구 가정이며, 과거 수정값 문제까지 해결하지는 않는다.
"""
import math
from bisect import bisect_right
from datetime import date, timedelta


def validate_settings(settings):
    required = {"lag_calendar_days", "maximum_age_days", "market_trend_days", "maximum_vix",
                "bond_change_days", "maximum_bond_rise_percentage_points"}
    if not isinstance(settings, dict) or set(settings) != required:
        raise ValueError("indicators.json의 설정 이름을 확인하세요.")
    for name in ("lag_calendar_days", "maximum_age_days", "market_trend_days", "bond_change_days"):
        if type(settings[name]) is not int or not 1 <= settings[name] <= 365:
            raise ValueError("지표 일수는 1~365 정수여야 합니다.")
    if settings["lag_calendar_days"] < 2 or settings["maximum_age_days"] < settings["lag_calendar_days"]:
        raise ValueError("시차를 고려해 지연 2일 이상, 유효 기간은 지연 이상으로 설정하세요.")
    for name in ("maximum_vix", "maximum_bond_rise_percentage_points"):
        value = settings[name]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError("지표 임계값은 유한한 양수여야 합니다.")
    return settings


def prepare_series(rows):
    """누락·충돌을 조용히 덮지 않는다. 금리는 이론상 음수도 가능하므로 유한성만 검사한다."""
    values = {}
    for row in rows:
        label = date.fromisoformat(row["date"])
        value = float(row["value"])
        if not math.isfinite(value) or label in values:
            raise ValueError("지표 값이 유한하지 않거나 날짜가 중복됐습니다.")
        values[label] = value
    dates = sorted(values)
    return {"dates": dates, "values": [values[label] for label in dates]}


def available_values(series, signal_date, settings):
    """미래·같은 날 지표를 제외하고, 오래된 마지막 값은 무한히 이월하지 않는다."""
    day = date.fromisoformat(signal_date)
    cutoff = day - timedelta(days=settings["lag_calendar_days"])
    count = bisect_right(series["dates"], cutoff)
    if not count or (day - series["dates"][count - 1]).days > settings["maximum_age_days"]:
        return []
    return series["values"][:count]


def make_entry_filter(mode, series, settings):
    """각 지표의 추가 효과를 따로 비교한다. 필요한 자료가 없으면 신규 매수는 보류한다."""
    if mode not in {"baseline", "market", "vix", "market_vix", "bond"}:
        raise ValueError("지원하지 않는 지표 비교입니다.")

    def permits_entry(signal_date):
        if mode in {"market", "market_vix"}:
            values = available_values(series["market"], signal_date, settings)
            count = settings["market_trend_days"]
            if len(values) < count or values[-1] <= sum(values[-count:]) / count:
                return False
        if mode in {"vix", "market_vix"}:
            values = available_values(series["vix"], signal_date, settings)
            if not values or not 0 < values[-1] <= settings["maximum_vix"]:
                return False
        if mode == "bond":
            values = available_values(series["bond"], signal_date, settings)
            count = settings["bond_change_days"]
            if len(values) <= count or values[-1] - values[-count - 1] > settings["maximum_bond_rise_percentage_points"]:
                return False
        return True

    return permits_entry
