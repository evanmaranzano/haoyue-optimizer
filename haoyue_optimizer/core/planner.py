from __future__ import annotations

from datetime import datetime
from typing import Any

from haoyue_optimizer import VERSION
from haoyue_optimizer.core.compat import is_intel_hybrid_cpu, is_amd_cpu, is_laptop
from haoyue_optimizer.core.power import WindowsPowerBackend
from haoyue_optimizer.core.registry import WindowsRegistryBackend
from haoyue_optimizer.core.scheduled_task import WindowsScheduledTaskBackend
from haoyue_optimizer.core.service import WindowsServiceBackend
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

_EXPLICIT_OPT_IN_TAGS = {"no_printer", "kiosk", "server_no_print", "extreme_only"}


def _applies_to_current_system(applicability: list[str]) -> bool:
    """Return True when all applicability constraints match the current hardware.

    Supported tags:
      - intel_hybrid_only  → skip on non-Intel-hybrid
      - amd_only           → skip on non-AMD
      - desktop_only       → skip on laptop
      - laptop_only        → skip on desktop
      - no_printer / kiosk / server_no_print / extreme_only
                            → never auto-apply (explicit opt-in)
    """
    hw = _ensure_hw()

    # Explicit opt-in profiles — never auto-apply
    if any(tag in _EXPLICIT_OPT_IN_TAGS for tag in applicability):
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
    *,
    hw_context: dict | None = None,
) -> dict[str, Any]:
    """Build a plan of optimizations for the given preset.

    Parameters
    ----------
    hw_context : dict, optional
        Override hardware detection for testing.  Must contain keys
        ``is_intel_hybrid`` (bool), ``is_amd`` (bool), ``is_laptop`` (bool).
        When omitted, real hardware detection is performed on first call.
    """
    global _hw
    if hw_context is not None:
        _hw = hw_context

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
        if not _applies_to_current_system(optimization.applicability):
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
    if action_type == "subprocess":
        return None
    raise ValueError(f"unsupported action type: {action_type}")
