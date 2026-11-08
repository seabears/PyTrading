"""--test engine-backtest: 저장된 KIS 분봉으로 현재 운용 엔진을 검증한다.

인증 파일·네트워크·기존 모의 계좌에 접근하지 않는다. 설정을 바꾸거나 최적화하지
않고, 기본 비용·비용 제거·비용 두 배·넓은 호가의 네 조건을 미리 고정한다.
"""
import copy
import hashlib
import json
import os
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
import sys

from paths import CODE_ROOT, CONFIG_ROOT, DATA_ROOT, RESULTS_ROOT
from research.engine_backtest import prepare_record, replay
from strategy.engine import load_config


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def load_inputs(strategy_override=None):
    """현재 실행 설정의 경로를 해석하지만 인증값·계좌 상태는 읽지 않는다."""
    runtime = json.loads((CONFIG_ROOT / "settings.json").read_text(encoding="utf-8"))
    def configured_path(name):
        path = CODE_ROOT / runtime[name]
        return path.resolve()
    strategy = json.loads(configured_path("strategy_config").read_text(encoding="utf-8"))
    paper = json.loads(configured_path("paper_settings").read_text(encoding="utf-8"))
    # 연구는 호출자의 별도 설정을 사용하며 운용 파일은 변경하지 않는다.
    if strategy_override is not None:
        strategy = copy.deepcopy(strategy_override)
    symbols = [tuple(value.split(":", 1)) for value in runtime["symbols"]]
    if not symbols or any(market != "US" for market, symbol in symbols):
        raise ValueError("현재 연구는 미국 종목 공동 계좌만 지원합니다.")
    prepared, hashes, coverage = {}, {}, {}
    for market, symbol in symbols:
        key = market + ":" + symbol
        path = DATA_ROOT / "history/minute" / f"{market}-{symbol}.json"
        raw = path.read_bytes()
        record = json.loads(raw)
        if (record.get("origin") != "kis_actual_historical_candles" or record.get("market") != market
                or record.get("symbol") != symbol or record.get("interval") != "1m"
                or record.get("collection_complete") is not True):
            raise ValueError(f"{key}: 출처·종목·분봉·수집 완료 여부를 확인하세요.")
        prepared[key] = prepare_record(record)
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
    # 모든 종목이 자료를 가진 시작·종료 날짜의 교집합. 중간 누락은 보간하지 않는다.
    start = max(sessions[0]["day"] for sessions in prepared.values())
    end = min(sessions[-1]["day"] for sessions in prepared.values())
    if start > end:
        raise ValueError("30종목의 공통 평가 기간이 없습니다.")
    all_days = sorted({session["day"] for sessions in prepared.values() for session in sessions
                       if start <= session["day"] <= end})
    for key, sessions in prepared.items():
        selected = [session for session in sessions if start <= session["day"] <= end]
        present = {session["day"] for session in selected}
        coverage[key] = {"sessions": len(selected), "minutes": sum(len(s["minutes"]) for s in selected),
                         "missing_days": [day for day in all_days if day not in present],
                         "missing_minutes": sum(s["expected_minutes"] - len(s["minutes"]) for s in selected),
                         "partial_sessions": [s["day"] for s in selected if len(s["minutes"]) != s["expected_minutes"]]}
    return symbols, strategy, paper, prepared, hashes, coverage, start, end


def stock_attribution(result, symbols):
    """종목별 실제 현금 흐름과 남은 보유의 가상 청산액을 맞춘다."""
    state = result["state"]
    rows = []
    for market, symbol in symbols:
        key = market + ":" + symbol
        trades = [t for t in state["trades"] if t["market"] == market and t["symbol"] == symbol]
        closed = [t for t in result["closed_trades"] if t["symbol"] == key]
        position = state["positions"].get(key)
        settings = state["settings"]
        liquidation = 0
        if position:
            liquidation = (position["quantity"] * state["last_prices"][key]
                           * (1 - settings["slippage_ratio"]) * (1 - settings["sell_cost_ratio"]))
        rows.append({"symbol": key, "closed_trades": len(closed), "open": bool(position),
                     "net_pnl": sum(t["cash_flow"] for t in trades) + liquidation,
                     "realized_pnl": sum(t["net_pnl"] for t in closed),
                     "gross_mid_pnl": sum(t["gross_mid_pnl"] for t in closed),
                     "closed_costs": sum(t["fees"] + t["spread_cost"] + t["slippage_cost"] for t in closed)})
    return rows


