"""표준 라이브러리만 사용하는 OHLCV CSV 로더."""
from __future__ import annotations

import csv
from pathlib import Path

from pytrading.stocks.models import StockCandle


REQUIRED_COLUMNS = {"date", "open", "high", "low", "close"}


def load_candles_from_csv(path: str | Path) -> list[StockCandle]:
    """
    date, open, high, low, close, volume 열이 있는 CSV를 읽는다.

    열 이름의 대소문자는 구분하지 않으며 volume은 생략할 수 있다.
    날짜 형식은 정렬 가능한 YYYY-MM-DD 또는 YYYYMMDD 사용을 권장한다.
    """

    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError("CSV 헤더가 없습니다.")

        columns = {name.strip().lower(): name for name in reader.fieldnames}
        missing = REQUIRED_COLUMNS - columns.keys()
        if missing:
            raise ValueError(f"CSV 필수 열이 없습니다: {', '.join(sorted(missing))}")

        candles: list[StockCandle] = []
        for line_number, row in enumerate(reader, start=2):
            try:
                candles.append(
                    StockCandle(
                        time=row[columns["date"]].strip(),
                        open=_to_number(row[columns["open"]]),
                        high=_to_number(row[columns["high"]]),
                        low=_to_number(row[columns["low"]]),
                        close=_to_number(row[columns["close"]]),
                        volume=int(_to_number(row[columns["volume"]])) if "volume" in columns else 0,
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"CSV {line_number}행의 숫자 형식이 잘못되었습니다.") from exc

    if not candles:
        raise ValueError("CSV에 가격 데이터가 없습니다.")

    candles.sort(key=lambda candle: candle.time)
    _validate_candles(candles)
    return candles


def save_candles_to_csv(candles: list[StockCandle], path: str | Path) -> None:
    """KIS에서 받은 데이터를 재사용할 수 있도록 표준 OHLCV CSV로 저장한다."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        for candle in candles:
            writer.writerow(
                [candle.time, candle.open, candle.high, candle.low, candle.close, candle.volume]
            )


def _to_number(value: str | None) -> float:
    if value is None or not value.strip():
        raise ValueError("빈 숫자")
    return float(value.replace(",", "").strip())


def _validate_candles(candles: list[StockCandle]) -> None:
    """백테스트 결과를 왜곡할 수 있는 기본 데이터 오류를 차단한다."""

    seen_dates: set[str] = set()
    for candle in candles:
        if not candle.time:
            raise ValueError("날짜가 비어 있는 행이 있습니다.")
        if candle.time in seen_dates:
            raise ValueError(f"중복 날짜가 있습니다: {candle.time}")
        seen_dates.add(candle.time)

        if min(candle.open, candle.high, candle.low, candle.close) <= 0:
            raise ValueError(f"가격은 0보다 커야 합니다: {candle.time}")
        if candle.high < max(candle.open, candle.close) or candle.low > min(candle.open, candle.close):
            raise ValueError(f"고가/저가 범위가 잘못되었습니다: {candle.time}")
