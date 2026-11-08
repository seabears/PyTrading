"""--test industry-history: 동종 기업의 KIS 일봉을 새 스냅샷으로 누적한다.

기존 Data/history를 삭제·교체하지 않는다. 공개 종목 마스터로 주식 종류를 확인한
종목만 조회하며, 인증값·토큰·주문·계좌 정보는 수집 결과에 넣지 않는다.
"""
import hashlib
import io
import json
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.runtime import acquire_run_lock, load_run_settings
from broker.kis_setup import create_kis_client, load_kis_settings
from paths import CONFIG_ROOT, DATA_ROOT
from research.kis_history import collect_us_history
from tools.run_algorithm_study import record_event, write_json


def read_master(raw, exchange, symbols):
    """정해진 마스터 이름만 메모리에서 읽는다. zip 파일을 임의 경로로 풀지 않는다."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        name = next(name for name in archive.namelist() if Path(name).name.casefold() == exchange.lower() + "mst.cod")
        contents = archive.read(name).decode("cp949")
    found = {}
    for line in contents.splitlines():
        fields = line.split("\t")
        if len(fields) >= 10 and fields[4] in symbols:
            if fields[4] in found:
                raise ValueError("종목 마스터 중복: " + fields[4])
            found[fields[4]] = {"exchange": exchange.upper(), "name": fields[7],
                                 "security_type": fields[8], "currency": fields[9]}
    return found


def register_verified_stocks(policy_path, master, sources, backup):
    """공식 마스터의 USD 주식(type=2)만 확인 목록에 추가한다. 허용 상품 범위는 그대로다."""
    original = policy_path.read_bytes()
    rules = json.loads(original)
    if set(rules["allowed_asset_types"]) != {"stock", "bond", "etf"}:
        raise ValueError("허용 상품 정책이 주식·채권·ETF와 다릅니다.")
    for symbol, row in master.items():
        if row["currency"] != "USD":
            raise ValueError("USD 상품 확인 실패: " + symbol)
        if symbol == "SPY":
            if row["security_type"] != "3" or rules["verified_instruments"].get("SPY", {}).get("asset_type") != "etf":
                raise ValueError("SPY 비교 ETF 확인 실패")
            continue
        if row["security_type"] != "2":
            raise ValueError("일반 주식 확인 실패: " + symbol)
        existing = rules["verified_instruments"].get(symbol)
        if existing and existing["asset_type"] != "stock":
            raise ValueError("기존 상품 종류와 충돌: " + symbol)
        if not existing:
            if symbol not in sources:
                raise ValueError("신규 기업의 확인 출처 누락: " + symbol)
            rules["verified_instruments"][symbol] = {"asset_type": "stock", "name": row["name"],
                "evidence": "KIS official USD stock master security_type=2; " + sources[symbol]}
    backup.write_bytes(original)
    temporary = policy_path.with_suffix(".tmp")
    write_json(temporary, rules)
    temporary.replace(policy_path)


def main():
    plan = json.loads((CONFIG_ROOT / "industry-peers.json").read_text(encoding="utf-8"))
    all_symbols = [symbol for group in plan["groups"].values() for symbol in group["symbols"]]
    if len(set(all_symbols)) != len(all_symbols) or "SPY" in all_symbols:
        raise ValueError("산업군 종목은 서로 중복 없이 정의해야 합니다.")
    symbols = [*all_symbols, "SPY"]
    start = date.fromisoformat(plan["start"])
    end = datetime.now(ZoneInfo("America/New_York")).date() - timedelta(days=1)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder = DATA_ROOT / "industry-peers/datasets" / run_id
    for name in ("daily", "raw", "master"):
        (folder / name).mkdir(parents=True, exist_ok=True)
    registry_folder = DATA_ROOT / "research/experiments"
    registry_folder.mkdir(parents=True, exist_ok=True)
    registry = registry_folder / "registry.jsonl"
    manifest = {"run_id": run_id, "source": "kis", "start": str(start), "requested_end": str(end),
                "plan": plan, "master": {}, "rows": [], "errors": [], "complete": False}
    manifest["reference_watchlist"] = json.loads((CONFIG_ROOT / "settings.json").read_text(encoding="utf-8"))["symbols"]
    record_event(registry, {"run_id": run_id, "study": "industry_data", "status": "declared", "folder": str(folder), "symbols": symbols})
    try:
        with acquire_run_lock(DATA_ROOT / "cache/history-refresh.lock"):
            for exchange in ("nas", "nys", "ams"):
                url = f"https://new.real.download.dws.co.kr/common/master/{exchange}mst.cod.zip"
                with urllib.request.urlopen(url, timeout=30) as response:
                    raw = response.read()
                (folder / "master" / (exchange + ".zip")).write_bytes(raw)
                found = read_master(raw, exchange, set(symbols))
                if set(found) & set(manifest["master"]):
                    raise ValueError("복수 거래소 종목 충돌")
                manifest["master"].update(found)
            if set(manifest["master"]) != set(symbols):
                raise ValueError("공식 마스터에 없는 종목: " + str(sorted(set(symbols) - set(manifest["master"]))))
            register_verified_stocks(CONFIG_ROOT / "product-policy.json", manifest["master"],
                                     plan["new_symbol_sources"], folder / "product-policy-before.json")
            runtime = load_run_settings()
            options = load_kis_settings(runtime["broker_config"])
            client = create_kis_client(runtime["env_file"], options)
            client.request_interval = .15
            client.authenticate()
            for symbol in symbols:
                try:
                    record, raw = collect_us_history(client, symbol, manifest["master"][symbol]["exchange"],
                                                     "1d", start, end, plan["maximum_pages"])
                    path = folder / "daily" / f"US-{symbol}.json"
                    write_json(path, record)
                    write_json(folder / "raw" / f"US-{symbol}-1d.json", raw)
                    if not record["collection_complete"] or not record["candles"]:
                        raise ValueError("수집 미완료 또는 유효 일봉 없음")
                    row = {"symbol": symbol, "count": len(record["candles"]),
                           "first": record["candles"][0]["timestamp"][:10], "last": record["candles"][-1]["timestamp"][:10],
                           "rejected": len(record["rejected"]), "stop_reason": record["stop_reason"],
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                    manifest["rows"].append(row)
                    print(f"{symbol}: {row['count']}일봉 / {row['first']} ~ {row['last']} / 오류 격리 {row['rejected']}", flush=True)
                except (ValueError, RuntimeError, OSError, KeyError) as error:
                    manifest["errors"].append({"symbol": symbol, "error": str(error)})
                    print(f"{symbol}: 수집 실패 — {error}", flush=True)
                write_json(folder / "manifest.json", manifest)
        if manifest["errors"]:
            raise ValueError("일부 수집 실패. 이전 데이터는 보존했습니다. 새 manifest.json을 확인하세요.")
        manifest["complete"] = True
        write_json(folder / "manifest.json", manifest)
        write_json(folder.parent / "latest.json", {"folder": str(folder)})
        record_event(registry, {"run_id": run_id, "study": "industry_data", "status": "finished", "folder": str(folder),
                               "symbols": len(manifest["rows"]), "candles": sum(row["count"] for row in manifest["rows"])})
    except Exception as error:
        manifest["errors"].append({"stage": "collection", "error_type": type(error).__name__})
        write_json(folder / "manifest.json", manifest)
        record_event(registry, {"run_id": run_id, "study": "industry_data", "status": "failed", "error_type": type(error).__name__, "folder": str(folder)})
        raise
    print("동종 기업 시세 스냅샷:", folder, flush=True)
