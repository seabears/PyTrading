"""합성 장애 검사. 실제 인증·주문·네트워크를 사용하지 않는다."""
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock
from broker.kis import KisMarketClient, KisApiError, TOKEN_PATH
from broker.kis_market import US_QUOTE
from app.operations import OperationMonitor

class QuoteRecoveryTests(unittest.TestCase):
    def test_auth_failure_across_thirty_symbols_does_not_sleep(self):
        client=KisMarketClient('synthetic-key','synthetic-secret')
        with patch.object(client,'_request',side_effect=KisApiError('private')), patch('broker.kis.time.sleep') as sleep:
            for _ in range(30):
                with self.assertRaises(KisApiError): client.authenticate()
            sleep.assert_not_called()

    def test_http_error_preserves_safe_code_and_stage(self):
        client=KisMarketClient('synthetic-key','synthetic-secret')
        error=urllib.error.HTTPError('https://invalid',403,'private',{},io.BytesIO(b'{"msg_cd":"EGW00103","msg1":"private-secret"}'))
        with patch('broker.kis.urllib.request.urlopen',side_effect=error):
            with self.assertRaises(KisApiError) as caught:client._request(TOKEN_PATH,token_request=True)
        self.assertEqual(caught.exception.http_status,403)
        self.assertEqual(caught.exception.provider_code,'EGW00103')
        self.assertEqual(caught.exception.stage,'authentication')
        self.assertNotIn('private',json.dumps(caught.exception.diagnostic()))

    def test_failed_get_has_fresh_elapsed_time(self):
        client=KisMarketClient('key','secret');client.last_timings={'total_seconds':999}
        with patch.object(client,'authenticate',side_effect=KisApiError('no')):
            with self.assertRaises(KisApiError):client.get(US_QUOTE,{'SYMB':'AAPL','EXCD':'NAS'})
        self.assertLess(client.last_timings['total_seconds'],1)
        self.assertIn('authentication_seconds',client.last_timings)

    def test_regular_gap_halts_and_fresh_quote_only_clears_own_halt(self):
        with tempfile.TemporaryDirectory() as folder:
            monitor=OperationMonitor(Path(folder));monitor.state['buy_halts']=['manual_stop']
            now=datetime(2026,10,29,14,tzinfo=timezone.utc)
            monitor.check_quote_health(now)
            self.assertIn('regular_quote_outage',monitor.state['buy_halts'])
            snapshot={'market':'US','symbol':'AAPL','now':now.isoformat(),'regular_session_open':True,'quote':{'available_at':now.isoformat()}}
            monitor.observe(snapshot,0.1)
            self.assertEqual(monitor.state['buy_halts'],['manual_stop'])

    def test_off_hours_no_false_outage(self):
        with tempfile.TemporaryDirectory() as folder:
            monitor=OperationMonitor(Path(folder));monitor.check_quote_health(datetime(2026,10,31,14,tzinfo=timezone.utc))
            self.assertNotIn('regular_quote_outage',monitor.state['buy_halts'])
            self.assertEqual(monitor.state['quote_health'],'outside_regular_session')

    def test_auth_recovers_after_cooldown_without_deleting_cache(self):
        client=KisMarketClient('key','secret')
        with patch('broker.kis.time.monotonic',return_value=100),patch.object(client,'_request',side_effect=KisApiError('denied')):
            with self.assertRaises(KisApiError):client.authenticate()
        with patch('broker.kis.time.monotonic',return_value=161),patch.object(client,'_request',return_value={'access_token':'synthetic','token_type':'Bearer','expires_in':3600}):
            client.authenticate()
        self.assertEqual(client.access_token,'synthetic')

    def test_normalization_failure_measures_new_duration_and_redacts_secret(self):
        from app.daily_service import observe_symbol
        with tempfile.TemporaryDirectory() as folder:
            account=Mock();account.state={'pending_daily':[]};monitor=Mock();journal=Mock()
            client=Mock();client.last_timings={}
            with patch('app.daily_service.regular_session',return_value={'id':'US:test'}),patch('app.daily_service.normalize_quote',side_effect=ValueError('private-key-secret')):
                observe_symbol(client,{'us_exchanges':{'AAPL':'NAS'}},account,monitor,Path(folder),'AAPL',journal)
            payload=journal.observe.call_args.args[0]
            self.assertEqual(payload['error']['stage'],'normalization')
            self.assertLess(payload['request_seconds'],1)
            self.assertNotIn('private-key-secret',json.dumps(payload))
            account.observe_quote.assert_not_called()

    def test_sqlite_secondary_failure_preserves_primary_diagnostic(self):
        import sqlite3,contextlib
        from app.daily_service import observe_symbol
        with tempfile.TemporaryDirectory() as folder:
            client=Mock();client.last_timings={};client.get.side_effect=KisApiError('private',stage='authentication',category='http_error',http_status=403)
            account=Mock();account.state={'pending_daily':[]};monitor=Mock();journal=Mock();journal.observe.side_effect=sqlite3.OperationalError('disk')
            output=io.StringIO()
            with patch('app.daily_service.regular_session',return_value={'id':'US:test'}),contextlib.redirect_stdout(output):
                observe_symbol(client,{'us_exchanges':{'AAPL':'NAS'}},account,monitor,Path(folder),'AAPL',journal)
            self.assertIn('authentication',output.getvalue());self.assertIn('journal_storage_failed',output.getvalue());self.assertNotIn('private',output.getvalue())

    def test_common_network_outage_only_sends_one_request(self):
        client=KisMarketClient('key','secret')
        with patch.object(client,'authenticate'),patch('broker.kis.urllib.request.urlopen',side_effect=urllib.error.URLError('private')) as network:
            for _ in range(30):
                with self.assertRaises(KisApiError):client.get(US_QUOTE,{'SYMB':'AAPL','EXCD':'NAS'})
            network.assert_called_once()

    def test_restart_preserves_halts_and_prior_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            first=OperationMonitor(Path(folder));first.state['buy_halts']=['manual_stop'];first.state['last_normal_observation_at']='2026-10-27T14:00:00+00:00';first.save()
            second=OperationMonitor(Path(folder))
            self.assertEqual(second.state['buy_halts'],['manual_stop'])
            self.assertEqual(second.state['last_normal_observation_at'],first.state['last_normal_observation_at'])
