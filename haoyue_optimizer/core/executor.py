from __future__ import annotations

from datetime import datetime
from typing import Any

from haoyue_optimizer import VERSION
from haoyue_optimizer.core.backup import write_backup
from haoyue_optimizer.core.power import WindowsPowerBackend
from haoyue_optimizer.core.registry import WindowsRegistryBackend
from haoyue_optimizer.core.scheduled_task import WindowsScheduledTaskBackend
from haoyue_optimizer.core.service import WindowsServiceBackend
from haoyue_optimizer.optimizations.catalog import get_optimizations


def apply_plan(
    plan: dict[str, Any],
    registry_backend=None,
    service_backend=None,
    task_backend=None,
    power_backend=None,
    write_file: bool = True,
) -> dict[str, Any]:
    registry_backend = registry_backend or WindowsRegistryBackend()
    service_backend = service_backend or WindowsServiceBackend()
    task_backend = task_backend or WindowsScheduledTaskBackend()
    power_backend = power_backend or WindowsPowerBackend()
    actions_by_id = _catalog_actions()
    backup = {
        "version": "2.0.0",
        "tool_version": VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "plan_preset": plan.get("preset"),
        "items": [],
    }

    for item in plan.get("items", []):
        backup_item = {"optimization_id": item["id"], "title": item["title"], "actions": []}
        item_statuses = []
        for action_plan in item.get("actions", []):
            try:
                action = actions_by_id[action_plan["action_id"]]
                backend = _backend_for(action.action_type, registry_backend, service_backend, task_backend, power_backend)
                action_backup = action.apply(backend)
                action_backup["verify"] = action.verify(backend)
            except Exception as exc:
                action_backup = {
                    "action_id": action_plan.get("action_id", "unknown"),
                    "target": action_plan.get("target", "unknown"),
                    "before": action_plan.get("current"),
                    "verify": {"status": "failed", "detail": str(exc)},
                }
            item_statuses.append(action_backup["verify"].get("status", "failed"))
            backup_item["actions"].append(action_backup)
        backup_item["status"] = _combine_statuses(item_statuses)
        backup["items"].append(backup_item)

    if write_file:
        path = write_backup(backup)
        backup["backup_path"] = str(path)
    return backup


def rollback_backup(backup: dict[str, Any], registry_backend=None, service_backend=None, task_backend=None, power_backend=None) -> None:
    registry_backend = registry_backend or WindowsRegistryBackend()
    service_backend = service_backend or WindowsServiceBackend()
    task_backend = task_backend or WindowsScheduledTaskBackend()
    power_backend = power_backend or WindowsPowerBackend()
    actions_by_id = _catalog_actions()

    for item in reversed(backup.get("items", [])):
        for action_backup in reversed(item.get("actions", [])):
            action = actions_by_id.get(action_backup.get("action_id"))
            if action is None:
                action = _catalog_actions_by_target().get(action_backup["target"])
            if action is None:
                continue
            backend = _backend_for(action.action_type, registry_backend, service_backend, task_backend, power_backend)
            action.rollback(backend, action_backup["before"])


def _catalog_actions() -> dict[str, Any]:
    result = {}
    for optimization in get_optimizations():
        for action in optimization.actions:
            result[action.action_id] = action
    return result


def _catalog_actions_by_target() -> dict[str, Any]:
    result = {}
    for optimization in get_optimizations():
        for action in optimization.actions:
            result[action.target] = action
    return result


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


def _combine_statuses(statuses: list[str]) -> str:
    if not statuses:
        return "skipped"
    unique = set(statuses)
    if len(unique) == 1:
        return statuses[0]
    if "failed" in unique:
        return "partial"
    if "pending_reboot" in unique:
        return "pending_reboot"
    return "partial"
