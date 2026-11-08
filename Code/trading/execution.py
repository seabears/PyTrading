"""전략 판단과 체결 경로를 분리한다. 하나의 설정으로 모든 전략의 실행 방식을 고른다.

내부 모의는 기존 동작 그대로다. 증권사 모드에서는 판단용 복사본의 가상체결을
저장하지 않고 실제 주문 의도만 전달한다. 주문 접수는 체결로 기록하지 않는다.
실계좌 전송 잠금은 이 선택기와 별개이며 이번 단계에서 해제하지 않는다.
"""
from __future__ import annotations
import copy,hashlib,json,os
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
from paths import CODE_ROOT,CONFIG_ROOT,DATA_ROOT
from strategy.engine import parse_timestamp

MODES=('internal_paper','kis_demo','live')


def load_execution(path=None):
    """enabled는 진짜 JSON boolean만 받는다. 0개면 관측 전용, 2개 이상이면 거절한다."""
    path=Path(path or os.environ.get('PYTRADING_EXECUTION_CONFIG',CONFIG_ROOT/'execution.json'))
    values=json.loads(path.read_text(encoding='utf-8'))
    if set(values)!=set(MODES):raise ValueError('execution_modes_invalid')
    for mode,row in values.items():
        expected={'enabled'} if mode=='internal_paper' else {'enabled','credentials_file'}
        if not isinstance(row,dict) or set(row)!=expected or type(row['enabled']) is not bool:
            raise ValueError('execution_mode_fields_invalid')
        if mode!='internal_paper' and (not isinstance(row['credentials_file'],str) or not row['credentials_file'].strip()):
            raise ValueError('execution_credential_path_invalid')
    selected=[mode for mode in MODES if values[mode]['enabled']]
    if len(selected)>1:raise ValueError('execution_enable_only_one_mode')
    from broker.diagnostic import diagnostic_active
    mode='internal_paper' if diagnostic_active() else (selected[0] if selected else 'disabled')
    return {'mode':mode,'settings':values,
            'path':path.resolve(),'fingerprint':hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()}


def strategy_path(original,selection):
    """내부 계좌 경로는 보존한다. 모의/실계좌 전략 투영은 서로 다른 폴더에 둔다."""
    original=Path(original)
    if selection['mode']=='internal_paper':return original
    if not original.resolve().is_relative_to(DATA_ROOT.resolve()):raise ValueError('execution_account_outside_data')
    return DATA_ROOT/'execution-accounts'/selection['mode']/original.resolve().parent.relative_to(DATA_ROOT.resolve())/'account.json'


def strategy_signal_id(strategy,symbol,side,signal_at):
    """주문과 일봉 계획을 같은 불변 신호 ID로 연결한다. 종목만으로 계획을 삭제하지 않는다."""
    identity={'strategy':strategy,'symbol':symbol,'side':side,'signal_at':signal_at}
    return hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()


def fills_daily_plan(order,plan,owner):
    """같은 전략·계획·주문 신호의 실제 누적 체결만 계획 집행으로 인정한다.

    이전 버전의 strategy_signal_at=계획ID도 같은 주문 해시일 때만 허용한다.
    식별 근거가 없는 과거 체결은 추정해서 새 계획에 연결하지 않는다.
    """
    plan_id=plan.get('id')
    if (not plan_id or type(order.get('filled')) is not int or order['filled']<=0
            or order.get('strategy_owner')!=owner or 'US:'+order.get('symbol','')!=plan['symbol']
            or order.get('side')!=plan['side'] or order.get('strategy_signal_at')!=plan_id):
        return False
    explicit=order.get('strategy_daily_plan_id')
    if explicit is not None and explicit!=plan_id:return False
    return order.get('id')==strategy_signal_id(owner,order['symbol'],order['side'],plan_id)


def validate_projection(path,state,settings):
    """증권사 체결 투영을 내부 가상 cash-flow 항등식으로 검증하지 않는다.

    원격 관측 계좌는 별도 경로와 모드를 강제하고 가상 체결 혼입을 거절한다.
    이 파일을 읽었다는 것만으로 주문 권한을 만들지 않으며 매번 원격 대조한다.
    """
    from strategy.engine import require_number
    mode=state['execution_mode']
    if mode not in {'kis_demo','live','disabled'} or not Path(path).resolve().is_relative_to((DATA_ROOT/'execution-accounts'/mode).resolve()):
        raise ValueError('broker_projection_path_or_mode_invalid')
    if state.get('trades'):raise ValueError('paper_trades_in_broker_projection_prohibited')
    for market in ['US','KR']:require_number(state['cash'][market],allow_zero=True)
    for key,position in state['positions'].items():
        if type(position['quantity']) is not int or position['quantity']<1 or key!=position['market']+':'+position['symbol']:
            raise ValueError('broker_projection_quantity_invalid')
        for field in ['average_cost','cost_basis']:require_number(position[field],allow_zero=True)


