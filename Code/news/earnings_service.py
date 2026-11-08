"""실적 뉴스의 백그라운드 수집·원자적 저장. 가격 손절 검사와 네트워크를 분리한다."""
import copy
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from news.earnings import collect_report, load_policy
from strategy.engine import parse_timestamp


class EarningsService:
    def __init__(self, symbols, path, policy=None, fetch_report=None):
        self.symbols = list(symbols)
        self.path = Path(path)
        self.policy = policy or load_policy()
        self.fetch_report = fetch_report or collect_report
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.state = {"version": 1, "events": [], "feeds": {}}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if loaded["version"] != 1 or not isinstance(loaded["events"], list) or not isinstance(loaded["feeds"], dict):
                    raise ValueError("실적 캐시 형식 오류")
                self.state = loaded
            except (ValueError, KeyError, TypeError):
                # 손상된 캐시는 무시하되 이전 파일을 삭제하지 않고 새 수집까지 매수를 보류한다.
                self.state["cache_error"] = True

    def refresh_one(self, market, symbol, now=None):
        now = now or datetime.now(timezone.utc)
        key = market + ":" + symbol
        try:
            report = self.fetch_report(market, symbol, self.policy)
            with self.lock:
                if self.stop_event.is_set():
                    return
                by_id = {row["event_id"]: row for row in self.state["events"]}
                for event in report["events"]:
                    event = copy.deepcopy(event)
                    if event["direction"] == "excluded":
                        continue
                    previous = by_id.get(event["event_id"])
                    if previous:
                        first_seen = min(previous["first_seen_at"], event["first_seen_at"], key=parse_timestamp)
                        event = {**event, "first_seen_at": first_seen, "available_at": first_seen}
                    else:
                        # 이후 연구용 수신 이력이다. 재시도 중 중복 기록은 event_id로 제거한다.
                        self.path.parent.mkdir(parents=True, exist_ok=True)
                        with (self.path.parent / "earnings-events.jsonl").open("a", encoding="utf-8") as ledger:
                            ledger.write(json.dumps({"recorded_at": now.isoformat(), "event": event}, ensure_ascii=False) + "\n")
                    by_id[event["event_id"]] = event
                self.state["events"] = sorted(by_id.values(), key=lambda row: row["first_seen_at"])[-2000:]
                self.state["feeds"][key] = {"last_success": now.isoformat(), "last_attempt": now.isoformat(),
                                            "error": bool(report.get("source_errors")), "fetched_count": report["fetched_count"]}
                reports = self.path.parent / "earnings-reports"
                reports.mkdir(parents=True, exist_ok=True)
                report_path = reports / (market + "-" + symbol + ".json")
                temporary = report_path.with_suffix(".tmp")
                temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                temporary.replace(report_path)
                self._save()
        except (OSError, ValueError, KeyError, TypeError):
            with self.lock:
                if self.stop_event.is_set():
                    return
                previous = self.state["feeds"].get(key, {})
                self.state["feeds"][key] = {**previous, "last_attempt": now.isoformat(), "error": True}
                try:
                    self._save()
                except OSError:
                    pass  # 저장 장애에서도 메모리의 오류 상태로 신규 매수를 차단한다.

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        temporary.replace(self.path)

    def snapshot(self, market, symbol, now=None):
        now = now or datetime.now(timezone.utc)
        with self.lock:
            feed = copy.deepcopy(self.state["feeds"].get(market + ":" + symbol, {}))
            events = [copy.deepcopy(row) for row in self.state["events"] if row.get("market") == market and row.get("symbol") == symbol]
        try:
            age = (now - parse_timestamp(feed["last_success"])).total_seconds()
            healthy = not feed.get("error", True) and 0 <= age <= self.policy["feed_stale_seconds"]
        except (KeyError, ValueError, TypeError):
            healthy = False
        return {"earnings_events": events, "earnings_feed_ok": healthy}

    def start(self):
        if self.thread is not None:
            return
        def worker():
            while not self.stop_event.is_set():
                for market, symbol in self.symbols:
                    if self.stop_event.is_set():
                        return
                    self.refresh_one(market, symbol)
                    self.stop_event.wait(.2)
                self.stop_event.wait(self.policy["refresh_seconds"])
        self.thread = threading.Thread(target=worker, name="earnings-news", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        with self.lock:
            pass  # 진행 중인 파일 저장이 끝난 뒤 종료한다. 네트워크 완료는 기다리지 않는다.
        if self.thread is not None:
            self.thread.join(timeout=.2)
