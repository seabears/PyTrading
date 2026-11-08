"""뉴스 확인은 인증을 요구하지 않고, 토스 확인은 휴장 응답을 정상 처리한다."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import check_news, check_toss


class CheckToolsTest(unittest.TestCase):
    def test_news_check_writes_separate_result(self):
        with tempfile.TemporaryDirectory(prefix=".test-", dir=Path(__file__).parent) as folder:
            root = Path(folder)
            settings = {"news_queries": None, "symbols": [("US", "AAPL")]}
            candidate = {"candidate_id": "fake", "first_seen_at": "2026-10-11T00:00:00Z",
                         "publisher": "가상 출처", "title": "가상 기사"}
            with patch("tools.check_news.load_run_settings", return_value=settings), \
                 patch("tools.check_news.RESULTS_ROOT", root / "tests/results"), \
                 patch("tools.check_news.collect_news", return_value={"selected": [], "excluded": [], "fetched_count": 0}), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    check_news.main()
            self.assertEqual(result.exception.code, 0)
            self.assertTrue((root / "tests" / "results" / "live-news.json").exists())
            self.assertFalse((root / "data").exists())

    def test_toss_closed_session_does_not_require_quote(self):
        settings = {"env_file": Path("fake.env"), "symbols": [("US", "AAPL")]}
        with patch("tools.check_toss.load_run_settings", return_value=settings), \
             patch("tools.check_toss.read_credentials", return_value=("fake", "fake")), \
             patch("tools.check_toss.TossMarketClient") as client, \
             patch("tools.check_toss.collect_snapshot", return_value={"regular_session_open": False}), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            check_toss.main()
        client.return_value.authenticate.assert_called_once()
        self.assertIn("휴장", output.getvalue())
