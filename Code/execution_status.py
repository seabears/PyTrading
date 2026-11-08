"""실행 모드·주문·보유·비용 대기를 로컬에서 확인한다. API·주문·상태 저장은 없다."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from paths import DATA_ROOT, CODE_ROOT
from trading.execution import load_execution


def read_status(ledger, mode):
    """SQLite를 읽기 전용으로 연다. 계좌번호·키·원본 응답·계좌 지문은 출력하지 않는다."""
    result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'mode': mode,
              'live_transmission_locked': True, 'read_only': True,
              'ledger_present': Path(ledger).exists(), 'process_running': None,
              'new_orders_allowed': False, 'authorization': 'fresh_remote_reconciliation_required'}
    if Path('/proc').is_dir():
        expected = str(CODE_ROOT / 'daily_paper.py').encode()
        processes = []
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit(): continue
            try:
                arguments = (entry / 'cmdline').read_bytes().split(b'\0')
                if expected in arguments: processes.append(int(entry.name))
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                pass
        result['process_running'] = bool(processes)
        result['process_count'] = len(processes)
    if not result['ledger_present']:
        result['status'] = 'NO_BROKER_LEDGER'
        return result
    try:
        with sqlite3.connect(Path(ledger).resolve().as_uri() + '?mode=ro', uri=True) as connection:
            row = connection.execute('SELECT body FROM journal WHERE id=1').fetchone()
        if row is None: raise ValueError('empty_journal')
        state = json.loads(row[0])
        if state['mode'] != mode or state['alias'] != 'strategies':
            raise ValueError('different_account_scope')
        from trading.orders import ACTIVE
        orders = list(state['orders'].values())
        observation = state.get('execution_observation', {})
        evaluation = state.get('risk_ledger', {}).get('last_evaluation', {})
        settlement = state.get('strategy_settlement', {})
        pending = sum(bool(order.get('filled')) and state.get('demo_settlement', {}).get('orders', {})
                      .get(order.get('broker_id'), {}).get('final_costs_usd') is None for order in orders)
        result.update(status='LOCAL_SNAPSHOT_NOT_ORDER_AUTHORIZATION',
            last_account_observed_at=observation.get('as_of'),
            positions=observation.get('inventory', {}).get('positions'),
            active_order_count=sum(order['status'] in ACTIVE for order in orders),
            uncertain_order_count=sum(order['status'] in {'UNKNOWN', 'SENDING'} for order in orders),
            filled_order_count=sum(bool(order.get('filled')) for order in orders),
            costs_pending_order_count=pending,
            settlement_phase='COSTS_PENDING' if pending else settlement.get('phase', 'NO_SETTLEMENT_SOURCE'),
            model_cash_usd=evaluation.get('cash_balance'), model_nav_usd=evaluation.get('net_asset_value'),
            source_kind=evaluation.get('source_kind'),
            realized_pnl_after_cost_usd=evaluation.get('realized_pnl_after_cost'),
            unrealized_pnl_usd=evaluation.get('unrealized_pnl'),
            daily_loss_ratio=evaluation.get('daily_loss_ratio'),
            consecutive_losses=evaluation.get('consecutive_losses'),
            last_loss_at=evaluation.get('last_loss_at'),
            last_evaluation_eligible=evaluation.get('eligible'),
            observed_max_drawdown_ratio=evaluation.get('observed_max_drawdown_ratio'),
            settlement_source_reason=settlement.get('reason', 'normalized_final_cost_and_cash_provider_unavailable'),
            daily_halts={day: value.get('halted') for day, value in state.get('risk_ledger', {}).get('days', {}).items()},
            restore_gate_present=bool(state.get('restore_gate')),
            last_reconcile_error_code=state.get('last_reconcile_error', {}).get('code'),
            last_broker_failure=state.get('broker_last_failure'),
            settlement_provider_last_observation=state.get('settlement_provider_observation'))
    except (sqlite3.Error, ValueError, KeyError, TypeError):
        result['status'] = 'LEDGER_UNREADABLE_OR_SCOPE_MISMATCH'
    return result


def main():
    selected = load_execution()
    value = read_status(DATA_ROOT / 'execution' / selected['mode'] / 'strategy-orders.sqlite', selected['mode'])
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
