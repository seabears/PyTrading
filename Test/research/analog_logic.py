"""과거 유사 시장의 다음 달 성과로 전략을 고르는 실험 전용 계산.

운용 엔진과 연결하지 않는다. 정규화는 결과가 확인된 과거 사례만 사용한다.
현재 상태의 미래 성과는 선택 함수에 전달하지 않는다.
"""
import math
from statistics import mean, pstdev


STATE_FIELDS = ("return5", "return20", "return60", "distance_ma50", "volatility20",
                "drawdown60", "volume_ratio20", "breadth_ma50")


def market_states(proxy_bars, features):
    """SPY 가격·거래량과 당시 지표 준비가 끝난 종목들의 상승 폭을 표현한다."""
    feature_maps = {symbol: {row["date"]: row for row in rows} for symbol, rows in features.items()}
    states = {}
    for index, bar in enumerate(proxy_bars):
        if index < 200:
            continue
        window = proxy_bars[index - 60:index + 1]
        closes = [row["close"] for row in window]
        volumes = [row["volume"] for row in window[-21:-1]]
        available = [rows[bar["date"]] for rows in feature_maps.values()
                     if bar["date"] in rows and rows[bar["date"]]["count"] >= 201]
        if len(available) < 10 or mean(volumes) <= 0:
            continue
        changes = [closes[position] / closes[position - 1] - 1 for position in range(41, 61)]
        states[bar["date"]] = {
            "date": bar["date"], "return5": closes[-1] / closes[-6] - 1,
            "return20": closes[-1] / closes[-21] - 1,
            "return60": closes[-1] / closes[0] - 1,
            "distance_ma50": closes[-1] / mean(closes[-50:]) - 1,
            "volatility20": pstdev(changes),
            "drawdown60": closes[-1] / max(closes[-60:]) - 1,
            "volume_ratio20": bar["volume"] / mean(volumes),
            "breadth_ma50": mean(row["close"] > row["ma50"] for row in available),
            "breadth_stocks": len(available),
        }
    return states


def mature_cases(cases, decision_date):
    """선행 구간뿐 아니라 이후 성과 관측도 끝난 사례만 허용한다."""
    return [case for case in cases
            if case["anchor_date"] < decision_date and case["outcome_end"] <= decision_date]


def nearest_cases(state, cases, neighbors, maximum_distance):
    """과거 상태만으로 척도를 정한다. 가격 수준 대신 비율을 비교한다."""
    if not cases:
        return []
    scales = {field: max(pstdev(case["state"][field] for case in cases), 1e-8) for field in STATE_FIELDS}
    ranked = []
    for case in cases:
        distance = math.sqrt(mean(((state[field] - case["state"][field]) / scales[field]) ** 2 for field in STATE_FIELDS))
        if distance <= maximum_distance:
            ranked.append({"case": case, "distance": distance, "weight": 1 / (1 + distance)})
    ranked.sort(key=lambda item: (item["distance"], item["case"]["anchor_date"]))
    return ranked[:neighbors]


def choose_strategy(state, cases, decision_date, families, policy, control=None):
    """선정 기준도 고정한다. 기대 수익·낙폭·비용 스트레스가 부족하면 현금이다."""
    history = mature_cases(cases, decision_date)
    trace = {"decision_date": decision_date, "selected": "cash", "history_count": len(history),
             "reason": "insufficient_history", "neighbors": [], "scores": {}}
    if len(history) < policy["minimum_history"]:
        return trace
    if control == "all_history":
        selected_cases = [{"case": case, "distance": None, "weight": 1} for case in history]
    elif control == "recent":
        selected_cases = [{"case": case, "distance": None, "weight": 1} for case in sorted(history, key=lambda item: item["outcome_end"])[-policy["neighbors"]:]]
    else:
        selected_cases = nearest_cases(state, history, policy["neighbors"], policy["maximum_distance"])
    trace["neighbors"] = [{"anchor_date": item["case"]["anchor_date"],
        "outcome_start": item["case"]["outcome_start"], "outcome_end": item["case"]["outcome_end"],
        "distance": item["distance"], "weight": item["weight"]} for item in selected_cases]
    if len(selected_cases) < policy["minimum_neighbors"]:
        trace["reason"] = "insufficient_similar_cases"
        return trace
    total_weight = sum(item["weight"] for item in selected_cases)
    best_score = 0
    for family in families:
        def weighted(field, scenario="base"):
            return sum(item["weight"] * item["case"]["outcomes"][family][scenario][field]
                       for item in selected_cases) / total_weight
        net = weighted("net_return")
        stress = weighted("net_return", "double_cost")
        drawdown = weighted("max_drawdown")
        positive_fraction = sum(item["case"]["outcomes"][family]["base"]["net_return"] > 0 for item in selected_cases) / len(selected_cases)
        score = net - policy["drawdown_penalty"] * drawdown
        eligible = (net > 0 and stress > 0 and score > 0 and
                    positive_fraction >= policy["minimum_positive_fraction"])
        trace["scores"][family] = {"net_mean": net, "stress_mean": stress, "drawdown_mean": drawdown,
                                  "positive_fraction": positive_fraction, "score": score, "eligible": eligible}
        if eligible and score > best_score:
            best_score, trace["selected"] = score, family
    trace["reason"] = "selected" if trace["selected"] != "cash" else "no_eligible_strategy"
    return trace
