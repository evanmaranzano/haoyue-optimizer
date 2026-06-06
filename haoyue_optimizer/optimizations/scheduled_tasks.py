from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.scheduled_task import ScheduledTaskSetEnabledAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="privacy_disable_compat_tasks",
            title="禁用兼容性与体验改善计划任务",
            category="privacy",
            preset="privacy",
            risk="yellow",
            evidence="high",
            benefit=["减少兼容性遥测和 CEIP 后台任务"],
            side_effects=["旧程序兼容性提示减少，部分诊断数据不再生成"],
            legacy_ids=["telemetry_full"],
            actions=[
                ScheduledTaskSetEnabledAction(r"\Microsoft\Windows\Application Experience\ProgramDataUpdater", enabled=False),
                ScheduledTaskSetEnabledAction(r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser", enabled=False),
                ScheduledTaskSetEnabledAction(r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator", enabled=False),
            ],
        ),
    ]
