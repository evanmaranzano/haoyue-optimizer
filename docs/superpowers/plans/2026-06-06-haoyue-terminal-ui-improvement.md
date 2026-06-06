# Haoyue Terminal UI Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the v2 terminal interaction at least as usable as the v1 single-file tool while preserving v2 safety guarantees, auditability, and plan/apply/rollback workflow.

**Architecture:** Split interactive UI out of `haoyue_optimizer/main.py` into a focused `haoyue_optimizer/ui/` package. Keep `main.py` responsible for argparse commands only; `ui.cli.run_interactive()` owns menus, scans, custom selection, confirmation, apply, rollback, and report presentation. Reuse existing `build_plan()`, `validate_plan_for_apply()`, `apply_plan()`, `rollback_backup()`, and `export_report()` instead of duplicating system-write logic.

**Tech Stack:** Python stdlib only, unittest, PyInstaller, existing Haoyue action/planner/executor modules.

---

## File Map

### Create

- `C:/Users/Administrator/haoyue_optimizer/ui/__init__.py` — UI package marker.
- `C:/Users/Administrator/haoyue_optimizer/ui/format.py` — colors, banner, risk coloring, table/list formatting, pause/clear helpers.
- `C:/Users/Administrator/haoyue_optimizer/ui/selection.py` — preset selection, numbered item selection, plan file selection.
- `C:/Users/Administrator/haoyue_optimizer/ui/scan.py` — derive applied/missing/skipped/advisory buckets from a plan's action current/desired values.
- `C:/Users/Administrator/haoyue_optimizer/ui/cli.py` — interactive menu flow.
- `C:/Users/Administrator/tests/test_ui_scan.py` — pure tests for scan classification.
- `C:/Users/Administrator/tests/test_ui_selection.py` — pure tests for custom selection parsing.
- `C:/Users/Administrator/tests/test_ui_cli_smoke.py` — subprocess/argument smoke tests for no-arg help/menu-safe paths if practical.

### Modify

- `C:/Users/Administrator/haoyue_optimizer/main.py` — remove large interactive helper code; call `run_interactive()` when no args.
- `C:/Users/Administrator/皓月定制优化工具-v2.spec` — no path changes expected, but rebuild after code changes.

### Preserve

- `C:/Users/Administrator/Desktop/皓月定制优化工具.py` — v1 reference only, do not edit.
- `C:/Users/Administrator/dist/皓月定制优化工具.exe` — legacy exe, do not overwrite.
- `C:/Users/Administrator/dist/皓月定制优化工具-v1-legacy.exe` — legacy backup, do not overwrite unless explicitly backing up again.

---

## UX Requirements

### Main menu must look and behave like a polished v1+ tool

Menu:

```text
╔══════════════════════════════════════════════════╗
║          皓月定制优化工具  v2.0.0-alpha          ║
║        Haoyue System Optimizer v2               ║
╚══════════════════════════════════════════════════╝

主菜单 [管理员]
────────────────────────────────────────────────
  1  扫描系统 + 智能补充缺失项
  2  一键应用 safe 方案
  3  自定义选择优化项
  4  生成 / 查看 JSON 计划
  5  查看全部优化项
  6  恢复备份
  7  系统体检 doctor
  8  预设说明
  0  退出
```

### Safety requirements

- Any interactive apply path must call `validate_plan_for_apply()` before `apply_plan()`.
- `experimental` must never be applied through normal menu choices.
- Applying experimental requires a dedicated high-risk menu path, `allow_experimental=True`, typing `EXPERIMENTAL`, then typing `APPLY`.
- Non-admin launch should show a clear admin message and pause before exit.
- Menu must not silently overwrite plan files; if a target plan file exists, create a timestamped filename.
- File cleanup (`temp_clean`) must remain age-filtered and locked-file-safe.

---

## Task 1: Create UI formatting module

**Files:**
- Create: `C:/Users/Administrator/haoyue_optimizer/ui/__init__.py`
- Create: `C:/Users/Administrator/haoyue_optimizer/ui/format.py`

- [ ] **Step 1: Create package marker**

Create `ui/__init__.py`:

```python
"""Interactive terminal UI for Haoyue optimizer."""
```

- [ ] **Step 2: Create formatting helpers**

Create `ui/format.py`:

