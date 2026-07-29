"""
Small shared helpers for stock providers.
"""
from __future__ import annotations

from typing import Any


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(str(value).replace(",", ""))


def to_int(value: Any) -> int | None:
    number = to_float(value)
    return None if number is None else int(number)


def change_rate(price: float | None, previous_close: float | None) -> float | None:
    if price is None or not previous_close:
        return None
    return (price - previous_close) / previous_close * 100