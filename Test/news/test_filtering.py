"""뉴스 선별 경계 검증. 합성 제목으로 규칙 동작만 확인하며 예측 성능은 측정하지 않는다."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from news.filtering import company_in_title, filter_candidates, load_filter_policy, select_candidate


class NewsFilteringTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_filter_policy()
        self.now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
        self.article = {
            "market": "US", "symbol": "AAPL", "title": "Apple raises guidance",
            "publisher": "Reuters", "source_url": "https://www.reuters.com",
            "published_at": (self.now - timedelta(hours=1)).isoformat(),
        }

    def select(self, **changes):
        return select_candidate({**self.article, **changes}, self.policy, self.now)

    def test_material_event_selected_but_never_confirmed(self):
        result = self.select(confirmed=True, source_verified=True)
        self.assertEqual(result["selection_status"], "selected")
        self.assertIn("earnings_or_guidance", result["impact_events"])
        self.assertFalse(result["confirmed"])
        self.assertFalse(result["source_verified"])
        self.assertEqual(result["source_check"], "rss_metadata_only")

    def test_source_name_and_domain_must_both_match(self):
        for changes in ({"publisher": "Yahoo Finance"}, {"source_url": "https://yahoo.com"},
                        {"source_url": ""}, {"source_url": "https://reuters.com.evil.example"},
                        {"source_url": "https://notreuters.com"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.select(**changes)["selection_status"], "excluded")

    def test_company_ticker_word_boundary(self):
        self.assertFalse(company_in_title("BAAPLX raises guidance", ["AAPL"]))
        self.assertTrue(company_in_title("(AAPL) raises guidance", ["AAPL"]))
        self.assertEqual(self.select(title="Microsoft raises guidance")["selection_status"], "excluded")

    def test_old_future_and_missing_timestamps_excluded(self):
        for published in ((self.now - timedelta(hours=25)).isoformat(),
                          (self.now + timedelta(seconds=1)).isoformat(), None, "2026-10-11T10:00:00"):
            with self.subTest(published=published):
                self.assertEqual(self.select(published_at=published)["selection_status"], "excluded")

    def test_uncertain_or_opinion_titles_excluded(self):
        for title in ("Apple could raise guidance", "Apple acquisition price target raised",
                      "Analysts expect Apple earnings growth", "Apple merger rumor"):
            with self.subTest(title=title):
                self.assertEqual(self.select(title=title)["selection_status"], "excluded")

    def test_ordinary_holdings_and_unclassified_headlines_excluded(self):
        for title in ("Fund buys 46,759 shares of Apple", "Apple streaming buzz"):
            self.assertEqual(self.select(title=title)["selection_status"], "excluded")

    def test_korean_real_event_and_delayed_flow_policy(self):
        changes = {"market": "KR", "symbol": "005930", "publisher": "연합뉴스",
                   "source_url": "https://www.yna.co.kr"}
        self.assertEqual(self.select(**changes, title="삼성전자 공급 계약 체결")["selection_status"], "selected")
        self.assertEqual(self.select(**changes, title="삼성전자 실적 발표에도 외국인 지분율 최저")["selection_status"], "excluded")

    def test_report_keeps_reasons_for_every_exclusion(self):
        report = filter_candidates([self.article, {**self.article, "publisher": "Unknown"}], self.policy, self.now)
        self.assertEqual(report["fetched_count"], 2)
        self.assertEqual(len(report["selected"]), 1)
        self.assertEqual(len(report["excluded"]), 1)
        self.assertTrue(report["excluded"][0]["selection_reasons"])

    def test_unknown_symbol_cannot_pass_without_company_alias(self):
        self.assertEqual(self.select(symbol="OTHER")["selection_status"], "excluded")

    def test_order_or_production_change_is_material_review_candidate(self):
        result = self.select(title="Apple cuts iPhone orders due to soft demand")
        self.assertEqual(result["selection_status"], "selected")
        self.assertIn("demand_or_production", result["impact_events"])
        self.assertFalse(result["confirmed"])

    def test_invalid_policy_fails_with_readable_value_error(self):
        broken = [[], {}, {**self.policy, "max_age_hours": True},
                  {**self.policy, "allowed_sources": {"KR": []}}]
        invalid_domain = copy.deepcopy(self.policy)
        invalid_domain["allowed_sources"]["US"][0]["domain"] = ".reuters.com"
        broken.append(invalid_domain)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "policy.json"
            for policy in broken:
                with self.subTest(policy=policy):
                    path.write_text(json.dumps(policy), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_filter_policy(path)
