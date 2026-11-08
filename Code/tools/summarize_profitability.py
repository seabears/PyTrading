"""수정 6단계의 실제 모의 결과를 묶는다. 실패 기록·보고서 경로를 삭제하지 않는다."""
import json
from pathlib import Path

from paths import DATA_ROOT, RESULTS_ROOT
from research.history import write_json


def main():
    results_root = RESULTS_ROOT
    final_folder = Path(json.loads((results_root / "adaptive-robust/latest.json").read_text(encoding="utf-8"))["folder"])
    paths = [
        ("고정 모멘텀 24개", results_root / "portfolio/20261011-130750-819093"),
        ("반등 가설 추가 48개", results_root / "portfolio/20261011-130934-250587"),
        ("순차 규칙 선택", results_root / "adaptive/20261011-131113-168369"),
        ("비용·기준선 선택", results_root / "adaptive-robust/20261011-131239-168466"),
        ("인버스 방어 탐색", results_root / "defensive/20261011-131510-512992"),
        ("최소 5일 보유", final_folder),
    ]
    comparisons = []
    for label, folder in paths:
        report = json.loads((folder / "results.json").read_text(encoding="utf-8"))
        comparisons.append({"label": label, "folder": str(folder), "report": report})
    # 첫 실행은 기존 분봉 시험 날짜 중복을 나중에 발견했다. 정정 사유를 명시하고 원래 값을 기록한다.
    first_folder = paths[0][1]
    first = comparisons[0]["report"]
    if not first["test_reused"]:
        first["test_reused_original_value"] = False
        first["test_reused"] = True
        first["reuse_correction_reason"] = "기존 분봉 연구의 2026-09~10 시험과 겹침을 사후 확인"
        for market in first["markets"].values():
            market["checks"]["unused_period"] = False
        write_json(first_folder / "results.json", first)
        text = (first_folder / "report.md").read_text(encoding="utf-8")
        text = text.replace("시험 기간 재사용: False", "시험 기간 재사용: True")
        text += "\n정정: 기존 분봉 연구의 시험 날짜와 중복됨을 사후 확인했다. 최초 재사용 False 표시는 잘못됐으며 독립 검증이 아니다.\n"
        (first_folder / "report.md").write_text(text, encoding="utf-8")
    folder = results_root / "profitability-review"
    folder.mkdir(parents=True, exist_ok=True)
    final = comparisons[-1]["report"]
    from tools.research_portfolio import plot_report
    plot_report(final_folder, final)
    lines = ["# 여섯 차례 수정·최종 수익률", "", "실제 과거 가격을 사용한 모의매매다. 실거래 이익·검증된 미래 수익률이 아니다.",
             "기간: 2026-06-15~2026-10-09(한국 마지막 거래일 10-08). 초기 자금 KR 1천만 원, US 1만 달러, 종목별 10%·최대 3종목.",
             "미국에서 비용 스트레스를 견디는 흑자 탐색 결과를 얻었다. 국내는 여전히 실패, 미국도 표본·독립 시험 부족으로 실전 승인하지 않는다.",
             "| 수정 | 국내 최종 수익 | 미국 최종 수익 | 미국 비용 2배 재선정 | 보고서 |",
             "| --- | ---: | ---: | ---: | --- |"]
    for item in comparisons:
        markets = item["report"]["markets"]
        relative = Path(item["folder"]).relative_to(results_root).as_posix()
        lines.append(f"| {item['label']} | {markets['KR']['test']['summary']['net_return']:.2%} | {markets['US']['test']['summary']['net_return']:.2%} | {markets['US']['stress']['summary']['net_return']:.2%} | [전체 결과](../{relative}/report.md) |")
    lines.extend(["", "## 최종 후보", "", "최근 훈련 63일·검증 21일로 48개 가설을 비교해 다음 21일에 적용한다.",
                  "훈련·검증 흑자, 검증 거래 3건 이상, 검증 2배 비용 흑자, 검증 단순 보유 초과, 낙폭 5% 이하를 요구한다.",
                  "적격 후보 없으면 현금. 순위 교체는 최소 5거래일 이후, 손절·구간 말 청산은 즉시 처리한다.",
                  "동일 선택 재생·거래 일정과 수량까지 고정한 순수 비용 민감도·비용을 높여 선택까지 다시 수행한 결과를 모두 남겼다.",
                  "| 시장 | 순이익 | 수익률 | 동일 거래 비용 2배 | 단순 보유 | 최대 낙폭 | 거래 |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for market, result in final["markets"].items():
        summary = result["test"]["summary"]
        lines.append(f"| {market} | {summary['net_pnl']:.2f} | {summary['net_return']:.2%} | {result['recorded_trade_stress']['net_return']:.2%} | {result['benchmark']['summary']['net_return']:.2%} | {summary['max_drawdown']:.2%} | {summary['trades']} |")
    lines.extend(["", "## 통과·실패·미검증", "", "- 미국: 흑자·기준선 초과·2배 비용·낙폭은 수치로 확인한다. 최소 30거래 기준과 새 독립 시험은 통과하지 못했다.",
                  "- 국내: 흑자·기준선 초과·거래 표본 실패. 국내를 사후 제외해 전체 시스템이 통과했다고 주장하지 않는다.",
                  "- 자료: 수정주가 요청 뒤 큰 가격 단절은 사라졌지만 배당·분사 보정 방식, 수정 단위의 정수 수량·과거 생존 편향은 독립 검증되지 않았다.",
                  "- 뉴스 공개·수신 시각, 장중 호가·부분 체결, 역사 세금·실제 수수료·환율은 미검증이다.",
                  "- 첫 실행에서 분봉 연구와 날짜 중복을 누락했다가 정정했다. 모든 후속 결과는 재사용 탐색이다.",
                  "- 다른 규칙을 같은 기간에 반복해서 넣으면 과최적화 위험이 커진다. 이 흑자는 실전 수익성 증명이 아니다.",
                  "- 원화·달러 자금을 합산한 수익률은 제공하지 않는다. 평균 수익률도 실제 통합 계좌 성과가 아니다.",
                  "- 최소 보유 5일은 이번 실패·비용 분석 뒤 도입한 설정이다. 새 자료에서 동일 설정으로 검증해야 한다.",
                  "", "## 실행·수정 위치", "", "실행 `python main.py --test adaptive-robust`, 종목 `../Config/peers.json`, 가설·최소 보유 `research/portfolio.py`.",
                  "기간·연구 한도 `../Config/portfolio-research.json`, 선택 기준 `simulate_walk_forward()`.",
                  "연구 결과를 기존 장중 뉴스 엔진에 자동 적용하지 않았다. 실제 주문 기능은 없다.",
                  "", "![수정별 실제 자료 모의 수익률](iterations.png)", "", "![최종 후보·기준선·비용 스트레스](final-curve.png)"])
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(folder / "results.json", {"comparisons": comparisons, "final_folder": str(final_folder)})
    import shutil
    shutil.copy2(final_folder / "portfolio.png", folder / "final-curve.png")
    import os
    os.environ.setdefault("MPLCONFIGDIR", str(DATA_ROOT / "cache/plots"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plot
    figure, axes = plot.subplots(2, 1, figsize=(10, 7), constrained_layout=True)
    for axis, market in zip(axes, ("KR", "US")):
        values = [item["report"]["markets"][market]["test"]["summary"]["net_return"] * 100 for item in comparisons]
        axis.bar(range(1, 7), values, color=["#b85d50" if value < 0 else "#31815e" for value in values])
        axis.axhline(final["markets"][market]["benchmark"]["summary"]["net_return"] * 100, linestyle="--", color="#d58b20", label="Same-budget stock buy/hold")
        axis.axhline(0, color="gray", linewidth=.6)
        axis.set_ylabel("Account return (%)")
        axis.set_xlabel("Research revision (all reused exploration)")
        axis.set_title(market)
        axis.legend()
    figure.suptitle("Actual adjusted-price requests, simulated fills, costs included")
    figure.savefig(folder / "iterations.png", dpi=150)
    plot.close(figure)
    print(f"최종 수익률·수정 이력 보고서: {folder / 'report.md'}")


if __name__ == "__main__":
    main()
