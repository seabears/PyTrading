"""실적 발표 제목을 설명 가능한 모의 매매 신호로 분류한다.

허용 언론사의 RSS 메타데이터와 명시적인 예상 대비 실적·회사 전망 표현만 사용한다.
원문·공시 대조를 마친 확정 뉴스와 다르므로 confirmed/source_verified는 올리지 않는다.
실적 증가 자체를 예상 상회로 해석하거나 제목에 없는 수치를 만들지 않는다.
"""
import hashlib
import json
import re
from pathlib import Path

from paths import CONFIG_ROOT
from news.filtering import company_in_title, source_matches
from strategy.engine import parse_timestamp


POLICY_PATH = CONFIG_ROOT / "earnings.json"
PREVIEW = r"\?|\b(?:preview|rumou?r|could|might|expected to|will report|to report|ahead of|what to expect|analysts? (?:expect|predict|forecast))\b|실적\s*발표\s*(?:앞두|예정)|실적\s*예고|실적\s*예상|루머|가능성|추측|사실무근|부인"
OPINION = r"\b(?:price target|rating|stocks? to buy|technical analysis|analysts? (?:raises?|lifts?|boosts?|cuts?|lowers?|reduces?|upgrades?|downgrades?))\b|목표\s*주가|매수\s*추천|추천\s*종목"
NEGATION = r"\b(?:does not|did not|doesn't|didn't|not a|no earnings miss|not cut|not raise)\b|상회하지|하회하지|하향하지|상향하지"
EARNINGS = r"\b(?:earnings|eps|revenue|profit|sales|financial results|quarterly results|guidance|outlook)\b|실적|주당\s*순이익|매출|영업이익|순이익|가이던스"
METRIC = r"(?:earnings|eps|revenue|profit|sales)"
ESTIMATE = r"(?:estimates?|expectations?|forecasts?|consensus)"
POSITIVE = [
    rf"\b{METRIC}\b.{{0,40}}\b(?:beats?|tops?|exceeds?|above)\b.{{0,25}}\b{ESTIMATE}\b",
    rf"\b(?:beats?|tops?)\s+(?:on\s+)?{METRIC}\b",
    r"(?:실적|영업이익|매출|순이익|EPS).{0,25}(?:예상|기대|컨센서스).{0,12}(?:상회|웃돌)|어닝\s*서프라이즈",
]
NEGATIVE = [
    rf"\b{METRIC}\b.{{0,40}}\b(?:miss(?:es)?|below|falls? short of)\b.{{0,25}}\b{ESTIMATE}\b",
    rf"\bmiss(?:es)?\s+(?:on\s+)?{METRIC}\b",
    r"(?:실적|영업이익|매출|순이익|EPS).{0,25}(?:예상|기대|컨센서스).{0,12}(?:하회|밑돌)|어닝\s*쇼크",
]
GUIDANCE_UP = r"\b(?:raises?|lifts?|boosts?)\s+(?:\w+[ -]){0,4}(?:guidance|outlook)\b|(?:가이던스|실적\s*전망).{0,10}상향"
GUIDANCE_DOWN = r"\b(?:cuts?|lowers?|reduces?)\s+(?:\w+[ -]){0,4}(?:guidance|outlook)\b|(?:가이던스|실적\s*전망).{0,10}하향"


