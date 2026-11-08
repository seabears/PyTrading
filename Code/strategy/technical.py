"""독립적인 장중 VWAP·거래량 / 일봉 MA·모멘텀 신호. 주문·파일·네트워크 호출 없음.

입력에는 그 시각까지 완성된 봉만 전달한다. 임계값은 Config/technical-study.json에서 수정한다.
VWAP은 체결별 가격이 없는 OHLCV 자료의 HLC3 가중 추정치다. ATR은 TR의 단순평균이다.
"""
from bisect import bisect_right
from datetime import date, timedelta


def average_true_range(history, period):
    """갭을 포함한 TR의 period개 단순평균. Wilder 평활 ATR과 구분한다."""
    if len(history) < period + 1:
        return None
    ranges = []
    for index in range(len(history) - period, len(history)):
        current, previous = history[index], history[index - 1]
        ranges.append(max(current["high"] - current["low"],
                          abs(current["high"] - previous["close"]), abs(current["low"] - previous["close"])))
    return sum(ranges) / period


def session_vwap(history):
    """해당 정규장 시작부터 전달된 완성 봉만 사용한다. 거래량이 0이면 계산하지 않는다."""
    volume = sum(bar["volume"] for bar in history)
    if volume <= 0:
        return None
    return sum((bar["high"] + bar["low"] + bar["close"]) / 3 * bar["volume"] for bar in history) / volume


def classify_regime(closes, fast, slow, slope_period):
    """단기·장기 평균과 장기 평균의 기울기로 상승·하락·횡보를 구분한다."""
    if len(closes) < slow + slope_period:
        return "unknown"
    fast_mean = sum(closes[-fast:]) / fast
    slow_mean = sum(closes[-slow:]) / slow
    prior_slow_mean = sum(closes[-slow - slope_period:-slope_period]) / slow
    if closes[-1] > fast_mean > slow_mean > prior_slow_mean:
        return "up"
    if closes[-1] < fast_mean < slow_mean < prior_slow_mean:
        return "down"
    return "sideways"


class MarketRegime:
    """같은 날 지수 종가가 장중 신호에 섞이지 않도록 2일 이상 지연해 사용한다."""
    def __init__(self, bars, settings):
        self.bars = bars
        self.dates = [bar["date"] for bar in bars]
        self.settings = settings

    def at(self, day):
        signal_date = date.fromisoformat(day)
        cutoff = (signal_date - timedelta(days=self.settings["lag_calendar_days"])).isoformat()
        count = bisect_right(self.dates, cutoff)
        if not count or (signal_date - date.fromisoformat(self.dates[count - 1])).days > self.settings["maximum_age_days"]:
            return "unknown"
        closes = [bar["close"] for bar in self.bars[max(0, count - self.settings["slow"] - self.settings["slope_period"]):count]]
        return classify_regime(closes, self.settings["fast"], self.settings["slow"], self.settings["slope_period"])


def signal_details(history, family, settings, regime="unknown", require_up_market=False):
    """조건별 통과 여부를 반환한다. 종목 신호와 시장 필터를 별도로 기록한다."""
    atr = average_true_range(history, settings["atr_period"])
    conditions = {"atr_ready": atr is not None and atr > 0,
                  "market_regime": not require_up_market or regime == "up"}
    values = {"atr": atr, "market_regime": regime}
    exit_signal = False
    if family == "vwap_volume":
        period = settings["volume_period"]
        conditions["history"] = len(history) >= max(period + 1, settings["atr_period"] + 1)
        current_vwap = session_vwap(history)
        previous_vwap = session_vwap(history[:-1])
        mean_volume = sum(bar["volume"] for bar in history[-period - 1:-1]) / period if len(history) > period else 0
        values.update(vwap=current_vwap, volume_ratio=history[-1]["volume"] / mean_volume if mean_volume > 0 else None)
        conditions["vwap_cross"] = (len(history) >= 2 and current_vwap is not None and previous_vwap is not None
            and history[-2]["close"] <= previous_vwap and history[-1]["close"] > current_vwap)
        conditions["volume"] = mean_volume > 0 and history[-1]["volume"] >= mean_volume * settings["volume_ratio"]
        exit_signal = current_vwap is not None and history[-1]["close"] < current_vwap
    elif family == "ma_momentum":
        minimum = max(settings["slow"], settings["momentum_period"] + 1)
        conditions["history"] = len(history) >= minimum
        if conditions["history"]:
            closes = [bar["close"] for bar in history]
            fast = sum(closes[-settings["fast"]:]) / settings["fast"]
            slow = sum(closes[-settings["slow"]:]) / settings["slow"]
            momentum = closes[-1] / closes[-settings["momentum_period"] - 1] - 1
            values.update(fast_mean=fast, slow_mean=slow, momentum=momentum)
            conditions["trend"] = closes[-1] > fast > slow
            conditions["momentum"] = momentum > settings["minimum_momentum"]
            exit_signal = closes[-1] < fast or momentum <= 0
    else:
        raise ValueError("지원하지 않는 기술적 전략입니다.")
    return {"enter": all(conditions.values()), "exit": exit_signal, "conditions": conditions, "values": values}
