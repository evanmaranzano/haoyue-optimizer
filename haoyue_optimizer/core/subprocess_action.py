from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any


class FakeSubprocessBackend:
    def __init__(self):
        self.commands: list[list[str]] = []

    def run(self, cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        self.commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")


@dataclass(frozen=True)
class SubprocessAction:
    action_id: str
    target: str
    apply_cmd: list[str]
    rollback_cmd: list[str] | None = None
    verify_cmd: list[str] | None = None
    verify_expect_rc: int = 0

    @property
    def action_type(self) -> str:
        return "subprocess"

    def current(self, backend) -> dict[str, Any]:
        if self.verify_cmd and isinstance(backend, FakeSubprocessBackend):
            return {"status": "pending_command"}
        if self.verify_cmd:
            try:
                r = subprocess.run(self.verify_cmd, capture_output=True, text=True, encoding="gbk", errors="ignore")
                return {"status": "applied" if r.returncode == self.verify_expect_rc else "not_applied", "output": r.stdout[:200]}
            except Exception:
                return {"status": "unknown"}
        return {"status": "pending_command"}

    def desired(self) -> dict[str, Any]:
        return {"status": "will_execute"}

    def apply(self, backend) -> dict[str, Any]:
        before = self.current(backend)
        try:
            if isinstance(backend, FakeSubprocessBackend):
                backend.run(self.apply_cmd)
                rc, out = 0, ""
            else:
                r = subprocess.run(self.apply_cmd, capture_output=True, text=True, encoding="gbk", errors="ignore")
                rc, out = r.returncode, (r.stdout + r.stderr)[:200]
            return {
                "action_id": self.action_id,
                "action_type": self.action_type,
                "target": self.target,
                "before": before,
                "after": {"rc": rc, "output": out},
            }
        except Exception as exc:
            return {
                "action_id": self.action_id,
                "action_type": self.action_type,
                "target": self.target,
                "before": before,
                "after": {"rc": -1, "output": str(exc)},
            }

    def verify(self, backend) -> dict[str, Any]:
        if self.verify_cmd:
            try:
                if isinstance(backend, FakeSubprocessBackend):
                    return {"status": "passed"}
                r = subprocess.run(self.verify_cmd, capture_output=True, text=True, encoding="gbk", errors="ignore")
                return {"status": "passed" if r.returncode == self.verify_expect_rc else "failed", "output": r.stdout[:200]}
            except Exception as exc:
                return {"status": "failed", "detail": str(exc)}
        # No verify command — trust apply result
        return {"status": "passed"}

    def rollback(self, backend: Any, before: dict[str, Any]) -> None:
        if self.rollback_cmd:
            if isinstance(backend, FakeSubprocessBackend):
                backend.run(self.rollback_cmd)
            else:
                subprocess.run(self.rollback_cmd, capture_output=True, text=True, encoding="gbk", errors="ignore")
