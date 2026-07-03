from __future__ import annotations

import json
import inspect
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent

from haoyue_optimizer.core.executor import apply_plan, rollback_backup
from haoyue_optimizer.core.compat import STORE_SAFE_DEFAULT_START_TYPES
import haoyue_optimizer.core.compat as compat_module
from haoyue_optimizer.core.cleanup import FileCleanupAction
import haoyue_optimizer.core.planner as planner_module
from haoyue_optimizer.core.planner import build_plan, reset_hw_cache
from haoyue_optimizer.core.power import FakePowerBackend, PowerCfgSetAction
from haoyue_optimizer.core.registry import FakeRegistryBackend, RegistrySetAction
from haoyue_optimizer.core.advisory import AdvisoryAction
from haoyue_optimizer.core.report import export_report
from haoyue_optimizer.core.scheduled_task import FakeScheduledTaskBackend, ScheduledTaskSetEnabledAction
from haoyue_optimizer.core.service import (
    FakeServiceBackend,
    ServiceNotModifiable,
    ServiceStartTypeAction,
)
from haoyue_optimizer.core.subprocess_action import FakeSubprocessBackend
from haoyue_optimizer.core.validation import validate_plan_for_apply
from haoyue_optimizer.optimizations.catalog import get_optimizations
from haoyue_optimizer.ui.scan import classify_action

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

    def test_ntfs_disabled_encodings_are_equivalent_without_rewrite(self):
        backend = FakeRegistryBackend()
        backend.write(
            "HKLM",
            r"SYSTEM\CurrentControlSet\Control\FileSystem",
            "NtfsDisableLastAccessUpdate",
            0x80000002,
            "dword",
        )
        action = next(
            action
            for item in get_optimizations()
            if item.id == "disable_last_access_update"
            for action in item.actions
        )

        action.apply(backend)
        current = action.current(backend)

        self.assertEqual(current["value"], 0x80000002)
        self.assertEqual(action.verify(backend)["status"], "passed")
        self.assertEqual(
            classify_action({
                "type": action.action_type,
                "current": current,
                "desired": action.desired(),
            }),
            "applied",
        )


