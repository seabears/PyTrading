"""사용자의 현재 보유 목록을 Portfolio CSV에서 읽는다."""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


DEFAULT_HOLDINGS_PATH = Path(__file__).resolve().parents[3] / "Portfolio" / "portfolio_holdings.csv"
SYMBOL_ALIASES = {"SPACEX": "SPCX"}
DEFAULT_US_MARKETS = {
    "RBLX": "NYSE",
    "SPCX": "NASDAQ",
    "TSLA": "NASDAQ",
    "COIN": "NASDAQ",
    "T": "NYSE",
    "NVDA": "NASDAQ",
    "AMZN": "NASDAQ",
    "QCOM": "NASDAQ",
    "AVGO": "NASDAQ",
    "TEM": "NASDAQ",
    "IBM": "NYSE",
    "BTQ": "NASDAQ",
    "O": "NYSE",
    "GOOGL": "NASDAQ",
    "MSFT": "NASDAQ",
}
DEFAULT_INVESTMENT_STYLES = {
    "MSFT": "CORE",
    "GOOGL": "CORE",
    "AMZN": "CORE",
    "NVDA": "CORE",
    "AVGO": "CORE",
    "QCOM": "CORE",
    "RBLX": "TACTICAL",
    "SPCX": "TACTICAL",
    "TSLA": "TACTICAL",
    "COIN": "TACTICAL",
    "TEM": "TACTICAL",
    "BTQ": "TACTICAL",
    "T": "INCOME",
    "IBM": "INCOME",
    "O": "INCOME",
}
DEFAULT_TARGET_WEIGHTS = {
    "MSFT": 15.0,
    "GOOGL": 10.0,
    "AMZN": 8.0,
    "NVDA": 10.0,
    "AVGO": 7.0,
    "QCOM": 5.0,
    "RBLX": 4.0,
    "SPCX": 5.0,
    "TSLA": 6.0,
    "COIN": 4.0,
    "TEM": 4.0,
    "BTQ": 1.0,
    "T": 7.0,
    "IBM": 5.0,
    "O": 9.0,
}


class InvestmentStyle(str, Enum):
    CORE = "CORE"
    TACTICAL = "TACTICAL"
    INCOME = "INCOME"


@dataclass(frozen=True)
class Holding:
    """현재 보유 중인 한 종목."""

    symbol: str
    name: str
    market: str
    quantity: float
    average_price_usd: float
    purchase_amount_usd: float
    weight_percent: float
    investment_style: InvestmentStyle = InvestmentStyle.CORE
    target_weight_percent: float = 10.0
    maximum_weight_percent: float = 15.0


@dataclass(frozen=True)
class HoldingsPortfolio:
    """CSV에서 읽은 현재 보유 포트폴리오."""

    holdings: list[Holding]
    total_purchase_amount_usd: float

    @property
    def symbols(self) -> list[str]:
        return [holding.symbol for holding in self.holdings]


