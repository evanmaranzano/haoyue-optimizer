# Haoyue Full Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate every legacy Haoyue optimizer item into an auditable matrix, safely expand the modular v2 catalog, add apply safety gates, verify with fake-backend tests, and build a separate v2 exe without overwriting the legacy exe.

**Architecture:** Build the migration in layers: first create a complete legacy migration matrix, then harden the v2 execution path, then migrate catalog items by category. `catalog.py` becomes an aggregator; category modules hold `Optimization` objects with `legacy_ids`; safety validation lives in `core/admin.py` and `core/validation.py`; apply/rollback remains in `core/executor.py`.

**Tech Stack:** Python 3.11+/stdlib dataclasses, unittest, PyInstaller, Windows registry/service/schtasks/powercfg wrappers, JSON/Markdown docs.

---

## File Map

### Existing files to modify

- `C:/Users/Administrator/haoyue_optimizer/core/models.py` — add `legacy_ids` and keep Optimization metadata explicit.
- `C:/Users/Administrator/haoyue_optimizer/core/registry.py` — add registry delete/advisory-friendly actions if required by the matrix.
- `C:/Users/Administrator/haoyue_optimizer/core/planner.py` — emit `legacy_ids`, `applicability`, and schema-friendly action fields.
- `C:/Users/Administrator/haoyue_optimizer/core/executor.py` — add validation, per-action error isolation, status summary, and experimental/admin enforcement hooks.
- `C:/Users/Administrator/haoyue_optimizer/core/backup.py` — make backup filenames collision-safe and keep latest lookup compatible.
- `C:/Users/Administrator/haoyue_optimizer/core/report.py` — summarize all execution statuses.
- `C:/Users/Administrator/haoyue_optimizer/main.py` — add `apply --yes`, `--allow-experimental`, confirmation, and clear errors.
- `C:/Users/Administrator/haoyue_optimizer/optimizations/catalog.py` — turn into category aggregator.
- `C:/Users/Administrator/tests/test_actions.py` — keep existing tests passing; move or supplement with focused tests.
- `C:/Users/Administrator/皓月定制优化工具.spec` — do not overwrite legacy build behavior until final task; preferably create a v2 spec instead.

### New files to create

- `C:/Users/Administrator/haoyue_optimizer/data/migration_matrix.json` — machine-readable complete mapping of legacy items.
- `C:/Users/Administrator/haoyue_optimizer/data/__init__.py` — package marker.
- `C:/Users/Administrator/docs/haoyue_optimizer_migration_matrix.md` — human-readable matrix review document.
- `C:/Users/Administrator/haoyue_optimizer/core/admin.py` — admin detection.
- `C:/Users/Administrator/haoyue_optimizer/core/validation.py` — plan schema and policy validation.
- `C:/Users/Administrator/haoyue_optimizer/core/advisory.py` — detect-only/no-op action for planned/experimental items that should not write.
- Category modules under `C:/Users/Administrator/haoyue_optimizer/optimizations/`:
  - `gaming.py`
  - `privacy.py`
  - `services.py`
  - `scheduled_tasks.py`
  - `network.py`
  - `power.py`
  - `input.py`
  - `disk.py`
  - `display.py`
  - `system.py`
  - `cleanup.py`
  - `experimental.py`
- Tests:
  - `C:/Users/Administrator/tests/test_migration_matrix.py`
  - `C:/Users/Administrator/tests/test_validation.py`
  - `C:/Users/Administrator/tests/test_backup_report.py`
  - `C:/Users/Administrator/tests/test_cli_safety.py`
- `C:/Users/Administrator/皓月定制优化工具-v2.spec` — separate v2 PyInstaller spec.

---

## Task 1: Create complete migration matrix skeleton

**Files:**
- Read: `C:/Users/Administrator/Desktop/皓月定制优化工具.py`
- Create: `C:/Users/Administrator/haoyue_optimizer/data/__init__.py`
- Create: `C:/Users/Administrator/haoyue_optimizer/data/migration_matrix.json`
- Create: `C:/Users/Administrator/docs/haoyue_optimizer_migration_matrix.md`
- Test: `C:/Users/Administrator/tests/test_migration_matrix.py`

- [ ] **Step 1: Create the data package marker**

Create `C:/Users/Administrator/haoyue_optimizer/data/__init__.py` with:

```python
"""Static data files for Haoyue optimizer."""
```

- [ ] **Step 2: Extract the legacy list exactly**

Read `C:/Users/Administrator/Desktop/皓月定制优化工具.py:200-352` and extract every tuple from `get_optimizations()` into `migration_matrix.json`.

The JSON must start with this structure and include all 73 legacy IDs from the old function:

```json
{
  "version": "1.0",
  "source": "C:/Users/Administrator/Desktop/皓月定制优化工具.py",
  "legacy_count": 73,
  "items": [
    {
      "legacy_id": "gamedvr",
      "legacy_name": "禁用 Game DVR / Xbox 录制",
      "legacy_category": "游戏",
      "legacy_risk": "LOW",
      "legacy_apply_fn": "apply_gamedvr",
      "targets": [],
      "new_status": "planned",
      "new_id": "disable_gamedvr",
      "new_preset": "safe",
      "new_risk": "green",
      "requires_admin": false,
      "requires_reboot": false,
      "side_effects": ["Xbox 录制、回放和截图功能不可用"],
      "verify": "读取相关注册表值并与 desired 比较。",
      "rollback": "通过动作级备份恢复原值；原值不存在则删除。",
      "decision_reason": "旧版低风险游戏录制项，副作用明确，可检测、可回滚，适合迁移。"
    }
  ]
}
```

