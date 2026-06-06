from __future__ import annotations

from pathlib import Path
from typing import Any

from haoyue_optimizer import PRESETS
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
    print(f"\n  {CYAN}选择预设:{RESET}")
    presets = list(PRESETS.keys())
    for i, name in enumerate(presets, 1):
        print(f"    {GREEN}{i}{RESET}  {CYAN}{name}{RESET}  {DIM}{PRESETS[name]}{RESET}")
    choice = input("\n  选择编号 (回车取消): ").strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(presets):
        return None
    return presets[int(choice) - 1]


def newest_plan_files(limit: int = 10) -> list[Path]:
    return sorted(Path.cwd().glob("*-plan.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
