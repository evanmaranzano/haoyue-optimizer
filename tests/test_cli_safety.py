from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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


if __name__ == "__main__":
    unittest.main()
