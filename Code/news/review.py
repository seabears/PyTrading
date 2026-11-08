"""뉴스 후보 목록 보기와 사람이 검토한 사건 등록.

제목 분류 결과를 자동 승인하지 않는다. 원문을 직접 확인한 뒤 근거 URL·메모를 입력한다.
매매 근거 시각은 기사 발행 시각이 아니라 지금 등록하는 시각으로 기록한다.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from strategy.engine import NEGATIVE_EVENT_KINDS, POSITIVE_EVENT_KINDS
from news.collector import load_confirmed_events
from app.runtime import load_run_settings


def approve_candidate(candidates_path: Path, events_path: Path, candidate_id: str,
                      kind: str, evidence_url: str, review_note: str,
                      event_id: str | None = None) -> dict:
    """검토한 원문 근거를 사건 파일에 추가한다. 출처의 실제 검증은 사용자가 수행한다."""
    if kind not in POSITIVE_EVENT_KINDS | NEGATIVE_EVENT_KINDS:
        raise ValueError("지원하지 않는 사건 종류입니다.")
    parsed_url = urlparse(evidence_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc or not review_note.strip():
        raise ValueError("원문 근거 URL과 검토 메모가 필요합니다.")
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    matches = [row for row in candidates if row["candidate_id"] == candidate_id]
    if len(matches) != 1:
        raise ValueError("후보 ID를 찾을 수 없습니다.")
    candidate = matches[0]
    now = datetime.now(timezone.utc)
    events = load_confirmed_events(events_path, now)
    # 한 사건을 다룬 다른 기사에는 같은 event_id를 지정해 중복 진입 근거를 막는다.
    canonical_id = event_id or candidate_id
    event = {"market": candidate["market"], "symbol": candidate["symbol"],
             "event_id": canonical_id, "candidate_id": candidate_id,
             "kind": kind, "available_at": now.isoformat(),
             "confirmed": True, "source_verified": True,
             "evidence_url": evidence_url, "review_note": review_note.strip()}
    # 같은 후보·분류·근거를 반복 등록해서 뉴스 유효기간을 연장하지 않는다.
    for previous in reversed(events):
        if (previous["event_id"] == canonical_id and previous["market"] == event["market"]
                and previous["symbol"] == event["symbol"]):
            if all(previous.get(field) == event[field] for field in
                   ("candidate_id", "kind", "evidence_url", "review_note")):
                return previous
            break
    events.append(event)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = events_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(events_path)
    return event


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    try:
        settings = load_run_settings()
    except (ValueError, TypeError, OSError):
        parser.exit(1, "../Config/settings.json의 내용과 경로를 확인하세요.\n")
    parser.add_argument("--candidates-file", type=Path, default=settings["output_dir"] / "news-candidates.json")
    parser.add_argument("--events-file", type=Path, default=settings["events_file"])
    parser.add_argument("--candidate-id", help="미지정이면 최근 후보 20개 표시")
    parser.add_argument("--kind", choices=sorted(POSITIVE_EVENT_KINDS | NEGATIVE_EVENT_KINDS))
    parser.add_argument("--evidence-url", help="회사 발표·공시 등 직접 검토한 원문 주소")
    parser.add_argument("--note", help="확정 여부·회사 일치·사건 중요도를 확인한 근거")
    parser.add_argument("--event-id", help="같은 사건의 다른 기사·정정에 사용하는 공통 ID")
    args = parser.parse_args()
    try:
        if not args.candidate_id:
            candidates = json.loads(args.candidates_file.read_text(encoding="utf-8"))
            for row in candidates[-20:]:
                print(f"{row['candidate_id']} {row['market']}:{row['symbol']} {row['title']}")
                print(f"  후보 분류: {', '.join(row['candidate_kinds']) or '미분류'} / {row['url']}")
            return
        if not args.kind or not args.evidence_url or not args.note:
            parser.error("등록하려면 --kind, --evidence-url, --note를 모두 입력하세요.")
        event = approve_candidate(args.candidates_file, args.events_file, args.candidate_id,
                                  args.kind, args.evidence_url, args.note, args.event_id)
        print(f"검토 사건 저장: {event['event_id']} / {event['available_at']}")
    except (ValueError, KeyError, TypeError, OSError):
        parser.exit(1, "뉴스 후보·사건 파일과 입력값을 확인하세요.\n")


if __name__ == "__main__":
    main()
