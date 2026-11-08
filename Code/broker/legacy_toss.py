"""이전 토스 원자료의 연구 재현 전용. KIS 인증을 토스로 보내지 않는다."""
from broker.toss import TossMarketClient, parse_symbol
from broker.toss import read_credentials as _read_credentials


def read_credentials(prompt_if_missing, env_file=None):
    from app.runtime import load_run_settings
    if load_run_settings().get("broker", "toss") != "toss":
        raise ValueError("이 연구의 신규 과거자료 수집기는 토스 전용입니다. KIS 모드에서는 저장된 토스 자료만 재현합니다. KIS 장기 과거자료 수집은 별도 변환이 필요합니다.")
    return _read_credentials(prompt_if_missing, env_file)
