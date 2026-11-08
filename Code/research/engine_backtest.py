"""현재 운용 중인 판단·모의 계좌를 과거 분봉으로 재생한다.

매수·매도 규칙을 여기에 복사하지 않는다. PaperAccount.evaluate_snapshot을 그대로
호출하며, 메모리 계좌는 반복 파일 저장만 생략한다. 실제 호가 이력이 없으므로
각 분 시작 가격에 가정 스프레드를 붙인다. 현재 분의 고가·저가·종가는 보지 않는다.
"""
from __future__ import annotations

import copy
import heapq
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from broker.sessions import calendar_for
from broker.toss import aggregate_five_minute_bars
from strategy.engine import load_config, parse_timestamp, require_number, validate_config
from trading.paper import PaperAccount


class ReplayAccount(PaperAccount):
    """신호·체결·현금 관리는 부모와 동일하고 연구 중 디스크 저장만 생략한다."""

    def __init__(self, settings):
        # 새 임시 폴더의 존재하지 않는 파일을 지정해 부모의 검증·초기화를 재사용한다.
        # save()가 비어 있으므로 임시 폴더나 운용 계좌에 거래 파일을 쓰지 않는다.
        with TemporaryDirectory(prefix="pytrading-replay-") as directory:
            super().__init__(Path(directory) / "account.json", settings)

    def save(self):
        """최종 결과는 호출자가 별도 연구 폴더에 한 번 저장한다."""


def prepare_record(record):
    """거래소 달력으로 정규장만 추리고, 실제 수집기와 같은 함수로 5분봉을 만든다."""
    market = record["market"]
    zone = ZoneInfo("America/New_York" if market == "US" else "Asia/Seoul")
    by_day = defaultdict(list)
    seen = set()
    for candle in record["candles"]:
        ending = parse_timestamp(candle["timestamp"]).astimezone(timezone.utc)
        if ending in seen:
            raise ValueError("중복 분봉은 재생할 수 없습니다.")
        seen.add(ending)
        if ending.second or ending.microsecond:
            raise ValueError("분봉은 정확한 분 경계여야 합니다.")
        high = require_number(candle["highPrice"])
        low = require_number(candle["lowPrice"])
        if not low <= require_number(candle["openPrice"]) <= high or not low <= require_number(candle["closePrice"]) <= high:
            raise ValueError("잘못된 OHLC 범위입니다.")
        require_number(candle["volume"], allow_zero=True)
        day = (ending - timedelta(minutes=1)).astimezone(zone).date().isoformat()
        by_day[day].append((ending, candle))
    sessions = []
    for day, members in sorted(by_day.items()):
        calendar = calendar_for(market, int(day[:4]))
        if day not in calendar.schedule.index:
            continue
        row = calendar.schedule.loc[day]
        opening = row["open"].to_pydatetime()
        closing = row["close"].to_pydatetime()
        if market == "KR":
            closing -= timedelta(minutes=10)
        session = {"start": opening, "end": closing, "id": market + ":" + day}
        selected = [(ending, candle) for ending, candle in sorted(members)
                    if opening < ending <= closing]
        if not selected:
            continue
        bars = aggregate_five_minute_bars([candle for _, candle in selected], session, closing)
        # 과거 재생에서는 지연 없이 봉 종료 시각에 데이터가 도착한다고 가정한다.
        for bar in bars:
            bar["available_at"] = bar["end"]
        sessions.append({**session, "day": day, "minutes": selected, "bars": bars,
                         "expected_minutes": int((closing - opening).total_seconds() / 60)})
    if not sessions:
        raise ValueError("정규장 분봉이 없습니다.")
    return sessions


