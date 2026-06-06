from __future__ import annotations

import unittest

from haoyue_optimizer.core.validation import PlanValidationError, validate_plan_for_apply


class PlanValidationTests(unittest.TestCase):
    def valid_plan(self):
        return {
            "version": "2.0.0",
            "tool_version": "2.0.0-alpha.1",
            "preset": "safe",
            "items": [
                {
                    "id": "disable_gamedvr",
                    "title": "禁用 Game DVR / Xbox 录制",
                    "preset": "safe",
                    "risk": "green",
                    "requires_admin": False,
                    "requires_reboot": False,
                    "side_effects": ["Xbox 录制不可用"],
                    "actions": [
                        {
                            "action_id": "registry_set:HKCU:System\\GameConfigStore:GameDVR_Enabled",
                            "type": "registry_set",
                            "target": "HKCU\\System\\GameConfigStore\\GameDVR_Enabled",
                            "current": {"exists": True, "value": 1},
                            "desired": {"value": 0, "value_type": "dword"},
                        }
                    ],
                }
            ],
        }

    def test_valid_plan_returns_summary(self):
        summary = validate_plan_for_apply(self.valid_plan(), allow_experimental=False)
        self.assertEqual(summary["item_count"], 1)
        self.assertEqual(summary["action_count"], 1)
        self.assertEqual(summary["risk_counts"], {"green": 1})
        self.assertFalse(summary["requires_admin"])
        self.assertFalse(summary["requires_reboot"])
        self.assertEqual(summary["side_effects"], ["Xbox 录制不可用"])
        self.assertFalse(summary["has_experimental"])

    def test_missing_action_id_is_rejected(self):
        plan = self.valid_plan()
        del plan["items"][0]["actions"][0]["action_id"]
        with self.assertRaises(PlanValidationError):
            validate_plan_for_apply(plan, allow_experimental=False)

    def test_unknown_action_type_is_rejected(self):
        plan = self.valid_plan()
        plan["items"][0]["actions"][0]["type"] = "dangerous_shell"
        with self.assertRaises(PlanValidationError):
            validate_plan_for_apply(plan, allow_experimental=False)

    def test_experimental_is_rejected_by_default(self):
        plan = self.valid_plan()
        plan["preset"] = "experimental"
        plan["items"][0]["preset"] = "experimental"
        plan["items"][0]["risk"] = "red"
        with self.assertRaises(PlanValidationError):
            validate_plan_for_apply(plan, allow_experimental=False)

    def test_experimental_can_be_allowed_explicitly(self):
        plan = self.valid_plan()
        plan["preset"] = "experimental"
        plan["items"][0]["preset"] = "experimental"
        plan["items"][0]["risk"] = "red"
        summary = validate_plan_for_apply(plan, allow_experimental=True)
        self.assertTrue(summary["has_experimental"])


if __name__ == "__main__":
    unittest.main()