For items whose exact target is not yet confirmed, use:

```json
"targets": [
  {
    "type": "advisory",
    "target": "legacy apply function requires review before implementation"
  }
]
```

Do not leave any empty string in `decision_reason`, `verify`, or `rollback`.

- [ ] **Step 3: Write the matrix completeness test**

Create `C:/Users/Administrator/tests/test_migration_matrix.py`:

```python
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path("C:/Users/Administrator")
MATRIX = ROOT / "haoyue_optimizer" / "data" / "migration_matrix.json"

EXPECTED_LEGACY_IDS = {
    "gamedvr", "gamedvr_policy", "fse", "gamemode", "hags", "vrr", "mmcss_games",
    "net_throttle", "tcp_nodelay", "dns_priority", "dns_negative", "qos_bw", "qos_nla", "net_mem",
    "kb_opt", "mouse_opt", "sticky_keys", "toggle_keys", "access_all",
    "ssd_opt", "bg_apps", "transparency", "setting_sync", "content_del", "tracking",
    "driver_search", "telemetry", "svchost_thresh", "file_alloc", "admin_share", "autorun",
    "explorer_restart", "map_download", "feeds", "soft_landing", "wu_pause",
    "mapsbroker", "svc_safe",
    "wifi_power", "cpu_unpark", "unlock_ppm", "energy_veto",
    "win32_pri", "low_latency2",
    "dns_flush", "temp_clean",
    "gaming_boost", "gaming_preset", "power_perf", "laptop_ac", "laptop_bat",
    "gpu_preempt", "superfetch", "large_cache", "disable_mmcss", "disk_no_sleep",
    "low_latency3", "wu_cache", "telemetry_full", "audio_no_excl", "startup_delay",
    "boot_timeout", "fse_global", "anim_disable", "usb_suspend_dis", "nic_nagle",
    "nic_lso_disable", "disable_prefetch", "disable_bg_tasks", "disable_mem_compress",
    "timer_res", "gpu_msi_mode", "nic_rss_opt",
}


class MigrationMatrixTests(unittest.TestCase):
    def load_matrix(self):
        return json.loads(MATRIX.read_text(encoding="utf-8"))

    def test_matrix_contains_every_legacy_id_once(self):
        payload = self.load_matrix()
        ids = [item["legacy_id"] for item in payload["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), EXPECTED_LEGACY_IDS)
        self.assertEqual(payload["legacy_count"], len(EXPECTED_LEGACY_IDS))

    def test_every_item_has_decision_fields(self):
        allowed_status = {"migrated", "merged", "planned", "experimental", "deprecated"}
        for item in self.load_matrix()["items"]:
            self.assertIn(item["new_status"], allowed_status, item["legacy_id"])
            self.assertTrue(item["decision_reason"].strip(), item["legacy_id"])
            self.assertTrue(item["verify"].strip(), item["legacy_id"])
            self.assertTrue(item["rollback"].strip(), item["legacy_id"])
            if item["new_status"] != "deprecated":
                self.assertTrue(item["side_effects"], item["legacy_id"])
            if item["new_status"] in {"migrated", "merged", "experimental"}:
                self.assertTrue(item["new_id"].strip(), item["legacy_id"])

    def test_safe_gaming_privacy_items_are_declared_rollbackable(self):
        for item in self.load_matrix()["items"]:
            if item.get("new_preset") in {"safe", "gaming", "privacy"} and item["new_status"] != "deprecated":
                self.assertNotIn("无法回滚", item["rollback"], item["legacy_id"])
                self.assertNotEqual(item["rollback"], "advisory only", item["legacy_id"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run the matrix test and verify it passes**

Run:

```powershell
python -m unittest C:/Users/Administrator/tests/test_migration_matrix.py -v
```

Expected: all tests pass. If import discovery behaves differently on Windows, run:

```powershell
python C:/Users/Administrator/tests/test_migration_matrix.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Create the human-readable matrix**

Create `C:/Users/Administrator/docs/haoyue_optimizer_migration_matrix.md` with a table containing all 73 items:

```markdown
# 皓月定制优化工具迁移矩阵

| Legacy ID | 旧分类 | 旧风险 | 新状态 | 新预设 | 新风险 | 新 ID | 决策原因 |
|---|---|---:|---|---|---|---|---|
| gamedvr | 游戏 | LOW | planned | safe | green | disable_gamedvr | 旧版低风险游戏录制项，副作用明确，可检测、可回滚，适合迁移。 |
```

The table must have one row per item in `migration_matrix.json`.

---

## Task 2: Add Optimization legacy IDs and planner metadata

**Files:**
- Modify: `C:/Users/Administrator/haoyue_optimizer/core/models.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/core/planner.py`
- Test: `C:/Users/Administrator/tests/test_actions.py`

- [ ] **Step 1: Add failing test for legacy IDs in plans**

Append this test to `CatalogPlanTests` in `C:/Users/Administrator/tests/test_actions.py`:

