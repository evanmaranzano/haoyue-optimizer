from __future__ import annotations

import winreg
from dataclasses import dataclass
from typing import Any

_ROOTS = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
}
_W64 = getattr(winreg, "KEY_WOW64_64KEY", 0)
_VALUE_TYPES = {
    "dword": winreg.REG_DWORD,
    "sz": winreg.REG_SZ,
    "binary": winreg.REG_BINARY,
}


class FakeRegistryBackend:
    def __init__(self):
        self.values: dict[tuple[str, str, str], dict[str, Any]] = {}

    def read(self, root: str, path: str, name: str) -> dict[str, Any] | None:
        value = self.values.get((root, path, name))
        return dict(value) if value is not None else None

    def write(self, root: str, path: str, name: str, value: Any, value_type: str) -> None:
        self.values[(root, path, name)] = {"value": value, "value_type": value_type}

    def delete(self, root: str, path: str, name: str) -> None:
        self.values.pop((root, path, name), None)


class WindowsRegistryBackend:
    def read(self, root: str, path: str, name: str) -> dict[str, Any] | None:
        try:
            with winreg.OpenKey(_ROOTS[root], path, 0, winreg.KEY_READ | _W64) as key:
                value, kind = winreg.QueryValueEx(key, name)
                return {"value": value, "value_type": _kind_to_name(kind)}
        except (FileNotFoundError, OSError):
            return None

    def write(self, root: str, path: str, name: str, value: Any, value_type: str) -> None:
        with winreg.CreateKeyEx(_ROOTS[root], path, 0, winreg.KEY_WRITE | _W64) as key:
            winreg.SetValueEx(key, name, 0, _VALUE_TYPES[value_type], value)

    def delete(self, root: str, path: str, name: str) -> None:
        try:
            with winreg.OpenKey(_ROOTS[root], path, 0, winreg.KEY_WRITE | _W64) as key:
                winreg.DeleteValue(key, name)
        except (FileNotFoundError, OSError):
            return


def _kind_to_name(kind: int) -> str:
    for name, value in _VALUE_TYPES.items():
        if value == kind:
            return name
    return "unknown"


@dataclass(frozen=True)
class RegistrySetAction:
    root: str
    path: str
    name: str
    value: Any
    value_type: str = "dword"
    qualifier: str = ""

    @property
    def action_id(self) -> str:
        base = f"registry:{self.target}"
        return f"{self.qualifier}:{base}" if self.qualifier else base

    @property
    def action_type(self) -> str:
        return "registry_set"

    @property
    def target(self) -> str:
        return f"{self.root}\\{self.path}\\{self.name}"

    def current(self, backend) -> dict[str, Any]:
        current = backend.read(self.root, self.path, self.name)
        if current is None:
            return {"exists": False, "value": None, "value_type": self.value_type}
        return {"exists": True, **current}

    def desired(self) -> dict[str, Any]:
        return {"exists": True, "value": self.value, "value_type": self.value_type}

    def apply(self, backend) -> dict[str, Any]:
        before = self.current(backend)
        backend.write(self.root, self.path, self.name, self.value, self.value_type)
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
        passed = current.get("exists") and current.get("value") == self.value
        return {"status": "passed" if passed else "failed", "current": current, "expected": self.desired()}

    def rollback(self, backend, before: dict[str, Any]) -> None:
        if before.get("exists"):
            backend.write(self.root, self.path, self.name, before.get("value"), before.get("value_type", self.value_type))
        else:
            backend.delete(self.root, self.path, self.name)
