import json
import tempfile
import unittest
from pathlib import Path

from news.review import approve_candidate


class ReviewTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix=".test-", dir=Path(__file__).parent)
        self.addCleanup(self.folder.cleanup)
        self.candidates = Path(self.folder.name) / "candidates.json"
        self.events = Path(self.folder.name) / "events.json"
        self.candidates.write_text(json.dumps([{"candidate_id": "fake", "market": "US", "symbol": "DEMO"}]), encoding="utf-8")

    def approve(self, kind="buyback_confirmed", url="https://example.com/fictional", note="가상 테스트"):
        return approve_candidate(self.candidates, self.events, "fake", kind, url, note)

    def test_repeated_approval_preserves_original_available_time(self):
        first = self.approve()
        second = self.approve()
        self.assertEqual(first, second)
        self.assertEqual(len(json.loads(self.events.read_text(encoding="utf-8"))), 1)

    def test_correction_uses_same_event_id(self):
        first = self.approve()
        second = self.approve(kind="earnings_guidance_cut")
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertGreaterEqual(second["available_at"], first["available_at"])

    def test_invalid_source_or_note_is_not_saved(self):
        for url, note in (("file:///fake", "test"), ("https://example.com", " ")):
            with self.assertRaises(ValueError):
                self.approve(url=url, note=note)
        self.assertFalse(self.events.exists())

    def test_corrupted_events_are_not_overwritten(self):
        self.events.write_text("broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.approve()
        self.assertEqual(self.events.read_text(encoding="utf-8"), "broken")


if __name__ == "__main__":
    unittest.main()