class FileCleanupActionTests(unittest.TestCase):
    def test_current_skips_directory_that_disappears_during_enumeration(self):
        action = FileCleanupAction(
            action_id="cleanup:test",
            target="test",
            temp_dirs=["C:/temporary-test-path"],
        )
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "rglob", side_effect=FileNotFoundError("disappeared")),
        ):
            try:
                current = action.current(None)
            except FileNotFoundError as exc:
                self.fail(f"current leaked enumeration race: {exc}")

        self.assertEqual(current["old_files"], 0)
        self.assertEqual(current["old_bytes"], 0)

    def test_apply_skips_directory_that_disappears_during_enumeration(self):
        action = FileCleanupAction(
            action_id="cleanup:test",
            target="test",
            temp_dirs=["C:/temporary-test-path"],
        )
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "rglob", side_effect=FileNotFoundError("disappeared")),
        ):
            try:
                backup = action.apply(None)
            except FileNotFoundError as exc:
                self.fail(f"apply leaked enumeration race: {exc}")

        self.assertEqual(backup["deleted_count"], 0)
        self.assertEqual(backup["skipped_locked"], 1)


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

    def test_store_safe_guard_is_case_insensitive(self):
        backend = FakeServiceBackend()
        backend.add_service("WUAUSERV", start_type="manual", running=True)
        action = ServiceStartTypeAction("WUAUSERV", "disabled", stop=True)

        backup = action.apply(backend)

        self.assertIn("verify", backup)
        self.assertEqual(backup["verify"]["status"], "blocked")
        self.assertEqual(backend.get("WUAUSERV")["start_type"], "manual")
        self.assertTrue(backend.get("WUAUSERV")["running"])

    def test_verify_fails_when_requested_stop_did_not_take_effect(self):
        class StopIgnoringBackend(FakeServiceBackend):
            def stop(self, name: str) -> None:
                pass

        backend = StopIgnoringBackend()
        backend.add_service("DiagTrack", start_type="auto", running=True)
        action = ServiceStartTypeAction("DiagTrack", "disabled", stop=True)

        action.apply(backend)

        self.assertEqual(action.verify(backend)["status"], "failed")


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
    def test_system_responsiveness_uses_supported_low_latency_value(self):
        action = next(
            action
            for item in get_optimizations()
            if item.id == "disable_net_throttle"
            for action in item.actions
            if action.target.endswith("\\SystemResponsiveness")
        )
        self.assertEqual(action.desired()["value"], 10)

    def test_laptop_power_items_are_excluded_on_desktop(self):
        plan = build_plan(
            "aggressive",
            registry_backend=FakeRegistryBackend(),
            service_backend=FakeServiceBackend(),
            task_backend=FakeScheduledTaskBackend(),
            power_backend=FakePowerBackend(active_scheme="scheme-a"),
            subprocess_backend=FakeSubprocessBackend(),
            hw_context={"is_intel_hybrid": True, "is_amd": False, "is_laptop": False},
        )
        ids = {item["id"] for item in plan["items"]}
        self.assertNotIn("disable_laptop_ac", ids)
        self.assertNotIn("disable_laptop_ac_intel_hybrid", ids)

    def test_laptop_power_items_are_included_on_matching_laptop(self):
        plan = build_plan(
            "aggressive",
            registry_backend=FakeRegistryBackend(),
            service_backend=FakeServiceBackend(),
            task_backend=FakeScheduledTaskBackend(),
            power_backend=FakePowerBackend(active_scheme="scheme-a"),
            subprocess_backend=FakeSubprocessBackend(),
            hw_context={"is_intel_hybrid": True, "is_amd": False, "is_laptop": True},
        )
        ids = {item["id"] for item in plan["items"]}
        self.assertIn("disable_laptop_ac", ids)
        self.assertIn("disable_laptop_ac_intel_hybrid", ids)

    def test_explicit_profile_items_require_matching_opt_in(self):
        self.assertIn("enabled_profiles", inspect.signature(build_plan).parameters)
        backends = {
            "registry_backend": FakeRegistryBackend(),
            "service_backend": FakeServiceBackend(),
            "task_backend": FakeScheduledTaskBackend(),
            "power_backend": FakePowerBackend(active_scheme="scheme-a"),
            "subprocess_backend": FakeSubprocessBackend(),
            "hw_context": _FAKE_HW,
        }
        default_plan = build_plan("aggressive", **backends)
        opted_in_plan = build_plan("aggressive", enabled_profiles={"no_printer"}, **backends)

        self.assertNotIn("disable_print_services", {item["id"] for item in default_plan["items"]})
        self.assertIn("disable_print_services", {item["id"] for item in opted_in_plan["items"]})

    def test_slate_system_type_is_treated_as_mobile(self):
        result = subprocess.CompletedProcess(["powershell"], 1, stdout="8 8", stderr="")
        with patch("haoyue_optimizer.core.compat.subprocess.run", return_value=result):
            self.assertTrue(compat_module.is_laptop())

    def test_injected_hardware_context_does_not_pollute_process_cache(self):
        planner_module.reset_hw_cache()
        backends = {
            "registry_backend": FakeRegistryBackend(),
            "service_backend": FakeServiceBackend(),
            "task_backend": FakeScheduledTaskBackend(),
            "power_backend": FakePowerBackend(active_scheme="scheme-a"),
            "subprocess_backend": FakeSubprocessBackend(),
        }
        build_plan(
            "aggressive",
            hw_context={"is_intel_hybrid": True, "is_amd": False, "is_laptop": True},
            **backends,
        )
        with (
            patch.object(planner_module, "is_intel_hybrid_cpu", return_value=False),
            patch.object(planner_module, "is_amd_cpu", return_value=False),
            patch.object(planner_module, "is_laptop", return_value=False),
        ):
            second_plan = build_plan("aggressive", **backends)

        ids = {item["id"] for item in second_plan["items"]}
        self.assertNotIn("disable_laptop_ac_intel_hybrid", ids)

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
        plan = build_plan(
            "safe",
            registry_backend=FakeRegistryBackend(),
            service_backend=FakeServiceBackend(),
            subprocess_backend=FakeSubprocessBackend(),
            hw_context=_FAKE_HW,
        )
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
        subprocess_backend = FakeSubprocessBackend()
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
            plan = build_plan(
                preset,
                registry_backend=registry,
                service_backend=services,
                task_backend=tasks,
                power_backend=power,
                subprocess_backend=subprocess_backend,
                hw_context=_FAKE_HW,
            )
            self.assertEqual(plan["preset"], preset)
            self.assertTrue(plan["items"], preset)
            for item in plan["items"]:
                for action in item["actions"]:
                    self.assertIn("action_id", action)
                    self.assertIn("current", action)
                    self.assertIn("desired", action)

    def test_build_plan_uses_injected_subprocess_backend(self):
        self.assertIn("subprocess_backend", inspect.signature(build_plan).parameters)
        subprocess_backend = FakeSubprocessBackend()

        plan = build_plan(
            "aggressive",
            registry_backend=FakeRegistryBackend(),
            service_backend=FakeServiceBackend(),
            task_backend=FakeScheduledTaskBackend(),
            power_backend=FakePowerBackend(active_scheme="scheme-a"),
            subprocess_backend=subprocess_backend,
            hw_context=_FAKE_HW,
        )

        subprocess_actions = [
            action
            for item in plan["items"]
            for action in item["actions"]
            if action["type"] == "subprocess"
        ]
        self.assertTrue(subprocess_actions)
        self.assertTrue(all(action["current"]["status"] == "pending_command" for action in subprocess_actions))


