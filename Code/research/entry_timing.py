"""동일 돌파 신호에서 진입 시점만 비교한다. 계좌 수익률을 계산하지 않는다.

판단 함수는 신호 뒤 완성된 봉과 주문 시가까지만 읽는다. 미래 봉은 성과 측정에만
사용한다. 미체결을 지우면 유리한 거래만 남으므로 현금 대기 결과도 함께 보존한다.
"""
from collections import Counter
from statistics import mean, median

from research.backtest import execution_price


def entry_decision(bars, anchor, mode, step, max_wait, gap_limit):
    """반환값: 진입 인덱스 또는 None, 사유. step은 일봉 1, 분봉 5다."""
    i, level = anchor["index"], anchor["level"]
    kind = mode["kind"]
    if kind == "volume" and anchor["volume_ratio"] < mode["minimum"]:
        return None, "volume_filter"
    wait = mode.get("wait", 0)
    decision = i
    if kind in {"delay", "confirm", "retest"}:
        for offset in range(step, wait + 1, step):
            decision = i + offset
            if decision >= len(bars) or bars[decision] is None:
                return None, "missing_decision_bar"
            bar = bars[decision]
            if bar["close"] < level:
                return None, "breakout_invalidated"
            if kind == "retest":
                # 체결됐다는 가정이 아니다. 지지를 확인한 뒤 다음 시가에 주문한다.
                block = bars[decision - step + 1:decision + 1]
                if any(row is None for row in block):
                    return None, "missing_decision_bar"
                touched = min(row["low"] for row in block) <= level + anchor["atr"] * .25
                if touched and bar["close"] <= bars[i]["close"]:
                    break
        else:
            if kind == "retest":
                return None, "retest_not_seen"
        if kind == "confirm" and bars[decision]["close"] < bars[i]["close"]:
            return None, "confirmation_failed"
    if decision - i > max_wait:
        raise ValueError("선언한 대기 기간을 초과했습니다.")
    entry = decision + 1
    if entry >= len(bars) or bars[entry] is None:
        return None, "missing_entry_bar"
    # 현재 봉의 고가·저가·종가·거래량은 주문 판단에 사용하지 않는다.
    opening = bars[entry]["open"]
    if opening < level:
        return None, "open_below_breakout"
    if opening / bars[decision]["close"] - 1 > mode.get("gap_limit", gap_limit):
        return None, "gap_limit"
    return entry, "filled"


def net_return(opening, closing, costs, spread, multiplier=1):
    """매수 원가와 매도 순수입의 비율. 비용 스트레스는 네 비율 모두 배수 적용."""
    adjusted = {key: value * multiplier for key, value in costs.items()}
    buy = execution_price(opening, "BUY", adjusted, spread * multiplier)
    sell = execution_price(closing, "SELL", adjusted, spread * multiplier)
    return sell * (1 - adjusted["sell_cost_ratio"]) / (buy * (1 + adjusted["buy_cost_ratio"])) - 1


def measure_event(bars, anchor, modes, horizons, step, max_wait, gap_limit, costs, spread):
    """이미 성숙·연속성을 확인한 공통 사건에 모든 조건을 적용한다.

    common: 즉시 진입 기준의 같은 날짜/시각에 매도해 진입 차이를 분리한다.
    holding: 진입 후 같은 봉 수를 보유한다. 매도 시점도 달라지는 보조 지표다.
    """
    rows = []
    for mode in modes:
        entry, reason = entry_decision(bars, anchor, mode, step, max_wait, gap_limit)
        for horizon in horizons:
            endpoint = anchor["index"] + horizon
            active = entry is not None and entry <= endpoint
            row = {key: anchor[key] for key in ("symbol", "date", "stage", "time_bucket", "event_id")}
            row.update(mode=mode["name"], horizon=horizon, reason=reason if not entry or active else "after_common_exit",
                       entry_index=entry, signal_index=anchor["index"], common_exit_index=endpoint,
                       entry_reference=None, common_exit_reference=bars[endpoint]["close"],
                       common_gross=None, common_net=None, common_double=None, holding_net=None, mae=None, mfe=None)
            if entry is not None:
                opening = bars[entry]["open"]
                row["entry_reference"] = opening
                row["holding_net"] = net_return(opening, bars[entry + horizon - 1]["close"], costs, spread)
                if active:
                    row["common_gross"] = bars[endpoint]["close"] / opening - 1
                    row["common_net"] = net_return(opening, bars[endpoint]["close"], costs, spread)
                    row["common_double"] = net_return(opening, bars[endpoint]["close"], costs, spread, 2)
                    window = bars[entry:endpoint + 1]
                    row["mae"] = min(0, min(bar["low"] for bar in window) / opening - 1)
                    row["mfe"] = max(0, max(bar["high"] for bar in window) / opening - 1)
            rows.append(row)
    return rows


