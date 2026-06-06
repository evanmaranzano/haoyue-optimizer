from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Any


class FakePowerBackend:
    def __init__(self, active_scheme: str = "SCHEME_CURRENT"):
        self.active_scheme = active_scheme
        self.values: dict[tuple[str, str, str], dict[str, int]] = {}

    def get_active_scheme(self) -> str:
        return self.active_scheme

    def set_active_scheme(self, scheme: str) -> None:
        self.active_scheme = scheme

    def get_value(self, scheme: str, subgroup: str, setting: str) -> dict[str, int]:
        return dict(self.values.get((scheme, subgroup, setting), {"ac": 0, "dc": 0}))

    def set_value(self, scheme: str, subgroup: str, setting: str, ac: int, dc: int) -> None:
        self.values[(scheme, subgroup, setting)] = {"ac": ac, "dc": dc}


class WindowsPowerBackend:
    def get_active_scheme(self) -> str:
        result = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True)
        match = re.search(rb"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", result.stdout)
        return match.group(1).decode("ascii") if match else "SCHEME_CURRENT"

    def set_active_scheme(self, scheme: str) -> None:
        subprocess.run(["powercfg", "/setactive", scheme], check=True, capture_output=True)

    def get_value(self, scheme: str, subgroup: str, setting: str) -> dict[str, int]:
        result = subprocess.run(["powercfg", "/query", scheme, subgroup, setting], capture_output=True)
        text = result.stdout.decode("gbk", errors="replace")
        matches = re.findall(r"当前(?:交流|直流).*?:\s*(0x[0-9a-fA-F]+)", text)
        if len(matches) >= 2:
            return {"ac": int(matches[0], 16), "dc": int(matches[1], 16)}
        return {"ac": 0, "dc": 0}

    def set_value(self, scheme: str, subgroup: str, setting: str, ac: int, dc: int) -> None:
        subprocess.run(["powercfg", "/setacvalueindex", scheme, subgroup, setting, str(ac)], check=True, capture_output=True)
        subprocess.run(["powercfg", "/setdcvalueindex", scheme, subgroup, setting, str(dc)], check=True, capture_output=True)


@dataclass(frozen=True)
class PowerCfgSetAction:
    subgroup: str
    setting: str
    ac: int
    dc: int
    _action_id: str | None = None

    @property
    def action_id(self) -> str:
        if self._action_id is not None:
            return self._action_id
        return f"power:{self.subgroup}:{self.setting}"

    @property
    def action_type(self) -> str:
        return "powercfg_set"

    @property
    def target(self) -> str:
        return f"{self.subgroup}\\{self.setting}"

    def current(self, backend) -> dict[str, Any]:
        scheme = backend.get_active_scheme()
        values = backend.get_value(scheme, self.subgroup, self.setting)
        return {"exists": True, "scheme": scheme, **values}

    def desired(self) -> dict[str, Any]:
        return {"exists": True, "ac": self.ac, "dc": self.dc}

    def apply(self, backend) -> dict[str, Any]:
        before = self.current(backend)
        backend.set_value(before["scheme"], self.subgroup, self.setting, self.ac, self.dc)
        after = self.current(backend)
        return {"action_id": self.action_id, "action_type": self.action_type, "target": self.target, "before": before, "after": after}

    def verify(self, backend) -> dict[str, Any]:
        current = self.current(backend)
        passed = current.get("ac") == self.ac and current.get("dc") == self.dc
        return {"status": "passed" if passed else "failed", "current": current, "expected": self.desired()}

    def rollback(self, backend, before: dict[str, Any]) -> None:
        backend.set_value(before["scheme"], self.subgroup, self.setting, before["ac"], before["dc"])
        backend.set_active_scheme(before["scheme"])
