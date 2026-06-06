from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_sticky_keys",
            title="禁用粘滞键",
            category="input",
            preset="safe",
            risk="green",
            evidence="high",
            benefit=["避免游戏中误触 Shift 键触发粘滞键弹窗"],
            side_effects=["辅助功能粘滞键热键不再可用"],
            legacy_ids=["sticky_keys"],
            actions=[
                RegistrySetAction("HKCU", r"Control Panel\Accessibility\StickyKeys", "Flags", "506", "sz"),
            ],
        ),
        Optimization(
            id="disable_toggle_keys",
            title="禁用切换键提示音",
            category="input",
            preset="safe",
            risk="green",
            evidence="high",
            benefit=["关闭 Caps Lock / Num Lock 切换提示音"],
            side_effects=["辅助功能切换键提示音不再播放"],
            legacy_ids=["toggle_keys"],
            actions=[
                RegistrySetAction("HKCU", r"Control Panel\Accessibility\ToggleKeys", "Flags", "58", "sz"),
            ],
        ),
        Optimization(
            id="disable_kb_opt",
            title="优化键盘响应参数",
            category="input",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["减少键盘重复延迟，提升输入响应速度"],
            side_effects=["键盘重复延迟和速率改变，影响打字手感"],
            legacy_ids=["kb_opt"],
            actions=[
                RegistrySetAction("HKCU", r"Control Panel\Keyboard", "KeyboardDelay", "0", "sz"),
                RegistrySetAction("HKCU", r"Control Panel\Keyboard", "KeyboardSpeed", "48", "sz"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\kbdclass\Parameters", "KeyboardDataQueueSize", 20, "dword"),
                RegistrySetAction("HKCU", r"Control Panel\Accessibility\Keyboard Response", "AutoRepeatDelay", "175", "sz"),
                RegistrySetAction("HKCU", r"Control Panel\Accessibility\Keyboard Response", "AutoRepeatRate", "25", "sz"),
                RegistrySetAction("HKCU", r"Control Panel\Accessibility\Keyboard Response", "BounceTime", "0", "sz"),
            ],
        ),
        Optimization(
            id="disable_mouse_opt",
            title="优化鼠标响应参数",
            category="input",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["关闭鼠标加速，提供更精准的鼠标控制"],
            side_effects=["关闭鼠标加速，鼠标移动行为改变"],
            legacy_ids=["mouse_opt"],
            actions=[
                RegistrySetAction("HKCU", r"Control Panel\Mouse", "MouseSpeed", "0", "sz"),
                RegistrySetAction("HKCU", r"Control Panel\Mouse", "MouseThreshold1", "0", "sz"),
                RegistrySetAction("HKCU", r"Control Panel\Mouse", "MouseThreshold2", "0", "sz"),
                RegistrySetAction("HKCU", r"Control Panel\Mouse", "MouseSensitivity", "10", "sz"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\mouclass\Parameters", "MouseDataQueueSize", 20, "dword"),
                RegistrySetAction("HKCU", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers", r"C:\Windows\System32\dwm.exe", "NoDTToDITMouseBatch", "sz"),
            ],
        ),
        Optimization(
            id="disable_access_all",
            title="禁用所有辅助功能快捷键",
            category="input",
            preset="safe",
            risk="green",
            evidence="medium",
            benefit=["一次性禁用粘滞键、切换键、筛选键和鼠标键快捷键"],
            side_effects=["辅助功能快捷键被禁用（粘滞键、切换键、筛选键、鼠标键）"],
            legacy_ids=["access_all"],
            actions=[
                RegistrySetAction("HKCU", r"Control Panel\Accessibility\StickyKeys", "Flags", "506", "sz", qualifier="access_all"),
                RegistrySetAction("HKCU", r"Control Panel\Accessibility\ToggleKeys", "Flags", "58", "sz", qualifier="access_all"),
                RegistrySetAction("HKCU", r"Control Panel\Accessibility\Keyboard Response", "Flags", "122", "sz"),
                RegistrySetAction("HKCU", r"Control Panel\Accessibility\MouseKeys", "Flags", "0", "sz"),
            ],
        ),
    ]
