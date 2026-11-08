"""--test history: 현재 관찰 종목을 KIS에서 새로 받고 검증 후 시세 폴더를 교체한다."""
import hashlib
import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.runtime import acquire_run_lock, load_run_settings
from broker.kis_setup import create_kis_client, load_kis_settings
from paths import CONFIG_ROOT, DATA_ROOT
from research.kis_history import collect_us_history
from research.history import write_json


def main():
    runtime = load_run_settings()
    options = load_kis_settings(runtime["broker_config"])
    if runtime["broker"] != "kis" or any(market != "US" for market, symbol in runtime["symbols"]):
        raise ValueError("이 수집 기능은 현재 KIS 미국 종목 목록 전용입니다.")
    settings = json.loads((CONFIG_ROOT / "history-kis.json").read_text(encoding="utf-8"))
    start = date.fromisoformat(settings["start"])
    # 진행 중인 오늘 일봉은 제외한다. 주말·휴일에는 직전 제공 거래일까지 수집된다.
    end = datetime.now(ZoneInfo("America/New_York")).date() - timedelta(days=1)
    unfinished = sorted(DATA_ROOT.glob("history-new-*"))
    stamp = unfinished[-1].name.removeprefix("history-new-") if unfinished else datetime.now().strftime("%Y%m%d-%H%M%S")
    report_folder = DATA_ROOT / "reports/data-refresh" / stamp
    staging = DATA_ROOT / ("history-new-" + stamp)
    report_folder.mkdir(parents=True, exist_ok=True)
    staging.mkdir(exist_ok=True)
    client = create_kis_client(runtime["env_file"], options)
    client.request_interval = 0.1
    rows, errors = [], []
    with acquire_run_lock(DATA_ROOT / "cache/history-refresh.lock"):
        # 정상 실행 계좌의 잠금을 잡아 동시 수집·설정 경합을 막는다.
        runtime["output_dir"].mkdir(parents=True, exist_ok=True)
        with acquire_run_lock(runtime["output_dir"] / "run.lock"):
            for symbol in [item[1] for item in runtime["symbols"]] + ["SPY"]:
                exchange = options["us_exchanges"].get(symbol, "AMS" if symbol == "SPY" else None)
                for interval, directory in (("1d", "daily"), ("1m", "minute")):
                    try:
                        path = staging / directory / f"US-{symbol}.json"
                        raw_path = staging / "raw" / f"US-{symbol}-{interval}.json"
                        cached = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
                        if (cached.get("requested_start") == str(start) and cached.get("requested_end") == str(end)
                                and cached.get("origin") == "kis_actual_historical_candles"
                                and cached.get("symbol") == symbol and cached.get("interval") == interval
                                and cached.get("exchange") == exchange and cached.get("collection_complete")
                                and raw_path.exists()):
                            from research.kis_history import validate_candle
                            for candle in cached["candles"]:
                                validate_candle(candle)
                            record = cached
                        else:
                            record, raw = collect_us_history(client, symbol, exchange, interval, start, end, settings["maximum_pages"])
                            write_json(path, record)
                            write_json(raw_path, raw)
                        if not record["candles"]:
                            raise ValueError("수집된 유효 시세 없음")
                        row = {"symbol": symbol, "interval": interval, "count": len(record["candles"]),
                               "first": record["candles"][0]["timestamp"], "last": record["candles"][-1]["timestamp"],
                               "stop_reason": record["stop_reason"], "requested_period_reached": record["requested_period_reached"],
                               "rejected_count": len(record.get("rejected", [])),
                               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                        rows.append(row)
                        print(f"{symbol} {interval}: {row['count']}봉 / {row['first'][:10]} ~ {row['last'][:10]} / {row['stop_reason']}", flush=True)
                    except (ValueError, OSError, RuntimeError, KeyError) as error:
                        errors.append({"symbol": symbol, "interval": interval, "error": str(error)})
                        print(f"{symbol} {interval} 수집 실패: {error}", flush=True)
                    write_json(report_folder / "results.json", {"rows": rows, "errors": errors, "replaced": False})
            if errors or len(rows) != 62:
                write_report(report_folder, rows, errors, False)
                raise ValueError("일부 수집 실패. 기존 시세는 삭제하지 않았습니다. 보고서를 확인하세요.")
            history = (DATA_ROOT / "history").resolve()
            if history.parent != DATA_ROOT.resolve() or history.name != "history" or history.is_symlink():
                raise ValueError("시세 삭제 대상 경로 검증 실패")
            # 신규 파일 62개를 다시 읽어 출처와 해시를 검사한 뒤, 명시한 시세 폴더만 지운다.
            for row in rows:
                directory = "daily" if row["interval"] == "1d" else "minute"
                path = staging / directory / f"US-{row['symbol']}.json"
                if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                    raise ValueError("새 시세 파일 해시 불일치")
            # 연구 시험 이력은 가격 데이터가 아니므로 삭제 대상에서 제외한다.
            for path in history.glob("*registry*.json"):
                shutil.copy2(path, staging / path.name)
            for path in history.glob("*test-periods.json"):
                shutil.copy2(path, staging / path.name)
            if history.exists():
                shutil.rmtree(history)
            staging.rename(history)
            write_json(history / "manifest.json", {"source": "kis", "rows": rows, "start": str(start), "end": str(end)})
            write_json(report_folder / "results.json", {"rows": rows, "errors": errors, "replaced": True})
            write_report(report_folder, rows, errors, True)
    print(f"수집 보고서: {report_folder / 'report.md'}", flush=True)


def write_report(folder, rows, errors, replaced):
    """수익 성과가 아니라 실제 수집 범위를 표시한다. 짧은 분봉을 장기 자료로 표기하지 않는다."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    symbols = list(dict.fromkeys(row["symbol"] for row in rows))
    figure, axes = plt.subplots(1, 2, figsize=(13, 11))
    for axis, interval in zip(axes, ("1d", "1m")):
        counts = {row["symbol"]: row["count"] for row in rows if row["interval"] == interval}
        axis.barh(symbols, [counts.get(symbol, 0) for symbol in symbols])
        axis.set_title("KIS actual candles: " + interval)
        axis.set_xlabel("Validated candle count")
    figure.tight_layout()
    figure.savefig(folder / "coverage.png", dpi=130)
    plt.close(figure)
    lines = ["# KIS 시세 새 수집", "", f"기존 시세 교체: {replaced}. 실제 KIS 시세이며 모의 수익률 시험은 수행하지 않았다.",
             "", "- 30개 관찰 종목 + 시장 비교용 SPY. 알파벳은 GOOGL 한 종류만 사용.",
             "- 2018-01-01부터 전일까지 요청. 일봉 수정주가 MODP=1, 분봉 원본. 상장 전·API 제공 밖 자료는 생성하지 않음.",
             "- 유한한 양수 가격·OHLC 범위·거래량·중복 충돌·파일 해시 검사. 오류 봉은 rejected와 raw에 격리. 전체 거래일 누락 여부는 미검증.",
             "- api_empty_page는 API 제공 종료, api_no_progress는 응답 반복, page_limit는 설정 상한. 짧은 이력이 상장일을 입증하지 않음.",
             "- 자격 증명·토큰·모의 계좌·기존 연구 보고서·시험 이력은 보존. 기존 연구 결과는 이전 데이터 결과임.",
             "", "| 종목 | 봉 | 개수 | 처음 | 마지막 | 오류 제외 | 중단 이유 |", "|---|---|---:|---|---|---:|---|"]
    lines += [f"| {row['symbol']} | {row['interval']} | {row['count']} | {row['first'][:10]} | {row['last'][:10]} | {row.get('rejected_count', 0)} | {row['stop_reason']} |" for row in rows]
    lines += ["", "## 실패", "", json.dumps(errors, ensure_ascii=False), "", "![수집 봉 수](coverage.png)"]
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
