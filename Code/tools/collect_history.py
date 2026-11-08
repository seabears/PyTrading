"""연구용 과거 시세를 수집한다. 공개 실행은 main.py --test backtest로 연결한다."""
import json

from app.runtime import acquire_run_lock, load_run_settings, release_run_lock
from broker.legacy_toss import TossMarketClient, read_credentials
from paths import PROJECT_ROOT, DATA_ROOT, CONFIG_ROOT
from research.history import collect_history, load_research_settings


def main():
    runtime = load_run_settings()
    settings = load_research_settings(CONFIG_ROOT / "research.json")
    pending = []
    for market, symbol in runtime["symbols"]:
        path = DATA_ROOT / "history" / (market + "-" + symbol + ".json")
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            complete = saved.get("collection_complete") and (saved.get("stop_reason") != "page_limit" or saved["pages"] >= settings["max_pages_per_symbol"])
            if complete:
                print(f"{market}:{symbol}: 저장된 과거 시세를 사용합니다. {path}")
                continue
        pending.append((market, symbol, path))
    if not pending:
        return  # 캐시 재검증은 인증 파일도 읽지 않는다.
    runtime["output_dir"].mkdir(parents=True, exist_ok=True)
    lock = acquire_run_lock(runtime["output_dir"] / "run.lock")
    try:
        credentials = read_credentials(False, runtime["env_file"])
        client = TossMarketClient(*credentials)
        for market, symbol, path in pending:
            collect_history(client, market, symbol, path, settings)
    finally:
        release_run_lock(lock)


if __name__ == "__main__":
    main()
