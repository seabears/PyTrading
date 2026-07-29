"""
PyTrading 프로그램의 메인 진입점.

실행:
    python main.py

명령행 인자는 사용하지 않는다. 프로그램을 실행한 다음 화면의 설명을 보고
증권사, 조회 종류, 시장, 종목을 차례대로 선택한다.
"""
from __future__ import annotations

import sys

from pytrading.stocks import StockProvider, create_stock_client


def format_number(value, digits: int = 2) -> str:
    """숫자에 천 단위 쉼표를 넣고 값이 없으면 '-'로 표시한다."""

    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.{digits}f}"


def render_quotes(quotes) -> str:
    """현재가 조회 결과를 터미널 표로 만든다."""

    lines = [
        f"{'PROVIDER':<8} {'SYMBOL':<10} {'MARKET':<8} {'PRICE':>12} {'CUR':<4} "
        f"{'CHG%':>8} {'VOLUME':>14} {'TIME':<25} NAME"
    ]
    lines.append("-" * 112)
    for quote in quotes:
        lines.append(
            f"{quote.provider.value:<8} {quote.symbol:<10} {quote.market:<8} "
            f"{format_number(quote.price):>12} {quote.currency:<4} "
            f"{format_number(quote.change_rate):>8} {format_number(quote.volume, 0):>14} "
            f"{quote.timestamp:<25} {quote.name}"
        )
    return "\n".join(lines)


def render_history(history) -> str:
    """과거 시세 조회 결과를 터미널 표로 만든다."""

    lines = [f"{history.provider.value} {history.symbol} {history.market} {history.timeframe}", ""]
    lines.append(f"{'TIME':<25} {'OPEN':>12} {'HIGH':>12} {'LOW':>12} {'CLOSE':>12} {'VOLUME':>14}")
    lines.append("-" * 94)
    for candle in history.candles:
        lines.append(
            f"{candle.time:<25} {format_number(candle.open):>12} {format_number(candle.high):>12} "
            f"{format_number(candle.low):>12} {format_number(candle.close):>12} "
            f"{format_number(candle.volume, 0):>14}"
        )
    return "\n".join(lines)


def ask_choice(prompt: str, choices: dict[str, str]) -> str:
    """
    사용자가 choices에 있는 값을 입력할 때까지 반복해서 질문한다.

    choices는 화면 입력값과 실제 코드에서 사용할 값을 연결한다.
    예: {"1": "kis", "kis": "kis"}
    """

    while True:
        answer = input(prompt).strip().lower()
        if answer in choices:
            return choices[answer]
        print("올바른 번호 또는 이름을 입력해 주세요.\n")


def ask_symbols() -> list[str]:
    """공백이나 쉼표로 입력한 종목 코드를 대문자 목록으로 변환한다."""

    while True:
        raw_symbols = input("종목 코드 입력 (예: AAPL 또는 AAPL MSFT): ").strip()
        symbols = [symbol.upper() for symbol in raw_symbols.replace(",", " ").split()]
        if symbols:
            return symbols
        print("종목 코드를 한 개 이상 입력해 주세요.\n")


def ask_count() -> int:
    """Toss 과거 시세 개수를 1~200 범위로 입력받는다."""

    while True:
        raw_count = input("가져올 봉 개수 (1~200, 기본 100): ").strip()
        if not raw_count:
            return 100
        try:
            count = int(raw_count)
        except ValueError:
            print("숫자로 입력해 주세요.\n")
            continue
        if 1 <= count <= 200:
            return count
        print("1부터 200 사이의 숫자를 입력해 주세요.\n")


def choose_provider() -> str:
    """사용할 증권사 API를 선택한다."""

    print("[증권사 선택]")
    print("1. KIS  - 한국투자증권")
    print("2. Toss - 토스증권\n")
    return ask_choice(
        "선택 (1/2): ",
        {
            "1": StockProvider.KIS.value,
            "kis": StockProvider.KIS.value,
            "2": StockProvider.TOSS.value,
            "toss": StockProvider.TOSS.value,
        },
    )


