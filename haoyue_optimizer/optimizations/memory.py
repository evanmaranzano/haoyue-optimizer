from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction
from haoyue_optimizer.core.subprocess_action import SubprocessAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_large_cache",
            title="优化内核内存驻留",
            category="memory",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["内核和驱动保留在物理内存，减少页面换出"],
            side_effects=["内核和驱动保留在物理内存，可用内存减少"],
            legacy_ids=["large_cache"],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management", "DisablePagingExecutive", 1, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management", "LargeSystemCache", 1, "dword"),
            ],
        ),
        Optimization(
            id="disable_disable_mem_compress",
            title="禁用内存压缩提示",
            category="memory",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["提示如何禁用 Windows 内存压缩"],
            side_effects=["禁用内存压缩会增加内存占用，可能影响低内存系统"],
            legacy_ids=["disable_mem_compress"],
            requires_reboot=False,
            actions=[
                SubprocessAction(
                    action_id="subprocess:disable_mem_compress",
                    target="Disable-MMAgent -MemoryCompression",
                    apply_cmd=["powershell", "-Command", "Disable-MMAgent -MemoryCompression"],
                    rollback_cmd=["powershell", "-Command", "Enable-MMAgent -MemoryCompression"],
                    verify_cmd=["powershell", "-Command", "if((Get-MMAgent).MemoryCompression -eq $false){exit 0}else{exit 1}"],
                ),
            ],
        ),
        Optimization(
            id="optimize_mmagent",
            title="优化内存管理代理 (MMAgent)",
            category="memory",
            preset="aggressive",
            risk="yellow",
            evidence="medium",
            benefit=["禁用应用预取和启动预加载，减少内存和磁盘 I/O 开销"],
            side_effects=["应用启动预加载关闭，首次启动可能稍慢"],
            legacy_ids=[],
            actions=[
                SubprocessAction(
                    action_id="subprocess:mmagent_tuning",
                    target="MMAgent: disable prefetch/bootprefetch/startupprefetch",
                    apply_cmd=["powershell", "-Command", "Disable-MMAgent -ApplicationPreLaunch; Disable-MMAgent -OperationAPI; Set-MMAgent -MemoryCompression $false -ErrorAction SilentlyContinue"],
                    rollback_cmd=["powershell", "-Command", "Enable-MMAgent -ApplicationPreLaunch; Enable-MMAgent -OperationAPI"],
                    verify_cmd=["powershell", "-Command", "$a=Get-MMAgent; if($a.ApplicationPreLaunch -eq $false){exit 0}else{exit 1}"],
                ),
            ],
        ),
        Optimization(
            id="optimize_io_page_lock",
            title="优化 I/O 页面锁定限制",
            category="memory",
            preset="aggressive",
            risk="yellow",
            evidence="low",
            benefit=["调整 IoPageLockLimit 优化大文件 I/O 性能"],
            side_effects=["锁定更多物理页面用于 I/O，可用内存略减"],
            legacy_ids=[],
            actions=[
                SubprocessAction(
                    action_id="subprocess:io_page_lock",
                    target="IoPageLockLimit based on RAM",
                    apply_cmd=[
                        "powershell", "-Command",
                        "$ram=(Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum; $val=[math]::Min([math]::Floor($ram/4), 1073741824); Set-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management' 'IoPageLockLimit' $val -Type DWord -ErrorAction SilentlyContinue",
                    ],
                    verify_cmd=["powershell", "-Command", "$v=(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management' -ErrorAction SilentlyContinue).IoPageLockLimit; if($v -gt 0){exit 0}else{exit 1}"],
                ),
            ],
        ),
    ]
