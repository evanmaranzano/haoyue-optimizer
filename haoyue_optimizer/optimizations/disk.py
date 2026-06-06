from __future__ import annotations

from haoyue_optimizer.core.advisory import AdvisoryAction
from haoyue_optimizer.core.cleanup import FileCleanupAction
from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction


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
                AdvisoryAction(
                    action_id="advisory:ssd_opt",
                    target="fsutil behavior",
                    message="SSD 优化需要 fsutil 命令，本阶段只生成提示，不自动执行。",
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
    ]
