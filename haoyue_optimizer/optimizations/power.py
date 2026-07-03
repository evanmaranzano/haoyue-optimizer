from __future__ import annotations

from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.power import PowerCfgSetAction, PowerCfgSetActiveAction
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

# Intel P-core / E-core heterogeneous scheduling GUIDs.
# These have no effect on AMD monolithic or older Intel non-hybrid CPUs.
CPU_HETERO_POLICY = "7f2f5cfa-f10c-4823-b5e1-e93ae85f46b5"
CPU_HETERO_THREAD = "93b8b6dc-0698-4d1c-9ee4-0644e900c85d"
CPU_HETERO_SHORT = "bae08b81-2d5e-4688-ad6a-13243356654b"
CPU_CORE_OVERUTIL = "943c8cb6-6f93-4227-ad87-e9a3feec08d1"

# Switchable dynamic GPU
GPU_SWITCH_SUBGROUP = "e276e160-7cb0-43c6-b20b-73f5dce39954"
GPU_SWITCH_GLOBAL = "a1662ab2-9d34-4e53-ba8b-2639b9e20857"


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="gaming_usb_suspend_off",
            title="禁用 USB 选择性暂停",
            category="power",
            preset="aggressive",
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
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["CPU Boost 设为 Efficient Aggressive (3)，激进加力"],
            side_effects=["CPU Boost 设为 Efficient Aggressive，可能增加功耗和发热"],
            legacy_ids=["gaming_boost"],
            requires_admin=True,
            actions=[
                PowerCfgSetAction(CPU_SUBGROUP, CPU_BOOST, ac=3, dc=3),
            ],
        ),
        Optimization(
            id="gaming_preset",
            title="游戏模式电源方案",
            category="power",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["全面调整电源方案以优化游戏性能"],
            side_effects=["全面修改电源方案，禁用休眠/混合睡眠/USB 暂停/ASPM，调整 CPU 和显示参数，可能显著增加功耗"],
            legacy_ids=["gaming_preset"],
            requires_admin=True,
            actions=[
                PowerCfgSetActiveAction(_action_id="power:gp:set_balanced"),
                PowerCfgSetAction(DISK_SUBGROUP, DISK_IDLE, ac=30, dc=60),
                PowerCfgSetAction(SLEEP_SUBGROUP, SLEEP_TIMEOUT, ac=0, dc=0),
                PowerCfgSetAction(SLEEP_SUBGROUP, HYBRID_SLEEP, ac=0, dc=0),
                PowerCfgSetAction(SLEEP_SUBGROUP, HIBERNATE, ac=0, dc=0x7FFFFFFF),
                PowerCfgSetAction(SLEEP_SUBGROUP, WAKE_TIMER, ac=0, dc=0),
                PowerCfgSetAction(USB_SUBGROUP, USB_SELECTIVE_SUSPEND, ac=0, dc=0, _action_id="power:gp:usb_suspend"),
                PowerCfgSetAction(ASPM_SUBGROUP, ASPM_SETTING, ac=0, dc=0),
                PowerCfgSetAction(WIFI_SUBGROUP, WIFI_POWER, ac=0, dc=2),
                PowerCfgSetAction(DISPLAY_SUBGROUP, DISPLAY_OFF, ac=1800, dc=180),
                # BRIGHTNESS excluded — user preference, see compat
                PowerCfgSetAction(DISPLAY_SUBGROUP, ADAPTIVE_BRIGHT, ac=0, dc=0),
                PowerCfgSetAction(CPU_SUBGROUP, CPU_MAX, ac=100, dc=100),
            ],
        ),
        Optimization(
            id="disable_power_perf",
            title="禁用电源节能功能",
            category="power",
            preset="aggressive",
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
        # ── disable_laptop_ac: 仅笔记本通用电源设置，不含 Intel 异构调度 ──
        Optimization(
            id="disable_laptop_ac",
            title="笔记本接电源时 CPU 高性能参数",
            category="power",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=[
                "CPU 最小频率 5%（AC）以允许空闲降频",
                "CPU Boost = Efficient Aggressive",
                "动态显卡 AC 切高性能",
                "禁用自适应亮度",
            ],
            side_effects=["CPU Boost 提升后发热和功耗增加"],
            legacy_ids=["laptop_ac"],
            applicability=["laptop_only"],
            requires_admin=True,
            actions=[
                PowerCfgSetActiveAction(_action_id="power:laptop_ac:set_balanced"),
                # AC 低限 5%（允许降压降频），DC 保留系统默认（由电池策略控制）
                PowerCfgSetAction(CPU_SUBGROUP, CPU_MIN, ac=5, dc=5, _action_id="power:laptop_ac:cpu_min"),
                PowerCfgSetAction(CPU_SUBGROUP, CPU_BOOST, ac=3, dc=3, _action_id="power:laptop_ac:cpu_boost"),
                PowerCfgSetAction(GPU_SWITCH_SUBGROUP, GPU_SWITCH_GLOBAL, ac=2, dc=1, _action_id="power:laptop_ac:gpu_switch"),
                PowerCfgSetAction(DISPLAY_SUBGROUP, ADAPTIVE_BRIGHT, ac=0, dc=0, _action_id="power:laptop_ac:adaptive_bright"),
            ],
        ),
        # ── Intel 异构调度专用版 ──
        Optimization(
            id="disable_laptop_ac_intel_hybrid",
            title="笔记本接电源时 Intel 异构调度优化",
            category="power",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=[
                "Intel P-core/E-core 异类调度全部设为性能优先",
                "P 核阈值 85%",
                "与 disable_laptop_ac 配合使用",
            ],
            side_effects=["仅 Intel 混合架构 CPU 有效，AMD 平台自动跳过"],
            legacy_ids=[],
            applicability=["laptop_only", "intel_hybrid_only"],
            requires_admin=True,
            actions=[
                PowerCfgSetActiveAction(_action_id="power:intel_hybrid:set_balanced"),
                PowerCfgSetAction(CPU_SUBGROUP, CPU_HETERO_POLICY, ac=0, dc=0, _action_id="power:intel_hybrid:hetero_policy"),
                PowerCfgSetAction(CPU_SUBGROUP, CPU_HETERO_THREAD, ac=0, dc=0, _action_id="power:intel_hybrid:hetero_thread"),
                PowerCfgSetAction(CPU_SUBGROUP, CPU_HETERO_SHORT, ac=0, dc=0, _action_id="power:intel_hybrid:hetero_short"),
                PowerCfgSetAction(CPU_SUBGROUP, CPU_CORE_OVERUTIL, ac=85, dc=85, _action_id="power:intel_hybrid:core_overutil"),
            ],
        ),
        Optimization(
            id="disable_cpu_unpark",
            title="禁用 CPU 核心停放",
            category="power",
            preset="aggressive",
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
        # ── Intel Core Overutilization Threshold 解锁（仅 Intel hybrid） ──
        Optimization(
            id="disable_unlock_ppm",
            title="解锁处理器电源管理隐藏选项",
            category="power",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["解锁 Intel 处理器异构核心过载阈值隐藏选项"],
            side_effects=["仅 Intel 混合架构有效，AMD 平台自动跳过"],
            legacy_ids=["unlock_ppm"],
            applicability=["intel_hybrid_only"],
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
            preset="aggressive",
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
