"""기능 직접 실행과 자동 검증의 분리, 계좌·입력·인증 파일 보호를 확인한다."""
import contextlib
import copy
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from strategy.engine import evaluate
from Test.sample_data import sample
from tools import run_once, show_settings, test_features
from tools.check_strategy import build_scenarios


class IndependentFunctionsTest(unittest.TestCase):
    def test_strategy_scenarios_do_not_mutate_input(self):
        for market in ("KR", "US"):
            original = sample(market)
            before = copy.deepcopy(original)
            decisions = [evaluate(snapshot) for name, snapshot in build_scenarios(original)]
            self.assertEqual([row["action"] for row in decisions], ["BUY", "WAIT", "HOLD", "SELL"])
            self.assertEqual(decisions[-1]["reason"], "stop_loss")
            self.assertEqual(original, before)

    def test_plain_feature_runs_function_instead_of_unit_tests(self):
        with patch("tools.check_strategy.main") as execute, patch("tools.test_features.run_tests") as verify:
            self.assertEqual(test_features.run_feature("strategy"), 0)
        execute.assert_called_once()
        verify.assert_not_called()

    def test_unit_feature_does_not_collect_actual_news(self):
        with patch("tools.test_features.run_tests", return_value=0) as verify, \
             patch("tools.check_news.main") as collect:
            self.assertEqual(test_features.run_feature("unit-news"), 0)
        verify.assert_called_once_with("news")
        collect.assert_not_called()

    def test_menu_selects_direct_news_execution(self):
        with patch("builtins.input", return_value="1"), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(test_features.select_feature(), "news")
        self.assertIn("실제 인터넷 뉴스", output.getvalue())

    def test_one_cycle_uses_separate_account_and_does_not_watch(self):
        with patch("tools.run_once.run") as runner, contextlib.redirect_stdout(io.StringIO()):
            run_once.main()
        arguments = runner.call_args.kwargs
        self.assertEqual(arguments["argv"], [])
        self.assertFalse(arguments["settings_override"]["watch"])
        self.assertIn("tests", arguments["settings_override"]["output_dir"].parts)
        self.assertIn("results", arguments["settings_override"]["output_dir"].parts)

    def test_settings_display_does_not_read_credentials(self):
        settings = {"env_file": Path("fake.env"), "symbols": [("US", "AAPL")]}
        with patch("tools.show_settings.load_run_settings", return_value=settings), \
             patch.object(Path, "read_text", side_effect=AssertionError("credential read")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            show_settings.main()
        self.assertIn("파일 내용은 읽지 않습니다", output.getvalue())
