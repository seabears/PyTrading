"""로컬 운용 감시. 외부 전송 없이 장애 이유를 저장하고 신규 매수를 중지한다."""
import json
import os
import shutil
import socket
import time
from datetime import datetime, timezone

from app.stateio import atomic_json, rotate_log


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def notify_systemd(message):
    address = os.environ.get("NOTIFY_SOCKET")
    if not address or os.name == "nt":
        return
    if address.startswith("@"):
        address = "\0" + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as connection:
        connection.sendto(message.encode(), address)


class OperationMonitor:
    """주기와 요청 지연을 실측하고 중단 이유를 재시작 후에도 유지한다."""
    def __init__(self, folder, minimum_free_bytes=256_000_000):
        self.folder = folder
        self.minimum_free_bytes = minimum_free_bytes
        self.path = folder / "operations.json"
        self.state = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {
            "version": 1, "buy_halts": [], "errors": {}, "last_valid_quotes": {}, "last_observations": {}}
        self.started = None
        self.last_cycle = None
        self.state["process_started_at"] = utc_now()
        notify_systemd("READY=1\nWATCHDOG=1")

    def save(self):
        self.state["heartbeat_at"] = utc_now()
        atomic_json(self.path, self.state)
        notify_systemd("WATCHDOG=1")

    def halt(self, reason):
        if reason not in self.state["buy_halts"]:
            self.state["buy_halts"].append(reason)
            from trading.observation_journal import control_event
            control_event(self.folder, reason)
            # 알림 경로는 로컬 outbox로 분리한다. 외부 채널로 자동 전송하지 않는다.
            alert_path = self.folder / "alerts.jsonl"
            rotate_log(alert_path, 1_000_000, 2)
            with alert_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"at": utc_now(), "category": reason, "action": "new_buys_halted"}) + "\n")
        self.save()

    def begin_cycle(self):
        current = time.monotonic()
        self.state["cycle_start_interval_seconds"] = current - self.last_cycle if self.last_cycle is not None else None
        self.last_cycle = current
        self.started = current
        self.check_quote_health()
        self.state["free_bytes"] = shutil.disk_usage(self.folder).free
        if self.state["free_bytes"] < self.minimum_free_bytes:
            self.halt("low_disk_space")
        self.save()

    def check_quote_health(self, now=None):
        """정규장 개장 후 180초 유예. 다른 중지 사유는 자동 해제하지 않는다."""
        from broker.sessions import regular_session
        from strategy.engine import parse_timestamp
        now = now or datetime.now(timezone.utc)
        session = regular_session("US", now)
        if session is None:
            self.state["quote_health"] = "outside_regular_session"
            return
        reference = session["start"]
        last = self.state.get("last_normal_observation_at")
        if last:
            reference = max(reference, parse_timestamp(last))
        age = max(0, (now - reference).total_seconds())
        self.state["normal_quote_gap_seconds"] = age
        self.state["quote_health"] = "outage" if age > 180 else "within_grace_or_fresh"
        if age > 180:
            self.halt("regular_quote_outage")
        elif last and parse_timestamp(last) >= session["start"] and "regular_quote_outage" in self.state["buy_halts"]:
            self.state["buy_halts"].remove("regular_quote_outage")
            from trading.observation_journal import control_event
            control_event(self.folder, "regular_quote_recovered")

    def error(self, key, category, diagnostic=None, request_seconds=None):
        count = self.state["errors"].get(key, 0) + 1
        self.state["errors"][key] = count
        self.state["last_error"] = {"symbol": key, "category": category, "at": utc_now()}
        if diagnostic is not None:
            self.state["last_error"]["diagnostic"] = diagnostic
        if request_seconds is not None:
            self.state["last_request_seconds"] = request_seconds
        self.check_quote_health()
        if count >= 3:
            self.halt("repeated_collection_errors")
        self.save()

    def observe(self, snapshot, request_seconds):
        from strategy.engine import parse_timestamp
        key = snapshot["market"] + ":" + snapshot["symbol"]
        now = parse_timestamp(snapshot["now"])
        self.state["last_observations"][key] = snapshot["now"]
        self.state["last_request_seconds"] = request_seconds
        self.state["maximum_request_seconds"] = max(request_seconds, self.state.get("maximum_request_seconds", 0))
        quote = snapshot.get("quote")
        if snapshot.get("regular_session_open"):
            if not quote or not 0 <= (now - parse_timestamp(quote["available_at"])).total_seconds() <= 30:
                self.error(key, "stale_or_missing_quote")
            else:
                self.state["errors"][key] = 0
                self.state["last_valid_quotes"][key] = quote["available_at"]
                self.state["last_normal_observation_at"] = snapshot["now"]
        self.check_quote_health(now)
        snapshot["operational_buy_block"] = bool(self.state["buy_halts"])
        self.save()

    def end_cycle(self, account, wait_seconds):
        from strategy.engine import parse_timestamp
        self.state["cycle_seconds"] = time.monotonic() - self.started
        self.state["configured_wait_seconds"] = wait_seconds
        self.state["expected_next_cycle_seconds"] = self.state["cycle_seconds"] + wait_seconds
        now = datetime.now(timezone.utc)
        self.state["held_quote_ages_seconds"] = {
            key: (now - parse_timestamp(account.state["quote_times"][key])).total_seconds()
            if key in account.state.get("quote_times", {}) else None for key in account.state["positions"]}
        from broker.sessions import regular_session
        if any((age is None or age > 180) and regular_session(key.split(":")[0], now)
               for key, age in self.state["held_quote_ages_seconds"].items()):
            self.halt("held_quotes_delayed")
        self.save()
        path = self.folder / "cycle-metrics.jsonl"
        rotate_log(path)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"at": utc_now(), "cycle_seconds": self.state["cycle_seconds"],
                "cycle_start_interval_seconds": self.state["cycle_start_interval_seconds"],
                "held_quote_ages_seconds": self.state["held_quote_ages_seconds"]}) + "\n")
