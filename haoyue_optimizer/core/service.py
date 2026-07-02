from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any

from haoyue_optimizer.core.compat import (
    OPTIONAL_SERVICES_MAY_NOT_EXIST,
    STORE_SAFE_PROTECTED_SERVICES,
    is_service_disabled,
)

_START_TO_REG = {"boot": 0, "system": 1, "auto": 2, "manual": 3, "disabled": 4}
_REG_TO_START = {value: key for key, value in _START_TO_REG.items()}


class ServiceNotModifiable(Exception):
    """Raised when a service cannot be modified (e.g. wscsvc with Tamper Protection)."""


class StoreSafeBlocked(Exception):
    """Raised when an operation is blocked by the Store-safe guard."""


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
        try:
            start = reg.read("HKLM", rf"SYSTEM\CurrentControlSet\Services\{name}", "Start")
        except OSError:
            return None
        if start is None:
            return None
        running = _query_running(name)
        return {"exists": True, "start_type": _REG_TO_START.get(start["value"], "unknown"), "running": running}

    def set_start_type(self, name: str, start_type: str) -> None:
        mode = {"auto": "auto", "manual": "demand", "disabled": "disabled"}[start_type]
        try:
            subprocess.run(["sc", "config", name, "start=", mode], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            import winreg
            reg_val = {"auto": 2, "manual": 3, "disabled": 4}[start_type]
            _W64 = getattr(winreg, "KEY_WOW64_64KEY", 0)
            try:
                with winreg.CreateKeyEx(
                    winreg.HKEY_LOCAL_MACHINE,
                    rf"SYSTEM\CurrentControlSet\Services\{name}",
                    0,
                    winreg.KEY_WRITE | _W64,
                ) as key:
                    winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, reg_val)
            except OSError:
                raise ServiceNotModifiable(f"{name}: sc config and registry write both denied")

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

    # ── skip / block result markers (set by apply) ──
    _skip_reason: str | None = None
    _block_reason: str | None = None

    @property
    def action_id(self) -> str:
        return f"service:{self.name}:start_type"

    @property
    def action_type(self) -> str:
        return "service_start_type"

    @property
    def target(self) -> str:
        return self.name

    # ── guard helpers ──

    @staticmethod
    def _service_exists(name: str, backend) -> bool:
        current = backend.get(name)
        return current is not None and current.get("exists", False) is True

    @staticmethod
    def _is_store_safe_protected(name: str) -> bool:
        return name.strip() in STORE_SAFE_PROTECTED_SERVICES

    @staticmethod
    def _is_forbidden_action(start_type: str, stop: bool) -> bool:
        """Block any action that would disable or stop a store-safe service."""
        if is_service_disabled(start_type):
            return True
        if stop:
            return True
        return False

    @staticmethod
    def _skip_missing(name: str) -> str | None:
        """Return a skip reason when a service is missing and should be skipped
        silently.  Return None when the service is expected to exist."""
        if name in OPTIONAL_SERVICES_MAY_NOT_EXIST:
            return "optional_service_not_present"
        return "service_not_present"

    # ── action protocol ──

    def current(self, backend) -> dict[str, Any]:
        current = backend.get(self.name)
        if current is None:
            return {"exists": False, "start_type": None, "running": False}
        return current

    def desired(self) -> dict[str, Any]:
        return {"exists": True, "start_type": self.start_type, "running": False if self.stop else None}

    def apply(self, backend) -> dict[str, Any]:
        before = self.current(backend)

        # 1. Missing service → skip
        if not before.get("exists"):
            skip_reason = self._skip_missing(self.name)
            return {
                "action_id": self.action_id,
                "action_type": self.action_type,
                "target": self.target,
                "before": before,
                "after": None,
                "verify": {"status": "skipped", "detail": f"{skip_reason}:{self.name}"},
            }

        # 2. Store-safe protection → block
        if self._is_store_safe_protected(self.name) and self._is_forbidden_action(self.start_type, self.stop):
            return {
                "action_id": self.action_id,
                "action_type": self.action_type,
                "target": self.target,
                "before": before,
                "after": None,
                "verify": {"status": "blocked", "detail": f"store_safe_protected:{self.name}"},
            }

        # 3. Proceed normally
        try:
            if self.stop:
                backend.stop(self.name)
            backend.set_start_type(self.name, self.start_type)
        except StoreSafeBlocked:
            return {
                "action_id": self.action_id,
                "action_type": self.action_type,
                "target": self.target,
                "before": before,
                "after": None,
                "verify": {"status": "blocked", "detail": f"store_safe_protected:{self.name}"},
            }

        after = self.current(backend)
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target": self.target,
            "before": before,
            "after": after,
        }

    def verify(self, backend) -> dict[str, Any]:
        current = self.current(backend)
        if not current.get("exists"):
            return {"status": "skipped", "current": current, "expected": self.desired(),
                    "detail": "service_not_present"}
        passed = current.get("start_type") == self.start_type
        if self.stop and not passed:
            passed = False
        elif self.stop and passed and current.get("running"):
            pass
        return {"status": "passed" if passed else "failed", "current": current, "expected": self.desired()}

    def rollback(self, backend, before: dict[str, Any]) -> None:
        if not before.get("exists"):
            return
        backend.set_start_type(self.name, before["start_type"])
        if before.get("running"):
            backend.start(self.name)
        else:
            backend.stop(self.name)


# ── Repair / utility functions ──


def repair_store_safe_services(backend=None) -> list[dict[str, Any]]:
    """Restore any store-safe services that are currently Disabled to their
    recommended start types.  Only restores Disabled → recommended; never
    forces a running service to stop.

    Returns a list of repair records: {service, before, after, status}.
    """
    from haoyue_optimizer.core.compat import STORE_SAFE_DEFAULT_START_TYPES

    backend = backend or WindowsServiceBackend()
    repairs: list[dict[str, Any]] = []

    for svc, desired_start in sorted(STORE_SAFE_DEFAULT_START_TYPES.items()):
        current = backend.get(svc)
        if current is None or not current.get("exists"):
            continue
        current_start = current.get("start_type")
        if current_start == "disabled":
            try:
                backend.set_start_type(svc, desired_start)
                repairs.append({
                    "service": svc,
                    "before": "disabled",
                    "after": desired_start,
                    "status": "repaired",
                })
            except (ServiceNotModifiable, StoreSafeBlocked, OSError) as exc:
                repairs.append({
                    "service": svc,
                    "before": "disabled",
                    "after": desired_start,
                    "status": "failed",
                    "detail": str(exc),
                })

    return repairs