def snapshots(sessions, market, symbol, spread_ratio, strategy, start, end):
    """t에 끝난 봉까지만 제공하고 [t,t+1분]의 시가로 t의 가상 호가를 만든다.

    완성 봉은 미리 집계하지만 end<=t인 봉만 노출한다. 현재 분의 나머지 OHLCV는
    다음 시각 전까지 판단에 들어가지 않는다. 누락 분·장외·다음 날 봉을 채우지 않는다.
    """
    for session in sessions:
        if not start <= session["day"] <= end:
            continue
        bars, cursor = session["bars"], 0
        ends = [parse_timestamp(bar["end"]) for bar in bars]
        for ending, candle in session["minutes"]:
            now = ending - timedelta(minutes=1)
            while cursor < len(bars) and ends[cursor] <= now:
                cursor += 1
            mid = float(candle["openPrice"])
            stamp = now.isoformat()
            yield now, {
                "market": market, "symbol": symbol, "now": stamp,
                "session_id": session["id"], "regular_session_open": True,
                "pending_order": False, "position": None, "news_events": [],
                "bars": bars[max(0, cursor - strategy["lookback"] - 1):cursor],
                "quote": {"available_at": stamp, "bid": mid * (1 - spread_ratio / 2),
                          "ask": mid * (1 + spread_ratio / 2)},
            }


def replay(prepared, symbols, strategy_overrides, paper_settings, spread_ratio, start, end,
           capture_decisions=False, progress=None):
    """종목별 독립 자금이 아닌, 운용 설정 순서의 공동 계좌 하나로 재생한다."""
    strategy = load_config(strategy_overrides)
    validate_config(strategy)
    if any(market != "US" for market, symbol in symbols) or len(set(symbols)) != len(symbols):
        raise ValueError("이번 공동 USD 계좌 연구는 중복 없는 미국 종목만 지원합니다.")
    if strategy["news_enabled"] or strategy["earnings_enabled"]:
        raise ValueError("과거 수신 뉴스 이력이 없어 뉴스 사용 전략은 재생하지 않습니다.")
    if strategy["bar_minutes"] != 5:
        raise ValueError("실제 수집기와 같은 5분봉만 지원합니다.")
    if not 0 <= require_number(spread_ratio, allow_zero=True) < 1:
        raise ValueError("가정 스프레드는 0 이상 1 미만이어야 합니다.")
    account = ReplayAccount(paper_settings)
    streams = []
    for index, (market, symbol) in enumerate(symbols):
        # 같은 시각에는 실제 설정의 종목 순서를 유지한다. 현금 경쟁도 재현한다.
        # 제너레이터 안의 index가 다음 반복에서 바뀌지 않게 별도 함수로 고정한다.
        streams.append(ordered_stream(index, snapshots(prepared[market + ":" + symbol],
            market, symbol, spread_ratio, strategy, start, end)))
    reasons, failures, symbol_reasons = Counter(), Counter(), defaultdict(Counter)
    curve, decisions = [], []
    entries, closed = {}, []
    last_time = None
    maximum_positions = 0
    processed = 0
    current_day = None
    initial = paper_settings["starting_cash"]["US"]
    for now, index, snapshot in heapq.merge(*streams):
        # 앞 시각의 모든 종목을 처리한 뒤 공동 계좌를 평가한다.
        if last_time is not None and now != last_time:
            curve.append(valuation(account, last_time, initial))
        last_time = now
        day = snapshot["session_id"].split(":", 1)[1]
        if day != current_day:
            current_day = day
            if progress:
                progress(day)
        decision = account.evaluate_snapshot(snapshot, strategy_overrides)
        processed += 1
        key = snapshot["market"] + ":" + snapshot["symbol"]
        reasons[decision["reason"]] += 1
        symbol_reasons[key][decision["reason"]] += 1
        for check in decision.get("checks", []):
            if not check["passed"]:
                failures[check["rule"]] += 1
        if capture_decisions:
            decisions.append(copy.deepcopy(decision))
        trade = decision.get("paper_fill")
        if trade:
            mid = (snapshot["quote"]["ask"] + snapshot["quote"]["bid"]) / 2
            reference = {**trade, "reference_mid": mid, "reference_bid": snapshot["quote"]["bid"],
                         "reference_ask": snapshot["quote"]["ask"]}
            if trade["action"] == "BUY":
                entries[key] = reference
            else:
                entry = entries.pop(key)
                quantity = trade["quantity"]
                gross = quantity * (mid - entry["reference_mid"])
                spread_cost = quantity * (entry["reference_ask"] - entry["reference_mid"]
                                         + mid - reference["reference_bid"])
                slippage = quantity * (entry["price"] - entry["reference_ask"]
                                       + reference["reference_bid"] - reference["price"])
                fees = entry["fees"] + reference["fees"]
                closed.append({"symbol": key, "entry": entry, "exit": reference,
                               "gross_mid_pnl": gross, "spread_cost": spread_cost,
                               "slippage_cost": slippage, "fees": fees,
                               "net_pnl": trade["realized_pnl"],
                               "holding_minutes": (now - parse_timestamp(entry["at"])).total_seconds() / 60})
        maximum_positions = max(maximum_positions, len(account.state["positions"]))
    if last_time is not None:
        curve.append(valuation(account, last_time, initial))
    if not curve:
        raise ValueError("선택 기간에 재생할 데이터가 없습니다.")
    summary = summarize(curve, closed, initial)
    summary.update(processed_snapshots=processed, maximum_positions=maximum_positions,
                   open_positions=len(account.state["positions"]))
    return {"summary": summary, "curve": curve, "closed_trades": closed,
            "open_entries": entries, "state": account.state, "reasons": dict(reasons),
            "failed_checks": dict(failures), "symbol_reasons": dict(symbol_reasons),
            "decisions": decisions}


