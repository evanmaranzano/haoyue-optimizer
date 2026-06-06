from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdvisoryAction:
    """Informational-only action that never writes to the system."""

    action_id: str
    target: str
    message: str
    action_type: str = "advisory"

    def current(self, backend: Any) -> dict[str, Any]:
        return {"status": "advisory", "detail": self.message}

    def desired(self) -> dict[str, Any]:
        return {"status": "advisory", "detail": self.message}

    def apply(self, backend: Any) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "type": self.action_type,
            "target": self.target,
            "before": self.current(backend),
            "verify": self.verify(backend),
        }

    def verify(self, backend: Any) -> dict[str, Any]:
        return {"status": "unsupported", "detail": self.message}

    def rollback(self, backend: Any, before: Any) -> None:
        pass
