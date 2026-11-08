"""고정 일봉 후보 검증용 새 KIS 스냅샷. 기존 시세·계좌는 덮어쓰지 않는다."""
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.runtime import load_run_settings, acquire_run_lock
from broker.kis_setup import create_kis_client, load_kis_settings
from paths import CONFIG_ROOT, DATA_ROOT
from research.kis_history import collect_us_history
from tools.run_algorithm_study import write_json


def main():
    plan = json.loads((CONFIG_ROOT / "fixed-trend-study.json").read_text(encoding="utf-8"))
    runtime = load_run_settings()
    options = load_kis_settings(runtime["broker_config"])
    root = DATA_ROOT / "fixed-trend/datasets"
    root.mkdir(parents=True, exist_ok=True)
    folder = root / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir()
    write_json(folder / "plan-before-collection.json", plan)
    client = create_kis_client(runtime["env_file"], options)
    client.request_interval = .15
    rows, errors = [], []
    with acquire_run_lock(DATA_ROOT / "cache/fixed-trend-collection.lock"):
        for market, symbol in [*runtime["symbols"], ("US", "SPY")]:
            if market != "US":
                raise ValueError("이번 연구는 미국 종목만 지원합니다.")
            exchange = options["us_exchanges"].get(symbol, "AMS" if symbol == "SPY" else None)
            try:
                record, raw = collect_us_history(client, symbol, exchange, "1d", date(2018, 1, 1),
                    date.fromisoformat(plan["collection_end"]), maximum_pages=40)
                if not record["collection_complete"] or not record["candles"]:
                    raise ValueError("완료된 유효 일봉이 없습니다.")
                for directory in ("daily", "raw"):
                    (folder / directory).mkdir(exist_ok=True)
                path = folder / "daily" / ("US-" + symbol + ".json")
                write_json(path, record)
                write_json(folder / "raw" / ("US-" + symbol + ".json"), raw)
                rows.append({"symbol": symbol, "bars": len(record["candles"]),
                    "last": record["candles"][-1]["timestamp"][:10],
                    "retrieved_at": record["retrieved_at"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                print(symbol, rows[-1]["bars"], rows[-1]["last"], flush=True)
            except Exception as error:
                # 원본 API 오류는 키를 포함하지 않는 클라이언트 형식만 사용한다.
                errors.append({"symbol": symbol, "type": type(error).__name__, "message": str(error)})
                print(symbol, type(error).__name__, str(error), flush=True)
            write_json(folder / "manifest.json", {"rows": rows, "errors": errors, "complete": not errors and len(rows) == 31})
    if errors or len(rows) != 31:
        raise ValueError("일부 수집 실패. 기존 시세는 보존했고 불완전 스냅샷은 채택하지 않았습니다.")
    write_json(root / "latest.json", {"folder": str(folder)})
    print("새 일봉 스냅샷:", folder, flush=True)