```python
from __future__ import annotations

import os
import subprocess

from haoyue_optimizer import VERSION

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

RISK_COLORS = {"green": GREEN, "yellow": YELLOW, "red": RED}


def clear_screen() -> None:
    subprocess.run(["cmd", "/c", "cls"] if os.name == "nt" else ["clear"])


def pause() -> None:
    input(f"\n  {DIM}按回车继续...{RESET}")


def risk_color(risk: str) -> str:
    return RISK_COLORS.get(risk, RESET)


def banner() -> str:
    return f"""
{CYAN}{BOLD}  ╔══════════════════════════════════════════════════╗
  ║          皓月定制优化工具  v{VERSION:<10s}             ║
  ║        Haoyue System Optimizer v2                 ║
  ╚══════════════════════════════════════════════════╝{RESET}
"""


def print_banner() -> None:
    print(banner())


def section(title: str) -> str:
    return f"\n  {BOLD}{title}{RESET}\n  {'─' * 48}"


def risk_label(risk: str) -> str:
    color = risk_color(risk)
    return f"{color}[{risk:8s}]{RESET}"
```

- [ ] **Step 3: No tests required for ANSI constants**

Run existing tests later in Task 7.

---

## Task 2: Add scan classification logic

**Files:**
- Create: `C:/Users/Administrator/haoyue_optimizer/ui/scan.py`
- Create: `C:/Users/Administrator/tests/test_ui_scan.py`

- [ ] **Step 1: Write scan tests**

Create `tests/test_ui_scan.py`:

```python
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
```

- [ ] **Step 2: Create scan module**

Create `ui/scan.py`:

```python
from __future__ import annotations

from typing import Any


def classify_action(action: dict[str, Any]) -> str:
    action_type = action.get("type")
    if action_type in {"advisory", "file_cleanup"}:
        return "advisory"
    current = action.get("current", {})
    desired = action.get("desired", {})
    if _matches(current, desired):
        return "applied"
    return "missing"


def _matches(current: dict[str, Any], desired: dict[str, Any]) -> bool:
    if "exists" in desired and current.get("exists") != desired.get("exists"):
        return False
    if "value" in desired and current.get("value") != desired.get("value"):
        return False
    if "ac" in desired and current.get("ac") != desired.get("ac"):
        return False
    if "dc" in desired and current.get("dc") != desired.get("dc"):
        return False
    if "enabled" in desired and current.get("enabled") != desired.get("enabled"):
        return False
    if "start_type" in desired and current.get("start_type") != desired.get("start_type"):
        return False
    return True


def summarize_plan_status(plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result = {"applied": [], "missing": [], "advisory": []}
    for item in plan.get("items", []):
        action_statuses = [classify_action(action) for action in item.get("actions", [])]
        if action_statuses and all(status == "applied" for status in action_statuses):
            result["applied"].append(item)
        elif action_statuses and all(status == "advisory" for status in action_statuses):
            result["advisory"].append(item)
        else:
            result["missing"].append(item)
    return result
```

- [ ] **Step 3: Run scan tests**

Run:

```powershell
python -m unittest C:/Users/Administrator/tests/test_ui_scan.py -v
```

Expected: 4 tests pass.

---

## Task 3: Add selection parsing

**Files:**
- Create: `C:/Users/Administrator/haoyue_optimizer/ui/selection.py`
- Create: `C:/Users/Administrator/tests/test_ui_selection.py`

- [ ] **Step 1: Write selection tests**

Create `tests/test_ui_selection.py`:

```python
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
```

- [ ] **Step 2: Create selection module**

Create `ui/selection.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from haoyue_optimizer.main import PRESETS
from haoyue_optimizer.ui.format import CYAN, DIM, GREEN, RESET


def parse_selection(raw: str, total: int, items: list[dict[str, Any]] | None = None) -> list[int]:
    raw = raw.strip().lower()
    if raw == "all":
        return list(range(total))
    if raw == "safe" and items is not None:
        return [i for i, item in enumerate(items) if item.get("risk") == "green"]
    selected: list[int] = []
    seen = set()
    for part in raw.split(","):
        part = part.strip()
        if not part.isdigit():
            continue
        index = int(part) - 1
        if 0 <= index < total and index not in seen:
            selected.append(index)
            seen.add(index)
    return selected


def ask_preset() -> str | None:
    print("\n  选择预设:")
    presets = list(PRESETS.keys())
    for i, name in enumerate(presets, 1):
        print(f"    {GREEN}{i}{RESET}  {CYAN}{name}{RESET}  {DIM}{PRESETS[name]}{RESET}")
    choice = input("\n  选择编号 (回车取消): ").strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(presets):
        return None
    return presets[int(choice) - 1]


def newest_plan_files(limit: int = 10) -> list[Path]:
    return sorted(Path.cwd().glob("*-plan.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
```

