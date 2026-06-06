from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any

_START_TO_REG = {"boot": 0, "system": 1, "auto": 2, "manual": 3, "disabled": 4}
_REG_TO_START = {value: key for key, value in _START_TO_REG.items()}


class FakeServiceBackend:
    def __init__(self):
        self.services: dict[str, dict[str, Any]] = {}

    def add_service(self, name: str, start_type: str, running: bool) -> None:
        self.services[name] = {"exists": True, "start_type": start_type, "running": running}

    def get(self, name: str) -> dict[str, Any] | None:
        value = self.services.get(name)
        return dict(value) if value is not None else None

    def set_start_type(self, name: str, start_type: str) -> None:
        if name in self.services:
            self.services[name]["start_type"] = start_type

    def stop(self, name: str) -> None:
        if name in self.services:
            self.services[name]["running"] = False

    def start(self, name: str) -> None:
        if name in self.services:
            self.services[name]["running"] = True


class WindowsServiceBackend:
    def get(self, name: str) -> dict[str, Any] | None:
        from haoyue_optimizer.core.registry import WindowsRegistryBackend

        reg = WindowsRegistryBackend()
        start = reg.read("HKLM", rf"SYSTEM\CurrentControlSet\Services\{name}", "Start")
        if start is None:
            return None
        running = _query_running(name)
        return {"exists": True, "start_type": _REG_TO_START.get(start["value"], "unknown"), "running": running}

    def set_start_type(self, name: str, start_type: str) -> None:
        mode = {"auto": "auto", "manual": "demand", "disabled": "disabled"}[start_type]
        subprocess.run(["sc", "config", name, "start=", mode], check=True, capture_output=True)

    def stop(self, name: str) -> None:
        subprocess.run(["sc", "stop", name], capture_output=True)

    def start(self, name: str) -> None:
        subprocess.run(["sc", "start", name], capture_output=True)


def _query_running(name: str) -> bool:
    result = subprocess.run(["sc", "query", name], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return "RUNNING" in result.stdout


@dataclass(frozen=True)
class ServiceStartTypeAction:
    name: str
    start_type: str
    stop: bool = False

    @property
    def action_id(self) -> str:
        return f"service:{self.name}:start_type"

    @property
    def action_type(self) -> str:
        return "service_start_type"

    @property
    def target(self) -> str:
        return self.name

    def current(self, backend) -> dict[str, Any]:
        current = backend.get(self.name)
        if current is None:
            return {"exists": False, "start_type": None, "running": False}
        return current

    def desired(self) -> dict[str, Any]:
        return {"exists": True, "start_type": self.start_type, "running": False if self.stop else None}

    def apply(self, backend) -> dict[str, Any]:
        before = self.current(backend)
        if not before.get("exists"):
            return {"action_id": self.action_id, "action_type": self.action_type, "target": self.target, "before": before, "after": before}
        if self.stop:
            backend.stop(self.name)
        backend.set_start_type(self.name, self.start_type)
        after = self.current(backend)
        return {"action_id": self.action_id, "action_type": self.action_type, "target": self.target, "before": before, "after": after}

    def verify(self, backend) -> dict[str, Any]:
        current = self.current(backend)
        if not current.get("exists"):
            return {"status": "skipped", "current": current, "expected": self.desired()}
        passed = current.get("start_type") == self.start_type
        if self.stop:
            passed = passed and not current.get("running")
        return {"status": "passed" if passed else "failed", "current": current, "expected": self.desired()}

    def rollback(self, backend, before: dict[str, Any]) -> None:
        if not before.get("exists"):
            return
        backend.set_start_type(self.name, before["start_type"])
        if before.get("running"):
            backend.start(self.name)
        else:
            backend.stop(self.name)
