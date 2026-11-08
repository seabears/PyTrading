"""공식 REST 명세의 계약과 가짜 HTTP·시계로 구현 동작을 함께 검증한다."""
import argparse
import contextlib
import io
import json
import re
import unittest
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from broker.rate_limits import GroupRateLimiter, PATH_GROUPS
from broker.toss import TossApiError, TossMarketClient, collect_snapshot, parse_symbol
from paths import FIXTURES_ROOT
from strategy.engine import evaluate


class SpecTest(unittest.TestCase):
    def setUp(self):
        self.clock = 100.0
        self.waits = []
        self.limiter = GroupRateLimiter()
        self.spec = json.loads((FIXTURES_ROOT / "toss-rest-spec.json").read_text(encoding="utf-8"))

    def sleep(self, seconds):
        self.clock += seconds
        self.waits.append(seconds)

    def test_allowed_paths_use_official_groups(self):
        for path, group in PATH_GROUPS.items():
            template = re.sub(r"/market-indicators/[^/]+/", "/market-indicators/{symbol}/", path)
            method = "post" if path == "/oauth2/token" else "get"
            description = self.spec["paths"][template][method]["description"]
            self.assertIn(f"`{group}`", description)

    def test_groups_do_not_share_cooldown(self):
        with patch("broker.rate_limits.time.monotonic", side_effect=lambda: self.clock), \
             patch("broker.rate_limits.time.sleep", side_effect=self.sleep), \
             patch("broker.rate_limits.random.uniform", return_value=0):
            self.limiter.observe("/api/v1/market-calendar/US", {"Retry-After": "5"}, limited=True)
            self.limiter.acquire("/api/v1/orderbook")
            self.assertEqual(self.waits, [])
            self.limiter.acquire("/api/v1/market-calendar/KR")
            self.assertEqual(self.waits, [5])

    def test_server_limit_and_low_remaining_apply_on_success(self):
        with patch("broker.rate_limits.time.monotonic", side_effect=lambda: self.clock), \
             patch("broker.rate_limits.time.sleep", side_effect=self.sleep):
            self.limiter.observe("/api/v1/orderbook", {"x-ratelimit-limit": "2", "X-RateLimit-Remaining": "1", "X-RateLimit-Reset": "3"})
            self.limiter.acquire("/api/v1/orderbook")
            self.assertEqual(self.waits, [3])
            self.limiter.acquire("/api/v1/orderbook")
            self.assertAlmostEqual(self.waits[-1], 1.1 / 2)

    def test_invalid_header_values_do_not_corrupt_pacing(self):
        for value in ("0", "nan", "inf", "-1", "1.5", "wrong"):
            self.limiter.observe("/api/v1/orderbook", {"X-RateLimit-Limit": value})
            self.assertEqual(self.limiter.groups["MARKET_DATA"]["limit"], 15)

    def test_backoff_and_jitter_are_bounded(self):
        with patch("broker.rate_limits.random.uniform", return_value=0.2):
            delays = [self.limiter.observe("/api/v1/orderbook", {}, limited=True) for _ in range(8)]
        self.assertEqual(delays, [1.2, 2.2, 4.2, 8.2, 16.2, 32.2, 32.2, 32.2])
        self.limiter.observe("/api/v1/candles", {})
        self.assertEqual(self.limiter.groups["MARKET_DATA"]["consecutive_429"], 8)
        self.limiter.observe("/api/v1/orderbook", {})
        self.assertEqual(self.limiter.groups["MARKET_DATA"]["consecutive_429"], 0)

    def test_auth_accepts_short_positive_integer_lifetime(self):
        client = TossMarketClient("fake", "fake")
        with patch.object(client, "_request", return_value={"access_token": "fake", "token_type": "Bearer", "expires_in": 30}), \
             patch("broker.toss.time.monotonic", return_value=100):
            client.authenticate()
        self.assertEqual(client.token_valid_until, 127)

    def test_auth_rejects_invalid_token_type_and_lifetime(self):
        client = TossMarketClient("fake", "fake")
        payload = {"access_token": "fake", "token_type": "Bearer", "expires_in": 300}
        for field, value in (("token_type", "Basic"), ("token_type", None), ("expires_in", True), ("expires_in", 0), ("expires_in", 2.5)):
            with patch.object(client, "_request", return_value={**payload, field: value}), self.assertRaises(TossApiError):
                client.authenticate()

    def test_retry_refreshes_token_that_expired_while_waiting(self):
        client = TossMarketClient("fake", "fake")
        client.access_token = "old"
        client.token_valid_until = 101
        error = urllib.error.HTTPError("https://openapi.tossinvest.com/api/v1/orderbook", 429, "limit", {"Retry-After": "2"}, io.BytesIO(b""))
        success = io.StringIO('{"result": {"ok": true}}')
        success.headers = {}
        auth = io.StringIO('{"access_token": "new", "token_type": "Bearer", "expires_in": 3600}')
        auth.headers = {}
        with patch("broker.toss.time.monotonic", side_effect=lambda: self.clock), \
             patch("broker.toss.time.sleep", side_effect=self.sleep), \
             patch("broker.rate_limits.random.uniform", return_value=0), \
             patch("broker.toss.urllib.request.urlopen", side_effect=[error, auth, success]) as network, \
             contextlib.redirect_stdout(io.StringIO()):
            client.get("/api/v1/orderbook")
        requests = [call.args[0] for call in network.call_args_list]
        self.assertEqual(requests[-1].get_header("Authorization"), "Bearer new")
        self.assertEqual(requests[1].get_method(), "POST")

    def test_query_encoding_preserves_timezone_and_boolean(self):
        client = TossMarketClient("fake", "fake")
        client.token_valid_until = float("inf")
        stamp = "2026-03-25T09:00:00+09:00"
        with patch.object(client, "_request", return_value={"result": {}}) as request:
            client.get("/api/v1/candles", {"symbol": "005930", "interval": "1m", "count": 200, "before": stamp, "adjusted": "false"})
        url = request.call_args.args[0].full_url
        self.assertIn("%2B09%3A00", url)
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        self.assertEqual(query["before"], [stamp])
        self.assertEqual(query["adjusted"], ["false"])
        names = {item["name"] for item in self.spec["paths"]["/api/v1/candles"]["get"]["parameters"] if "name" in item}
        self.assertTrue(set(query) - {"symbol"} <= names)

    def test_kr_alphanumeric_code_is_supported(self):
        self.assertEqual(parse_symbol("KR:0101n0"), ("KR", "0101N0"))
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_symbol("KR:0101N00")

    def test_nullable_orderbook_is_wait_not_crash_or_fake_quote(self):
        now = datetime(2026, 10, 9, 14, 0, tzinfo=timezone.utc)
        calendar = {"today": {"date": "2026-10-09", "regularMarket": {
            "startTime": (now - timedelta(hours=1)).isoformat(), "endTime": (now + timedelta(hours=1)).isoformat()}}}
        client = Mock()
        client.get.side_effect = [calendar, {"candles": []}, {"timestamp": None, "currency": "USD", "asks": [], "bids": []}]
        with patch("broker.toss.datetime", wraps=datetime) as clock:
            clock.now.return_value = now
            snapshot = collect_snapshot(client, "US", "AAPL")
        self.assertIsNone(snapshot["quote"])
        self.assertEqual(evaluate(snapshot)["reason"], "quote_unavailable")
        self.assertEqual(self.spec["components"]["schemas"]["OrderbookResponse"]["properties"]["timestamp"]["type"], ["string", "null"])


if __name__ == "__main__":
    unittest.main()