- [ ] **Step 3: Run selection tests**

Run:

```powershell
python -m unittest C:/Users/Administrator/tests/test_ui_selection.py -v
```

Expected: 4 tests pass.

---

## Task 4: Move interactive menu into ui.cli

**Files:**
- Create: `C:/Users/Administrator/haoyue_optimizer/ui/cli.py`
- Modify: `C:/Users/Administrator/haoyue_optimizer/main.py`

- [ ] **Step 1: Create cli module with menu skeleton**

Create `ui/cli.py` containing `run_interactive()`, but initially keep behavior minimal:

```python
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from haoyue_optimizer import VERSION
from haoyue_optimizer.core.admin import is_admin
from haoyue_optimizer.core.backup import backup_root, read_backup
from haoyue_optimizer.core.executor import apply_plan, rollback_backup
from haoyue_optimizer.core.planner import build_plan
from haoyue_optimizer.core.report import export_report
from haoyue_optimizer.core.validation import PlanValidationError, validate_plan_for_apply
from haoyue_optimizer.ui.format import BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW, banner, clear_screen, pause, risk_label, section
from haoyue_optimizer.ui.scan import summarize_plan_status
from haoyue_optimizer.ui.selection import ask_preset, newest_plan_files, parse_selection


def run_interactive() -> int:
    clear_screen()
    print(banner())
    if not is_admin():
        print(f"  {RED}请以管理员身份运行此工具！{RESET}")
        print("  右键点击 → 以管理员身份运行")
        pause()
        return 1
    while True:
        print_main_menu()
        choice = input(f"  选择 [{GREEN}1-8{RESET}, {DIM}0{RESET}]: ").strip()
        if choice == "0":
            print(f"\n  {DIM}退出。{RESET}")
            return 0
        if choice == "1":
            scan_and_supplement()
        elif choice == "2":
            apply_preset("safe")
        elif choice == "3":
            custom_select()
        elif choice == "4":
            generate_plan()
        elif choice == "5":
            show_items()
        elif choice == "6":
            rollback_menu()
        elif choice == "7":
            print(section("系统体检"))
            print_doctor()
        elif choice == "8":
            show_presets()
        else:
            print(f"  {DIM}无效选项{RESET}")
        pause()


def print_main_menu() -> None:
    print(section("主菜单 [管理员]"))
    print(f"    {GREEN}1{RESET}  扫描系统 + 智能补充缺失项")
    print(f"    {GREEN}2{RESET}  一键应用 safe 方案")
    print(f"    {YELLOW}3{RESET}  自定义选择优化项")
    print(f"    {CYAN}4{RESET}  生成 / 查看 JSON 计划")
    print(f"    {CYAN}5{RESET}  查看全部优化项")
    print(f"    {RED}6{RESET}  恢复备份")
    print(f"    {DIM}7{RESET}  系统体检 doctor")
    print(f"    {DIM}8{RESET}  预设说明")
    print(f"    {DIM}0{RESET}  退出")
    print()
```

Continue in the same file by moving the existing helper flows from `main.py` into `ui.cli`, then adjust them in later tasks.

- [ ] **Step 2: Modify main.py to delegate no-arg mode**

In `main.py`, import:

```python
from haoyue_optimizer.ui.cli import run_interactive
```

Then replace:

```python
if argv is None and len(sys.argv) == 1:
    return _interactive_menu()
```

with:

```python
if argv is None and len(sys.argv) == 1:
    return run_interactive()
```

Remove old interactive helper functions from `main.py` after they exist in `ui.cli`.

- [ ] **Step 3: Run existing CLI tests**

Run:

```powershell
python -m unittest discover -s C:/Users/Administrator/tests -t C:/Users/Administrator -v
```

Expected: all tests pass.

---

## Task 5: Implement real scan + smart supplement flow

**Files:**
- Modify: `C:/Users/Administrator/haoyue_optimizer/ui/cli.py`
- Test: `C:/Users/Administrator/tests/test_ui_scan.py`

- [ ] **Step 1: Use summarize_plan_status in scan flow**

