from __future__ import annotations

from haoyue_optimizer.core.advisory import AdvisoryAction
from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_win32_pri",
            title="调整 Win32 线程调度优先级",
            category="scheduling",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["优化前台线程调度优先级"],
            side_effects=["改变线程调度优先级策略，可能影响系统稳定性"],
            legacy_ids=["win32_pri"],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation", 40, "dword"),
            ],
        ),
        Optimization(
            id="experimental_low_latency2",
            title="多媒体低延迟任务配置提示",
            category="scheduling",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["提示如何优化多媒体任务延迟"],
            side_effects=["改变音频和低延迟任务的调度配置，可能影响音频延迟"],
            legacy_ids=["low_latency2"],
            requires_reboot=False,
            actions=[
                AdvisoryAction(
                    action_id="advisory:low_latency2",
                    target="Multimedia SystemProfile Tasks Audio/Low Latency",
                    message="多媒体任务配置需要修改多个 SystemProfile 子键，本阶段只生成提示。",
                ),
            ],
        ),
        Optimization(
            id="experimental_low_latency3",
            title="全局多媒体调度优化提示",
            category="scheduling",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["提示如何全局优化多媒体调度"],
            side_effects=["全局修改多媒体调度策略，可能影响系统整体调度行为"],
            legacy_ids=["low_latency3"],
            requires_reboot=False,
            actions=[
                AdvisoryAction(
                    action_id="advisory:low_latency3",
                    target="Multimedia SystemProfile all task groups",
                    message="全局多媒体调度优化需要修改 9 个任务组，本阶段只生成提示。",
                ),
            ],
        ),
    ]
