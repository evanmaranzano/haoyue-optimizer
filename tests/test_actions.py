from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent

from haoyue_optimizer.core.executor import apply_plan, rollback_backup
from haoyue_optimizer.core.planner import build_plan, reset_hw_cache
from haoyue_optimizer.core.power import FakePowerBackend, PowerCfgSetAction
from haoyue_optimizer.core.registry import FakeRegistryBackend, RegistrySetAction
from haoyue_optimizer.core.advisory import AdvisoryAction
from haoyue_optimizer.core.report import export_report
from haoyue_optimizer.core.scheduled_task import FakeScheduledTaskBackend, ScheduledTaskSetEnabledAction
from haoyue_optimizer.core.service import FakeServiceBackend, ServiceStartTypeAction
from haoyue_optimizer.optimizations.catalog import get_optimizations

# Hardware context for tests that use fake backends — prevents real
# hardware detection (PowerShell/WMI) from being invoked during tests.
_FAKE_HW = {"is_intel_hybrid": False, "is_amd": False, "is_laptop": False}


class RegistryActionTests(unittest.TestCase):
    def test_registry_action_backup_apply_verify_and_rollback(self):
        backend = FakeRegistryBackend()
        backend.write("HKCU", "Software\\HYTest", "Enabled", 1, "dword")
        action = RegistrySetAction("HKCU", "Software\\HYTest", "Enabled", 0, "dword")

        before = action.current(backend)
        self.assertEqual(before["value"], 1)
        self.assertTrue(before["exists"])

        backup = action.apply(backend)
        self.assertEqual(backend.read("HKCU", "Software\\HYTest", "Enabled")["value"], 0)
        self.assertEqual(action.verify(backend)["status"], "passed")

        action.rollback(backend, backup["before"])
        restored = backend.read("HKCU", "Software\\HYTest", "Enabled")
        self.assertEqual(restored["value"], 1)
        self.assertEqual(restored["value_type"], "dword")

    def test_registry_action_removes_value_when_original_did_not_exist(self):
        backend = FakeRegistryBackend()
        action = RegistrySetAction("HKCU", "Software\\HYTest", "Missing", 0, "dword")

        backup = action.apply(backend)
        self.assertEqual(action.verify(backend)["status"], "passed")

        action.rollback(backend, backup["before"])
        self.assertIsNone(backend.read("HKCU", "Software\\HYTest", "Missing"))


class ServiceActionTests(unittest.TestCase):
    def test_service_action_backup_apply_verify_and_rollback(self):
        backend = FakeServiceBackend()
        backend.add_service("DiagTrack", start_type="auto", running=True)
        action = ServiceStartTypeAction("DiagTrack", "disabled", stop=True)

        before = action.current(backend)
        self.assertEqual(before["start_type"], "auto")
        self.assertTrue(before["running"])

        backup = action.apply(backend)
        state = backend.get("DiagTrack")
        self.assertEqual(state["start_type"], "disabled")
        self.assertFalse(state["running"])
        self.assertEqual(action.verify(backend)["status"], "passed")

        action.rollback(backend, backup["before"])
        restored = backend.get("DiagTrack")
        self.assertEqual(restored["start_type"], "auto")
        self.assertTrue(restored["running"])

    def test_service_action_skips_missing_service(self):
        backend = FakeServiceBackend()
        action = ServiceStartTypeAction("MissingSvc", "disabled", stop=True)

        backup = action.apply(backend)
        self.assertFalse(backup["before"]["exists"])
        self.assertEqual(action.verify(backend)["status"], "skipped")


class ScheduledTaskActionTests(unittest.TestCase):
    def test_scheduled_task_action_apply_verify_and_rollback(self):
        backend = FakeScheduledTaskBackend()
        backend.add_task(r"\Microsoft\Windows\Application Experience\ProgramDataUpdater", enabled=True)
        action = ScheduledTaskSetEnabledAction(r"\Microsoft\Windows\Application Experience\ProgramDataUpdater", enabled=False)

        backup = action.apply(backend)
        self.assertFalse(backend.get(action.path)["enabled"])
        self.assertEqual(action.verify(backend)["status"], "passed")

        action.rollback(backend, backup["before"])
        self.assertTrue(backend.get(action.path)["enabled"])

    def test_scheduled_task_missing_is_skipped(self):
        backend = FakeScheduledTaskBackend()
        action = ScheduledTaskSetEnabledAction(r"\Missing\Task", enabled=False)
        backup = action.apply(backend)
        self.assertFalse(backup["before"]["exists"])
        self.assertEqual(action.verify(backend)["status"], "skipped")