Implement `scan_and_supplement()` in `ui.cli`:

```python
def scan_and_supplement() -> None:
    clear_screen()
    print(banner())
    preset = ask_preset()
    if not preset:
        return
    plan = build_plan(preset)
    summary = summarize_plan_status(plan)
    print_scan_summary(preset, summary)
    if not summary["missing"]:
        print(f"\n  {GREEN}没有缺失项。{RESET}")
        return
    if preset == "experimental":
        print(f"\n  {RED}experimental 不能通过智能补充直接应用，请生成计划后走高风险流程。{RESET}")
        return
    confirm = input(f"\n  是否补充缺失项？[{GREEN}y{RESET}/{DIM}N{RESET}]: ").strip().lower()
    if confirm != "y":
        print(f"  {YELLOW}已取消{RESET}")
        return
    missing_plan = {**plan, "items": summary["missing"]}
    execute_plan(missing_plan, allow_experimental=False)
```

- [ ] **Step 2: Add print_scan_summary helper**

```python
def print_scan_summary(preset: str, summary: dict) -> None:
    print(section(f"扫描结果: {preset}"))
    print(f"  {GREEN}已生效: {len(summary['applied'])}{RESET}")
    for item in summary["applied"][:20]:
        print(f"    {GREEN}✓{RESET} {item['title']}")
    print(f"\n  {YELLOW}缺失: {len(summary['missing'])}{RESET}")
    for item in summary["missing"][:30]:
        print(f"    {YELLOW}✗{RESET} {item['title']}")
    print(f"\n  {DIM}提示项: {len(summary['advisory'])}{RESET}")
    for item in summary["advisory"][:20]:
        print(f"    {DIM}! {item['title']}{RESET}")
```

- [ ] **Step 3: Verify no experimental direct apply path**

Manually inspect `scan_and_supplement()`: experimental must return before `execute_plan()`.

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest C:/Users/Administrator/tests/test_ui_scan.py -v
python -m unittest discover -s C:/Users/Administrator/tests -t C:/Users/Administrator -v
```

Expected: all tests pass.

---

## Task 6: Implement custom numbered selection

**Files:**
- Modify: `C:/Users/Administrator/haoyue_optimizer/ui/cli.py`
- Test: `C:/Users/Administrator/tests/test_ui_selection.py`

- [ ] **Step 1: Implement item list printer**

In `ui.cli`:

```python
def print_items(items: list[dict]) -> None:
    by_cat: dict[str, list[tuple[int, dict]]] = {}
    for i, item in enumerate(items):
        by_cat.setdefault(item.get("category", "other"), []).append((i, item))
    for cat, entries in by_cat.items():
        print(f"\n  {BOLD}[{cat}]{RESET}")
        for i, item in entries:
            print(f"    {DIM}{i + 1:3d}{RESET}  {risk_label(item['risk'])}  {item['title']}")
```

- [ ] **Step 2: Implement custom_select()**

```python
def custom_select() -> None:
    clear_screen()
    print(banner())
    preset = ask_preset()
    if not preset:
        return
    if preset == "experimental":
        print(f"\n  {RED}experimental 需要走高风险计划流程，不能在普通自定义选择中直接应用。{RESET}")
        return
    plan = build_plan(preset)
    print(section(f"自定义选择: {preset}"))
    print_items(plan["items"])
    raw = input(f"\n  输入编号（如 1,3,5），{GREEN}all{RESET} 全选，{GREEN}safe{RESET} 只选 green: ").strip()
    indices = parse_selection(raw, len(plan["items"]), plan["items"])
    if not indices:
        print(f"  {YELLOW}没有选中任何优化项{RESET}")
        return
    selected_items = [plan["items"][i] for i in indices]
    selected_plan = {**plan, "items": selected_items}
    execute_plan(selected_plan, allow_experimental=False)
