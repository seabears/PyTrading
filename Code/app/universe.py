"""사용자 지정과 일별 자동 선정을 분리한다. 주문 허가나 전략 최적화는 하지 않는다."""
import hashlib
import json
import math
import re
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.stateio import atomic_json
from broker.sessions import calendar_for
from paths import CONFIG_ROOT, DATA_ROOT
from trading.daily_account import last_closed_day

SYMBOL_PATTERN = re.compile(r"[A-Z][A-Z0-9.\-]{0,14}")


def load_policy(path=None):
    """금액은 USD, 비율은 0~1, 간격은 초다. 잘못된 설정은 자동 선정을 중지한다."""
    policy = json.loads(Path(path or CONFIG_ROOT / 'universe.json').read_text(encoding='utf-8'))
    integers = {'maximum_auto_symbols': (1, 300), 'ranking_per_exchange': (1, 300),
                'maximum_ranking_pages': (1, 10), 'minimum_spread_samples': (20, 100),
                'spread_sample_seconds': (60, 3600), 'retry_seconds': (60, 3600)}
    numbers = {'minimum_price_usd': (5, 1000), 'minimum_market_cap_usd': (2e9, 1e13),
               'minimum_turnover20_usd': (20e6, 1e12), 'minimum_turnover5_usd': (5e6, 1e12),
               'maximum_atr_ratio': (.001, .08), 'maximum_spread_ratio': (.00001, .002),
               'request_interval_seconds': (1, 10)}
    if set(policy) != {'enabled', *integers, *numbers} or type(policy['enabled']) is not bool:
        raise ValueError('universe_policy_fields_invalid')
    for name, (minimum, maximum) in {**integers, **numbers}.items():
        value = policy[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError('universe_policy_value_invalid')
        if name in integers and type(value) is not int:
            raise ValueError('universe_policy_integer_required')
    return policy


def policy_hash(policy):
    return hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()


def numeric(value, *, zero=False):
    number = float(value)
    if isinstance(value, bool) or not math.isfinite(number) or number < 0 or (number == 0 and not zero):
        raise ValueError('universe_invalid_number')
    return number


def evaluate_daily(bars, detail, required, policy):
    """최신 60거래일 품질→가격·유동성→ATR→시총·가격 정합성 순서로 검사한다.

    거래대금은 수정 종가×거래량 근삿값이다. 시총은 공식 상장주수(shar)×현재가(last)의
    계산값이다. 단위가 불명확한 tomv를 USD라고 추정해서 사용하지 않는다.
    """
    schedule = calendar_for('US', int(required[:4])).schedule.loc[:required]
    expected = [label.date().isoformat() for label in schedule.index[-60:]]
    dates = [bar['date'] for bar in bars]
    if len(dates) != len(set(dates)) or dates != sorted(dates):
        return {'passed': False, 'reason': 'duplicate_or_unordered_daily'}
    if not bars or dates[-1] != required or any(day > required for day in dates):
        return {'passed': False, 'reason': 'latest_completed_daily_missing'}
    if len(set(dates) & set(expected)) < 59 or len(bars) < 60:
        return {'passed': False, 'reason': 'daily_coverage_below_59_of_60'}
    if any(day not in set(label.date().isoformat() for label in schedule.index) for day in dates):
        return {'passed': False, 'reason': 'non_session_daily'}
    # 지표 계산에는 검증된 일봉만 받으며 0 거래량도 유동성 탈락 근거로 남긴다.
    for bar in bars[-61:]:
        opening, high, low, close = (numeric(bar[name]) for name in ('open', 'high', 'low', 'close'))
        numeric(bar['volume'], zero=True)
        if not low <= opening <= high or not low <= close <= high:
            return {'passed': False, 'reason': 'daily_ohlc_invalid'}
    close = bars[-1]['close']
    turnover20 = statistics.median(bar['close'] * bar['volume'] for bar in bars[-20:])
    turnover5 = min(bar['close'] * bar['volume'] for bar in bars[-5:])
    ranges = [max(bar['high']-bar['low'], abs(bar['high']-previous['close']), abs(bar['low']-previous['close']))
              for previous, bar in zip(bars[-15:-1], bars[-14:])]
    atr_ratio = statistics.mean(ranges) / close
    values = {'close': close, 'turnover20_usd_approx': turnover20, 'minimum_turnover5_usd_approx': turnover5,
              'atr_ratio': atr_ratio, 'valid_sessions60': len(set(dates) & set(expected)), 'signal_day': required}
    for passed, reason in [(close >= policy['minimum_price_usd'], 'price_below_minimum'),
                           (turnover20 >= policy['minimum_turnover20_usd'], 'median_turnover_below_minimum'),
                           (turnover5 >= policy['minimum_turnover5_usd'], 'recent_turnover_below_minimum'),
                           (atr_ratio <= policy['maximum_atr_ratio'], 'atr_above_maximum')]:
        if not passed:
            return dict(values, passed=False, reason=reason)
    if detail.get('curr') != 'USD' or detail.get('e_ordyn') != '매매 가능':
        return dict(values, passed=False, reason='currency_or_trade_permission_unconfirmed')
    shares = numeric(detail.get('shar'))
    last = numeric(detail.get('last'))
    if not shares.is_integer():
        return dict(values, passed=False, reason='listed_share_unit_unconfirmed')
    values['market_cap_usd_calculated'] = shares * last
    if values['market_cap_usd_calculated'] < policy['minimum_market_cap_usd']:
        return dict(values, passed=False, reason='market_cap_below_minimum')
    # 수정주가/실시간 가격이 크게 다르면 기업행동 또는 가격 급변 검토로 제외한다.
    if abs(numeric(detail.get('base')) / close - 1) > .2:
        return dict(values, passed=False, reason='corporate_action_or_price_mismatch')
    return dict(values, passed=True, reason='awaiting_regular_spread_samples')


def spread_result(samples, required, now, policy):
    """같은 정규장 20개 이상의 실제 신선한 호가만 사용한다. 합성·중복·미래 시각은 거절한다."""
    from broker.sessions import regular_session
    sessions = {}
    for row in samples:
        at = datetime.fromisoformat(row['at'])
        available = datetime.fromisoformat(row['quote_at'])
        session = regular_session('US', at)
        if not session or not 0 <= (now-at).total_seconds() or not 0 <= (at-available).total_seconds() <= 30:
            continue
        day = session['id'].split(':')[1]
        if day < required:
            continue
        bid, ask = numeric(row['bid']), numeric(row['ask'])
        if ask < bid:
            continue
        session_rows = sessions.setdefault(day, [])
        if not session_rows or (at-session_rows[-1][0]).total_seconds() >= policy['spread_sample_seconds']:
            session_rows.append((at, available.isoformat(), (ask-bid)/((ask+bid)/2)))
    if not sessions:
        return {'passed': False, 'reason': 'regular_spread_samples_missing', 'samples': 0}
    day = max(sessions)
    rows = sessions[day]
    # 같은 원천 호가를 다른 관측 시각으로 반복한 것은 새 표본이 아니다.
    unique = {row[1] for row in rows}
    median = statistics.median(row[2] for row in rows)
    passed = len(unique) >= policy['minimum_spread_samples'] and median <= policy['maximum_spread_ratio']
    return {'passed': passed, 'reason': 'eligible' if passed else 'insufficient_or_wide_spread',
            'samples': len(unique), 'median_spread_ratio': median, 'spread_day': day}


def publish_selection(folder, rows, required, now, policy, *, scope):
    """매일 목록을 교체한다. 탈락·조회 실패·검색 범위 이탈은 삭제 사유로 보존한다."""
    folder = Path(folder)
    previous_path = folder/'selection.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else {}
    passed = sorted((row for row in rows if row.get('passed')),
                    key=lambda row: (-row['turnover20_usd_approx'], row['symbol']))[:policy['maximum_auto_symbols']]
    selected = {row['symbol']: row['exchange'] for row in passed}
    old = previous.get('selected', {})
    reasons = {row['symbol']: row.get('reason', 'not_eligible') for row in rows}
    for row in rows:
        if row.get('passed') and row['symbol'] not in selected:
            reasons[row['symbol']] = 'below_selection_limit'
    removals = [{'symbol': symbol, 'reason': reasons.get(symbol, 'not_in_daily_search_scope')}
                for symbol in old if symbol not in selected]
    manifest = {'schema': 1, 'signal_day': required, 'published_at': now.isoformat(),
                'policy_hash': policy_hash(policy), 'selected': selected, 'scope': scope,
                'added': sorted(set(selected)-set(old)), 'removed': removals,
                'rows': rows, 'kind': 'actual_kis_daily_screen_not_buy_authorization'}
    # 날짜별 이력을 먼저 저장한다. 장애 시에도 오래된 목록을 무기한 사용하지 않는다.
    stamp = now.strftime('%Y%m%d-%H%M%S-%f')
    atomic_json(folder/'history'/required/(stamp+'.json'), manifest)
    atomic_json(previous_path, manifest, backup=True)
    return manifest


def selection_view(user_symbols, state, now, *, folder=None, policy=None, broker_orders=()):
    """사용자 지정+당일 유효 자동 선정+관리 전용. 보유·미체결은 제외돼도 계속 관찰한다."""
    policy = load_policy() if policy is None else policy
    folder = Path(folder or DATA_ROOT/'universe')
    user_symbols = list(dict.fromkeys(user_symbols))
    automatic = {}
    reason = 'disabled' if not policy['enabled'] else 'selection_missing'
    try:
        if policy['enabled']:
            manifest = json.loads((folder/'selection.json').read_text(encoding='utf-8'))
            published = datetime.fromisoformat(manifest['published_at'])
            if (manifest['signal_day'] == last_closed_day(now) and manifest['policy_hash'] == policy_hash(policy)
                    and 0 <= (now-published).total_seconds() <= 26*3600):
                automatic = manifest['selected']
                if not isinstance(automatic, dict) or any(not SYMBOL_PATTERN.fullmatch(s) or e not in {'NAS','NYS','AMS'} for s,e in automatic.items()):
                    raise ValueError('universe_selection_invalid')
                reason = 'current_selection'
                status_path = folder/'status.json'
                if status_path.exists():
                    status = json.loads(status_path.read_text(encoding='utf-8'))
                    if status.get('status') == 'failed' and datetime.fromisoformat(status['at']) >= published:
                        automatic = {}
                        reason = 'latest_screen_failed'
            else:
                reason = 'selection_expired_or_policy_changed'
    except (OSError, ValueError, KeyError, TypeError):
        automatic = {}
        reason = 'selection_unavailable'
    entries = list(dict.fromkeys(user_symbols + [('US', symbol) for symbol in automatic]))
    held = [tuple(key.split(':',1)) for key in state.get('positions',{})]
    plans = [tuple(row['symbol'].split(':',1)) for row in state.get('pending_daily',[])]
    from trading.orders import ACTIVE
    pending = [('US', row['symbol']) for row in broker_orders if row['status'] in ACTIVE]
    observed = list(dict.fromkeys(held + pending + plans + entries))
    return {'users': user_symbols, 'automatic': automatic, 'entry_symbols': entries,
            'observed_symbols': observed, 'management_only': [row for row in observed if row not in entries], 'reason': reason}


def current_entry_allowed(symbol, now):
    """증권사 전략 매수 전 최신 사용자·자동 목록을 재확인한다. 불명확하면 신규 매수만 차단한다."""
    from app.runtime import load_run_settings
    try:
        runtime = load_run_settings()
        view = selection_view(runtime['symbols'], {}, now)
        return ('US',symbol) in view['entry_symbols']
    except (OSError, ValueError, KeyError, TypeError):
        return False
