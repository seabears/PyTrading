"""실제 계정·네트워크 없이 시세 정규화와 인증 정보 취급을 검증한다."""
import os
import getpass
import unittest
import warnings
import io
import urllib.error
import urllib.request
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from broker.toss import (
    TossApiError, TossMarketClient, aggregate_five_minute_bars,
    find_regular_session, parse_symbol,
    read_credentials,
    read_credentials_file,
)


def minute_candles():
    start = datetime(2026, 10, 9, 13, 30, tzinfo=timezone.utc)
    rows = []
    for index in range(10):
        rows.append({
            "timestamp": (start + timedelta(minutes=index + 1)).isoformat(),
            "openPrice": "100", "highPrice": "102", "lowPrice": "99",
            "closePrice": str(100 + index / 10), "volume": "10", "currency": "USD",
        })
    return start, rows


class AdapterTest(unittest.TestCase):
    def setUp(self):
        self.start, self.candles = minute_candles()
        self.session = {"start": self.start, "end": self.start + timedelta(hours=6), "id": "US:demo"}
        self.received = self.start + timedelta(minutes=10)

    def test_end_timestamp_and_reverse_order(self):
        bars = aggregate_five_minute_bars(list(reversed(self.candles)), self.session, self.received)
        self.assertEqual(len(bars), 2)
        self.assertEqual(bars[0]["start"], self.start.isoformat())
        self.assertEqual(bars[0]["volume"], 50)
        self.assertEqual(bars[0]["close"], 100.4)

    def test_missing_and_duplicate_minutes(self):
        for rows in (self.candles[1:], self.candles + [self.candles[0]]):
            bars = aggregate_five_minute_bars(rows, self.session, self.received)
            self.assertEqual(len(bars), 1)
            self.assertEqual(bars[0]["start"], (self.start + timedelta(minutes=5)).isoformat())

    def test_future_minutes_excluded(self):
        bars = aggregate_five_minute_bars(self.candles, self.session, self.start + timedelta(minutes=7))
        self.assertEqual(len(bars), 1)

    def test_outside_session_excluded(self):
        self.session["start"] += timedelta(minutes=5)
        bars = aggregate_five_minute_bars(self.candles, self.session, self.received)
        self.assertEqual(len(bars), 1)

    def test_calendar_offsets_and_previous_day(self):
        calendar = {"today": {"date": "2026-10-10", "regularMarket": None},
                    "previousBusinessDay": {"date": "2026-10-09", "regularMarket": {
                        "startTime": "2026-10-09T22:30:00+09:00",
                        "endTime": "2026-10-10T05:00:00+09:00"}}}
        current = datetime(2026, 10, 9, 18, tzinfo=timezone.utc)
        self.assertEqual(find_regular_session(calendar, "US", current)["id"], "US:2026-10-09")
        self.assertIsNone(find_regular_session(calendar, "US", current + timedelta(days=1)))

    def test_kr_auction_excluded(self):
        calendar = {"today": {"date": "2026-10-09", "integrated": {"regularMarket": {
            "startTime": "2026-10-09T09:00:00+09:00",
            "endTime": "2026-10-09T15:30:00+09:00",
            "singlePriceAuctionStartTime": "2026-10-09T15:20:00+09:00"}}}}
        self.assertIsNone(find_regular_session(calendar, "KR", datetime(2026, 10, 9, 6, 25, tzinfo=timezone.utc)))

    def test_missing_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(TossApiError):
                TossMarketClient()

    def test_auth_request_and_token_reuse(self):
        with patch.dict(os.environ, {"TOSS_CLIENT_ID": "fake-id", "TOSS_CLIENT_SECRET": "fake-secret"}):
            client = TossMarketClient()
        with patch.object(client, "_request", side_effect=[
            {"access_token": "fake-token", "token_type": "Bearer", "expires_in": 3600}, {"result": {"test": 1}},
        ]) as request_mock:
            self.assertEqual(client.get("/api/v1/orderbook", {"symbol": "AAPL"}), {"test": 1})
            auth_request = request_mock.call_args_list[0].args[0]
            self.assertEqual(auth_request.get_method(), "POST")
            self.assertIn(b"grant_type=client_credentials", auth_request.data)
            get_request = request_mock.call_args_list[1].args[0]
            self.assertEqual(get_request.get_method(), "GET")
            self.assertEqual(get_request.get_header("Authorization"), "Bearer fake-token")
        with self.assertRaises(TossApiError):
            client.get("/api/v1/orders")

    def test_symbol_validation(self):
        self.assertEqual(parse_symbol("us:brk.b"), ("US", "BRK.B"))
        self.assertEqual(parse_symbol("KR:005930"), ("KR", "005930"))

    def test_auth_403_identifies_ip_without_leaking_secrets(self):
        client = TossMarketClient("fake-id", "fake-secret")
        error = urllib.error.HTTPError(
            "https://openapi.tossinvest.com/oauth2/token", 403, "Forbidden", {},
            io.BytesIO(b'{"error":"access_denied","debug":"fake-secret"}'),
        )
        with patch("broker.toss.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(TossApiError) as caught:
                client.authenticate()
        self.assertIn("토큰 발급", str(caught.exception))
        self.assertIn("공인 IP", str(caught.exception))
        self.assertNotIn("fake-secret", str(caught.exception))

    def test_quote_403_is_not_labelled_as_token_failure(self):
        client = TossMarketClient("fake-id", "fake-secret")
        request = urllib.request.Request("https://openapi.tossinvest.com/api/v1/orderbook?symbol=AAPL")
        error = urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, io.BytesIO(b"private-debug"))
        with patch("broker.toss.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(TossApiError) as caught:
                client._request(request)
        self.assertIn("시세 조회", str(caught.exception))
        self.assertNotIn("private-debug", str(caught.exception))

    def test_private_prompt_does_not_set_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("broker.toss.sys.stdin.isatty", return_value=True):
                with patch("broker.toss.getpass.getpass", side_effect=["fake-id", "fake-secret"]) as prompt:
                    self.assertEqual(read_credentials(True), ("fake-id", "fake-secret"))
                    self.assertEqual(prompt.call_count, 2)
                    self.assertNotIn("TOSS_CLIENT_SECRET", os.environ)

    def test_credentials_environment_needs_no_prompt(self):
        with patch.dict(os.environ, {"TOSS_CLIENT_ID": "fake-id", "TOSS_CLIENT_SECRET": "fake-secret"}):
            with patch("broker.toss.getpass.getpass") as prompt:
                self.assertEqual(read_credentials(True), ("fake-id", "fake-secret"))
                prompt.assert_not_called()

    def test_redirected_input_does_not_prompt(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("broker.toss.sys.stdin.isatty", return_value=False):
                with self.assertRaises(TossApiError):
                    read_credentials(True)

    def test_visible_prompt_fallback_is_rejected(self):
        def cannot_hide_input(prompt):
            warnings.warn("cannot hide input", getpass.GetPassWarning)

        with patch.dict(os.environ, {}, clear=True):
            with patch("broker.toss.sys.stdin.isatty", return_value=True):
                with patch("broker.toss.getpass.getpass", side_effect=cannot_hide_input):
                    with self.assertRaises(TossApiError):
                        read_credentials(True)


class CredentialsFileTest(unittest.TestCase):
    """가짜 인증값으로만 테스트하며 실제 사용자의 env 파일은 읽지 않는다."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env_file = Path(self.directory.name) / "인증 파일.env"

    def write_file(self, contents, encoding="utf-8"):
        self.env_file.write_text(contents, encoding=encoding)

    def test_plain_file_and_special_characters(self):
        self.write_file("# comment\n\nTOSS_CLIENT_ID=fake-id\nTOSS_CLIENT_SECRET=a=b#c%PATH%$x\\y\n")
        self.assertEqual(read_credentials_file(self.env_file), ("fake-id", "a=b#c%PATH%$x\\y"))

    def test_bom_and_quoted_values(self):
        self.write_file('TOSS_CLIENT_ID = "fake-id"\nTOSS_CLIENT_SECRET=\'fake-secret\'\n', encoding="utf-8-sig")
        self.assertEqual(read_credentials_file(self.env_file), ("fake-id", "fake-secret"))

    def test_explicit_file_wins_without_environment_mutation(self):
        self.write_file("TOSS_CLIENT_ID=file-id\nTOSS_CLIENT_SECRET=file-secret\n")
        with patch.dict(os.environ, {"TOSS_CLIENT_ID": "env-id", "TOSS_CLIENT_SECRET": "env-secret"}):
            with patch("broker.toss.getpass.getpass") as prompt:
                self.assertEqual(read_credentials(True, self.env_file), ("file-id", "file-secret"))
                self.assertEqual(os.environ["TOSS_CLIENT_SECRET"], "env-secret")
                prompt.assert_not_called()

    def test_missing_file(self):
        with self.assertRaises(TossApiError):
            read_credentials_file(self.env_file)

    def test_missing_empty_duplicate_and_bad_format(self):
        invalid_files = [
            "TOSS_CLIENT_ID=fake-id\n",
            "TOSS_CLIENT_ID=fake-id\nTOSS_CLIENT_SECRET=\n",
            "TOSS_CLIENT_ID=fake-id\nTOSS_CLIENT_SECRET=fake-secret\nTOSS_CLIENT_SECRET=second-secret",
            "TOSS_CLIENT_ID=fake-id\nTOSS_CLIENT_SECRET='unclosed-secret",
            "fake-secret-with-no-key",
        ]
        for contents in invalid_files:
            with self.subTest(contents=contents):
                self.write_file(contents)
                with self.assertRaises(TossApiError) as caught:
                    read_credentials_file(self.env_file)
                self.assertNotIn("fake-secret", str(caught.exception))
                self.assertNotIn("unclosed-secret", str(caught.exception))
                self.assertNotIn("second-secret", str(caught.exception))

    def test_invalid_file_does_not_fall_back(self):
        self.write_file("TOSS_CLIENT_ID=file-id\n")
        with patch.dict(os.environ, {"TOSS_CLIENT_ID": "env-id", "TOSS_CLIENT_SECRET": "env-secret"}):
            with patch("broker.toss.getpass.getpass") as prompt:
                with self.assertRaises(TossApiError):
                    read_credentials(True, self.env_file)
                prompt.assert_not_called()



class RateLimitTest(unittest.TestCase):
    """가짜 시간·HTTP 응답으로 대기와 재시도를 검증한다. 실제 인증은 하지 않는다."""

    def setUp(self):
        self.clock = 100.0
        self.waits = []
        self.client = TossMarketClient("fake", "fake")
        self.client.access_token = "fake-token"
        self.client.token_valid_until = 10000
        self.request = urllib.request.Request("https://openapi.tossinvest.com/api/v1/orderbook")

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.clock += seconds

    def test_requests_are_paced(self):
        with patch("broker.toss.time.monotonic", side_effect=lambda: self.clock), \
             patch("broker.toss.time.sleep", side_effect=self.sleep), \
             patch("broker.toss.urllib.request.urlopen") as network:
            network.return_value.__enter__.return_value = io.StringIO('{"result": {}}')
            self.client._request(self.request)
            network.return_value.__enter__.return_value = io.StringIO('{"result": {}}')
            self.client._request(self.request)
        self.assertAlmostEqual(self.waits[0], 1.1 / 15)

    def test_429_retries_once_and_respects_server_wait(self):
        error = urllib.error.HTTPError(self.request.full_url, 429, "limited", {"Retry-After": "90"}, io.BytesIO(b""))
        import contextlib
        with patch("broker.toss.time.monotonic", side_effect=lambda: self.clock), \
             patch("broker.toss.time.sleep", side_effect=self.sleep), \
             patch("broker.toss.urllib.request.urlopen") as network, \
             contextlib.redirect_stdout(io.StringIO()):
            network.side_effect = [error, network.return_value]
            network.return_value.__enter__.return_value = io.StringIO('{"result": {"ok": true}}')
            self.assertEqual(self.client.get("/api/v1/orderbook"), {"ok": True})
        self.assertGreaterEqual(self.waits[0], 90.0)
        self.assertLess(self.waits[0], 90.3)
        self.assertEqual(network.call_count, 2)

    def test_repeated_429_stops_retry_and_preserves_cooldown(self):
        from broker.toss import TossRateLimitError
        import contextlib
        error = urllib.error.HTTPError(self.request.full_url, 429, "limited", {}, io.BytesIO(b""))
        with patch("broker.toss.time.monotonic", side_effect=lambda: self.clock), \
             patch("broker.toss.time.sleep", side_effect=self.sleep), \
             patch("broker.toss.urllib.request.urlopen", side_effect=error) as network, \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(TossRateLimitError):
                self.client.get("/api/v1/orderbook")
        self.assertEqual(network.call_count, 2)
        self.assertGreaterEqual(self.waits[0], 1.0)
        self.assertLess(self.waits[0], 1.3)
        remaining = self.client.rate_limiter.groups["MARKET_DATA"]["next_at"] - self.clock
        self.assertGreaterEqual(remaining, 2.0)
        self.assertLess(remaining, 2.3)

    def test_calendar_cache_expires_but_quotes_are_not_cached(self):
        with patch("broker.toss.time.monotonic", side_effect=lambda: self.clock), \
             patch.object(self.client, "_request", return_value={"result": {"day": 1}}) as request:
            calendar = "/api/v1/market-calendar/US"
            self.client.get(calendar)
            self.client.get(calendar)
            self.assertEqual(request.call_count, 1)
            self.clock += 31
            self.client.get(calendar)
            self.client.get("/api/v1/orderbook")
            self.client.get("/api/v1/orderbook")
            self.assertEqual(request.call_count, 4)

    def test_retry_header_validation(self):
        from broker.toss import retry_after_seconds
        for value in (None, "invalid", "-2", "nan", "inf"):
            self.assertIsNone(retry_after_seconds(value))
        self.assertEqual(retry_after_seconds("90"), 90)
        self.assertEqual(retry_after_seconds("0"), 0)
        from email.utils import format_datetime
        future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=90))
        self.assertGreater(retry_after_seconds(future), 85)


if __name__ == "__main__":
    unittest.main()