```python
    def test_plan_includes_legacy_ids_and_applicability(self):
        plan = build_plan("safe", registry_backend=FakeRegistryBackend(), service_backend=FakeServiceBackend())
        self.assertTrue(plan["items"])
        for item in plan["items"]:
            self.assertIn("legacy_ids", item)
            self.assertIsInstance(item["legacy_ids"], list)
            self.assertTrue(item["legacy_ids"], item["id"])
            self.assertIn("applicability", item)
            self.assertIsInstance(item["applicability"], list)
            self.assertTrue(item["applicability"], item["id"])
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```powershell
python C:/Users/Administrator/tests/test_actions.py -v
```

Expected: failure because `legacy_ids` is missing from `Optimization` and plan output.

- [ ] **Step 3: Extend the Optimization model**

Modify `C:/Users/Administrator/haoyue_optimizer/core/models.py` so `Optimization` becomes:

```python
@dataclass(frozen=True)
class Optimization:
    id: str
    title: str
    category: str
    preset: str
    risk: str
    evidence: str
    benefit: list[str]
    side_effects: list[str]
    actions: list[Any]
    legacy_ids: list[str] = field(default_factory=list)
    requires_admin: bool = True
    requires_reboot: bool = False
    applicability: list[str] = field(default_factory=lambda: ["Windows 10/11"])
```

- [ ] **Step 4: Emit metadata in the planner**

Modify the `items.append({ ... })` block in `C:/Users/Administrator/haoyue_optimizer/core/planner.py` to include:

```python
            "legacy_ids": optimization.legacy_ids,
            "applicability": optimization.applicability,
```

The final item dictionary must include both fields before `actions`.

- [ ] **Step 5: Update existing catalog items with legacy IDs**

In `C:/Users/Administrator/haoyue_optimizer/optimizations/catalog.py`, add `legacy_ids` to every existing `Optimization`:

```python
legacy_ids=["gamedvr", "gamedvr_policy"],
```

Use these mappings:

- `disable_gamedvr`: `['gamedvr', 'gamedvr_policy']`
- `enable_gamemode`: `['gamemode']`
- `disable_basic_telemetry`: `['telemetry', 'tracking']`
- `disable_content_delivery`: `['content_del', 'feeds']`
- `disable_safe_services`: `['mapsbroker', 'svc_safe']`
- `gaming_usb_suspend_off`: `['usb_suspend_dis']`
- `privacy_disable_compat_tasks`: `['telemetry_full', 'disable_bg_tasks']`
- `experimental_gpu_msi_placeholder`: `['gpu_msi_mode']`

- [ ] **Step 6: Run tests and verify they pass**

Run:

```powershell
python C:/Users/Administrator/tests/test_actions.py -v
```

Expected: all tests pass.

---

## Task 3: Add plan validation and admin detection

**Files:**
- Create: `C:/Users/Administrator/haoyue_optimizer/core/admin.py`
- Create: `C:/Users/Administrator/haoyue_optimizer/core/validation.py`
- Test: `C:/Users/Administrator/tests/test_validation.py`

- [ ] **Step 1: Write validation tests**

Create `C:/Users/Administrator/tests/test_validation.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify they fail because the module does not exist**

Run:

```powershell
python C:/Users/Administrator/tests/test_validation.py -v
```

Expected: `ModuleNotFoundError` for `haoyue_optimizer.core.validation`.

- [ ] **Step 3: Create admin detection**

Create `C:/Users/Administrator/haoyue_optimizer/core/admin.py`:

```python
from __future__ import annotations

import ctypes


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
```

- [ ] **Step 4: Create plan validation**

Create `C:/Users/Administrator/haoyue_optimizer/core/validation.py`:

```python
from __future__ import annotations

from typing import Any

ALLOWED_ACTION_TYPES = {
    "registry_set",
    "service_start_type",
    "scheduled_task_enabled",
    "powercfg_set",
    "advisory",
}

ALLOWED_STATUSES = {"passed", "failed", "skipped", "unsupported", "pending_reboot", "partial"}


class PlanValidationError(ValueError):
    pass


def validate_plan_for_apply(plan: dict[str, Any], allow_experimental: bool) -> dict[str, Any]:
    if plan.get("version") != "2.0.0":
        raise PlanValidationError("unsupported or missing plan version")
    items = plan.get("items")
    if not isinstance(items, list):
        raise PlanValidationError("plan items must be a list")

    action_count = 0
    risk_counts: dict[str, int] = {}
    requires_admin = False
    requires_reboot = 0
    side_effects: list[str] = []
    has_experimental = plan.get("preset") == "experimental"

    for index, item in enumerate(items):
        for key in ("id", "preset", "risk", "actions"):
            if key not in item:
                raise PlanValidationError(f"item {index} missing {key}")
        if item["preset"] == "experimental" or item["risk"] == "red":
            has_experimental = True
        risk_counts[item["risk"]] = risk_counts.get(item["risk"], 0) + 1
        requires_admin = requires_admin or bool(item.get("requires_admin", True))
        if item.get("requires_reboot"):
            requires_reboot += 1
        side_effects.extend(item.get("side_effects", []))

        actions = item["actions"]
        if not isinstance(actions, list):
            raise PlanValidationError(f"item {item['id']} actions must be a list")
        for action_index, action in enumerate(actions):
            for key in ("action_id", "type", "target", "desired"):
                if key not in action:
                    raise PlanValidationError(f"item {item['id']} action {action_index} missing {key}")
            if action["type"] not in ALLOWED_ACTION_TYPES:
                raise PlanValidationError(f"unsupported action type: {action['type']}")
            action_count += 1

    if has_experimental and not allow_experimental:
        raise PlanValidationError("experimental plan requires --allow-experimental")

    return {
        "item_count": len(items),
        "action_count": action_count,
        "risk_counts": risk_counts,
        "requires_admin": requires_admin,
        "requires_reboot": requires_reboot,
        "side_effects": side_effects,
        "has_experimental": has_experimental,
    }
```

