"""--test strategies: 저장한 실제 자료로 장중·일봉 전략을 독립 비교한다. API 호출 없음."""
import copy
import hashlib
import json
import math
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from app.runtime import load_run_settings
from paths import CONFIG_ROOT, DATA_ROOT, PROJECT_ROOT, RESULTS_ROOT
from research.backtest import simulate, validate_costs
from research.daily import prepare_daily_bars
from research.history import prepare_sessions, write_json
from research.technical import buy_and_hold, performance, replay
from strategy.technical import MarketRegime


def load_settings():
    settings = json.loads((CONFIG_ROOT / "technical-study.json").read_text(encoding="utf-8"))
    required = {"start", "end", "spread_ratio", "intraday", "swing", "risk", "regime", "criteria"}
    if not isinstance(settings, dict) or set(settings) != required:
        raise ValueError("technical-study.json의 설정 이름을 확인하세요.")
    if date.fromisoformat(settings["start"]) >= date.fromisoformat(settings["end"]):
        raise ValueError("평가 시작 날짜가 종료 날짜보다 이전이어야 합니다.")
    def positive_integer(value):
        return type(value) is int and 1 <= value <= 252
    for name in ("intraday", "swing"):
        policy = settings[name]
        expected = ({"atr_period", "volume_period", "volume_ratio", "maximum_holding_bars"} if name == "intraday"
                    else {"atr_period", "fast", "slow", "momentum_period", "minimum_momentum", "maximum_holding_bars"})
        if set(policy) != expected:
            raise ValueError("장중·일봉 전략 설정 이름을 확인하세요.")
        for key in expected - {"volume_ratio", "minimum_momentum"}:
            if not positive_integer(policy[key]):
                raise ValueError("전략 기간은 1~252 정수여야 합니다.")
    if settings["swing"]["fast"] >= settings["swing"]["slow"]:
        raise ValueError("일봉 단기 평균 기간은 장기 평균보다 짧아야 합니다.")
    if set(settings["risk"]) != {"risk_per_trade", "stop_atr", "trailing_atr", "daily_loss_limit", "maximum_entry_gap", "cooldown_bars"}:
        raise ValueError("공통 위험 설정 이름을 확인하세요.")
    if type(settings["risk"]["cooldown_bars"]) is not int or not 0 <= settings["risk"]["cooldown_bars"] <= 100:
        raise ValueError("재진입 대기는 0~100 정수여야 합니다.")
    if set(settings["regime"]) != {"fast", "slow", "slope_period", "lag_calendar_days", "maximum_age_days"}:
        raise ValueError("시장 국면 설정 이름을 확인하세요.")
    if not all(positive_integer(value) for value in settings["regime"].values()):
        raise ValueError("시장 국면 기간은 양의 정수여야 합니다.")
    if settings["regime"]["fast"] >= settings["regime"]["slow"] or settings["regime"]["lag_calendar_days"] < 2:
        raise ValueError("시장 단기/장기 기간과 지연 2일 이상을 확인하세요.")
    if settings["regime"]["maximum_age_days"] < settings["regime"]["lag_calendar_days"]:
        raise ValueError("시장 자료 유효 기간은 지연 기간보다 짧을 수 없습니다.")
    if set(settings["criteria"]) != {"minimum_trades", "maximum_drawdown", "minimum_profit_factor"} or not positive_integer(settings["criteria"]["minimum_trades"]):
        raise ValueError("판정 기준 설정을 확인하세요.")
    values = [settings["spread_ratio"], settings["intraday"]["volume_ratio"], settings["swing"]["minimum_momentum"],
              *[value for name, value in settings["risk"].items() if name != "cooldown_bars"],
              settings["criteria"]["maximum_drawdown"], settings["criteria"]["minimum_profit_factor"]]
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("지표·위험 비율은 유한한 0 이상 숫자여야 합니다.")
    if not 0 < settings["risk"]["risk_per_trade"] < 1 or not 0 < settings["risk"]["daily_loss_limit"] < 1:
        raise ValueError("거래 위험·일일 손실 비율은 0 초과 1 미만이어야 합니다.")
    if settings["risk"]["stop_atr"] <= 0 or settings["risk"]["trailing_atr"] <= 0 or settings["intraday"]["volume_ratio"] <= 0:
        raise ValueError("ATR 배수와 거래량 배수는 양수여야 합니다.")
    if not 0 <= settings["spread_ratio"] < 1 or not 0 < settings["criteria"]["maximum_drawdown"] < 1 or not 0 <= settings["risk"]["maximum_entry_gap"] < 1:
        raise ValueError("스프레드·최대 낙폭·진입 갭 비율을 확인하세요.")
    return settings


