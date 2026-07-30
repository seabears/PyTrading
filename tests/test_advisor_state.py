"""추천 상태 JSON 저장과 복원 테스트."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pytrading.data import (
    AdvisorState,
    AdvisorSymbolState,
    load_advisor_state,
    save_advisor_state,
)


class AdvisorStateTest(unittest.TestCase):
    def test_missing_file_starts_with_empty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state = load_advisor_state(Path(directory) / "missing.json")

        self.assertEqual(state.symbols, {})

    def test_round_trips_symbol_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            expected = AdvisorState(
                symbols={
                    "MSFT": AdvisorSymbolState(
                        first_seen="20260730",
                        observed_quantity=8,
                        observed_average_price_usd=402.2125,
                        last_action="보유",
                        signal_streak=2,
                    )
                }
            )

            save_advisor_state(expected, path)
            actual = load_advisor_state(path)

        self.assertEqual(actual, expected)