- [ ] **Step 5: Run validation tests and verify they pass**

Run:

```powershell
python C:/Users/Administrator/tests/test_validation.py -v
```

Expected: all tests pass.

---

## Task 4: Harden apply CLI and executor policy

**Files:**
- Modify: `C:/Users/Administrator/haoyue_optimizer/main.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/core/executor.py`
- Test: `C:/Users/Administrator/tests/test_cli_safety.py`

- [ ] **Step 1: Write CLI safety tests**

Create `C:/Users/Administrator/tests/test_cli_safety.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class CliSafetyTests(unittest.TestCase):
    def write_plan(self, tmp: str, preset: str = "safe") -> Path:
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
                    "risk": "red" if preset == "experimental" else "green",
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
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("已取消", result.stderr + result.stdout)

    def test_experimental_requires_flag_even_with_yes(self):
        with TemporaryDirectory() as tmp:
            plan = self.write_plan(tmp, preset="experimental")
            result = subprocess.run(
                [sys.executable, "-m", "haoyue_optimizer.main", "apply", "--plan", str(plan), "--yes"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("experimental", result.stderr.lower() + result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run CLI safety tests and verify they fail**

Run:

```powershell
python C:/Users/Administrator/tests/test_cli_safety.py -v
```

Expected: tests fail because `--yes` and experimental enforcement are not implemented.

- [ ] **Step 3: Add CLI arguments**

Modify the apply parser in `C:/Users/Administrator/haoyue_optimizer/main.py`:

```python
    apply_parser = sub.add_parser("apply", help="应用 JSON 变更计划")
    apply_parser.add_argument("--plan", required=True)
    apply_parser.add_argument("--report", action="store_true")
    apply_parser.add_argument("--yes", action="store_true", help="跳过交互确认")
    apply_parser.add_argument("--allow-experimental", action="store_true", help="允许应用 experimental 计划")
```

- [ ] **Step 4: Add imports for safety checks**

At the top of `main.py`, add:

```python
from haoyue_optimizer.core.admin import is_admin
from haoyue_optimizer.core.validation import PlanValidationError, validate_plan_for_apply
```

- [ ] **Step 5: Replace apply handling with validated confirmation flow**

Replace the `if args.command == "apply":` block in `main.py` with:

```python
    if args.command == "apply":
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        try:
            summary = validate_plan_for_apply(plan, allow_experimental=args.allow_experimental)
        except PlanValidationError as exc:
            print(f"计划校验失败: {exc}", file=sys.stderr)
            return 2
        if summary["requires_admin"] and not is_admin():
            print("此计划需要管理员权限，请用管理员 PowerShell 重新运行。", file=sys.stderr)
            return 3
        if not args.yes:
            print(_format_apply_summary(summary))
            confirm = input("输入 APPLY 确认执行: ").strip()
            if confirm != "APPLY":
                print("已取消", file=sys.stderr)
                return 4
        backup = apply_plan(plan)
        if args.report:
            report_path = export_report(plan, backup)
            backup["report_path"] = str(report_path)
        print(json.dumps(backup, ensure_ascii=False, indent=2))
        return 0
```

Add this helper before `if __name__ == "__main__":`:

```python
def _format_apply_summary(summary: dict) -> str:
    lines = [
        "即将应用计划:",
        f"优化项: {summary['item_count']}",
        f"动作数: {summary['action_count']}",
        f"风险分布: {summary['risk_counts']}",
        f"需要重启的优化项: {summary['requires_reboot']}",
    ]
    if summary["side_effects"]:
        lines.append("副作用:")
        for effect in summary["side_effects"][:20]:
            lines.append(f"- {effect}")
    return "\n".join(lines)
```

- [ ] **Step 6: Add executor per-action error isolation**

In `C:/Users/Administrator/haoyue_optimizer/core/executor.py`, replace the inner action loop with:

```python
        item_statuses = []
        for action_plan in item.get("actions", []):
            try:
                action = actions_by_id[action_plan["action_id"]]
                backend = _backend_for(action.action_type, registry_backend, service_backend, task_backend, power_backend)
                action_backup = action.apply(backend)
                action_backup["verify"] = action.verify(backend)
            except Exception as exc:
                action_backup = {
                    "action_id": action_plan.get("action_id", "unknown"),
                    "target": action_plan.get("target", "unknown"),
                    "before": action_plan.get("current"),
                    "verify": {"status": "failed", "detail": str(exc)},
                }
            item_statuses.append(action_backup["verify"].get("status", "failed"))
            backup_item["actions"].append(action_backup)
        backup_item["status"] = _combine_statuses(item_statuses)
```

Add helper near the bottom:

```python
def _combine_statuses(statuses: list[str]) -> str:
    if not statuses:
        return "skipped"
    unique = set(statuses)
    if len(unique) == 1:
        return statuses[0]
    if "failed" in unique:
        return "partial"
    if "pending_reboot" in unique:
        return "pending_reboot"
    return "partial"
