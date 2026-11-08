"""뉴스만 실제 수집해 확인한다. 토스 인증·매매 판단·모의 계좌 변경은 없다."""
import json

from app.runtime import load_run_settings
from news.collector import NEWS_QUERIES, collect_news
from paths import RESULTS_ROOT


def main():
    settings = load_run_settings()
    queries = dict(NEWS_QUERIES)
    if settings["news_queries"]:
        queries.update(json.loads(settings["news_queries"].read_text(encoding="utf-8-sig")))
    collected = []
    reports = []
    failed = False
    for market, symbol in settings["symbols"]:
        query = queries.get(market + ":" + symbol)
        if not query:
            print(f"{market}:{symbol}: 검색어 없음")
            failed = True
            continue
        try:
            report = collect_news(market, symbol, query)
            reports.append(report)
            candidates = report["selected"]
            collected.extend(candidates)
            print(f"{market}:{symbol}: 수집 {report['fetched_count']}건 → 검토 후보 {len(candidates)}건 / 제외 {len(report['excluded'])}건")
            if not candidates:
                print("  현재 조건을 통과한 기사가 없습니다. 결과를 채우기 위해 기준을 낮추지 않습니다.")
            for candidate in candidates[:5]:
                print(f"  [{candidate['publisher']}] {candidate['title']}")
                print(f"    사건: {', '.join(candidate['impact_events'])}")
                print(f"    선정 이유: {'; '.join(candidate['selection_reasons'])}")
                print("    상태: 원문 검토 전 후보. 사실·주가 방향 미확정.")
            for candidate in report["excluded"][:3]:
                print(f"  제외: {candidate['title']}")
                print(f"    이유: {'; '.join(candidate['selection_reasons'])}")
        except (ValueError, OSError) as error:
            print(f"{market}:{symbol}: {error}")
            failed = True
    output = RESULTS_ROOT / "live-news.json"
    # 테스트 결과는 매번 현재 선정 목록으로 교체한다. 제외 기사는 설명 보고서에만 저장한다.
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(collected, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = output.with_name("live-news-report.json")
    report_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"뉴스 확인 결과: {output}")
    print(f"선정·제외 이유와 전체 링크: {report_path}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
