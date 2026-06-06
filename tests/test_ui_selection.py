from __future__ import annotations

import unittest

from haoyue_optimizer.ui.selection import parse_selection


class UiSelectionTests(unittest.TestCase):
    def test_parse_comma_numbers(self):
        self.assertEqual(parse_selection("1,3,5", total=6), [0, 2, 4])

    def test_parse_all(self):
        self.assertEqual(parse_selection("all", total=3), [0, 1, 2])

    def test_parse_safe_keyword(self):
        items = [{"risk": "green"}, {"risk": "yellow"}, {"risk": "green"}]
        self.assertEqual(parse_selection("safe", total=3, items=items), [0, 2])

    def test_parse_ignores_out_of_range_and_duplicates(self):
        self.assertEqual(parse_selection("2,2,9,x", total=3), [1])


if __name__ == "__main__":
    unittest.main()
