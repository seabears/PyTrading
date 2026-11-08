"""관찰 목록 TUI 합성 검사. 실제 인증·주문·계좌 변경을 사용하지 않는다."""
import copy
from contextlib import closing
import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from app.watchlist_tui_model import WatchlistModel, digest
from app.watchlist_tui import render, table_rows, fit, safe_text, run
from paths import CONFIG_ROOT


class FakeTerminal:
    def __init__(self,keys,answers=()):
        self.keys=iter(keys);self.answers=iter(answers);self.frames=[];self.closed=False
    def __enter__(self):return self
    def __exit__(self,*unused):self.closed=True
    def key(self,*unused):return next(self.keys,'q')
    def draw(self,text):self.frames.append(text)
    def prompt(self,text):return next(self.answers,'')


class WatchlistTuiTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.config=self.root/'Config';self.data=self.root/'Data'
        self.config.mkdir();self.data.mkdir()
        for name in ('settings.json','universe.json','product-policy.json','execution.json'):
            value=json.loads((CONFIG_ROOT/name).read_text(encoding='utf-8'))
            if name=='settings.json':value['symbols']=['US:AAPL','US:T']
            if name=='execution.json':
                for mode in value:value[mode]['enabled']=mode=='internal_paper'
            (self.config/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
        self.now=datetime(2026,11,5,13,tzinfo=timezone.utc)
        self.model=WatchlistModel(settings=self.config/'settings.json',config_root=self.config,data_root=self.data,clock=lambda:self.now)

    def test_initial_screen_reads_without_creating_account_or_network(self):
        before=list(self.data.rglob('*'))
        with patch('urllib.request.urlopen') as http:
            snapshot=self.model.snapshot()
        http.assert_not_called();self.assertFalse(snapshot['account_source_exists'])
        self.assertEqual(list(self.data.rglob('*')),before)
        self.assertEqual(len(snapshot['view']['users']),2)

    def test_all_five_tabs_render_without_private_fields(self):
        snapshot=self.model.snapshot()
        snapshot['runtime']['env_file']='PRIVATE_KEY_FILE_PATH'
        for tab in range(5):
            text=render(snapshot,tab,0,'화면 검사',100,30)
            self.assertIn('관찰 목록 관리',text);self.assertIn('화면 검사',text)
            self.assertNotIn('PRIVATE_KEY_FILE_PATH',text)
            self.assertLessEqual(len(text.splitlines()),30)

    def test_add_user_saves_only_symbols_and_original_backup(self):
        original=json.loads(self.model.settings.read_text(encoding='utf-8'))
        with patch('broker.product_policy.load_product_rules',return_value={'allowed_asset_types':['stock','bond','etf'],
              'verified_instruments':{'MSFT':{'asset_type':'stock'}}}), \
             patch('broker.kis_setup.load_kis_settings',return_value={'us_exchanges':{'MSFT':'NAS'}}), \
             patch('urllib.request.urlopen') as http:
            message=self.model.add_user('msft',digest(self.model.settings))
        changed=json.loads(self.model.settings.read_text(encoding='utf-8'))
        self.assertEqual(changed['symbols'],['US:AAPL','US:T','US:MSFT'])
        self.assertEqual({k:v for k,v in changed.items() if k!='symbols'},{k:v for k,v in original.items() if k!='symbols'})
        self.assertIn('재시작',message);http.assert_not_called()
        self.assertEqual(json.loads(self.model.settings.with_suffix('.json.previous').read_text(encoding='utf-8')),original)

    def test_unknown_symbol_is_not_added_or_registered(self):
        before=self.model.settings.read_bytes()
        with patch('broker.product_policy.load_product_rules',return_value={'verified_instruments':{}}):
            with self.assertRaises(ValueError):self.model.add_user('UNKNOWN',digest(self.model.settings))
        self.assertEqual(self.model.settings.read_bytes(),before)

    def test_disallowed_or_etf_symbol_not_added_by_stock_tui(self):
        for asset_type in ('etn','etf','future'):
            with patch('broker.product_policy.load_product_rules',return_value={'verified_instruments':{'TEST':{'asset_type':asset_type}}}):
                with self.assertRaises(ValueError):self.model.add_user('TEST',digest(self.model.settings))

    def test_missing_exchange_not_added(self):
        with patch('broker.product_policy.load_product_rules',return_value={'allowed_asset_types':['stock','bond','etf'],
            'verified_instruments':{'TEST':{'asset_type':'stock'}}}),patch('broker.kis_setup.load_kis_settings',return_value={'us_exchanges':{}}):
            with self.assertRaises(ValueError):self.model.add_user('TEST',digest(self.model.settings))

    def test_remove_user_does_not_touch_holdings_or_selection(self):
        account=self.data/'paper-daily-frozen/account.json';account.parent.mkdir()
        account.write_text('{"positions":{"US:AAPL":{"quantity":1}}}',encoding='utf-8')
        original=account.read_bytes()
        self.model.remove_user('US:AAPL',digest(self.model.settings))
        self.assertEqual(account.read_bytes(),original)
        self.assertEqual(self.model.snapshot()['view']['management_only'],[('US','AAPL')])

    def test_cannot_remove_last_symbol(self):
        self.model.remove_user('US:AAPL',digest(self.model.settings))
        with self.assertRaises(ValueError):self.model.remove_user('US:T',digest(self.model.settings))

    def test_toggle_changes_only_enabled(self):
        original=json.loads(self.model.policy_path.read_text())
        self.model.toggle(digest(self.model.policy_path))
        changed=json.loads(self.model.policy_path.read_text())
        self.assertEqual(changed['enabled'],not original['enabled'])
        self.assertEqual({k:v for k,v in changed.items() if k!='enabled'},{k:v for k,v in original.items() if k!='enabled'})

    def test_percent_edit_uses_percent_input_and_ratio_storage(self):
        self.model.edit_condition('maximum_atr_ratio','7',digest(self.model.policy_path))
        self.assertEqual(json.loads(self.model.policy_path.read_text())['maximum_atr_ratio'],.07)

    def test_existing_policy_bounds_and_nonfinite_values_remain_blocked(self):
        before=self.model.policy_path.read_bytes()
        for key,value in [('maximum_atr_ratio','9'),('minimum_price_usd','1'),('maximum_spread_ratio','NaN'),('maximum_auto_symbols','1.2')]:
            with self.assertRaises(ValueError):self.model.edit_condition(key,value,digest(self.model.policy_path))
        self.assertEqual(self.model.policy_path.read_bytes(),before)

    def test_stale_editor_rejects_overwrite(self):
        expected=digest(self.model.settings)
        raw=json.loads(self.model.settings.read_text());raw['symbols'].append('US:NVDA')
        self.model.settings.write_text(json.dumps(raw),encoding='utf-8')
        with self.assertRaises(ValueError):self.model.remove_user('US:AAPL',expected)
        self.assertIn('US:NVDA',json.loads(self.model.settings.read_text())['symbols'])

    def test_audit_failure_before_save_preserves_settings(self):
        before=self.model.settings.read_bytes()
        with patch('app.watchlist_tui_model.atomic_json',side_effect=OSError('disk')):
            with self.assertRaises(OSError):self.model.remove_user('US:AAPL',digest(self.model.settings))
        self.assertEqual(self.model.settings.read_bytes(),before)

    def test_audit_never_contains_full_credential_path_or_settings(self):
        self.model.remove_user('US:AAPL',digest(self.model.settings))
        text=next((self.data/'watchlist-tui/audit').glob('*.json')).read_text(encoding='utf-8')
        self.assertNotIn('env_file',text);self.assertNotIn('kis.env',text);self.assertNotIn('APP_SECRET',text)
        self.assertEqual(json.loads(text)['status'],'SAVED')

    def test_empty_or_corrupt_selection_does_not_crash_dashboard(self):
        self.model.folder.mkdir()
        (self.model.folder/'selection.json').write_text('corrupt',encoding='utf-8')
        snapshot=self.model.snapshot()
        self.assertTrue(snapshot['errors']);self.assertEqual(snapshot['view']['automatic'],{})

    def test_history_retains_removal_even_when_latest_record_has_no_delta(self):
        folder=self.model.folder/'history/2026-11-04';folder.mkdir(parents=True)
        (folder/'one.json').write_text(json.dumps({'published_at':self.now.isoformat(),'removed':[{'symbol':'GOOG','reason':'atr_above_maximum'}]}))
        (folder/'two.json').write_text(json.dumps({'published_at':self.now.isoformat(),'removed':[]}))
        rows=table_rows(self.model.snapshot(),2)
        self.assertTrue(any(row[1]=='GOOG' and row[3]=='변동성 상한 초과' for row in rows))

    def test_navigation_and_quit_do_not_mutate_files(self):
        before={p:p.read_bytes() for p in self.config.iterdir()}
        terminal=FakeTerminal(['2','3','4','5','left','right','down','n','p','r','q'])
        with patch('urllib.request.urlopen') as http:
            self.assertEqual(run(self.model,terminal),0)
        self.assertTrue(terminal.closed);http.assert_not_called()
        self.assertEqual(before,{p:p.read_bytes() for p in self.config.iterdir()})

    def test_delete_cancel_does_not_save(self):
        before=self.model.settings.read_bytes();terminal=FakeTerminal(['d','q'],['n'])
        run(self.model,terminal)
        self.assertEqual(self.model.settings.read_bytes(),before)

    def test_delete_confirmation_updates_selected_user(self):
        run(self.model,FakeTerminal(['d','q'],['y']))
        self.assertEqual(json.loads(self.model.settings.read_text())['symbols'],['US:T'])

    def test_control_sequences_are_removed_from_display(self):
        text=safe_text('GOOG\x1b[2J\nSECRET')
        self.assertNotIn('\x1b',text);self.assertNotIn('\n',text)

    def test_korean_width_and_small_terminal(self):
        self.assertEqual(fit('삼성',5),'삼성 ')
        self.assertLessEqual(len(render(self.model.snapshot(),0,0,'',30,10).splitlines()),1)

    def test_read_only_sqlite_is_not_rewritten(self):
        execution=json.loads((self.config/'execution.json').read_text())
        execution['internal_paper']['enabled']=False;execution['kis_demo']['enabled']=True
        (self.config/'execution.json').write_text(json.dumps(execution))
        ledger=self.data/'execution/kis_demo/strategy-orders.sqlite';ledger.parent.mkdir(parents=True)
        with closing(sqlite3.connect(ledger)) as connection:
            connection.execute('CREATE TABLE journal(id INTEGER PRIMARY KEY,body TEXT)')
            connection.execute('INSERT INTO journal VALUES(1,?)',(json.dumps({'orders':{'one':{'symbol':'GOOG','status':'ACCEPTED'}}}),))
            connection.commit()
        before=ledger.read_bytes();snapshot=self.model.snapshot()
        self.assertIn(('US','GOOG'),snapshot['view']['management_only'])
        self.assertEqual(ledger.read_bytes(),before)

    def test_audit_failure_after_config_commit_reports_saved_state(self):
        from app.stateio import atomic_json
        calls=[0]
        def writer(path,value,**options):
            calls[0]+=1
            if calls[0]==3:raise OSError('synthetic_audit_commit_failure')
            return atomic_json(path,value,**options)
        with patch('app.watchlist_tui_model.atomic_json',side_effect=writer):
            message=self.model.remove_user('US:AAPL',digest(self.model.settings))
        self.assertEqual(json.loads(self.model.settings.read_text())['symbols'],['US:T'])
        self.assertIn('설정은 저장',message);self.assertIn('감사 기록',message)

    def test_linux_keyboard_switch_does_not_flush_early_input(self):
        from app.watchlist_tui import Terminal
        from unittest.mock import Mock
        terminal=Terminal.__new__(Terminal);terminal.interactive=True
        termios=Mock();tty=Mock();stdin=Mock();stdin.fileno.return_value=3
        with patch.dict('sys.modules',{'termios':termios,'tty':tty}), \
             patch('app.watchlist_tui.os.name','posix'),patch('app.watchlist_tui.sys.stdin',stdin), \
             patch('app.watchlist_tui.select.select',return_value=([3],[],[])),patch('app.watchlist_tui.os.read',return_value=b'q'):
            self.assertEqual(terminal.key(),'q')
        tty.setcbreak.assert_called_once_with(3,termios.TCSANOW)
        termios.tcsetattr.assert_called_once_with(3,termios.TCSADRAIN,termios.tcgetattr.return_value)

    def make_draw_terminal(self):
        from app.watchlist_tui import Terminal
        terminal=Terminal();terminal.ansi=True
        return terminal

    def test_unchanged_frame_writes_nothing(self):
        import io,os
        terminal=self.make_draw_terminal();output=io.StringIO()
        with patch('app.watchlist_tui.sys.stdout',output),patch('app.watchlist_tui.shutil.get_terminal_size',return_value=os.terminal_size((80,24))):
            terminal.draw('same\nrow');output.seek(0);output.truncate(0)
            terminal.draw('same\nrow')
        self.assertEqual(output.getvalue(),'')

    def test_only_changed_row_is_sent_in_one_write(self):
        from unittest.mock import Mock
        import os
        terminal=self.make_draw_terminal();output=Mock()
        with patch('app.watchlist_tui.sys.stdout',output),patch('app.watchlist_tui.shutil.get_terminal_size',return_value=os.terminal_size((80,24))):
            terminal.draw('first\nold');output.reset_mock()
            terminal.draw('first\nnew')
        output.write.assert_called_once_with('\x1b[2;1Hnew\x1b[K')
        output.flush.assert_called_once()

    def test_shorter_row_erases_only_its_tail(self):
        import io,os
        terminal=self.make_draw_terminal();output=io.StringIO()
        with patch('app.watchlist_tui.sys.stdout',output),patch('app.watchlist_tui.shutil.get_terminal_size',return_value=os.terminal_size((80,24))):
            terminal.draw('long text');output.seek(0);output.truncate(0)
            terminal.draw('short')
        self.assertEqual(output.getvalue(),'\x1b[1;1Hshort\x1b[K')

    def test_removed_rows_are_cleared_without_screen_clear(self):
        import io,os
        terminal=self.make_draw_terminal();output=io.StringIO()
        with patch('app.watchlist_tui.sys.stdout',output),patch('app.watchlist_tui.shutil.get_terminal_size',return_value=os.terminal_size((80,24))):
            terminal.draw('keep\nremove\nremove');output.seek(0);output.truncate(0)
            terminal.draw('keep')
        self.assertEqual(output.getvalue(),'\x1b[2;1H\x1b[K\x1b[3;1H\x1b[K')
        self.assertNotIn('\x1b[2J',output.getvalue())

    def test_resize_repaints_without_full_screen_clear(self):
        import io,os
        terminal=self.make_draw_terminal();output=io.StringIO()
        with patch('app.watchlist_tui.sys.stdout',output),patch('app.watchlist_tui.shutil.get_terminal_size',side_effect=[os.terminal_size((80,24)),os.terminal_size((100,30))]):
            terminal.draw('row');output.seek(0);output.truncate(0)
            terminal.draw('row')
        self.assertIn('\x1b[1;1Hrow',output.getvalue())
        self.assertNotIn('\x1b[2J',output.getvalue())

    def test_prompt_invalidates_frame_even_after_cancel(self):
        import io,os
        terminal=self.make_draw_terminal();output=io.StringIO()
        with patch('app.watchlist_tui.sys.stdout',output),patch('app.watchlist_tui.shutil.get_terminal_size',return_value=os.terminal_size((80,24))),patch('builtins.input',return_value=''):
            terminal.draw('row');terminal.prompt('cancel')
            output.seek(0);output.truncate(0);terminal.draw('row')
        self.assertIn('\x1b[1;1Hrow',output.getvalue())
        self.assertNotIn('\x1b[2J',output.getvalue())

    def test_full_width_line_keeps_last_character(self):
        import io,os
        terminal=self.make_draw_terminal();output=io.StringIO()
        with patch('app.watchlist_tui.sys.stdout',output),patch('app.watchlist_tui.shutil.get_terminal_size',return_value=os.terminal_size((80,24))):
            terminal.draw('-'*80)
        self.assertTrue(output.getvalue().startswith('\x1b[1;1H'+'-'*80))
        self.assertNotIn('-'*80+'\x1b[K',output.getvalue())
