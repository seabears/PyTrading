"""실적 제목의 오분류·출처·시각·수집 장애·실제 모의 계좌 연결을 검증한다."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from news.earnings import active_signals, classify, collect_report, load_policy
from news.earnings_service import EarningsService
from strategy.engine import evaluate, parse_timestamp
from trading.paper import PaperAccount
from Test.sample_data import sample, later


CONFIG = {"news_enabled": False, "earnings_enabled": True}


def article(title="Apple earnings beat analyst estimates", now=None):
    now = now or parse_timestamp(sample()["now"])
    return {"candidate_id": "test", "market": "US", "symbol": "AAPL", "title": title,
            "url": "https://news.google.com/rss/articles/test", "publisher": "Reuters",
            "source_url": "https://www.reuters.com", "published_at": (now - timedelta(minutes=10)).isoformat(),
            "first_seen_at": (now - timedelta(minutes=1)).isoformat()}


def snapshot(title="Apple earnings beat analyst estimates"):
    row = sample()
    row.update(symbol="AAPL", news_events=[], earnings_feed_ok=True, earnings_events=[article(title)])
    return row


class EarningsClassificationTests(unittest.TestCase):
    def setUp(self):
        self.now = parse_timestamp(sample()["now"])
        self.policy = load_policy()

    def classify(self, title):
        return classify(article(title), self.policy, self.now)

    def test_reported_beat_is_positive_without_fake_verification(self):
        row = self.classify("Apple earnings beat analyst estimates")
        self.assertEqual(row["direction"], "positive")
        self.assertFalse(row["confirmed"])
        self.assertFalse(row["source_verified"])

    def test_reported_miss_is_negative(self):
        self.assertEqual(self.classify("Apple revenue misses estimates")["direction"], "negative")

    def test_growth_alone_is_not_surprise(self):
        self.assertEqual(self.classify("Apple reports revenue growth of 20%")["direction"], "neutral")

    def test_preview_is_excluded(self):
        self.assertEqual(self.classify("Apple earnings preview: expected to beat estimates")["direction"], "excluded")

    def test_question_and_analyst_prediction_are_not_reported_results(self):
        self.assertEqual(self.classify("Apple earnings beat estimates?")["direction"], "excluded")
        self.assertEqual(self.classify("Apple analysts predict earnings beat estimates")["direction"], "excluded")

    def test_beat_and_miss_are_mixed(self):
        self.assertEqual(self.classify("Apple earnings beat estimates but revenue misses forecasts")["direction"], "mixed")

    def test_guidance_cut_dominates_reported_beat(self):
        self.assertEqual(self.classify("Apple beats earnings estimates but cuts full-year guidance")["direction"], "negative")

    def test_company_guidance_raise_is_positive(self):
        self.assertEqual(self.classify("Apple raises full-year revenue guidance")["direction"], "positive")

    def test_negation_is_excluded(self):
        self.assertEqual(self.classify("Apple did not cut earnings guidance")["direction"], "excluded")

    def test_supplier_or_customer_mentions_are_not_target_earnings(self):
        self.assertEqual(self.classify("Apple supplier Foxconn revenue beats estimates")["direction"], "excluded")
        self.assertEqual(self.classify("Qualcomm earnings beat estimates on Apple demand")["direction"], "excluded")

    def test_analyst_guidance_change_is_not_company_guidance(self):
        self.assertEqual(self.classify("Analysts lift Apple earnings outlook")["direction"], "excluded")

    def test_untrusted_source_and_wrong_company_are_excluded(self):
        row = article()
        row["source_url"] = "https://reuters.com.evil.example"
        self.assertEqual(classify(row, self.policy, self.now)["direction"], "excluded")
        self.assertEqual(self.classify("Microsoft earnings beat estimates")["direction"], "excluded")

    def test_stale_publication_is_not_revived_by_new_reception(self):
        row = article()
        row["published_at"] = (self.now - timedelta(days=2)).isoformat()
        self.assertEqual(classify(row, self.policy, self.now)["direction"], "excluded")

    def test_future_availability_is_rejected(self):
        row = article()
        row["first_seen_at"] = (self.now + timedelta(seconds=1)).isoformat()
        self.assertEqual(classify(row, self.policy, self.now)["direction"], "excluded")

    def test_korean_earnings_and_guidance(self):
        row = article("삼성전자 영업이익 컨센서스 상회")
        row.update(market="KR", symbol="005930", source_url="https://yna.co.kr", publisher="연합뉴스")
        self.assertEqual(classify(row, self.policy, self.now)["direction"], "positive")

    def test_all_watchlist_symbols_have_company_aliases(self):
        from paths import CONFIG_ROOT
        symbols = json.loads((CONFIG_ROOT / "settings.json").read_text(encoding="utf-8"))["symbols"]
        self.assertTrue(all(symbol in self.policy["company_aliases"] for symbol in symbols))

    def test_collector_uses_explicit_company_earnings_and_allowed_sources(self):
        calls = []
        def fetch(*args):
            calls.append(args)
            return [article()]
        report = collect_report("US", "AAPL", self.policy, fetch=fetch, now=self.now)
        self.assertIn('"Apple"', calls[0][2])
        self.assertIn("earnings", calls[0][2])
        self.assertIn("reuters.com", calls[0][3])
        self.assertEqual(report["events"][0]["direction"], "positive")


class EarningsTradingTests(unittest.TestCase):
    def setUp(self):
        # 이 클래스는 제목 신호의 가격 결합만 격리 검증한다. 실제 설정은 원문 검증 필수다.
        policy = {**load_policy(), "require_primary_verification": False}
        self.policy_patch = patch("news.earnings.load_policy", return_value=policy)
        self.policy_patch.start()
        self.addCleanup(self.policy_patch.stop)

    def test_positive_still_requires_price_and_volume(self):
        row = snapshot()
        self.assertEqual(evaluate(row, CONFIG)["action"], "BUY")
        row["bars"][-1]["volume"] = 100
        self.assertEqual(evaluate(row, CONFIG)["action"], "WAIT")

    def test_no_earnings_is_not_positive_evidence(self):
        row = snapshot()
        row["earnings_events"] = []
        self.assertEqual(evaluate(row, CONFIG)["action"], "WAIT")

    def test_negative_blocks_entry_and_sells_held_position(self):
        row = snapshot("Apple revenue misses estimates")
        self.assertEqual(evaluate(row, CONFIG)["reason"], "earnings_negative_blocks_entry")
        row["position"] = {"quantity": 1, "average_cost": 100, "peak_bid_since_entry": 101}
        self.assertEqual(evaluate(row, CONFIG)["reason"], "earnings_negative_report")

    def test_mixed_blocks_new_entry_without_forcing_news_sale(self):
        row = snapshot("Apple earnings beat estimates but revenue misses forecasts")
        self.assertEqual(evaluate(row, CONFIG)["reason"], "earnings_conflict_blocks_entry")
        row["position"] = {"quantity": 1, "average_cost": 100, "peak_bid_since_entry": 101}
        self.assertEqual(evaluate(row, CONFIG)["action"], "HOLD")

    def test_price_stop_has_priority_over_bad_news_input(self):
        row = snapshot()
        row.update(earnings_events=[{}], earnings_feed_ok=False,
                   position={"quantity": 1, "average_cost": 110, "peak_bid_since_entry": 110})
        self.assertEqual(evaluate(row, CONFIG)["reason"], "stop_loss")

    def test_feed_error_blocks_entry_but_preserves_price_exit(self):
        row = snapshot()
        row["earnings_feed_ok"] = False
        self.assertEqual(evaluate(row, CONFIG)["reason"], "earnings_feed_unavailable")
        row["position"] = {"quantity": 1, "average_cost": 100, "peak_bid_since_entry": 101}
        row["bars"][-1]["close"] = 99.4
        self.assertEqual(evaluate(row, CONFIG)["reason"], "close_below_prior_average")

    def test_forged_direction_flag_is_reclassified(self):
        row = snapshot("Apple reports quarterly results")
        row["earnings_events"][0]["direction"] = "positive"
        self.assertEqual(evaluate(row, CONFIG)["action"], "WAIT")

    def test_contradictory_articles_do_not_force_sale(self):
        row = snapshot()
        row["earnings_events"].append(article("Apple revenue misses estimates"))
        self.assertEqual(evaluate(row, CONFIG)["reason"], "earnings_conflict_blocks_entry")

    def test_earnings_can_be_disabled_independently(self):
        self.assertEqual(evaluate(snapshot("Apple revenue misses estimates"), {"news_enabled": False, "earnings_enabled": False})["action"], "BUY")

    def test_deduplication_and_paper_account_buy_then_sell(self):
        with tempfile.TemporaryDirectory() as directory:
            account = PaperAccount(Path(directory) / "account.json")
            row = snapshot()
            row["earnings_events"] *= 2
            bought = account.evaluate_snapshot(row, CONFIG)
            self.assertEqual(bought["action"], "BUY")
            self.assertEqual(len(bought["metrics"]["earnings_positive_ids"]), 1)
            negative = later(row)
            negative["earnings_events"] = [article("Apple revenue misses estimates")]
            sold = account.evaluate_snapshot(negative, CONFIG)
            self.assertEqual(sold["action"], "SELL")
            self.assertEqual(len(account.state["trades"]), 2)
            self.assertFalse(account.state["positions"])


class EarningsServiceTests(unittest.TestCase):
    def test_partial_source_failure_blocks_new_buys(self):
        now = parse_timestamp(sample()["now"])
        with tempfile.TemporaryDirectory() as directory:
            service = EarningsService([], Path(directory) / "cache.json", fetch_report=lambda *args: {
                "events": [], "fetched_count": 0, "source_errors": ["reuters.com"]})
            service.refresh_one("US", "AAPL", now)
            self.assertFalse(service.snapshot("US", "AAPL", now)["earnings_feed_ok"])

    def test_duplicate_refresh_preserves_first_seen_and_restart_cache(self):
        now = parse_timestamp(sample()["now"])
        policy = load_policy()
        event = classify(article(), policy, now)
        def fetch(*args):
            return {"events": [event], "fetched_count": 1}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "earnings.json"
            service = EarningsService([("US", "AAPL")], path, policy, fetch)
            service.refresh_one("US", "AAPL", now)
            first_seen = service.snapshot("US", "AAPL", now)["earnings_events"][0]["first_seen_at"]
            event["first_seen_at"] = now.isoformat()
            service.refresh_one("US", "AAPL", now)
            restored = EarningsService([], path, policy, fetch)
            result = restored.snapshot("US", "AAPL", now)
            self.assertTrue(result["earnings_feed_ok"])
            self.assertEqual(result["earnings_events"][0]["first_seen_at"], first_seen)
            self.assertEqual(len(result["earnings_events"]), 1)

    def test_failure_and_expiry_do_not_look_like_successful_empty_feed(self):
        now = parse_timestamp(sample()["now"])
        with tempfile.TemporaryDirectory() as directory:
            service = EarningsService([], Path(directory) / "cache.json", fetch_report=lambda *args: {"events": [], "fetched_count": 0})
            service.refresh_one("US", "AAPL", now)
            self.assertTrue(service.snapshot("US", "AAPL", now)["earnings_feed_ok"])
            self.assertFalse(service.snapshot("US", "AAPL", now + timedelta(hours=1))["earnings_feed_ok"])
            def failing(*args):
                raise ValueError("network unavailable")
            service.fetch_report = failing
            service.refresh_one("US", "AAPL", now)
            self.assertFalse(service.snapshot("US", "AAPL", now)["earnings_feed_ok"])

    def test_corrupt_cache_is_not_treated_as_verified_feed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.json"
            path.write_text("broken", encoding="utf-8")
            service = EarningsService([], path)
            self.assertFalse(service.snapshot("US", "AAPL")["earnings_feed_ok"])


class EarningsRunnerTests(unittest.TestCase):
    def test_runtime_attaches_earnings_and_closes_service_without_orders(self):
        from app import runner
        from app.runtime import load_run_settings
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            strategy = folder / "strategy.json"
            strategy.write_text(json.dumps(CONFIG), encoding="utf-8")
            settings = load_run_settings()
            settings.update(strategy_config=strategy, output_dir=folder / "paper", watch=False,
                            collect_news=False, symbols=[("US", "AAPL")])
            market_snapshot = snapshot()
            market_snapshot.pop("earnings_events")
            market_snapshot.pop("earnings_feed_ok")
            with patch("app.runner.load_run_settings", return_value=settings), \
                 patch("app.runner.create_kis_client"), \
                 patch("app.runner.collect_kis_snapshot", return_value=market_snapshot), \
                 patch("app.runner.EarningsService") as service, \
                 patch("app.runner.record_decision") as record, contextlib.redirect_stdout(io.StringIO()):
                service.return_value.snapshot.return_value = {"earnings_events": [article()], "earnings_feed_ok": True}
                runner.main(argv=[])
            self.assertEqual(record.call_args.args[1]["earnings_events"][0]["title"], article()["title"])
            service.return_value.stop.assert_called_once()
            service.return_value.start.assert_not_called()
            service.return_value.snapshot.assert_called_once()
