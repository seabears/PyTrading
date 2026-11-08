"""수동 편입 메뉴·신청·다음 실제 관측 경계 처리를 합성 자료로 검증한다."""
import copy
import json
import sqlite3
import unittest
from datetime import datetime,timedelta
from unittest.mock import patch

from trading.adoption_requests import list_positions,request_adoption,list_requests,apply_pending_requests


class AdoptionRequestTests(unittest.TestCase):
    def setUp(self):
        from Test.trading.test_strategy_adoption import StrategyAdoptionTests
        self.fixture=StrategyAdoptionTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.manager=self.fixture.manager;self.account=self.fixture.account
        self.selection={'mode':'kis_demo','fingerprint':'test-selection'}
        self.manager._strategy_execution_selection=self.selection
        current=patch('trading.adoption_requests.DATA_ROOT',self.root);current.start();self.addCleanup(current.stop)
        self.manager.state['alias']='strategies'
        self.account.state['last_signal_day']='2026-11-03'
        self.account.path.parent.mkdir(parents=True,exist_ok=True)
        self.account.path.write_text(json.dumps(self.account.state),encoding='utf-8')
        source=self.account.path.parent/'sources/2026-11-03/T.json';source.parent.mkdir(parents=True)
        source.write_text(json.dumps(self.fixture.record),encoding='utf-8')
        self.journal=self.root/'execution/kis_demo/strategy-orders.sqlite';self.journal.parent.mkdir(parents=True)
        self.write_journal()

    def write_journal(self):
        with sqlite3.connect(self.journal) as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS journal(id INTEGER PRIMARY KEY,body TEXT)')
            connection.execute('INSERT OR REPLACE INTO journal VALUES(1,?)',(json.dumps(self.manager.state),))

    def request(self):
        self.write_journal()
        return request_adoption(self.journal,self.account.path,self.selection,'manual-buy',now=self.fixture.now)

    def apply(self,now=None):
        return apply_pending_requests(self.manager,self.account,self.fixture.snapshot,now=now or self.fixture.now)

    def change_request(self,**changes):
        path=next((self.root/'management/adoption-requests').glob('*.json'))
        value=json.loads(path.read_text());value.update(changes);path.write_text(json.dumps(value),encoding='utf-8')

    def test_list_reads_only_and_request_requires_remote_validation(self):
        before=self.journal.read_bytes()
        rows=list_positions(self.journal,self.account.path)
        self.assertEqual(rows[0]['status'],'REQUESTABLE_REQUIRES_REMOTE_CHECK')
        self.assertTrue(rows[0]['requires_remote_validation'])
        self.assertEqual(before,self.journal.read_bytes())

    def test_request_writes_only_queue_without_http_or_order_mutation(self):
        original=copy.deepcopy(self.manager.state)
        with patch('urllib.request.urlopen',side_effect=AssertionError('no HTTP')) as network:
            request=self.request()
        self.assertEqual(request['status'],'QUEUED')
        self.assertEqual(request['quantity'],1)
        self.assertEqual(self.manager.state,original)
        network.assert_not_called()

    def test_repeated_request_reuses_pending_identifier(self):
        first=self.request();second=self.request()
        self.assertEqual(first['request_id'],second['request_id'])
        self.assertEqual(len(list_requests()),1)

    def test_diagnostic_scope_cannot_queue_management_mutation(self):
        from broker.diagnostic import diagnostic_scope
        with diagnostic_scope(),self.assertRaises(ValueError):self.request()
        self.assertEqual(list_requests(),[])

    def test_live_or_internal_selection_rejected(self):
        for mode in ['live','internal_paper','disabled']:
            self.selection['mode']=mode
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.request()

    def test_foreign_account_request_is_failed_without_adoption(self):
        self.request();self.change_request(account_fingerprint='other')
        self.assertEqual(self.apply(),0)
        self.assertEqual(list_requests()[0]['status'],'FAILED')
        self.assertNotIn('management_adoptions',self.manager.state)

    def test_selection_change_and_source_change_block(self):
        self.request();self.manager._strategy_execution_selection={'fingerprint':'changed'}
        self.apply();self.assertEqual(list_requests()[0]['status'],'FAILED')

    def test_changed_fill_contract_is_not_silently_adopted(self):
        self.request();self.manager.state['orders']['manual-buy']['notional']='99'
        self.apply();self.assertEqual(list_requests()[0]['status'],'FAILED')

    def test_expired_request_is_not_extended_when_read(self):
        self.request();self.apply(self.fixture.now+timedelta(hours=25))
        self.assertEqual(list_requests()[0]['status'],'EXPIRED')

    def test_queued_request_needs_current_process_observation(self):
        self.request();self.manager._execution_observation_valid=False
        self.assertEqual(self.apply(),0)
        self.assertEqual(list_requests()[0]['status'],'QUEUED')

    def test_matching_symbol_only_and_closed_source_needed(self):
        self.request();self.fixture.snapshot['symbol']='AAPL'
        self.assertEqual(self.apply(),0)
        self.fixture.snapshot['symbol']='T'
        source=self.account.path.parent/'sources/2026-11-03/T.json';source.unlink()
        self.assertEqual(self.apply(),0)
        self.assertEqual(list_requests()[0]['last_reason'],'closed_daily_source_unavailable')

    def test_apply_is_metadata_only_and_cost_gate_remains_closed(self):
        request=self.request()
        with patch('urllib.request.urlopen',side_effect=AssertionError('no HTTP')) as network:
            self.assertEqual(self.apply(),1)
        receipt=self.manager.state['management_adoptions']['manual-buy']
        self.assertEqual(receipt['operator_request']['request_id'],request['request_id'])
        self.assertEqual(list_requests()[0]['status'],'APPLIED')
        self.assertFalse(self.manager.ready)
        self.assertFalse(receipt['costs_finalized_by_adoption'])
        network.assert_not_called()

    def test_duplicate_processing_recovers_receipt_without_double_adoption(self):
        self.request();self.assertEqual(self.apply(),1)
        self.change_request(status='PROCESSING')
        self.assertEqual(self.apply(),0)
        self.assertEqual(list_requests()[0]['status'],'APPLIED')
        self.assertEqual(len(self.manager.state['management_adoptions']),1)
        self.assertEqual(len(self.manager.state['orders']),1)

    def test_sync_applies_request_then_rechecks_account_before_projection(self):
        self.request();port=self.fixture.port()
        with patch('trading.adoption_requests.datetime',wraps=datetime) as clock:
            clock.now.return_value=self.fixture.now
            result=port.sync(self.account,self.fixture.snapshot)
        self.assertTrue(result['observation_valid'])
        self.assertEqual(port.refresh.call_count,2)
        self.assertTrue(port.refresh.call_args.kwargs['force'])
        self.assertEqual(self.account.state['positions']['US:T']['quantity'],1)

    def test_menu_exit_does_not_queue_or_send(self):
        from manage_positions import main
        with patch('manage_positions.current_context',return_value=(self.journal,self.account.path,self.selection)),patch('builtins.input',return_value='0'),patch('builtins.print'),patch('urllib.request.urlopen') as network:
            self.assertEqual(main(),0)
        self.assertEqual(list_requests(),[]);network.assert_not_called()

    def test_menu_explicit_selection_creates_request_only(self):
        from manage_positions import main
        with patch('manage_positions.current_context',return_value=(self.journal,self.account.path,self.selection)),patch('builtins.input',side_effect=['1','편입']),patch('builtins.print'),patch('urllib.request.urlopen') as network:
            self.assertEqual(main(),0)
        self.assertEqual(len(list_requests()),1);network.assert_not_called()

    def test_menu_cancel_does_not_create_request(self):
        from manage_positions import main
        with patch('manage_positions.current_context',return_value=(self.journal,self.account.path,self.selection)),patch('builtins.input',side_effect=['1','취소']),patch('builtins.print'):
            self.assertEqual(main(),0)
        self.assertEqual(list_requests(),[])