def load_record(path, market, symbol, hashes, interval="1d"):
    raw = path.read_bytes()
    record = json.loads(raw)
    if (record.get("origin") not in {"toss_actual_historical_candles", "kis_actual_historical_candles"} or record.get("market") != market
            or record.get("symbol") != symbol or not record.get("collection_complete")
            or record.get("interval", "1m") != interval):
        raise ValueError("저장 자료의 실제 출처·종목·수집 완료·봉 단위를 확인하세요.")
    if interval == "1d" and record.get("adjusted") is not True:
        raise ValueError("일봉 연구에는 수정주가 요청 자료만 사용합니다.")
    hashes[str(path)] = hashlib.sha256(raw).hexdigest()
    return record


def daily_window(bars, start, end):
    converted = [{**bar, "time": bar["date"]} for bar in bars]
    return ([bar for bar in converted if start <= bar["date"] <= end],
            [bar for bar in converted if bar["date"] < start][-253:])


def evaluate_one(bars, warmup, market, family, settings, costs, provider, filtered):
    policy = settings["intraday" if family == "vwap_volume" else "swing"]
    result = replay(bars, market, family, policy, settings["risk"], costs, settings["spread_ratio"], provider, filtered, warmup)
    stressed_costs = copy.deepcopy(costs)
    for name in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
        stressed_costs[name] *= 2
    validate_costs(stressed_costs)
    stress = replay(bars, market, family, policy, settings["risk"], stressed_costs, settings["spread_ratio"] * 2, provider, filtered, warmup)
    summary, criteria = result["summary"], settings["criteria"]
    checks = {"positive": summary["net_return"] > 0, "double_cost_positive": stress["summary"]["net_return"] > 0,
              "drawdown": summary["max_drawdown"] <= criteria["maximum_drawdown"],
              "sample": summary["trades"] >= criteria["minimum_trades"],
              "profit_factor": summary["profit_factor"] is not None and summary["profit_factor"] >= criteria["minimum_profit_factor"]}
    benchmark = buy_and_hold(bars, market, costs, settings["spread_ratio"])
    return {"base": result, "double_cost": stress["summary"], "buy_hold": benchmark["summary"], "checks": checks,
            "verdict": "exploratory_candidate" if all(checks.values()) else "rejected"}


def percent(value):
    return "—" if value is None else f"{value:.2%}"


def number(value):
    return "—" if value is None else f"{value:.2f}"


