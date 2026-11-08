"""계좌 조회·대조·파일 저장의 실패 분류. 모든 계좌/HTTP는 합성이며 외부 연결은 없다."""
import copy
import io
import json
import contextlib
import sqlite3
import unittest
import urllib.error
from types import SimpleNamespace
from datetime import datetime,timezone
from unittest.mock import Mock,patch


class BrokerDiagnosticsTests(unittest.TestCase):
    def sync_fixture(self):
        from Test.trading.test_execution_review_three import ExecutionReviewThreeTests
        fixture=ExecutionReviewThreeTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        port,account,plan,owner=fixture.sync_fixture()
        return fixture,port,account

    def test_query_error_exposes_stage_and_never_exception_free_text(self):
        fixture,port,account=self.sync_fixture()
        port.refresh.side_effect=ValueError('secret-token account 12345678')
        outcome=port.sync(account,{})
        self.assertEqual(outcome['reason'],'broker_account_refresh_failed')
        self.assertEqual(outcome['broker_error']['stage'],'account_refresh')
        self.assertNotIn('secret-token',json.dumps(outcome))

    def test_projection_save_failure_restores_memory_and_has_separate_category(self):
        fixture,port,account=self.sync_fixture()
        before=copy.deepcopy(account.state)
        account.save.side_effect=OSError('secret-credentials-file')
        with patch('broker.strategy_execution.DATA_ROOT',fixture.folder):outcome=port.sync(account,{})
        self.assertEqual(outcome['broker_error']['category'],'projection_storage_error')
        self.assertEqual(account.state,before)
        self.assertNotIn('secret-credentials-file',json.dumps(outcome))

    def pipeline(self):
        from trading.demo_port import DemoExecutionPort
        manager=Mock();manager.state={'mode':'kis_demo','alias':'strategies',
            'broker_identity':'synthetic-test-account','orders':{}}
        api=SimpleNamespace(records=[])
        adapter=Mock();adapter.api=api;adapter.query_history.return_value=[]
        profile={'symbol':'AAPL','maximum_gross_buy_commitments_usd':'100','buying_power_service':'unknown'}
        return manager,adapter,DemoExecutionPort(manager,adapter,profile,{},'unused.json')

    def test_initial_history_and_balance_query_failures_have_different_stages(self):
        from broker.kis import KisApiError
        for query,stage in [('query_history','history_query_initial'),('query_balances','balances_query')]:
            manager,adapter,port=self.pipeline()
            getattr(adapter,query).side_effect=KisApiError('secret response',category='connection_error')
            with self.subTest(stage=stage),self.assertRaises(KisApiError):port.refresh()
            details=manager.state['broker_last_failure']
            self.assertEqual(details['stage'],stage);self.assertEqual(details['category'],'connection_error')
            self.assertFalse(manager.ready);self.assertFalse(manager._execution_observation_valid)
            self.assertNotIn('secret response',json.dumps(details))

    def test_normalization_failure_is_not_account_http_error(self):
        manager,adapter,port=self.pipeline();adapter.query_history.return_value=[{'private_key':'hidden'}]
        with self.assertRaises(KeyError):port.refresh()
        details=manager.state['broker_last_failure']
        self.assertEqual(details['stage'],'history_normalization')
        self.assertEqual(details['category'],'response_contract_error')

    def test_authentication_failure_preserves_http_and_allowlisted_provider_code(self):
        from broker.kis import KisApiError
        manager,adapter,port=self.pipeline()
        adapter.query_history.side_effect=KisApiError('Bearer super-secret',stage='authentication',
            category='http_error',http_status=403,provider_code='EGW00103')
        with self.assertRaises(KisApiError):port.refresh()
        details=manager.state['broker_last_failure']
        self.assertEqual(details['stage'],'authentication');self.assertEqual(details['http_status'],403)
        self.assertEqual(details['provider_code'],'EGW00103')
        self.assertNotIn('super-secret',json.dumps(details))

    def test_ledger_failure_and_projection_failure_are_separate(self):
        from trading.broker_diagnostics import failure_details
        ledger=failure_details(sqlite3.OperationalError('disk-full-secret'),'risk_ingest',0)
        projection=failure_details(OSError('path-secret'),'account_projection_storage',0)
        self.assertEqual(ledger['category'],'ledger_storage_error')
        self.assertEqual(projection['category'],'projection_storage_error')
        self.assertNotEqual(ledger['code'],projection['code'])

    def test_diagnostic_write_failure_keeps_primary_error_and_safe_console(self):
        from trading.broker_diagnostics import failure_details,record_failure
        from broker.kis import KisApiError
        manager=Mock();manager.state={};manager._save.side_effect=sqlite3.OperationalError('token-account-private')
        details=failure_details(KisApiError('password secret',category='http_error',http_status=403),'balances_query',0)
        with contextlib.redirect_stdout(io.StringIO()) as output:result=record_failure(manager,details)
        self.assertEqual(result['http_status'],403);self.assertEqual(result['stage'],'balances_query')
        self.assertEqual(result['secondary_code'],'diagnostic_storage_failed')
        self.assertNotIn('token-account-private',output.getvalue());self.assertNotIn('password',output.getvalue())

    def test_error_elapsed_time_does_not_reuse_previous_request_value(self):
        from trading.broker_diagnostics import failure_details
        with patch('trading.broker_diagnostics.time.monotonic',return_value=105):
            details=failure_details(ValueError('unclassified private error'),'snapshot_validation',100,104)
        self.assertEqual(details['elapsed_seconds'],5);self.assertEqual(details['step_seconds'],1)

    def test_unknown_category_stage_status_and_provider_are_not_exposed(self):
        from trading.broker_diagnostics import failure_details
        from broker.kis import KisApiError
        error=KisApiError('APP_KEY=secret',category='private-category',http_status='12345678')
        error.provider_code=['private-provider'];error.stage={'secret':'private-stage'}
        details=failure_details(error,'private-stage',0)
        self.assertEqual(details['category'],'api_error');self.assertEqual(details['stage'],'broker_processing')
        self.assertIsNone(details['http_status']);self.assertIsNone(details['provider_code'])
        self.assertNotIn('private',json.dumps(details))

    def test_sync_preserves_nested_query_stage_instead_of_overwriting_it(self):
        from trading.broker_diagnostics import failure_details
        from broker.kis import KisApiError
        fixture,port,account=self.sync_fixture()
        def failed_refresh(*args):
            error=KisApiError('secret',category='rate_limit',http_status=429,provider_code='EGW00201')
            port.manager._broker_failure=failure_details(error,'buying_power_query',0)
            raise error
        port.refresh.side_effect=failed_refresh
        outcome=port.sync(account,{})
        self.assertEqual(outcome['reason'],'broker_buying_power_query_failed')
        self.assertEqual(outcome['broker_error']['http_status'],429)

    def test_expected_unverified_observation_has_explicit_contract_failure(self):
        fixture,port,account=self.sync_fixture();port.manager._execution_observation_valid=False
        outcome=port.sync(account,{})
        self.assertEqual(outcome['reason'],'broker_account_contract_failed')
        self.assertEqual(outcome['broker_error']['code'],'account_observation_requires_review')

    def test_common_http_failure_has_structured_fields_without_error_body(self):
        from broker.kis_api.client import KisApiClient,KisApiError
        from Test.broker.test_kis_api import market_client,sample_request
        from trading.broker_diagnostics import failure_details
        client=KisApiClient(market_client('prod'))
        error=urllib.error.HTTPError('private-url',403,'private-msg',{},
            io.BytesIO(b'{"msg_cd":"EGW00103","msg1":"secret-account-private"}'))
        with patch('urllib.request.urlopen',side_effect=error),self.assertRaises(KisApiError) as raised:
            client.execute(sample_request())
        details=failure_details(raised.exception,'balances_query',0)
        self.assertEqual(details['http_status'],403);self.assertEqual(details['provider_code'],'EGW00103')
        self.assertNotIn('secret-account-private',json.dumps(details))

    def test_json_decode_failure_is_distinct_from_connection_failure(self):
        from broker.kis_api.client import KisApiClient,KisApiError
        from Test.broker.test_kis_api import market_client,sample_request
        client=KisApiClient(market_client('prod'))
        response=Mock();response.__enter__=Mock(return_value=io.StringIO('not-json-private'))
        response.__exit__=Mock(return_value=False)
        with patch('urllib.request.urlopen',return_value=response),self.assertRaises(KisApiError) as raised:
            client.execute(sample_request())
        self.assertEqual(raised.exception.category,'response_decode_error')
        self.assertNotIn('private',str(raised.exception))

    def test_token_cache_storage_failure_is_authentication_stage(self):
        from broker.kis_api.client import KisApiClient,KisApiError
        from Test.broker.test_kis_api import market_client,sample_request
        client=KisApiClient(market_client('prod'))
        client.market_client.authenticate.side_effect=OSError('credentials-path-private')
        with patch('urllib.request.urlopen') as network,self.assertRaises(KisApiError) as raised:
            client.execute(sample_request())
        self.assertEqual(raised.exception.stage,'authentication')
        self.assertEqual(raised.exception.category,'token_storage_error');network.assert_not_called()

    def test_diagnostic_history_is_bounded_without_removing_orders(self):
        from trading.broker_diagnostics import failure_details,record_failure
        manager=Mock();manager.state={'orders':{'kept':{'status':'UNKNOWN'}}}
        for _ in range(105):record_failure(manager,failure_details(ValueError('private'),'risk_ingest',0))
        self.assertEqual(len(manager.state['broker_failure_history']),100)
        self.assertEqual(manager.state['orders'],{'kept':{'status':'UNKNOWN'}})

    def test_projection_and_diagnostic_write_failures_keep_original_failure(self):
        fixture,port,account=self.sync_fixture();before=copy.deepcopy(account.state)
        account.save.side_effect=OSError('private-account-path')
        port.manager._save.side_effect=sqlite3.OperationalError('private-ledger-path')
        with patch('broker.strategy_execution.DATA_ROOT',fixture.folder),contextlib.redirect_stdout(io.StringIO()) as output:
            outcome=port.sync(account,{})
        self.assertEqual(outcome['broker_error']['category'],'projection_storage_error')
        self.assertEqual(outcome['broker_error']['secondary_code'],'diagnostic_storage_failed')
        self.assertEqual(account.state,before)
        self.assertNotIn('private-account-path',output.getvalue());self.assertNotIn('private-ledger-path',output.getvalue())

    def test_execution_decision_keeps_structured_broker_failure(self):
        from Test.trading.test_execution_modes import SignalAccount
        from trading.execution import configure_account,load_execution
        fixture,_,_=self.sync_fixture()
        account=SignalAccount(fixture.folder/'signal.json');port=Mock()
        diagnostic={'stage':'balances_query','category':'http_error','http_status':403}
        port.sync.return_value={'observation_valid':False,'reason':'broker_balances_query_failed','broker_error':diagnostic}
        snapshot={'regular_session_open':True,'data_mode':'live_observation','source':'kis'}
        with patch('trading.execution.DATA_ROOT',fixture.folder):
            result=configure_account(account,load_execution(fixture.selection),port=port).observe_quote(snapshot)
        self.assertEqual(result['broker_error'],diagnostic);port.submit.assert_not_called()

    def test_readonly_status_contains_persisted_safe_failure(self):
        from trading.orders import OrderManager
        from trading.broker_diagnostics import record_failure,failure_details
        from execution_status import read_status
        fixture,_,_=self.sync_fixture();path=fixture.folder/'diagnostic.sqlite'
        manager=OrderManager(path,'kis_demo','strategies');self.addCleanup(manager.close)
        manager.state['broker_identity']='never-print-account-secret'
        record_failure(manager,failure_details(ValueError('history_changed_during_snapshot'),'snapshot_validation',0))
        value=read_status(path,'kis_demo')
        self.assertEqual(value['last_broker_failure']['code'],'history_changed_during_snapshot')
        self.assertNotIn('never-print-account-secret',json.dumps(value))
        self.assertIsNone(value['settlement_provider_last_observation'])
