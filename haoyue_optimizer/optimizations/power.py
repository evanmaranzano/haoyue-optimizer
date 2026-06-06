from __future__ import annotations

from haoyue_optimizer.core.advisory import AdvisoryAction
from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.power import PowerCfgSetAction
from haoyue_optimizer.core.registry import RegistrySetAction

USB_SUBGROUP = "2a737441-1930-4402-8d77-b2bebba308a3"
USB_SELECTIVE_SUSPEND = "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"

CPU_SUBGROUP = "54533251-82be-4824-96c1-47b60b740d00"
CPU_BOOST = "be337238-0d82-4146-a960-4f3749d470c7"
CPU_MIN = "893dee8e-2bef-41e0-89c6-b55d0929964c"
CPU_MAX = "bc5038f7-23e0-4960-96da-33abaf5935ec"

DISK_SUBGROUP = "0012ee47-9041-4b5d-9b77-535fba8b1442"
DISK_IDLE = "6738e2c4-e8a5-4a42-b16a-e040e769756e"

SLEEP_SUBGROUP = "238c9fa8-0aad-41ed-83f4-97be242c8f20"
SLEEP_TIMEOUT = "29f6c1db-86da-48c5-9fdb-f2b67b1f44da"
HYBRID_SLEEP = "94ac6d29-73ce-41a6-809f-6363ba21b47e"
HIBERNATE = "9d7815a6-7ee4-497e-8888-515a05f02364"
WAKE_TIMER = "bd3b718a-0680-4d9d-8ab2-e1d2b4ac806d"

ASPM_SUBGROUP = "501a4d13-42af-4429-9fd1-a8218c268e20"
ASPM_SETTING = "ee12f906-d277-404b-b6da-e5fa1a576df5"

WIFI_SUBGROUP = "19cbb8fa-5279-450e-9fac-8a3d5fedd0c1"
WIFI_POWER = "12bbebe6-58d6-4636-95bb-3217ef867c1a"