```

- [ ] **Step 7: Run CLI safety tests**

Run:

```powershell
python C:/Users/Administrator/tests/test_cli_safety.py -v
```

Expected: all tests pass.

- [ ] **Step 8: Run existing action tests**

Run:

```powershell
python C:/Users/Administrator/tests/test_actions.py -v
```

Expected: all tests pass.

---

## Task 5: Stabilize backup and report summaries

**Files:**
- Modify: `C:/Users/Administrator/haoyue_optimizer/core/backup.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/core/report.py`
- Create: `C:/Users/Administrator/tests/test_backup_report.py`

- [ ] **Step 1: Write backup/report tests**

Create `C:/Users/Administrator/tests/test_backup_report.py`:

```python
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from haoyue_optimizer.core.backup import latest_backup, write_backup
from haoyue_optimizer.core.report import export_report


class BackupReportTests(unittest.TestCase):
    def test_write_backup_uses_unique_names(self):
        backup = {"items": []}
        with TemporaryDirectory() as tmp:
            first = write_backup(backup, backup_dir=Path(tmp))
            second = write_backup(backup, backup_dir=Path(tmp))
            self.assertNotEqual(first.name, second.name)
            self.assertTrue(first.name.endswith(".json"))
            self.assertTrue(second.name.endswith(".json"))

    def test_latest_backup_reads_newest_file(self):
        with TemporaryDirectory() as tmp:
            first = write_backup({"name": "first", "items": []}, backup_dir=Path(tmp))
            second = write_backup({"name": "second", "items": []}, backup_dir=Path(tmp))
            latest = latest_backup(backup_dir=Path(tmp))
            self.assertEqual(latest, second)
            self.assertNotEqual(first, second)

    def test_report_counts_all_statuses(self):
        backup = {
            "items": [
                {"actions": [
                    {"verify": {"status": "passed"}},
                    {"verify": {"status": "failed"}},
                    {"verify": {"status": "skipped"}},
                    {"verify": {"status": "unsupported"}},
                    {"verify": {"status": "pending_reboot"}},
                    {"verify": {"status": "partial"}},
                ]}
            ]
        }
        with TemporaryDirectory() as tmp:
            path = export_report({"preset": "safe", "items": []}, backup, report_dir=Path(tmp))
            payload = json.loads(path.read_text(encoding="utf-8"))
        for status in ("passed", "failed", "skipped", "unsupported", "pending_reboot", "partial"):
            self.assertEqual(payload["summary"][status], 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify failures where behavior is missing**

Run:

```powershell
python C:/Users/Administrator/tests/test_backup_report.py -v
```

Expected: unique-name or summary tests fail with current implementation.

- [ ] **Step 3: Update backup naming and latest lookup**

Modify `C:/Users/Administrator/haoyue_optimizer/core/backup.py` to use UUID-backed names:

```python
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def backup_root() -> Path:
    return Path.home() / "AppData" / "Local" / "HY_Optimizer" / "backups"


def write_backup(backup: dict, backup_dir: Path | None = None) -> Path:
    root = backup_dir or backup_root()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = root / f"{stamp}-{uuid4().hex[:8]}.json"
    path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def latest_backup(backup_dir: Path | None = None) -> Path | None:
    root = backup_dir or backup_root()
    if not root.exists():
        return None
    files = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def read_backup(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Update report status summary**

Modify `C:/Users/Administrator/haoyue_optimizer/core/report.py` summary initialization to include:

```python
summary = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "unsupported": 0,
    "pending_reboot": 0,
    "partial": 0,
}
```

When counting, use:

```python
status = action.get("verify", {}).get("status", "failed")
if status not in summary:
    summary["failed"] += 1
else:
    summary[status] += 1
```

- [ ] **Step 5: Run backup/report tests**

Run:

```powershell
python C:/Users/Administrator/tests/test_backup_report.py -v
```

Expected: all tests pass.

---

## Task 6: Split catalog and migrate safe first batch

**Files:**
- Create: `C:/Users/Administrator/haoyue_optimizer/optimizations/gaming.py`
- Create: `C:/Users/Administrator/haoyue_optimizer/optimizations/privacy.py`
- Create: `C:/Users/Administrator/haoyue_optimizer/optimizations/services.py`
- Create: `C:/Users/Administrator/haoyue_optimizer/optimizations/input.py`
- Create: `C:/Users/Administrator/haoyue_optimizer/optimizations/display.py`
- Create: `C:/Users/Administrator/haoyue_optimizer/optimizations/system.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/optimizations/catalog.py`
- Modify: `C:/Users/Administrator/tests/test_actions.py`

- [ ] **Step 1: Add catalog coverage test**

Append to `CatalogPlanTests` in `test_actions.py`:

```python
    def test_catalog_legacy_ids_are_unique_for_migrated_items(self):
        seen = {}
        for item in get_optimizations():
            self.assertTrue(item.legacy_ids, item.id)
            for legacy_id in item.legacy_ids:
                self.assertNotIn(legacy_id, seen, f"{legacy_id} reused by {item.id} and {seen.get(legacy_id)}")
                seen[legacy_id] = item.id