def ordered_stream(index, stream):
    for now, snapshot in stream:
        yield now, index, snapshot


def valuation(account, now, initial):
    """운용 평가와 전량 매도 비용을 가정한 평가를 구분한다. 실제 청산은 하지 않는다."""
    summary = account.summary()["US"]
    marked = summary["equity_at_last_quote"] - summary["cash"]
    proceeds_ratio = ((1 - account.settings["slippage_ratio"])
                      * (1 - account.settings["sell_cost_ratio"]))
    return {"at": now.isoformat(), "equity": summary["equity_at_last_quote"],
            "net_liquidation_equity": summary["cash"] + marked * proceeds_ratio,
            "cash": summary["cash"], "exposure": marked / initial,
            "positions": summary["position_count"]}


def summarize(curve, closed, initial):
    """분 단위 평가의 최대 낙폭과 일별 평가액을 집계한다."""
    peak, maximum_drawdown = initial, 0
    daily = {}
    for point in curve:
        equity = point["net_liquidation_equity"]
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, 1 - equity / peak)
        day = parse_timestamp(point["at"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
        daily[day] = equity
    # 짧은 기간의 연율 환산은 오해를 줄 수 있어 연환산 수익률·Sharpe는 표시하지 않는다.
    profits = [trade["net_pnl"] for trade in closed]
    gain = sum(value for value in profits if value > 0)
    loss = -sum(value for value in profits if value < 0)
    return {"net_return": curve[-1]["net_liquidation_equity"] / initial - 1,
            "final_equity": curve[-1]["net_liquidation_equity"],
            "marked_return": curve[-1]["equity"] / initial - 1,
            "max_drawdown": maximum_drawdown, "closed_trades": len(closed),
            "win_rate": sum(value > 0 for value in profits) / len(profits) if profits else None,
            "profit_factor": gain / loss if loss else None,
            "realized_pnl": sum(profits), "gross_mid_pnl": sum(t["gross_mid_pnl"] for t in closed),
            "spread_cost": sum(t["spread_cost"] for t in closed),
            "slippage_cost": sum(t["slippage_cost"] for t in closed),
            "fees": sum(t["fees"] for t in closed), "sessions": len(daily),
            "average_exposure": sum(p["exposure"] for p in curve) / len(curve),
            "daily_equity": daily}
