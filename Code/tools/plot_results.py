"""모의 판단 일지의 시장별 수익률 그래프. matplotlib가 있을 때 선택적으로 실행한다.

모의 실행 자체는 표준 라이브러리만 사용한다. 그래프 생성은 별도 도구로 분리한다.
반복 재생된 입력은 제외하고, 당시 기록된 평가액을 사용한다.
"""
import argparse
import json
import os
from pathlib import Path

from strategy.engine import parse_timestamp
from paths import DATA_ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="decisions.jsonl이 있는 모의 결과 폴더")
    args = parser.parse_args()
    os.environ.setdefault("MPLCONFIGDIR", str(DATA_ROOT / "cache/plots"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as dates
    import matplotlib.pyplot as plot

    records = [json.loads(line) for line in (args.folder / "decisions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    records = [row for row in records if row["decision"]["reason"] != "already_processed_snapshot"]
    synthetic = all("synthetic" in row["snapshot"].get("data_origin", "") for row in records)
    figure, axes = plot.subplots(2, 1, figsize=(9, 6), sharex=True, constrained_layout=True)
    for axis, market, currency in zip(axes, ("KR", "US"), ("KRW", "USD")):
        rows = [row for row in records if row["snapshot"]["market"] == market and "account_summary" in row]
        times = [parse_timestamp(row["snapshot"]["now"]) for row in rows]
        returns = [row["account_summary"][market]["return_at_last_quote"] * 100 for row in rows]
        axis.plot(times, returns, marker="o", label=f"{market} paper account ({currency})")
        axis.axhline(0, color="gray", linewidth=0.7)
        axis.set_ylabel("Return (%)")
        axis.grid(alpha=0.25)
        axis.legend(loc="lower left")
        for row, when, value in zip(rows, times, returns):
            action = row["decision"]["action"]
            if action in {"BUY", "SELL"}:
                axis.annotate(action, (when, value), xytext=(5, 8), textcoords="offset points", fontsize=9)
    axes[-1].xaxis.set_major_locator(dates.AutoDateLocator(minticks=3, maxticks=5, interval_multiples=True))
    axes[-1].xaxis.set_major_formatter(dates.DateFormatter("%H:%M:%S UTC"))
    title = "Synthetic replay: mechanics test, not performance evidence" if synthetic else "Paper account: valuation at last collected quote"
    figure.suptitle(title)
    figure.savefig(args.folder / "returns.png", dpi=160)
    plot.close(figure)
    print(str(args.folder / "returns.png"))


if __name__ == "__main__":
    main()
