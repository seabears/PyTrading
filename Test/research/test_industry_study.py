"""산업군 자료 확인·상품 차단·동일 자금 비교·적은 표본의 노출을 검증한다."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from research.industry_study import group_benchmark, peer_statistics
from tools.collect_industry_history import read_master, register_verified_stocks


class IndustryStudyTests(unittest.TestCase):
    def setUp(self):
        self.costs = {"starting_cash": {"US": 10000}, "allocation_fraction": .1,
                      "max_positions_per_market": 3, "buy_cost_ratio": .001,
                      "sell_cost_ratio": .002, "slippage_ratio": .001}
        self.settings = {"spread_ratio": .001}

    def test_master_reads_exact_stock_fields_without_extracting_archive(self):
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as archive:
            archive.writestr("nasmst.cod", "a\tb\tc\td\tTMUS\tf\tg\tT-MOBILE US INC\t2\tUSD\n")
            archive.writestr("../../unrelated.txt", "ignore")
        found = read_master(memory.getvalue(), "NAS", {"TMUS"})
        self.assertEqual(found["TMUS"], {"exchange": "NAS", "name": "T-MOBILE US INC", "security_type": "2", "currency": "USD"})

    def policy(self):
        return {"allowed_asset_types": ["stock", "bond", "etf"], "disallowed_asset_types": ["etn", "elw", "future", "option"],
                "unknown_instrument": "deny", "verified_instruments": {"SPY": {"asset_type": "etf"}}}

    def test_only_verified_stock_is_added_and_disallowed_products_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            original = self.policy()
            path.write_text(json.dumps(original), encoding="utf-8")
            backup = Path(directory) / "before.json"
            register_verified_stocks(path, {"MRVL": {"name": "Marvell", "currency": "USD", "security_type": "2"}},
                                     {"MRVL": "https://investor.marvell.com/"}, backup)
            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(result["verified_instruments"]["MRVL"]["asset_type"], "stock")
            self.assertEqual(result["disallowed_asset_types"], original["disallowed_asset_types"])
            self.assertEqual(json.loads(backup.read_text(encoding="utf-8")), original)

    def test_nonstock_or_currency_mismatch_never_changes_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            raw = json.dumps(self.policy())
            path.write_text(raw, encoding="utf-8")
            for code, currency in (("3", "USD"), ("2", "EUR")):
                with self.assertRaises(ValueError):
                    register_verified_stocks(path, {"BAD": {"name": "Bad", "currency": currency, "security_type": code}},
                                             {"BAD": "https://example.test/"}, Path(directory) / "before.json")
                self.assertEqual(path.read_text(encoding="utf-8"), raw)

    def test_new_instrument_without_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(self.policy()), encoding="utf-8")
            with self.assertRaises(ValueError):
                register_verified_stocks(path, {"NEW": {"name": "New", "currency": "USD", "security_type": "2"}}, {}, Path(directory) / "before.json")

    def series(self):
        return {"A": [{"date": "2025-01-02", "open": 100, "close": 100}, {"date": "2025-01-03", "open": 101, "close": 101}],
                "B": [{"date": "2025-01-02", "open": 100, "close": 100}, {"date": "2025-01-03", "open": 101, "close": 101}]}

    def test_benchmark_keeps_same_initial_capital_limit_and_reserves_exit_costs(self):
        result = group_benchmark(self.series(), ["2025-01-02", "2025-01-03"], self.costs, self.settings, "2025-01-02", "2025-01-03")
        self.assertGreaterEqual(result["curve"][0]["cash"], 7000)
        self.assertLess(result["curve"][0]["equity"], 10000)

    def test_delayed_symbol_does_not_shorten_period_or_get_synthetic_old_prices(self):
        series = self.series()
        series["B"] = series["B"][1:]
        result = group_benchmark(series, ["2025-01-02", "2025-01-03"], self.costs, self.settings, "2025-01-02", "2025-01-03")
        self.assertEqual(len(result["curve"]), 2)
        self.assertEqual(result["curve"][0]["positions"], 1)
        self.assertEqual(result["curve"][1]["positions"], 2)

    def test_future_price_does_not_change_earlier_benchmark(self):
        series = self.series()
        baseline = group_benchmark(series, ["2025-01-02", "2025-01-03"], self.costs, self.settings, "2025-01-02", "2025-01-03")
        series["B"][1].update(open=500, close=500)
        changed = group_benchmark(series, ["2025-01-02", "2025-01-03"], self.costs, self.settings, "2025-01-02", "2025-01-03")
        self.assertEqual(baseline["curve"][0], changed["curve"][0])

    def test_new_peer_statistics_keep_low_sample_and_zero_trades_visible(self):
        rows = [{"symbol": "A", "base": {"trades": 20, "net_return": .1}, "double_cost": {"net_return": .05}},
                {"symbol": "B", "base": {"trades": 0, "net_return": 0}, "double_cost": {"net_return": 0}},
                {"symbol": "C", "base": {"trades": 2, "net_return": .2}, "double_cost": {"net_return": -.1}}]
        result = peer_statistics(rows, {"A", "B"}, 10)
        self.assertEqual(result["new"]["stocks"], 2)
        self.assertEqual(result["new"]["enough_sample_stocks"], 1)
        self.assertEqual(result["new"]["no_closed_trades"], 1)
        self.assertEqual(result["all"]["positive_both_with_enough_sample"], 1)

    def test_symbol_is_not_double_counted_between_existing_and_new(self):
        rows = [{"symbol": "A", "base": {"trades": 12, "net_return": -.1}, "double_cost": {"net_return": -.2}}]
        result = peer_statistics(rows, {"A"}, 10)
        self.assertEqual(result["all"]["stocks"], result["new"]["stocks"] + result["existing"]["stocks"])
        self.assertEqual(result["new"]["positive_base"], 0)
