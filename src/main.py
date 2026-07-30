"""
PyTrading 프로그램의 메인 진입점.

실행:
    python src/main.py

명령행 인자는 사용하지 않는다. 프로그램을 실행한 다음 화면 안내에 따라
조회 기능, 시장, 종목, 전략 설정을 차례대로 선택한다.
"""
from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
import math
from pathlib import Path
import re

from pytrading.backtest import (
    BacktestConfig,
    BacktestEngine,
    PortfolioBacktestConfig,
    PortfolioBacktestEngine,
)
from pytrading.data import (
    load_candles_from_csv,
    load_candles_from_kis,
    load_portfolio_from_kis,
    save_candles_to_csv,
)
from pytrading.reporting import (
    format_backtest_result,
    format_portfolio_result,
    save_portfolio_trades_csv,
    save_trades_csv,
)
from pytrading.stocks import StockProvider, create_stock_client
from pytrading.stocks.models import StockCandle
from pytrading.strategies import MovingAverageCrossStrategy


@dataclass(frozen=True)
class BacktestInputs:
    """화면에서 입력받은 백테스트 설정."""

    short_window: int
    long_window: int
    initial_cash: float
    commission_rate: float
    slippage_rate: float
    trades_csv: str


@dataclass(frozen=True)
class PortfolioInputs:
    """화면에서 입력받은 포트폴리오 설정과 출력 경로."""

    config: PortfolioBacktestConfig
    trades_csv: str
    refresh_cache: bool


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
    lines.append(
        f"{'TIME':<25} {'OPEN':>12} {'HIGH':>12} {'LOW':>12} "
        f"{'CLOSE':>12} {'VOLUME':>14}"
    )
    lines.append("-" * 94)
    for candle in history.candles:
        lines.append(
            f"{candle.time:<25} {format_number(candle.open):>12} "
            f"{format_number(candle.high):>12} {format_number(candle.low):>12} "
            f"{format_number(candle.close):>12} {format_number(candle.volume, 0):>14}"
        )
    return "\n".join(lines)


def ask_choice(prompt: str, choices: dict[str, str]) -> str:
    """목록에 있는 값이 입력될 때까지 질문을 반복한다."""

    while True:
        answer = input(prompt).strip().lower()
        if answer in choices:
            return choices[answer]
        print("올바른 번호 또는 이름을 입력해 주세요.\n")


def ask_text(prompt: str) -> str:
    """빈 문자열이 아닌 값을 입력받는다."""

    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("값을 입력해 주세요.\n")