def load_policy(path=POLICY_PATH):
    policy = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    for name, minimum, maximum in (("max_age_hours", 1, 48), ("refresh_seconds", 300, 86400),
                                   ("feed_stale_seconds", 600, 172800)):
        value = policy.get(name)
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError("실적 뉴스 시간 설정을 확인하세요: " + name)
    if policy["feed_stale_seconds"] < policy["refresh_seconds"]:
        raise ValueError("실적 뉴스 수집 유효 시간은 갱신 주기 이상이어야 합니다.")
    if not isinstance(policy.get("allowed_sources"), dict) or not isinstance(policy.get("company_aliases"), dict):
        raise ValueError("실적 뉴스 출처·회사 이름 목록이 필요합니다.")
    for market in ("KR", "US"):
        if not policy["allowed_sources"].get(market):
            raise ValueError("시장별 실적 뉴스 허용 출처가 필요합니다.")
        for source in policy["allowed_sources"][market]:
            if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", source.get("domain", "")) or not source.get("publishers"):
                raise ValueError("실적 뉴스 출처 형식을 확인하세요.")
    for aliases in policy["company_aliases"].values():
        if not isinstance(aliases, list) or not aliases or not all(isinstance(alias, str) and alias.strip() for alias in aliases):
            raise ValueError("실적 뉴스 회사 이름은 문자열 목록이어야 합니다.")
    return policy


def classify(candidate, policy, now):
    """제목의 실제 표현과 제외 사유를 함께 남긴다. 분류 결과를 확정 공시로 부르지 않는다."""
    row = dict(candidate)
    title = row.get("title", "")
    reasons = []
    key = row.get("market", "") + ":" + row.get("symbol", "")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("실적 기사 제목이 없습니다.")
    if row.get("market") not in {"KR", "US"} or not source_matches(row, policy):
        reasons.append("source_not_allowed")
    aliases = policy["company_aliases"].get(key, [])
    if not company_in_title(title, aliases):
        reasons.append("company_not_matched")
    else:
        matches = [re.search((r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])") if alias.isascii()
                             else re.escape(alias), title, re.I) for alias in aliases]
        match = min((match for match in matches if match), key=lambda match: match.start())
        following = title[match.end():]
        first_metric = re.search(EARNINGS, title, re.I)
        prefix = title[:match.start()].strip().casefold()
        if re.match(r"(?:['’]s)?\s+(?:supplier|rival|partner|competitor|협력사|경쟁사)\b", following, re.I):
            reasons.append("company_is_related_not_subject")
        elif first_metric and first_metric.start() < match.start() and prefix not in {"earnings:", "earnings results:"}:
            reasons.append("company_is_related_not_subject")
    try:
        published = parse_timestamp(row["published_at"])
        seen = parse_timestamp(row["first_seen_at"])
        if not 0 <= (now - published).total_seconds() <= policy["max_age_hours"] * 3600:
            reasons.append("stale_or_future_publication")
        if seen > now or published > seen:
            reasons.append("invalid_availability_time")
    except (KeyError, TypeError, ValueError, AttributeError):
        reasons.append("invalid_timestamp")
    if re.search(PREVIEW, title, re.I):
        reasons.append("preview_or_uncertain")
    if re.search(OPINION, title, re.I):
        reasons.append("opinion_or_rating")
    if re.search(NEGATION, title, re.I):
        reasons.append("negated_claim")
    if not re.search(EARNINGS, title, re.I):
        reasons.append("not_earnings")
    matched_positive = [pattern for pattern in POSITIVE if re.search(pattern, title, re.I)]
    matched_negative = [pattern for pattern in NEGATIVE if re.search(pattern, title, re.I)]
    guidance_up = bool(re.search(GUIDANCE_UP, title, re.I))
    guidance_down = bool(re.search(GUIDANCE_DOWN, title, re.I))
    # 실적 호조에도 회사 전망을 낮췄다면 부정으로 보되, 상향·하향이 함께 나오면 보류한다.
    if guidance_up and guidance_down:
        direction = "mixed"
    elif guidance_down:
        direction = "negative"
    elif matched_positive and matched_negative or guidance_up and matched_negative:
        direction = "mixed"
    elif matched_negative:
        direction = "negative"
    elif matched_positive or guidance_up:
        direction = "positive"
    else:
        direction = "neutral"
    normalized = re.sub(r"\s+", " ", title.strip().casefold())
    row.update(event_id="earnings-" + hashlib.sha256((key + ":" + normalized).encode()).hexdigest()[:24],
               direction="excluded" if reasons else direction, exclusions=reasons,
               guidance="cut" if guidance_down else "raised" if guidance_up else "not_stated",
               reported_surprise="mixed" if matched_positive and matched_negative else "beat" if matched_positive else "miss" if matched_negative else "not_stated",
               available_at=row.get("first_seen_at"), confirmed=False, source_verified=False,
               evidence_level="rss_headline_and_publisher_metadata", usage="paper_only")
    return row


