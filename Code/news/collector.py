"""뉴스 제목을 수집하고 사건 후보로 분류한다. 제목을 확정 공시로 간주하지 않는다.

수정 위치: NEWS_QUERIES는 검색 대상, CANDIDATE_RULES는 한·영 키워드 규칙이다.
후보와 확정 사건을 구분한다. confirmed-events.json의 검토된 사건만 매매 근거로 사용한다.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from strategy.engine import NEGATIVE_EVENT_KINDS, POSITIVE_EVENT_KINDS, parse_timestamp
from news.filtering import UNCERTAIN_PATTERN, filter_candidates, load_filter_policy

NEWS_QUERIES = {
    "KR:005930": "삼성전자",
    "KR:000660": "SK하이닉스",
    "US:AAPL": "Apple AAPL",
    "US:MSFT": "Microsoft MSFT",
    "US:NVDA": "Nvidia NVDA",
}

# 제목에서 발견할 수 있는 후보일 뿐, 계약 금액·본문·회사 발표 확인은 별도다.
CANDIDATE_RULES = {
    "earnings_guidance_raised": r"실적\s*전망\s*상향|가이던스\s*상향|raises?\s+(?:\w+\s+){0,2}(?:guidance|outlook)",
    "earnings_guidance_cut": r"실적\s*전망\s*하향|가이던스\s*하향|(?:cuts?|lowers?)\s+(?:\w+\s+){0,2}(?:guidance|outlook)",
    "material_contract_confirmed": r"공급\s*계약\s*체결|수주\s*계약|signs?\s+(?:\w+\s+){0,2}contract",
    "material_contract_cancelled": r"계약\s*(?:취소|해지)|cancels?\s+(?:\w+\s+){0,2}contract",
    "buyback_confirmed": r"자사주\s*(?:매입|취득)|share\s*(?:buyback|repurchase)",
    "accounting_issue_confirmed": r"회계\s*(?:부정|오류)|분식\s*회계|accounting\s*(?:fraud|error)|restatement",
}
UNCERTAINTY_WORDS = UNCERTAIN_PATTERN


def classify_title(title: str) -> dict:
    """모호성·부정 표현이 있으면 자동 확정을 하지 않는 설명 가능한 규칙."""
    matched = [kind for kind, pattern in CANDIDATE_RULES.items() if re.search(pattern, title, re.IGNORECASE)]
    uncertain = bool(re.search(UNCERTAINTY_WORDS, title, re.IGNORECASE))
    return {"candidate_kinds": matched, "uncertain": uncertain,
            "confirmed": False, "source_verified": False}


def fetch_rss_candidates(market: str, symbol: str, query: str, source_domains=None) -> list[dict]:
    """공개 Google News RSS 검색. 토스 인증 정보는 이 요청에 전달하지 않는다."""
    search = query
    if source_domains:
        search = "(" + query + ") (" + " OR ".join("site:" + domain for domain in source_domains) + ")"
    parameters = {"q": search + " when:1d", "hl": "ko" if market == "KR" else "en-US",
                  "gl": "KR" if market == "KR" else "US",
                  "ceid": "KR:ko" if market == "KR" else "US:en"}
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(parameters)
    request = urllib.request.Request(url, headers={"User-Agent": "RuleTrader-News/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            content = response.read(2_000_001)
        if len(content) > 2_000_000:
            raise ValueError("뉴스 응답이 너무 큽니다.")
        root = ET.fromstring(content)
    except (urllib.error.URLError, OSError, ValueError, ET.ParseError):
        raise ValueError("뉴스 수집 실패: 네트워크 또는 RSS 형식을 확인하세요.") from None

    received_at = datetime.now(timezone.utc).isoformat()
    candidates = []
    for item in root.findall("./channel/item")[:50]:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        if not title or not link:
            continue
        # 같은 기사라도 다른 검색 종목에서 발견하면 별도 대상 후보다.
        candidate_id = hashlib.sha256((market + ":" + symbol + ":" + link + ":" + title).encode()).hexdigest()[:20]
        published_at = None
        try:
            published_at = parsedate_to_datetime(item.findtext("pubDate", "")).isoformat()
        except (ValueError, TypeError):
            pass
        source = item.find("source")
        candidates.append({
            "candidate_id": candidate_id, "market": market, "symbol": symbol,
            "title": title, "url": link, "publisher": item.findtext("source", ""),
            "source_url": source.get("url", "") if source is not None else "",
            "published_at": published_at, "first_seen_at": received_at,
            **classify_title(title),
        })
    return candidates


def collect_news(market: str, symbol: str, query: str) -> dict:
    """허용 출처로 검색 범위를 좁히고, 선정·제외 이유를 함께 반환한다."""
    policy = load_filter_policy()
    domains = [source["domain"] for source in policy["allowed_sources"][market]]
    raw = fetch_rss_candidates(market, symbol, query, domains)
    report = filter_candidates(raw, policy, datetime.now(timezone.utc))
    report.update(market=market, symbol=symbol, query=query)
    return report


def fetch_candidates(market: str, symbol: str, query: str) -> list[dict]:
    """매매 관찰에 제공하는 목록에는 선정된 검토 후보만 포함한다."""
    return collect_news(market, symbol, query)["selected"]


def update_news_cache(path: Path, candidates: list[dict], *, selected_only=False) -> None:
    """최초 수신 시각을 유지한다. 반복 검색을 새 뉴스로 처리하지 않는다."""
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    if selected_only:
        # 이전 일반 기사 제거 후 현재 정책·유효 기간을 다시 검사한다.
        existing = [item for item in existing if item.get("selection_status") == "selected"]
        existing = filter_candidates(existing, load_filter_policy(), datetime.now(timezone.utc))["selected"]
        candidates = [item for item in candidates if item.get("selection_status") == "selected"]
    by_id = {item["candidate_id"]: item for item in existing}
    for candidate in candidates:
        if candidate["candidate_id"] not in by_id:
            by_id[candidate["candidate_id"]] = candidate
        elif selected_only:
            # 새 필터 설명을 반영해도 최초 발견 시각은 원래 값을 유지한다.
            by_id[candidate["candidate_id"]] = {**candidate, "first_seen_at": by_id[candidate["candidate_id"]]["first_seen_at"]}
    # 저장 용량 제한. 최근 최초 수신 기사만 유지하며 매매 사건은 이 파일과 별개다.
    rows = sorted(by_id.values(), key=lambda item: item["first_seen_at"])[-2000:]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_confirmed_events(path: Path, now: datetime) -> list[dict]:
    """검토한 사건 파일을 읽는다. 입력 오류를 빈 뉴스로 바꿔 숨기지 않는다.

    available_at은 본문 검토가 끝난 시각이다. 이후 실행에서만 사용할 수 있다.
    같은 사건의 정정은 같은 event_id를 사용해 더 늦은 available_at으로 추가한다.
    """
    if not path.exists():
        return []
    events = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(events, list):
        raise ValueError("확정 뉴스 파일은 JSON 배열이어야 합니다.")
    allowed_kinds = POSITIVE_EVENT_KINDS | NEGATIVE_EVENT_KINDS
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("확정 뉴스 항목은 JSON 객체여야 합니다.")
        if (event.get("market") not in {"KR", "US"} or not event.get("symbol")
                or not event.get("event_id") or event.get("kind") not in allowed_kinds
                or event.get("confirmed") is not True or event.get("source_verified") is not True
                or not event.get("evidence_url") or not event.get("review_note")):
            raise ValueError("확정 뉴스에 종목·사건 종류·근거 URL·검토 메모가 필요합니다.")
        if not isinstance(event.get("available_at"), str):
            raise ValueError("확정 뉴스 검토 시각에 시간대가 포함된 문자열이 필요합니다.")
        if parse_timestamp(event["available_at"]) > now:
            raise ValueError("확정 뉴스 검토 시각이 현재보다 미래입니다.")
    return events
