"""SEC·IR 원문 수치 대조와 발표 후 수익의 제한된 진단. 당시 수신 이력을 만들지 않는다."""
import hashlib
import json
import math
import re
from datetime import datetime
from html.parser import HTMLParser

from paths import DATA_ROOT
from news.earnings_validation import quarter_facts, REVENUE_TAGS
from research.daily import prepare_daily_bars
from research.entry_timing import net_return


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.hidden = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def extract_release(raw, symbol):
    parser = VisibleText()
    parser.feed(raw.decode("utf-8"))
    text = " ".join(" ".join(parser.parts).split())
    month = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    ending = re.search(r"quarter ended (" + month + r" \d{1,2}, \d{4})", text, re.I)
    announcement = re.search(month + r" \d{1,2},? \d{4}", text)
    if ending is None or announcement is None:
        raise ValueError("공식 발표의 분기 종료일·발표일을 읽지 못했습니다.")
    revenue = re.search(r"(?:quarterly\s+)?revenue\s+(?:was|of)\s*\$([\d,.]+)\s*billion", text, re.I)
    # 뒤쪽 연간 요약·조정 주석을 분기 EPS로 읽지 않도록 발표 첫 문단 범위로 제한한다.
    intro = text[ending.end():ending.end() + 1800]
    if symbol == "NVDA":
        eps = re.search(r"GAAP and non-GAAP earnings per diluted share were \$(\d+(?:\.\d+)?) and \$(\d+(?:\.\d+)?)", intro, re.I)
        adjusted = float(eps.group(2)) if eps else None
    else:
        eps = re.search(r"(?:diluted )?earnings per share (?:on a GAAP basis )?(?:was|of|were)\s*\$(\d+(?:\.\d+)?)", intro, re.I)
        adjusted = None
        if symbol == "MSFT" and eps:
            context = intro[eps.start():eps.start() + 250]
            extra = re.search(r"non-GAAP basis.*?", context)
            values = re.findall(r"(?:was|were) \$(\d+(?:\.\d+)?)", context)
            if extra and len(values) >= 2:
                adjusted = float(values[1])
    if revenue is None or eps is None:
        raise ValueError("공식 발표 매출·EPS 문장을 읽지 못했습니다.")
    return {"period_end": datetime.strptime(ending.group(1), "%B %d, %Y").date().isoformat(),
            "announcement_date": datetime.strptime(announcement.group().replace(",", ""), "%B %d %Y").date().isoformat(),
            "ir_revenue": float(revenue.group(1).replace(",", "")) * 1e9,
            "ir_eps_gaap": float(eps.group(1)), "ir_eps_non_gaap": adjusted,
            "revenue_rounding_tolerance": 50_000_000, "basis": "GAAP", "unit": "USD"}


def audit_release(release, facts, as_of):
    ending = release["period_end"]
    revenue = {"status": "no_standalone_quarter_fact"}
    for tag in REVENUE_TAGS:
        candidate = quarter_facts(facts, tag, "USD", ending, as_of)
        if candidate["status"] == "found":
            revenue = candidate
            break
    eps = quarter_facts(facts, "EarningsPerShareDiluted", "USD/shares", ending, as_of)
    # 연간 EPS−9개월 EPS는 사용하지 않는다. 분기 단독 사실이 없으면 미검증이다.
    checks = {"revenue": "unverified", "gaap_eps": "unverified", "non_gaap_eps": "not_checked_by_standard_gaap_facts"}
    if revenue["status"] == "found":
        checks["revenue"] = "matched" if math.isclose(revenue["val"], release["ir_revenue"], rel_tol=0,
                                                    abs_tol=release["revenue_rounding_tolerance"]) else "mismatch"
    if eps["status"] == "found":
        checks["gaap_eps"] = "matched" if math.isclose(eps["val"], release["ir_eps_gaap"], rel_tol=0, abs_tol=.005) else "mismatch"
    return {**release, "sec_revenue": revenue, "sec_eps": eps, "checks": checks,
            "actuals_cross_checked": checks["revenue"] == checks["gaap_eps"] == "matched",
            "consensus_verified": False, "trade_signal_verified": False}


def event_diagnostic(audits, series, proxy, costs, spread):
    """실적 상회 전략이 아닌, 원본 수치 확인일 이후의 무조건 보유 사후 진단이다."""
    results = []
    proxy_map = {bar["date"]: bar for bar in proxy}
    calendar = sorted(proxy_map)
    for audit in audits:
        if not audit.get("actuals_cross_checked"):
            continue
        known_after = max(audit["announcement_date"], audit["sec_revenue"]["filed"], audit["sec_eps"]["filed"])
        bars = series[audit["symbol"]]
        indexed = {bar["date"]: bar for bar in bars}
        entry = next((index for index, day in enumerate(calendar) if day > known_after), None)
        if entry is None:
            continue
        for horizon in (1, 5, 20):
            if entry + horizon > len(calendar):
                continue
            expected_dates = calendar[entry:entry + horizon]
            if any(day not in indexed for day in expected_dates):
                continue
            window = [indexed[day] for day in expected_dates]
            start, end = window[0], window[-1]
            reference = net_return(proxy_map[start["date"]]["open"], proxy_map[end["date"]]["close"], costs, spread)
            value = net_return(start["open"], end["close"], costs, spread)
            results.append({"release_id": audit["release_id"], "symbol": audit["symbol"], "horizon": horizon,
                "entry_date": start["date"], "exit_date": end["date"], "net_return": value,
                "double_cost_return": net_return(start["open"], end["close"], costs, spread, 2),
                "spy_net_return": reference, "excess_return": value - reference,
                "maximum_adverse_excursion": min(0, min(bar["low"] for bar in window) / start["open"] - 1),
                "timing_assumption": "hypothetical_next_session_after_official_filing_date_not_actual_first_seen",
                "is_original_strategy_backtest": False})
    return results


def audit_identity(row, raw_folder, as_of):
    symbol = row["symbol"]
    facts_path, submissions_path = raw_folder / (symbol + "-companyfacts.json"), raw_folder / (symbol + "-submissions.json")
    if row["status"] != "matched" or not facts_path.exists() or not submissions_path.exists():
        return {**row, "coverage": "unverified"}
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
    identity_ok = int(facts["cik"]) == int(submissions["cik"]) == int(row["cik"]) and symbol in submissions.get("tickers", [])
    taxonomy = "us-gaap" if "us-gaap" in facts.get("facts", {}) else "unsupported_taxonomy"
    return {**row, "identity_verified": identity_ok, "taxonomy": taxonomy,
            "coverage": "sec_source_available" if identity_ok else "identity_mismatch",
            "facts_sha256": hashlib.sha256(facts_path.read_bytes()).hexdigest(),
            "submissions_sha256": hashlib.sha256(submissions_path.read_bytes()).hexdigest()}