```

- [ ] **Step 3: Run selection tests and full tests**

Run:

```powershell
python -m unittest C:/Users/Administrator/tests/test_ui_selection.py -v
python -m unittest discover -s C:/Users/Administrator/tests -t C:/Users/Administrator -v
```

Expected: all tests pass.

---

## Task 7: Implement safe apply and high-risk experimental flow

**Files:**
- Modify: `C:/Users/Administrator/haoyue_optimizer/ui/cli.py`

- [ ] **Step 1: Implement execute_plan() wrapper**

```python
def execute_plan(plan: dict, allow_experimental: bool) -> None:
    try:
        summary = validate_plan_for_apply(plan, allow_experimental=allow_experimental)
    except PlanValidationError as exc:
        print(f"\n  {RED}计划校验失败: {exc}{RESET}")
        return
    print(format_apply_summary(summary))
    if summary["has_experimental"]:
        token = input(f"\n  输入 {RED}EXPERIMENTAL{RESET} 确认进入高风险执行: ").strip()
        if token != "EXPERIMENTAL":
            print(f"  {YELLOW}已取消{RESET}")
            return
    confirm = input(f"\n  输入 {RED}APPLY{RESET} 确认执行: ").strip()
    if confirm != "APPLY":
        print(f"  {YELLOW}已取消{RESET}")
        return
    backup = apply_plan(plan)
    report_path = export_report(plan, backup)
    print_execution_result(backup, report_path)
```

- [ ] **Step 2: Implement apply_preset()**

```python
def apply_preset(preset: str) -> None:
    clear_screen()
    print(banner())
    plan = build_plan(preset)
    print_scan_summary(preset, summarize_plan_status(plan))
    execute_plan(plan, allow_experimental=False)
```

- [ ] **Step 3: Add experimental menu path only if desired**

Do not add high-risk apply to the main menu yet. Generate experimental plan via menu 4; CLI users can still use `--allow-experimental` explicitly.

- [ ] **Step 4: Run full tests**

Run:

```powershell
python -m unittest discover -s C:/Users/Administrator/tests -t C:/Users/Administrator -v
```

Expected: all tests pass.

---

## Task 8: Improve plan generation and rollback UX

**Files:**
- Modify: `C:/Users/Administrator/haoyue_optimizer/ui/cli.py`

- [ ] **Step 1: Generate timestamped plan files**

Implement:

```python
def plan_output_path(preset: str) -> Path:
    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path.cwd() / f"{preset}-plan-{stamp}.json"
```

Use it in `generate_plan()` so no existing plan gets overwritten.

- [ ] **Step 2: Rollback menu should show size and mtime**

Use backup files from `backup_root()` sorted by mtime, print top 10 with filename and KB size.

- [ ] **Step 3: Run full tests**

Run:

```powershell
python -m unittest discover -s C:/Users/Administrator/tests -t C:/Users/Administrator -v
```

Expected: all tests pass.

---

## Task 9: Final verification and rebuild exe

**Files:**
- Modify build output only: `C:/Users/Administrator/dist/皓月定制优化工具-v2.exe`

- [ ] **Step 1: Run full tests**

Run:

```powershell
python -m unittest discover -s C:/Users/Administrator/tests -t C:/Users/Administrator -v
```

Expected:

```text
Ran 32+ tests
OK
```

- [ ] **Step 2: Smoke test no-arg import path**

Do not launch an interactive subprocess that hangs. Instead verify CLI commands still work:

```powershell
python -m haoyue_optimizer.main presets
python -m haoyue_optimizer.main doctor
python -m haoyue_optimizer.main plan --preset safe --out C:/Users/Administrator/safe-plan-ui-test.json
```

Expected: all return 0.

- [ ] **Step 3: Rebuild v2 exe**

Run:

```powershell
C:/Users/Administrator/build_env/Scripts/pyinstaller.exe C:/Users/Administrator/皓月定制优化工具-v2.spec --distpath C:/Users/Administrator/dist --workpath C:/Users/Administrator/build
```

Expected: build succeeds and updates:

```text
C:/Users/Administrator/dist/皓月定制优化工具-v2.exe
```

- [ ] **Step 4: Smoke test rebuilt exe**

Run:

```powershell
C:/Users/Administrator/dist/皓月定制优化工具-v2.exe presets
C:/Users/Administrator/dist/皓月定制优化工具-v2.exe doctor
```

Expected: both return 0.

---

## Self-Review

- Spec coverage: Plan covers UI split, scan+smart supplement, custom selection, safe apply, experimental gating, plan no-overwrite, rollback UX, tests, and rebuild.
- Placeholder scan: No TODO/TBD placeholders. Each task has exact files, code, commands, expected results.
- Type consistency: `run_interactive`, `summarize_plan_status`, `parse_selection`, `execute_plan`, and `plan_output_path` are consistently named.
- Safety: All interactive apply paths go through `validate_plan_for_apply`; experimental direct application is blocked from normal menu flow.
