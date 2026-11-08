"""예상치 공급자의 원본을 관측 자료로 정리한다. 검증된 매매 사건으로 자동 승격하지 않는다.

공급자 date는 회계기간 종료일이다. 실제 수신 시각은 별도 received_at만 사용한다.
현재 공개 데모에는 GAAP/조정 기준·통화·정확한 발표 시각이 없어 observation_only다.
"""
import csv
import io
import math
from datetime import date

from strategy.engine import parse_timestamp


def numeric(value, *, positive=False):
    if value is None or isinstance(value, bool) or str(value).strip().casefold() in {"", "none", "null", "nan", "n/a"}:
        raise ValueError("예상치 숫자가 없습니다.")
    number = float(value)
    if not math.isfinite(number) or positive and number <= 0:
        raise ValueError("예상치 숫자가 유효하지 않습니다.")
    return number


def alpha_observations(payload, received_at, *, expected_symbol="IBM", demo=True):
    """발표 전 예상치 관측을 쌓을 형식만 만든다. 과거 수정 이력을 과거 수신으로 바꾸지 않는다."""
    received = parse_timestamp(received_at)
    if not isinstance(payload, dict) or payload.get("symbol") != expected_symbol or not isinstance(payload.get("estimates"), list):
        raise ValueError("예상치 응답이 아니거나 요청 종목과 다릅니다.")
    observations, excluded = [], []
    seen = set()
    for row in payload["estimates"]:
        if row.get("horizon") != "fiscal quarter":
            excluded.append({"date": row.get("date"), "reason": "not_standalone_quarter_horizon"})
            continue
        ending = date.fromisoformat(row["date"])
        for metric, field in (("eps", "eps_estimate_average"), ("revenue", "revenue_estimate_average")):
            try:
                value = numeric(row.get(field), positive=metric == "revenue")
            except (ValueError, TypeError, OverflowError):
                excluded.append({"date": row["date"], "metric": metric, "reason": "missing_or_invalid_estimate"})
                continue
            identity = (row["date"], metric)
            if identity in seen:
                raise ValueError("같은 기간·지표의 중복 예상치를 임의 선택하지 않습니다.")
            seen.add(identity)
            observations.append({"provider": "alpha_vantage", "symbol": expected_symbol, "metric": metric,
                "period_start": None, "period_end": ending.isoformat(), "date_role": "fiscal_period_end",
                "basis": None, "unit": None, "currency": None, "value": value,
                "observed_at": received_at, "source_url": "https://www.alphavantage.co/query?function=EARNINGS_ESTIMATES&symbol=" + expected_symbol,
                "future_period_candidate": ending > received.date(), "report_at": None,
                "access_mode": "public_demo" if demo else "personal_key_unvalidated",
                "status": "observation_only", "trading_eligible": False,
                "eligibility_reasons": ["accounting_basis_unknown", "unit_currency_unknown", "period_start_unknown",
                                        "release_time_unknown", "demo_not_production" if demo else "provider_not_approved"],
                "analyst_count": row.get("eps_estimate_analyst_count" if metric == "eps" else "revenue_estimate_analyst_count")})
    return {"observed_at": received_at, "observations": observations, "excluded": excluded}


def alpha_calendar(raw):
    """헤더만 온 응답은 연결 성공·자료 0건으로 기록한다. 발표가 없다고 결론내리지 않는다."""
    text = raw.decode("utf-8-sig")
    if text.lstrip().startswith(("{", "[")):
        raise ValueError("달력 CSV 대신 API 안내·오류 응답을 받았습니다.")
    reader = csv.DictReader(io.StringIO(text))
    required = {"symbol", "reportDate", "fiscalDateEnding", "estimate", "currency"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("실적 달력의 필수 열이 없습니다.")
    rows = list(reader)
    return {"rows": rows, "count": len(rows), "status": "data_received" if rows else "valid_header_but_no_rows",
            "empty_is_not_no_upcoming_earnings": True}
