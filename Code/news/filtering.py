"""출처·회사 일치·사건 종류·시각으로 검토할 뉴스만 선별한다.

허용 출처는 편집 가능한 정책이며 사실 보증이나 주가 예측 점수가 아니다.
Google RSS의 출처 메타데이터를 비교하며 기사 원문 도메인을 독립 검증하지 않는다.
통과한 기사도 미확정 후보다. 매매에 쓰려면 원문·금액·맥락 검토가 필요하다.
"""
import json
import re
from urllib.parse import urlsplit

from paths import PROJECT_ROOT, CONFIG_ROOT
from strategy.engine import parse_timestamp

FILTER_PATH = CONFIG_ROOT / "news-filter.json"

# 사건은 영향 검토 대상일 뿐, 항상 같은 방향으로 가격이 움직인다는 의미가 아니다.
IMPACT_PATTERNS = {
    "earnings_or_guidance": r"실적\s*(?:발표|전망|상향|하향)|잠정\s*실적|가이던스|(?:영업이익|매출|순이익).{0,20}(?:증가|감소|발표|상향|하향)|\b(?:earnings|guidance)\b|\b(?:profit|revenue).{0,25}(?:reports?|beats?|misses?|rises?|falls?|forecast|outlook)\b",
    "contract": r"(?:공급|수주)\s*계약|계약\s*(?:체결|해지|취소)|\b(?:signs?|wins?|cancels?|terminates?).{0,30}(?:contract|deal)\b",
    "buyback_or_dividend": r"자사주\s*(?:매입|취득|소각)|배당.{0,15}(?:결정|인상|축소|삭감)|\b(?:buyback|repurchase)\b|\bdividend.{0,20}(?:raises?|cuts?|increase|decrease|announces?)\b",
    "capital_or_debt": r"유상\s*증자|전환\s*사채|감자\s*결정|\b(?:share offering|stock offering|convertible bonds?|debt default)\b",
    "merger_acquisition": r"인수\s*(?:계약|발표|합의)|합병\s*(?:계약|발표|승인)|\b(?:acquires?|acquisition|merger|takeover)\b",
    "regulatory_or_legal": r"과징금|영업\s*정지|소송\s*(?:제기|판결)|회계\s*(?:부정|오류)|분식\s*회계|\b(?:antitrust|regulatory approval|accounting fraud|restatement|lawsuit|fined)\b",
    "operating_disruption": r"공장.{0,15}(?:화재|중단)|생산\s*중단|제품\s*리콜|\b(?:recalls?|production halt|factory fire|plant shutdown)\b",
    "demand_or_production": r"감산|증산|(?:생산량|주문량|출하량).{0,15}(?:축소|감소|확대|증가)|\b(?:cuts?|reduces?|raises?|increases?).{0,45}(?:orders|production|output|shipments)\b",
    "financial_distress": r"부도|회생\s*절차|파산\s*(?:신청|선고)|\b(?:bankruptcy|insolvency|files for bankruptcy)\b",
}
OPINION_PATTERN = r"목표\s*주가|주가\s*전망|매수\s*추천|추천\s*종목|수혜주|대박|왜\s*이래|저평가|고평가|\b(?:price target|stock forecast|overvalued|undervalued|stocks? to buy|technical analysis)\b"
UNCERTAIN_PATTERN = r"루머|가능성|검토\s*중|추측|사실무근|부인|\b(?:rumou?r|could|considering|denies|analysts?)\b|\bmay\s+(?:raise|cut|announce|acquire|launch)\b"
DELAYED_FLOW_PATTERN = r"지분율|외국인\s*보유율|\b(?:buys?|sells?)\s+[\d,.]+\s+shares\b"


