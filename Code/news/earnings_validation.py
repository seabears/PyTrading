"""실적 수치·예상치의 기간·단위·회계 기준을 대조한다. 모르는 항목은 통과시키지 않는다."""
import json
import math
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from paths import DATA_ROOT
from strategy.engine import parse_timestamp


AUDIT_ROOT = DATA_ROOT / "earnings-audit"
REVENUE_TAGS = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet")


def quarter_facts(companyfacts, concept, unit, ending, as_of):
    """당시 제출된 70~105일짜리 단독 분기만 읽는다. 누적 6·9개월이나 연간 EPS를 빼서 만들지 않는다."""
    rows = companyfacts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get(unit, [])
    valid = []
    for row in rows:
        if row.get("end") != ending or row.get("filed", "9999") > as_of or row.get("form") not in {"10-Q", "10-K"}:
            continue
        if "start" not in row or not 70 <= (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days <= 105:
            continue
        valid.append(row)
    if not valid:
        return {"status": "no_standalone_quarter_fact"}
    earliest = min(row["filed"] for row in valid)
    originals = [row for row in valid if row["filed"] == earliest]
    if len({(row["start"], row["val"]) for row in originals}) != 1:
        return {"status": "conflicting_original_facts"}
    row = originals[0]
    return {"status": "found", **row, "concept": concept, "unit": unit,
            "later_value_changed": any(row["val"] != other["val"] for other in valid)}


def validate_claim(claim, official, now):
    """실적 원본과 발표 전 예상치를 구분한다. 단순 검증 완료 플래그를 신뢰하지 않는다."""
    reasons = []
    if claim.get("metric") != "eps":
        reasons.append("unsupported_claim_metric")
    if official.get("status") != "found":
        reasons.append("official_quarter_not_found")
    if official.get("later_value_changed"):
        reasons.append("later_filing_changed_original_value")
    for key in ("symbol", "period_start", "period_end", "basis", "unit"):
        if not claim.get(key) or claim.get(key) != official.get(key):
            reasons.append(key + "_mismatch")
    if claim.get("basis") != "GAAP":
        reasons.append("non_gaap_requires_separate_official_reconciliation")
    try:
        actual, estimate = float(claim["actual"]), float(claim["estimate"])
        if isinstance(claim["actual"], bool) or isinstance(claim["estimate"], bool) or not math.isfinite(actual + estimate):
            raise ValueError("invalid metric")
        tolerance = .005 if claim.get("unit") == "USD/shares" else 50_000_000
        if not math.isclose(actual, float(official["val"]), abs_tol=tolerance, rel_tol=0):
            reasons.append("actual_does_not_match_official")
        if estimate == 0:
            reasons.append("zero_estimate")
    except (KeyError, TypeError, ValueError):
        actual, estimate = None, None
        reasons.append("missing_or_invalid_actual_estimate")
    try:
        release = parse_timestamp(claim["released_at"])
        estimate_seen = parse_timestamp(claim["estimate_observed_at"])
        available = parse_timestamp(claim["verified_at"])
        official_available = parse_timestamp(official["available_at"])
        if not estimate_seen < release <= available <= now or official_available > available:
            reasons.append("invalid_point_in_time_order")
    except (KeyError, ValueError, TypeError, AttributeError):
        reasons.append("missing_point_in_time_evidence")
    for field in ("official_url", "estimate_url"):
        parsed = urlsplit(claim.get(field, ""))
        if parsed.scheme != "https" or not parsed.hostname:
            reasons.append("missing_" + field)
    official_host = (urlsplit(claim.get("official_url", "")).hostname or "").lower()
    if official_host not in {"data.sec.gov", "www.sec.gov", "sec.gov"}:
        reasons.append("official_sec_source_required")
    estimate_host = (urlsplit(claim.get("estimate_url", "")).hostname or "").lower()
    if not any(estimate_host == host or estimate_host.endswith("." + host) for host in ("reuters.com", "bloomberg.com", "wsj.com", "ft.com", "factset.com")):
        reasons.append("estimate_source_not_allowed")
    if not isinstance(claim.get("estimate_snapshot_sha256"), str) or len(claim["estimate_snapshot_sha256"]) != 64:
        reasons.append("missing_pre_release_estimate_snapshot")
    direction = None
    surprise = None
    if not reasons:
        surprise = (actual - estimate) / abs(estimate)
        direction = "positive" if actual > estimate else "negative" if actual < estimate else "neutral"
    return {"verified": not reasons, "reasons": reasons, "direction": direction, "surprise_ratio": surprise}


def eligible_event_ids(now):
    """로컬 검증 이력과 증거 파일 해시를 재검사한다. 근거가 없으면 빈 목록이다."""
    import hashlib
    path = AUDIT_ROOT / "verified-events.json"
    if not path.exists():
        return {}
    records = json.loads(path.read_text(encoding="utf-8"))
    allowed = {}
    for record in records:
        evidence = record.get("evidence_files", [])
        if len(evidence) < 3:
            continue
        valid = True
        for item in evidence:
            target = (AUDIT_ROOT / item["relative_path"]).resolve()
            if not target.is_relative_to(AUDIT_ROOT.resolve()) or not target.is_file():
                valid = False
                break
            if hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
                valid = False
                break
        claim = record.get("claim", {})
        symbol = claim.get("symbol", "")
        if not symbol.isalnum():
            continue
        facts_path = AUDIT_ROOT / "raw" / (symbol + "-companyfacts.json")
        submissions_path = AUDIT_ROOT / "raw" / (symbol + "-submissions.json")
        required = {str(facts_path.resolve()), str(submissions_path.resolve())}
        provided = {str((AUDIT_ROOT / item["relative_path"]).resolve()) for item in evidence}
        if not required.issubset(provided):
            continue
        estimate_files = [item for item in evidence if item.get("kind") == "consensus_snapshot"
                          and item["sha256"] == claim.get("estimate_snapshot_sha256")]
        if len(estimate_files) != 1:
            continue
        estimate = json.loads((AUDIT_ROOT / estimate_files[0]["relative_path"]).read_text(encoding="utf-8"))
        if any(estimate.get(key) != claim.get(key) for key in ("symbol", "period_start", "period_end", "basis", "unit", "metric")):
            continue
        if estimate.get("value") != claim.get("estimate") or estimate.get("observed_at") != claim.get("estimate_observed_at") or estimate.get("source_url") != claim.get("estimate_url"):
            continue
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
        if symbol not in submissions.get("tickers", []) or facts["cik"] != int(submissions["cik"]):
            continue
        expected_official_url = "https://data.sec.gov/api/xbrl/companyfacts/CIK" + str(facts["cik"]).zfill(10) + ".json"
        if claim.get("official_url") != expected_official_url:
            continue
        original = quarter_facts(facts, "EarningsPerShareDiluted", "USD/shares", claim.get("period_end"), now.date().isoformat())
        recent = submissions["filings"]["recent"]
        if original.get("accn") not in recent["accessionNumber"]:
            continue
        position = recent["accessionNumber"].index(original["accn"])
        official = {**original, "symbol": symbol, "period_start": original["start"], "period_end": original["end"],
                    "basis": "GAAP", "available_at": recent["acceptanceDateTime"][position]}
        result = validate_claim(claim, official, now)
        if valid and result["verified"]:
            allowed[record["event_id"]] = {"symbol": claim["symbol"], "direction": result["direction"],
                                          "released_at": claim["released_at"], "verified_at": claim["verified_at"]}
    return allowed
