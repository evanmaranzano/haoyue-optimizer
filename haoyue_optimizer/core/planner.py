from __future__ import annotations

from datetime import datetime
from typing import Any

from haoyue_optimizer import VERSION
from haoyue_optimizer.core.power import WindowsPowerBackend
from haoyue_optimizer.core.registry import WindowsRegistryBackend
from haoyue_optimizer.core.scheduled_task import WindowsScheduledTaskBackend
from haoyue_optimizer.core.service import WindowsServiceBackend
from haoyue_optimizer.optimizations.catalog import get_optimizations


def build_plan(preset: str, registry_backend=None, service_backend=None, task_backend=None, power_backend=None) -> dict[str, Any]:
    registry_backend = registry_backend or WindowsRegistryBackend()
    service_backend = service_backend or WindowsServiceBackend()
    task_backend = task_backend or WindowsScheduledTaskBackend()
    power_backend = power_backend or WindowsPowerBackend()
    items = []

    for optimization in get_optimizations():
        if optimization.preset != preset:
            continue
        actions = []
        for action in optimization.actions:
            backend = _backend_for(action.action_type, registry_backend, service_backend, task_backend, power_backend)
            actions.append({
                "action_id": action.action_id,
                "type": action.action_type,
                "target": action.target,
                "current": action.current(backend),
                "desired": action.desired(),
            })
        items.append({
            "id": optimization.id,
            "title": optimization.title,
            "category": optimization.category,
            "preset": optimization.preset,
            "risk": optimization.risk,
            "evidence": optimization.evidence,
            "benefit": optimization.benefit,
            "side_effects": optimization.side_effects,
            "legacy_ids": optimization.legacy_ids,
            "requires_admin": optimization.requires_admin,
            "requires_reboot": optimization.requires_reboot,
            "applicability": optimization.applicability,
            "actions": actions,
        })

    return {
        "version": "2.0.0",
        "tool_version": VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "preset": preset,
        "items": items,
    }


def _backend_for(action_type: str, registry_backend, service_backend, task_backend, power_backend):
    if action_type == "registry_set":
        return registry_backend
    if action_type == "service_start_type":
        return service_backend
    if action_type == "scheduled_task_enabled":
        return task_backend
    if action_type == "powercfg_set":
        return power_backend
    if action_type == "advisory":
        return None
    if action_type == "file_cleanup":
        return None
    raise ValueError(f"unsupported action type: {action_type}")