def collect_report(market, symbol, policy, fetch=None, now=None):
    """허용 출처에 실적 발표 검색을 한다. 증권사 인증·계좌 API는 호출하지 않는다."""
    from datetime import datetime, timezone
    from news.collector import fetch_rss_candidates
    aliases = policy["company_aliases"].get(market + ":" + symbol)
    if not aliases:
        raise ValueError("실적 뉴스 회사 이름 미설정: " + market + ":" + symbol)
    keywords = "실적" if market == "KR" else "earnings"
    query = '"' + aliases[0] + '" ' + keywords
    domains = [source["domain"] for source in policy["allowed_sources"][market]]
    # Google 검색의 OR 범위가 회사 조건을 느슨하게 만들 수 있어 출처별로 좁게 검색한다.
    by_id, source_errors = {}, []
    successful_sources = 0
    for domain in domains:
        try:
            candidates = (fetch or fetch_rss_candidates)(market, symbol, query, [domain])
            successful_sources += 1
            for candidate in candidates:
                by_id[candidate.get("candidate_id") or candidate["url"]] = candidate
        except (ValueError, OSError):
            source_errors.append(domain)
    if successful_sources == 0:
        raise ValueError("모든 실적 뉴스 출처 수집에 실패했습니다.")
    raw = list(by_id.values())
    now = now or datetime.now(timezone.utc)
    rows = [classify(item, policy, now) for item in raw]
    return {"market": market, "symbol": symbol, "query": query, "checked_at": now.isoformat(),
            "fetched_count": len(rows), "source_errors": source_errors, "events": rows}


def active_signals(snapshot, policy, now):
    """파일의 direction 플래그를 신뢰하지 않고 원래 제목·출처·시간을 다시 검사한다."""
    grouped = {"positive": [], "negative": [], "mixed": []}
    verification_required = policy.get("require_primary_verification", True)
    if type(verification_required) is not bool:
        raise ValueError("실적 원문 검증 설정은 true/false여야 합니다.")
    if verification_required:
        from news.earnings_validation import eligible_event_ids
        verified = eligible_event_ids(now)
    else:
        verified = {}
    unverified = []
    seen = set()
    for candidate in snapshot.get("earnings_events", []):
        if candidate.get("market") != snapshot["market"] or candidate.get("symbol") != snapshot["symbol"]:
            continue
        row = classify(candidate, policy, now)
        if row["event_id"] in seen:
            continue
        seen.add(row["event_id"])
        if row["direction"] in grouped:
            validation = verified.get(row["event_id"], {})
            if verification_required:
                try:
                    released = parse_timestamp(validation["released_at"])
                    verified_at = parse_timestamp(validation["verified_at"])
                    published = parse_timestamp(row["published_at"])
                    same_release = (validation.get("symbol") == row["symbol"] and validation.get("direction") == row["direction"]
                        and released <= published <= now and verified_at <= now
                        and (now - released).total_seconds() <= policy["max_age_hours"] * 3600)
                except (KeyError, TypeError, ValueError):
                    same_release = False
                if not same_release:
                    unverified.append(row["event_id"])
                    continue
            grouped[row["direction"]].append(row)
    if grouped["negative"] and grouped["positive"]:
        # 호재와 악재가 공존할 때 전망 하향은 우선한다. 그 외 충돌은 매수만 차단한다.
        if not any(row["guidance"] == "cut" for row in grouped["negative"]):
            grouped["mixed"] += grouped["positive"] + grouped["negative"]
            grouped["positive"], grouped["negative"] = [], []
    return {**{kind: [row["event_id"] for row in rows] for kind, rows in grouped.items()}, "unverified": unverified}
