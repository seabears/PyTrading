"""제목을 확정 뉴스로 오해하지 않는지, 중복·시각·검토 근거를 검증한다."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

from news.collector import classify_title, fetch_rss_candidates, load_confirmed_events, update_news_cache


class NewsTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix=".test-", dir=Path(__file__).parent)
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "news.json"
        self.now = datetime(2026, 10, 11, tzinfo=timezone.utc)

    def event(self):
        return {"market": "US", "symbol": "DEMO", "event_id": "test-event",
                "available_at": "2026-10-10T16:00:00Z", "kind": "earnings_guidance_raised",
                "confirmed": True, "source_verified": True,
                "evidence_url": "https://example.com/fictional", "review_note": "가상 테스트 근거"}

    def test_korean_and_english_are_candidates_only(self):
        for title in ("삼성전자 실적 전망 상향", "DEMO raises earnings guidance"):
            row = classify_title(title)
            self.assertIn("earnings_guidance_raised", row["candidate_kinds"])
            self.assertFalse(row["confirmed"])
            self.assertFalse(row["source_verified"])

    def test_uncertain_news_is_flagged(self):
        self.assertTrue(classify_title("Rumor: DEMO may announce share buyback")["uncertain"])

    def test_rss_does_not_forward_broker_secrets(self):
        xml = b'<rss><channel><item><title>DEMO raises guidance</title><link>https://example.com/story</link><source url="https://example.com">Demo</source><pubDate>Fri, 09 Oct 2026 16:00:00 GMT</pubDate></item></channel></rss>'
        response = MagicMock()
        response.__enter__.return_value.read.return_value = xml
        with patch("news.collector.urllib.request.urlopen", return_value=response) as request:
            rows = fetch_rss_candidates("US", "DEMO", "DEMO", ["reuters.com", "ft.com"])
            self.assertNotIn("Authorization", request.call_args.args[0].headers)
            search = parse_qs(urlsplit(request.call_args.args[0].full_url).query)["q"][0]
            self.assertIn("site:reuters.com OR site:ft.com", search)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["confirmed"])
        self.assertIn("+00:00", rows[0]["published_at"])
        self.assertEqual(rows[0]["source_url"], "https://example.com")

    def test_selected_cache_removes_old_and_pre_filter_articles(self):
        row = {"candidate_id": "fresh", "market": "US", "symbol": "AAPL",
               "title": "Apple raises guidance", "publisher": "Reuters",
               "source_url": "https://reuters.com", "selection_status": "selected",
               "published_at": datetime.now(timezone.utc).isoformat(),
               "first_seen_at": datetime.now(timezone.utc).isoformat()}
        old = {**row, "candidate_id": "old", "published_at": "2020-01-01T00:00:00Z"}
        broad = {"candidate_id": "broad", "first_seen_at": row["first_seen_at"]}
        self.path.write_text(json.dumps([old, broad]), encoding="utf-8")
        update_news_cache(self.path, [row], selected_only=True)
        result = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual([item["candidate_id"] for item in result], ["fresh"])

    def test_duplicate_cache_preserves_first_seen(self):
        row = {"candidate_id": "same", "first_seen_at": "2026-10-09T16:00:00Z"}
        update_news_cache(self.path, [row])
        update_news_cache(self.path, [{**row, "first_seen_at": "2026-10-10T16:00:00Z"}])
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), [row])

    def test_event_requires_review(self):
        for field in ("confirmed", "source_verified", "evidence_url", "review_note"):
            row = self.event()
            row[field] = False
            self.path.write_text(json.dumps([row]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_confirmed_events(self.path, self.now)

    def test_future_or_missing_review_time_rejected(self):
        for value in ("2027-01-01T00:00:00Z", None, "2026-10-10T16:00:00"):
            row = self.event()
            row["available_at"] = value
            self.path.write_text(json.dumps([row]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_confirmed_events(self.path, self.now)

    def test_valid_event_and_invalid_list_item(self):
        row = self.event()
        self.path.write_text(json.dumps([row]), encoding="utf-8")
        self.assertEqual(load_confirmed_events(self.path, self.now), [row])
        self.path.write_text('[null]', encoding="utf-8")
        with self.assertRaises(ValueError):
            load_confirmed_events(self.path, self.now)


if __name__ == "__main__":
    unittest.main()