def load_holdings_csv(
    path: str | Path = DEFAULT_HOLDINGS_PATH,
) -> HoldingsPortfolio:
    """현재 보유 목록 CSV를 읽고 값의 일관성을 검증한다."""

    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"보유 목록 CSV 파일을 찾을 수 없습니다: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_headers = {
            "티커",
            "종목",
            "수량",
            "평균단가_USD",
            "매입금액_USD",
            "비중_pct",
        }
        missing_headers = required_headers - set(reader.fieldnames or [])
        if missing_headers:
            missing = ", ".join(sorted(missing_headers))
            raise ValueError(f"보유 목록 CSV에 필요한 열이 없습니다: {missing}")

        holdings: list[Holding] = []
        seen_symbols: set[str] = set()
        declared_total: float | None = None

        for line_number, row in enumerate(reader, start=2):
            symbol = (row["티커"] or "").strip().upper()
            if symbol == "합계":
                declared_total = _parse_number(
                    row["매입금액_USD"], "매입금액_USD", line_number, allow_zero=True
                )
                continue
            if not symbol:
                continue
            symbol = SYMBOL_ALIASES.get(symbol, symbol)
            if symbol in seen_symbols:
                raise ValueError(f"{line_number}행에 중복 티커가 있습니다: {symbol}")

            name = (row["종목"] or "").strip()
            if not name:
                raise ValueError(f"{line_number}행의 종목명이 비어 있습니다.")
            market = (row.get("시장") or DEFAULT_US_MARKETS.get(symbol) or "").strip().upper()
            if market not in {"NASDAQ", "NYSE", "AMEX"}:
                raise ValueError(
                    f"{line_number}행의 시장을 확인할 수 없습니다. CSV에 NASDAQ, NYSE, "
                    f"AMEX 중 하나를 입력해 주세요: {symbol}"
                )

            quantity = _parse_number(row["수량"], "수량", line_number)
            average_price = _parse_number(row["평균단가_USD"], "평균단가_USD", line_number)
            purchase_amount = _parse_number(row["매입금액_USD"], "매입금액_USD", line_number)
            weight = _parse_number(
                row["비중_pct"], "비중_pct", line_number, allow_zero=True
            )
            if weight > 100:
                raise ValueError(f"{line_number}행의 비중_pct는 100 이하여야 합니다.")
            style_text = (
                row.get("투자유형") or DEFAULT_INVESTMENT_STYLES.get(symbol) or "CORE"
            ).strip().upper()
            try:
                investment_style = InvestmentStyle(style_text)
            except ValueError as exc:
                raise ValueError(
                    f"{line_number}행의 투자유형은 CORE, TACTICAL, INCOME 중 "
                    f"하나여야 합니다: {style_text!r}"
                ) from exc
            target_weight = _parse_optional_number(
                row.get("목표비중_pct"),
                DEFAULT_TARGET_WEIGHTS.get(symbol, 10.0),
                "목표비중_pct",
                line_number,
            )
            default_maximum = (
                25.0
                if symbol == "MSFT"
                else 8.0
                if investment_style == InvestmentStyle.TACTICAL
                else 15.0
            )
            maximum_weight = _parse_optional_number(
                row.get("최대비중_pct"),
                default_maximum,
                "최대비중_pct",
                line_number,
            )
            if not 0 < target_weight <= maximum_weight <= 100:
                raise ValueError(
                    f"{line_number}행은 0 < 목표비중_pct <= 최대비중_pct <= 100을 "
                    f"만족해야 합니다."
                )

            expected_amount = round(quantity * average_price, 2)
            if not math.isclose(purchase_amount, expected_amount, abs_tol=0.01):
                raise ValueError(
                    f"{line_number}행의 매입금액_USD가 수량 x 평균단가와 다릅니다: "
                    f"{purchase_amount:.2f} != {expected_amount:.2f}"
                )

            holdings.append(
                Holding(
                    symbol=symbol,
                    name=name,
                    market=market,
                    quantity=quantity,
                    average_price_usd=average_price,
                    purchase_amount_usd=purchase_amount,
                    weight_percent=weight,
                    investment_style=investment_style,
                    target_weight_percent=target_weight,
                    maximum_weight_percent=maximum_weight,
                )
            )
            seen_symbols.add(symbol)

    if not holdings:
        raise ValueError("보유 목록 CSV에 종목이 없습니다.")

    total = round(sum(holding.purchase_amount_usd for holding in holdings), 2)
    if declared_total is not None and not math.isclose(total, declared_total, abs_tol=0.01):
        raise ValueError(
            f"합계 행의 매입금액_USD가 종목 합계와 다릅니다: "
            f"{declared_total:.2f} != {total:.2f}"
        )

    return HoldingsPortfolio(holdings=holdings, total_purchase_amount_usd=total)


def _parse_number(
    raw_value: str | None,
    column: str,
    line_number: int,
    *,
    allow_zero: bool = False,
) -> float:
    value_text = (raw_value or "").strip().replace(",", "")
    try:
        value = float(value_text)
    except ValueError as exc:
        raise ValueError(
            f"{line_number}행의 {column} 값이 숫자가 아닙니다: {value_text!r}"
        ) from exc

    minimum_is_valid = value >= 0 if allow_zero else value > 0
    if not math.isfinite(value) or not minimum_is_valid:
        comparison = "0 이상" if allow_zero else "0보다 큰"
        raise ValueError(f"{line_number}행의 {column} 값은 {comparison} 유한수여야 합니다.")
    return value


def _parse_optional_number(
    raw_value: str | None,
    default: float,
    column: str,
    line_number: int,
) -> float:
    if raw_value is None or not raw_value.strip():
        return default
    return _parse_number(raw_value, column, line_number)
