from __future__ import annotations

from datetime import datetime
from typing import Any

from haoyue_optimizer import VERSION
from haoyue_optimizer.core.compat import (
    STORE_SAFE_DEFAULT_START_TYPES,
    is_amd_cpu,
    is_intel_hybrid_cpu,
    is_laptop,
    is_service_disabled,
)
from haoyue_optimizer.core.power import WindowsPowerBackend
from haoyue_optimizer.core.registry import WindowsRegistryBackend
from haoyue_optimizer.core.scheduled_task import WindowsScheduledTaskBackend
from haoyue_optimizer.core.service import ServiceStartTypeAction, WindowsServiceBackend
from haoyue_optimizer.optimizations.catalog import get_optimizations

# ── Hardware context cache (populated once per process lifetime) ──

_hw: dict = {}


def _ensure_hw() -> dict:
    global _hw
    if not _hw:
        _hw = {
            "is_intel_hybrid": is_intel_hybrid_cpu(),
            "is_amd": is_amd_cpu(),
            "is_laptop": is_laptop(),
        }
    return _hw


def reset_hw_cache() -> None:
    """Reset the hardware detection cache.  Used in tests to avoid real
    hardware detection calls leaking across test cases."""
    global _hw
    _hw = {}


# ── Explicit opt-in profiles ──

EXPLICIT_PROFILES = frozenset({"no_printer", "kiosk", "server_no_print", "extreme_only"})


def _applies_to_current_system(
    applicability: list[str],
    enabled_profiles: set[str] | frozenset[str] | None = None,
    hw_context: dict | None = None,
) -> bool:
    """Return True when all applicability constraints match the current hardware.

    Supported tags:
      - intel_hybrid_only  → skip on non-Intel-hybrid
      - amd_only           → skip on non-AMD
      - desktop_only       → skip on laptop
      - laptop_only        → skip on desktop
      - no_printer / kiosk / server_no_print / extreme_only
                            → never auto-apply (explicit opt-in)
    """
    hw = hw_context if hw_context is not None else _ensure_hw()

    explicit_tags = set(applicability) & EXPLICIT_PROFILES
    if explicit_tags and not explicit_tags.intersection(enabled_profiles or set()):
        return False

    if "intel_hybrid_only" in applicability and not hw["is_intel_hybrid"]:
        return False
    if "amd_only" in applicability and not hw["is_amd"]:
        return False
    if "desktop_only" in applicability and hw["is_laptop"]:
        return False
    if "laptop_only" in applicability and not hw["is_laptop"]:
        return False

    return True


def build_plan(
    preset: str,
    registry_backend=None,
    service_backend=None,
    task_backend=None,
    power_backend=None,
    subprocess_backend=None,
    *,
    hw_context: dict | None = None,
    enabled_profiles: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    """Build a plan of optimizations for the given preset.

    Parameters
    ----------
    hw_context : dict, optional
        Override hardware detection for testing.  Must contain keys
        ``is_intel_hybrid`` (bool), ``is_amd`` (bool), ``is_laptop`` (bool).
        When omitted, real hardware detection is performed on first call.
    """
    registry_backend = registry_backend or WindowsRegistryBackend()
    service_backend = service_backend or WindowsServiceBackend()
    task_backend = task_backend or WindowsScheduledTaskBackend()
    power_backend = power_backend or WindowsPowerBackend()
    items = []

    for optimization in get_optimizations():
        # Preset filtering
        if preset == "aggressive":
            if optimization.preset not in ("safe", "aggressive"):
                continue
        elif optimization.preset != preset:
            continue

        # Hardware applicability filtering
        if not _applies_to_current_system(
            optimization.applicability,
            enabled_profiles,
            hw_context,
        ):
            continue

        actions = []
        for action in optimization.actions:
            backend = _backend_for(
                action.action_type,
                registry_backend,
                service_backend,
                task_backend,
                power_backend,
                subprocess_backend,
            )
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


def build_store_safe_repair_plan(
    service_backend=None,
) -> tuple[dict[str, Any], dict[str, ServiceStartTypeAction]]:
    service_backend = service_backend or WindowsServiceBackend()
    items = []
    actions_by_id: dict[str, ServiceStartTypeAction] = {}

    for service_name, start_type in sorted(STORE_SAFE_DEFAULT_START_TYPES.items()):
        action = ServiceStartTypeAction(service_name, start_type, only_if_disabled=True)
        current = action.current(service_backend)
        if not current.get("exists") or not is_service_disabled(current.get("start_type")):
            continue
        actions_by_id[action.action_id] = action
        items.append({
            "id": f"repair_store_safe_{service_name.casefold()}",
            "title": f"恢复受保护服务 {service_name}",
            "category": "services",
            "preset": "repair-store-safe",
            "risk": "green",
            "evidence": "high",
            "benefit": ["恢复 Microsoft Store、Windows Update 或系统可靠性所需服务"],
            "side_effects": [f"{service_name} 将从 Disabled 恢复为 {start_type}"],
            "legacy_ids": [],
            "requires_admin": True,
            "requires_reboot": False,
            "applicability": ["Windows 10/11"],
            "actions": [{
                "action_id": action.action_id,
                "type": action.action_type,
                "target": action.target,
                "current": current,
                "desired": action.desired(),
            }],
        })

    return {
        "version": "2.0.0",
        "tool_version": VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "preset": "repair-store-safe",
        "items": items,
    }, actions_by_id


def _backend_for(
    action_type: str,
    registry_backend,
    service_backend,
    task_backend,
    power_backend,
    subprocess_backend,
):
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
    if action_type == "subprocess":
        return subprocess_backend
    raise ValueError(f"unsupported action type: {action_type}")