```

- [ ] **Step 2: Create category files with functions**

Each category file must define `get_optimizations() -> list[Optimization]`.

Example for `C:/Users/Administrator/haoyue_optimizer/optimizations/gaming.py`:

```python
from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_gamedvr",
            title="禁用 Game DVR / Xbox 录制",
            category="gaming",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["减少后台录制占用", "降低游戏叠加层干扰"],
            side_effects=["Xbox 录制、截图、回放功能不可用"],
            legacy_ids=["gamedvr", "gamedvr_policy"],
            requires_admin=False,
            actions=[
                RegistrySetAction("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 0, "dword"),
                RegistrySetAction("HKCU", r"System\GameConfigStore", "GameDVR_FSEBehaviorMode", 2, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0, "dword"),
            ],
        ),
        Optimization(
            id="enable_gamemode",
            title="启用 Windows Game Mode",
            category="gaming",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["让 Windows 优先使用游戏模式调度策略"],
            side_effects=["少数旧游戏可能表现不同"],
            legacy_ids=["gamemode"],
            requires_admin=False,
            actions=[
                RegistrySetAction("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled", 1, "dword"),
                RegistrySetAction("HKCU", r"Software\Microsoft\GameBar", "AllowAutoGameMode", 1, "dword"),
            ],
        ),
    ]
```

Move existing matching entries from old `catalog.py` into the appropriate files.

- [ ] **Step 3: Add low-risk UI/system/input entries**

Add safe registry-backed items only when the old target is confirmed from the legacy apply function. Examples that may be added if confirmed:

- `disable_transparency`, legacy `transparency`, preset `safe`, registry-backed.
- `disable_setting_sync`, legacy `setting_sync`, preset `safe`, registry-backed.
- `disable_sticky_toggle_keys`, legacy `sticky_keys` and `toggle_keys`, preset `safe`, registry-backed.
- `disable_startup_delay`, legacy `startup_delay`, preset `safe`, registry-backed.
- `disable_autorun`, legacy `autorun`, preset `safe`, registry-backed.

Do not invent registry paths. If the exact old target is not found, leave the item in the migration matrix as `planned` and do not add it to executable catalog.

- [ ] **Step 4: Make catalog.py aggregate category files**

Replace `C:/Users/Administrator/haoyue_optimizer/optimizations/catalog.py` with:

```python
from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.optimizations import display, gaming, input, privacy, services, system


def get_optimizations() -> list[Optimization]:
    result: list[Optimization] = []
    for module in (gaming, privacy, services, input, display, system):
        result.extend(module.get_optimizations())
    return result
```

When later category modules are created, add them to the module tuple.

- [ ] **Step 5: Run catalog and plan tests**

Run:

```powershell
python C:/Users/Administrator/tests/test_actions.py -v
python -m haoyue_optimizer.main plan --preset safe
python -m haoyue_optimizer.main scan --preset safe
```

Expected: tests pass; safe plan and scan output valid JSON/text.

---

## Task 7: Migrate gaming, privacy, services, and power batches

**Files:**
- Create/modify: `C:/Users/Administrator/haoyue_optimizer/optimizations/power.py`
- Create/modify: `C:/Users/Administrator/haoyue_optimizer/optimizations/scheduled_tasks.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/optimizations/gaming.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/optimizations/privacy.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/optimizations/services.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/optimizations/catalog.py`
- Test: `C:/Users/Administrator/tests/test_actions.py`

- [ ] **Step 1: Add category modules to catalog aggregator**

Update import and module tuple in `catalog.py`:

```python
from haoyue_optimizer.optimizations import display, gaming, input, power, privacy, scheduled_tasks, services, system

...
for module in (gaming, privacy, services, scheduled_tasks, power, input, display, system):
```

- [ ] **Step 2: Move current USB selective suspend item to power.py**

Create `power.py` with the existing `gaming_usb_suspend_off` optimization using `PowerCfgSetAction` and `legacy_ids=["usb_suspend_dis"]`.

- [ ] **Step 3: Move compatibility scheduled task item to scheduled_tasks.py**

Create `scheduled_tasks.py` with the existing `privacy_disable_compat_tasks` optimization using `ScheduledTaskSetEnabledAction` and `legacy_ids=["telemetry_full", "disable_bg_tasks"]`.

- [ ] **Step 4: Split service optimization into smaller items**

In `services.py`, avoid one broad `disable_safe_services` item if it mixes unrelated services. Prefer separate optimizations:

```python
Optimization(
    id="disable_maps_broker",
    title="禁用地图下载服务",
    category="services",
    preset="safe",
    risk="green",
    evidence="medium",
    benefit=["减少不使用离线地图时的后台服务"],
    side_effects=["离线地图自动下载不可用"],
    legacy_ids=["mapsbroker"],
    actions=[ServiceStartTypeAction("MapsBroker", "disabled", stop=True)],
)
```

For broader `svc_safe`, include only services that are confirmed low-side-effect. Put disputed services in migration matrix as `experimental` or `planned`, not in safe.

- [ ] **Step 5: Add gaming/privacy items only if current action types support them**

Use registry/service/scheduled-task/powercfg actions only. Items suitable for this batch if exact targets are confirmed:

- HAGS/VRR as `gaming` or `experimental` depending on target and support detection.
- MMCSS Games as `gaming` if registry-backed and rollbackable.
- privacy telemetry/CEIP/tasks as `privacy`.

For each item, include `legacy_ids`, `side_effects`, and non-empty `applicability`.

- [ ] **Step 6: Run tests and plan generation**

Run:

```powershell
python C:/Users/Administrator/tests/test_actions.py -v
python -m haoyue_optimizer.main plan --preset gaming
python -m haoyue_optimizer.main plan --preset privacy
```

Expected: tests pass; gaming/privacy plans generate without exceptions.

---

## Task 8: Add advisory action and experimental catalog

**Files:**
- Create: `C:/Users/Administrator/haoyue_optimizer/core/advisory.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/core/planner.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/core/executor.py`
- Create/modify: `C:/Users/Administrator/haoyue_optimizer/optimizations/experimental.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/optimizations/catalog.py`
- Test: `C:/Users/Administrator/tests/test_actions.py`

- [ ] **Step 1: Write advisory action tests**

Add this test class to `test_actions.py`:

```python
class AdvisoryActionTests(unittest.TestCase):
    def test_advisory_action_never_writes_and_reports_unsupported(self):
        from haoyue_optimizer.core.advisory import AdvisoryAction

        action = AdvisoryAction(
            action_id="advisory:gpu_msi_mode",
            target="GPU MSI mode",
            message="需要按设备检测 GPU PCI 路径，本阶段不自动写入。",
        )
        self.assertEqual(action.action_type, "advisory")
        self.assertEqual(action.current(None)["status"], "advisory")
        backup = action.apply(None)
        self.assertEqual(backup["verify"]["status"], "unsupported")
        self.assertEqual(action.verify(None)["status"], "unsupported")
