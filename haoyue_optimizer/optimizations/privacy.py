from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction
from haoyue_optimizer.core.scheduled_task import ScheduledTaskSetEnabledAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_basic_telemetry",
            title="禁用基础遥测和广告 ID",
            category="privacy",
            preset="safe",
            risk="green",
            evidence="high",
            benefit=["减少诊断和个性化广告数据收集"],
            side_effects=["Windows 个性化推荐和反馈体验减少"],
            legacy_ids=["telemetry", "tracking"],
            actions=[
                RegistrySetAction("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Policies\Microsoft\SQMClient\Windows", "CEIPEnable", 0, "dword"),
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_content_delivery",
            title="禁用推荐内容和 Windows 技巧",
            category="privacy",
            preset="safe",
            risk="green",
            evidence="high",
            benefit=["减少开始菜单、锁屏和系统提示中的推荐内容"],
            side_effects=["Windows 新功能提示和个性化内容减少"],
            legacy_ids=["content_del", "feeds"],
            actions=[
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SystemPaneSuggestionsEnabled", 0, "dword"),
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SoftLandingEnabled", 0, "dword"),
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "RotatingLockScreenEnabled", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_telemetry_ex",
            title="禁用扩展遥测和反馈数据收集",
            category="privacy",
            preset="aggressive",
            risk="green",
            evidence="medium",
            benefit=["减少 Connected User Experiences、反馈通知和语音数据上传"],
            side_effects=["语音识别、墨迹输入个性化和反馈中心功能受限"],
            legacy_ids=[],
            actions=[
                RegistrySetAction("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "LimitDiagnosticLogWriter", 1, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "LimitDumpCollection", 1, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection", "AllowTelemetry", 0, "dword"),
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\InputPersonalization", "RestrictImplicitInkCollection", 1, "dword"),
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\InputPersonalization", "RestrictImplicitTextCollection", 1, "dword"),
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy", "HasAccepted", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_disable_bg_tasks",
            title="禁用诊断和系统维护计划任务",
            category="privacy",
            preset="aggressive",
            risk="green",
            evidence="medium",
            benefit=["减少磁盘诊断、内存诊断、碎片整理和 Windows 错误报告后台任务"],
            side_effects=["磁盘健康告警不再自动触发，错误报告队列不再自动上传，碎片整理不再自动运行"],
            legacy_ids=["disable_bg_tasks"],
            actions=[
                ScheduledTaskSetEnabledAction(r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector", enabled=False),
                ScheduledTaskSetEnabledAction(r"\Microsoft\Windows\MemoryDiagnostic\ProcessMemoryDiagnosticEvents", enabled=False),
                ScheduledTaskSetEnabledAction(r"\Microsoft\Windows\Windows Error Reporting\QueueReporting", enabled=False),
                ScheduledTaskSetEnabledAction(r"\Microsoft\Windows\Defrag\ScheduledDefrag", enabled=False),
                ScheduledTaskSetEnabledAction(r"\Microsoft\Windows\MemoryDiagnostic\RunFullMemoryDiagnostic", enabled=False),
                ScheduledTaskSetEnabledAction(r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip", enabled=False),
            ],
        ),
    ]
