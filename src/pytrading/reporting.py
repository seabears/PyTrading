"""백테스트 결과의 콘솔·CSV 출력."""
from __future__ import annotations

import csv
from pathlib import Path

from pytrading.backtest.models import BacktestResult
from pytrading.backtest.portfolio_models import PortfolioBacktestResult


def format_backtest_result(result: BacktestResult) -> str:
    """터미널에서 빠르게 확인할 수 있는 한글 요약을 만든다."""

    return "\n".join(
        [
            f"전략               : {result.strategy_name}",
            f"초기 자금          : {result.initial_cash:,.0f}",
            f"최종 평가금액      : {result.final_equity:,.0f}",
            f"전략 수익률        : {result.total_return_rate:,.2f}%",
            f"단순 보유 수익률   : {result.benchmark_return_rate:,.2f}%",
            f"최대 낙폭(MDD)     : {result.max_drawdown_rate:,.2f}%",
            f"완료 거래 수       : {result.trade_count}",
            f"승률               : {result.win_rate:,.2f}%",
            f"총 수수료          : {result.total_fees:,.0f}",
        ]
    )


def save_trades_csv(result: BacktestResult, path: str | Path) -> None:
    """각 거래의 체결 정보와 손익을 UTF-8 CSV로 저장한다."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["매수일", "매도일", "수량", "매수가", "매도가", "매수수수료", "매도수수료", "손익", "수익률(%)"]
        )
        for trade in result.trades:
            writer.writerow(
                [
                    trade.entry_time,
                    trade.exit_time,
                    trade.quantity,
                    trade.entry_price,
                    trade.exit_price,
                    trade.entry_fee,
                    trade.exit_fee,
                    trade.profit,
                    trade.return_rate,
                ]
            )


def format_portfolio_result(result: PortfolioBacktestResult) -> str:
    """포트폴리오 성과와 연 10% 목표 판정을 한글 요약으로 만든다."""

    target_status = "달성" if result.target_achieved else "미달성"
    lines = [
        f"전략                    : {result.strategy_name}",
        f"검증 기간               : {result.start_time} ~ {result.end_time}",
        f"초기 자금               : {result.initial_cash:,.0f}",
        f"최종 평가금액           : {result.final_equity:,.0f}",
        f"누적 수익률             : {result.total_return_rate:,.2f}%",
        f"연복리수익률(CAGR)      : {result.cagr_rate:,.2f}%",
        f"최종 검증구간 시작      : {result.validation_start_time}",
        f"최종 검증구간 수익률    : {result.validation_return_rate:,.2f}%",
        f"최종 검증구간 CAGR      : {result.validation_cagr_rate:,.2f}%",
        f"동일비중 보유 CAGR      : {result.benchmark_cagr_rate:,.2f}%",
        f"최대 낙폭(MDD)          : {result.max_drawdown_rate:,.2f}%",
        f"샤프지수                : {result.sharpe_ratio:,.2f}",
        f"완료 거래 수            : {result.trade_count}",
        f"승률                    : {result.win_rate:,.2f}%",
        f"총 수수료               : {result.total_fees:,.0f}",
        f"목표 CAGR               : {result.target_cagr_rate:,.1f}% 이상",
        f"허용 MDD 기준           : -{result.maximum_allowed_drawdown_rate:,.1f}% 이내",
        f"CAGR·MDD 종합 목표      : {target_status}",
        "",
        "[연도별 수익률]",
    ]
    lines.extend(
        f"{year}년                   : {return_rate:,.2f}%"
        for year, return_rate in result.annual_returns.items()
    )
    return "\n".join(lines)


def save_portfolio_trades_csv(
    result: PortfolioBacktestResult,
    path: str | Path,
) -> None:
    """포트폴리오 종목별 거래 내역과 청산 사유를 CSV로 저장한다."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "종목",
                "매수일",
                "매도일",
                "수량",
                "매수가",
                "매도가",
                "매수수수료",
                "매도수수료",
                "손익",
                "수익률(%)",
                "청산사유",
            ]
        )
        for trade in result.trades:
            writer.writerow(
                [
                    trade.symbol,
                    trade.entry_time,
                    trade.exit_time,
                    trade.quantity,
                    trade.entry_price,
                    trade.exit_price,
                    trade.entry_fee,
                    trade.exit_fee,
                    trade.profit,
                    trade.return_rate,
                    trade.exit_reason,
                ]
            )
