"""가격·거래량 전략을 별도 설정으로 재생한다. 인증·실제 주문·운용 계좌에는 접근하지 않는다."""
import copy
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from paths import CODE_ROOT, CONFIG_ROOT, DATA_ROOT, RESULTS_ROOT
from strategy.engine import load_config
from research.engine_backtest import replay
from tools.research_engine_backtest import (
    load_inputs, write_json, stock_attribution, write_validation, plot_report,
)


def research_strategy():
    """운용 설정을 복사해 덮어쓰지 않고 연구 파일만 읽는다."""
    settings = json.loads((CONFIG_ROOT / "strategy-price-research.json").read_text(encoding="utf-8"))
    if settings.get("news_enabled") is not False or settings.get("earnings_enabled") is not False:
        raise ValueError("가격 연구는 일반 뉴스·실적 조건을 모두 꺼야 합니다.")
    return settings


def audit_symbols(symbols, prepared):
    """저장된 회사 식별·허용 상품·정규장 시세를 대조한다. 현재 상장 상태를 새 조회한 검사는 아니다."""
    companies = json.loads((CONFIG_ROOT / "watchlist.json").read_text(encoding="utf-8"))["companies"]
    policy = json.loads((CONFIG_ROOT / "product-policy.json").read_text(encoding="utf-8"))
    rows = []
    for market, symbol in symbols:
        company = companies.get(symbol, {})
        verified = policy["verified_instruments"].get(symbol, {})
        sessions = prepared[market + ":" + symbol]
        submission = DATA_ROOT / "earnings-audit/raw" / (symbol + "-submissions.json")
        filing = json.loads(submission.read_text(encoding="utf-8")) if submission.exists() else {}
        tickers = filing.get("tickers", [])
        rows.append({"symbol": market + ":" + symbol, "name": company.get("name"),
            "exchange": company.get("exchange"), "asset_type": verified.get("asset_type"),
            "sec_ticker_matches_saved_source": symbol in tickers,
            "sec_name": filing.get("name"), "first_session": sessions[0]["day"],
            "last_session": sessions[-1]["day"], "sessions": len(sessions),
            "latest_session_missing_minutes": sessions[-1]["expected_minutes"] - len(sessions[-1]["minutes"]),
            "identity_status": "saved_sources_consistent" if company.get("name") and company.get("exchange")
                and verified.get("asset_type") in policy["allowed_asset_types"] and symbol in tickers else "needs_review"})
    return rows


