from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_transparency",
            title="禁用窗口透明效果",
            category="display",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["减少桌面窗口合成的 GPU 开销"],
            side_effects=["窗口标题栏和开始菜单不再有半透明毛玻璃效果"],
            legacy_ids=["transparency"],
            actions=[
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_anim_disable",
            title="禁用窗口动画和 Aero Peek",
            category="display",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["关闭窗口动画和 Aero Peek 预览，减少 GPU 开销"],
            side_effects=["窗口动画和 Aero Peek 预览关闭"],
            legacy_ids=["anim_disable"],
            actions=[
                RegistrySetAction("HKCU", r"Control Panel\Desktop\WindowMetrics", "MinAnimate", "0", "sz"),
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Windows\DWM", "EnableAeroPeek", 0, "dword"),
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Windows\DWM", "AlwaysHibernateThumbnails", 0, "dword"),
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", 2, "dword"),
            ],
        ),
        Optimization(
            id="disable_fullscreen_optimizations",
            title="禁用全屏优化",
            category="display",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["禁用全屏优化以减少游戏输入延迟"],
            side_effects=["全屏优化被禁用，窗口化游戏可能受影响"],
            legacy_ids=["fse_global"],
            actions=[
                RegistrySetAction("HKCU", r"System\GameConfigStore", "GameDVR_DXGIHonorFSEWindowsCompatible", 1, "dword"),
                RegistrySetAction("HKCU", r"System\GameConfigStore", "GameDVR_EFSEFeatureFlags", 0, "dword"),
                RegistrySetAction("HKCU", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "GameDVR_DXGIHonorFSEWindowsCompatible", 1, "dword"),
            ],
        ),
        Optimization(
            id="enable_dx_flip_model",
            title="启用 DirectX Flip Model",
            category="display",
            preset="aggressive",
            risk="yellow",
            evidence="medium",
            benefit=["强制启用 Flip Model 呈现模式，减少帧延迟并改善 VSync/VRR 兼容性"],
            side_effects=["部分旧应用可能不兼容 Flip Model"],
            legacy_ids=[],
            actions=[
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\DirectX\UserGpuPreferences", "DirectXUserGlobalSettings", "SwapEffectUpgradeEnable=1;VRROptimizeEnable=0;", "sz", qualifier="flip"),
            ],
        ),
        Optimization(
            id="disable_audio_exclusive",
            title="禁用音频独占模式",
            category="audio",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["禁用音频独占模式以避免音频设备独占"],
            side_effects=["音频独占模式被禁用，专业音频软件可能受影响"],
            legacy_ids=["audio_no_excl"],
            actions=[
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Multimedia\Audio", "ExclusiveMode", 0, "dword"),
            ],
        ),
    ]