DISPLAY_SUBGROUP = "7516b95f-f776-4464-8c53-06167f40cc99"
DISPLAY_OFF = "3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e"
BRIGHTNESS = "aded5e82-b909-4619-9949-f5d71dac0bcb"
ADAPTIVE_BRIGHT = "fbd9aa66-9553-4097-ba44-ed6e9d65eab8"


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="gaming_usb_suspend_off",
            title="禁用 USB 选择性暂停",
            category="power",
            preset="gaming",
            risk="yellow",
            evidence="medium",
            benefit=["减少键鼠、手柄、声卡等 USB 设备休眠导致的断连或唤醒延迟"],
            side_effects=["笔记本功耗可能上升，USB 设备不再自动省电"],
            legacy_ids=["usb_suspend_dis"],
            actions=[PowerCfgSetAction(USB_SUBGROUP, USB_SELECTIVE_SUSPEND, ac=0, dc=0)],
        ),
        Optimization(
            id="gaming_boost",
            title="游戏模式 CPU 提升",
            category="power",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["CPU Boost 设为 Aggressive，最小处理器状态设为 5%"],
            side_effects=["CPU Boost 设为 Aggressive，最小处理器状态设为 5%，可能增加功耗和发热"],
            legacy_ids=["gaming_boost"],
            requires_admin=True,
            actions=[
                PowerCfgSetAction(CPU_SUBGROUP, CPU_BOOST, ac=3, dc=3),
                PowerCfgSetAction(CPU_SUBGROUP, CPU_MIN, ac=5, dc=5),
            ],
        ),
        Optimization(
            id="gaming_preset",
            title="游戏模式电源方案",
            category="power",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["全面调整电源方案以优化游戏性能"],
            side_effects=["全面修改电源方案，禁用休眠/混合睡眠/USB 暂停/ASPM，调整 CPU 和显示参数，可能显著增加功耗"],
            legacy_ids=["gaming_preset"],
            requires_admin=True,
            actions=[
                PowerCfgSetAction(DISK_SUBGROUP, DISK_IDLE, ac=30, dc=60),
                PowerCfgSetAction(SLEEP_SUBGROUP, SLEEP_TIMEOUT, ac=0, dc=0),
                PowerCfgSetAction(SLEEP_SUBGROUP, HYBRID_SLEEP, ac=0, dc=0),
                PowerCfgSetAction(SLEEP_SUBGROUP, HIBERNATE, ac=0, dc=0x7FFFFFFF),
                PowerCfgSetAction(SLEEP_SUBGROUP, WAKE_TIMER, ac=0, dc=0),
                PowerCfgSetAction(USB_SUBGROUP, USB_SELECTIVE_SUSPEND, ac=0, dc=0, _action_id="power:gp:usb_suspend"),
                PowerCfgSetAction(ASPM_SUBGROUP, ASPM_SETTING, ac=0, dc=0),
                PowerCfgSetAction(WIFI_SUBGROUP, WIFI_POWER, ac=0, dc=2),
                PowerCfgSetAction(DISPLAY_SUBGROUP, DISPLAY_OFF, ac=1800, dc=180),
                PowerCfgSetAction(DISPLAY_SUBGROUP, BRIGHTNESS, ac=60, dc=60),
                PowerCfgSetAction(DISPLAY_SUBGROUP, ADAPTIVE_BRIGHT, ac=0, dc=0),
                PowerCfgSetAction(CPU_SUBGROUP, CPU_MIN, ac=5, dc=5, _action_id="power:gp:cpu_min"),
                PowerCfgSetAction(CPU_SUBGROUP, CPU_MAX, ac=100, dc=100),
                PowerCfgSetAction(CPU_SUBGROUP, CPU_BOOST, ac=3, dc=3, _action_id="power:gp:cpu_boost"),
            ],
        ),
        Optimization(
            id="disable_power_perf",
            title="禁用电源节能功能",
            category="power",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["禁用休眠、快速启动和电源节流以最大化性能"],
            side_effects=["禁用休眠、快速启动和电源节流，笔记本续航显著降低"],
            legacy_ids=["power_perf"],
            requires_admin=True,
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "HibernateEnabledDefault", 0, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", 1, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power", "HiberbootEnabled", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_laptop_ac",
            title="笔记本接电源时高性能方案",
            category="power",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["接电源时自动切换到高性能电源方案"],
            side_effects=["需要复制高性能电源方案并切换，可能影响电池寿命"],
            legacy_ids=["laptop_ac"],
            requires_admin=True,
            actions=[
                AdvisoryAction(
                    action_id="advisory:laptop_ac",
                    target="powercfg scheme duplication",
                    message=(
                        "笔记本 AC 高性能方案需要复制电源方案并设置活动方案，"
                        "本阶段只生成提示。"
                    ),
                ),
            ],
        ),
        Optimization(
            id="disable_laptop_bat",
            title="笔记本电池模式平衡方案",
            category="power",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["电池模式自动切换到平衡电源方案"],
            side_effects=["切换到平衡电源方案，可能影响电池续航表现"],
            legacy_ids=["laptop_bat"],
            requires_admin=True,
            actions=[
                AdvisoryAction(
                    action_id="advisory:laptop_bat",
                    target="powercfg scheme switch",
                    message=(
                        "笔记本电池模式切换需要设置活动电源方案，"
                        "本阶段只生成提示。"
                    ),
                ),
            ],
        ),
        Optimization(
            id="disable_cpu_unpark",
            title="禁用 CPU 核心停放",
            category="power",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["CPU 核心不进入停放状态，保持全部核心活跃"],
            side_effects=["CPU 核心始终活跃，功耗和发热可能增加"],
            legacy_ids=["cpu_unpark"],
            requires_admin=True,
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "Class1InitialUnparkCount", 100, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "InitialUnparkCount", 100, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\Policy\Settings\Processor", "PerfEnergyPreference", 0, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\Policy\Settings\Misc", "DeviceIdlePolicy", 0, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PDC\Activators\Default\VetoPolicy", "EA:EnergySaverEngaged", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_unlock_ppm",
            title="解锁处理器电源管理",
            category="power",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["解锁处理器电源管理隐藏选项"],
            side_effects=["解锁后可能被误改导致电源管理异常"],
            legacy_ids=["unlock_ppm"],
            requires_admin=True,
            actions=[
                RegistrySetAction(
                    "HKLM",
                    r"SYSTEM\CurrentControlSet\Control\Power\PowerSettings\54533251-82be-4824-96c1-47b60b740d00\943c8cb6-6f93-4227-ad87-e9a3feec08d1",
                    "Attributes", 2, "dword",
                ),
            ],
        ),
        Optimization(
            id="disable_energy_veto",
            title="禁用节能策略否决",
            category="power",
            preset="experimental",
            risk="red",
            evidence="low",
            benefit=["禁用放电状态下的节能策略否决"],
            side_effects=["系统在放电时不再强制节能，电池消耗可能加快"],
            legacy_ids=["energy_veto"],
            requires_admin=True,
            actions=[
                RegistrySetAction(
                    "HKLM",
                    r"SYSTEM\CurrentControlSet\Control\Power\PDC\Activators\28\VetoPolicy",
                    "EA:PowerStateDischarging", 0, "dword",
                ),
            ],
        ),
    ]
