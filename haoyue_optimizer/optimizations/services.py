from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.service import ServiceStartTypeAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_safe_services",
            title="禁用低副作用后台服务",
            category="services",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["减少 Xbox、地图、传真、远程注册表和遥测相关后台服务"],
            side_effects=["Xbox 联动、地图后台下载、传真、远程注册表和错误上传不可用"],
            legacy_ids=["mapsbroker", "svc_safe"],
            actions=[
                ServiceStartTypeAction("XblAuthManager", "disabled", stop=True),
                ServiceStartTypeAction("XblGameSave", "disabled", stop=True),
                ServiceStartTypeAction("XboxNetApiSvc", "disabled", stop=True),
                ServiceStartTypeAction("MapsBroker", "disabled", stop=True),
                ServiceStartTypeAction("DiagTrack", "disabled", stop=True),
                ServiceStartTypeAction("RemoteRegistry", "disabled", stop=True),
                ServiceStartTypeAction("Fax", "disabled", stop=True),
                ServiceStartTypeAction("WerSvc", "disabled", stop=True),
            ],
        ),
        Optimization(
            id="disable_mmcss",
            title="禁用多媒体类调度服务",
            category="services",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["关闭 MMCSS 减少系统对多媒体线程的调度干预"],
            side_effects=["MMCSS 服务禁用，音频和多媒体调度可能受影响，游戏音频可能出问题"],
            legacy_ids=["disable_mmcss"],
            requires_admin=True,
            actions=[
                ServiceStartTypeAction("MMCSS", "disabled", stop=True),
            ],
        ),
    ]