def plot_report(folder, results, attribution):
    os.environ["MPLCONFIGDIR"] = str(DATA_ROOT / "cache/plots")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as dates
    figure, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for name, result in results.items():
        # 장중 계좌 곡선을 10분 간격으로 표시한다. MDD 계산은 모든 분을 사용한다.
        points = result["curve"][::10] + [result["curve"][-1]]
        initial = result["state"]["settings"]["starting_cash"]["US"]
        times = [datetime.fromisoformat(p["at"]) for p in points]
        axes[0].plot(times, [(p["net_liquidation_equity"] / initial - 1) * 100 for p in points], label=name)
        if name == "base":
            peak, drawdowns = initial, []
            for point in result["curve"]:
                peak = max(peak, point["net_liquidation_equity"])
                drawdowns.append((point["net_liquidation_equity"] / peak - 1) * 100)
            axes[1].plot([datetime.fromisoformat(p["at"]) for p in result["curve"]], drawdowns, label="base drawdown")
    axes[0].set_ylabel("Net liquidation return (%)")
    axes[0].set_title("Current live engine / synthetic quotes / shared USD account")
    axes[1].set_ylabel("Drawdown (%)")
    for axis in axes:
        axis.axhline(0, color="gray", linewidth=.5)
        axis.grid(alpha=.2)
        axis.legend()
    locator = dates.AutoDateLocator(minticks=4, maxticks=7)
    axes[1].xaxis.set_major_locator(locator)
    axes[1].xaxis.set_major_formatter(dates.ConciseDateFormatter(locator))
    figure.tight_layout()
    figure.savefig(folder / "performance.png", dpi=150)
    plt.close(figure)
    ordered = sorted(attribution, key=lambda row: row["net_pnl"])
    figure, axis = plt.subplots(figsize=(11, 9))
    axis.barh([r["symbol"] for r in ordered], [r["net_pnl"] for r in ordered],
              color=["#c75555" if r["net_pnl"] < 0 else "#36836c" for r in ordered])
    axis.set_xlabel("PnL contribution (USD), including open positions at hypothetical liquidation")
    axis.set_title("30 stocks, shared capital / base scenario")
    axis.axvline(0, color="gray", linewidth=.7)
    figure.tight_layout()
    figure.savefig(folder / "stocks.png", dpi=150)
    plt.close(figure)


def write_validation(folder, declaration, results, attribution):
    """검증이 실패하면 성공 보고서로 넘어가지 않고 해당 항목을 명시한다."""
    checks = {}
    for name, result in results.items():
        state, summary = result["state"], result["summary"]
        initial = state["settings"]["starting_cash"]["US"]
        checks[name + ": cash_flow_reconciles"] = abs(
            initial + sum(t["cash_flow"] for t in state["trades"]) - state["cash"]["US"]) < 1e-7
        checks[name + ": position_limit"] = summary["maximum_positions"] <= state["settings"]["max_positions_per_market"]
        checks[name + ": no_invalid_input"] = not any(r.startswith("invalid_input") for r in result["reasons"])
        checks[name + ": trade_costs_reconcile"] = all(abs(
            t["gross_mid_pnl"] - t["spread_cost"] - t["slippage_cost"] - t["fees"] - t["net_pnl"]
        ) < 1e-7 for t in result["closed_trades"])
    base = results["base"]["summary"]
    checks["base: all_stocks_accounted_for"] = len(attribution) == len(declaration["symbols"])
    checks["base: stock_contributions_reconcile"] = abs(sum(r["net_pnl"] for r in attribution)
        - (base["final_equity"] - declaration["paper"]["starting_cash"]["US"])) < 1e-7
    write_json(folder / "validation.json", checks)
    lines = ["# 재생 결과 정합성", "", "아래 항목은 이번 결과에서 직접 계산했다.", ""]
    lines += [f"- {'PASS' if passed else 'FAIL'}: {name}" for name, passed in checks.items()]
    lines += ["", "## 별도 자동 검증", "", "`python Code/main.py --test unit-engine-backtest`:",
              "운용 계좌와 매 시점 판단·최종 상태 일치, 미래 정보 차단, 공동 자금, 비용, 누락 분, 달력 등을 확인한다.",
              "`python Code/main.py --test all`: 기존 기능·상품 차단 포함 전체 자동 검증.",
              "이 백테스트 명령은 자동 검증 전체를 재실행하지 않는다. 통과 여부는 해당 명령 출력으로 확인한다.", ""]
    (folder / "validation.md").write_text("\n".join(lines), encoding="utf-8")
    if not all(checks.values()):
        raise ValueError("백테스트 결과 정합성 실패: validation.md를 확인하세요.")


