from __future__ import annotations

import unittest

from haoyue_optimizer.ui.scan import classify_action, summarize_plan_status


class UiScanTests(unittest.TestCase):
    def test_classify_passed_registry_action(self):
        action = {
            "type": "registry_set",
            "current": {"exists": True, "value": 0, "value_type": "dword"},
            "desired": {"exists": True, "value": 0, "value_type": "dword"},
        }
        self.assertEqual(classify_action(action), "applied")

    def test_classify_missing_registry_action(self):
        action = {
            "type": "registry_set",
            "current": {"exists": True, "value": 1, "value_type": "dword"},
            "desired": {"exists": True, "value": 0, "value_type": "dword"},
        }
        self.assertEqual(classify_action(action), "missing")

    def test_classify_advisory_action(self):
        action = {"type": "advisory", "current": {"status": "advisory"}, "desired": {"status": "advisory"}}
        self.assertEqual(classify_action(action), "advisory")

    def test_summarize_plan_status(self):
        plan = {
            "items": [
                {"id": "a", "title": "A", "actions": [{"type": "registry_set", "current": {"value": 0}, "desired": {"value": 0}}]},
                {"id": "b", "title": "B", "actions": [{"type": "registry_set", "current": {"value": 1}, "desired": {"value": 0}}]},
                {"id": "c", "title": "C", "actions": [{"type": "advisory", "current": {"status": "advisory"}, "desired": {"status": "advisory"}}]},
            ]
        }
        summary = summarize_plan_status(plan)
        self.assertEqual([item["id"] for item in summary["applied"]], ["a"])
        self.assertEqual([item["id"] for item in summary["missing"]], ["b"])
        self.assertEqual([item["id"] for item in summary["advisory"]], ["c"])


if __name__ == "__main__":
    unittest.main()