class PowerActionTests(unittest.TestCase):
    def test_power_action_apply_verify_and_rollback(self):
        backend = FakePowerBackend(active_scheme="scheme-a")
        backend.set_value("scheme-a", "sub", "setting", ac=1, dc=2)
        action = PowerCfgSetAction("sub", "setting", ac=3, dc=4)

        backup = action.apply(backend)
        self.assertEqual(backend.get_value("scheme-a", "sub", "setting"), {"ac": 3, "dc": 4})
        self.assertEqual(action.verify(backend)["status"], "passed")

        action.rollback(backend, backup["before"])
        self.assertEqual(backend.get_value("scheme-a", "sub", "setting"), {"ac": 1, "dc": 2})
        self.assertEqual(backend.active_scheme, "scheme-a")


class AdvisoryActionTests(unittest.TestCase):
    def test_advisory_action_never_writes_and_reports_unsupported(self):
        action = AdvisoryAction(action_id="advisory:gpu_msi_mode", target="GPU MSI mode", message="test message")
        self.assertEqual(action.action_type, "advisory")
        self.assertEqual(action.current(None)["status"], "advisory")
        backup = action.apply(None)
        self.assertEqual(backup["verify"]["status"], "unsupported")
        self.assertEqual(action.verify(None)["status"], "unsupported")
        action.rollback(None, None)


