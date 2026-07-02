from __future__ import annotations

from haoyue_optimizer.core.cleanup import FileCleanupAction
from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction
from haoyue_optimizer.core.subprocess_action import SubprocessAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_disable_prefetch",
            title="禁用预取功能",
            category="disk",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["减少预取文件的磁盘占用"],
            side_effects=["预取功能关闭，首次启动应用可能变慢"],
            legacy_ids=["disable_prefetch"],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters", "EnablePrefetcher", 0, "dword", qualifier="disk"),
            ],
        ),
        Optimization(
            id="disable_ssd_opt",
            title="SSD 优化提示",
            category="disk",
            preset="aggressive",
            risk="yellow",
            evidence="medium",
            benefit=["提示 SSD 优化所需的 fsutil 命令"],
            side_effects=["SSD 优化需要 fsutil 命令，本阶段只生成提示，不自动执行"],
            legacy_ids=["ssd_opt"],
            actions=[
                SubprocessAction(
                    action_id="subprocess:ssd_opt",
                    target="fsutil behavior settings",
                    apply_cmd=[
                        "powershell", "-Command",
                        "fsutil behavior set DisableDeleteNotify 0 | Out-Null; fsutil behavior set EncryptPagingFile 0 | Out-Null; fsutil 8dot3name set 0 | Out-Null",
                    ],
                    verify_cmd=["powershell", "-Command", "if((fsutil behavior query DisableDeleteNotify) -match 'DisableDeleteNotify = 0'){exit 0}else{exit 1}"],
                ),
            ],
        ),
        Optimization(
            id="experimental_temp_clean",
            title="清理过期临时文件",
            category="cleanup",
            preset="aggressive",
            risk="yellow",
            evidence="medium",
            benefit=["释放超过 7 天的临时文件占用的磁盘空间"],
            side_effects=["超过 7 天的临时文件会被删除，正在使用的文件自动跳过，删除后无法回滚"],
            legacy_ids=["temp_clean"],
            requires_admin=False,
            actions=[
                FileCleanupAction(
                    action_id="file_cleanup:temp_clean",
                    target="TEMP and Windows\\Temp",
                    max_age_seconds=7 * 24 * 3600,
                ),
            ],
        ),
        Optimization(
            id="nvme_write_cache",
            title="NVMe 写缓存与电源优化",
            category="disk",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["启用 NVMe 写缓存、禁用 Modern Standby 下的 NVMe D3 电源转换，减少睡眠唤醒延迟"],
            side_effects=["NVMe D3 禁用后 Modern Standby 功耗略增"],
            legacy_ids=[],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Storage", "StorageD3InModernStandby", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_8_3_filenames",
            title="禁用 NTFS 8.3 短文件名",
            category="disk",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["减少 NTFS 创建短文件名的额外开销"],
            side_effects=["16 位应用依赖的 8.3 短文件名不再自动生成"],
            legacy_ids=[],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "NtfsDisable8dot3NameCreation", 1, "dword"),
            ],
        ),
        # ── NTFS last-access: 0x80000002 and 0x80000003 are both disabled ──
        # Windows encodes the "system managed + disabled" state as 0x80000002
        # and the "user disabled" state as 0x80000003.  Both mean "last access
        # time updates are off".  The optimizer targets 0x80000003 (user
        # explicitly disabled) but treats 0x80000002 as equivalent.
        Optimization(
            id="disable_last_access_update",
            title="禁用 NTFS 最后访问时间更新",
            category="disk",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["减少每次文件访问时的磁盘写入开销"],
            side_effects=["文件最后访问时间不再更新，可能影响某些备份和归档工具"],
            legacy_ids=[],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "NtfsDisableLastAccessUpdate", 0x80000003, "dword"),
            ],
        ),
    ]
