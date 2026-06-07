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
    ]
