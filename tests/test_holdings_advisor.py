"""투자 유형별 단계형 매매 의견 엔진 테스트."""
from __future__ import annotations

import unittest

from pytrading.data import (
    AdvisorState,
    AdvisorSymbolState,
    Holding,
    HoldingsPortfolio,
    InvestmentStyle,
)
from pytrading.stocks.models import StockCandle
from pytrading.strategies import AdviceAction, HoldingsAdviceConfig, analyze_holdings


def make_candles(prices: list[float]) -> list[StockCandle]:
    return [
        StockCandle(
            time=f"2025{index:04d}",
            open=price,
            high=price * 1.01,
            low=price * 0.99,
            close=price,
            volume=1_000_000,
        )
        for index, price in enumerate(prices, start=1)
    ]


def make_portfolio(*holdings: Holding) -> HoldingsPortfolio:
    return HoldingsPortfolio(
        holdings=list(holdings),
        total_purchase_amount_usd=sum(item.purchase_amount_usd for item in holdings),
    )


def holding(
    symbol: str,
    quantity: float,
    average_price: float,
    *,
    style: InvestmentStyle = InvestmentStyle.CORE,
    target: float = 10,
    maximum: float = 15,
) -> Holding:
    return Holding(
        symbol=symbol,
        name=symbol,
        market="NASDAQ",
        quantity=quantity,
        average_price_usd=average_price,
        purchase_amount_usd=quantity * average_price,
        weight_percent=0,
        investment_style=style,
        target_weight_percent=target,
        maximum_weight_percent=maximum,
    )


class HoldingsAdvisorTest(unittest.TestCase):
    def setUp(self):
        self.config = HoldingsAdviceConfig(
            short_window=3,
            medium_window=5,
            long_window=8,
            momentum_window=4,
            long_momentum_window=6,
            volatility_window=4,
            atr_window=3,
            rsi_window=4,
            confirmation_days=2,
            long_confirmation_days=3,
        )
        self.rising = [100, 102, 101, 103, 102, 104, 103, 105, 104, 106]

    def test_does_not_apply_retroactive_stop_to_legacy_core_holding(self):
        owned = holding("CORE", 10, 140, target=50, maximum=100)

        result = analyze_holdings(
            make_portfolio(owned),
            {"CORE": make_candles(self.rising)},
            self.config,
        )

        self.assertEqual(result.advices[0].action, AdviceAction.HOLD)

    def test_tactical_stop_applies_only_to_tracked_new_quantity(self):
        owned = holding(
            "TACT",
            10,
            120,
            style=InvestmentStyle.TACTICAL,
            target=5,
            maximum=8,
        )
        state = AdvisorState(
            symbols={
                "TACT": AdvisorSymbolState(
                    first_seen="20250001",
                    observed_quantity=10,
                    observed_average_price_usd=120,
                    protected_quantity=4,
                    protected_entry_price_usd=120,
                    highest_price_usd=125,
                )
            }
        )
        prices = [105, 104, 103, 102, 101, 100, 99, 98, 99, 98]

        result = analyze_holdings(
            make_portfolio(owned),
            {"TACT": make_candles(prices)},
            self.config,
            advisor_state=state,
        )

        self.assertEqual(result.advices[0].action, AdviceAction.SELL_REVIEW)
        self.assertEqual(result.advices[0].suggested_quantity, 4)

    def test_tactical_long_term_breakdown_starts_with_50_percent_reduction(self):
        owned = holding(
            "TACT",
            10,
            100,
            style=InvestmentStyle.TACTICAL,
            target=5,
            maximum=8,
        )
        falling = [110, 109, 108, 107, 106, 104, 102, 100, 98, 96]

        result = analyze_holdings(
            make_portfolio(owned),
            {"TACT": make_candles(falling)},
            self.config,
        )

        self.assertEqual(result.advices[0].action, AdviceAction.REDUCE_50)
        self.assertEqual(result.advices[0].suggested_quantity, 5)

    def test_tactical_breakdown_escalates_after_repeated_signals(self):
        owned = holding(
            "TACT",
            10,
            100,
            style=InvestmentStyle.TACTICAL,
            target=5,
            maximum=8,
        )
        falling = [110, 109, 108, 107, 106, 104, 102, 100, 98, 96]
        state = AdvisorState(
            symbols={
                "TACT": AdvisorSymbolState(
                    observed_quantity=10,
                    observed_average_price_usd=100,
                    last_action=AdviceAction.REDUCE_50.value,
                    signal_streak=2,
                    last_signal_date="20250009",
                )
            }
        )

        result = analyze_holdings(
            make_portfolio(owned),
            {"TACT": make_candles(falling)},
            self.config,
            advisor_state=state,
        )

        self.assertEqual(result.advices[0].action, AdviceAction.SELL_REVIEW)

    def test_core_overweight_reduction_is_limited_to_25_percent(self):
        large = holding("LARGE", 20, 100, maximum=15)
        small = holding("SMALL", 100, 100, maximum=90)

        result = analyze_holdings(
            make_portfolio(large, small),
            {
                "LARGE": make_candles(self.rising),
                "SMALL": make_candles(self.rising),
            },
            self.config,
        )
        advice = next(item for item in result.advices if item.symbol == "LARGE")

        self.assertEqual(advice.action, AdviceAction.REDUCE_25)
        self.assertLessEqual(advice.suggested_quantity, 5)

    def test_add_is_limited_by_cash_and_account_value(self):
        candidate = holding("ADD", 1, 100, target=10, maximum=15)
        ballast = holding(
            "INCOME",
            100,
            100,
            style=InvestmentStyle.INCOME,
            target=70,
            maximum=90,
        )

        result = analyze_holdings(
            make_portfolio(candidate, ballast),
            {
                "ADD": make_candles(self.rising),
                "INCOME": make_candles([100] * len(self.rising)),
            },
            self.config,
            available_cash_usd=5_000,
        )
        advice = next(item for item in result.advices if item.symbol == "ADD")

        self.assertEqual(advice.action, AdviceAction.ADD)
        self.assertLessEqual(advice.suggested_amount_usd, 15_106 * 0.02)
        self.assertLessEqual(advice.suggested_amount_usd, 5_000 * 0.25)

    def test_income_holding_never_auto_adds_without_dividend_data(self):
        income = holding(
            "O",
            1,
            100,
            style=InvestmentStyle.INCOME,
            target=50,
            maximum=80,
        )

        result = analyze_holdings(
            make_portfolio(income),
            {"O": make_candles(self.rising)},
            self.config,
            available_cash_usd=10_000,
        )

        self.assertEqual(result.advices[0].action, AdviceAction.HOLD)
        self.assertIn("배당 데이터", result.advices[0].reasons[0])

    def test_marks_short_history_for_manual_review(self):
        owned = holding("NEW", 2, 100)

        result = analyze_holdings(
            make_portfolio(owned),
            {"NEW": make_candles([100, 101])},
            self.config,
        )

        self.assertEqual(result.advices[0].action, AdviceAction.REVIEW)


if __name__ == "__main__":
    unittest.main()
