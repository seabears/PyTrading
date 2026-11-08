"""갱신100건 제한·비밀값 제외·미국 거래일별 판단을 외부 통신 없이 검증한다."""
import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.audit_logs import append_token_event, token_event, token_event_path, record_symbol_decision, signal_context
from broker.kis import KisMarketClient, KisApiError
from paths import CONFIG_ROOT


class TokenAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.cache = self.folder / "token.json"
        self.path = self.folder / "token-refresh.json"

    def payload(self):
        return {"access_token": "PRIVATE-TOKEN", "token_type": "Bearer", "expires_in": 86400}

    def test_101st_event_removes_only_oldest_and_preserves_order(self):
        events = [token_event("vps", 1000 + index, 2000 + index) for index in range(101)]
        for event in events:
            append_token_event(self.path, event)
        saved = json.loads(self.path.read_text())
        self.assertEqual(len(saved), 100)
        self.assertEqual(saved, events[1:])

    def test_retention_continues_one_by_one_beyond_100(self):
        events = [token_event("prod", 1000 + index, 2000 + index) for index in range(105)]
        for event in events:
            append_token_event(self.path, event)
        self.assertEqual(json.loads(self.path.read_text()), events[-100:])

    def test_same_pending_event_is_not_duplicated(self):
        event = token_event("vps", 1000, 2000)
        append_token_event(self.path, event)
        append_token_event(self.path, event)
        self.assertEqual(len(json.loads(self.path.read_text())), 1)

    def test_process_lock_prevents_concurrent_lost_updates(self):
        events = [token_event("vps", 1000, 2000) for _ in range(8)]
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda event: append_token_event(self.path, event), events))
        self.assertEqual({row["event_id"] for row in json.loads(self.path.read_text())}, {row["event_id"] for row in events})

    def test_operating_cache_uses_common_log_and_external_cache_is_isolated(self):
        with patch("app.audit_logs.DATA_ROOT", self.folder / "Data"):
            self.assertEqual(token_event_path(self.folder/"Data/cache/kis/vps/a.json"), self.folder/"Data/logs/token-refresh.json")
            self.assertEqual(token_event_path(self.folder/"Data/cache/kis/prod/b.json"), self.folder/"Data/logs/token-refresh.json")
        self.assertEqual(token_event_path(self.cache), self.path)
        self.assertIsNone(token_event_path(None))

    def test_success_is_logged_once_and_cache_reuse_does_not_add_rows(self):
        first = KisMarketClient("PRIVATE-KEY", "PRIVATE-SECRET", "vps", self.cache)
        with patch.object(first, "_request", return_value=self.payload()) as request:
            first.authenticate()
            first.authenticate()
        request.assert_called_once()
        second = KisMarketClient("PRIVATE-KEY", "PRIVATE-SECRET", "vps", self.cache)
        with patch.object(second, "_request", side_effect=AssertionError("no renewal")):
            second.authenticate()
        saved = json.loads(self.path.read_text())
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["event"], "token_issued")
        for secret in ["PRIVATE-KEY", "PRIVATE-SECRET", "PRIVATE-TOKEN"]:
            self.assertNotIn(secret, self.path.read_text())

    def test_failed_issuance_logs_safe_fields_not_exception_message(self):
        client = KisMarketClient("PRIVATE-KEY", "PRIVATE-SECRET", "vps", self.cache)
        failure = KisApiError("PRIVATE-TOKEN", http_status=403, category="http_error", provider_code="EGW00103")
        with patch.object(client, "_request", side_effect=failure):
            with self.assertRaises(KisApiError):
                client.authenticate()
        row = json.loads(self.path.read_text())[0]
        self.assertEqual(row["event"], "token_issue_failed")
        self.assertEqual(row["error"]["http_status"], 403)
        self.assertEqual(row["error"]["provider_code"], "EGW00103")
        self.assertNotIn("PRIVATE", self.path.read_text())

    def test_auth_cooldown_does_not_repeat_failure_event(self):
        client = KisMarketClient("key", "secret", "vps", self.cache)
        with patch.object(client, "_request", side_effect=KisApiError("failed")) as request:
            for _ in range(2):
                with self.assertRaises(KisApiError):
                    client.authenticate()
        request.assert_called_once()
        self.assertEqual(len(json.loads(self.path.read_text())), 1)

    def test_log_storage_retry_does_not_reissue_valid_token(self):
        client = KisMarketClient("key", "secret", "vps", self.cache)
        with patch.object(client, "_request", return_value=self.payload()) as request:
            with patch("app.audit_logs.append_token_event", side_effect=OSError("full")):
                with self.assertRaises(OSError):
                    client.authenticate()
            client.authenticate()
        request.assert_called_once()
        self.assertEqual(len(json.loads(self.path.read_text())), 1)

    def test_secondary_storage_failure_preserves_original_authentication_error(self):
        client = KisMarketClient("key", "secret", "vps", self.cache)
        failure = KisApiError("private", category="http_error", http_status=403)
        with patch.object(client, "_request", side_effect=failure), patch("app.audit_logs.append_token_event", side_effect=OSError("full")), patch("builtins.print"):
            with self.assertRaises(KisApiError) as caught:
                client.authenticate()
        self.assertIs(caught.exception, failure)

    def test_atomic_replace_failure_preserves_existing_history(self):
        append_token_event(self.path, token_event("vps", 1000, 2000))
        before = self.path.read_bytes()
        with patch("app.stateio.os.replace", side_effect=OSError("full")):
            with self.assertRaises(OSError):
                append_token_event(self.path, token_event("vps", 1001, 2001))
        self.assertEqual(self.path.read_bytes(), before)

    def test_corrupt_history_is_not_silently_reset(self):
        self.path.write_text("broken")
        with self.assertRaises(ValueError):
            append_token_event(self.path, token_event("vps", 1000, 2000))
        self.assertEqual(self.path.read_text(), "broken")


class DailyDecisionLogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.account = SimpleNamespace(state={"positions": {}, "pending_daily": []})
        self.monitor = SimpleNamespace(state={"buy_halts": []})
        self.decision = {"action": "WAIT", "reason": "no_daily_plan"}

    def snapshot(self, stamp="2026-11-04T14:31:00+00:00", symbol="T"):
        return {"market": "US", "symbol": symbol, "now": stamp, "data_mode": "live_observation",
                "regular_session_open": True, "quote": {"bid": 20, "ask": 20.01, "available_at": stamp}}

    def write(self, snapshot=None):
        return record_symbol_decision(self.folder, snapshot or self.snapshot(), self.decision, self.account, self.monitor)

    def test_symbols_are_separate_and_korean_midnight_keeps_us_trading_day(self):
        first = self.write(self.snapshot("2026-11-04T23:59:00+09:00"))
        second = self.write(self.snapshot("2026-11-05T00:01:00+09:00"))
        other = self.write(self.snapshot("2026-11-05T00:01:00+09:00", "AAPL"))
        self.assertEqual(first, second)
        self.assertEqual(first.parent.name, "US-2026-11-04")
        self.assertEqual(len(first.read_text(encoding="utf-8").splitlines()), 2)
        self.assertNotEqual(first, other)

    def test_us_midnight_moves_to_new_daily_folder(self):
        first = self.write(self.snapshot("2026-11-05T04:59:00+00:00"))
        second = self.write(self.snapshot("2026-11-05T05:00:00+00:00"))
        self.assertNotEqual(first.parent, second.parent)
        self.assertEqual(second.parent.name, "US-2026-11-05")

    def test_only_permitted_decision_and_diagnostic_fields_are_saved(self):
        snapshot = self.snapshot()
        snapshot.update(appkey="PRIVATE-KEY", headers={"authorization": "PRIVATE-TOKEN"},
            error={"stage": "authentication", "category": "http_error", "http_status": 403,
                   "provider_code": "PRIVATE-ERROR", "body": "PRIVATE-SECRET"})
        self.decision["message"] = "PRIVATE-MESSAGE"
        path = self.write(snapshot)
        row = json.loads(path.read_text())
        self.assertEqual(row["error"]["stage"], "authentication")
        self.assertIsNone(row["error"]["provider_code"])
        self.assertNotIn("PRIVATE", path.read_text())

    def test_daily_log_keeps_over_100_decisions_and_restart_appends(self):
        for index in range(105):
            self.write(self.snapshot((datetime(2026,11,4,14,31,tzinfo=timezone.utc)+timedelta(seconds=index)).isoformat()))
        self.account = SimpleNamespace(state={"positions": {}, "pending_daily": []})
        path = self.write(self.snapshot("2026-11-04T14:40:00+00:00"))
        self.assertEqual(len(path.read_text().splitlines()), 106)

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            self.write(self.snapshot(symbol="../../secret"))

    def test_incomplete_tail_is_not_overwritten(self):
        path = self.write()
        path.write_text('{"broken":', encoding="utf-8")
        with self.assertRaises(OSError):
            self.write()
        self.assertEqual(path.read_text(), '{"broken":')

    def write_daily_source(self, symbol, count=211):
        end = datetime(2026,11,3,tzinfo=timezone.utc)
        candles=[]
        for index in range(count):
            close=100+index*.01
            candles.append({"timestamp":(end-timedelta(days=count-index-1)).isoformat(),
                "currency":"USD","openPrice":close,"highPrice":close+1,"lowPrice":close-1,
                "closePrice":close,"volume":1000})
        path=self.folder/'sources/2026-11-03'/(symbol+'.json')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({"interval":"1d","market":"US","candles":candles}),encoding="utf-8")

    def test_original_closed_daily_signal_explains_no_plan_without_mutating_account(self):
        self.write_daily_source("SPY")
        self.write_daily_source("T")
        self.write_daily_source("SPCX",100)
        self.account.candidate=json.loads((CONFIG_ROOT/'fixed-trend-study.json').read_text(encoding='utf-8'))['candidate']
        self.account.state.update(last_signal_day="2026-11-03",last_signal_observed_at="2026-11-04T13:00:00+00:00")
        before=copy.deepcopy(self.account.state)
        row=json.loads(self.write().read_text())
        self.assertEqual(row['signal']['bars'],211)
        self.assertEqual(row['signal']['reason'],'entry_signal_not_met')
        self.assertEqual(row['signal']['source_kind'],'stored_closed_daily_diagnostic_replay')
        self.assertEqual(row['signal']['original_plan_calculated_at'],"2026-11-04T13:00:00+00:00")
        self.assertEqual(signal_context(self.account,self.folder,'SPCX')['reason'],'insufficient_indicator_history')
        self.assertEqual(self.account.state,before)

    def test_missing_signal_source_is_explicitly_unavailable(self):
        self.account.candidate=json.loads((CONFIG_ROOT/'fixed-trend-study.json').read_text(encoding='utf-8'))['candidate']
        self.account.state['last_signal_day']='2026-11-03'
        row=json.loads(self.write().read_text())
        self.assertEqual(row['signal']['status'],'unavailable')

    def test_service_writes_success_and_lookup_failure_logs(self):
        from app.daily_service import observe_symbol
        self.account.observe_quote=Mock(return_value=self.decision)
        self.account.summary=Mock(return_value={})
        self.monitor.observe=Mock()
        self.monitor.error=Mock()
        client=Mock();client.last_timings={}
        quote=self.snapshot()['quote']
        with patch('app.daily_service.regular_session',return_value={'id':'US:2026-11-04'}), patch('app.daily_service.normalize_quote',return_value=quote):
            observe_symbol(client,{'us_exchanges':{'T':'NYS'}},self.account,self.monitor,self.folder,'T')
        client.get.side_effect=KisApiError('PRIVATE',stage='authentication',category='http_error',http_status=403)
        with patch('app.daily_service.regular_session',return_value={'id':'US:2026-11-04'}):
            observe_symbol(client,{'us_exchanges':{'T':'NYS'}},self.account,self.monitor,self.folder,'T')
        rows=[json.loads(line) for path in self.folder.glob('logs/decisions/*/T.jsonl') for line in path.read_text().splitlines()]
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['reason'],'no_daily_plan')
        self.assertEqual(rows[1]['error']['stage'],'authentication')
        self.assertNotIn('PRIVATE',json.dumps(rows))
