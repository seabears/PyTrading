"""뉴스·가격·거래량으로 매매 신호를 만드는 룰 기반 판단 엔진.

읽는 순서: DEFAULT_CONFIG → evaluate() → 필요한 개별 함수.
설정 변경: DEFAULT_CONFIG 또는 --config JSON.
매수 조건 변경: build_entry_conditions(). 매도 순서 변경: evaluate().
이 파일은 신호만 반환한다. 시세 수집·주문·체결·상태 저장은 호출자의 책임이다.
모든 수치는 검증용 초기값이며 수익성이 확인된 투자 기준이 아니다.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from strategy.exits import PROFIT_EXIT_DEFAULTS, profit_exit_floor, validate_profit_exits


# 비율은 소수로 적는다: 0.03 = 3%. 가격·매입가는 같은 통화여야 한다.
DEFAULT_CONFIG = {
    "earnings_enabled": False,       # 실적 뉴스는 일반 뉴스와 독립된 모의 매매 조건.
    "news_enabled": True,             # 호재 필수·악재 매도 사용. 실제 실행은 Config/strategy.json에서 선택한다.
    "lookback": 20,                 # 비교할 과거 완성 봉 개수. 최신 봉은 별도다.
    "bar_minutes": 5,               # 봉 하나의 길이: 분.
    "volume_ratio": 2.0,            # 최신 거래량 / 과거 평균 거래량의 최소 배수.
    "max_spread": 0.003,            # 호가 차이 / 중간 가격: 최대 0.3%.
    "max_quote_age_seconds": 30,    # 현재 호가의 최대 경과 시간: 초.
    "max_chase": 0.02,              # 과거 최고가 대비 매수 호가의 최대 초과율: 2%.
    "stop_loss": 0.03,              # 평균 매입가 대비 손실 한도: 3%.
    "trailing_stop": 0.04,          # 진입 이후 최고 매수 호가 대비 하락 한도: 4%.
    "news_hours": 24,               # 뉴스 수신 후 사건을 사용할 시간: 시간.
    "cooldown_minutes": 30,         # 매도 체결 이후 재진입 대기 시간: 분.
    **PROFIT_EXIT_DEFAULTS,
}

# 뉴스 수집 계층과 약속한 사건 종류. 제목 키워드만으로 확정하면 안 된다.
POSITIVE_EVENT_KINDS = {
    "earnings_guidance_raised",       # 실적 전망 상향.
    "material_contract_confirmed",   # 중요한 계약 확정.
    "buyback_confirmed",             # 자사주 매입 확정.
}
NEGATIVE_EVENT_KINDS = {
    "earnings_guidance_cut",          # 실적 전망 하향.
    "material_contract_cancelled",   # 중요한 계약 취소.
    "accounting_issue_confirmed",    # 확인된 회계 문제.
}
JsonObject = dict[str, Any]


def parse_timestamp(value: str) -> datetime:
    """ISO 8601 시각을 읽는다. Z 또는 +09:00 같은 시간대 표기가 필수다."""
    parsed_time = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed_time.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed_time


def require_number(value: Any, *, allow_zero: bool = False) -> float:
    """양수를 읽는다. 거래량·수량처럼 0을 허용할 때만 allow_zero=True를 쓴다."""
    # Python은 True를 1로 취급하지만 가격·거래량으로 허용하지 않는다.
    if isinstance(value, bool):
        raise ValueError("boolean is not a numeric input")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError("invalid numeric input")
    if numeric_value < 0 or (numeric_value == 0 and not allow_zero):
        raise ValueError("invalid numeric input")
    return numeric_value


def load_config(overrides: JsonObject | None) -> JsonObject:
    """기본 설정에 JSON 설정을 덮어쓴다. 잘못된 설정 이름은 무시하지 않는다."""
    config = dict(DEFAULT_CONFIG)
    if overrides:
        if set(overrides) - set(config):
            raise ValueError("unknown configuration key")
        config.update(overrides)
    return config


def validate_config(config: JsonObject) -> None:
    """기간은 양수, 비율은 허용 범위인지 검사한다."""
    if type(config["earnings_enabled"]) is not bool:
        raise ValueError("earnings_enabled must be boolean")
    if type(config["news_enabled"]) is not bool:
        raise ValueError("news_enabled must be boolean")
    if type(config["lookback"]) is not int or config["lookback"] < 2:
        raise ValueError("lookback must be an integer >= 2")
    for name, value in config.items():
        if name not in {"lookback", "news_enabled", "earnings_enabled"} and name not in PROFIT_EXIT_DEFAULTS:
            require_number(value)
    validate_profit_exits(config)
    for name in ("stop_loss", "trailing_stop", "max_spread", "max_chase"):
        if config[name] >= 1:
            raise ValueError("percentage settings must be between 0 and 1")


def collect_news_events(
    snapshot: JsonObject, now: datetime, config: JsonObject,
) -> tuple[list[str], list[str]]:
    """알 수 있는 확정 사건을 중복 제거하고 긍정·부정 사건 ID를 반환한다.

    available_at은 시스템이 실제로 받은 시각이다. event_id는 같은 사건을 묶는 ID다.
    정정 기사는 최신 수신본을 쓴다. 출처 검증 자체는 뉴스 수집 계층의 책임이다.
    """
    latest_event_by_id: dict[str, JsonObject] = {}
    maximum_age_seconds = config["news_hours"] * 3600
    for event in snapshot.get("news_events", []):
        received_at = parse_timestamp(event["available_at"])
        age_seconds = (now - received_at).total_seconds()
        # 미래·오래된·미확정 정보와 다른 종목의 뉴스는 진입 근거가 될 수 없다.
        if not 0 <= age_seconds <= maximum_age_seconds:
            continue
        if event.get("confirmed") is not True or event.get("source_verified") is not True:
            continue
        if event.get("market") != snapshot["market"] or event.get("symbol") != snapshot["symbol"]:
            continue

        event_id = event["event_id"]
        if not event_id:
            raise ValueError("missing canonical event ID")
        previous_event = latest_event_by_id.get(event_id)
        if previous_event is None:
            latest_event_by_id[event_id] = event
        elif received_at >= parse_timestamp(previous_event["available_at"]):
            latest_event_by_id[event_id] = event

    positive_ids = []
    negative_ids = []
    for event_id, event in latest_event_by_id.items():
        if event["kind"] in POSITIVE_EVENT_KINDS:
            positive_ids.append(event_id)
        if event["kind"] in NEGATIVE_EVENT_KINDS:
            negative_ids.append(event_id)
    return positive_ids, negative_ids


def check_completed_bars(
    snapshot: JsonObject, now: datetime, config: JsonObject,
) -> tuple[list[JsonObject], str | None]:
    """과거 봉과 최신 봉을 검증해 (봉 목록, 대기 이유)를 반환한다.

    대기 이유가 None이면 통과했다. 같은 정규장 안의 연속 완성 봉만 사용한다.
    """
    required_count = config["lookback"] + 1
    all_bars = snapshot["bars"]
    if len(all_bars) < required_count:
        return [], "insufficient_completed_bars"
    bars = all_bars[-required_count:]
    expected_duration = timedelta(minutes=config["bar_minutes"])
    previous_end = None
    for bar in bars:
        start = parse_timestamp(bar["start"])
        end = parse_timestamp(bar["end"])
        received_at = parse_timestamp(bar["available_at"])
        if bar.get("complete") is not True:
            return [], "invalid_or_unfinished_bar"
        if end > now or received_at > now or received_at < end:
            return [], "invalid_or_unfinished_bar"
        if end - start != expected_duration or bar["session_id"] != snapshot["session_id"]:
            return [], "invalid_or_unfinished_bar"
        if previous_end is not None and start != previous_end:
            return [], "non_contiguous_bars"
        previous_end = end
        low = require_number(bar["low"])
        high = require_number(bar["high"])
        close = require_number(bar["close"])
        if not low <= close <= high:
            raise ValueError("invalid bar price range")
        require_number(bar["volume"], allow_zero=True)

    # 다음 봉이 완성될 시간이 지났는데 갱신되지 않았으면 오래된 데이터다.
    if now - previous_end >= expected_duration:
        return [], "stale_bars"
    return bars, None


def calculate_bar_metrics(bars: list[JsonObject]) -> JsonObject:
    """최신 봉을 제외한 과거 평균·최고가와 최신 봉의 거래량 배수를 계산한다."""
    previous_bars = bars[:-1]
    latest_bar = bars[-1]
    count = len(previous_bars)
    average_volume = sum(float(bar["volume"]) for bar in previous_bars) / count
    average_close = sum(float(bar["close"]) for bar in previous_bars) / count
    prior_high = max(float(bar["high"]) for bar in previous_bars)
    # 과거 거래량이 전부 0이면 배수를 정의할 수 없으므로 진입하지 않는다.
    volume_ratio = None
    if average_volume > 0:
        volume_ratio = float(latest_bar["volume"]) / average_volume
    return {
        "prior_average_close": average_close,
        "prior_high": prior_high,
        "volume_ratio": volume_ratio,
    }


def build_entry_conditions(
    snapshot: JsonObject, config: JsonObject, metrics: JsonObject,
    latest_bar: JsonObject, ask_price: float,
) -> dict[str, bool]:
    """매수 조건을 수정하는 중심 함수. 모든 조건이 True여야 BUY가 된다.

    각 조건에 이름을 붙여 결과에서 실패 이유를 확인할 수 있도록 한다.
    계좌 전체의 위험 예산은 외부 관리 계층에서 확인해야 한다.
    """
    breakout_price = metrics["prior_high"]
    volume_ratio = metrics["volume_ratio"]
    maximum_entry_price = breakout_price * (1 + config["max_chase"])
    conditions = {}
    if config["news_enabled"]:
        conditions["confirmed_positive_event"] = bool(metrics["positive_event_ids"])
    if config["earnings_enabled"]:
        conditions["positive_earnings_report"] = bool(metrics.get("earnings_positive_ids"))
    conditions.update({
        "completed_bar_breakout": float(latest_bar["close"]) > breakout_price,
        "volume_expansion": volume_ratio is not None and volume_ratio >= config["volume_ratio"],
        "spread_acceptable": metrics["spread_ratio"] <= config["max_spread"],
        "entry_quote_still_above_breakout": ask_price > breakout_price,
        "not_chasing_price": ask_price <= maximum_entry_price,
        "risk_budget_available": snapshot.get("risk_budget_available") is True,
    })
    return conditions


def evaluate(snapshot: JsonObject, config: JsonObject | None = None) -> JsonObject:
    """한 종목의 입력을 검사해 BUY / SELL / HOLD / WAIT와 이유를 반환한다.

    아래 단계의 순서가 판단 우선순위다. 손절은 뉴스와 봉 검사보다 먼저 한다.
    잘못된 필수 입력은 WAIT로 반환한다. 주문·체결 상태는 변경하지 않는다.
    """
    settings = load_config(config)
    metrics: JsonObject = {"news_enabled": settings["news_enabled"]}
    checks: list[JsonObject] = []

    def result(action: str, reason: str) -> JsonObject:
        """모든 분기에서 같은 결과 형식을 사용한다. reason은 기계 처리용 고정 코드다."""
        return {
            "market": snapshot.get("market"),
            "symbol": snapshot.get("symbol"),
            "as_of": snapshot.get("now"),
            "action": action,
            "reason": reason,
            "checks": checks,
            "metrics": metrics,
            "mode": "signal_only",
        }

    try:
        # 1. 필수 식별 정보·설정·보유 수량을 확인한다.
        now = parse_timestamp(snapshot["now"])
        if snapshot.get("market") not in {"KR", "US"} or not snapshot.get("symbol"):
            raise ValueError("unsupported market or missing symbol")
        validate_config(settings)
        position = snapshot.get("position")
        quantity = 0.0
        if position:
            quantity = require_number(position["quantity"], allow_zero=True)
        has_position = quantity > 0

        # 2. 미체결 주문이 있으면 추가 신호보다 주문 상태 확인을 우선한다.
        # 정규장 상태는 거래소 캘린더 또는 토스 API 계층에서 제공해야 한다.
        if snapshot.get("pending_order") is True:
            return result("WAIT", "pending_order_requires_reconciliation")
        if snapshot.get("regular_session_open") is not True:
            return result("WAIT", "outside_regular_session")
        quote = snapshot.get("quote")
        if quote is None:
            return result("WAIT", "quote_unavailable")
        quote_age_seconds = (now - parse_timestamp(quote["available_at"])).total_seconds()
        if not 0 <= quote_age_seconds <= settings["max_quote_age_seconds"]:
            return result("WAIT", "stale_or_future_quote")
        bid_price = require_number(quote["bid"])  # 지금 팔 때 상대방이 사겠다는 가격.
        ask_price = require_number(quote["ask"])  # 지금 살 때 상대방이 팔겠다는 가격.
        if bid_price > ask_price:
            raise ValueError("crossed quote")
        mid_price = (bid_price + ask_price) / 2
        metrics["spread_ratio"] = (ask_price - bid_price) / mid_price

        # 3. 보유 중이면 가격 손절부터 확인한다.
        # 뉴스 입력 오류 때문에 유효한 손절 신호가 막히지 않게 한다.
        if has_position:
            average_cost = require_number(position["average_cost"])
            stop_price = average_cost * (1 - settings["stop_loss"])
            metrics["return_at_bid"] = bid_price / average_cost - 1
            if bid_price <= stop_price:
                return result("SELL", "stop_loss")
            # 가격 보호는 뉴스·봉 처리보다 먼저 검사한다. 보조 데이터 오류와 독립적이다.
            peak_bid = require_number(position["peak_bid_since_entry"])
            proceeds_ratio = require_number(position.get("sell_proceeds_ratio", 1 - settings["exit_sell_cost_ratio"]))
            protected = profit_exit_floor(average_cost, peak_bid, proceeds_ratio, settings)
            trailing_stop_price = peak_bid * (1 - settings["trailing_stop"])
            exit_price, exit_reason = trailing_stop_price, "trailing_stop"
            if protected and protected[0] > exit_price:
                exit_price, exit_reason = protected
            metrics["protective_exit_price"] = max(stop_price, exit_price)
            metrics["profit_protection_active"] = protected is not None
            metrics["estimated_net_return"] = bid_price * proceeds_ratio / average_cost - 1
            if bid_price <= exit_price:
                return result("SELL", exit_reason)

        # 4. 확정 악재는 보유 중 매도, 미보유 중 진입 차단으로 처리한다.
        metrics["news_enabled"] = settings["news_enabled"]
        positive_ids, negative_ids = [], []
        if settings["news_enabled"]:
            positive_ids, negative_ids = collect_news_events(snapshot, now, settings)
        metrics["positive_event_ids"] = positive_ids
        metrics["negative_event_ids"] = negative_ids
        if negative_ids:
            if has_position:
                return result("SELL", "confirmed_negative_event")
            return result("WAIT", "negative_event_blocks_entry")

        # 실적 제목 신호는 확정 공시와 별개이며 모의 매매에서만 사용한다.
        if settings["earnings_enabled"]:
            from news.earnings import active_signals, load_policy
            feed_ok = snapshot.get("earnings_feed_ok") is True
            try:
                earnings = active_signals(snapshot, load_policy(), now)
            except (ValueError, TypeError, KeyError, AttributeError, OSError):
                earnings = {"positive": [], "negative": [], "mixed": []}
                feed_ok = False
            metrics.update(earnings_positive_ids=earnings["positive"], earnings_negative_ids=earnings["negative"],
                           earnings_mixed_ids=earnings["mixed"], earnings_feed_ok=feed_ok,
                           earnings_evidence="rss_headline_and_publisher_metadata")
            metrics["earnings_unverified_ids"] = earnings.get("unverified", [])
            if earnings["negative"]:
                return result("SELL" if has_position else "WAIT",
                              "earnings_negative_report" if has_position else "earnings_negative_blocks_entry")
            if not has_position and not feed_ok:
                return result("WAIT", "earnings_feed_unavailable")
            if not has_position and earnings.get("unverified") and not earnings["positive"] and not earnings["negative"]:
                return result("WAIT", "earnings_awaiting_verification")
            if not has_position and earnings["mixed"]:
                return result("WAIT", "earnings_conflict_blocks_entry")

        # 6. 가격 추세와 거래량 계산에는 완성된 연속 봉만 사용한다.
        bars, wait_reason = check_completed_bars(snapshot, now, settings)
        if wait_reason is not None:
            return result("WAIT", wait_reason)
        metrics.update(calculate_bar_metrics(bars))
        latest_bar = bars[-1]

        # 7. 보유 중이면 평균가격 이탈을 검사하고, 나머지는 보유한다.
        if has_position:
            if float(latest_bar["close"]) < metrics["prior_average_close"]:
                return result("SELL", "close_below_prior_average")
            return result("HOLD", "exit_rules_not_triggered")

        # 8. 같은 봉의 반복 진입 신호와 매도 직후 재진입을 막는다.
        if snapshot.get("last_entry_signal_bar") == latest_bar["end"]:
            return result("WAIT", "entry_already_signalled_for_bar")
        last_exit_at = snapshot.get("last_exit_at")
        if last_exit_at:
            elapsed_seconds = (now - parse_timestamp(last_exit_at)).total_seconds()
            if elapsed_seconds < settings["cooldown_minutes"] * 60:
                return result("WAIT", "reentry_cooldown")

        # 9. 매수 조건을 모두 평가하고 각 조건의 통과 여부를 기록한다.
        entry_conditions = build_entry_conditions(snapshot, settings, metrics, latest_bar, ask_price)
        for rule_name, passed in entry_conditions.items():
            checks.append({"rule": rule_name, "passed": passed})
        if all(entry_conditions.values()):
            reason = "positive_event_breakout_with_volume" if settings["news_enabled"] else "price_breakout_with_volume"
            if settings["earnings_enabled"]:
                reason = "earnings_positive_breakout_with_volume"
            return result("BUY", reason)
        return result("WAIT", "entry_conditions_not_met")
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        # 잘못된 입력을 임의 값으로 대체하면 잘못된 매매 신호를 만들 수 있다.
        return result("WAIT", "invalid_input: " + str(error))


def main() -> None:
    """JSON 파일로 한 종목 또는 종목 목록을 평가하는 명령행 진입점."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="시세·봉·뉴스·보유 상태 JSON")
    parser.add_argument("--config", type=Path, help="기본값을 덮어쓸 설정 JSON")
    arguments = parser.parse_args()
    input_data = json.loads(arguments.snapshot.read_text(encoding="utf-8"))
    config = None
    if arguments.config:
        config = json.loads(arguments.config.read_text(encoding="utf-8"))
    snapshots = input_data if isinstance(input_data, list) else [input_data]
    decisions = [evaluate(snapshot, config) for snapshot in snapshots]
    print(json.dumps(decisions, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
