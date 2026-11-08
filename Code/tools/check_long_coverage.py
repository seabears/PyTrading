"""수집한 장기 일봉의 시작·종료·봉 수를 확인한다. 인증 파일은 읽지 않는다."""
import json
from pathlib import Path
from paths import DATA_ROOT, RESULTS_ROOT
from research.daily import prepare_daily_bars


if __name__ == "__main__":
    for path in sorted((DATA_ROOT / "history/long-adjusted").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        bars = prepare_daily_bars(record)
        print(record["market"], record["symbol"], len(bars), bars[0]["date"], bars[-1]["date"], record["stop_reason"])
    # 계산 결과를 바꾸지 않고 최신 장기 보고서·그림의 표시만 다시 생성한다.
    pointer = RESULTS_ROOT / "long-history/latest.json"
    if pointer.exists():
        from tools.research_long_history import write_report
        from tools.research_portfolio import plot_report
        folder = Path(json.loads(pointer.read_text(encoding="utf-8"))["folder"])
        report = json.loads((folder / "results.json").read_text(encoding="utf-8"))
        write_report(folder, report)
        for name, cohort in report["cohorts"].items():
            plot_report(folder / name, {"costs": report["costs"], "markets": cohort["markets"]})
