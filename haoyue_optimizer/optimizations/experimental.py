from __future__ import annotations

from haoyue_optimizer.core.advisory import AdvisoryAction
from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="experimental_gpu_msi_advisory",
            title="GPU MSI 模式检测提示",
            category="gaming",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["检测 GPU 是否已启用 MSI 模式"],
            side_effects=[
                "仅提供信息，不做任何写入",
                "需要用户手动使用 MSI Mode Tool 或注册表修改",
            ],
            legacy_ids=["gpu_msi_mode"],
            requires_admin=True,
            requires_reboot=True,
            actions=[
                AdvisoryAction(
                    action_id="advisory:gpu_msi_mode",
                    target="GPU MSI mode",
                    message=(
                        "GPU MSI (Message Signaled Interrupts) 模式可减少中断延迟，"
                        "但自动写入注册表存在硬件兼容风险。请使用 MSI Mode Utility "
                        "手动检测并启用。本工具不会自动修改此项。"
                    ),
                ),
            ],
        ),
        Optimization(
            id="experimental_timer_resolution_advisory",
            title="系统定时器分辨率检测提示",
            category="system",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["提示当前系统定时器分辨率状态"],
            side_effects=[
                "仅提供信息，不做任何写入",
                "修改定时器分辨率可能增加功耗",
            ],
            legacy_ids=["timer_res"],
            requires_admin=True,
            requires_reboot=False,
            actions=[
                AdvisoryAction(
                    action_id="advisory:timer_res",
                    target="Timer resolution",
                    message=(
                        "Windows 默认定时器分辨率 15.6ms，部分游戏和低延迟场景建议 "
                        "1ms。但系统级修改可能导致功耗增加和睡眠中断。请使用 "
                        "TimerTool 或 Windows 内置工具手动调整。本工具不会自动修改此项。"
                    ),
                ),
            ],
        ),
        Optimization(
            id="disable_superfetch",
            title="禁用 Superfetch 预取",
            category="system",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["关闭预取和 Superfetch 减少磁盘活动"],
            side_effects=["预取和 Superfetch 关闭，应用启动可能变慢"],
            legacy_ids=["superfetch"],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters", "EnableSuperfetch", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_disk_no_sleep",
            title="禁用磁盘休眠超时",
            category="disk",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["防止磁盘进入休眠状态"],
            side_effects=["磁盘超时值设为 0，可能影响磁盘休眠行为"],
            legacy_ids=["disk_no_sleep"],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\Disk", "TimeOutValue", 0, "dword"),
            ],
        ),
    ]
