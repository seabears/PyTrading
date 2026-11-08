"""장기 평가의 연도별 계산과 기간 설정을 합성 자료로 검증한다."""
import unittest

from tools.research_long_history import annual_results, load_settings


class LongHistoryTest(unittest.TestCase):
    def test_annual_returns_compound_instead_of_resetting_capital(self):
        result = {"curve": [{"date": "2020-01-02", "equity": 100}, {"date": "2020-12-31", "equity": 110},
                            {"date": "2021-01-04", "equity": 105}, {"date": "2021-12-31", "equity": 121}],
                  "trades": [{"exit_date": "2021-01-04"}]}
        rows = annual_results(result, 100)
        self.assertAlmostEqual(rows[0]["return"], .1)
        self.assertAlmostEqual(rows[1]["return"], .1)
        self.assertAlmostEqual(rows[1]["max_drawdown"], 1 - 105 / 110)
        self.assertEqual(rows[0]["trades"], 0)
        self.assertEqual(rows[1]["trades"], 1)

    def test_long_and_recent_universes_keep_recent_ipo_separate(self):
        settings = load_settings()
        long_cohort, recent = settings["cohorts"]
        self.assertEqual(long_cohort["start"], "2020-01-02")
        self.assertIn("US:ARM", long_cohort["excluded_symbols"])
        self.assertNotIn("US:ARM", recent["excluded_symbols"])
        self.assertIn("US:SONY", long_cohort["excluded_symbols"])
        self.assertNotIn("US:SONY", recent["excluded_symbols"])
        self.assertIn("US:SPCX", recent["excluded_symbols"])
