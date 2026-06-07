from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any


class FakeScheduledTaskBackend:
    def __init__(self):
        self.tasks: dict[str, dict[str, Any]] = {}

    def add_task(self, path: str, enabled: bool) -> None:
        self.tasks[path] = {"exists": True, "enabled": enabled}

    def get(self, path: str) -> dict[str, Any] | None:
        task = self.tasks.get(path)
        return dict(task) if task is not None else None

    def set_enabled(self, path: str, enabled: bool) -> None:
        if path in self.tasks:
            self.tasks[path]["enabled"] = enabled


class WindowsScheduledTaskBackend:
    def get(self, path: str) -> dict[str, Any] | None:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", path, "/FO", "LIST", "/V"],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="ignore",
        )
        if result.returncode != 0:
            return None
        text = result.stdout.lower()
        disabled = "disabled" in text or "已禁用" in text
        return {"exists": True, "enabled": not disabled}

    def set_enabled(self, path: str, enabled: bool) -> None:
        state = "/ENABLE" if enabled else "/DISABLE"
        subprocess.run(
            ["schtasks", "/Change", "/TN", path, state],
            check=True,
            capture_output=True,
            encoding="gbk",
            errors="ignore",
        )


@dataclass(frozen=True)
class ScheduledTaskSetEnabledAction:
    path: str
    enabled: bool

    @property
    def action_id(self) -> str:
        return f"scheduled_task:{self.path}:enabled"

    @property
    def action_type(self) -> str:
        return "scheduled_task_enabled"

    @property
    def target(self) -> str:
        return self.path

    def current(self, backend) -> dict[str, Any]:
        current = backend.get(self.path)
        if current is None:
            return {"exists": False, "enabled": None}
        return current

    def desired(self) -> dict[str, Any]:
        return {"exists": True, "enabled": self.enabled}

    def apply(self, backend) -> dict[str, Any]:
        before = self.current(backend)
        if not before.get("exists"):
            return {"action_id": self.action_id, "action_type": self.action_type, "target": self.target, "before": before, "after": before}
        backend.set_enabled(self.path, self.enabled)
        after = self.current(backend)
        return {"action_id": self.action_id, "action_type": self.action_type, "target": self.target, "before": before, "after": after}

    def verify(self, backend) -> dict[str, Any]:
        current = self.current(backend)
        if not current.get("exists"):
            return {"status": "skipped", "current": current, "expected": self.desired()}
        passed = current.get("enabled") == self.enabled
        return {"status": "passed" if passed else "failed", "current": current, "expected": self.desired()}

    def rollback(self, backend, before: dict[str, Any]) -> None:
        if not before.get("exists"):
            return
        backend.set_enabled(self.path, before["enabled"])