def ask_integer(
    prompt: str,
    default: int,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    """기본값과 최솟값이 있는 정수를 입력받는다."""

    while True:
        raw_value = input(prompt).strip()
        if not raw_value:
            value = default
        else:
            try:
                value = int(raw_value)
            except ValueError:
                print("정수로 입력해 주세요.\n")
                continue
        if value < minimum:
            print(f"{minimum} 이상의 숫자를 입력해 주세요.\n")
            continue
        if maximum is not None and value > maximum:
            print(f"{maximum} 이하의 숫자를 입력해 주세요.\n")
            continue
        return value


def ask_float(
    prompt: str,
    default: float,
    minimum: float = 0.0,
    maximum: float | None = None,
) -> float:
    """유한한 숫자와 허용 범위를 확인하며 실수를 입력받는다."""

    while True:
        raw_value = input(prompt).strip().replace(",", "")
        if not raw_value:
            value = default
        else:
            try:
                value = float(raw_value)
            except ValueError:
                print("숫자로 입력해 주세요.\n")
                continue
        if not math.isfinite(value):
            print("유한한 숫자로 입력해 주세요.\n")
            continue
        if value < minimum:
            print(f"{minimum} 이상의 숫자를 입력해 주세요.\n")
            continue
        if maximum is not None and value > maximum:
            print(f"{maximum} 이하의 숫자를 입력해 주세요.\n")
            continue
        return value


def ask_date(prompt: str, *, earliest: date | None = None, latest: date | None = None) -> str:
    """YYYYMMDD 형식과 허용 날짜 범위를 확인한다."""

    while True:
        raw_value = input(prompt).strip()
        try:
            parsed = datetime.strptime(raw_value, "%Y%m%d").date()
        except ValueError:
            print("날짜를 YYYYMMDD 형식으로 입력해 주세요. 예: 20260101\n")
            continue
        if earliest is not None and parsed < earliest:
            print(f"{earliest:%Y%m%d} 이후 날짜를 입력해 주세요.\n")
            continue
        if latest is not None and parsed > latest:
            print(f"{latest:%Y%m%d} 이전 날짜를 입력해 주세요.\n")
            continue
        return raw_value


def ask_date_range() -> tuple[str, str]:
    """시작일과 종료일의 형식 및 선후 관계를 확인한다."""

    today = date.today()
    start = ask_date("조회 시작일 (YYYYMMDD): ", latest=today)
    start_date = datetime.strptime(start, "%Y%m%d").date()
    end = ask_date("조회 종료일 (YYYYMMDD): ", earliest=start_date, latest=today)
    return start, end


def ask_optional_csv_path(prompt: str) -> str:
    """생략 가능 CSV 저장 경로의 확장자와 기본 문자를 확인한다."""

    while True:
        value = input(prompt).strip()
        if not value:
            return ""
        if any(character in value for character in '<>"|?*'):
            print("파일 경로에 사용할 수 없는 문자가 있습니다.\n")
            continue
        if Path(value).suffix.lower() != ".csv":
            print("저장 파일은 .csv 확장자로 입력해 주세요.\n")
            continue
        return value


def ask_symbols() -> list[str]:
    """공백이나 쉼표로 입력한 종목 코드를 대문자 목록으로 변환한다."""

    while True:
        raw_symbols = input("종목 코드 입력 (예: AAPL 또는 AAPL MSFT): ").strip()
        symbols = [symbol.upper() for symbol in raw_symbols.replace(",", " ").split()]
        if symbols and all(re.fullmatch(r"[A-Z0-9.-]+", symbol) for symbol in symbols):
            return symbols
        print("종목 코드는 영문, 숫자, 마침표, 하이픈만 사용해 주세요.\n")


def ask_count() -> int:
    """Toss 과거 시세 개수를 1~200 범위로 입력받는다."""

    return ask_integer("가져올 봉 개수 (1~200, 기본 100): ", default=100, maximum=200)


def choose_main_action() -> str:
    """프로그램에서 실행할 기능을 선택한다."""

    print("[기능 선택]")
    print("1. 현재가 조회")
    print("2. 과거 시세 조회")
    print("3. KIS 실제 과거 데이터 백테스트")
    print("4. CSV 파일 백테스트")
    print("5. KIS 다중 종목 포트폴리오 백테스트")
    print("0. 종료\n")
    return ask_choice(
        "선택 (0~5): ",
        {
            "0": "exit",
            "1": "quote",
            "2": "history",
            "3": "kis_backtest",
            "4": "csv_backtest",
            "5": "portfolio_backtest",
        },
    )


def choose_provider() -> str:
    """현재가·과거 시세 조회에 사용할 증권사를 선택한다."""

    print("\n[증권사 선택]")
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


def choose_market(provider: str, *, include_korea: bool = False) -> str:
    """선택한 증권사와 기능에 맞는 시장을 입력받는다."""

    print("\n[시장 선택]")
    if provider == StockProvider.KIS.value:
        if include_korea:
            print("1. KOREA - 한국 주식")
            print("2. NASDAQ")
            print("3. NYSE")
            print("4. AMEX\n")
            return ask_choice(
                "선택 (1~4, 기본 1): ",
                {
                    "": "KOREA",
                    "1": "KOREA",
                    "korea": "KOREA",
                    "kr": "KOREA",
                    "2": "NASDAQ",
                    "nasdaq": "NASDAQ",
                    "3": "NYSE",
                    "nyse": "NYSE",
                    "4": "AMEX",
                    "amex": "AMEX",
                },
            )

        print("1. NASDAQ")
        print("2. NYSE")
        print("3. AMEX\n")
        return ask_choice(
            "선택 (1~3, 기본 1): ",
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
        {"": "US", "1": "US", "us": "US", "2": "KR", "kr": "KR"},
    )


def choose_kis_backtest_market(symbol: str) -> str:
    """
    종목 코드 형식에 맞춰 KIS 백테스트 시장을 선택한다.

    국내 종목은 6자리 숫자이므로 KOREA를 자동 적용한다. 영문자가 포함된
    해외 종목에는 국내 시장을 보여주지 않아 잘못된 조합을 사전에 막는다.
    """

    if symbol.isdigit():
        if len(symbol) != 6:
            raise ValueError("국내주식 종목 코드는 6자리 숫자여야 합니다. 예: 005930")
        print("시장 자동 선택: KOREA - 한국 주식")
        return "KOREA"

    print("\n[해외 시장 선택]")
    print("1. NASDAQ")
    print("2. NYSE")
    print("3. AMEX\n")
    return ask_choice(
        "선택 (1~3, 기본 1): ",
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


def ask_kis_backtest_symbol() -> str:
    """지원하는 국내·해외 종목 코드가 입력될 때까지 다시 질문한다."""

    while True:
        symbol = ask_text("종목 코드 (예: 005930 또는 AAPL): ").upper()
        if not re.fullmatch(r"[A-Z0-9.-]+", symbol):
            print("종목 코드는 영문, 숫자, 마침표, 하이픈만 사용해 주세요.\n")
            continue
        if not symbol.isdigit() or len(symbol) == 6:
            return symbol
        print("국내주식 종목 코드는 6자리 숫자로 입력해 주세요. 예: 005930\n")


def ask_portfolio_symbols() -> list[str]:
    """같은 시장에 속한 중복 없는 종목 코드를 두 개 이상 입력받는다."""

    while True:
        symbols = list(dict.fromkeys(ask_symbols()))
        if len(symbols) < 2:
            print("포트폴리오에는 서로 다른 종목을 최소 2개 입력해 주세요.\n")
            continue

        domestic_flags = [symbol.isdigit() and len(symbol) == 6 for symbol in symbols]
        invalid_numeric = [symbol for symbol in symbols if symbol.isdigit() and len(symbol) != 6]
        if invalid_numeric:
            print(
                "국내주식 종목 코드는 6자리 숫자여야 합니다: "
                f"{', '.join(invalid_numeric)}\n"
            )
            continue
        if any(domestic_flags) and not all(domestic_flags):
            print("국내주식과 해외주식은 한 포트폴리오에 섞을 수 없습니다.\n")
            continue
        return symbols


def ask_portfolio_date_range() -> tuple[str, str]:
    """CAGR 검증을 위해 최소 1년 이상의 조회 기간을 입력받는다."""

    while True:
        start, end = ask_date_range()
        start_date = datetime.strptime(start, "%Y%m%d").date()
        end_date = datetime.strptime(end, "%Y%m%d").date()
        if (end_date - start_date).days >= 365:
            return start, end
        print("연복리수익률 검증을 위해 조회 기간을 최소 1년 이상으로 입력해 주세요.\n")


def ask_backtest_inputs() -> BacktestInputs:
    """이동평균 기간, 투자금, 거래 비용을 화면에서 입력받는다."""

    print("\n[백테스트 설정]")
    short_window = ask_integer("단기 이동평균 기간 (기본 5): ", default=5)
    long_window = ask_integer(
        "장기 이동평균 기간 (기본 20): ",
        default=max(20, short_window + 1),
        minimum=short_window + 1,
    )
    initial_cash = ask_float("초기 자금 (기본 10,000,000): ", default=10_000_000, minimum=1)
    commission_percent = ask_float(
        "수수료율 % (기본 0.015): ", default=0.015, maximum=100
    )
    slippage_percent = ask_float(
        "슬리피지율 % (기본 0.05): ", default=0.05, maximum=100
    )
    trades_csv = ask_optional_csv_path("거래 내역 저장 경로 (생략 가능): ")
    return BacktestInputs(
        short_window=short_window,
        long_window=long_window,
        initial_cash=initial_cash,
        commission_rate=commission_percent / 100.0,
        slippage_rate=slippage_percent / 100.0,
        trades_csv=trades_csv,
    )


def ask_portfolio_inputs(symbol_count: int, market: str) -> PortfolioInputs:
    """포트폴리오 전략, 위험 관리, 거래비용 기본값을 입력받는다."""

    print("\n[포트폴리오 전략 설정]")
    initial_cash = ask_float(
        "초기 자금 (기본 10,000,000): ",
        default=10_000_000,
        minimum=1,
    )
    maximum_positions = ask_integer(
        f"최대 보유 종목 수 (기본 {min(5, symbol_count)}): ",
        default=min(5, symbol_count),
        minimum=1,
        maximum=symbol_count,
    )
    trend_window = ask_integer(
        "장기 추세 기간 (기본 200일): ",
        default=200,
        minimum=21,
    )
    momentum_window = ask_integer("모멘텀 기간 (기본 126일): ", default=126)
    rebalance_interval = ask_integer("리밸런싱 주기 (기본 20거래일): ", default=20)
    default_trading_value = 1_000_000_000 if market == "KOREA" else 10_000_000
    minimum_trading_value = ask_float(
        f"최소 일평균 거래대금 (기본 {default_trading_value:,.0f}): ",
        default=default_trading_value,
    )
    maximum_volatility_percent = ask_float(
        "최대 연환산 변동성 % (기본 60): ",
        default=60,
        minimum=0.01,
        maximum=500,
    )
    stop_loss_percent = ask_float(
        "고정 손절률 % (기본 5): ",
        default=5,
        maximum=99,
    )
    trailing_stop_percent = ask_float(
        "트레일링 스톱률 % (기본 7): ",
        default=7,
        maximum=99,
    )
    commission_percent = ask_float(
        "수수료율 % (기본 0.015): ",
        default=0.015,
        maximum=99,
    )
    slippage_percent = ask_float(
        "슬리피지율 % (기본 0.05): ",
        default=0.05,
        maximum=99,
    )
    target_cagr = ask_float(
        "목표 연복리수익률 % (기본 10): ",
        default=10,
    )
    maximum_drawdown = ask_float(
        "최대 허용 MDD % (기본 15): ",
        default=15,
        minimum=0.01,
        maximum=100,
    )
    validation_percent = ask_float(
        "마지막 검증 구간 비율 % (기본 30): ",
        default=30,
        minimum=1,
        maximum=90,
    )
    refresh_cache = ask_choice(
        "기존 데이터 캐시를 새로 받을까요? (y/N): ",
        {"": "no", "n": "no", "no": "no", "y": "yes", "yes": "yes"},
    ) == "yes"
    trades_csv = ask_optional_csv_path("포트폴리오 거래 내역 저장 경로 (생략 가능): ")

    return PortfolioInputs(
        config=PortfolioBacktestConfig(
            initial_cash=initial_cash,
            commission_rate=commission_percent / 100.0,
            slippage_rate=slippage_percent / 100.0,
            maximum_positions=maximum_positions,
            rebalance_interval=rebalance_interval,
            trend_window=trend_window,
            momentum_window=momentum_window,
            minimum_average_trading_value=minimum_trading_value,
            maximum_annualized_volatility=maximum_volatility_percent / 100.0,
            stop_loss_rate=stop_loss_percent / 100.0,
            trailing_stop_rate=trailing_stop_percent / 100.0,
            target_cagr_rate=target_cagr,
            maximum_allowed_drawdown_rate=maximum_drawdown,
            validation_ratio=validation_percent / 100.0,
        ),
        trades_csv=trades_csv,
        refresh_cache=refresh_cache,
    )


def run_quote() -> None:
    """선택한 증권사에서 현재가를 조회하고 표를 출력한다."""

    provider = choose_provider()
    market = choose_market(provider)
    symbols = ask_symbols()
    client = create_stock_client(provider)
    quotes = client.quotes(symbols, market=market)
    print("\n[현재가 조회 결과]\n")
    print(render_quotes(quotes))


def run_history() -> None:
    """선택한 증권사에서 과거 시세를 조회하고 표를 출력한다."""

    provider = choose_provider()
    market = choose_market(provider, include_korea=provider == StockProvider.KIS.value)
    symbols = ask_symbols()
    client = create_stock_client(provider)
    histories = []

    if provider == StockProvider.KIS.value:
        print("\nKIS 과거 시세는 일봉(1d)을 조회합니다.")
        start, end = ask_date_range()
        for symbol in symbols:
            histories.append(
                client.history(symbol, market=market, timeframe="1d", start=start, end=end)
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
                client.history(symbol, market=market, timeframe=timeframe, count=count)
            )

    print("\n[과거 시세 조회 결과]\n")
    print("\n\n".join(render_history(history) for history in histories))


def run_kis_backtest() -> None:
    """화면 입력값으로 KIS 실제 과거 데이터 백테스트를 실행한다."""

    print("\n[KIS 실제 과거 데이터 백테스트]")
    while True:
        symbol = ask_kis_backtest_symbol()
        market = choose_kis_backtest_market(symbol)
        start, end = ask_date_range()

        print("\nKIS에서 과거 데이터를 수집하고 있습니다...")
        try:
            candles = load_candles_from_kis(symbol, market, start, end)
        except ValueError as exc:
            # 종목·시장 조합이나 조회 기간 때문에 데이터가 없으면 처음부터 다시 받는다.
            print(f"\n조회할 수 없습니다: {exc}")
            print("종목, 시장, 조회 기간을 다시 입력해 주세요.\n")
            continue
        break

    settings = ask_backtest_inputs()
    data_csv = ask_optional_csv_path("수집한 KIS 일봉 저장 경로 (생략 가능): ")

    print(f"KIS 데이터 수집 완료: {symbol} {len(candles):,}개 일봉")
    if data_csv:
        save_candles_to_csv(candles, data_csv)
        print(f"과거 데이터 저장: {data_csv}")
    _execute_backtest(candles, settings)


def run_csv_backtest() -> None:
    """화면에서 선택한 CSV 파일로 백테스트를 실행한다."""

    print("\n[CSV 파일 백테스트]")
    while True:
        csv_path = ask_text("OHLCV CSV 파일 경로: ")
        try:
            candles = load_candles_from_csv(csv_path)
        except (FileNotFoundError, ValueError) as exc:
            print(f"CSV를 불러올 수 없습니다: {exc}")
            print("CSV 파일 경로를 다시 입력해 주세요.\n")
            continue
        break

    settings = ask_backtest_inputs()
    print(f"\nCSV 데이터 불러오기 완료: {len(candles):,}개 일봉")
    _execute_backtest(candles, settings)


def run_portfolio_backtest() -> None:
    """KIS 여러 종목으로 추세·모멘텀 포트폴리오를 검증한다."""

    print("\n[KIS 다중 종목 포트폴리오 백테스트]")
    print("같은 시장의 종목 코드를 공백 또는 쉼표로 구분해 입력하세요.")
    symbols = ask_portfolio_symbols()
    market = choose_kis_backtest_market(symbols[0])
    start, end = ask_portfolio_date_range()
    inputs = ask_portfolio_inputs(len(symbols), market)

    print("\n종목별 KIS 과거 데이터를 준비하고 있습니다...")
    portfolio_data = load_portfolio_from_kis(
        symbols=symbols,
        market=market,
        start=start,
        end=end,
        refresh=inputs.refresh_cache,
    )
    if portfolio_data.cache_hits:
        print(f"캐시 사용: {', '.join(portfolio_data.cache_hits)}")
    if portfolio_data.downloaded:
        print(f"KIS 다운로드: {', '.join(portfolio_data.downloaded)}")
    for symbol, message in portfolio_data.errors.items():
        print(f"제외된 종목: {symbol} ({message})")

    print(f"포트폴리오 데이터 준비 완료: {len(portfolio_data.histories)}종목")
    result = PortfolioBacktestEngine(inputs.config).run(portfolio_data.histories)
    print("\n[포트폴리오 백테스트 결과]\n")
    print(format_portfolio_result(result))
    if inputs.trades_csv:
        save_portfolio_trades_csv(result, inputs.trades_csv)
        print(f"\n포트폴리오 거래 내역 저장: {inputs.trades_csv}")


def _execute_backtest(
    candles: Sequence[StockCandle],
    settings: BacktestInputs,
) -> None:
    """데이터 출처와 무관하게 동일한 전략과 체결 규칙을 실행한다."""

    strategy = MovingAverageCrossStrategy(settings.short_window, settings.long_window)
    config = BacktestConfig(
        initial_cash=settings.initial_cash,
        commission_rate=settings.commission_rate,
        slippage_rate=settings.slippage_rate,
    )
    result = BacktestEngine(config).run(candles, strategy)

    print("\n[백테스트 결과]\n")
    print(format_backtest_result(result))
    if settings.trades_csv:
        save_trades_csv(result, settings.trades_csv)
        print(f"\n거래 내역 저장: {settings.trades_csv}")


def main() -> int:
    """화면 안내에 따라 기능과 설정을 입력받아 한 번의 작업을 실행한다."""

    print("=" * 60)
    print(" PyTrading - 주식 자동매매 및 백테스트 시스템")
    print("=" * 60)
    print("명령행 옵션 없이 화면의 번호를 선택하여 실행합니다.\n")

    try:
        action = choose_main_action()
        if action == "exit":
            print("프로그램을 종료합니다.")
        elif action == "quote":
            run_quote()
        elif action == "history":
            run_history()
        elif action == "kis_backtest":
            run_kis_backtest()
        elif action == "csv_backtest":
            run_csv_backtest()
        elif action == "portfolio_backtest":
            run_portfolio_backtest()
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\n프로그램을 종료합니다.")
        return 130
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"\n오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
