"""일봉 위험 예산 설정. 사용자 지정 상향은 내부 가상체결에서만 읽는다."""
import hashlib
import json
import math
from pathlib import Path
from paths import CONFIG_ROOT

FROZEN_TRADE_RISK = 0.0025


def validate_fraction(value):
    """비율 단위다. 0.5는 50%이며, bool·NaN·무한대는 받지 않는다."""
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0 < value <= .5:
        raise ValueError('daily_trade_risk_fraction_invalid')
    return float(value)


def load_daily_risk(mode,path=None):
    if mode not in {'internal_paper','kis_demo','live','disabled'}:
        raise ValueError('daily_risk_execution_mode_invalid')
    if mode != 'internal_paper':
        return {'maximum_trade_risk':FROZEN_TRADE_RISK,'scope':'frozen_broker_default','sha256':None}
    path=Path(path or CONFIG_ROOT/'daily-paper-risk.json')
    if not path.exists():
        return {'maximum_trade_risk':FROZEN_TRADE_RISK,'scope':'internal_paper_default','sha256':None}
    raw=path.read_bytes();policy=json.loads(raw)
    if set(policy)!={'scope','maximum_trade_risk'} or policy['scope']!='internal_paper_only':
        raise ValueError('internal_paper_risk_scope_required')
    return {'maximum_trade_risk':validate_fraction(policy['maximum_trade_risk']),
            'scope':'internal_paper_only','sha256':hashlib.sha256(raw).hexdigest()}
