from __future__ import annotations

from haoyue_optimizer.core.advisory import AdvisoryAction
from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction
from haoyue_optimizer.core.service import ServiceStartTypeAction
from haoyue_optimizer.core.subprocess_action import SubprocessAction


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
                SubprocessAction(
                    action_id="subprocess:gpu_msi_mode",
                    target="GPU MSI mode via PCI enumeration",
                    apply_cmd=[
                        "powershell", "-Command",
                        "Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\PCI' -ErrorAction SilentlyContinue | ForEach-Object { Get-ChildItem $_.PSPath -ErrorAction SilentlyContinue | ForEach-Object { if((Get-ItemProperty $_.PSPath -Name 'ClassGUID' -ErrorAction SilentlyContinue).ClassGUID -eq '{4d36e968-e325-11ce-bfc1-08002be10318}'){ $p=Join-Path $_.PSPath 'Device Parameters\\Interrupt Management\\MessageSignaledInterruptProperties'; if(Test-Path $p){ Set-ItemProperty $p 'MSISupported' 1 -Type DWord } } } }",
                    ],
                    verify_cmd=[
                        "powershell", "-Command",
                        "$found=0; Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\PCI' -ErrorAction SilentlyContinue | ForEach-Object { Get-ChildItem $_.PSPath -ErrorAction SilentlyContinue | ForEach-Object { if((Get-ItemProperty $_.PSPath -Name 'ClassGUID' -ErrorAction SilentlyContinue).ClassGUID -eq '{4d36e968-e325-11ce-bfc1-08002be10318}'){ $p=Join-Path $_.PSPath 'Device Parameters\\Interrupt Management\\MessageSignaledInterruptProperties'; if(Test-Path $p){ $v=(Get-ItemProperty $p -ErrorAction SilentlyContinue).MSISupported; if($v -eq 1){$found++} } } } }; if($found -gt 0){exit 0}else{exit 1}",
                    ],
                ),
            ],
        ),
        Optimization(
            id="experimental_timer_resolution",
            title="启用全局定时器高精度请求",
            category="system",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["允许进程请求高精度定时器分辨率，减少帧时间抖动"],
            side_effects=["定时器分辨率提高可能增加功耗"],
            legacy_ids=["timer_res"],
            requires_admin=True,
            requires_reboot=True,
            actions=[
                RegistrySetAction(
                    "HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\kernel",
                    "GlobalTimerResolutionRequests", 1, "dword",
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
                ServiceStartTypeAction("SysMain", "disabled", stop=True),
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
        # ── IRQ affinity: advisory-only on modern systems ──
        # Most modern GPUs use MSI/MSI-X, so fixed IRQ affinity (IRQ8/IRQ16)
        # has no effect.  This optimization is retained as advisory so users can
        # check their device interrupt mode before applying manual tuning.
        Optimization(
            id="experimental_irq_affinity",
            title="IRQ 中断亲和性检测（仅报告）",
            category="system",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["检测 GPU 和音频设备使用的中断模式，如为 line-based IRQ 则提示优化方案"],
            side_effects=[
                "仅检测和报告，不自动写入 PriorityControl",
                "现代 GPU（MSI/MSI-X 模式）不受 IRQ 优先级影响",
            ],
            legacy_ids=[],
            requires_admin=True,
            requires_reboot=False,
            actions=[
                AdvisoryAction(
                    action_id="advisory:irq_affinity",
                    target="GPU interrupt mode detection",
                    message=(
                        "检查设备管理器 → GPU → 资源 → IRQ。"
                        "如果 GPU 使用 MSI 模式（负 IRQ 编号如 -2/-5），无需配置 IRQ 优先级。"
                        "如果使用正数 IRQ（line-based），可手动调整 PriorityControl。"
                    ),
                ),
            ],
        ),
        Optimization(
            id="experimental_disable_dynamic_tick",
            title="禁用动态时钟节拍 (BCDEdit)",
            category="system",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["固定时钟中断频率，减少帧时间抖动"],
            side_effects=["笔记本功耗增加，需重启生效"],
            legacy_ids=[],
            requires_admin=True,
            requires_reboot=True,
            actions=[
                SubprocessAction(
                    action_id="subprocess:bcdedit_disabledynamictick",
                    target="bcdedit disabledynamictick",
                    apply_cmd=["bcdedit", "/set", "disabledynamictick", "yes"],
                    rollback_cmd=["bcdedit", "/deletevalue", "disabledynamictick"],
                    verify_cmd=[
                        "powershell", "-Command",
                        "$v=(bcdedit /enum '{current}' | Select-String 'disabledynamictick'); if($v){exit 0}else{exit 1}",
                    ],
                ),
            ],
        ),
        Optimization(
            id="experimental_tsc_sync",
            title="TSC 同步策略优化 (BCDEdit)",
            category="system",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["设置 TSC 同步策略为 Enhanced，优化多核时间戳计数器精度"],
            side_effects=["需重启生效，极少数旧硬件可能不兼容 Enhanced 模式"],
            legacy_ids=[],
            requires_admin=True,
            requires_reboot=True,
            actions=[
                SubprocessAction(
                    action_id="subprocess:bcdedit_tscsync",
                    target="bcdedit tscsyncpolicy enhanced",
                    apply_cmd=["bcdedit", "/set", "tscsyncpolicy", "enhanced"],
                    rollback_cmd=["bcdedit", "/deletevalue", "tscsyncpolicy"],
                    verify_cmd=[
                        "powershell", "-Command",
                        "$v=(bcdedit /enum '{current}' | Select-String 'tscsyncpolicy.*Enhanced'); if($v){exit 0}else{exit 1}",
                    ],
                ),
            ],
        ),
        Optimization(
            id="experimental_useplatformtick",
            title="强制使用平台时钟 (BCDEdit)",
            category="system",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["强制使用平台硬件时钟而非 TSC，提高计时精度"],
            side_effects=["需重启生效，与 disabledynamictick 配合使用效果更佳"],
            legacy_ids=[],
            requires_admin=True,
            requires_reboot=True,
            actions=[
                SubprocessAction(
                    action_id="subprocess:bcdedit_useplatformtick",
                    target="bcdedit useplatformtick yes",
                    apply_cmd=["bcdedit", "/set", "useplatformtick", "yes"],
                    rollback_cmd=["bcdedit", "/deletevalue", "useplatformtick"],
                    verify_cmd=[
                        "powershell", "-Command",
                        "$v=(bcdedit /enum '{current}' | Select-String 'useplatformtick.*Yes'); if($v){exit 0}else{exit 1}",
                    ],
                ),
            ],
        ),
    ]
