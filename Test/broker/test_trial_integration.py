"""실제 어댑터·원장·축소 매도 경로를 합성 HTTP로 검사한다. 실제 계좌 주문 없음."""
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock,patch

from trading.orders import OrderManager
from trading.demo_session import LimitedDemoSession
from trading.execution_observation import observe_execution
from broker.demo_trial import TrialKisApi
from broker.managed_kis import ManagedKisAdapter
from Test.broker.test_kis_api import market_client
from Test.trading.test_review_regressions import event


class TrialReductionIntegration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.manager=OrderManager(Path(self.temp.name)/'orders.sqlite','kis_demo');self.addCleanup(self.manager.close)
        self.api=TrialKisApi(market_client('vps'),'00000000')
        self.adapter=ManagedKisAdapter(self.api,self.manager,'00000000','01',{'AAPL':'NASD'},enabled=False)
        self.session=LimitedDemoSession(self.manager,self.adapter,'synthetic-integration','AAPL')
        self.api.trial_session=self.session
        now=datetime.now(timezone.utc);self.stamp=now.isoformat()
        self.session.state['expires_at']=(now+timedelta(minutes=5)).isoformat()
        order={'id':'buy','symbol':'AAPL','side':'BUY','quantity':1,'price':'100','order_type':'LIMIT',
            'status':'ACCEPTED','filled':0,'notional':'0','broker_id':'20261027:123','quote_at':self.stamp,'stop_price':'98','created_at':self.stamp}
        self.manager.state['orders']['buy']=order
        self.session.state['order_ids']=['buy']
        self.session.state['contracts']['buy']={key:order[key] for key in ('symbol','side','quantity','price','order_type')}
        row=event(self.manager,quantity=1,filled=1);row.update(status='FILLED',remaining=0)
        observe_execution(self.manager,[row],{'positions':{'AAPL':1},'sellable':{'AAPL':1},'remote_reserved_sell':{},
            'broker_reserved_ids':[],'position_costs':{'AAPL':'100'}},observed_at=self.stamp,complete=True,source_hashes={'synthetic':'a'*64})
        regular=patch('trading.demo_session.regular_session',return_value={'end':now+timedelta(hours=1)})
        regular.start();self.addCleanup(regular.stop);self.addCleanup(self.session.disarm)

    def sell(self):
        self.session.prepare_reduction()
        self.session.create('sell','SELL',1,'101','0',self.stamp)
        self.session.submit('sell')

    def test_real_execution_stack_sends_one_synthetic_limit_sell_and_closes_permission(self):
        response=Mock();response.status=200;response.headers={};response.read.return_value=b'{"rt_cd":"0","output":{"ODNO":"124"}}'
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with patch('urllib.request.urlopen',return_value=response) as http:
            self.sell()
        self.assertEqual(http.call_count,1)
        request=http.call_args.args[0]
        self.assertIn('openapivts.koreainvestment.com',request.full_url)
        self.assertEqual(request.get_method(),'POST');self.assertEqual(json.loads(request.data)['ORD_QTY'],'1')
        self.assertEqual(self.manager.state['orders']['sell']['status'],'ACCEPTED')
        self.assertFalse(self.manager.ready);self.assertFalse(self.api._managed_permission)
        self.session.disarm();self.assertFalse(self.api.allow_trading)

    def test_lost_synthetic_sell_response_never_retries_and_disarms(self):
        with patch('urllib.request.urlopen',side_effect=TimeoutError('synthetic')) as http:
            with self.assertRaises(RuntimeError):self.sell()
            self.assertEqual(http.call_count,1)
        self.assertEqual(self.manager.state['orders']['sell']['status'],'UNKNOWN')
        self.assertFalse(self.session.armed);self.assertFalse(self.api.allow_trading)