def write_report(folder, report):
    lines = ["# VWAP·거래량 / MA·모멘텀 독립 비교", "", "실제 저장 시세에 가상 체결·비용을 적용한 탐색이다. 실거래 수익이 아니다.",
        "규칙 2개 × 시장 필터 유무만 사전 고정했다. 결과를 보고 임계값을 다시 최적화하지 않았다.",
        "", "## 조건", "", "- 장중: 완성 5분봉의 세션 HLC3 추정 VWAP 상향 교차 + 이전 10봉 평균 대비 거래량 1.5배.",
        "- 일봉: 종가 > MA20 > MA60, 63거래일 모멘텀 양수. MA20 이탈·모멘텀 약화는 다음 날 시가 청산.",
        "- 공통: ATR14 단순평균, 2 ATR 고정 손절, 이전 고점에서 3 ATR 추적 손절, 거래 위험 0.5%, 초기 자금의 최대 10% 투자.",
        "- 일일 평가손실 1% 도달 시 그날 신규 진입 중단. 갭·비용으로 손실이 예산을 초과할 수 있다.",
        "- 장중은 당일 청산·최대 12봉 보유, 일봉은 최대 60거래일 보유. 각 종목은 별도 연구 계좌다.",
        "- 시장 필터: KODEX 200(KR)·SPY(US)의 MA20/60와 장기 평균 기울기. 2일 지연, 최대 7일 자료만 사용. 상승 국면에서만 신규 진입.",
        "- 매수·신호 매도는 다음 봉 시가, 갭 손절은 낮은 시가 반영. 고점·ATR은 다음 봉 손절부터 반영.",
        "- 현금 이자·환율·역사 세금·부분 체결은 미반영. 공통 비용은 declaration.json에 기록한다.", ""]
    for scope, title in [("matched", "같은 종목·같은 기간 비교"), ("extended_daily", "일봉 15종목 확대 평가")]:
        lines += [f"## {title}", "", "| 종목 | 전략 | 시장 필터 | 실제 평가 기간 | 수익 | 비용 2배 | MDD | Sharpe | PF | 승률 | 손익비 | 거래 | 판정 |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        for row in report["runs"]:
            if row["scope"] != scope:
                continue
            summary = row["result"]["base"]["summary"]
            lines.append(f"| {row['symbol']} | {row['family']} | {row['market_filter']} | {row['start']}~{row['end']} | {percent(summary['net_return'])} | {percent(row['result']['double_cost']['net_return'])} | {percent(summary['max_drawdown'])} | {number(summary['sharpe'])} | {number(summary['profit_factor'])} | {percent(summary['win_rate'])} | {number(summary['payoff_ratio'])} | {summary['trades']} | {row['result']['verdict']} |")
    lines += ["", "## 기준선", "", "| 종목 | 기간 | 기존 가격돌파 연구 수익 | 같은 기간 초기 10% 보유 수익 |", "|---|---|---:|---:|"]
    for symbol, reference in report["references"].items():
        lines.append(f"| {symbol} | {reference['start']}~{reference['end']} | {percent(reference['legacy']['summary']['net_return'])} | {percent(reference['buy_hold']['summary']['net_return'])} |")
    lines += ["", "![같은 기간 계좌 비교](matched.png)", "", "![일봉 수익과 낙폭](daily.png)", "", "## 한계와 적용", "",
        "- PF는 손실 거래가 없으면 정의하지 않는다. Sharpe는 일별 평가액 수익률·연 252일·무위험 수익률 0%이며 짧은 표본에서 불안정하다.",
        "- 분봉은 삼성전자·애플 두 종목만 저장돼 있다. 장중 전략의 다른 종목 일반화는 미검증이다.",
        "- 모든 종목 수익률은 개별 계좌 기준이다. 합계·평균을 공동 자금 포트폴리오 수익으로 해석하면 안 된다.",
        "- 가격돌파 기준선은 기존 연구 모듈을 사용한 뉴스 제외 대조군이다. 과거 확정 뉴스가 없어 현재 뉴스 기반 실시간 엔진의 백테스트는 아니다.",
        "- 장기 보유 기준선과 단타는 시장 노출·거래 빈도가 다르다. 데이터 빈도별 낙폭 관측 차이도 남는다.",
        "- 저장 자료는 manifest와 해시로 확인한 KIS 과거 수정주가·원시 분봉이다. 오류 봉 제외 내역은 수집 보고서를 참조한다. 현재 KIS 실시간 체결 품질 검증과 구분한다.",
        "- 기존에 본 과거 자료를 재사용했다. 현재 생존 종목 선정·수정주가의 사후 정보·배당 누락 한계가 있다.",
        "- 성과 판정은 수익 양수·비용 2배 양수·MDD 5% 이하·30거래 이상·PF 1.2 이상. 통과해도 탐색 후보이며 독립 검증·실전 승인이 아니다.",
        "- 새 전략은 --test strategies 연구 기능에 연결했다. 기본 실시간 뉴스 전략과 실제 주문 설정은 변경하지 않았다.",
        "- 초단위 호가 불균형·체결 강도는 틱 자료와 재현 가능한 호가 이력이 없어 구현하지 않았다. RSI·MACD를 중복 조건으로 추가하지 않았다.", "", "## 제외·부족 자료", ""]
    lines += [f"- {symbol}: {reason}" for symbol, reason in report["skipped"].items()]
    lines += ["", "## 공식 지표 참고", "", "- [VWAP 정의](https://www.interactivebrokers.com/campus/glossary-terms/volume-weighted-average-price-vwap/)",
              "- [ATR·TR 설명](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr)"]
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_report(folder, report):
    import os
    os.environ["MPLCONFIGDIR"] = str(DATA_ROOT / "cache/plots")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    symbols = list(report["references"])
    figure, axes = plt.subplots(len(symbols), 1, figsize=(12, 4 * len(symbols)), squeeze=False)
    for axis, symbol in zip(axes.flat, symbols):
        initial = report["costs"]["starting_cash"][symbol.split(":")[0]]
        for row in report["runs"]:
            if row["scope"] != "matched" or row["symbol"] != symbol:
                continue
            daily = {}
            for point in row["result"]["base"]["curve"]:
                daily[point["date"]] = point["equity"]
            axis.plot([date.fromisoformat(day) for day in daily], [(equity / initial - 1) * 100 for equity in daily.values()], label=row["family"] + (" + market" if row["market_filter"] else ""))
        for name in ("legacy", "buy_hold"):
            daily = {row["date"]: row["equity"] for row in report["references"][symbol][name]["curve"]}
            axis.plot([date.fromisoformat(day) for day in daily], [(equity / initial - 1) * 100 for equity in daily.values()], linestyle="--", label=name)
        axis.set_title(symbol + ": same dates, separate simulated accounts")
        axis.set_ylabel("Account return (%)")
        axis.grid(alpha=.2)
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(folder / "matched.png", dpi=150)
    plt.close(figure)
    rows = [row for row in report["runs"] if row["scope"] == "extended_daily"]
    figure, axis = plt.subplots(figsize=(12, 7))
    for filtered, marker in ((False, "o"), (True, "x")):
        selected = [row for row in rows if row["market_filter"] == filtered]
        axis.scatter([row["result"]["base"]["summary"]["max_drawdown"] * 100 for row in selected],
                     [row["result"]["base"]["summary"]["net_return"] * 100 for row in selected], marker=marker, label="MA + momentum" + (" + market" if filtered else ""))
        for row in selected:
            summary = row["result"]["base"]["summary"]
            axis.annotate(row["symbol"], (summary["max_drawdown"] * 100, summary["net_return"] * 100), fontsize=7)
    axis.axhline(0, color="gray", linewidth=.7)
    axis.axvline(5, color="red", linestyle="--", linewidth=.7)
    axis.set_xlabel("Maximum drawdown (%)")
    axis.set_ylabel("Net account return (%)")
    axis.set_title("Daily strategies - separate accounts, historical exploratory comparison")
    axis.legend()
    figure.tight_layout()
    figure.savefig(folder / "daily.png", dpi=150)
    plt.close(figure)


def main():
    settings = load_settings()
    runtime = load_run_settings()
    costs = json.loads(runtime["paper_settings"].read_text(encoding="utf-8"))
    validate_costs(costs)
    folder = RESULTS_ROOT / "technical-strategies" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True)
    write_json(folder / "declaration.json", {"settings": settings, "costs": costs,
        "fixed_families": ["vwap_volume", "ma_momentum"], "market_filter_variants": [False, True],
        "purpose": "fixed_rule_exploration", "live_strategy_updated": False})
    source = folder / "source"
    source.mkdir()
    for relative in ("strategy/technical.py", "research/technical.py", "research/backtest.py", "tools/research_technical.py"):
        shutil.copy2(PROJECT_ROOT / relative, source / Path(relative).name.replace(".py", "-" + Path(relative).parent.name + ".py"))
    hashes, providers = {}, {}
    for market in sorted({market for market, symbol in runtime["symbols"]}):
        symbol = "SPY" if market == "US" else "069500"
        path = DATA_ROOT / "history/daily" / f"{market}-{symbol}.json"
        providers[market] = MarketRegime(prepare_daily_bars(load_record(path, market, symbol, hashes)), settings["regime"])
    report = {"settings": settings, "costs": costs, "runs": [], "references": {}, "skipped": {},
              "source_hashes": hashes, "live_strategy_updated": False}
    for market, symbol in runtime["symbols"]:
        key = market + ":" + symbol
        if key == "US:GOOG":
            report["skipped"][key] = "동일 회사 중복을 줄이기 위해 GOOGL로 대표"
            continue
        daily_path = DATA_ROOT / "history/daily" / f"{market}-{symbol}.json"
        if not daily_path.exists():
            report["skipped"][key] = "저장된 장기 수정주가 없음. 신규 API 수집 없이 제외"
            continue
        daily = prepare_daily_bars(load_record(daily_path, market, symbol, hashes))
        selected, warmup = daily_window(daily, settings["start"], settings["end"])
        if len(selected) < 2:
            report["skipped"][key] = "평가 구간 일봉 부족"
            continue
        for filtered in (False, True):
            outcome = evaluate_one(selected, warmup, market, "ma_momentum", settings, costs, providers[market], filtered)
            report["runs"].append({"symbol": key, "family": "ma_momentum", "market_filter": filtered,
                "scope": "extended_daily", "start": selected[0]["date"], "end": selected[-1]["date"], "result": outcome})
        minute_path = DATA_ROOT / "history/minute" / f"{market}-{symbol}.json"
        if not minute_path.exists():
            report["skipped"][key + " 장중"] = "저장된 분봉 없음. 일봉 평가만 수행"
            continue
        raw = load_record(minute_path, market, symbol, hashes, "1m")
        sessions = [session for session in prepare_sessions(raw) if settings["start"] <= session["date"] <= settings["end"]]
        if not sessions:
            report["skipped"][key + " 장중"] = "완전한 정규장 세션 없음"
            continue
        # 두 전략을 동일 거래일에 평가한다. 제외된 부분 세션 날짜에 일봉 거래도 넣지 않는다.
        days = {session["date"] for session in sessions}
        intraday = [{**bar, "date": session["date"], "time": bar["end"]} for session in sessions for bar in session["bars"]]
        matched_daily, daily_warmup = daily_window(daily, sessions[0]["date"], sessions[-1]["date"])
        if {bar["date"] for bar in matched_daily} != days:
            report["skipped"][key + " 장중"] = "오류 봉 제외·부분 세션으로 일봉과 날짜 불일치. 동일 기간 비교 제외"
            continue
        reference_rule = {"family": "breakout", "lookback": 20, "volume_ratio": 2.0, "stop_loss": .03,
            "trailing_stop": .04, "deviation": .01, "max_chase": .02, "hold_overnight": False, "max_holding_sessions": 1}
        reference = simulate(sessions, reference_rule, costs, settings["spread_ratio"])
        reference["summary"] = performance(reference["curve"], reference["trades"], costs["starting_cash"][market])
        report["references"][key] = {"start": sessions[0]["date"], "end": sessions[-1]["date"],
            "legacy": reference, "buy_hold": buy_and_hold(intraday, market, costs, settings["spread_ratio"])}
        for family, bars, previous in (("vwap_volume", intraday, []), ("ma_momentum", matched_daily, daily_warmup)):
            for filtered in (False, True):
                outcome = evaluate_one(bars, previous, market, family, settings, costs, providers[market], filtered)
                report["runs"].append({"symbol": key, "family": family, "market_filter": filtered, "scope": "matched",
                    "start": bars[0]["date"], "end": bars[-1]["date"], "result": outcome})
                print(f"{key} {family} market={filtered}: 수익 {outcome['base']['summary']['net_return']:.2%}, MDD {outcome['base']['summary']['max_drawdown']:.2%}, {outcome['base']['summary']['trades']}거래", flush=True)
    if not report["references"]:
        raise ValueError("동일 기간 비교를 위한 실제 분봉 자료가 없습니다.")
    write_json(folder / "results.json", report)
    write_report(folder, report)
    plot_report(folder, report)
    write_json(folder.parent / "latest.json", {"folder": str(folder)})
    print(f"기술적 전략 비교 보고서: {folder / 'report.md'}")