```

- [ ] **Step 2: Create advisory action**

Create `C:/Users/Administrator/haoyue_optimizer/core/advisory.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdvisoryAction:
    action_id: str
    target: str
    message: str
    action_type: str = "advisory"

    def current(self, backend) -> dict:
        return {"status": "advisory", "detail": self.message}

    def desired(self) -> dict:
        return {"status": "advisory", "detail": self.message}

    def apply(self, backend) -> dict:
        return {
            "action_id": self.action_id,
            "type": self.action_type,
            "target": self.target,
            "before": self.current(backend),
            "verify": self.verify(backend),
        }

    def verify(self, backend) -> dict:
        return {"status": "unsupported", "detail": self.message}

    def rollback(self, backend, before: dict) -> None:
        return None
```

- [ ] **Step 3: Route advisory backend**

In both `planner.py` and `executor.py`, update `_backend_for`:

```python
    if action_type == "advisory":
        return None
```

- [ ] **Step 4: Create experimental catalog**

Create `C:/Users/Administrator/haoyue_optimizer/optimizations/experimental.py` with advisory-only high-risk items:

```python
from __future__ import annotations

from haoyue_optimizer.core.advisory import AdvisoryAction
from haoyue_optimizer.core.models import Optimization


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="experimental_gpu_msi_advisory",
            title="GPU MSI 模式检测提示",
            category="gpu",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["仅提示可能的 GPU MSI 检测方向，不自动修改设备注册表"],
            side_effects=["错误启用 GPU MSI 可能导致驱动异常或设备不可用；本阶段不自动写入"],
            legacy_ids=["gpu_msi_mode"],
            requires_admin=True,
            requires_reboot=True,
            actions=[
                AdvisoryAction(
                    action_id="advisory:gpu_msi_mode",
                    target="GPU MSI mode",
                    message="需要按 GPU 设备实例路径检测，本阶段只生成提示，不自动写入。",
                )
            ],
        ),
        Optimization(
            id="experimental_timer_resolution_advisory",
            title="定时器分辨率优化提示",
            category="scheduling",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["仅提示旧版 timer resolution 项，不自动修改系统定时器"],
            side_effects=["可能增加功耗或影响系统调度；本阶段不自动写入"],
            legacy_ids=["timer_res"],
            requires_admin=True,
            actions=[
                AdvisoryAction(
                    action_id="advisory:timer_res",
                    target="Timer resolution",
                    message="定时器分辨率变更需单独验证，本阶段只作为 experimental 提示。",
                )
            ],
        ),
    ]
