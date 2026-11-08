"""KIS 설정과 읽기 전용 클라이언트 생성. main.py와 연결 확인이 같은 설정을 쓴다."""
import json
from pathlib import Path
from broker.kis import KisMarketClient, KisApiError
from broker.credentials import read_credentials_file
from paths import DATA_ROOT


def load_kis_settings(path):
    settings = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    names = {"environment", "us_exchanges", "maximum_minute_pages"}
    if not isinstance(settings, dict) or set(settings) != names:
        raise ValueError("Config/kis.json의 필수 설정 이름을 확인하세요.")
    if settings["environment"] not in {"prod", "vps"}:
        raise ValueError("KIS environment는 prod 또는 vps여야 합니다.")
    pages = settings["maximum_minute_pages"]
    if type(pages) is not int or not 1 <= pages <= 10:
        raise ValueError("KIS 분봉 최대 페이지는 1~10 정수여야 합니다.")
    exchanges = settings["us_exchanges"]
    if not isinstance(exchanges, dict) or not all(isinstance(symbol, str) and exchange in {"NAS", "NYS", "AMS"} for symbol, exchange in exchanges.items()):
        raise ValueError("KIS 미국 거래소는 NAS, NYS, AMS 중 하나여야 합니다.")
    # 자동 확인된 USD 주식의 거래소만 덧붙인다. 기존 사용자 설정은 덮어쓰지 않는다.
    from broker.universe_data import verified_stocks
    try:
        discovered = verified_stocks()
    except (OSError, ValueError, KeyError, TypeError):
        discovered = {}  # 손상된 자동 자료가 기존 보유 종목의 관리까지 중단시키지 않는다.
    for symbol, row in discovered.items():
        settings["us_exchanges"].setdefault(symbol, row["exchange"])
    return settings


def create_kis_client(env_file, options):
    try:
        app_key, secret = read_credentials_file(env_file)
    except ValueError as error:
        raise KisApiError(str(error)) from None
    cache = DATA_ROOT / "cache/kis" / options["environment"] / "market-token.json"
    client = KisMarketClient(app_key, secret, options["environment"], token_cache=cache)
    # 이전 정상 토큰을 재발급 없이 이관한다. 원본 파일은 삭제하지 않는다.
    legacy = DATA_ROOT / "cache/kis/token.json"
    if not cache.exists() and legacy.exists():
        import shutil
        from app.runtime import acquire_run_lock
        cache.parent.mkdir(parents=True, exist_ok=True)
        with acquire_run_lock(cache.with_suffix(".lock")):
            try:
                saved = json.loads(legacy.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                saved = {}
            if isinstance(saved, dict) and saved.get("identity") == client.identity and not cache.exists():
                shutil.copy2(legacy, cache)
    return client
