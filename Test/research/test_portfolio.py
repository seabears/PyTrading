"""공동 자금·미래 정보 차단·갭 손절·비용 스트레스를 합성 자료로 검증한다."""
import copy
import math
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from research.portfolio import candidate_rules, reversal_rules, rank_symbols, simulate_portfolio, simulate_walk_forward, stress_recorded_trades


class PortfolioTest(unittest.TestCase):
    def setUp(self):
        self.rule = {"family": "momentum", "momentum_days": 2, "trend_days": 2,
                     "rebalance_days": 2, "maximum_positions": 3, "stop_loss": .08, "trailing_stop": .12}
        self.costs = {"starting_cash": {"KR": 10000, "US": 10000}, "allocation_fraction": .1,
                      "buy_cost_ratio": .001, "sell_cost_ratio": .002, "slippage_ratio": .001}
        self.series = {symbol: [{"date": (date(2025, 1, 1) + timedelta(days=index)).isoformat(),
                                 "open": 10 + index, "high": 10 + index, "low": 10 + index,
                                 "close": 10 + index, "volume": 100} for index in range(40)]
                       for symbol in ("US:A", "US:B", "US:C", "US:D")}

    def simulate(self, series=None, costs=None, **kwargs):
        return simulate_portfolio(series or self.series, "US", self.rule, costs or self.costs,
                                  .001, "2025-01-26", "2025-02-09", **kwargs)

    def test_candidate_count_is_bounded(self):
        self.assertEqual(len(candidate_rules()), 24)

    def test_bounded_history_preserves_all_forty_eight_rule_results(self):
        bars = []
        for index in range(500):
            close = 100 + index * .03 + math.sin(index / 8) * 8
            bars.append({"date": (date(2024, 1, 1) + timedelta(days=index)).isoformat(),
                         "open": close, "high": close + 2, "low": close - 2, "close": close, "volume": 100})
        for rule in candidate_rules() + reversal_rules():
            full = simulate_portfolio({"US:A": bars}, "US", rule, self.costs, .001, bars[416]["date"], bars[-1]["date"])
            bounded = simulate_portfolio({"US:A": bars[260:]}, "US", rule, self.costs, .001, bars[416]["date"], bars[-1]["date"])
            self.assertEqual(full, bounded)

    def test_signals_execute_next_day_and_shared_cash_is_nonnegative(self):
        result = self.simulate()
        self.assertEqual(result["trades"][0]["entry_date"], "2025-01-27")
        self.assertTrue(all(row["cash"] >= 0 and row["positions"] <= 3 for row in result["curve"]))
        self.assertTrue(all(row["signal_date"] < row["execution_date"] for row in result["decisions"]))

    def test_future_prices_do_not_change_earlier_targets(self):
        original = self.simulate()
        changed = copy.deepcopy(self.series)
        changed["US:D"][-1].update(open=1000, high=1000, low=1000, close=1000)
        self.assertEqual(original["decisions"], self.simulate(changed)["decisions"])

    def test_double_costs_reduce_profit(self):
        stressed = {**self.costs, **{key: self.costs[key] * 2 for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
        self.assertLess(self.simulate(costs=stressed)["summary"]["net_return"], self.simulate()["summary"]["net_return"])

    def test_recorded_trade_cost_stress_preserves_base_profit_and_reduces_it(self):
        result = self.simulate()
        same_costs = stress_recorded_trades(result["trades"], 10000, self.costs, self.costs, .001, .001)
        self.assertAlmostEqual(same_costs["net_pnl"], result["summary"]["net_pnl"])
        stressed = {**self.costs, **{key: self.costs[key] * 2 for key in ("buy_cost_ratio", "sell_cost_ratio", "slippage_ratio")}}
        stress = stress_recorded_trades(result["trades"], 10000, self.costs, stressed, .001, .002)
        self.assertLess(stress["net_pnl"], same_costs["net_pnl"])

    def test_gap_below_stop_fills_at_open(self):
        changed = copy.deepcopy(self.series)
        for bars in changed.values():
            bars[27].update(open=20, high=20, low=20, close=20)
        result = self.simulate(changed)
        stopped = [trade for trade in result["trades"] if trade["reason"] == "gap_adjusted_stop"]
        self.assertTrue(stopped)
        self.assertTrue(all(trade["exit_price"] < 20 for trade in stopped))

    def test_benchmark_uses_same_total_thirty_percent_budget(self):
        result = self.simulate(buy_and_hold=True)
        invested = 10000 - result["curve"][0]["cash"]
        self.assertLessEqual(invested, 3000)
        self.assertGreater(invested, 2800)
        self.assertEqual(len(result["trades"]), 4)

    def test_negative_momentum_holds_cash(self):
        downward = {symbol: list(reversed(bars)) for symbol, bars in self.series.items()}
        self.assertEqual(rank_symbols(downward, self.rule), [])

    def test_minimum_holding_does_not_block_stop(self):
        self.rule["minimum_holding_days"] = 5
        changed = copy.deepcopy(self.series)
        for bars in changed.values():
            bars[27].update(open=20, high=20, low=20, close=20)
        self.assertTrue(any(trade["exit_date"] == "2025-01-28" and trade["reason"] == "gap_adjusted_stop"
                            for trade in self.simulate(changed)["trades"]))

    def test_walk_forward_selection_receives_only_previous_dates(self):
        bars = [{"date": (date(2024, 1, 1) + timedelta(days=index)).isoformat(),
                 "open": 100 + index, "high": 100 + index, "low": 100 + index,
                 "close": 100 + index, "volume": 100} for index in range(230)]
        start, end = bars[200]["date"], bars[225]["date"]
        seen = []

        def fake_simulate(series, market, rule, costs, spread, first, last, buy_and_hold=False):
            seen.append((max(bar["date"] for bar in series["US:A"]), last))
            summary = {"net_return": 0 if buy_and_hold else .01, "trades": 4, "max_drawdown": .001}
            return {"summary": summary, "curve": [{"date": last, "equity": costs["starting_cash"][market] * 1.01}], "trades": []}

        with patch("research.portfolio.simulate_portfolio", side_effect=fake_simulate):
            result = simulate_walk_forward({"US:A": bars}, "US", self.costs, .001, start, end)
        self.assertTrue(seen)
        legal_cutoffs = {bars[199]["date"], bars[220]["date"]}
        # 한 구간당 48개 후보의 훈련·검증 96회 뒤 실제 운용 1회가 온다.
        # 운용 호출은 해당 구간의 가격을 전달받아도 되며 선택 호출만 과거로 제한된다.
        selection_calls = seen[:96] + seen[97:193]
        self.assertEqual(len(selection_calls), 192)
        self.assertTrue(all(day in legal_cutoffs and last <= day for day, last in selection_calls))
        self.assertTrue(all(item["selected_at"] < item["start"] for item in result["selections"]))

    def test_market_down_filter_excludes_stocks(self):
        histories = {symbol: bars[:] for symbol, bars in self.series.items()}
        # 50개 이상 과거 자료를 만들어 시장은 하락, 방어 ETF는 상승하도록 한다.
        rising = [{"close": 100 + index} for index in range(60)]
        falling = [{"close": 200 - index} for index in range(60)]
        histories.update({"US:SPY": falling, "US:SH": rising, "US:A": rising})
        rule = {**self.rule, "market_proxy": "US:SPY", "defensive_symbol": "US:SH"}
        self.assertEqual(rank_symbols(histories, rule), ["US:SH"])

    def test_profit_stop_does_not_use_same_day_high(self):
        self.rule.update(profit_exits={}, rebalance_days=100, minimum_holding_days=5)
        self.rule["profit_exits"] = {"breakeven_trigger": .03, "profit_lock_trigger": .05}
        changed = copy.deepcopy(self.series)
        for bars in changed.values():
            # 27일 시가 36에 매수. 같은 날 45까지 갔다가 35까지 내려온 순서는 모른다.
            bars[26].update(open=36, high=45, low=35, close=44)
            bars[27].update(open=38, high=40, low=37, close=39)
        result = self.simulate(changed)
        locked = [trade for trade in result["trades"] if trade["reason"] == "profit_lock"]
        self.assertTrue(locked)
        self.assertTrue(all(trade["exit_date"] == "2025-01-28" for trade in locked))
        # 고점 갱신 다음 날 갭 하락: 보호 기준보다 낮은 시가에서 불리하게 체결한다.
        self.assertTrue(all(trade["exit_price"] < 38 for trade in locked))
