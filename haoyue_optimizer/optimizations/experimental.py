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
    ]
