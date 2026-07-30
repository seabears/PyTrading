"""여러 종목의 KIS 일봉을 로컬 캐시와 함께 수집한다."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pytrading.data.csv_loader import load_candles_from_csv, save_candles_to_csv
from pytrading.data.kis_loader import load_candles_from_kis
from pytrading.stocks.models import StockCandle
from pytrading.stocks.providers.kis import KisStockClient


@dataclass(frozen=True)
class PortfolioData:
    """포트폴리오 연구에 사용할 종목별 일봉과 수집 상태."""

    histories: dict[str, list[StockCandle]]
    cache_hits: list[str] = field(default_factory=list)
    downloaded: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


def load_portfolio_from_kis(
    symbols: list[str],
    market: str,
    start: str,
    end: str,
    *,
    cache_dir: str | Path = "data/cache",
    refresh: bool = False,
    client: KisStockClient | None = None,
) -> PortfolioData:
    """
    여러 종목의 일봉을 가져오되 같은 요청의 캐시가 있으면 API 호출을 생략한다.

    일부 종목 조회가 실패해도 나머지 종목은 유지하고 errors에 원인을 기록한다.
    최종적으로 정상 데이터가 두 종목 미만이면 포트폴리오 검증이 불가능하므로 실패한다.
    """

    normalized_symbols = _normalize_symbols(symbols)
    cache_root = Path(cache_dir)
    # 모든 종목이 캐시에 있으면 인증 정보 없이도 재실행할 수 있도록 지연 생성한다.
    kis_client = client
    histories: dict[str, list[StockCandle]] = {}
    cache_hits: list[str] = []
    downloaded: list[str] = []
    errors: dict[str, str] = {}

    for symbol in normalized_symbols:
        cache_path = _cache_path(cache_root, market, symbol, start, end)
        try:
            if cache_path.exists() and not refresh:
                histories[symbol] = load_candles_from_csv(cache_path)
                cache_hits.append(symbol)
                continue

            if kis_client is None:
                kis_client = KisStockClient()
            candles = load_candles_from_kis(
                symbol=symbol,
                market=market,
                start=start,
                end=end,
                client=kis_client,
            )
            save_candles_to_csv(candles, cache_path)
            histories[symbol] = candles
            downloaded.append(symbol)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            errors[symbol] = str(exc)

    if len(histories) < 2:
        details = "; ".join(f"{symbol}: {message}" for symbol, message in errors.items())
        raise ValueError(f"포트폴리오 데이터는 최소 2종목이 필요합니다. {details}".strip())

    return PortfolioData(
        histories=histories,
        cache_hits=cache_hits,
        downloaded=downloaded,
        errors=errors,
    )


def _normalize_symbols(symbols: list[str]) -> list[str]:
    normalized = list(dict.fromkeys(symbol.strip().upper() for symbol in symbols if symbol.strip()))
    if len(normalized) < 2:
        raise ValueError("포트폴리오에는 서로 다른 종목을 최소 2개 입력해야 합니다.")
    return normalized


def _cache_path(
    cache_root: Path,
    market: str,
    symbol: str,
    start: str,
    end: str,
) -> Path:
    safe_symbol = symbol.replace(".", "_").replace("/", "_")
    return cache_root / market.upper() / f"{safe_symbol}_{start}_{end}.csv"