def write_report(folder, declaration, results, attribution):
    base = results["base"]
    summary = base["summary"]
    strategy, paper = declaration["strategy"], declaration["paper"]
    lines = ["# 현재 운용 엔진 백테스트", "", "실제 KIS 분봉 + 가상 호가·체결·비용. 실거래 성과가 아니다.", "",
        f"- 기간: {declaration['start']} ~ {declaration['end']}, {summary['sessions']}거래일, {len(attribution)}종목 공동 USD 계좌.",
        "- PaperAccount.evaluate_snapshot → strategy.engine.evaluate를 그대로 호출한다. 연구 계좌는 반복 파일 저장만 생략한다.",
        f"- 설정 파일 순서로 같은 시각의 종목을 처리한다. 초기 {paper['starting_cash']['US']:,.0f} USD, 종목별 초기 자금 {paper['allocation_fraction']:.0%}, 최대 {paper['max_positions_per_market']}개 보유.",
        f"- 완성 5분봉 {strategy['lookback'] + 1}개 필요: 당일 {(strategy['lookback'] + 1) * 5}분 이전 신규 진입 불가. 직전 {strategy['lookback']}봉 고점 돌파·평균 거래량 {strategy['volume_ratio']:g}배·호가·예산 조건 모두 충족 시 매수.",
        f"- 매도: 비용 포함 원가 대비 -{strategy['stop_loss']:.0%}, 고점 대비 -{strategy['trailing_stop']:.0%}, 본전·이익 보호, 이전 {strategy['lookback']}봉 평균 종가 하향 이탈. 종가 강제 청산 없이 다음 날 보유 가능.",
        "- 손절은 보장 가격이 아니다. 다음 장 시가의 갭과 분 사이 급락으로 설정 손실을 초과할 수 있다.", "",
        "## 재생·비용 가정", "",
        "- 각 분 시작 t에, t까지 완성된 5분봉과 [t,t+1분] 시가로 만든 호가를 제공한다. 현재 분의 고가·저가·종가·거래량은 미리 사용하지 않는다.",
        "- 시가는 호가 중간값의 대용일 뿐 실제 bid/ask가 아니다. 1분마다 모든 종목을 지연 없이 판단하고 즉시 전량 체결된다고 가정한다.",
        "- 실제 수집·호가 지연, API 실패, 유동성·부분 체결, 1분 내 고저가 경로는 재현하지 못한다. 실시간과 입력·체결까지 동일하다는 의미는 아니다.",
        f"- 기본: 스프레드 0.10%, 매수 비용 {paper['buy_cost_ratio']:.2%}, 매도 비용 {paper['sell_cost_ratio']:.2%}, 매수·매도 각각 슬리피지 {paper['slippage_ratio']:.2%}. 실제 증권사 요율이 아니다.",
        "- no_cost는 수수료·슬리피지만 0, 스프레드 유지. double_cost는 해당 비용 2배. wide_spread는 기본 비용 + 스프레드 0.25%.",
        "- 비용을 바꾸면 원가·수량·보호 매도선·후속 신호도 달라진다. 조건 간 차이를 순수 비용 차이로 해석하지 않는다.",
        "- 평가액은 마지막 관측 호가 기준이다. 보유 포지션의 가상 매도 비용까지 차감한 청산 평가액으로 수익률·MDD를 계산한다. 실제 종가 청산 거래는 추가하지 않는다.",
        "- MDD는 1분 간격 평가이며 1분 내 낙폭은 미관측. 휴장·조기 종료·서머타임은 운용과 같은 거래소 달력 사용. 누락 분은 채우지 않는다.",
        "- 무수정 분봉 사용. 분할·배당 등 기업행동의 별도 조정·배당 현금·이자·환율·실제 세율 이력은 미반영. 장기 보유 성과와 직접 비교하기 어렵다.", "",
        "## 성과", "", "|조건|순수익률|최대 낙폭|완료 거래|승률|Profit Factor|미청산|", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, result in results.items():
        row = result["summary"]
        win = "—" if row["win_rate"] is None else f"{row['win_rate']:.1%}"
        factor = "— (손실 거래 없음/정의 불가)" if row["profit_factor"] is None else f"{row['profit_factor']:.2f}"
        lines.append(f"|{name}|{row['net_return']:.3%}|{row['max_drawdown']:.3%}|{row['closed_trades']}|{win}|{factor}|{row['open_positions']}|")
    lines += ["", "## 손익 원인", "",
        f"- 기본 완료 거래의 중간값 기준 가격 손익: {summary['gross_mid_pnl']:.2f} USD.",
        f"- 같은 거래의 스프레드 {summary['spread_cost']:.2f}, 슬리피지 {summary['slippage_cost']:.2f}, 매수·매도 수수료 {summary['fees']:.2f} USD.",
        f"- 완료 거래 순손익: {summary['realized_pnl']:.2f} USD. 미청산 평가 포함 전체 순손익: {summary['final_equity'] - declaration['paper']['starting_cash']['US']:.2f} USD.",
        f"- 평균 투자 노출: {summary['average_exposure']:.2%}. 최대 동시 보유: {summary['maximum_positions']}개. 대기 자금도 수익률 분모에 포함한다.",
        "- 매수 조건 실패 횟수는 서로 중복된다. 조건 하나 제거 시의 수익성을 뜻하지 않는다.", ""]
    lines += [f"- 조건 실패 {name}: {count:,}회" for name, count in sorted(base["failed_checks"].items(), key=lambda item: -item[1])]
    exits = defaultdict(lambda: {"count": 0, "pnl": 0})
    for trade in base["closed_trades"]:
        row = exits[trade["exit"]["reason"]]
        row["count"] += 1
        row["pnl"] += trade["net_pnl"]
    lines += ["", "|매도 사유|완료 거래|순손익 USD|", "|---|---:|---:|"]
    lines += [f"|{reason}|{row['count']}|{row['pnl']:.2f}|" for reason, row in exits.items()]
    lines += ["", "## 종목별 기여", "", "같은 공동 자금에서의 기여이며 종목별 독립 수익률이 아니다. 미청산 가상 청산 비용 포함.", "",
              "|종목|완료 거래|미청산|실현 손익 USD|전체 기여 USD|", "|---|---:|---:|---:|---:|"]
    lines += [f"|{r['symbol']}|{r['closed_trades']}|{int(r['open'])}|{r['realized_pnl']:.2f}|{r['net_pnl']:.2f}|" for r in attribution]
    lines += ["", "## 자료 범위·제한", "", "|종목|거래일|정규장 분봉|누락 분|없는 날짜|", "|---|---:|---:|---:|---|"]
    lines += [f"|{key}|{r['sessions']}|{r['minutes']}|{r['missing_minutes']}|{', '.join(r['missing_days']) or '없음'}|" for key, r in declaration["coverage"].items()]
    negative_gross = sum(t["gross_mid_pnl"] < 0 for t in base["closed_trades"])
    cost_reversed = sum(t["gross_mid_pnl"] > 0 and t["net_pnl"] < 0 for t in base["closed_trades"])
    lines += ["", "## 손실 진단과 다음 단계", "",
        f"- 완료 {summary['closed_trades']}거래 중 가격 손익이 음수인 거래 {negative_gross}건, 가격 손익이 양수지만 비용 후 손실인 거래 {cost_reversed}건.",
        "- 가격 손익·비용과 매도 사유를 함께 검토한다. 비용 제거 조건도 손실이면 수수료만 낮추는 것으로 해결됐다고 볼 수 없다.",
        "- 다음 실험 후보는 거래 빈도를 줄이는 별도 일봉 추세 전략과 현금 대기다. 이 결과를 보고 고른 규칙은 새로운 미사용 구간에서 재검증해야 한다.",
        "- 장중 전략은 장기 분봉·실제 호가 기록을 추가 확보한다. 일봉을 분봉처럼 사용해 표본 수를 늘리지 않는다.",
        "- 과거 수익 종목만 골라 설정을 바꾸지 않았다. 이번 작업에서 운용 전략·모의 계좌·실제 주문 설정은 변경하지 않았다.",
        "", "## 판정", "", "- 통과: 운용 판단·계좌 코드 공유, 공동 자금·비용 반영, 원본 해시와 소스·설정 보존. 자동 검증 내역은 validation.md 참고.",
        "- 미검증: 실제 과거 호가·체결, 장기간·별도 미사용 기간, 하락장·급락장·다양한 시장 국면의 안정성.",
        "- 이 자료는 약 한 달의 탐색 평가다. 이전에도 검토한 기간이므로 독립적인 미사용 평가 자료로 보지 않는다.",
        "- 수익이 양수여도 실전 전환 판정은 보류한다. 결과에 맞춰 임계값을 바꾸지 않았다. 장기 분봉 확보와 이후 기간의 모의 운용을 먼저 진행한다.",
        "", "![계좌 성과](performance.png)", "", "![종목 기여](stocks.png)", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    symbols, strategy, paper, prepared, hashes, coverage, start, end = load_inputs()
    folder = RESULTS_ROOT / "engine-backtest" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True)
    base_costs = copy.deepcopy(paper)
    no_costs, double_costs = copy.deepcopy(paper), copy.deepcopy(paper)
    for name in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
        no_costs[name] = 0
        double_costs[name] *= 2
    scenarios = {"base": (base_costs, .001), "no_cost": (no_costs, .001),
                 "double_cost": (double_costs, .001), "wide_spread": (base_costs, .0025)}
    declaration = {"start": start, "end": end, "symbols": symbols, "strategy": load_config(strategy),
                   "paper": paper, "scenarios": scenarios, "source_hashes": hashes, "coverage": coverage,
                   "optimization": False, "actual_quotes": False, "live_config_modified": False}
    declaration["environment"] = {"python": sys.version, "exchange_calendars": version("exchange_calendars"),
                                   "tzdata": version("tzdata")}
    source_folder = folder / "source"
    source_folder.mkdir()
    for name in ("research/engine_backtest.py", "tools/research_engine_backtest.py", "strategy/engine.py",
                 "strategy/exits.py", "trading/paper.py", "broker/toss.py", "broker/sessions.py"):
        raw = (CODE_ROOT / name).read_bytes()
        declaration.setdefault("code_hashes", {})[name] = hashlib.sha256(raw).hexdigest()
        (source_folder / name.replace("/", "-")).write_bytes(raw)
    write_json(folder / "declaration.json", declaration)
    results = {}
    for name, (costs, spread) in scenarios.items():
        print(f"[{name}] {start} ~ {end}, {len(symbols)}종목 공동 계좌 재생", flush=True)
        results[name] = replay(prepared, symbols, strategy, costs, spread, start, end,
                               progress=lambda day: print(f"  {day}", flush=True))
        write_json(folder / f"{name}.json", results[name])
        row = results[name]["summary"]
        print(f"[{name}] 수익 {row['net_return']:.3%}, MDD {row['max_drawdown']:.3%}, 완료 {row['closed_trades']}거래", flush=True)
    attribution = stock_attribution(results["base"], symbols)
    write_json(folder / "attribution.json", attribution)
    write_validation(folder, declaration, results, attribution)
    write_report(folder, declaration, results, attribution)
    plot_report(folder, results, attribution)
    write_json(folder.parent / "latest.json", {"folder": str(folder)})
    # 사용자에게 안내한 고정 보고서 경로도 다음 실행의 결과로 갱신한다.
    destination = DATA_ROOT / "reports/engine-backtest"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("report.md", "performance.png", "stocks.png", "validation.md", "validation.json",
                 "declaration.json", "attribution.json"):
        shutil.copy2(folder / name, destination / name)
    # 이전 실행의 테스트 로그가 최신 결과의 검증으로 보이지 않게 별도 실행 기록으로 둔다.
    if (destination / "test-log.txt").exists():
        (destination / "test-log.txt").replace(destination / "previous-test-log.txt")
    write_json(destination / "latest.json", {"folder": str(folder)})
    print(f"보고서: {folder / 'report.md'}", flush=True)
