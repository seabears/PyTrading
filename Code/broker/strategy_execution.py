"""기존 전략의 주문 의도를 기존 KIS 모의 주문 관리자에 전달한다.

종목·수량은 전략 결과 그대로 사용한다. 한정 시험 runner와 강제 청산은 호출하지
않는다. 실제 전체 계좌 대조와 RiskLedger 검사가 실패하면 주문을 전송하지 않는다.
"""
import copy,json,time,sqlite3
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
from paths import CONFIG_ROOT,CODE_ROOT,DATA_ROOT
from broker.kis_readonly import ReadOnlyKisApi
from broker.kis_api.client import KisApiClient,KisApiError


class ManagedStrategyApi(ReadOnlyKisApi):
    """조회는 기존 redactor, 주문은 기존 managed 검사를 통과한 vps 주식만 허용한다."""
    def _require_selected_demo(self):
        from trading.execution import load_execution
        selected=getattr(self,'_execution_selection',None)
        if not selected:raise KisApiError('strategy_mode_binding_required')
        current=load_execution(selected['path'])
        if current['mode']!='kis_demo' or current['fingerprint']!=selected['fingerprint']:
            raise KisApiError('strategy_mode_changed_before_http')
        from broker.sessions import regular_session
        if regular_session('US',datetime.now(timezone.utc)) is None:
            raise KisApiError('strategy_regular_session_required_before_http')

    def execute(self,specification):
        if specification.method=='GET':return super().execute(specification)
        if (self.market_client.environment!='vps' or not self._managed_permission or not self.allow_trading
                or specification.name not in {'overseas_stock.order','overseas_stock.order_rvsecncl'}):
            raise KisApiError('strategy_unmanaged_or_live_post_blocked')
        self._require_selected_demo()
        return KisApiClient.execute(self,specification)
    def execute_managed(self,specification,manager,intent_id):
        # ReadOnly의 전송 금지는 일반 조회 도구에 그대로 둔다. 이 클래스만 원장 경로를 연다.
        self._require_selected_demo()
        order=manager.state['orders'].get(intent_id)
        if (manager.state['mode']!='kis_demo' or manager.state['alias']!='strategies'
                or not order or not order.get('strategy_owner')):
            raise KisApiError('strategy_managed_account_and_owner_required')
        return KisApiClient.execute_managed(self,specification,manager,intent_id)

    def _http(self,path,parameters,method,headers=None,*,order=False):
        if method=='GET':return super()._http(path,parameters,method,headers,order=order)
        if (self.market_client.environment!='vps' or not self._managed_permission or not self.allow_trading
                or path not in {'/uapi/overseas-stock/v1/trading/order','/uapi/overseas-stock/v1/trading/order-rvsecncl'}):
            raise KisApiError('strategy_post_permission_blocked')
        self._require_selected_demo()
        return KisApiClient._http(self,path,parameters,method,headers,order=order)


