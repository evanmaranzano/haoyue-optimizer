from __future__ import annotations

from typing import Any

ALLOWED_ACTION_TYPES = {
    "registry_set",
    "service_start_type",
    "scheduled_task_enabled",
    "powercfg_set",
    "advisory",
    "file_cleanup",
}

ALLOWED_STATUSES = {"passed", "failed", "skipped", "unsupported", "pending_reboot", "partial"}


class PlanValidationError(ValueError):
    pass


def validate_plan_for_apply(plan: dict[str, Any], allow_experimental: bool) -> dict[str, Any]:
    if plan.get("version") != "2.0.0":
        raise PlanValidationError("unsupported or missing plan version")
    items = plan.get("items")
    if not isinstance(items, list):
        raise PlanValidationError("plan items must be a list")

    action_count = 0
    risk_counts: dict[str, int] = {}
    requires_admin = False
    requires_reboot = False
    side_effects: list[str] = []
    has_experimental = plan.get("preset") == "experimental"

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise PlanValidationError(f"item {index} must be an object")
        for key in ("id", "preset", "risk", "actions"):
            if key not in item:
                raise PlanValidationError(f"item {index} missing {key}")
        if item["preset"] == "experimental" or item["risk"] == "red":
            has_experimental = True
        risk_counts[item["risk"]] = risk_counts.get(item["risk"], 0) + 1
        requires_admin = requires_admin or bool(item.get("requires_admin", True))
        requires_reboot = requires_reboot or bool(item.get("requires_reboot", False))
        for effect in item.get("side_effects", []):
            if isinstance(effect, str):
                side_effects.append(effect)

        actions = item["actions"]
        if not isinstance(actions, list):
            raise PlanValidationError(f"item {item['id']} actions must be a list")
        for action_index, action in enumerate(actions):
            if not isinstance(action, dict):
                raise PlanValidationError(f"item {item['id']} action {action_index} must be an object")
            for key in ("action_id", "type", "target", "desired"):
                if key not in action:
                    raise PlanValidationError(f"item {item['id']} action {action_index} missing {key}")
            if action["type"] not in ALLOWED_ACTION_TYPES:
                raise PlanValidationError(f"unsupported action type: {action['type']}")
            action_count += 1

    if has_experimental and not allow_experimental:
        raise PlanValidationError("experimental plan requires --allow-experimental")

    return {
        "item_count": len(items),
        "action_count": action_count,
        "risk_counts": risk_counts,
        "requires_admin": requires_admin,
        "requires_reboot": requires_reboot,
        "side_effects": side_effects,
        "has_experimental": has_experimental,
    }
