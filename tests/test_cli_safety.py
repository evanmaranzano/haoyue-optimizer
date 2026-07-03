from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import haoyue_optimizer.main as main_module
ROOT = Path(__file__).resolve().parent.parent


class CliSafetyTests(unittest.TestCase):
    def write_plan(self, tmp: str, preset: str = "safe", risk: str = "green") -> Path:
        path = Path(tmp) / "plan.json"
        payload = {
            "version": "2.0.0",
            "tool_version": "2.0.0-alpha.1",
            "preset": preset,
            "items": [
                {
                    "id": "disable_gamedvr",
                    "title": "禁用 Game DVR / Xbox 录制",
                    "preset": preset,
                    "risk": risk,
                    "requires_admin": False,
                    "requires_reboot": False,
                    "side_effects": ["Xbox 录制不可用"],
                    "actions": [
                        {
                            "action_id": "missing-action-for-cli-safety-test",
                            "type": "registry_set",
                            "target": "HKCU\\System\\GameConfigStore\\GameDVR_Enabled",
                            "current": {"exists": False},
                            "desired": {"value": 0, "value_type": "dword"},
                        }
                    ],
                }
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_apply_requires_confirmation_or_yes(self):
        with TemporaryDirectory() as tmp:
            plan = self.write_plan(tmp)
            result = subprocess.run(
                [sys.executable, "-m", "haoyue_optimizer.main", "apply", "--plan", str(plan)],
                input="NO\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=ROOT,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("已取消", result.stderr + result.stdout)

    def test_aggressive_plan_accepted_with_yes(self):
        with TemporaryDirectory() as tmp:
            plan = self.write_plan(tmp, preset="aggressive", risk="red")
            result = subprocess.run(
                [sys.executable, "-m", "haoyue_optimizer.main", "apply", "--plan", str(plan), "--yes"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=ROOT,
            )
        self.assertEqual(result.returncode, 0)

    def test_repair_store_safe_uses_validated_plan_executor(self):
        self.assertTrue(hasattr(main_module, "build_store_safe_repair_plan"))
        plan = {
            "version": "2.0.0",
            "preset": "repair-store-safe",
            "items": [{
                "id": "repair_store_safe_wuauserv",
                "title": "repair wuauserv",
                "preset": "repair-store-safe",
                "risk": "green",
                "requires_admin": True,
                "actions": [],
            }],
        }
        actions = {"service:wuauserv:start_type": object()}
        backup = {"items": [], "backup_path": "backup.json"}

        with (
            patch.object(main_module, "is_admin", return_value=True),
            patch.object(main_module, "build_store_safe_repair_plan", return_value=(plan, actions)) as build,
            patch.object(main_module, "validate_plan_for_apply", return_value={"item_count": 1}) as validate,
            patch.object(main_module, "apply_plan", return_value=backup) as apply,
        ):
            result = main_module.main(["repair-store-safe", "--yes"])

        self.assertEqual(result, 0)
        build.assert_called_once_with()
        validate.assert_called_once_with(plan)
        apply.assert_called_once_with(plan, additional_actions=actions)

    def test_plan_command_passes_explicit_profiles_to_planner(self):
        plan = {"version": "2.0.0", "preset": "aggressive", "items": []}
        with patch.object(main_module, "build_plan", return_value=plan) as build:
            try:
                result = main_module.main([
                    "plan",
                    "--preset",
                    "aggressive",
                    "--profile",
                    "no_printer",
                ])
            except SystemExit as exc:
                self.fail(f"--profile was rejected by argparse: {exc}")

        self.assertEqual(result, 0)
        build.assert_called_once_with("aggressive", enabled_profiles={"no_printer"})

    def test_rollback_requires_admin_before_reading_backup(self):
        with (
            patch.object(main_module, "is_admin", return_value=False),
            patch.object(main_module, "read_backup") as read,
            patch.object(main_module, "rollback_backup") as rollback,
        ):
            result = main_module.main(["rollback", "backup.json"])

        self.assertEqual(result, 3)
        read.assert_not_called()
        rollback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
