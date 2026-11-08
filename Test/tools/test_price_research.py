"""별도 연구 설정·계좌 격리와 일별 기록의 재시작 동작을 검증한다."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from paths import CONFIG_ROOT, DATA_ROOT
from tools.price_research import research_strategy
from tools.price_forward import main, write_daily_report
from trading.paper import PaperAccount


class PriceResearchTests(unittest.TestCase):
    def test_research_does_not_disable_live_earnings(self):
        path = CONFIG_ROOT / "strategy.json"
        before = path.read_bytes()
        strategy = research_strategy()
        self.assertFalse(strategy["earnings_enabled"])
        self.assertFalse(strategy["news_enabled"])
        self.assertEqual(path.read_bytes(), before)

    def test_forward_uses_separate_account_and_observer(self):
        with patch("app.runner.main") as run:
            main(watch=False)
        options = run.call_args.kwargs
        self.assertEqual(options["settings_override"]["output_dir"], DATA_ROOT / "paper-price-research")
        self.assertFalse(options["settings_override"]["watch"])
        self.assertIs(options["decision_observer"], write_daily_report)

    def test_forward_refuses_enabled_earnings(self):
        with patch("tools.price_forward.json.loads", return_value={"earnings_enabled": True, "news_enabled": False}), patch("app.runner.main") as run:
            with self.assertRaises(ValueError):
                main()
            run.assert_not_called()

    def test_daily_report_resumes_counts_without_changing_account(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            account = PaperAccount(folder / "account.json")
            before = copy.deepcopy(account.state)
            snapshot = {"market": "US", "now": "2026-10-20T14:00:00+00:00", "research_decision_reason": "entry_conditions_not_met"}
            write_daily_report(account, snapshot, folder)
            write_daily_report(account, snapshot, folder)
            row = json.loads((folder / "daily/US-2026-10-20.json").read_text(encoding="utf-8"))
            self.assertEqual(row["observations"], 2)
            self.assertEqual(row["reasons"]["entry_conditions_not_met"], 2)
            self.assertEqual(row["buys"], 0)
            self.assertEqual(row["daily_return"], 0)
            self.assertEqual(account.state, before)

    def test_us_day_is_not_utc_day(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            account = PaperAccount(folder / "account.json")
            write_daily_report(account, {"market": "US", "now": "2026-10-21T00:01:00+00:00"}, folder)
            self.assertTrue((folder / "daily/US-2026-10-20.json").exists())

    def test_corrupt_daily_state_is_not_silently_reset(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "daily").mkdir()
            path = folder / "daily/US-2026-10-20.json"
            path.write_text("broken", encoding="utf-8")
            account = PaperAccount(folder / "account.json")
            with self.assertRaises(ValueError):
                write_daily_report(account, {"market": "US", "now": "2026-10-20T14:00:00+00:00"}, folder)
            self.assertEqual(path.read_text(encoding="utf-8"), "broken")
