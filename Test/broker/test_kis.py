"""KIS 연결을 실제 인증키·네트워크 없이 검증한다. 달력만 설치된 로컬 자료를 사용한다."""
import contextlib
import io
import json
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from app.runtime import load_run_settings
from broker.credentials import read_credentials_file
from broker.kis import KisApiError, KisMarketClient, KisRateLimitError, READ_OPERATIONS, TOKEN_PATH
from broker.kis_market import collect_snapshot, collect_minutes, normalize_minute, normalize_quote
from broker.kis_setup import load_kis_settings
from broker.sessions import regular_session
from paths import CONFIG_ROOT
from strategy.engine import evaluate
from Test.sample_data import sample


def response(payload):
    return io.StringIO(json.dumps(payload))


def minute_row(moment, market="US"):
    if market == "US":
        return {"xymd": moment.strftime("%Y%m%d"), "xhms": moment.strftime("%H%M%S"),
                "open": "100", "high": "102", "low": "99", "last": "101", "evol": "10"}
    return {"stck_bsop_date": moment.strftime("%Y%m%d"), "stck_cntg_hour": moment.strftime("%H%M%S"),
            "stck_oprc": "100", "stck_hgpr": "102", "stck_lwpr": "99", "stck_prpr": "101", "cntg_vol": "10"}


