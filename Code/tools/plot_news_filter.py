"""저장된 실제 뉴스 선별 건수 그래프. 선택적 matplotlib 도구이며 매매 실행에는 필요 없다."""
import json
import os

from paths import DATA_ROOT, RESULTS_ROOT


def main():
    folder = RESULTS_ROOT
    reports = json.loads((folder / "live-news-report.json").read_text(encoding="utf-8"))
    os.environ.setdefault("MPLCONFIGDIR", str(DATA_ROOT / "cache/plots"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plot

    figure, axes = plot.subplots(1, len(reports), figsize=(9, 4), squeeze=False, constrained_layout=True)
    for axis, report in zip(axes[0], reports):
        counts = [report["fetched_count"], len(report["selected"]), len(report["excluded"])]
        bars = axis.bar(["Fetched", "Selected", "Excluded"], counts, color=["#78909c", "#00897b", "#e57373"])
        axis.bar_label(bars, padding=3)
        axis.set_ylim(0, max(counts + [1]) * 1.2)
        axis.set_ylabel("Articles")
        axis.set_title(report["market"] + ":" + report["symbol"])
        axis.grid(axis="y", alpha=0.2)
    figure.suptitle("Live RSS filtering counts: not prediction accuracy")
    output = folder / "news-filter.png"
    figure.savefig(output, dpi=160)
    plot.close(figure)
    print(output)


if __name__ == "__main__":
    main()
