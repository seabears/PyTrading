"""실시간 필드 순서는 예제보다 최신인 공식 포털 계약을 사용한다."""
import json
from functools import lru_cache
from paths import CONFIG_ROOT

@lru_cache(maxsize=1)
def load_schemas():
    return json.loads((CONFIG_ROOT / "kis-websocket-schemas.json").read_text(encoding="utf-8"))

def websocket_columns(transaction_id, fallback=()):
    contract = load_schemas().get(transaction_id)
    return tuple(contract["columns"]) if contract else tuple(fallback)