class CatalogPlanTests(unittest.TestCase):
    def test_catalog_ids_are_unique_and_have_side_effects(self):
        optimizations = get_optimizations()
        ids = [item.id for item in optimizations]
        self.assertEqual(len(ids), len(set(ids)))
        action_ids = [action.action_id for item in optimizations for action in item.actions]
        self.assertEqual(len(action_ids), len(set(action_ids)))
        for item in optimizations:
            self.assertTrue(item.side_effects, item.id)
            self.assertIn(item.risk, {"green", "yellow", "red"})
            self.assertIn(item.preset, {"safe", "aggressive"})

    def test_plan_includes_legacy_ids_and_applicability(self):
        plan = build_plan("safe", registry_backend=FakeRegistryBackend(), service_backend=FakeServiceBackend(), hw_context=_FAKE_HW)
        self.assertTrue(plan["items"])
        for item in plan["items"]:
            self.assertIn("legacy_ids", item)
            self.assertIsInstance(item["legacy_ids"], list)
            self.assertIsInstance(item["legacy_ids"], list)
            self.assertIn("applicability", item)
            self.assertIsInstance(item["applicability"], list)
            self.assertTrue(item["applicability"], item["id"])

    def test_build_plans_for_all_presets_contains_current_and_desired_values(self):
        registry = FakeRegistryBackend()
        services = FakeServiceBackend()
        tasks = FakeScheduledTaskBackend()
        power = FakePowerBackend(active_scheme="scheme-a")
        registry.write("HKCU", "System\\GameConfigStore", "GameDVR_Enabled", 1, "dword")
        services.add_service("DiagTrack", start_type="auto", running=True)
        tasks.add_task(r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\MemoryDiagnostic\ProcessMemoryDiagnosticEvents", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\Windows Error Reporting\QueueReporting", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\Defrag\ScheduledDefrag", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\MemoryDiagnostic\RunFullMemoryDiagnostic", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip", enabled=True)
        services.add_service("MMCMS", start_type="auto", running=True)
        power.set_value("scheme-a", "2a737441-1930-4402-8d77-b2bebba308a3", "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", ac=1, dc=1)

        for preset in ("safe", "aggressive"):
            plan = build_plan(preset, registry_backend=registry, service_backend=services, task_backend=tasks, power_backend=power, hw_context=_FAKE_HW)
            self.assertEqual(plan["preset"], preset)
            self.assertTrue(plan["items"], preset)
            for item in plan["items"]:
                for action in item["actions"]:
                    self.assertIn("action_id", action)
                    self.assertIn("current", action)
                    self.assertIn("desired", action)


class ExecutorTests(unittest.TestCase):
    def test_apply_plan_writes_backup_and_rollback_restores_state_for_all_action_types(self):
        registry = FakeRegistryBackend()
        services = FakeServiceBackend()
        tasks = FakeScheduledTaskBackend()
        power = FakePowerBackend(active_scheme="scheme-a")
        registry.write("HKCU", "System\\GameConfigStore", "GameDVR_Enabled", 1, "dword")
        services.add_service("DiagTrack", start_type="auto", running=True)
        tasks.add_task(r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\MemoryDiagnostic\ProcessMemoryDiagnosticEvents", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\Windows Error Reporting\QueueReporting", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\Defrag\ScheduledDefrag", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\MemoryDiagnostic\RunFullMemoryDiagnostic", enabled=True)
        tasks.add_task(r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip", enabled=True)
        services.add_service("MMCMS", start_type="auto", running=True)
        power.set_value("scheme-a", "2a737441-1930-4402-8d77-b2bebba308a3", "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", ac=1, dc=1)

        safe_plan = build_plan("safe", registry_backend=registry, service_backend=services, task_backend=tasks, power_backend=power, hw_context=_FAKE_HW)
        aggressive_plan = build_plan("aggressive", registry_backend=registry, service_backend=services, task_backend=tasks, power_backend=power, hw_context=_FAKE_HW)
        combined = {**safe_plan, "preset": "combined", "items": safe_plan["items"] + aggressive_plan["items"]}

        backup = apply_plan(combined, registry_backend=registry, service_backend=services, task_backend=tasks, power_backend=power, write_file=False)

        self.assertTrue(backup["items"])
        self.assertEqual(registry.read("HKCU", "System\\GameConfigStore", "GameDVR_Enabled")["value"], 0)
        self.assertEqual(services.get("DiagTrack")["start_type"], "disabled")
        self.assertFalse(tasks.get(r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator")["enabled"])
        self.assertEqual(power.get_value("scheme-a", "2a737441-1930-4402-8d77-b2bebba308a3", "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"), {"ac": 0, "dc": 0})

        rollback_backup(backup, registry_backend=registry, service_backend=services, task_backend=tasks, power_backend=power)

        self.assertEqual(registry.read("HKCU", "System\\GameConfigStore", "GameDVR_Enabled")["value"], 1)
        self.assertEqual(services.get("DiagTrack")["start_type"], "auto")
        self.assertTrue(services.get("DiagTrack")["running"])
        self.assertTrue(tasks.get(r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator")["enabled"])
        self.assertEqual(power.get_value("scheme-a", "2a737441-1930-4402-8d77-b2bebba308a3", "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"), {"ac": 1, "dc": 1})


class ReportTests(unittest.TestCase):
    def test_export_report_writes_summary_json(self):
        plan = {"preset": "safe", "items": [{"id": "x", "actions": []}]}
        backup = {"items": [{"actions": [{"verify": {"status": "passed"}}]}]}
        with TemporaryDirectory() as tmp:
            path = export_report(plan, backup, report_dir=Path(tmp))
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["passed"], 1)
        self.assertEqual(payload["summary"]["failed"], 0)


class CatalogLegacyIdTests(unittest.TestCase):
    def test_catalog_legacy_ids_are_unique_for_migrated_items(self):
        optimizations = get_optimizations()
        seen: dict[str, str] = {}
        for item in optimizations:
            if not item.legacy_ids:
                continue  # genuinely new optimization with no legacy mapping
            for lid in item.legacy_ids:
                if lid in seen:
                    self.fail(f"legacy_id {lid!r} appears in both {seen[lid]} and {item.id}")
                seen[lid] = item.id


class CliSmokeTests(unittest.TestCase):
    def test_cli_plan_outputs_json_for_all_presets(self):
        for preset in ("safe", "aggressive"):
            result = subprocess.run(
                [sys.executable, "-m", "haoyue_optimizer.main", "plan", "--preset", preset],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=ROOT,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["preset"], preset)
            self.assertTrue(payload["items"])

    def test_cli_presets_and_doctor_are_read_only(self):
        for command in (["presets"], ["doctor"]):
            result = subprocess.run(
                [sys.executable, "-m", "haoyue_optimizer.main", *command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=ROOT,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