```

- [ ] **Step 5: Add experimental to catalog aggregator**

Update `catalog.py` imports and module tuple to include `experimental`.

- [ ] **Step 6: Run experimental plan and safety test**

Run:

```powershell
python C:/Users/Administrator/tests/test_actions.py -v
python -m haoyue_optimizer.main plan --preset experimental
python -m haoyue_optimizer.main apply --plan C:/Users/Administrator/safe-plan.json
```

Expected: tests pass; experimental plan generates; apply without confirmation does not execute unless `APPLY` is typed. Do not type `APPLY` during this check.

---

## Task 9: Full test sweep and read-only verification

**Files:**
- Modify tests as needed under `C:/Users/Administrator/tests/`
- No production code unless tests expose a real defect.

- [ ] **Step 1: Run full unittest discovery**

Run:

```powershell
python -m unittest discover -s C:/Users/Administrator/tests -t C:/Users/Administrator -v
```

Expected: all tests pass. If a test fails because it assumes old catalog counts, update the assertion to check invariants instead of exact counts.

- [ ] **Step 2: Run read-only CLI commands for all presets**

Run:

```powershell
python -m haoyue_optimizer.main presets
python -m haoyue_optimizer.main doctor
python -m haoyue_optimizer.main scan --preset safe
python -m haoyue_optimizer.main scan --preset gaming
python -m haoyue_optimizer.main scan --preset privacy
python -m haoyue_optimizer.main scan --preset experimental
python -m haoyue_optimizer.main plan --preset safe --out C:/Users/Administrator/safe-plan.json
python -m haoyue_optimizer.main plan --preset gaming --out C:/Users/Administrator/gaming-plan.json
python -m haoyue_optimizer.main plan --preset privacy --out C:/Users/Administrator/privacy-plan.json
python -m haoyue_optimizer.main plan --preset experimental --out C:/Users/Administrator/experimental-plan.json
```

Expected: all commands return code 0. These are read-only plan/scan commands.

- [ ] **Step 3: Verify generated JSON parses**

Run:

```powershell
python -c "import json, pathlib; [json.loads(pathlib.Path(p).read_text(encoding='utf-8')) for p in ['C:/Users/Administrator/safe-plan.json','C:/Users/Administrator/gaming-plan.json','C:/Users/Administrator/privacy-plan.json','C:/Users/Administrator/experimental-plan.json']]; print('plans ok')"
```

Expected:

```text
plans ok
```

- [ ] **Step 4: Do not run real apply by default**

Record in the final implementation report:

```text
真实管理员 apply/rollback 未执行，原因：需要用户明确授权并使用最小 HKCU safe plan。
```

Only run real apply/rollback if the user explicitly approves it after seeing the plan output.

---

## Task 10: Create separate v2 PyInstaller spec and build without overwriting legacy

**Files:**
- Create: `C:/Users/Administrator/皓月定制优化工具-v2.spec`
- Preserve: `C:/Users/Administrator/皓月定制优化工具.spec`
- Output: `C:/Users/Administrator/dist/皓月定制优化工具-v2.exe`
- Optional copy: `C:/Users/Administrator/dist/皓月定制优化工具-v1-legacy.exe`

- [ ] **Step 1: Create v2 spec**

Create `C:/Users/Administrator/皓月定制优化工具-v2.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('haoyue_optimizer')


a = Analysis(
    ['C:/Users/Administrator/haoyue_optimizer/main.py'],
    pathex=['C:/Users/Administrator'],
    binaries=[],
    datas=[('C:/Users/Administrator/haoyue_optimizer/data', 'haoyue_optimizer/data')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='皓月定制优化工具-v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

- [ ] **Step 2: Preserve current legacy exe in dist if present**

Run:

```powershell
if (Test-Path "C:/Users/Administrator/dist/皓月定制优化工具.exe") { Copy-Item "C:/Users/Administrator/dist/皓月定制优化工具.exe" "C:/Users/Administrator/dist/皓月定制优化工具-v1-legacy.exe" -Force }
```

Expected: if the legacy exe exists, a `皓月定制优化工具-v1-legacy.exe` copy exists.

- [ ] **Step 3: Build v2 exe**

Run:

```powershell
C:/Users/Administrator/build_env/Scripts/pyinstaller.exe C:/Users/Administrator/皓月定制优化工具-v2.spec --distpath C:/Users/Administrator/dist --workpath C:/Users/Administrator/build
```

Expected: build succeeds and outputs:

```text
C:/Users/Administrator/dist/皓月定制优化工具-v2.exe
```

If PyInstaller warns about running as administrator, record the warning and rerun from a non-admin terminal if needed.

- [ ] **Step 4: Smoke-test v2 exe with read-only commands**

Run:

```powershell
C:/Users/Administrator/dist/皓月定制优化工具-v2.exe presets
C:/Users/Administrator/dist/皓月定制优化工具-v2.exe doctor
C:/Users/Administrator/dist/皓月定制优化工具-v2.exe plan --preset safe --out C:/Users/Administrator/safe-plan-v2-exe.json
```

Expected: all commands succeed. Do not run exe `apply` unless the user separately approves real system writes.

---

## Final Verification Checklist

- [ ] `python -m unittest discover -s C:/Users/Administrator/tests -t C:/Users/Administrator -v` passes.
- [ ] `python -m haoyue_optimizer.main plan --preset safe` succeeds.
- [ ] `python -m haoyue_optimizer.main plan --preset gaming` succeeds.
- [ ] `python -m haoyue_optimizer.main plan --preset privacy` succeeds.
- [ ] `python -m haoyue_optimizer.main plan --preset experimental` succeeds.
- [ ] `python -m haoyue_optimizer.main apply --plan C:/Users/Administrator/experimental-plan.json --yes` fails unless `--allow-experimental` is supplied.
- [ ] Migration matrix contains all 73 legacy IDs.
- [ ] No deprecated item appears in executable catalog.
- [ ] Old exe remains available.
- [ ] New v2 exe is built separately.
- [ ] Real admin apply/rollback is either verified with explicit approval or reported as not run.

## Self-Review

- Spec coverage: The plan covers the migration matrix, safety gates, catalog split, category migration, advisory experimental handling, tests, read-only verification, and separate v2 packaging.
- Placeholder scan: No TBD/TODO placeholders remain; every task has concrete paths, snippets, commands, and expected results.
- Type consistency: `legacy_ids`, `validate_plan_for_apply`, `PlanValidationError`, `AdvisoryAction`, and status names are used consistently across tasks.
- Scope note: The full 73-item matrix requires careful old-code extraction. The plan intentionally requires the matrix before broad catalog migration so no old item disappears silently.
