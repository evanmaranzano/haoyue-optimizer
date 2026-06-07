from __future__ import annotations

from haoyue_optimizer.core.advisory import AdvisoryAction
from haoyue_optimizer.core.models import Optimization
from haoyue_optimizer.core.registry import RegistrySetAction
from haoyue_optimizer.core.subprocess_action import SubprocessAction


def get_optimizations() -> list[Optimization]:
    return [
        Optimization(
            id="disable_net_throttle",
            title="禁用网络节流",
            category="network",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["移除系统网络节流限制"],
            side_effects=["改变系统网络节流策略，可能影响非游戏网络行为"],
            legacy_ids=["net_throttle"],
            actions=[
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", 0xFFFFFFFF, "dword"),
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_tcp_nodelay",
            title="禁用 TCP Nagle 算法",
            category="network",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["禁用 Nagle 算法降低小包延迟"],
            side_effects=["禁用 TCP Nagle 算法，可能增加小包网络开销"],
            legacy_ids=["tcp_nodelay"],
            actions=[
                RegistrySetAction("HKLM", r"SOFTWARE\Microsoft\MSMQ\Parameters", "TCPNoDelay", 1, "dword"),
            ],
        ),
        Optimization(
            id="disable_dns_priority",
            title="优化 DNS 解析优先级",
            category="network",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["调整 DNS 和主机名解析优先级顺序"],
            side_effects=["改变 DNS 和主机名解析优先级顺序"],
            legacy_ids=["dns_priority"],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\ServiceProvider", "Class", 8, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\ServiceProvider", "DnsPriority", 6, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\ServiceProvider", "HostsPriority", 5, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\ServiceProvider", "LocalPriority", 4, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\ServiceProvider", "NetbtPriority", 7, "dword"),
            ],
        ),
        Optimization(
            id="disable_dns_negative",
            title="禁用 DNS 失败缓存",
            category="network",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["DNS 查询失败后立即重试"],
            side_effects=["禁用 DNS 失败缓存，每次查询失败都会重试"],
            legacy_ids=["dns_negative"],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters", "NegativeCacheTime", 0, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters", "NegativeSOACacheTime", 0, "dword"),
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters", "NetFailureCacheTime", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_qos_bw",
            title="取消 QoS 带宽保留",
            category="network",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["取消 QoS 带宽保留限制"],
            side_effects=["取消 QoS 带宽保留限制"],
            legacy_ids=["qos_bw"],
            actions=[
                RegistrySetAction("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Psched", "NonBestEffortLimit", 0, "dword"),
            ],
        ),
        Optimization(
            id="disable_qos_nla",
            title="QoS 禁用网络位置感知",
            category="network",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["QoS 不再依赖网络位置感知"],
            side_effects=["QoS 不再依赖网络位置感知"],
            legacy_ids=["qos_nla"],
            actions=[
                RegistrySetAction("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\QoS", "Do not use NLA", 1, "dword"),
            ],
        ),
        Optimization(
            id="disable_wifi_power",
            title="禁用 WiFi 电源管理",
            category="network",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["防止 WiFi 节电导致的延迟波动"],
            side_effects=["WiFi 电源管理禁用，笔记本耗电增加"],
            legacy_ids=["wifi_power"],
            actions=[
                RegistrySetAction("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WcmSvc\GroupPolicy", "fDisablePowerManagement", 1, "dword"),
            ],
        ),
        Optimization(
            id="experimental_nic_nagle",
            title="网卡 Nagle 算法禁用提示",
            category="network",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["提示如何按网卡禁用 Nagle 算法"],
            side_effects=["需要枚举所有网卡接口，本阶段不自动写入"],
            legacy_ids=["nic_nagle"],
            requires_reboot=False,
            actions=[
                SubprocessAction(
                    action_id="subprocess:nic_nagle",
                    target="per-NIC TcpAckFrequency/TCPNoDelay/TcpDelAckTicks",
                    apply_cmd=[
                        "powershell", "-Command",
                        "Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' | ForEach-Object { $ip=(Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DhcpIPAddress; if($ip -and $ip -ne '0.0.0.0'){ Set-ItemProperty $_.PSPath 'TcpAckFrequency' 1 -Type DWord -ErrorAction SilentlyContinue; Set-ItemProperty $_.PSPath 'TCPNoDelay' 1 -Type DWord -ErrorAction SilentlyContinue; Set-ItemProperty $_.PSPath 'TcpDelAckTicks' 0 -Type DWord -ErrorAction SilentlyContinue } }",
                    ],
                    verify_cmd=[
                        "powershell", "-Command",
                        "$ok=0; Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' | ForEach-Object { $ip=(Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DhcpIPAddress; if($ip -and $ip -ne '0.0.0.0'){ $v=(Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).TcpAckFrequency; if($v -eq 1){$ok++} } }; if($ok -gt 0){exit 0}else{exit 1}",
                    ],
                ),
            ],
        ),
        Optimization(
            id="experimental_nic_lso",
            title="网卡 LSO 禁用提示",
            category="network",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["提示如何按网卡禁用 LSO"],
            side_effects=["需要枚举所有网卡接口，本阶段不自动写入"],
            legacy_ids=["nic_lso_disable"],
            requires_reboot=False,
            actions=[
                SubprocessAction(
                    action_id="subprocess:nic_lso",
                    target="per-NIC LsoV2IPv4/LsoV2IPv6",
                    apply_cmd=[
                        "powershell", "-Command",
                        "Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' | ForEach-Object { $ip=(Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DhcpIPAddress; if($ip -and $ip -ne '0.0.0.0'){ Set-ItemProperty $_.PSPath 'LsoV2IPv4' 0 -Type DWord -ErrorAction SilentlyContinue; Set-ItemProperty $_.PSPath 'LsoV2IPv6' 0 -Type DWord -ErrorAction SilentlyContinue } }",
                    ],
                    verify_cmd=[
                        "powershell", "-Command",
                        "Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' | ForEach-Object { $ip=(Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DhcpIPAddress; if($ip -and $ip -ne '0.0.0.0'){ $v=(Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).LsoV2IPv4; if($v -eq 0){exit 0} } }; exit 1",
                    ],
                ),
            ],
        ),
        Optimization(
            id="experimental_nic_rss",
            title="网卡 RSS 优化提示",
            category="network",
            preset="aggressive",
            risk="red",
            evidence="low",
            benefit=["提示如何按网卡优化 RSS"],
            side_effects=["需要枚举所有网卡接口，本阶段不自动写入"],
            legacy_ids=["nic_rss_opt"],
            requires_reboot=False,
            actions=[
                SubprocessAction(
                    action_id="subprocess:nic_rss",
                    target="global EnableRSS + per-NIC RSS",
                    apply_cmd=[
                        "powershell", "-Command",
                        "Set-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters' 'EnableRSS' 1 -Type DWord -ErrorAction SilentlyContinue; Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' | ForEach-Object { $ip=(Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DhcpIPAddress; if($ip -and $ip -ne '0.0.0.0'){ Set-ItemProperty $_.PSPath '*RSS' 1 -Type DWord -ErrorAction SilentlyContinue; Set-ItemProperty $_.PSPath 'RSS' 1 -Type DWord -ErrorAction SilentlyContinue } }",
                    ],
                    verify_cmd=[
                        "powershell", "-Command",
                        "$v=(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters' -ErrorAction SilentlyContinue).EnableRSS; if($v -eq 1){exit 0}else{exit 1}",
                    ],
                ),
            ],
        ),
    ]
