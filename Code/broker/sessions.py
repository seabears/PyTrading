"""휴장·조기 종료·서머타임을 반영하는 KRX/미국 정규장 달력.

exchange_calendars는 커뮤니티 달력으로 거래소의 실시간 장 상태가 아니다.
갑작스러운 휴장·거래 정지는 호가 신선도 검사로 추가 차단한다.
"""
from functools import lru_cache
from datetime import timedelta


@lru_cache(maxsize=4)
def calendar_for(market, year):
    try:
        import exchange_calendars
    except ImportError:
        raise ValueError("거래소 달력이 없습니다. python -m pip install -r Deployment/requirements.txt를 실행하세요.") from None
    name = "XKRX" if market == "KR" else "XNYS"
    return exchange_calendars.get_calendar(name, start=f"{year - 1}-01-01", end=f"{year + 1}-12-31")


def regular_session(market, now):
    """UTC 시각을 달력과 대조한다. 한국 종가 단일가 10분은 기존 전략처럼 제외한다."""
    if market not in {"KR", "US"}:
        raise ValueError("지원하지 않는 시장입니다.")
    calendar = calendar_for(market, now.year)
    first = (now - timedelta(days=1)).date().isoformat()
    last = (now + timedelta(days=1)).date().isoformat()
    for label, row in calendar.schedule.loc[first:last].iterrows():
        opening = row["open"].to_pydatetime()
        closing = row["close"].to_pydatetime()
        if market == "KR":
            closing -= timedelta(minutes=10)
        if opening <= now < closing:
            return {"start": opening, "end": closing, "id": market + ":" + label.date().isoformat()}
    return None
