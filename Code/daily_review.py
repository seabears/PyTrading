"""실제 일봉 관측 원장을 읽기 전용으로 평가한다. 과거 호가·미관측 성과는 생성하지 않는다."""

from contextlib import closing
import argparse
import json
import sqlite3
from pathlib import Path
from datetime import timedelta
from collections import Counter

from broker.sessions import calendar_for
from strategy.engine import parse_timestamp
from trading.risk_ledger import digest
from app.stateio import atomic_json


def review_observations(folder):
    path = Path(folder) / "observation-ledger.sqlite"
    days, plans, coverage, versions, fills = {}, {}, {}, [], {}
    heartbeats = []
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.execute("BEGIN")
        events = connection.execute("SELECT day,kind,at,body FROM events ORDER BY at,id").fetchall()
        summaries = {
            day: json.loads(body) for day, body in connection.execute("SELECT day,body FROM days")
        }
    for day, kind, stamp, body in events:
        payload = json.loads(body)
        row = days.setdefault(
            day,
            {
                "phases": Counter(),
                "reasons": Counter(),
                "normal_quotes": 0,
                "first_normal": None,
                "last_normal": None,
                "open_window_symbols": set(),
                "prepared_plans": [],
                "fills": 0,
                "controls": [],
                "process_starts": 0,
                "buy_halted_observations": 0,
            },
        )
        at = parse_timestamp(stamp)
        if kind == "heartbeat":
            heartbeats.append(at)
        elif kind == "startup":
            row["process_starts"] += 1
            versions.append({"at": stamp, "versions": payload.get("versions", {})})
            for plan in payload.get("restored_plans", []):
                plans.setdefault(
                    plan["id"], {"plan": plan, "first_recorded_at": stamp, "restored": True}
                )
        elif kind == "plan":
            coverage.update(payload.get("coverage", {}))
            for plan in payload["plans"]:
                plans.setdefault(
                    plan["id"], {"plan": plan, "first_recorded_at": stamp, "restored": False}
                )
        elif kind == "control":
            row["controls"].append({"at": stamp, **payload})
        elif kind == "fill_recovery":
            fills[digest(payload["fill"])] = payload["fill"]
        elif kind == "observation":
            if payload.get("input_kind") != "live_observation":
                continue
            schedule = calendar_for("US", at.year).schedule
            if day not in schedule.index.strftime("%Y-%m-%d"):
                phase = "non_trading_day"
                session = None
            else:
                session = schedule.loc[day]
                phase = (
                    "premarket"
                    if at < session["open"]
                    else "postmarket" if at >= session["close"] else "regular"
                )
            row["phases"][phase] += 1
            age = payload.get("quote_age_seconds")
            normal = (
                phase == "regular"
                and not payload.get("lookup_error")
                and age is not None
                and 0 <= age <= 30
            )
            if normal:
                row["normal_quotes"] += 1
                row["first_normal"] = row["first_normal"] or stamp
                row["last_normal"] = stamp
                if at <= session["open"] + timedelta(minutes=5):
                    row["open_window_symbols"].add(payload["symbol"])
            if payload.get("buy_halts") or payload.get("manual_buy_pause"):
                row["buy_halted_observations"] += 1
            reason = payload["reason"]
            if reason == "no_daily_plan":
                ready = coverage.get("US:" + payload["symbol"], {}).get("indicator_ready")
                reason = (
                    "data_not_ready"
                    if ready is False
                    else "no_entry_signal" if ready is True else "no_plan_readiness_unknown"
                )
            row["reasons"][reason] += 1
            if payload.get("fill"):
                fills[digest(payload["fill"])] = payload["fill"]
    for identifier, detail in plans.items():
        plan = detail["plan"]
        execution_day = plan["execution_day"]
        schedule = calendar_for("US", int(execution_day[:4])).schedule
        opening = schedule.loc[execution_day]["open"]
        detail["prepared_before_open"] = parse_timestamp(detail["first_recorded_at"]) < opening
        if execution_day in days:
            days[execution_day]["prepared_plans"].append({"id": identifier, **detail})
    for day, row in days.items():
        row["phases"] = dict(row["phases"])
        row["reasons"] = dict(row["reasons"])
        row["open_window_symbols"] = sorted(row["open_window_symbols"])
        row["fills"] = sum(
            parse_timestamp(fill["at"])
            .astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
            .date()
            .isoformat()
            == day
            for fill in fills.values()
        )
        summary = summaries.get(day, {})
        row["stale_quotes"] = summary.get("stale_quotes", 0)
        row["lookup_errors"] = summary.get("lookup_errors", 0)
        row["quote_gaps"] = summary.get("quote_gaps", 0)
    actual_days = sum(row["normal_quotes"] > 0 for row in days.values())
    closed = [fill for fill in fills.values() if fill["action"] == "SELL"]
    return {
        "data_kind": "actual_observation_ledger",
        "status": "관측 진행 중",
        "observed_trading_days": actual_days,
        "virtual_fills": len(fills),
        "closed_trades": len(closed),
        "minimum_days_met": actual_days >= 20,
        "minimum_closed_trades_met": len(closed) >= 30,
        "days": days,
        "heartbeat_gaps_over_300_seconds": [
            {
                "from": first.isoformat(),
                "to": second.isoformat(),
                "seconds": (second - first).total_seconds(),
            }
            for first, second in zip(heartbeats, heartbeats[1:])
            if (second - first).total_seconds() > 300
        ],
        "code_and_setting_versions": versions,
        "first_virtual_buy": next(
            (
                fill
                for fill in sorted(fills.values(), key=lambda item: item["at"])
                if fill["action"] == "BUY"
            ),
            None,
        ),
        "limitations": [
            "관측 거래일 수는 정규장 전 구간 관측을 뜻하지 않음",
            "정규장 밖 호가를 수집하지 않는 현 프로필의 정상 동작과 장전/장후 프로세스 관측을 구분",
            "매수 전에는 보유·손절·청산 경로의 실제 관측을 검증할 수 없음",
            "heartbeat 공백은 누락 가능 구간이며 그 사이 가동을 보장하지 않음",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = review_observations(arguments.folder)
    atomic_json(arguments.output, result)
    print(
        "실제 관측 거래일:",
        result["observed_trading_days"],
        "/ 가상 체결:",
        result["virtual_fills"],
    )
    print("상태:", result["status"])


if __name__ == "__main__":
    main()
