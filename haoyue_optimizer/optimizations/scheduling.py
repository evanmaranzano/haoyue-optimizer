from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_win32_pri",
            title="调整 Win32 线程调度优先级",
            category="scheduling",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["优化前台线程调度优先级"],
            side_effects=["改变线程调度优先级策略，可能影响系统稳定性"],
            legacy_ids=["win32_pri"],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation", 40, "dword"),
            ],
        ),
        # ── MMCSS: gaming low-latency profile (current default) ──
        Optimization(
            id="experimental_low_latency2",
            title="多媒体低延迟任务调度（游戏优先）",
            category="scheduling",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["优化音频和低延迟任务的 MMCSS 调度参数，游戏低延迟优先"],
            side_effects=["改变音频和低延迟任务的调度配置，多媒体播放可能失配"],
            legacy_ids=["low_latency2"],
            actions=[
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Audio", "Affinity", 0, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Audio", "Background Only", "False", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Audio", "Clock Rate", 10000, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Audio", "GPU Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Audio", "Priority", 6, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Audio", "Scheduling Category", "High", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Audio", "SFIO Priority", "Normal", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Low Latency", "Affinity", 0, "dword", qualifier="low_latency"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Low Latency", "Background Only", "False", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Low Latency", "Clock Rate", 10000, "dword", qualifier="low_latency"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Low Latency", "GPU Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Low Latency", "Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Low Latency", "Scheduling Category", "High", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Low Latency", "SFIO Priority", "High", "sz", qualifier="low_latency"),
            ],
        ),
        # ── MMCSS: global multimedia scheduling (gaming-low-latency aligned) ──
        Optimization(
            id="experimental_low_latency3",
            title="全局多媒体调度优化（游戏优先）",
            category="scheduling",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["全面优化所有多媒体任务组的 MMCSS 调度参数，游戏低延迟优先"],
            side_effects=["全局修改多媒体调度策略，可能影响系统整体调度行为"],
            legacy_ids=["low_latency3"],
            actions=[
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Capture", "GPU Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Capture", "Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Capture", "Scheduling Category", "High", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Capture", "SFIO Priority", "High", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\DisplayPostProcessing", "GPU Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\DisplayPostProcessing", "Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\DisplayPostProcessing", "Scheduling Category", "High", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\DisplayPostProcessing", "SFIO Priority", "High", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Distribution", "GPU Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Distribution", "Priority", 4, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Distribution", "Scheduling Category", "Medium", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Distribution", "SFIO Priority", "Normal", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Playback", "GPU Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Playback", "Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Playback", "Scheduling Category", "High", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Playback", "SFIO Priority", "High", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Pro Audio", "GPU Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Pro Audio", "Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Pro Audio", "Scheduling Category", "High", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Pro Audio", "SFIO Priority", "High", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Window Manager", "GPU Priority", 8, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Window Manager", "Priority", 2, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Window Manager", "Scheduling Category", "Medium", "sz"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Window Manager", "SFIO Priority", "Normal", "sz"),
            ],
        ),
    ]
