from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class Backend(Protocol):
    """Marker protocol for action-specific backends."""


@dataclass(frozen=True)
class ActionResult:
    status: str
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


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