def configure_account(account,selection,*,port=None):
    """전략 클래스는 유지하고 평가 메서드만 공통 라우터로 감싼다. replay에는 붙이지 않는다."""
    from broker.diagnostic import diagnostic_active
    if diagnostic_active() and selection['mode']!='internal_paper':
        raise ValueError('diagnostic_broker_account_prohibited')
    if selection['mode']=='internal_paper':return account
    # 내부 모의의 사용자 위험 상향을 증권사 계좌 계산/주문 경로로 넘기지 않는다.
    if getattr(account,'internal_daily_risk_override',False) is True:
        raise ValueError('internal_paper_risk_override_in_broker_mode_prohibited')
    return ExecutionAccount(account,selection,port=port)


class ExecutionAccount:
    """신호 원본 수량을 유지한다. 1주/500USD/즉시청산 같은 시험 규칙을 넣지 않는다."""
    def __init__(self,account,selection,*,port=None):
        object.__setattr__(self,'account',account);object.__setattr__(self,'selection',selection)
        object.__setattr__(self,'port',port);object.__setattr__(self,'execution_mode',selection['mode'])
        object.__setattr__(self,'_last_sync',None)
        # 현재 live는 주문 관리자/HTTP 경계도 차단한다. 선택했다고 안전 검사를 없애지 않는다.
        if self.execution_mode=='live':raise ValueError('live_strategy_transmission_locked')
        old=account.state.get('execution_mode',self.execution_mode)
        if old!=self.execution_mode:raise ValueError('execution_account_mode_mismatch')
        account.state['execution_mode']=self.execution_mode
        account.state.setdefault('broker_signals',{})
        account.save()

    def __getattr__(self,name):return getattr(self.account,name)
    def __setattr__(self,name,value):setattr(self.account,name,value)

    def _unchanged(self):
        if load_execution(self.selection['path'])['fingerprint']!=self.selection['fingerprint']:
            raise ValueError('execution_config_changed_restart_required')

    def _evaluate(self,snapshot,method,strategy=None):
        self._unchanged()
        if self.execution_mode=='kis_demo':
            if not snapshot.get('regular_session_open'):
                return {'action':'WAIT','reason':'outside_regular_session','execution_mode':self.execution_mode}
            if snapshot.get('data_mode')!='live_observation' or snapshot.get('source')!='kis':
                return {'action':'WAIT','reason':'broker_requires_actual_kis_observation','execution_mode':self.execution_mode}
            if self.port is None:
                from broker.strategy_execution import StrategyDemoPort
                object.__setattr__(self,'port',StrategyDemoPort(self.selection))
            # 조회를 실패/불완전 상태로 처리하면 기존 투영을 실제 체결인 것처럼 바꾸지 않는다.
            synchronized=self.port.sync(self.account,snapshot)
            if not synchronized.get('observation_valid'):
                return {'action':'WAIT','reason':synchronized['reason'],'execution_mode':self.execution_mode,
                        'broker_error':synchronized.get('broker_error')}
        # 기존 전략을 그대로 실행하되 복사본의 save와 가상체결은 운영 계좌에 반영하지 않는다.
        preview=copy.copy(self.account);preview.state=copy.deepcopy(self.account.state);preview.save=lambda:None
        result=(getattr(preview,method)(snapshot,strategy) if method=='evaluate_snapshot' else getattr(preview,method)(snapshot))
        result=copy.deepcopy(result);trade=result.pop('paper_fill',None)
        result['execution_mode']=self.execution_mode
        if not trade:
            # 호가/추적 보호선 등 비금융 상태는 저장한다. 현금·수량·거래는 원본을 유지한다.
            for key in ['last_prices','quote_times','quote_reference','last_processed_at','safety_days','pending_daily','corporate_action_suspicions']:
                if key in preview.state:self.account.state[key]=copy.deepcopy(preview.state[key])
            for key,position in self.account.state['positions'].items():
                proposed=preview.state['positions'].get(key,{})
                for field in ['daily_stop','daily_peak','peak_bid_since_entry']:
                    if field in proposed:position[field]=proposed[field]
            if self.execution_mode=='kis_demo' and hasattr(self.port,'cancel_invalid_entry'):
                result['broker_cancellations']=self.port.cancel_invalid_entry(self.account,snapshot,result)
            self.account.save();return result
        result['strategy_action']=trade['action'];result['strategy_quantity']=trade['quantity']
        result.update(action='WAIT',reason='execution_disabled' if self.execution_mode=='disabled' else 'broker_order_not_filled')
        if self.execution_mode=='disabled':return result
        quote=snapshot.get('quote') or {};now=parse_timestamp(snapshot['now'])
        if (not snapshot.get('regular_session_open') or not quote or snapshot.get('market')!='US'
                or not 0<=(now-parse_timestamp(quote['available_at'])).total_seconds()<=30):
            result['reason']='broker_quote_or_session_invalid';return result
        symbol=snapshot['symbol'];side=trade['action']
        plans=self.account.state.get('pending_daily',[])
        matching_plans=[row for row in plans if row['symbol']=='US:'+symbol and row['side']==side]
        if 'daily_plan_id' in result:
            # 일봉 전략 자신이 실제 판단에 사용한 계획 ID를 넘긴다. 보호 매도는 None이다.
            plan=result['daily_plan_id']
            if plan is not None and not any(row['id']==plan for row in matching_plans):
                raise ValueError('strategy_daily_plan_identity_mismatch')
        else:
            if len(matching_plans)>1:
                raise ValueError('strategy_daily_plan_identity_ambiguous')
            plan=matching_plans[0]['id'] if matching_plans else None
        signal_at=plan or ((snapshot.get('bars') or [{}])[-1].get('end') if side=='BUY' else None) or snapshot['now']
        identity={'strategy':str(self.account.path.relative_to(DATA_ROOT)),'symbol':symbol,'side':side,'signal_at':signal_at}
        identifier=strategy_signal_id(identity['strategy'],symbol,side,signal_at)
        before=self.account.state['broker_signals'].get(identifier)
        if before:
            result.update(reason='broker_signal_already_recorded',broker_signal_id=identifier,broker_status=before['status']);return result
        price=quote['ask' if side=='BUY' else 'bid']
        position=preview.state['positions'].get('US:'+symbol,{})
        stop=position.get('daily_stop')
        if stop is None:
            from strategy.engine import load_config
            stop=float(price)*(1-load_config(strategy)['stop_loss']) if side=='BUY' else 0
        intent={**identity,'id':identifier,'quantity':trade['quantity'],'price':str(price),'stop_price':str(stop),
                'quote_at':quote['available_at'],'observed_at':snapshot['now'],'reason':trade['reason'],'status':'RECORDED',
                'strategy_position':copy.deepcopy(position),'daily_plan_id':plan}
        self._unchanged()  # 계좌 조회 중 설정이 바뀌었어도 전송 의도 저장 전에 중지한다.
        self.account.state['broker_signals'][identifier]=intent
        # 전송 전에 저장한다. 이 지점 이후 응답이 유실돼도 같은 신호는 자동 재전송하지 않는다.
        self.account.save()
        try:
            outcome=self.port.submit(intent,snapshot)
        except Exception:
            outcome={'status':'UNKNOWN','reason':'broker_execution_requires_reconciliation'}
        intent.update(outcome);self.account.save()
        result.update(reason=outcome.get('reason','broker_order_not_filled'),broker_status=outcome['status'],broker_signal_id=identifier,
                      broker_error=outcome.get('broker_error'))
        # 체결 결과는 다음 sync의 원격 누적체결 대조로만 투영한다.
        return result

    def evaluate_snapshot(self,snapshot,strategy=None):return self._evaluate(snapshot,'evaluate_snapshot',strategy)
    def observe_quote(self,snapshot):return self._evaluate(snapshot,'observe_quote')
    def summary(self):
        return {'execution_mode':self.execution_mode,'financial_values_are_strategy_projection':True,
                'actual_fills':len(self.account.state.get('broker_confirmed_fills',[])),
                'signals':len(self.account.state['broker_signals']),'account_source':'broker_reconciliation_only','broker_readiness':self.account.state.get('broker_readiness')}
    def close(self):
        if self.port:self.port.close()