class KisCredentialsTest(unittest.TestCase):
    def test_bom_quotes_and_equals_in_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fake.env"
            path.write_text('# comment\nKIS_APP_KEY="fake"\nKIS_APP_SECRET=\'a=b#c\'\n', encoding="utf-8-sig")
            self.assertEqual(read_credentials_file(path), ("fake", "a=b#c"))

    def test_invalid_file_never_leaks_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fake.env"
            for content in ("KIS_APP_KEY=fake", "KIS_APP_KEY=fake\nKIS_APP_SECRET='private", "KIS_APP_KEY=fake\nKIS_APP_KEY=private", "KIS_APP_KEY=fake\nKIS_APP_SECRET=\n"):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError) as caught:
                    read_credentials_file(path)
                self.assertNotIn("private", str(caught.exception))

    def test_existing_app_key_names_are_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fake.env"
            path.write_text("APP_KEY=fake\nAPP_SECRET=fake-secret", encoding="utf-8")
            self.assertEqual(read_credentials_file(path), ("fake", "fake-secret"))
            path.write_text("APP_KEY=fake\nKIS_APP_KEY=other\nAPP_SECRET=fake-secret", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_credentials_file(path)

    def test_toss_file_does_not_satisfy_kis_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fake.env"
            path.write_text("TOSS_CLIENT_ID=fake\nTOSS_CLIENT_SECRET=private", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_credentials_file(path)


class KisClientTest(unittest.TestCase):
    def test_json_auth_and_token_reuse(self):
        client = KisMarketClient("fake-key", "fake-secret")
        with patch("broker.kis.urllib.request.urlopen", return_value=response({"access_token": "fake-token", "token_type": "Bearer", "expires_in": 86400})) as network:
            client.authenticate()
            client.authenticate()
        network.assert_called_once()
        request = network.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/oauth2/tokenP"))
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data)["appkey"], "fake-key")
        self.assertEqual(request.get_header("Content-type"), "application/json")

    def test_cache_reused_by_new_client_and_bound_to_key(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "token.json"
            first = KisMarketClient("key", "secret", token_cache=path)
            with patch.object(first, "_request", return_value={"access_token": "cached", "token_type": "Bearer", "expires_in": 86400}):
                first.authenticate()
            second = KisMarketClient("key", "secret", token_cache=path)
            with patch.object(second, "_request", side_effect=AssertionError("must use cache")):
                second.authenticate()
            self.assertEqual(second.access_token, "cached")
            third = KisMarketClient("other-key", "secret", token_cache=path)
            self.assertFalse(third._load_cached_token())

    def test_expired_cache_not_used(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "token.json"
            client = KisMarketClient("key", "secret", token_cache=path)
            path.write_text(json.dumps({"identity": client.identity, "access_token": "old", "valid_until": time.time() - 1}), encoding="utf-8")
            self.assertFalse(client._load_cached_token())

    def test_request_uses_official_tr_id_and_no_account(self):
        client = KisMarketClient("fake-key", "fake-secret")
        client.access_token, client.token_valid_until = "fake-token", time.time() + 3600
        client.token_issued_at = time.time()
        path = "/uapi/overseas-price/v1/quotations/inquire-asking-price"
        with patch("broker.kis.urllib.request.urlopen", return_value=response({"rt_cd": "0", "output1": {}})) as network:
            client.get(path, {"EXCD": "NAS", "SYMB": "AAPL"})
        request = network.call_args.args[0]
        self.assertEqual(request.get_header("Tr_id"), "HHDFS76200100")
        self.assertEqual(request.get_header("Custtype"), "P")
        self.assertEqual(request.get_header("Authorization"), "Bearer fake-token")
        self.assertNotIn("CANO", request.full_url)

    def test_order_account_arbitrary_url_are_blocked_before_network(self):
        client = KisMarketClient("key", "secret")
        with patch("broker.kis.urllib.request.urlopen", side_effect=AssertionError("network")):
            for path in ("/uapi/domestic-stock/v1/trading/order-cash", "/uapi/domestic-stock/v1/trading/inquire-balance", "https://example.com"):
                with self.assertRaises(KisApiError):
                    client.get(path)

    def test_business_error_is_not_mistaken_for_success(self):
        client = KisMarketClient("key", "secret")
        path = next(iter(READ_OPERATIONS))
        with patch("broker.kis.urllib.request.urlopen", return_value=response({"rt_cd": "1", "msg1": "private-secret", "msg_cd": "unknown"})):
            with self.assertRaises(KisApiError) as caught:
                client._request(path)
        self.assertNotIn("private-secret", str(caught.exception))

    def test_http_rate_error_includes_kis_egw00201_on_500(self):
        client = KisMarketClient("key", "secret")
        error = urllib.error.HTTPError("https://example.com", 500, "error", {}, io.BytesIO(b'{"msg_cd":"EGW00201","msg1":"private"}'))
        with patch("broker.kis.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(KisRateLimitError):
                client._request(next(iter(READ_OPERATIONS)))

    def test_http_403_does_not_leak_body(self):
        client = KisMarketClient("key", "secret")
        error = urllib.error.HTTPError("https://example.com", 403, "error", {}, io.BytesIO(b'private-secret'))
        with patch("broker.kis.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(KisApiError) as caught:
                client._request(TOKEN_PATH, token_request=True)
        self.assertNotIn("private-secret", str(caught.exception))

    def test_limited_get_retries_only_once(self):
        client = KisMarketClient("key", "secret")
        with patch.object(client, "authenticate"), patch.object(client, "_request", side_effect=KisRateLimitError("limited")) as request, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(KisRateLimitError):
                client.get(next(iter(READ_OPERATIONS)))
        self.assertEqual(request.call_count, 2)

    def test_24_hour_boundary_and_server_expiry(self):
        client = KisMarketClient("key", "secret")
        issued = 100000.0
        expiry = issued + 100000
        for elapsed, expected in ((0, True), (86399, True), (86400, False), (86401, False), (-1, False)):
            with patch("broker.kis.time.time", return_value=issued + elapsed):
                self.assertEqual(client._token_is_reusable(issued, expiry), expected)
        with patch("broker.kis.time.time", return_value=issued + 100):
            self.assertFalse(client._token_is_reusable(issued, issued + 100))

    def test_issue_time_is_saved_and_restart_does_not_reissue(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "token.json"
            client = KisMarketClient("key", "secret", token_cache=path)
            with patch("broker.kis.time.time", return_value=100000.0), patch.object(client, "_request", return_value={"access_token": "fake", "token_type": "Bearer", "expires_in": 86400}):
                client.authenticate()
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(datetime.fromisoformat(saved["issued_at"]).timestamp(), 100000)
            self.assertEqual(datetime.fromisoformat(saved["expires_at"]).timestamp(), 186400)
            fresh = KisMarketClient("key", "secret", token_cache=path)
            with patch("broker.kis.time.time", return_value=186399), patch.object(fresh, "_request", side_effect=AssertionError("no reissue")):
                fresh.authenticate()
            self.assertEqual(fresh.access_token, "fake")

    def test_after_24_hours_token_is_reissued_and_time_updated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "token.json"
            client = KisMarketClient("key", "secret", token_cache=path)
            client.access_token, client.token_issued_at, client.token_valid_until = "old", 100000.0, 200000.0
            client._save_token()
            with patch("broker.kis.time.time", return_value=186400), patch.object(client, "_request", return_value={"access_token": "new", "token_type": "Bearer", "expires_in": 86400}) as request:
                client.authenticate()
            request.assert_called_once()
            self.assertEqual(client.access_token, "new")
            self.assertEqual(datetime.fromisoformat(json.loads(path.read_text(encoding="utf-8"))["issued_at"]).timestamp(), 186400)

    def test_legacy_cache_upgraded_without_token_request(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "token.json"
            client = KisMarketClient("key", "secret", token_cache=path)
            path.write_text(json.dumps({"identity": client.identity, "access_token": "legacy", "valid_until": 186400}), encoding="utf-8")
            with patch("broker.kis.time.time", return_value=100100), patch.object(client, "_request", side_effect=AssertionError("no auth")):
                client.authenticate()
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["issued_at_source"], "legacy_expiry_minus_24_hours")
            self.assertEqual(client.access_token, "legacy")

    def test_failed_auth_not_requested_more_than_once_per_minute(self):
        client = KisMarketClient("key", "secret")
        clock = [100.0]
        def sleep(seconds):
            clock[0] += seconds
        with patch("broker.kis.time.monotonic", side_effect=lambda: clock[0]), patch("broker.kis.time.sleep", side_effect=sleep) as pause, patch.object(client, "_request", side_effect=KisApiError("no token")) as network:
            for _ in range(2):
                with self.assertRaises(KisApiError):
                    client.authenticate()
        pause.assert_not_called()
        network.assert_called_once()
        self.assertEqual(client.next_token_request_at, 160.0)


class KisMarketTest(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 10, 22, 13, 30, tzinfo=timezone.utc)
        self.session = {"start": self.start, "end": self.start + timedelta(hours=6, minutes=30), "id": "US:2026-10-22"}

    def test_domestic_minute_uses_trade_volume_not_cumulative(self):
        row = minute_row(datetime(2026, 10, 22, 9, 0), "KR")
        row["acml_vol"] = "99999"
        normalized = normalize_minute(row, "KR", self.session)
        self.assertTrue(normalized["timestamp"].endswith("09:01:00+09:00"))
        self.assertEqual(normalized["volume"], "10")

    def test_domestic_pages_move_backward_and_do_not_stop_at_thirty(self):
        opening = datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc)
        session = {"start": opening, "end": opening + timedelta(hours=6), "id": "KR:2026-10-22"}
        from broker.kis_market import market_zone
        pages = []
        for offset in (90, 60, 30, 0):
            pages.append({"output2": [minute_row((opening + timedelta(minutes=index)).astimezone(market_zone("KR")), "KR") for index in reversed(range(offset, offset + 30))]})
        client = Mock()
        client.get.side_effect = pages
        candles = collect_minutes(client, "KR", "005930", "KRX", session, opening + timedelta(minutes=120), 8)
        self.assertEqual(len(candles), 120)
        self.assertEqual(client.get.call_count, 4)
        calls = client.get.call_args_list
        self.assertEqual(calls[1].args[1]["FID_INPUT_HOUR_1"], "102900")
        self.assertEqual(calls[0].args[1]["FID_COND_MRKT_DIV_CODE"], "J")

    def test_us_incomplete_minute_excluded_and_requests_120(self):
        from broker.kis_market import market_zone
        rows = [minute_row((self.start + timedelta(minutes=index)).astimezone(market_zone("US"))) for index in range(6)]
        client = Mock()
        client.get.return_value = {"output2": rows}
        candles = collect_minutes(client, "US", "AAPL", "NAS", self.session, self.start + timedelta(minutes=5, seconds=20), 1)
        self.assertEqual(len(candles), 5)
        self.assertEqual(client.get.call_args.args[1]["NREC"], "120")
        self.assertEqual(client.get.call_args.args[1]["NMIN"], "1")

    def test_near_future_quote_waits_without_fabricating_current_time(self):
        from broker.kis_market import wait_for_quote_time
        now = self.start
        quote = {"available_at": (now + timedelta(seconds=1)).isoformat()}
        with patch("broker.kis_market.time.sleep") as sleep, patch("broker.kis_market.datetime", wraps=datetime) as clock:
            clock.now.return_value = now + timedelta(seconds=1.1)
            result = wait_for_quote_time(quote, now)
            sleep.assert_called_once_with(1.05)
            self.assertGreaterEqual(result, datetime.fromisoformat(quote["available_at"]))
            quote["available_at"] = (now + timedelta(seconds=10)).isoformat()
            sleep.reset_mock()
            self.assertEqual(wait_for_quote_time(quote, now), now)
            sleep.assert_not_called()

    def test_us_quote_uses_korean_source_time(self):
        payload = {"output1": {"curr": "USD", "dymd": "20261022", "dhms": "223500"},
                   "output2": {"pbid1": "100", "pask1": "100.1", "vbid1": "20", "vask1": "30"}}
        quote = normalize_quote(payload, "US", self.session)
        self.assertEqual(quote["available_at"], "2026-10-22T22:35:00+09:00")
        self.assertEqual(quote["bid"], 100)
        payload["output1"]["dhms"] = ""
        self.assertIsNone(normalize_quote(payload, "US", self.session))

    def test_kr_quote_requires_quantity_and_source_time(self):
        session = {**self.session, "start": datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc)}
        payload = {"output1": {"aspr_acpt_hour": "093500", "bidp1": "100", "askp1": "101", "bidp_rsqn1": "20", "askp_rsqn1": "30"}}
        self.assertEqual(normalize_quote(payload, "KR", session)["available_at"], "2026-10-22T09:35:00+09:00")
        payload["output1"]["bidp_rsqn1"] = "0"
        self.assertIsNone(normalize_quote(payload, "KR", session))

    def test_closed_session_makes_no_http_call(self):
        client = Mock()
        with patch("broker.kis_market.regular_session", return_value=None):
            snapshot = collect_snapshot(client, "US", "AAPL", {})
        client.get.assert_not_called()
        self.assertEqual(evaluate(snapshot)["reason"], "outside_regular_session")

    def test_unknown_exchange_is_not_guessed(self):
        with patch("broker.kis_market.regular_session", return_value=self.session):
            with self.assertRaises(KisApiError):
                collect_snapshot(Mock(), "US", "UNKNOWN", {"us_exchanges": {}, "maximum_minute_pages": 1})

    def test_snapshot_aggregates_five_minutes_and_preserves_no_trade_mode(self):
        from broker.kis_market import market_zone
        rows = [minute_row((self.start + timedelta(minutes=index)).astimezone(market_zone("US"))) for index in range(5)]
        quote = {"output1": {"curr": "USD", "dymd": "20261022", "dhms": "223500"},
                 "output2": {"pbid1": "100", "pask1": "101", "vbid1": "10", "vask1": "10"}}
        client = Mock()
        client.get.side_effect = [{"output2": rows}, quote]
        now = self.start + timedelta(minutes=5, seconds=10)
        with patch("broker.kis_market.regular_session", return_value=self.session), patch("broker.kis_market.datetime", wraps=datetime) as clock:
            clock.now.return_value = now
            snapshot = collect_snapshot(client, "US", "AAPL", {"us_exchanges": {"AAPL": "NAS"}, "maximum_minute_pages": 1})
        self.assertEqual(len(snapshot["bars"]), 1)
        self.assertEqual(snapshot["bars"][0]["volume"], 50)
        self.assertFalse(snapshot["risk_budget_available"])
        self.assertEqual(snapshot["source"], "kis")


class KisCalendarTest(unittest.TestCase):
    def test_us_holiday_and_early_close(self):
        self.assertIsNone(regular_session("US", datetime(2026, 11, 26, 16, tzinfo=timezone.utc)))
        early = regular_session("US", datetime(2026, 11, 27, 17, tzinfo=timezone.utc))
        self.assertEqual(early["end"].hour, 18)
        self.assertIsNone(regular_session("US", datetime(2026, 11, 27, 18, tzinfo=timezone.utc)))

    def test_us_daylight_saving_boundary(self):
        summer = regular_session("US", datetime(2026, 10, 22, 15, tzinfo=timezone.utc))
        winter = regular_session("US", datetime(2026, 11, 2, 15, tzinfo=timezone.utc))
        self.assertEqual((summer["start"].hour, summer["start"].minute), (13, 30))
        self.assertEqual((winter["start"].hour, winter["start"].minute), (14, 30))

    def test_kr_holiday_and_closing_auction(self):
        self.assertIsNone(regular_session("KR", datetime(2026, 10, 9, 1, tzinfo=timezone.utc)))
        self.assertIsNotNone(regular_session("KR", datetime(2026, 10, 22, 6, 19, tzinfo=timezone.utc)))
        self.assertIsNone(regular_session("KR", datetime(2026, 10, 22, 6, 20, tzinfo=timezone.utc)))


class KisIntegrationTest(unittest.TestCase):
    def test_default_settings_are_kis_with_separate_account(self):
        settings = load_run_settings()
        self.assertEqual(settings["broker"], "kis")
        # 기본 Windows 설정은 보존하되 호스트 OS의 경로 해석을 검사한다.
        # Linux 서비스의 인증 경로는 별도 settings-linux.json 검사에서 확인한다.
        configured = Path(json.loads((CONFIG_ROOT / "settings.json").read_text(encoding="utf-8"))["env_file"])
        expected = configured if configured.is_absolute() else (CONFIG_ROOT.parent / "Code" / configured).resolve()
        self.assertEqual(settings["env_file"], expected)
        self.assertEqual(settings["output_dir"].name, "paper-kis")
        self.assertEqual(load_kis_settings(CONFIG_ROOT / "kis.json")["us_exchanges"]["AAPL"], "NAS")

    def test_kis_env_is_never_sent_to_legacy_toss_collector(self):
        from broker import legacy_toss
        with patch("app.runtime.load_run_settings", return_value={"broker": "kis"}), patch.object(legacy_toss, "_read_credentials", side_effect=AssertionError("no secrets")):
            with self.assertRaises(ValueError):
                legacy_toss.read_credentials(False, Path("fake.env"))

    def test_runner_selects_kis_without_toss_auth(self):
        from app import runner
        with tempfile.TemporaryDirectory() as folder:
            settings = load_run_settings()
            settings.update(watch=False, collect_news=False, output_dir=Path(folder), symbols=[("US", "AAPL")])
            with patch("app.runner.load_run_settings", return_value=settings), patch("app.runner.create_kis_client") as create, patch("app.runner.collect_kis_snapshot", return_value=sample()) as collect, patch("app.runner.read_credentials", side_effect=AssertionError("no toss credentials")), contextlib.redirect_stdout(io.StringIO()) as output:
                runner.main(argv=[])
            create.return_value.authenticate.assert_called_once()
            collect.assert_called_once()
            self.assertIn("KIS 인증 성공", output.getvalue())
            self.assertTrue((Path(folder) / "account.json").exists())


if __name__ == "__main__":
    unittest.main()
