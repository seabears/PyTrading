"""Python 공통 진입점이 지속 실행과 기능 테스트를 정확히 분기하는지 검증한다."""
import contextlib
import io
import unittest
from unittest.mock import patch

import main as entrypoint


class EntrypointTest(unittest.TestCase):
    def test_no_argument_starts_continuous_runner(self):
        with patch("app.runner.main") as runner:
            self.assertEqual(entrypoint.main([]), 0)
        runner.assert_called_once()

    def test_named_feature_does_not_start_live_runner(self):
        with patch("tools.test_features.run_feature", return_value=0) as test, \
             patch("app.runner.main") as runner:
            self.assertEqual(entrypoint.main(["--test", "news"]), 0)
        test.assert_called_once_with("news")
        runner.assert_not_called()

    def test_test_without_value_opens_feature_menu(self):
        with patch("tools.test_features.select_feature", return_value="paper") as menu, \
             patch("tools.test_features.run_feature", return_value=1) as test:
            self.assertEqual(entrypoint.main(["--test"]), 1)
        menu.assert_called_once()
        test.assert_called_once_with("paper")

    def test_cancelled_menu_does_not_run_any_feature(self):
        with patch("tools.test_features.select_feature", return_value=None), \
             patch("tools.test_features.run_feature") as test:
            self.assertEqual(entrypoint.main(["--test"]), 0)
        test.assert_not_called()

    def test_unsupported_flag_or_feature_is_rejected(self):
        for arguments in (["--watch"], ["--test", "unknown"]):
            with self.assertRaises(SystemExit) as result, contextlib.redirect_stderr(io.StringIO()):
                entrypoint.main(arguments)
            self.assertEqual(result.exception.code, 2)
