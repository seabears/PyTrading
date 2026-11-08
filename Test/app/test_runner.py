"""CMD 진입점이 호출하는 실행 흐름을 네트워크 없이 검증한다."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import runner as run_paper
from trading.paper import PaperAccount
from app.runtime import acquire_run_lock, load_run_settings, release_run_lock
from Test.sample_data import sample
from Test.sample_data import later


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix=".test-", dir=Path(__file__).parent)
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.replay = self.root / "replay.json"
        self.output = self.root / "output"
        self.news_strategy = self.root / "news-strategy.json"
        self.news_strategy.write_text(json.dumps({"news_enabled": True}), encoding="utf-8")
        self.replay.write_text(json.dumps([sample(), later(sample(), bid=95)]), encoding="utf-8")

    def execute(self, extra=None):
        arguments = ["app.runner.py", "--strategy-config", str(self.news_strategy), "--replay", str(self.replay), "--output-dir", str(self.output)]
        with patch("sys.argv", arguments + (extra or [])), contextlib.redirect_stdout(io.StringIO()):
            run_paper.main()

    def test_replay_does_not_authenticate_and_restart_does_not_duplicate(self):
        with patch("app.runner.read_credentials", side_effect=AssertionError("offline credentials")), \
             patch("app.runner.TossMarketClient", side_effect=AssertionError("offline broker")):
            self.execute()
            self.execute()
        state = json.loads((self.output / "account.json").read_text(encoding="utf-8"))
        self.assertEqual(len(state["trades"]), 2)
        released = acquire_run_lock(self.output / "run.lock")
        release_run_lock(released)
        self.assertTrue((self.output / "summary.md").exists())

    def test_existing_lock_remains_untouched(self):
        self.output.mkdir()
        lock = self.output / "run.lock"
        held = acquire_run_lock(lock)
        try:
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.execute()
        finally:
            release_run_lock(held)
        self.assertEqual(lock.read_bytes(), b"0")

    def test_bad_replay_releases_lock(self):
        self.replay.write_text("not json", encoding="utf-8")
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.execute()
        released = acquire_run_lock(self.output / "run.lock")
        release_run_lock(released)

    def test_invalid_news_file_still_allows_price_stop(self):
        self.output.mkdir()
        account = PaperAccount(self.output / "account.json")
        account.evaluate_snapshot(sample())
        events = self.root / "bad-events.json"
        events.write_text("broken", encoding="utf-8")
        arguments = ["app.runner.py", "--symbols", "US:AAPL", "--events-file", str(events),
                     "--output-dir", str(self.output)]
        settings = load_run_settings()
        settings.update(collect_news=True, strategy_config=self.news_strategy)
        settings["broker"] = "toss"
        settings.update(watch=False, collect_news=False)
        with patch("sys.argv", arguments), patch("app.runner.read_credentials", return_value=("fake", "fake")), \
             patch("app.runner.load_run_settings", return_value=settings), \
             patch("app.runner.TossMarketClient"), \
             patch("app.runner.collect_snapshot", return_value=later(sample(), bid=95)), \
             contextlib.redirect_stdout(io.StringIO()):
            run_paper.main()
        state = json.loads((self.output / "account.json").read_text(encoding="utf-8"))
        self.assertEqual(state["trades"][-1]["reason"], "stop_loss")

    def test_no_arguments_repeats_and_collects_news(self):
        settings = load_run_settings()
        settings.update(collect_news=True, strategy_config=self.news_strategy)
        settings["broker"] = "toss"
        settings.update(output_dir=self.output, symbols=[("US", "AAPL")])
        with patch("sys.argv", ["app.runner.py"]), \
             patch("app.runner.load_run_settings", return_value=settings), \
             patch("app.runner.read_credentials", return_value=("fake", "fake")) as credentials, \
             patch("app.runner.TossMarketClient"), \
             patch("app.runner.collect_snapshot", side_effect=[sample(), later(sample())]) as collect, \
             patch("app.runner.refresh_news") as news, \
             patch("app.runner.time.sleep", side_effect=[None, KeyboardInterrupt]) as sleep, \
             contextlib.redirect_stdout(io.StringIO()):
            run_paper.main()
        self.assertEqual(collect.call_count, 2)
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_called_with(60)
        news.assert_called_once()
        credentials.assert_called_once_with(False, settings["env_file"])

    def test_authentication_error_retries_without_exiting(self):
        from broker.toss import TossApiError
        settings = load_run_settings()
        settings.update(collect_news=True, strategy_config=self.news_strategy)
        settings["broker"] = "toss"
        settings.update(output_dir=self.output, symbols=[("US", "AAPL")], collect_news=False)
        with patch("sys.argv", ["app.runner.py"]), \
             patch("app.runner.load_run_settings", return_value=settings), \
             patch("app.runner.read_credentials", return_value=("fake", "fake")), \
             patch("app.runner.TossMarketClient") as client, \
             patch("app.runner.collect_snapshot", return_value=sample()), \
             patch("app.runner.time.sleep", side_effect=[None, KeyboardInterrupt]), \
             contextlib.redirect_stdout(io.StringIO()):
            client.return_value.authenticate.side_effect = [TossApiError("network offline"), None]
            run_paper.main()
        self.assertEqual(client.return_value.authenticate.call_count, 2)

    def test_auth_429_uses_group_wait_instead_of_fixed_retry_interval(self):
        from broker.toss import TossRateLimitError
        settings = load_run_settings()
        settings.update(collect_news=True, strategy_config=self.news_strategy)
        settings["broker"] = "toss"
        settings.update(output_dir=self.output, symbols=[("US", "AAPL")], collect_news=False)
        with patch("sys.argv", ["app.runner.py"]), \
             patch("app.runner.load_run_settings", return_value=settings), \
             patch("app.runner.read_credentials", return_value=("fake", "fake")), \
             patch("app.runner.TossMarketClient") as client, \
             patch("app.runner.collect_snapshot", return_value=sample()), \
             patch("app.runner.time.sleep", side_effect=KeyboardInterrupt) as sleep, \
             contextlib.redirect_stdout(io.StringIO()):
            client.return_value.authenticate.side_effect = [TossRateLimitError("429"), None]
            run_paper.main()
        client.return_value.rate_limiter.wait.assert_called_once_with("/oauth2/token")
        self.assertEqual(sleep.call_count, 1)  # 인증 지연은 그룹에서, 주기 대기는 runner에서 처리한다.

    def test_one_malformed_quote_does_not_stop_other_symbols(self):
        settings = load_run_settings()
        settings.update(collect_news=True, strategy_config=self.news_strategy)
        settings["broker"] = "toss"
        settings.update(output_dir=self.output, symbols=[("US", "MU"), ("US", "AAPL")], collect_news=False, watch=False)
        with patch("sys.argv", ["app.runner.py"]), \
             patch("app.runner.load_run_settings", return_value=settings), \
             patch("app.runner.read_credentials", return_value=("fake", "fake")), \
             patch("app.runner.TossMarketClient"), \
             patch("app.runner.collect_snapshot", side_effect=[ValueError("bad quote"), sample()]) as collect, \
             patch("app.runner.record_decision") as record, \
             contextlib.redirect_stdout(io.StringIO()):
            run_paper.main()
        self.assertEqual(collect.call_count, 2)
        record.assert_called_once()

    def test_disabled_news_does_not_read_files_or_collect_and_can_buy(self):
        settings = load_run_settings()
        disabled = self.root / "disabled-all-news.json"
        disabled.write_text(json.dumps({"news_enabled": False, "earnings_enabled": False}), encoding="utf-8")
        settings["strategy_config"] = disabled
        settings.update(output_dir=self.output, symbols=[("US", "AAPL")], watch=False,
                        collect_news=True, events_file=self.root / "missing-events.json",
                        news_queries=self.root / "missing-queries.json")
        with patch("app.runner.load_run_settings", return_value=settings), \
             patch("app.runner.create_kis_client"), \
             patch("app.runner.collect_kis_snapshot", return_value=sample()), \
             patch("app.runner.load_confirmed_events", side_effect=AssertionError("news file read")), \
             patch("app.runner.refresh_news", side_effect=AssertionError("news collection")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            run_paper.main(argv=[])
        account = json.loads((self.output / "account.json").read_text(encoding="utf-8"))
        self.assertEqual(account["trades"][0]["action"], "BUY")
        self.assertEqual(account["trades"][0]["reason"], "price_breakout_with_volume")
        self.assertIn("뉴스 기능 끔", output.getvalue())

    def test_service_signal_uses_graceful_shutdown(self):
        with self.assertRaises(KeyboardInterrupt):
            run_paper.stop_on_service_signal(None, None)


if __name__ == "__main__":
    unittest.main()