class StrategyDemoPort:
    """전략 전체가 같은 계좌 원장을 쓴다. 프로세스 간 동시 운용은 OS 잠금이 거절한다."""
    def __init__(self,selection,*,settlement_source_provider=None):
        if selection['mode']!='kis_demo':raise ValueError('strategy_vps_mode_required')
        from kis_preflight import read_demo_identity
        from broker.kis import KisMarketClient
        from broker.managed_kis import ManagedKisAdapter
        from broker.kis_setup import load_kis_settings
        from trading.orders import OrderManager
        from trading.demo_account import record_initial_reference
        path=Path(selection['settings']['kis_demo']['credentials_file']).expanduser()
        if not path.is_absolute():path=(CODE_ROOT/path).resolve()
        key,secret,account,product=read_demo_identity(path)
        client=KisMarketClient(key,secret,'vps')
        client.token_cache=DATA_ROOT/'cache/kis/vps'/('readonly-'+client.identity[:16]+'.json')
        self.api=ManagedStrategyApi(client,account)
        self.api._execution_selection=copy.deepcopy(selection)
        # 실제 원본 계약을 확인한 공급기만 주입한다. 기본은 없는 자료를 만들지 않는다.
        self.api.settlement_source_provider=settlement_source_provider
        self.manager=OrderManager(DATA_ROOT/'execution/kis_demo/strategy-orders.sqlite','kis_demo','strategies')
        try:
            options=load_kis_settings(CONFIG_ROOT/'kis.json')
            exchanges={symbol:{'NAS':'NASD','NYS':'NYSE','AMS':'AMEX'}[value] for symbol,value in options['us_exchanges'].items()}
            self.adapter=ManagedKisAdapter(self.api,self.manager,account,product,exchanges,enabled=False)
            reference=json.loads((CONFIG_ROOT/'kis-demo-session.json').read_text(encoding='utf-8'))['initial_reference']
            record_initial_reference(self.manager,reference)
        except BaseException:
            self.manager.close();raise
        self.manager._strategy_execution_selection=copy.deepcopy(selection)
        self.latest=None;self.refreshed=0

    def refresh(self,snapshot,*,force=False):
        # 프로세스 시작 뒤 추가된 자동 종목도 공식 분류 자료로 거래소를 연결한다.
        # 매수 허가는 만들지 않으며 기존 거래소 설정을 추정해서 바꾸지 않는다.
        symbol = snapshot['symbol']
        if symbol not in self.adapter.exchanges:
            from broker.universe_data import verified_stocks
            discovered = verified_stocks()
            if symbol not in discovered:
                raise ValueError('strategy_symbol_exchange_unverified')
            self.adapter.exchanges[symbol] = {'NAS':'NASD','NYS':'NYSE','AMS':'AMEX'}[discovered[symbol]['exchange']]
        if not force and self.latest and time.monotonic()-self.refreshed<10:return self.latest
        from trading.demo_port import DemoExecutionPort
        # 이 값은 여력 조회에 넣는 단가다. 한정 시험의 500USD 상한을 여기로 가져오지 않는다.
        price=str(snapshot['quote']['ask'])
        profile={'symbol':snapshot['symbol'],'buying_power_service':'unknown',
                 'maximum_gross_buy_commitments_usd':price,'risk_basis':'user_designated_strategy_demo'}
        self.latest=DemoExecutionPort(self.manager,self.adapter,profile,{},DATA_ROOT/'unused-recovery.json').refresh()
        self.refreshed=time.monotonic();return self.latest

    def sync(self,account,snapshot):
        from trading.broker_diagnostics import failed_result,record_failure
        started=time.monotonic();stage='account_refresh'
        before=copy.deepcopy(account.state)
        self.manager._broker_failure=None
        try:
            observed=self.refresh(snapshot)
            stage='account_contract' 
            if not getattr(self.manager,'_execution_observation_valid',False):
                return failed_result(self.manager,ValueError('account_observation_requires_review'),stage,started)
            # 사용자 수동 편입 신청도 현재 계좌·호가가 확인된 해당 종목에서만 처리한다.
            from trading.adoption_requests import apply_pending_requests
            applied = apply_pending_requests(self.manager, account, snapshot)
            if applied:
                self.refreshed = 0
                observed = self.refresh(snapshot, force=True)
                if not getattr(self.manager, '_execution_observation_valid', False):
                    raise ValueError('adoption_post_refresh_requires_review')
            # 내부 가상 체결을 이 원장으로 복사하지 않는다. 원격에서 확인한 자기 체결만 사용한다.
            stage='position_projection'
            owner=str(account.path.relative_to(DATA_ROOT));orders=list(self.manager.state['orders'].values())
            own=[order for order in orders if order.get('strategy_owner')==owner]
            positions={};confirmed=[]
            for symbol in {order['symbol'] for order in own}:
                buys=[order for order in own if order['symbol']==symbol and order['side']=='BUY']
                sells=[order for order in own if order['symbol']==symbol and order['side']=='SELL']
                bought=sum(order['filled'] for order in buys);sold=sum(order['filled'] for order in sells)
                remaining=bought-sold
                if remaining<0:raise ValueError('strategy_owned_position_mismatch')
                if not remaining:continue
                from trading.strategy_posttrade import owned_position_basis
                basis=owned_position_basis(self.manager,owner,symbol,observed['report']['inventory'],account.settings['buy_cost_ratio'])
                unit_reserved=float(Decimal(basis['cost'])/Decimal(remaining))
                unit=unit_reserved
                prior=account.state['positions'].get('US:'+symbol,{})
                position={**prior,'market':'US','symbol':symbol,'quantity':remaining,
                    'average_cost':unit_reserved,'cost_basis':float(Decimal(basis['cost'])),
                    'peak_bid_since_entry':max(prior.get('peak_bid_since_entry',unit),unit),
                    'entry_at':basis['entry_at'] or prior.get('entry_at',buys[-1]['created_at']),
                    'actual_costs_final':basis['costs_final']}
                if hasattr(account,'candidate'):
                    details=next((order.get('strategy_position',{}) for order in reversed(buys) if order.get('strategy_position')), {})
                    if not {'daily_stop','daily_peak','entry_day','signal_day'}<=details.keys():
                        raise ValueError('daily_broker_position_metadata_missing')
                    position={**details,**position}
                positions['US:'+symbol]=position
            for order in own:
                if order['filled']:confirmed.append({key:order[key] for key in ['id','symbol','side','filled','notional','status']})
            previous_symbols=set(account.state['positions'])
            account.state['positions']=positions;account.state['broker_confirmed_fills']=confirmed
            for key in previous_symbols-set(positions):account.state['last_exit_at'][key]=observed['observed_at']
            for order in own:
                if order['side']=='BUY' and order['filled']:
                    account.state['last_entry_signal_bar']['US:'+order['symbol']]=order.get('strategy_signal_at',order['quote_at'])
            stage='daily_plan_linkage'
            if 'pending_daily' in account.state:
                from trading.strategy_adoption import restore_adopted_exit_plans
                restore_adopted_exit_plans(self.manager, account)
                from trading.execution import fills_daily_plan
                account.state['pending_daily']=[plan for plan in account.state['pending_daily']
                    if not any(fills_daily_plan(order,plan,owner) for order in own)]
            model=observed['user_cash_account']
            # 전략 계산용 사용자 기준 자금이며 공식 현금·NAV로 표시하지 않는다.
            model_cash=model['cash_usd']
            if model_cash is None:model_cash=observed['cash_risk_review']['estimated_cash_after_cost_reserve_usd']
            if model_cash is not None:account.state['cash']['US']=float(model_cash)
            account.state['strategy_cash_basis']='user_model_with_cost_reserve_not_official_cash'
            account.state['broker_costs_pending']=list(model['orders_with_costs_pending'])
            account.state['broker_readiness']={'as_of':observed['observed_at'],
                'new_orders_allowed':observed['new_orders_allowed'],
                'risk_resolution':observed['resolution'],
                'costs_final':observed['settlement_complete'],'settlement_source':observed.get('settlement_source'),
                'posttrade':observed.get('strategy_posttrade')}
            stage='account_projection_storage'
            account.save()
            return {'observation_valid':True,'reason':'broker_execution_observed'}
        except (ValueError,OSError,RuntimeError,KeyError,TypeError,sqlite3.Error) as error:
            account.state=before
            self.manager.ready=False
            details=getattr(self.manager,'_broker_failure',None)
            if stage=='account_refresh' and isinstance(details,dict):
                return {'observation_valid':False,'reason':'broker_'+details['stage']+'_failed','broker_error':details}
            return failed_result(self.manager,error,stage,started)

    def cancel_entries(self,owner,symbol):
        """진입 무효/매도 신호 때 확인된 자기 미체결 매수만 취소한다. 접수를 최종 취소로 쓰지 않는다."""
        from trading.orders import ACTIVE
        outcomes=[]
        for order in list(self.manager.state['orders'].values()):
            if (order.get('strategy_owner')!=owner or order['symbol']!=symbol or order['side']!='BUY'
                    or order['status'] not in ACTIVE):
                continue
            # 증권사 전송 여부는 원장의 취소 상태로 판정한다. 과거 불리언은 감사용이다.
            # NOT_SENT/의도만 저장된 요청은 새 잔량 대조 뒤 재시도할 수 있다.
            # 응답 유실·접수·명시 거절은 자동 반복하지 않는다.
            if order.get('cancel_status') not in {None,'NOT_SENT'}:
                continue
            if not self.manager.can_cancel(order['id']):
                outcomes.append({'id':order['id'],'status':'CANCEL_IDENTITY_UNVERIFIED'});continue
            started=time.monotonic()
            try:
                self.adapter.enabled=True;self.api.allow_trading=True
                # OrderManager.cancel 자체가 전송 전 영속 의도를 기록한다.
                self.manager.cancel(order['id'],self.adapter)
                outcomes.append({'id':order['id'],'status':'CANCEL_REQUESTED_NOT_FINAL'})
            except (ValueError,OSError,RuntimeError,KeyError,TypeError,sqlite3.Error) as error:
                from trading.broker_diagnostics import failure_details,record_failure
                stage='cancel_preflight' if order.get('cancel_status')=='NOT_SENT' else 'cancel_transmission'
                details=record_failure(self.manager,failure_details(error,stage,started))
                outcomes.append({'id':order['id'],'status':'CANCEL_RECONCILIATION_REQUIRED','broker_error':details})
            finally:
                self.adapter.enabled=False;self.api.allow_trading=False;self.refreshed=0
        return outcomes

    def cancel_invalid_entry(self,account,snapshot,decision):
        """기존 전략이 진입을 무효화했을 때만 요청한다. 임의 시간 제한/추가 매수 규칙은 넣지 않는다."""
        if snapshot.get('universe_entry_allowed') is False:
            # 일부 매수가 체결돼 HOLD 중이어도 제외된 종목의 남은 매수 잔량은 취소 검사한다.
            # 체결된 보유를 매도하지 않으며 기존 취소 식별·잔량 검사를 그대로 통과해야 한다.
            return self.cancel_entries(str(account.path.relative_to(DATA_ROOT)),snapshot['symbol'])
        reason=decision['reason']
        invalid=reason in {'missed_open_window','entry_gap_cancelled','corporate_action_or_price_mismatch',
            'entry_conditions_not_met','operations_buy_halt','adverse_news','universe_no_longer_eligible'} or reason.startswith(('safety_','earnings_'))
        if decision['action']!='WAIT' or not invalid:return []
        return self.cancel_entries(str(account.path.relative_to(DATA_ROOT)),snapshot['symbol'])

    def submit(self,intent,snapshot):
        from trading.orders import ACTIVE
        # 키·계좌 원문이나 자유문 예외를 반환하지 않고 상태 코드만 실행 기록에 남긴다.
        started=time.monotonic();stage='account_refresh'
        self.manager._broker_failure=None
        try:
            observation=self.refresh(snapshot,force=True)
            if intent['side']=='SELL':
                # 부분 매수의 잔량은 취소 요청하되 확인된 체결 수량의 보호 매도를 막지 않는다.
                self.cancel_entries(intent['strategy'],intent['symbol'])
                observation=self.refresh(snapshot,force=True)
            if any(order['symbol']==intent['symbol'] and order['status'] in ACTIVE
                   and (intent['side']=='BUY' or order['side']=='SELL') for order in self.manager.state['orders'].values()):
                return {'status':'BLOCKED','reason':'broker_existing_order_requires_reconciliation'}
            if intent['side']=='BUY' and not observation['new_orders_allowed']:
                return {'status':'BLOCKED','reason':'broker_strategy_risk_evidence_required',
                        'evidence_status':observation['resolution'].get('reason','unproven')}
            if intent['side']=='BUY':
                # 선정 직후 제외될 수 있으므로 의도 저장 직전 다시 확인한다.
                from app.universe import current_entry_allowed
                if not current_entry_allowed(intent['symbol'], datetime.now(timezone.utc)):
                    return {'status':'BLOCKED','reason':'universe_no_longer_eligible'}
            stage='intent_creation' 
            order=self.manager.create(intent['id'],intent['symbol'],intent['side'],intent['quantity'],
                                      intent['price'],intent['stop_price'],intent['quote_at'])
            if order['status']!='INTENT':return {'status':order['status'],'reason':'broker_order_already_recorded'}
            order['strategy_owner']=intent['strategy']
            order['strategy_position']=copy.deepcopy(intent.get('strategy_position',{}))
            order['strategy_signal_at']=intent['signal_at']
            order['strategy_daily_plan_id']=intent.get('daily_plan_id')
            stage='intent_storage'
            self.manager._save()
            stage='order_transmission'
            self.adapter.enabled=True;self.api.allow_trading=True
            self.manager.dispatch(order['id'],self.adapter)
            self.refreshed=0
            return {'status':order['status'],'reason':'broker_acceptance_is_not_fill'}
        except (ValueError,OSError,RuntimeError,KeyError,TypeError,sqlite3.Error) as error:
            from trading.broker_diagnostics import failure_details,record_failure
            details=getattr(self.manager,'_broker_failure',None)
            if stage!='account_refresh' or not isinstance(details,dict):
                details=record_failure(self.manager,failure_details(error,stage,started))
            order=self.manager.state['orders'].get(intent.get('id'))
            return {'status':order['status'] if order else 'BLOCKED',
                    'reason':'broker_'+details['stage']+'_failed','broker_error':details}
        finally:
            self.adapter.enabled=False;self.api.allow_trading=False

    def close(self):
        self.adapter.enabled=False;self.api.allow_trading=False;self.manager.close()
