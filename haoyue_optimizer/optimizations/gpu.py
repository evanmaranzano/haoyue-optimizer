from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_gpu_preempt",
            title="禁用 GPU 抢占调度",
            category="gpu",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["减少 GPU 调度抢占，降低渲染延迟"],
            side_effects=["禁用 GPU 抢占调度，可能影响多任务 GPU 性能"],
            legacy_ids=["gpu_preempt"],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Scheduler", "EnablePreemption", 0, "dword"),
            ],
        ),
    ]
