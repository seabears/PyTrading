"""명령행 인자 없이 동작하는 메인 화면 테스트."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import main as app


class InteractiveMainTest(unittest.TestCase):
    def test_exit_is_selected_from_screen_menu(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["0"]), redirect_stdout(output):
            exit_code = app.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("현재가 조회", output.getvalue())
        self.assertIn("프로그램을 종료합니다.", output.getvalue())

    def test_csv_backtest_uses_screen_inputs_and_defaults(self):
        # 기능 번호, CSV 경로, 전략 기본값 5개, 거래내역 경로 순서다.
        answers = [
            "4",
            "data/sample_prices.csv",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            exit_code = app.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("CSV 데이터 불러오기 완료", output.getvalue())
        self.assertIn("[백테스트 결과]", output.getvalue())

    def test_invalid_menu_input_is_asked_again(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["잘못된값", "0"]), redirect_stdout(output):
            exit_code = app.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("올바른 번호", output.getvalue())

    def test_portfolio_menu_can_be_selected(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["5"]), redirect_stdout(output):
            self.assertEqual(app.choose_main_action(), "portfolio_backtest")

    def test_domestic_symbol_selects_korea_automatically(self):
        output = io.StringIO()
        with redirect_stdout(output):
            market = app.choose_kis_backtest_market("005930")

        self.assertEqual(market, "KOREA")
        self.assertIn("시장 자동 선택", output.getvalue())

    def test_overseas_symbol_cannot_select_korea(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=[""]), redirect_stdout(output):
            market = app.choose_kis_backtest_market("AAPL")

        self.assertEqual(market, "NASDAQ")
        self.assertNotIn("KOREA", output.getvalue())

    def test_invalid_numeric_symbol_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "6자리"):
            app.choose_kis_backtest_market("1234")

    def test_invalid_numeric_symbol_is_asked_again(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["1234", "005930"]), redirect_stdout(output):
            symbol = app.ask_kis_backtest_symbol()

        self.assertEqual(symbol, "005930")
        self.assertIn("6자리 숫자", output.getvalue())

    def test_portfolio_symbols_reject_mixed_markets(self):
        output = io.StringIO()
        with (
            patch(
                "main.ask_symbols",
                side_effect=[["005930", "AAPL"], ["AAPL", "MSFT"]],
            ),
            redirect_stdout(output),
        ):
            symbols = app.ask_portfolio_symbols()

        self.assertEqual(symbols, ["AAPL", "MSFT"])
        self.assertIn("섞을 수 없습니다", output.getvalue())

    def test_number_outside_range_is_asked_again(self):
        output = io.StringIO()
        answers = ["문자", "0", "11", "5"]
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            value = app.ask_integer("숫자: ", default=3, minimum=1, maximum=10)

        self.assertEqual(value, 5)
        self.assertIn("정수로", output.getvalue())
        self.assertIn("1 이상의", output.getvalue())
        self.assertIn("10 이하의", output.getvalue())

    def test_invalid_date_and_reversed_range_are_asked_again(self):
        output = io.StringIO()
        answers = ["20260230", "20260102", "20260101", "20260103"]
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            start, end = app.ask_date_range()

        self.assertEqual((start, end), ("20260102", "20260103"))
        self.assertIn("YYYYMMDD", output.getvalue())
        self.assertIn("이후 날짜", output.getvalue())

    def test_missing_csv_path_is_asked_again(self):
        answers = [
            "없는파일.csv",
            "data/sample_prices.csv",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            app.run_csv_backtest()

        self.assertIn("CSV 파일 경로를 다시 입력", output.getvalue())
        self.assertIn("[백테스트 결과]", output.getvalue())

    def test_empty_kis_result_restarts_symbol_inputs(self):
        sample_candles = app.load_candles_from_csv("data/sample_prices.csv")
        answers = [
            "AAPL",
            "",
            "20260101",
            "20260131",
            "AAPL",
            "",
            "20260101",
            "20260131",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        output = io.StringIO()
        with (
            patch("builtins.input", side_effect=answers),
            patch(
                "main.load_candles_from_kis",
                side_effect=[ValueError("0건"), sample_candles],
            ) as loader,
            redirect_stdout(output),
        ):
            app.run_kis_backtest()

        self.assertEqual(loader.call_count, 2)
        self.assertIn("다시 입력해 주세요", output.getvalue())
        self.assertIn("[백테스트 결과]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