def load_filter_policy(path=FILTER_PATH):
    policy = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(policy, dict):
        raise ValueError("뉴스 필터 설정은 JSON 객체여야 합니다.")
    age = policy.get("max_age_hours")
    if isinstance(age, bool) or not isinstance(age, (int, float)) or not 0 < age <= 168:
        raise ValueError("뉴스 유효 시간은 0 초과 168시간 이하여야 합니다.")
    allowed_sources = policy.get("allowed_sources")
    if not isinstance(allowed_sources, dict):
        raise ValueError("시장별 허용 뉴스 출처 목록이 필요합니다.")
    for market in ("KR", "US"):
        sources = allowed_sources.get(market)
        if not isinstance(sources, list) or not sources:
            raise ValueError("시장별 허용 뉴스 출처 목록이 필요합니다.")
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("뉴스 출처는 도메인과 언론사 이름을 가진 객체여야 합니다.")
            domain = source.get("domain")
            publishers = source.get("publishers")
            domain_pattern = r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}"
            if not isinstance(domain, str) or not re.fullmatch(domain_pattern, domain):
                raise ValueError("뉴스 출처에는 URL이 아닌 도메인을 적으세요.")
            if not isinstance(publishers, list) or not publishers or not all(isinstance(item, str) and item.strip() for item in publishers):
                raise ValueError("출처별 RSS 언론사 이름 목록이 필요합니다.")
    if not isinstance(policy.get("company_aliases"), dict):
        raise ValueError("종목별 회사 이름 목록이 필요합니다.")
    for aliases in policy["company_aliases"].values():
        if not isinstance(aliases, list) or not aliases or not all(isinstance(item, str) and item.strip() for item in aliases):
            raise ValueError("회사 이름은 비어 있지 않은 문자열 배열이어야 합니다.")
    return policy


def company_in_title(title, aliases):
    # 영문 ticker를 단어 경계로 비교해 AAPL이 긴 다른 이름 안에 포함되는 경우를 막는다.
    for alias in aliases:
        pattern = re.escape(alias)
        if alias.isascii():
            pattern = r"(?<![A-Za-z0-9])" + pattern + r"(?![A-Za-z0-9])"
        if re.search(pattern, title, re.IGNORECASE):
            return True
    return False


def source_matches(candidate, policy):
    """RSS의 출처 도메인과 언론사 이름이 모두 허용 목록과 일치해야 한다."""
    source = urlsplit(candidate.get("source_url", ""))
    domain = (source.hostname or "").lower()
    publisher = candidate.get("publisher", "").strip().casefold()
    if source.scheme not in {"http", "https"}:
        return False
    for allowed in policy["allowed_sources"][candidate["market"]]:
        matches_domain = domain == allowed["domain"] or domain.endswith("." + allowed["domain"])
        matches_name = publisher in {name.casefold() for name in allowed["publishers"]}
        if matches_domain and matches_name:
            return True
    return False


def select_candidate(candidate, policy, now):
    """검토 후보 선정과 제외 이유를 반환한다. 확정·출처 검증 표시를 true로 올리지 않는다."""
    selected = dict(candidate)
    title = candidate["title"]
    reasons = []
    if not source_matches(candidate, policy):
        reasons.append("출처 도메인·언론사 이름이 허용 목록과 일치하지 않음")
    aliases = policy["company_aliases"].get(candidate["market"] + ":" + candidate["symbol"], [])
    if not company_in_title(title, aliases):
        reasons.append("제목에서 대상 회사 이름을 확인하지 못함")
    try:
        published = parse_timestamp(candidate.get("published_at") or "")
        age = (now - published).total_seconds()
        if not 0 <= age <= policy["max_age_hours"] * 3600:
            reasons.append("기사 발행 시각이 미래이거나 유효 기간 초과")
    except (ValueError, TypeError, AttributeError):
        reasons.append("시간대가 포함된 기사 발행 시각 없음")
    events = [name for name, pattern in IMPACT_PATTERNS.items() if re.search(pattern, title, re.IGNORECASE)]
    if not events:
        reasons.append("선정한 실적·계약·재무·규제·생산 사건에 해당하지 않음")
    if re.search(OPINION_PATTERN, title, re.IGNORECASE):
        reasons.append("추천·가치평가·주가 전망·클릭 유도 표현")
    if re.search(UNCERTAIN_PATTERN, title, re.IGNORECASE):
        reasons.append("추측·검토·부인·애널리스트 의견 표현")
    if re.search(DELAYED_FLOW_PATTERN, title, re.IGNORECASE):
        reasons.append("지분율·보유 변동 보도: 직접 사건 대신 지연된 수급 정보")
    selected.update(selection_status="excluded" if reasons else "selected", selection_reasons=reasons or ["허용 출처·회사 일치·최근 발행·사건 종류 조건 통과"],
                    impact_events=events, source_check="rss_metadata_only", confirmed=False, source_verified=False)
    return selected


def filter_candidates(candidates, policy, now):
    records = [select_candidate(candidate, policy, now) for candidate in candidates]
    return {"checked_at": now.isoformat(), "fetched_count": len(records),
            "selected": [item for item in records if item["selection_status"] == "selected"],
            "excluded": [item for item in records if item["selection_status"] == "excluded"]}
