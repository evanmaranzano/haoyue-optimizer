from __future__ import annotations

from typing import Any


def classify_action(action: dict[str, Any]) -> str:
    action_type = action.get("type")
    if action_type in {"advisory", "file_cleanup"}:
        return "advisory"
    current = action.get("current", {})
    desired = action.get("desired", {})
    if _matches(current, desired):
        return "applied"
    return "missing"


def _matches(current: dict[str, Any], desired: dict[str, Any]) -> bool:
    if "exists" in desired and current.get("exists") != desired.get("exists"):
        return False
    if "value" in desired and current.get("value") != desired.get("value"):
        return False
    if "ac" in desired and current.get("ac") != desired.get("ac"):
        return False
    if "dc" in desired and current.get("dc") != desired.get("dc"):
        return False
    if "enabled" in desired and current.get("enabled") != desired.get("enabled"):
        return False
    if "start_type" in desired and current.get("start_type") != desired.get("start_type"):
        return False
    return True


def summarize_plan_status(plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result = {"applied": [], "missing": [], "advisory": []}
    for item in plan.get("items", []):
        action_statuses = [classify_action(action) for action in item.get("actions", [])]
        if action_statuses and all(status == "applied" for status in action_statuses):
            result["applied"].append(item)
        elif action_statuses and all(status == "advisory" for status in action_statuses):
            result["advisory"].append(item)
        else:
            result["missing"].append(item)
    return result