def study_series(bars, anchors, modes, horizons, step, max_wait, gap_limit, costs, spread):
    """같은 종목의 관측 창을 겹치지 않는다. 미성숙·누락·기간 경계는 별도로 기록한다."""
    # 계산 함수는 공유하지만 일봉과 분봉의 사건은 따로 분석한다.
    audit, results = [], []
    blocked_until = -1
    span = max_wait + max(horizons)
    for anchor in anchors:
        i = anchor["index"]
        status = "accepted"
        if i <= blocked_until:
            status = "overlap_skipped"
        else:
            # 이후 자료의 유무나 손익과 무관하게 첫 신호를 선택한다.
            blocked_until = i + span
            if i + span >= len(bars):
                status = "right_censored"
            elif any(bar is None for bar in bars[i:i + span + 1]):
                status = "data_gap"
            elif bars[i + span]["date"] > anchor["period_end"]:
                status = "period_boundary"
        audit.append({**anchor, "status": status})
        if status == "accepted":
            results.extend(measure_event(bars, anchor, modes, horizons, step, max_wait, gap_limit, costs, spread))
    return results, audit


def summarize(rows, baseline):
    """미체결은 사건당 수익 0. 같은 사건의 기준 진입과 짝지어 비교한다."""
    base = {(row["event_id"], row["horizon"]): row for row in rows if row["mode"] == baseline}
    groups = {}
    for row in rows:
        groups.setdefault((row["mode"], row["horizon"]), []).append(row)
    output = []
    for (mode, horizon), members in groups.items():
        filled = [row for row in members if row["common_net"] is not None]
        paired = [(row, base[(row["event_id"], horizon)]) for row in filled
                  if base[(row["event_id"], horizon)]["common_net"] is not None]
        values = [row["common_net"] for row in filled]
        output.append({"mode": mode, "horizon": horizon, "events": len(members), "fills": len(filled),
            "fill_rate": len(filled) / len(members), "mean_filled": mean(values) if values else None,
            "mean_gross_filled": mean(row["common_gross"] for row in filled) if filled else None,
            "median_filled": median(values) if values else None,
            "win_rate": mean(value > 0 for value in values) if values else None,
            "mean_all": mean(row["common_net"] or 0 for row in members),
            "mean_all_double": mean(row["common_double"] or 0 for row in members),
            "paired_count": len(paired),
            "paired_delta": mean(row["common_net"] - ref["common_net"] for row, ref in paired) if paired else None,
            "opportunity_delta": mean((row["common_net"] or 0) - (base[(row["event_id"], horizon)]["common_net"] or 0) for row in members),
            "mean_mae": mean(row["mae"] for row in filled) if filled else None,
            "worst_mae": min((row["mae"] for row in filled), default=None),
            "mean_holding": mean(row["holding_net"] for row in members if row["holding_net"] is not None) if any(row["holding_net"] is not None for row in members) else None,
            "reasons": dict(Counter(row["reason"] for row in members))})
    return output