def main():
    strategy = research_strategy()
    symbols, _, paper, prepared, hashes, coverage, start, end = load_inputs(strategy)
    rows = audit_symbols(symbols, prepared)
    folder = RESULTS_ROOT / "price-research" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True)
    days = sorted({session["day"] for sessions in prepared.values() for session in sessions if start <= session["day"] <= end})
    if len(days) < 4:
        raise ValueError("구간을 나누려면 최소 4거래일이 필요합니다.")
    midpoint = len(days) // 2
    double = copy.deepcopy(paper)
    for name in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio"):
        double[name] *= 2
    # 결과를 보기 전에 고정한다. 두 구간은 각각 초기 자금으로 시작하는 안정성 진단이다.
    scenarios = {"base": (paper, start, end), "double_cost": (double, start, end),
        "early_period": (paper, start, days[midpoint - 1]), "late_period": (paper, days[midpoint], end)}
    declaration = {"symbols": symbols, "start": start, "end": end, "strategy": load_config(strategy),
        "paper": paper, "coverage": coverage, "source_hashes": hashes, "optimization": False,
        "independent_holdout": False, "live_config_modified": False, "actual_quotes": False,
        "scenarios": scenarios, "safety": json.loads((CONFIG_ROOT / "safety.json").read_text(encoding="utf-8"))}
    for relative in ("strategy/engine.py", "strategy/exits.py", "trading/paper.py", "trading/safety.py",
                     "research/engine_backtest.py", "tools/price_research.py", "tools/research_engine_backtest.py"):
        raw = (CODE_ROOT / relative).read_bytes()
        destination = folder / "source" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        declaration.setdefault("code_hashes", {})[relative] = hashlib.sha256(raw).hexdigest()
    write_json(folder / "declaration.json", declaration)
    write_json(folder / "symbol-audit.json", rows)
    results = {}
    for name, (costs, first, last) in scenarios.items():
        print(f"[{name}] {first} ~ {last}", flush=True)
        results[name] = replay(prepared, symbols, strategy, costs, .001, first, last,
                               progress=lambda day: print("  " + day, flush=True))
        write_json(folder / (name + ".json"), results[name])
        print(json.dumps(results[name]["summary"], ensure_ascii=False), flush=True)
    attribution = stock_attribution(results["base"], symbols)
    write_validation(folder, declaration, results, attribution)
    plot_report(folder, results, attribution)
    write_json(folder / "attribution.json", attribution)
    lines = ["# 뉴스·실적을 사용하지 않는 가격·거래량 연구", "",
        f"기간: {start} ~ {end}. {len(symbols)}종목 공동 가상 계좌. 실제 KIS 분봉과 가상 호가를 사용했다.", "",
        "운용 strategy.json·settings.json·기존 계좌는 변경하지 않았다. 별도 strategy-price-research.json을 사용한다.",
        "일반 뉴스·실적 조건만 끄고 돌파·거래량·매도 규칙과 안전장치는 유지했다. 결과에 맞춘 수치 조정은 하지 않았다.", "",
        "## 비용 반영 결과", "", "|조건|순수익률|최대 낙폭|완료 거래|승률|Profit Factor|", "|---|---:|---:|---:|---:|---:|"]
    for name, result in results.items():
        summary = result["summary"]
        win = f"{summary['win_rate']:.1%}" if summary["win_rate"] is not None else "정의 불가"
        factor = f"{summary['profit_factor']:.3f}" if summary["profit_factor"] is not None else "정의 불가"
        lines.append(f"|{name}|{summary['net_return']:.2%}|{summary['max_drawdown']:.2%}|{summary['closed_trades']}|{win}|{factor}|")
    lines += ["|현금 대기(이자 제외)|0.00%|0.00%|0|해당 없음|해당 없음|", "",
        "두 구간은 전체 기간의 앞/뒤 절반이며 각각 초기 자금으로 시작한다. 두 수익률을 더하지 않는다.",
        "자료는 이전 연구에서 사용한 구간이다. 날짜를 나눠도 새로운 독립 검증이 되지 않는다. 시장지수 대비 초과수익은 이 분봉 시험에서 산출하지 않았다.", "",
        "## 저장된 종목·데이터 상태", "", "|종목|회사명|거래소|식별 대조|처음~마지막 거래일|거래일 수|", "|---|---|---|---|---|---:|"]
    for row in rows:
        lines.append(f"|{row['symbol']}|{row['name']}|{row['exchange']}|{row['identity_status']}|{row['first_session']} ~ {row['last_session']}|{row['sessions']}|")
    lines += ["", "회사 식별은 저장된 KIS 설정·SEC submissions 대조이며 최신 온라인 상장·거래 가능 확인이 아니다.",
        "누락 거래일·분봉은 declaration.json coverage에 기록했다. 장기 일봉을 분봉으로 늘려 쓰지 않았다.", "",
        "## 판정과 다음 행동", "",
        "이 짧은 재사용 구간만으로 실전 채택하지 않는다. 비용 후 손실이면 해당 조건은 채택 보류하고, 미사용 장기 분봉·실제 호가와 이후 모의 관측으로 확인한다.",
        "실시간 수집·지속 모의 운용을 이번 명령이 시작하지는 않는다. 기본 main.py는 검증 실적 조건이 켜진 상태 그대로다.",
        "실시간 연구 모드 연결 전 종목·신선도 검사를 하고, 별도 가상 계좌·일별 손익·차단 사유를 기록해야 한다. FMP는 사용하지 않는다.", "",
        "![비용·구간별 평가](performance.png)", "", "![종목별 기여](stocks.png)", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")
    destination = DATA_ROOT / "reports/price-research"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("declaration.json", "symbol-audit.json", "attribution.json", "report.md", "performance.png", "stocks.png", "validation.md", "validation.json"):
        shutil.copy2(folder / name, destination / name)
    for path in (folder.parent, destination):
        write_json(path / "latest.json", {"folder": str(folder)})
    with (CONFIG_ROOT.parent / "Docs/RESEARCH_LOG.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n\n## {folder.name} — 별도 설정 가격·거래량 연구\n")
        stream.write(f"\n결과: {folder}. 뉴스·실적 조건 비활성, 운용 설정 보존. 기본 {results['base']['summary']['net_return']:.2%}, 비용 두 배 {results['double_cost']['summary']['net_return']:.2%}. 기존 구간 재사용, 실전 채택 보류.\n")
    print("보고서:", destination / "report.md", flush=True)
