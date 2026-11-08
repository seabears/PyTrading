"""회전 로그와 독립된 일봉 관측 근거. 프로세스 진행과 정상 정규장 시세를 구분한다."""

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.stateio import atomic_json
from strategy.engine import parse_timestamp


class ObservationJournal:
    def __init__(self, folder, input_kind="live_observation"):
        self.folder = folder
        self.input_kind = input_kind
        folder.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(folder / "observation-ledger.sqlite", timeout=5)
        try:
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,day TEXT,kind TEXT,at TEXT,body TEXT)"
            )
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS days(day TEXT PRIMARY KEY,body TEXT)"
            )
            self.connection.execute("CREATE INDEX IF NOT EXISTS event_day ON events(day)")
        except Exception:
            self.connection.close()
            raise
        self.process_id = uuid.uuid4().hex

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.connection.close()

    def record(self, kind, payload, at=None, event_id=None, accounting_day=None):
        """실제 입력 하나와 일별 집계를 같은 트랜잭션으로 저장한다. event_id 중복은 무시한다."""
        at = at or datetime.now(timezone.utc).isoformat()
        moment = parse_timestamp(at)
        day = moment.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        day = accounting_day or day
        event_id = event_id or uuid.uuid4().hex
        with self.connection:
            cursor = self.connection.execute(
                "INSERT OR IGNORE INTO events VALUES(?,?,?,?,?)",
                (event_id, day, kind, at, json.dumps(payload, ensure_ascii=False, allow_nan=False)),
            )
            if not cursor.rowcount:
                return False
            saved = self.connection.execute("SELECT body FROM days WHERE day=?", (day,)).fetchone()
            row = (
                json.loads(saved[0])
                if saved
                else {
                    "day": day,
                    "status": "관측 진행 중",
                    "process_events": 0,
                    "regular_attempts": 0,
                    "normal_quotes": 0,
                    "lookup_errors": 0,
                    "missing_quotes": 0,
                    "stale_quotes": 0,
                    "quote_gaps": 0,
                    "maximum_quote_age_seconds": None,
                    "reasons": {},
                    "controls": [],
                    "plans": {},
                    "fills": {},
                    "process_spans": {},
                    "last_quotes": {},
                    "observed_process_seconds": 0,
                    "last_process_progress_at": None,
                    "valuation_count": 0,
                    "observed_mdd": None,
                    "last_valid_valuation": None,
                    "input_kind": self.input_kind,
                }
            )
            if kind != "fill_recovery":
                row["last_process_progress_at"] = at
                row["process_events"] += 1
            if kind == "heartbeat":
                previous = row["process_spans"].get(self.process_id)
                if previous:
                    elapsed = (moment - parse_timestamp(previous)).total_seconds()
                    if 0 <= elapsed <= 300:
                        row["observed_process_seconds"] += elapsed
                row["process_spans"][self.process_id] = at
            elif kind == "startup":
                row.setdefault("starts", []).append(
                    {"at": at, "restored_plans": payload.get("restored_plans", [])}
                )
                row["versions"] = payload["versions"]
                row["settings_snapshot"] = payload.get("settings_snapshot")
            elif kind == "plan":
                row["plans"].update({plan["id"]: plan for plan in payload["plans"]})
                row.setdefault("signal_evidence", []).append(payload)
            elif kind == "fill_recovery":
                row["fills"][payload["trade_hash"]] = payload["fill"]
                row.setdefault("fill_recovery_evidence", []).append(
                    {"recovered_at": at, "trade_at": payload["fill"]["at"]}
                )
            elif kind == "control":
                row["controls"].append({"at": at, **payload})
            elif kind == "observation":
                row['execution_mode']=payload.get('execution_mode','internal_paper')
                broker_orders=row.setdefault('broker_confirmed_orders',{})
                for order in payload.get('broker_confirmed_orders',[]):
                    broker_orders[order['id']]={**order,'observed_at':payload.get('broker_observed_at')}
                reason = payload["reason"]
                row["reasons"][reason] = row["reasons"].get(reason, 0) + 1
                regular = (
                    payload["regular_session_open"] and payload["input_kind"] == "live_observation"
                )
                if regular:
                    row["regular_attempts"] += 1
                    age = payload.get("quote_age_seconds")
                    if payload.get("lookup_error"):
                        row["lookup_errors"] += 1
                    elif age is None:
                        row["missing_quotes"] += 1
                    elif not 0 <= age <= 30:
                        row["stale_quotes"] += 1
                    else:
                        row["normal_quotes"] += 1
                        row.setdefault("first_normal_quote_at", at)
                        row["last_normal_quote_at"] = at
                        previous = row["last_quotes"].get(payload["symbol"])
                        if previous and (moment - parse_timestamp(previous)).total_seconds() > 180:
                            row["quote_gaps"] += 1
                        row["last_quotes"][payload["symbol"]] = at
                    if age is not None:
                        row["maximum_quote_age_seconds"] = max(
                            age, row["maximum_quote_age_seconds"] or 0
                        )
                if payload.get("valuation") is not None and regular:
                    valuation = payload["valuation"]
                    value = valuation["net_liquidation_equity"]
                    row["valuation_count"] += 1
                    row.setdefault("first_observed_equity", value)
                    row["observed_peak"] = max(row.get("observed_peak", value), value)
                    row["observed_mdd"] = (
                        max(row["observed_mdd"] or 0, 1 - value / row["observed_peak"])
                        if row["observed_peak"] > 0
                        else None
                    )
                    row["last_valid_valuation"] = {"at": at, **valuation}
                row["latest_valuation_available"] = payload.get("valuation") is not None and regular
                row["cash"] = payload["cash"]
                row["positions"] = payload["positions"]
                row["pending_plans"] = payload["pending_plans"]
                row["buy_halts"] = payload["buy_halts"]
                row["manual_buy_pause"] = payload["manual_buy_pause"]
                row.setdefault("plan_outcomes", {}).update(
                    {identifier: reason for identifier in payload["affected_plans"]}
                )
                if payload.get("fill"):
                    fill = payload["fill"]
                    identifier = hashlib.sha256(
                        json.dumps(fill, sort_keys=True).encode()
                    ).hexdigest()
                    row["fills"][identifier] = fill
            self.connection.execute(
                "INSERT OR REPLACE INTO days VALUES(?,?)",
                (day, json.dumps(row, ensure_ascii=False, allow_nan=False)),
            )
        self.render(day, row)
        return True

    def observe(self, snapshot, decision, account, monitor, affected_plans=(), lookup_error=False):
        """정규장 신선도와 보유 시세를 검사하고 정상 평가가 있을 때만 성과를 남긴다."""
        at = snapshot["now"]
        broker_mode=getattr(account,'execution_mode','internal_paper')!='internal_paper'
        now = parse_timestamp(at)
        quote = snapshot.get("quote")
        age = (now - parse_timestamp(quote["available_at"])).total_seconds() if quote else None
        valuation = None
        if (
            not broker_mode
            and not lookup_error
            and snapshot.get("regular_session_open")
            and age is not None
            and 0 <= age <= 30
        ):
            fresh = all(
                key in account.state.get("quote_times", {})
                and 0
                <= (now - parse_timestamp(account.state["quote_times"][key])).total_seconds()
                <= 180
                for key in account.state["positions"]
            )
            if fresh:
                from trading.safety import equity

                marked = sum(
                    position["quantity"] * account.state["last_prices"][key]
                    for key, position in account.state["positions"].items()
                )
                cost = sum(
                    position["cost_basis"] for position in account.state["positions"].values()
                )
                day = now.astimezone(ZoneInfo("America/New_York")).date().isoformat()
                trades = [
                    trade
                    for trade in account.state["trades"]
                    if parse_timestamp(trade["at"])
                    .astimezone(ZoneInfo("America/New_York"))
                    .date()
                    .isoformat()
                    == day
                ]
                valuation = {
                    "net_liquidation_equity": equity(account.state, "US", account.settings),
                    "cash": None if broker_mode else account.state["cash"]["US"],
                    "marked_positions": marked,
                    "unrealized_pnl_before_exit_cost": marked - cost,
                    "fees": sum(trade["fees"] for trade in trades),
                    "realized_pnl": sum(trade.get("realized_pnl", 0) for trade in trades),
                    "cost_basis_exposure": cost / account.settings["starting_cash"]["US"],
                }
        if broker_mode:valuation=None
        payload = {
            'execution_mode':getattr(account,'execution_mode','internal_paper'),
            'broker_confirmed_orders':account.state.get('broker_confirmed_fills',[]),
            'broker_observed_at':account.state.get('broker_readiness',{}).get('as_of'),
            "symbol": snapshot["symbol"],
            "input_kind": snapshot.get("data_mode", self.input_kind),
            "regular_session_open": snapshot.get("regular_session_open", False),
            "quote": quote,
            "quote_age_seconds": age,
            "request_seconds": snapshot.get("request_seconds", monitor.state.get("last_request_seconds") if not lookup_error else None),
            "timings": snapshot.get("timings"),
            "error": snapshot.get("error"),
            "lookup_error": lookup_error,
            "reason": decision["reason"],
            "action": decision["action"],
            "affected_plans": list(affected_plans),
            "pending_plans": account.state["pending_daily"],
            "cash": None if broker_mode else account.state["cash"]["US"],
            "positions": account.state["positions"],
            "valuation": valuation,
            "fill": decision.get("paper_fill"),
            "buy_halts": monitor.state["buy_halts"],
            "manual_buy_pause": (self.folder / "PAUSE_BUYS").exists(),
        }
        identifier = hashlib.sha256(
            ("observation:" + at + ":" + snapshot["symbol"]).encode()
        ).hexdigest()
        self.record("observation", payload, at, identifier)

    def recover_fills(self, account):
        """권위 계좌에 이미 기록된 실제 관측 체결만 복구한다. 시세·성과 구간은 만들지 않는다."""
        for trade in account.state["trades"]:
            if trade.get("data_mode") != "live_observation":
                continue
            day = (
                parse_timestamp(trade["at"])
                .astimezone(ZoneInfo("America/New_York"))
                .date()
                .isoformat()
            )
            identifier = hashlib.sha256(json.dumps(trade, sort_keys=True).encode()).hexdigest()
            saved = self.connection.execute("SELECT body FROM days WHERE day=?", (day,)).fetchone()
            if saved and identifier in json.loads(saved[0])["fills"]:
                continue
            self.record(
                "fill_recovery",
                {"trade_hash": identifier, "fill": trade},
                event_id="fill-recovery:" + identifier,
                accounting_day=day,
            )

    def render(self, day, row):
        """원장 집계에서 사용자가 확인할 JSON·Markdown을 만든다. 과거 호가를 생성하지 않는다."""
        destination = self.folder / "daily"
        destination.mkdir(exist_ok=True)
        atomic_json(destination / ("US-" + day + ".json"), row)
        lines = [
            f"# {day} 고정 일봉 "+{'internal_paper':'내부 모의','kis_demo':'KIS 모의 전략','disabled':'관측 전용'}.get(row.get('execution_mode','internal_paper'),'체결 경로 확인 필요')+" 관측",
            "",
            "상태: 관측 진행 중. 20거래일·거래 표본·수익성 조건 충족을 의미하지 않는다.",
            "프로세스 진행 시간과 실제 정상 정규장 관측은 별개다. 미관측 구간을 가동·무손실로 채우지 않는다.",
            "",
            f"- 마지막 프로세스 진행: {row['last_process_progress_at']}",
            f"- 확인된 짧은 heartbeat 구간 합계: {row['observed_process_seconds']:.1f}초 (300초 초과 구간 제외)",
            f"- 정상 정규장 호가 {row['normal_quotes']} / 정규장 시도 {row['regular_attempts']}",
            f"- 조회 오류 {row['lookup_errors']}, 호가 누락 {row['missing_quotes']}, 오래된 호가 {row['stale_quotes']}, 관측 간격 180초 초과 {row['quote_gaps']}",
            f"- 계획 {len(row['plans'])}, 내부 가상 체결 {len(row['fills'])}, 원격 누적 체결 주문 {len(row.get('broker_confirmed_orders',{}))} (개별 체결 횟수/확정 비용과 구분)",
            f"- 관측 기준 최대 낙폭: {row['observed_mdd'] if row['observed_mdd'] is not None else '미검증 — 정상 평가 관측 없음'}",
            "",
            "상세 현금·보유·평가액·비용·손익·계획·미체결 사유·재시작·중지 이력·설정/원본 지문은 같은 이름의 JSON과 observation-ledger.sqlite에 보존한다.",
            "last_valid_valuation은 표시된 시각의 평가이며 latest_valuation_available=false이면 현재 가치로 해석하지 않는다.",
            "",
            "|판단 사유|횟수|",
            "|---|---:|",
        ]
        lines.extend(f"|{reason}|{count}|" for reason, count in sorted(row["reasons"].items()))
        (destination / ("US-" + day + ".md")).write_text("\n".join(lines) + "\n", encoding="utf-8")


def control_event(folder, action):
    if (folder / "observation-ledger.sqlite").exists():
        with ObservationJournal(folder) as journal:
            journal.record("control", {"action": action})
