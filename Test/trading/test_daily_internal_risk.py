"""내부 가상체결의 사용자 위험 상향. 실제 시세·계좌·주문 없이 검증한다."""
import json,math,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
from paths import CONFIG_ROOT
from trading.daily_account import DailyAccount
from trading.daily_risk import load_daily_risk,validate_fraction


class DailyInternalRiskTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.folder=Path(temporary.name)
        self.settings=json.loads((CONFIG_ROOT/'paper.json').read_text())
        self.candidate=json.loads((CONFIG_ROOT/'fixed-trend-study.json').read_text())['candidate']
        self.now=datetime(2026,11,5,15,50,tzinfo=timezone.utc)

    def account(self,fraction=.0025):
        account=DailyAccount(self.folder/'account.json',self.settings,self.candidate,
            process_started_at=self.now,maximum_trade_risk=fraction)
        account.state['pending_daily']=[{'id':'signal','symbol':'US:ISRG','side':'BUY','execution_day':'2026-11-05',
            'signal_day':'2026-11-04','close':482.1,'atr':16.228207142857134,'score':1}]
        return account

    def quote(self):
        return {'market':'US','symbol':'ISRG','now':self.now.isoformat(),'source':'synthetic','data_mode':'synthetic',
                'quote':{'available_at':self.now.isoformat(),'bid':472.92,'ask':472.94}}

    def test_old_twenty_five_dollar_limit_blocks_one_share(self):
        self.assertEqual(self.account().observe_quote(self.quote())['reason'],'safety_risk_or_exposure_limit')

    def test_user_fifty_percent_risk_buys_with_other_caps_intact(self):
        account=self.account(.5);result=account.observe_quote(self.quote())
        self.assertEqual(result['action'],'BUY');self.assertEqual(result['paper_fill']['quantity'],2)
        self.assertEqual(account.safety_policy['daily_loss_limit'],.02)
        self.assertEqual(account.safety_policy['maximum_order_fraction'],.1)
        self.assertEqual(account.safety_policy['maximum_exposure_fraction'],.5)
        self.assertEqual(account.safety_policy['maximum_trade_risk'],.5)
        self.assertLessEqual(-result['paper_fill']['cash_flow'],1000)

    def test_daily_loss_halt_is_not_removed(self):
        from trading.safety import begin_day
        account=self.account(.5);begin_day(account.state,'US',self.now,account.settings)
        account.state['safety_days']['US']['loss_halted']=True
        self.assertEqual(account.observe_quote(self.quote())['reason'],'safety_daily_loss_halt')

    def test_broker_modes_ignore_internal_file(self):
        path=self.folder/'risk.json';path.write_text(json.dumps({'scope':'internal_paper_only','maximum_trade_risk':.5}))
        self.assertEqual(load_daily_risk('internal_paper',path)['maximum_trade_risk'],.5)
        for mode in ('kis_demo','live','disabled'):
            self.assertEqual(load_daily_risk(mode,path)['maximum_trade_risk'],.0025)

    def test_override_cannot_be_attached_to_broker_adapter(self):
        from trading.execution import configure_account
        account=self.account(.5)
        with patch('broker.strategy_execution.StrategyDemoPort') as broker:
            with self.assertRaises(ValueError):configure_account(account,{'mode':'kis_demo'})
        broker.assert_not_called()

    def test_restart_preserves_money_and_does_not_duplicate_fill(self):
        account=self.account(.5);account.observe_quote(self.quote());cash=account.state['cash']['US']
        restored=DailyAccount(self.folder/'account.json',self.settings,self.candidate,maximum_trade_risk=.5)
        self.assertEqual(restored.state['cash']['US'],cash)
        self.assertEqual(len(restored.state['trades']),1)
        self.assertEqual(restored.observe_quote(self.quote())['reason'],'duplicate_observation')
        self.assertEqual(len(restored.state['trades']),1)

    def test_invalid_fractions_are_rejected(self):
        for value in (True,0,-1,.50001,float('nan'),float('inf')):
            with self.assertRaises(ValueError):validate_fraction(value)

    def test_wrong_scope_cannot_be_loaded(self):
        path=self.folder/'risk.json';path.write_text(json.dumps({'scope':'kis_demo','maximum_trade_risk':.5}))
        with self.assertRaises(ValueError):load_daily_risk('internal_paper',path)
