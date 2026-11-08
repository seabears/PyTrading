"""--test earnings는 합성 실적·실제 판단 엔진, earnings-live는 실제 RSS 수집 확인이다."""
import copy
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from paths import RESULTS_ROOT, DATA_ROOT, FIXTURES_ROOT
from news.earnings import classify, collect_report, load_policy
from strategy.engine import parse_timestamp
from trading.paper import PaperAccount


def main():
    snapshots = json.loads((FIXTURES_ROOT / "demo_replay.json").read_text(encoding="utf-8"))
    source = next(row for row in snapshots if row["market"] == "US")
    source.update(symbol="AAPL", news_events=[], earnings_feed_ok=True)
    now = parse_timestamp(source["now"])
    policy = load_policy()
    titles = ["Apple earnings beat analyst estimates", "Apple revenue misses estimates"]
    records = []
    with TemporaryDirectory(prefix="earnings-paper-") as directory:
        account = PaperAccount(Path(directory) / "account.json")
        for number, title in enumerate(titles):
            stamp = (now + timedelta(seconds=number * 60)).isoformat()
            row = copy.deepcopy(source)
            row["now"] = row["quote"]["available_at"] = stamp
            article = {"market": "US", "symbol": "AAPL", "title": title,
                       "url": "https://example.invalid/synthetic-earnings", "publisher": "Reuters",
                       "source_url": "https://reuters.com", "published_at": (now - timedelta(minutes=10)).isoformat(),
                       "first_seen_at": (now - timedelta(minutes=1)).isoformat()}
            row["earnings_events"] = [classify(article, policy, parse_timestamp(stamp))]
            decision = account.evaluate_snapshot(row, {"news_enabled": False, "earnings_enabled": True})
            records.append({"synthetic": True, "title": title, "snapshot": row, "decision": decision})
            print(title)
            print(" ", decision["action"], decision["reason"])
    output = RESULTS_ROOT / "earnings-demo.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("합성 실적·모의 체결 확인:", output)


def live():
    policy = load_policy()
    records = []
    for symbol in ("AAPL", "MSFT", "NVDA"):
        try:
            report = collect_report("US", symbol, policy)
            records.append(report)
            print(symbol, "실제 RSS", report["fetched_count"], "건", dict(Counter(row["direction"] for row in report["events"])))
        except (ValueError, OSError):
            records.append({"symbol": symbol, "error": "rss_collection_failed"})
            print(symbol, "RSS 수집 실패 — 네트워크·출처 접근 확인 필요")
    output = RESULTS_ROOT / "earnings-live.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"checked_at": datetime.now(timezone.utc).isoformat(), "reports": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("실제 수집 확인:", output)
