"""가격 연구 전용 실시간 모의 운용. 실제 주문 없이 별도 가상 계좌와 일별 기록을 만든다."""
import json
from zoneinfo import ZoneInfo

from paths import CONFIG_ROOT, DATA_ROOT
from strategy.engine import parse_timestamp
from trading.safety import equity


def write_daily_report(account, snapshot, folder):
    """실제 관측 시각 기준으로 기록한다. 미관측 기간을 수익 곡선으로 채우지 않는다."""
    if getattr(account,'execution_mode','internal_paper')!='internal_paper':
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'broker-research-status.json').write_text(json.dumps(account.summary(),ensure_ascii=False,indent=2),encoding='utf-8')
        return
    market = snapshot["market"]
    zone = ZoneInfo("America/New_York" if market == "US" else "Asia/Seoul")
    day = parse_timestamp(snapshot["now"]).astimezone(zone).date().isoformat()
    destination = folder / "daily"
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / (market + "-" + day + ".json")
    row = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "day": day, "market": market, "observations": 0, "reasons": {},
        "first_observed_at": snapshot["now"], "mode": "local_paper_only"}
    value = equity(account.state, market, account.settings)
    baseline = account.state.get("safety_days", {}).get(market, {}).get("baseline_equity", value)
    row.setdefault("baseline_equity", baseline)
    row["observations"] += 1
    row["last_observed_at"] = snapshot["now"]
    row["net_liquidation_equity"] = value
    row["peak_equity"] = max(row.get("peak_equity", row["baseline_equity"]), value)
    row["maximum_drawdown"] = max(row.get("maximum_drawdown", 0), 1 - value / row["peak_equity"]) if row["peak_equity"] else 0
    row["daily_return"] = value / row["baseline_equity"] - 1 if row["baseline_equity"] else None
    # 당일 거래를 저장된 상태에서 다시 집계해 재시작 시 중복 합산하지 않는다.
    trades = [trade for trade in account.state["trades"] if trade["market"] == market
        and parse_timestamp(trade["at"]).astimezone(zone).date().isoformat() == day]
    row["fees"] = sum(trade["fees"] for trade in trades)
    row["cost_basis_exposure"] = sum(position["cost_basis"] for position in account.state["positions"].values() if position["market"] == market) / account.settings["starting_cash"][market]
    row["buys"] = sum(trade["action"] == "BUY" for trade in trades)
    row["sells"] = sum(trade["action"] == "SELL" for trade in trades)
    row["realized_pnl"] = sum(trade.get("realized_pnl", 0) for trade in trades)
    row["quote_times"] = dict(account.state.get("quote_times", {}))
    # 판단 사유는 호출자에게 받아 큰 거래 일지를 매번 다시 읽지 않는다.
    reason = snapshot.get("research_decision_reason", "unknown")
    row["reasons"][reason] = row["reasons"].get(reason, 0) + 1
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    lines = [f"# {day} {market} 실시간 로컬 모의 관측", "",
        "실제 주문 없음. 마지막 유효 호가에 가상 청산 비용을 적용한 평가이며 종가 확정 보고서가 아니다.",
        "당일 첫 유효 관측 직전 평가가 기준이다. 관측 사이 손실과 시세 지연은 완전히 재현하지 못한다.", "",
        f"- 관측 수: {row['observations']}, 마지막: {row['last_observed_at']}",
        f"- 순청산 평가: {value:,.2f}, 기준: {row['baseline_equity']:,.2f}",
        f"- 당일 기록 비용: {row['fees']:.2f}, 초기 자금 대비 보유 원가 비중: {row['cost_basis_exposure']:.2%}",
        f"- 관측 최대 낙폭: {row['maximum_drawdown']:.2%}",
        f"- 모의 매수 {row['buys']}건 / 매도 {row['sells']}건 / 실현 손익 {row['realized_pnl']:.2f}",
        "", "|판단 사유|관측 횟수|", "|---|---:|"]
    lines += [f"|{name}|{count}|" for name, count in sorted(row["reasons"].items(), key=lambda item: -item[1])]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(watch=True):
    """인자를 늘리지 않고 별도 Python 진입점에서 호출한다."""
    from app.runner import main as run
    strategy_path = CONFIG_ROOT / "strategy-price-research.json"
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    if strategy.get("earnings_enabled") is not False or strategy.get("news_enabled") is not False:
        raise ValueError("가격 연구에서 뉴스·실적 조건은 꺼야 합니다.")
    print("가격 연구: 기존 전략을 실행하며 체결 방식은 Config/execution.json을 따릅니다.", flush=True)
    run([], settings_override={"strategy_config": strategy_path,
        "output_dir": DATA_ROOT / "paper-price-research", "collect_news": False, "watch": watch},
        decision_observer=write_daily_report)