class ExecutorTests(unittest.TestCase):
    def test_partial_service_failure_is_failed_and_can_rollback(self):
        class FailOnceBackend(FakeServiceBackend):
            def __init__(self):
                super().__init__()
                self.failed_once = False

            def set_start_type(self, name: str, start_type: str) -> None:
                if not self.failed_once:
                    self.failed_once = True
                    raise ServiceNotModifiable("denied")
                super().set_start_type(name, start_type)

        backend = FailOnceBackend()
        backend.add_service("DiagTrack", start_type="auto", running=True)
        action = ServiceStartTypeAction("DiagTrack", "disabled", stop=True)
        plan = {
            "preset": "test",
            "items": [{
                "id": "partial-service",
                "title": "partial service",
                "actions": [{
                    "action_id": action.action_id,
                    "target": action.target,
                    "current": action.current(backend),
                }],
            }],
        }
        with patch("haoyue_optimizer.core.executor._catalog_actions", return_value={action.action_id: action}):
            backup = apply_plan(plan, service_backend=backend, write_file=False)

        self.assertEqual(backup["items"][0]["status"], "failed")
        self.assertFalse(backend.get("DiagTrack")["running"])

        rollback_backup(backup, service_backend=backend)
        self.assertEqual(backend.get("DiagTrack")["start_type"], "auto")
        self.assertTrue(backend.get("DiagTrack")["running"])

    def test_rollback_does_not_write_for_blocked_action(self):
        class TrackingBackend(FakeServiceBackend):
            def __init__(self):
                super().__init__()
                self.write_count = 0

            def set_start_type(self, name: str, start_type: str) -> None:
                self.write_count += 1
                super().set_start_type(name, start_type)

            def stop(self, name: str) -> None:
                self.write_count += 1
                super().stop(name)

            def start(self, name: str) -> None:
                self.write_count += 1
                super().start(name)

        backend = TrackingBackend()
        backend.add_service("wuauserv", start_type="manual", running=True)
        action = ServiceStartTypeAction("wuauserv", "disabled", stop=True)
        plan = {
            "preset": "test",
            "items": [{
                "id": "protected-service",
                "title": "protected service",
                "actions": [{"action_id": action.action_id, "target": action.target}],
            }],
        }
        with patch("haoyue_optimizer.core.executor._catalog_actions", return_value={action.action_id: action}):
            backup = apply_plan(plan, service_backend=backend, write_file=False)

        rollback_backup(backup, service_backend=backend)

        self.assertEqual(backend.write_count, 0)

    def test_apply_plan_preserves_blocked_action_status(self):
        backend = FakeServiceBackend()
        backend.add_service("wuauserv", start_type="manual", running=True)
        action = ServiceStartTypeAction("wuauserv", "disabled", stop=True)
        plan = {
            "preset": "test",
            "items": [{
                "id": "protected-service",
                "title": "protected service",
                "actions": [{"action_id": action.action_id, "target": action.target}],
            }],
        }

        with patch("haoyue_optimizer.core.executor._catalog_actions", return_value={action.action_id: action}):
            backup = apply_plan(plan, service_backend=backend, write_file=False)

        self.assertEqual(backup["items"][0]["status"], "blocked")
        self.assertEqual(backup["items"][0]["actions"][0]["verify"]["status"], "blocked")

    def test_apply_and_rollback_use_injected_subprocess_backend(self):
        self.assertIn("subprocess_backend", inspect.signature(apply_plan).parameters)
        self.assertIn("subprocess_backend", inspect.signature(rollback_backup).parameters)
        subprocess_backend = FakeSubprocessBackend()
        action_id = "firewall:block_diagtrack"
        plan = {
            "preset": "test",
            "items": [{
                "id": "block_telemetry_firewall",
                "title": "test subprocess",
                "actions": [{"action_id": action_id, "target": "DiagTrack"}],
            }],
        }

        backup = apply_plan(plan, subprocess_backend=subprocess_backend, write_file=False)
        self.assertEqual(backup["items"][0]["status"], "passed")
        self.assertEqual(len(subprocess_backend.commands), 1)

        rollback_backup(backup, subprocess_backend=subprocess_backend)
        self.assertEqual(len(subprocess_backend.commands), 2)

    def test_apply_plan_writes_backup_and_rollback_restores_state_for_all_action_types(self):
        registry = FakeRegistryBackend()
        services = FakeServiceBackend()
        tasks = FakeScheduledTaskBackend()
        power = FakePowerBackend(active_scheme="scheme-a")
        subprocess_backend = FakeSubprocessBackend()
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

        safe_plan = build_plan(
            "safe",
            registry_backend=registry,
            service_backend=services,
            task_backend=tasks,
            power_backend=power,
            subprocess_backend=subprocess_backend,
            hw_context=_FAKE_HW,
        )
        aggressive_plan = build_plan(
            "aggressive",
            registry_backend=registry,
            service_backend=services,
            task_backend=tasks,
            power_backend=power,
            subprocess_backend=subprocess_backend,
            hw_context=_FAKE_HW,
        )
        combined = {**safe_plan, "preset": "combined", "items": safe_plan["items"] + aggressive_plan["items"]}

        backup = apply_plan(
            combined,
            registry_backend=registry,
            service_backend=services,
            task_backend=tasks,
            power_backend=power,
            subprocess_backend=subprocess_backend,
            write_file=False,
        )

        self.assertTrue(backup["items"])
        self.assertEqual(registry.read("HKCU", "System\\GameConfigStore", "GameDVR_Enabled")["value"], 0)
        self.assertEqual(services.get("DiagTrack")["start_type"], "disabled")
        self.assertFalse(tasks.get(r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator")["enabled"])
        self.assertEqual(power.get_value("scheme-a", "2a737441-1930-4402-8d77-b2bebba308a3", "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"), {"ac": 0, "dc": 0})

        rollback_backup(
            backup,
            registry_backend=registry,
            service_backend=services,
            task_backend=tasks,
            power_backend=power,
            subprocess_backend=subprocess_backend,
        )

        self.assertEqual(registry.read("HKCU", "System\\GameConfigStore", "GameDVR_Enabled")["value"], 1)
        self.assertEqual(services.get("DiagTrack")["start_type"], "auto")
        self.assertTrue(services.get("DiagTrack")["running"])
        self.assertTrue(tasks.get(r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator")["enabled"])
        self.assertEqual(power.get_value("scheme-a", "2a737441-1930-4402-8d77-b2bebba308a3", "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"), {"ac": 1, "dc": 1})


class StoreSafeRepairTests(unittest.TestCase):
    def test_repair_default_start_types_use_backend_vocabulary(self):
        self.assertLessEqual(
            set(STORE_SAFE_DEFAULT_START_TYPES.values()),
            {"auto", "manual"},
        )

    def test_repair_plan_contains_only_disabled_services_and_validates(self):
        self.assertTrue(hasattr(planner_module, "build_store_safe_repair_plan"))
        backend = FakeServiceBackend()
        backend.add_service("wuauserv", start_type="disabled", running=False)
        backend.add_service("BITS", start_type="manual", running=False)

        plan, actions = planner_module.build_store_safe_repair_plan(service_backend=backend)
        summary = validate_plan_for_apply(plan)

        self.assertEqual(summary["item_count"], 1)
        self.assertEqual(plan["preset"], "repair-store-safe")
        self.assertEqual(plan["items"][0]["actions"][0]["target"], "wuauserv")
        self.assertEqual(plan["items"][0]["actions"][0]["desired"]["start_type"], "manual")
        self.assertIn(plan["items"][0]["actions"][0]["action_id"], actions)

    def test_repair_plan_apply_writes_backup_and_can_rollback(self):
        self.assertIn("additional_actions", inspect.signature(apply_plan).parameters)
        self.assertIn("backup_dir", inspect.signature(apply_plan).parameters)
        backend = FakeServiceBackend()
        backend.add_service("wuauserv", start_type="disabled", running=False)
        plan, actions = planner_module.build_store_safe_repair_plan(service_backend=backend)

        with TemporaryDirectory() as tmp:
            backup = apply_plan(
                plan,
                service_backend=backend,
                additional_actions=actions,
                backup_dir=Path(tmp),
            )
            self.assertTrue(Path(backup["backup_path"]).exists())

        self.assertEqual(backend.get("wuauserv")["start_type"], "manual")
        rollback_backup(backup, service_backend=backend)
        self.assertEqual(backend.get("wuauserv")["start_type"], "disabled")

    def test_repair_plan_skips_service_that_is_no_longer_disabled(self):
        backend = FakeServiceBackend()
        backend.add_service("DoSvc", start_type="disabled", running=False)
        plan, actions = planner_module.build_store_safe_repair_plan(service_backend=backend)
        backend.set_start_type("DoSvc", "manual")

        backup = apply_plan(
            plan,
            service_backend=backend,
            additional_actions=actions,
            write_file=False,
        )

        self.assertEqual(backend.get("DoSvc")["start_type"], "manual")
        self.assertEqual(backup["items"][0]["status"], "skipped")


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