def choose_action() -> str:
    """현재가 또는 과거 시세 조회를 선택한다."""

    print("\n[기능 선택]")
    print("1. 현재가 조회")
    print("2. 과거 시세 조회\n")
    return ask_choice(
        "선택 (1/2): ",
        {
            "1": "quote",
            "quote": "quote",
            "2": "history",
            "history": "history",
        },
    )


def choose_market(provider: str) -> str:
    """선택한 증권사에 맞는 시장을 입력받는다."""

    print("\n[시장 선택]")
    if provider == StockProvider.KIS.value:
        print("1. NASDAQ")
        print("2. NYSE")
        print("3. AMEX\n")
        return ask_choice(
            "선택 (1/2/3, 기본 1): ",
            {
                "": "NASDAQ",
                "1": "NASDAQ",
                "nasdaq": "NASDAQ",
                "2": "NYSE",
                "nyse": "NYSE",
                "3": "AMEX",
                "amex": "AMEX",
            },
        )

    print("1. US - 미국 주식")
    print("2. KR - 한국 주식\n")
    return ask_choice(
        "선택 (1/2, 기본 1): ",
        {
            "": "US",
            "1": "US",
            "us": "US",
            "2": "KR",
            "kr": "KR",
        },
    )


def run_quote(provider: str, market: str, symbols: list[str]) -> None:
    """선택한 증권사에서 현재가를 조회하고 표를 출력한다."""

    client = create_stock_client(provider)
    quotes = client.quotes(symbols, market=market)
    print("\n[현재가 조회 결과]\n")
    print(render_quotes(quotes))


def run_history(provider: str, market: str, symbols: list[str]) -> None:
    """선택한 증권사에서 과거 시세를 조회하고 표를 출력한다."""

    client = create_stock_client(provider)
    histories = []

    if provider == StockProvider.KIS.value:
        print("\nKIS 과거 시세는 현재 일봉(1d)을 지원합니다.")
        start = input("시작일 (YYYYMMDD, 생략 가능): ").strip()
        end = input("종료일 (YYYYMMDD, 생략 가능): ").strip()
        for symbol in symbols:
            histories.append(
                client.history(
                    symbol,
                    market=market,
                    timeframe="1d",
                    start=start,
                    end=end,
                )
            )
    else:
        print("\nToss 봉 간격을 선택하세요.")
        print("1. 1분봉")
        print("2. 일봉\n")
        timeframe = ask_choice(
            "선택 (1/2, 기본 2): ",
            {"": "1d", "1": "1m", "1m": "1m", "2": "1d", "1d": "1d"},
        )
        count = ask_count()
        for symbol in symbols:
            histories.append(
                client.history(
                    symbol,
                    market=market,
                    timeframe=timeframe,
                    count=count,
                )
            )

    print("\n[과거 시세 조회 결과]\n")
    print("\n\n".join(render_history(history) for history in histories))


def main() -> int:
    """화면 안내에 따라 필요한 값을 입력받아 주식 정보를 조회한다."""

    print("=" * 56)
    print(" PyTrading - 주식 자동매매 시스템")
    print("=" * 56)
    print("현재는 KIS와 Toss의 현재가 및 과거 시세를 조회할 수 있습니다.")
    print("아래 설명에 따라 번호를 선택하세요.\n")

    try:
        provider = choose_provider()
        action = choose_action()
        market = choose_market(provider)
        symbols = ask_symbols()

        if action == "quote":
            run_quote(provider, market, symbols)
        else:
            run_history(provider, market, symbols)
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\n프로그램을 종료합니다.")
        return 130
    except Exception as exc:
        # API 오류는 긴 traceback 대신 사용자가 읽기 쉬운 한 줄로 표시한다.
        print(f"\n오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
