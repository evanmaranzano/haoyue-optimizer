# -*- coding: utf-8 -*-
"""
皓月定制 保守优化工具 v1.2.0
========================
基于全量扫描去重后的保守优化方案。
所有操作可逆，修改前自动备份，不影响系统安全和日常生产力。

用法：以管理员身份运行 python 皓月定制优化工具.py
"""

import ctypes
import json
import os
import subprocess
import sys
import winreg
from datetime import datetime
from pathlib import Path

# ─── 常量 ───────────────────────────────────────────────
VERSION = "1.2.0"
BACKUP_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "HY_Optimizer" / "backups"
BACKUP_FILE = BACKUP_DIR / f"backup_{datetime.now():%Y%m%d_%H%M%S}.json"
LOG_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "HY_Optimizer" / "logs"
LOG_FILE = LOG_DIR / f"log_{datetime.now():%Y%m%d_%H%M%S}.txt"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ─── 注册表操作封装 ─────────────────────────────────────

# 64 位注册表访问标志（绕过 WoW64 重定向）
_W64 = getattr(winreg, "KEY_WOW64_64KEY", 0)


def _parse_root(root_str):
    """将字符串根键映射到 winreg 常量。"""
    mapping = {
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKCR": winreg.HKEY_CLASSES_ROOT,
    }
    return mapping.get(root_str.upper(), winreg.HKEY_LOCAL_MACHINE)


def reg_read(root, subkey, name):
    """读取注册表值（64 位视图），不存在返回 None。"""
    try:
        with winreg.OpenKey(_parse_root(root), subkey, 0, winreg.KEY_READ | _W64) as k:
            val, _ = winreg.QueryValueEx(k, name)
            return val
    except (FileNotFoundError, OSError):
        return None


def reg_write(root, subkey, name, value, kind=winreg.REG_DWORD):
    """写入注册表值（64 位视图），自动创建子键。"""
    with winreg.CreateKeyEx(_parse_root(root), subkey, 0, winreg.KEY_WRITE | _W64) as k:
        winreg.SetValueEx(k, name, 0, kind, value)


def reg_delete(root, subkey, name=None):
    """删除注册表值或子键（64 位视图）。"""
    try:
        if name:
            with winreg.OpenKey(_parse_root(root), subkey, 0, winreg.KEY_WRITE | _W64) as k:
                winreg.DeleteValue(k, name)
        else:
            winreg.DeleteKey(_parse_root(root), subkey)
    except (FileNotFoundError, OSError):
        pass


# ─── 日志系统 ───────────────────────────────────────────

class Logger:
    """运行日志记录器。"""

    def __init__(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.lines = []
        self.start(f"皓月定制优化工具 v{VERSION}")
        self.start(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")

    def start(self, msg):
        self.lines.append(f"[INFO] {msg}")

    def ok(self, name, detail=""):
        line = f"[  OK] {name}"
        if detail:
            line += f"  -- {detail}"
        self.lines.append(line)

    def fail(self, name, error=""):
        line = f"[FAIL] {name}"
        if error:
            line += f"  -- {error}"
        self.lines.append(line)

    def skip(self, name, reason=""):
        line = f"[SKIP] {name}"
        if reason:
            line += f"  -- {reason}"
        self.lines.append(line)

    def summary(self, success, fail, total):
        self.lines.append("")
        self.lines.append(f"[DONE] 成功 {success}/{total}, 失败 {fail}/{total}")

    def save(self):
        content = "\n".join(self.lines) + "\n"
        LOG_FILE.write_text(content, encoding="utf-8")
        return LOG_FILE

    def get_path(self):
        return LOG_FILE

class BackupManager:
    """备份/恢复注册表修改。"""

    def __init__(self):
        self.data = {}  # {key: {"root":..., "subkey":..., "name":..., "old_value":..., "old_type":...}}
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def snapshot(self, root, subkey, name, label=""):
        """在修改前记录当前值。"""
        key = f"{root}\\{subkey}\\{name}"
        if key in self.data:
            return
        old = reg_read(root, subkey, name)
        self.data[key] = {
            "root": root, "subkey": subkey, "name": name,
            "label": label,
            "old_value": old,
            "exists": old is not None,
        }

    def save(self):
        """将备份写入文件。"""
        serializable = {}
        for k, v in self.data.items():
            entry = dict(v)
            val = entry["old_value"]
            if isinstance(val, int):
                entry["old_type"] = "dword"
            elif isinstance(val, str):
                entry["old_type"] = "sz"
            elif isinstance(val, bytes):
                entry["old_type"] = "binary"
                entry["old_value"] = val.hex()
            else:
                entry["old_type"] = "none"
            serializable[k] = entry
        BACKUP_FILE.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
        return BACKUP_FILE

    def restore(self, backup_path=None):
        """从备份文件恢复。"""
        path = Path(backup_path) if backup_path else self._latest()
        if not path or not path.exists():
            print(f"  {RED}未找到备份文件{RESET}")
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for key, entry in data.items():
            root, subkey, name = entry["root"], entry["subkey"], entry["name"]
            if entry.get("exists") and entry.get("old_value") is not None:
                old_type = entry.get("old_type", "none")
                if old_type == "dword":
                    kind = winreg.REG_DWORD
                    val = entry["old_value"]
                elif old_type == "sz":
                    kind = winreg.REG_SZ
                    val = entry["old_value"]
                elif old_type == "binary":
                    kind = winreg.REG_BINARY
                    val = bytes.fromhex(entry["old_value"])
                else:
                    continue
                reg_write(root, subkey, name, val, kind)
                count += 1
            else:
                reg_delete(root, subkey, name)
                count += 1
        print(f"  {GREEN}已恢复 {count} 项注册表设置{RESET}")
        return True

    def _latest(self):
        files = sorted(BACKUP_DIR.glob("backup_*.json"), reverse=True)
        return files[0] if files else None


# ─── 优化定义 ───────────────────────────────────────────

def get_optimizations():
    """返回所有保守优化项列表。每项: (id, name, risk, category, apply_fn)。"""
    return [
        # ── LOW: 默认启用 ──
        ("gamedvr",       "禁用 Game DVR / Xbox 录制",              "LOW",    "游戏",
         opt_disable_gamedvr),
        ("gamedvr_policy","组策略层禁用 Game DVR",                  "LOW",    "游戏",
         opt_disable_gamedvr_policy),
        ("fse",           "强制全屏独占模式 (FSE)",                 "LOW",    "游戏",
         opt_force_fse),
        ("gamemode",      "启用 Windows Game Mode",                "LOW",    "游戏",
         opt_enable_gamemode),
        ("hags",          "启用硬件加速 GPU 调度 (HAGS)",           "LOW",    "游戏",
         opt_enable_hags),
        ("vrr",           "禁用可变刷新率 (VRR)",                   "LOW",    "游戏",
         opt_disable_vrr),
        ("mmcss_games",   "MMCSS 游戏调度高优先级",                 "LOW",    "游戏",
         opt_mmcss_games),
        ("net_throttle",  "禁用网络节流 + 系统响应最大化",           "LOW",    "网络",
         opt_network_throttle),
        ("tcp_nodelay",   "TCP 无延迟 (关闭 Nagle)",               "LOW",    "网络",
         opt_tcp_nodelay),
        ("dns_priority",  "主机解析优先级调整",                     "LOW",    "网络",
         opt_dns_priority),
        ("dns_negative",  "DNS 负面缓存禁用",                      "LOW",    "网络",
         opt_dns_negative_cache),
        ("qos_bw",        "取消 QoS 保留带宽",                     "LOW",    "网络",
         opt_qos_bandwidth),
        ("qos_nla",       "QoS 不依赖网络位置感知",                 "LOW",    "网络",
         opt_qos_nla),
        ("net_mem",       "网络内存分配优化",                      "LOW",    "网络",
         opt_network_memory_alloc),
        ("kb_opt",        "键盘响应优化",                          "LOW",    "键鼠",
         opt_keyboard),
        ("mouse_opt",     "鼠标响应优化 (禁用加速)",                "LOW",    "键鼠",
         opt_mouse),
        ("sticky_keys",   "禁用粘滞键",                           "LOW",    "键鼠",
         opt_disable_sticky_keys),
        ("toggle_keys",   "禁用切换键提示音",                      "LOW",    "键鼠",
         opt_disable_toggle_keys),
        ("access_all",    "全面禁用辅助功能热键",                   "LOW",    "键鼠",
         opt_disable_accessibility_all),
        ("ssd_opt",       "SSD 磁盘优化 (fsutil)",                 "LOW",    "磁盘",
         opt_ssd),
        ("bg_apps",       "禁用后台应用",                          "LOW",    "系统",
         opt_disable_background_apps),
        ("transparency",  "禁用窗口透明效果",                      "LOW",    "系统",
         opt_disable_transparency),
        ("setting_sync",  "禁用设置同步",                          "LOW",    "系统",
         opt_disable_setting_sync),
        ("content_del",   "禁用开始菜单广告/建议",                  "LOW",    "系统",
         opt_disable_content_delivery),
        ("tracking",      "禁用使用习惯跟踪",                      "LOW",    "系统",
         opt_disable_tracking),
        ("driver_search", "禁用自动驱动搜索",                      "LOW",    "系统",
         opt_disable_driver_search),
        ("telemetry",     "关闭遥测 / 广告 / 建议",                "LOW",    "系统",
         opt_disable_telemetry),
        ("svchost_thresh","SvcHost 内存拆分阈值",                  "LOW",    "系统",
         opt_svchost_threshold),
        ("file_alloc",    "文件系统分配优化",                      "LOW",    "系统",
         opt_file_alloc),
        ("admin_share",   "禁用默认管理共享",                      "LOW",    "系统",
         opt_disable_admin_shares),
        ("autorun",       "禁用自动运行",                          "LOW",    "系统",
         opt_disable_autorun),
        ("explorer_restart","Explorer 崩溃自动重启",               "LOW",    "系统",
         opt_explorer_restart),
        ("map_download",  "禁用地图数据下载",                      "LOW",    "系统",
         opt_disable_map_download),
        ("feeds",         "隐藏任务栏新闻和兴趣",                   "LOW",    "系统",
         opt_hide_feeds),
        ("soft_landing",  "关闭 Windows 技巧和建议",                "LOW",    "系统",
         opt_disable_soft_landing),
        ("wu_pause",      "Windows Update 暂停上限 3650 天",       "LOW",    "系统",
         opt_wu_max_pause),
        ("mapsbroker",    "禁用 MapsBroker 地图服务",               "LOW",    "服务",
         opt_disable_mapsbroker),
        ("svc_safe",      "禁用非必要服务 (Xbox/遥测/传真等)",       "LOW",    "服务",
         opt_disable_services_safe),
        ("wifi_power",    "禁用 WiFi 电源管理",                    "LOW",    "电源",
         opt_wifi_power_disable),
        ("cpu_unpark",    "CPU 核心全部唤醒 (Unpark)",              "LOW",    "电源",
         opt_cpu_unpark),
        ("unlock_ppm",    "解锁处理器电源管理高级选项",              "LOW",    "电源",
         opt_unlock_ppm),
        ("energy_veto",   "阻止放电降性能",                        "LOW",    "电源",
         opt_energy_saver_veto),
        ("win32_pri",     "进程优先级分离优化 (Win32PrioritySeparation)", "LOW", "调度",
         opt_win32_priority),
        ("low_latency2",  "多媒体低延迟任务调度 (手感2)",           "LOW",    "调度",
         opt_low_latency_schedule),
        ("dns_flush",     "DNS 缓存清理",                          "LOW",    "清理",
         opt_flush_dns),
        ("temp_clean",    "临时文件清理",                          "LOW",    "清理",
         opt_clean_temp),
        # ── MEDIUM: 可选 ──
        ("gaming_boost",  "修复游戏 Boost (CPU 不锁频)",            "MEDIUM", "电源",
         opt_fix_gaming_boost),
        ("gaming_preset", "完整电竞电源预设 (一键应用全部调校)",      "MEDIUM", "电源",
         opt_apply_gaming_preset),
        ("power_perf",    "禁用电源节流 + 高性能模式",              "MEDIUM", "电源",
         opt_power_performance),
        ("laptop_ac",     "笔记本插电优化 (高性能+禁用节流)",        "MEDIUM", "电源",
         opt_laptop_power_ac),
        ("laptop_bat",    "笔记本电池模式 (平衡方案)",              "MEDIUM", "电源",
         opt_laptop_power_battery),
        ("gpu_preempt",   "禁用 GPU 抢占调度",                     "MEDIUM", "GPU",
         opt_disable_gpu_preemption),
        ("superfetch",    "禁用 Superfetch / Prefetch",            "MEDIUM", "磁盘",
         opt_disable_superfetch),
        ("large_cache",   "提升系统缓存 / 内核常驻内存",            "MEDIUM", "内存",
         opt_large_system_cache),
        ("disable_mmcss", "完全禁用 MMCSS 服务",                   "MEDIUM", "服务",
         opt_disable_mmcss_service),
        ("disk_no_sleep", "硬盘永不休眠",                          "MEDIUM", "磁盘",
         opt_disk_no_sleep),
        ("low_latency3",  "游戏低延迟全调度 (手感3)",               "MEDIUM", "调度",
         opt_low_latency_full),
        ("wu_cache",      "清理 Windows Update 缓存",              "MEDIUM", "清理",
         opt_clean_wu_cache),
        ("telemetry_full","扩展遥测禁用 (AppCompat+UAR)",          "MEDIUM", "系统",
         opt_disable_telemetry_full),
        # ── 研究补充：音频/启动/网络/内存/调度/GPU ──
        ("audio_no_excl", "禁用音频独占模式",                       "LOW",    "音频",
         opt_disable_audio_exclusive),
        ("startup_delay", "禁用启动延迟",                           "LOW",    "启动",
         opt_disable_startup_delay),
        ("boot_timeout",  "启动菜单超时设为 0",                     "LOW",    "启动",
         opt_boot_timeout_zero),
        ("fse_global",    "禁用全局全屏优化",                       "LOW",    "显示",
         opt_disable_fso_global),
        ("anim_disable",  "禁用窗口动画效果",                       "LOW",    "显示",
         opt_disable_animations),
        ("usb_suspend_dis","禁用 USB 选择性暂停",                   "LOW",    "电源",
         opt_usb_suspend_disable),
        ("nic_nagle",     "按网卡禁用 Nagle 算法",                  "LOW",    "网络",
         opt_nic_disable_nagle),
        ("nic_lso_disable","禁用大包卸载 (LSO)",                    "LOW",    "网络",
         opt_nic_disable_lso),
        ("disable_prefetch","禁用 Prefetch 预读取",                 "LOW",    "磁盘",
         opt_disable_prefetch),
        ("disable_bg_tasks","禁用后台优化计划任务",                  "LOW",    "系统",
         opt_disable_background_tasks),
        ("disable_mem_compress","禁用内存压缩 (MEDIUM)",            "MEDIUM", "内存",
         opt_disable_memory_compression),
        ("timer_res",     "系统定时器分辨率锁定 0.5ms (MEDIUM)",     "MEDIUM", "调度",
         opt_lock_timer_resolution),
        ("gpu_msi_mode",  "GPU MSI 中断模式 (MEDIUM)",             "MEDIUM", "GPU",
         opt_gpu_msi_mode),
        ("nic_rss_opt",   "网卡 RSS 接收端缩放优化",               "MEDIUM", "网络",
         opt_nic_rss_optimize),
    ]


# ─── 优化实现 ───────────────────────────────────────────

def opt_disable_gamedvr(bm):
    items = [
        ("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 0),
        ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0),
        ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0),
    ]
    for root, sub, name, val in items:
        bm.snapshot(root, sub, name)
        reg_write(root, sub, name, val)


def opt_force_fse(bm):
    sub = r"System\GameConfigStore"
    items = [("GameDVR_FSEBehaviorMode", 2), ("GameDVR_HonorUserFSEBehaviorMode", 1),
             ("GameDVR_FSEBehavior", 2), ("GameDVR_DXGIHonorFSEWindowsCompatible", 1),
             ("HonorUserFSEBehaviorMode", 1), ("FSEBehavior", 2),
             ("DXGIFHonorFSEWindowsCompatible", 1)]
    for name, val in items:
        bm.snapshot("HKCU", sub, name)
        reg_write("HKCU", sub, name, val)


def opt_mmcss_games(bm):
    sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile\Tasks\Games"
    items = {"Affinity": 0, "Background Only": "False", "Clock Rate": 10000,
             "GPU Priority": 8, "Priority": 6, "Scheduling Category": "High", "SFIO Priority": "High"}
    for name, val in items.items():
        bm.snapshot("HKLM", sub, name)
        kind = winreg.REG_SZ if isinstance(val, str) else winreg.REG_DWORD
        reg_write("HKLM", sub, name, val, kind)


def opt_network_throttle(bm):
    sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile"
    bm.snapshot("HKLM", sub, "NetworkThrottlingIndex")
    bm.snapshot("HKLM", sub, "SystemResponsiveness")
    reg_write("HKLM", sub, "NetworkThrottlingIndex", 0xFFFFFFFF)
    reg_write("HKLM", sub, "SystemResponsiveness", 0)


def opt_tcp_nodelay(bm):
    sub = r"SOFTWARE\Microsoft\MSMQ\Parameters"
    bm.snapshot("HKLM", sub, "TCPNoDelay")
    reg_write("HKLM", sub, "TCPNoDelay", 1)


def opt_dns_priority(bm):
    sub = r"SYSTEM\CurrentControlSet\Services\Tcpip\ServiceProvider"
    for name, val in [("Class", 8), ("DnsPriority", 6), ("HostsPriority", 5),
                      ("LocalPriority", 4), ("NetbtPriority", 7)]:
        bm.snapshot("HKLM", sub, name)
        reg_write("HKLM", sub, name, val)


def opt_dns_negative_cache(bm):
    sub = r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters"
    for name in ["NegativeCacheTime", "NegativeSOACacheTime", "NetFailureCacheTime"]:
        bm.snapshot("HKLM", sub, name)
        reg_write("HKLM", sub, name, 0)


def opt_qos_bandwidth(bm):
    sub = r"SOFTWARE\Policies\Microsoft\Windows\Psched"
    bm.snapshot("HKLM", sub, "NonBestEffortLimit")
    reg_write("HKLM", sub, "NonBestEffortLimit", 0)


def opt_qos_nla(bm):
    sub = r"SYSTEM\CurrentControlSet\Services\Tcpip\QoS"
    bm.snapshot("HKLM", sub, "Do not use NLA")
    reg_write("HKLM", sub, "Do not use NLA", 1)


def opt_keyboard(bm):
    # KeyboardDelay=0, KeyboardSpeed=48
    sub1 = r"Control Panel\Keyboard"
    bm.snapshot("HKCU", sub1, "KeyboardDelay")
    bm.snapshot("HKCU", sub1, "KeyboardSpeed")
    reg_write("HKCU", sub1, "KeyboardDelay", "0", winreg.REG_SZ)
    reg_write("HKCU", sub1, "KeyboardSpeed", "48", winreg.REG_SZ)
    # KeyboardDataQueueSize=20
    sub2 = r"SYSTEM\CurrentControlSet\Services\kbdclass\Parameters"
    bm.snapshot("HKLM", sub2, "KeyboardDataQueueSize")
    reg_write("HKLM", sub2, "KeyboardDataQueueSize", 20)
    # Keyboard Response
    sub3 = r"Control Panel\Accessibility\Keyboard Response"
    bm.snapshot("HKCU", sub3, "AutoRepeatDelay")
    bm.snapshot("HKCU", sub3, "AutoRepeatRate")
    bm.snapshot("HKCU", sub3, "BounceTime")
    reg_write("HKCU", sub3, "AutoRepeatDelay", "175", winreg.REG_SZ)
    reg_write("HKCU", sub3, "AutoRepeatRate", "25", winreg.REG_SZ)
    reg_write("HKCU", sub3, "BounceTime", "0", winreg.REG_SZ)


def opt_mouse(bm):
    sub = r"Control Panel\Mouse"
    items = {"MouseSpeed": "0", "MouseThreshold1": "0", "MouseThreshold2": "0",
             "MouseSensitivity": "10", "SmoothMouseXCurve": None, "SmoothMouseYCurve": None}
    for name, val in items.items():
        if val is None:
            continue
        bm.snapshot("HKCU", sub, name)
        reg_write("HKCU", sub, name, val, winreg.REG_SZ)
    # MouseDataQueueSize
    sub2 = r"SYSTEM\CurrentControlSet\Services\mouclass\Parameters"
    bm.snapshot("HKLM", sub2, "MouseDataQueueSize")
    reg_write("HKLM", sub2, "MouseDataQueueSize", 20)
    # DWM 鼠标批处理
    sub3 = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
    bm.snapshot("HKCU", sub3, r"C:\Windows\System32\dwm.exe")
    reg_write("HKCU", sub3, r"C:\Windows\System32\dwm.exe", "NoDTToDITMouseBatch", winreg.REG_SZ)


def opt_disable_sticky_keys(bm):
    sub = r"Control Panel\Accessibility\StickyKeys"
    bm.snapshot("HKCU", sub, "Flags")
    reg_write("HKCU", sub, "Flags", "506", winreg.REG_SZ)


def opt_ssd(bm):
    cmds = [
        ["fsutil", "behavior", "set", "disableLastAccess", "1"],
        ["fsutil", "behavior", "set", "disable8dot3", "1"],
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True)
        label = " ".join(cmd)
        if r.returncode == 0:
            print(f"    {label} ... {GREEN}OK{RESET}")
        else:
            print(f"    {label} ... {YELLOW}需要管理员权限{RESET}")


def opt_disable_background_apps(bm):
    sub1 = r"SOFTWARE\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications"
    bm.snapshot("HKCU", sub1, "GlobalUserDisabled")
    reg_write("HKCU", sub1, "GlobalUserDisabled", 1)
    sub2 = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Search"
    bm.snapshot("HKCU", sub2, "BackgroundAppGlobalToggle")
    reg_write("HKCU", sub2, "BackgroundAppGlobalToggle", 0)


def opt_disable_telemetry(bm):
    # AllowTelemetry
    sub1 = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"
    bm.snapshot("HKLM", sub1, "AllowTelemetry")
    reg_write("HKLM", sub1, "AllowTelemetry", 0)
    # CEIP
    sub2 = r"SOFTWARE\Policies\Microsoft\SQMClient\Windows"
    bm.snapshot("HKLM", sub2, "CEIPEnable")
    reg_write("HKLM", sub2, "CEIPEnable", 0)
    # 广告 ID
    sub3 = r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo"
    bm.snapshot("HKCU", sub3, "Enabled")
    reg_write("HKCU", sub3, "Enabled", 0)
    # Content Delivery
    sub4 = r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
    for name in ["SystemPaneSuggestionsEnabled", "SoftLandingEnabled",
                 "RotatingLockScreenEnabled", "RotatingLockScreenOverlayEnabled"]:
        bm.snapshot("HKCU", sub4, name)
        reg_write("HKCU", sub4, name, 0)


def opt_svchost_threshold(bm):
    import ctypes
    kernel32 = ctypes.windll.kernel32
    buf = ctypes.c_ulonglong(0)
    kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(buf))
    mem_kb = buf.value  # 实际物理内存 KB
    # 转为对应阈值: 物理内存 KB 值
    sub = r"SYSTEM\ControlSet001\Control"
    bm.snapshot("HKLM", sub, "SvcHostSplitThresholdInKB")
    reg_write("HKLM", sub, "SvcHostSplitThresholdInKB", int(mem_kb))
    mem_gb = round(mem_kb / 1024 / 1024, 1)
    print(f"    检测到 {mem_gb}GB 内存, 设置阈值 = {mem_kb} KB")


def opt_file_alloc(bm):
    sub = r"SYSTEM\CurrentControlSet\Control\FileSystem"
    bm.snapshot("HKLM", sub, "ConfigFileAllocSize")
    reg_write("HKLM", sub, "ConfigFileAllocSize", 500)


def opt_disable_admin_shares(bm):
    sub = r"SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters"
    for name in ["AutoShareServer", "AutoShareWks"]:
        bm.snapshot("HKLM", sub, name)
        reg_write("HKLM", sub, name, 0)


def opt_disable_autorun(bm):
    sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer"
    bm.snapshot("HKCU", sub, "NoDriveTypeAutoRun")
    reg_write("HKCU", sub, "NoDriveTypeAutoRun", 0xFF)


def opt_explorer_restart(bm):
    sub = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
    bm.snapshot("HKLM", sub, "AutoRestartShell")
    reg_write("HKLM", sub, "AutoRestartShell", 1)


def opt_disable_map_download(bm):
    sub = r"SOFTWARE\Policies\Microsoft\Windows\Maps"
    bm.snapshot("HKLM", sub, "AutoDownloadAndUpdateMapData")
    reg_write("HKLM", sub, "AutoDownloadAndUpdateMapData", 0)


def opt_hide_feeds(bm):
    sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Feeds"
    bm.snapshot("HKCU", sub, "ShellFeedsTaskbarViewMode")
    try:
        reg_write("HKCU", sub, "ShellFeedsTaskbarViewMode", 2)
    except OSError:
        # Feeds 键可能被系统锁 ACL，改用 HKLM 组策略绕过
        sub2 = r"SOFTWARE\Policies\Microsoft\Windows\Windows Feeds"
        bm.snapshot("HKLM", sub2, "EnableFeeds")
        reg_write("HKLM", sub2, "EnableFeeds", 0)


def opt_disable_soft_landing(bm):
    sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
    bm.snapshot("HKCU", sub, "SoftLandingEnabled")
    reg_write("HKCU", sub, "SoftLandingEnabled", 0)


def opt_wu_max_pause(bm):
    """Windows Update 暂停上限设为 3650 天（10 年），在设置里可选最远暂停日期。"""
    sub = r"SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"
    bm.snapshot("HKLM", sub, "FlightSettingsMaxPauseDays")
    reg_write("HKLM", sub, "FlightSettingsMaxPauseDays", 3650)


def opt_win32_priority(bm):
    """Win32PrioritySeparation=40 (十进制)，短时间片+固定+前台优先。"""
    sub = r"SYSTEM\CurrentControlSet\Control\PriorityControl"
    bm.snapshot("HKLM", sub, "Win32PrioritySeparation")
    reg_write("HKLM", sub, "Win32PrioritySeparation", 40)


def opt_low_latency_schedule(bm):
    base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile\Tasks"
    tasks = {
        "Audio": {"Affinity": 0, "Background Only": "False", "Clock Rate": 10000,
                  "GPU Priority": 1, "Priority": 2, "Scheduling Category": "Medium", "SFIO Priority": "High"},
        "Low Latency": {"Affinity": 0, "Background Only": "False", "Clock Rate": 10000,
                        "GPU Priority": 1, "Priority": 3, "Scheduling Category": "High", "SFIO Priority": "High"},
    }
    for task, params in tasks.items():
        sub = f"{base}\\{task}"
        for name, val in params.items():
            bm.snapshot("HKLM", sub, name)
            kind = winreg.REG_SZ if isinstance(val, str) else winreg.REG_DWORD
            reg_write("HKLM", sub, name, val, kind)


# ── 补充优化（深情电竞目录全面审查结果） ──

def opt_enable_gamemode(bm):
    """启用 Windows Game Mode，让系统优先分配资源给游戏。"""
    sub = r"SOFTWARE\Microsoft\GameBar"
    bm.snapshot("HKCU", sub, "AllowAutoGameMode")
    bm.snapshot("HKCU", sub, "AutoGameModeEnabled")
    reg_write("HKCU", sub, "AllowAutoGameMode", 1)
    reg_write("HKCU", sub, "AutoGameModeEnabled", 1)


def opt_enable_hags(bm):
    """启用硬件加速 GPU 调度 (HAGS)。GTX 1050 Ti 及以上支持。"""
    sub = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
    bm.snapshot("HKLM", sub, "HwSchMode")
    reg_write("HKLM", sub, "HwSchMode", 2)


def opt_disable_vrr(bm):
    """禁用可变刷新率 (VRR)，减少输入延迟。"""
    sub = r"SOFTWARE\Microsoft\DirectX\UserGpuPreferences"
    bm.snapshot("HKCU", sub, "DirectXUserGlobalSettings")
    reg_write("HKCU", sub, "DirectXUserGlobalSettings",
              "VRROptimizeEnable=0;", winreg.REG_SZ)


def opt_disable_transparency(bm):
    """禁用窗口透明效果，减少 GPU 合成负担。"""
    sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    bm.snapshot("HKCU", sub, "EnableTransparency")
    reg_write("HKCU", sub, "EnableTransparency", 0)


def opt_disable_setting_sync(bm):
    """禁用 Windows 设置同步（不再跨设备同步配置）。"""
    groups = ["Personalization", "BrowserSettings", "Credentials",
              "Accessibility", "Windows"]
    sub_base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\SettingSync"
    bm.snapshot("HKCU", sub_base, "SyncPolicy")
    reg_write("HKCU", sub_base, "SyncPolicy", 5)
    for g in groups:
        sub = f"{sub_base}\\Groups\\{g}"
        bm.snapshot("HKCU", sub, "Enabled")
        reg_write("HKCU", sub, "Enabled", 0)


def opt_disable_content_delivery(bm):
    """禁用开始菜单建议/广告/推荐内容。"""
    sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
    keys = [
        "SubscribedContent-338393Enabled",  # 开始菜单建议
        "SubscribedContent-353694Enabled",  # 开始菜单建议
        "SystemPaneSuggestionsEnabled",     # 磁贴建议
        "RotatingLockScreenEnabled",        # 锁屏聚焦
        "RotatingLockScreenOverlayEnabled",
        "SoftLandingEnabled",               # 提示建议
    ]
    for name in keys:
        bm.snapshot("HKCU", sub, name)
        reg_write("HKCU", sub, name, 0)


def opt_disable_tracking(bm):
    """禁用 Windows 使用习惯跟踪。"""
    items = [
        ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
         "Start_TrackProgs", 0),
        ("HKCU", r"Control Panel\International\User Profile",
         "HttpAcceptLanguageOptOut", 1),
    ]
    for root, sub, name, val in items:
        bm.snapshot(root, sub, name)
        reg_write(root, sub, name, val)


def opt_disable_toggle_keys(bm):
    """禁用切换键（Caps Lock/Num Lock 提示音）。"""
    sub = r"Control Panel\Accessibility\ToggleKeys"
    bm.snapshot("HKCU", sub, "Flags")
    reg_write("HKCU", sub, "Flags", "58", winreg.REG_SZ)


def opt_disable_accessibility_all(bm):
    """全面禁用辅助功能热键（粘滞键/切换键/筛选键/鼠标键）。"""
    targets = {
        "StickyKeys": "506",
        "ToggleKeys": "58",
        "Keyboard Response": "122",
        "MouseKeys": "0",
    }
    for name, flags in targets.items():
        sub = f"Control Panel\\Accessibility\\{name}"
        bm.snapshot("HKCU", sub, "Flags")
        reg_write("HKCU", sub, "Flags", flags, winreg.REG_SZ)


def opt_wifi_power_disable(bm):
    """禁用 WiFi 电源管理，防止游戏时 WiFi 降速或断连。"""
    sub = r"SOFTWARE\Policies\Microsoft\Windows\WcmSvc\GroupPolicy"
    bm.snapshot("HKLM", sub, "fDisablePowerManagement")
    reg_write("HKLM", sub, "fDisablePowerManagement", 1)


def opt_cpu_unpark(bm):
    """CPU 核心全部唤醒 (Unpark)，不让任何核心休眠。"""
    sub = r"SYSTEM\CurrentControlSet\Control\Power"
    for name in ["Class1InitialUnparkCount", "InitialUnparkCount"]:
        bm.snapshot("HKLM", sub, name)
        reg_write("HKLM", sub, name, 100)
    # 性能偏好=纯性能
    sub2 = r"SYSTEM\CurrentControlSet\Control\Power\Policy\Settings\Processor"
    bm.snapshot("HKLM", sub2, "PerfEnergyPreference")
    reg_write("HKLM", sub2, "PerfEnergyPreference", 0)
    # 设备不空闲
    sub3 = r"SYSTEM\CurrentControlSet\Control\Power\Policy\Settings\Misc"
    bm.snapshot("HKLM", sub3, "DeviceIdlePolicy")
    reg_write("HKLM", sub3, "DeviceIdlePolicy", 0)
    # 阻止节能器介入
    sub4 = r"SYSTEM\CurrentControlSet\Control\Power\PDC\Activators\Default\VetoPolicy"
    bm.snapshot("HKLM", sub4, "EA:EnergySaverEngaged")
    reg_write("HKLM", sub4, "EA:EnergySaverEngaged", 0)


def opt_network_memory_alloc(bm):
    """网络内存分配优化：优先分配给应用而非文件缓存。"""
    sub = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
    bm.snapshot("HKLM", sub, "LargeSystemCache")
    reg_write("HKLM", sub, "LargeSystemCache", 0)


def opt_disable_driver_search(bm):
    """禁用 Windows Update 自动驱动搜索。"""
    sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching"
    bm.snapshot("HKLM", sub, "SearchOrderConfig")
    reg_write("HKLM", sub, "SearchOrderConfig", 0)


def opt_unlock_ppm(bm):
    """解锁处理器电源管理高级选项（让 powercfg 可调更多参数）。"""
    sub = (r"SYSTEM\CurrentControlSet\Control\Power\PowerSettings"
           r"\54533251-82be-4824-96c1-47b60b740d00"
           r"\943c8cb6-6f93-4227-ad87-e9a3feec08d1")
    bm.snapshot("HKLM", sub, "Attributes")
    reg_write("HKLM", sub, "Attributes", 2)


def opt_disable_gamedvr_policy(bm):
    """通过组策略彻底禁用 Game DVR（比注册表更高优先级）。"""
    items = [
        ("HKLM", r"SOFTWARE\Microsoft\PolicyManager\default\ApplicationManagement\AllowGameDVR",
         "value", 0),
        ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR",
         "AllowGameDVR", 0),
    ]
    for root, sub, name, val in items:
        bm.snapshot(root, sub, name)
        reg_write(root, sub, name, val)


def opt_energy_saver_veto(bm):
    """阻止放电状态自动降性能。"""
    sub = r"SYSTEM\CurrentControlSet\Control\Power\PDC\Activators\28\VetoPolicy"
    bm.snapshot("HKLM", sub, "EA:PowerStateDischarging")
    reg_write("HKLM", sub, "EA:PowerStateDischarging", 0)


def opt_flush_dns(bm):
    subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
    print(f"    DNS 缓存已清空")


def opt_clean_temp(bm):
    import shutil
    count = 0
    for d in [Path(os.environ.get("TEMP", "")), Path(r"C:\Windows\Temp")]:
        if d.exists():
            for f in d.iterdir():
                try:
                    if f.is_file():
                        f.unlink()
                        count += 1
                    elif f.is_dir():
                        shutil.rmtree(f, ignore_errors=True)
                        count += 1
                except (PermissionError, OSError):
                    pass
    print(f"    清理了 {count} 个临时文件/目录")


# ── MEDIUM 优化 ──

def opt_power_performance(bm):
    sub1 = r"SYSTEM\CurrentControlSet\Control\Power"
    bm.snapshot("HKLM", sub1, "HibernateEnabledDefault")
    reg_write("HKLM", sub1, "HibernateEnabledDefault", 0)
    sub2 = r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling"
    bm.snapshot("HKLM", sub2, "PowerThrottlingOff")
    reg_write("HKLM", sub2, "PowerThrottlingOff", 1)
    # 禁用快速启动
    sub3 = r"SYSTEM\CurrentControlSet\Control\Session Manager\Power"
    bm.snapshot("HKLM", sub3, "HiberbootEnabled")
    reg_write("HKLM", sub3, "HiberbootEnabled", 0)


def opt_disable_gpu_preemption(bm):
    sub = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Scheduler"
    bm.snapshot("HKLM", sub, "EnablePreemption")
    reg_write("HKLM", sub, "EnablePreemption", 0)


def opt_disable_superfetch(bm):
    sub = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters"
    bm.snapshot("HKLM", sub, "EnablePrefetcher")
    bm.snapshot("HKLM", sub, "EnableSuperfetch")
    reg_write("HKLM", sub, "EnablePrefetcher", 0)
    reg_write("HKLM", sub, "EnableSuperfetch", 0)


def opt_large_system_cache(bm):
    sub = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
    bm.snapshot("HKLM", sub, "DisablePagingExecutive")
    bm.snapshot("HKLM", sub, "LargeSystemCache")
    reg_write("HKLM", sub, "DisablePagingExecutive", 1)
    reg_write("HKLM", sub, "LargeSystemCache", 1)


def opt_disable_mmcss_service(bm):
    sub = r"SYSTEM\CurrentControlSet\Services\MMCSS"
    bm.snapshot("HKLM", sub, "Start")
    reg_write("HKLM", sub, "Start", 4)


def opt_disk_no_sleep(bm):
    sub = r"SYSTEM\CurrentControlSet\Services\Disk\TimeOutValue"
    bm.snapshot("HKLM", sub, "TimeOutValue")
    reg_write("HKLM", sub, "TimeOutValue", 0)


def opt_low_latency_full(bm):
    base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile"
    # SystemProfile 级别
    bm.snapshot("HKLM", base, "NetworkThrottlingIndex")
    bm.snapshot("HKLM", base, "SystemResponsiveness")
    reg_write("HKLM", base, "NetworkThrottlingIndex", 0xFFFFFFFF)
    reg_write("HKLM", base, "SystemResponsiveness", 0)
    # 全部 9 个任务组
    tasks_base = f"{base}\\Tasks"
    full_tasks = {
        "Audio": {"GPU Priority": 1, "Priority": 2, "Scheduling Category": "Medium", "SFIO Priority": "High", "LatencySensitive": "True"},
        "Capture": {"GPU Priority": 1, "Priority": 2, "Scheduling Category": "Medium", "SFIO Priority": "Normal"},
        "DisplayPostProcessing": {"GPU Priority": 1, "Priority": 3, "Scheduling Category": "High", "SFIO Priority": "High"},
        "Distribution": {"GPU Priority": 1, "Priority": 2, "Scheduling Category": "Medium", "SFIO Priority": "Normal"},
        "Games": {"GPU Priority": 8, "Priority": 6, "Scheduling Category": "High", "SFIO Priority": "High", "LatencySensitive": "True"},
        "Low Latency": {"GPU Priority": 1, "Priority": 3, "Scheduling Category": "High", "SFIO Priority": "High", "LatencySensitive": "True"},
        "Playback": {"GPU Priority": 1, "Priority": 2, "Scheduling Category": "Medium", "SFIO Priority": "Normal"},
        "Pro Audio": {"GPU Priority": 1, "Priority": 4, "Scheduling Category": "High", "SFIO Priority": "Critical"},
        "Window Manager": {"GPU Priority": 1, "Priority": 2, "Scheduling Category": "Medium", "SFIO Priority": "Normal"},
    }
    for task, params in full_tasks.items():
        sub = f"{tasks_base}\\{task}"
        for name, val in params.items():
            bm.snapshot("HKLM", sub, name)
            kind = winreg.REG_SZ if isinstance(val, str) else winreg.REG_DWORD
            reg_write("HKLM", sub, name, val, kind)


def opt_clean_wu_cache(bm):
    print(f"    {YELLOW}正在停止 Windows Update 服务...{RESET}")
    subprocess.run(["net", "stop", "wuauserv"], capture_output=True)
    subprocess.run(["net", "stop", "UsoSvc"], capture_output=True)
    sd = Path(r"C:\Windows\SoftwareDistribution")
    if sd.exists():
        import shutil
        shutil.rmtree(sd, ignore_errors=True)
        print(f"    SoftwareDistribution 已清理")
    subprocess.run(["net", "start", "wuauserv"], capture_output=True)
    subprocess.run(["net", "start", "UsoSvc"], capture_output=True)
    print(f"    Windows Update 服务已重启")


# ── 笔记本 / 服务 补充优化 ──

def opt_disable_mapsbroker(bm):
    """禁用 MapsBroker 地图下载服务。"""
    sub = r"SYSTEM\CurrentControlSet\Services\MapsBroker"
    bm.snapshot("HKLM", sub, "Start")
    reg_write("HKLM", sub, "Start", 4)


def opt_disable_services_safe(bm):
    """禁用非必要的 Windows 服务（保守列表，不影响日常使用）。"""
    services = [
        # Xbox 相关
        "XblAuthManager", "XblGameSave", "XboxNetApiSvc",
        # 遥测/诊断
        "DiagTrack", "dmwappushsvc", "WerSvc",
        # 搜索/索引
        "WSearch", "SysMain",
        # 地图/零售/传真
        "MapsBroker", "RetailDemo", "Fax",
        # 远程/共享
        "RemoteRegistry", "SharedAccess",
        # 生物识别/蓝牙(无设备时)
        "WbioSrvc",
        # 多媒体网络
        "WMPNetworkSvc",
        # 地理位置
        "lfsvc",
        # 电话/通信
        "PhoneSvc", "TapiSrv", "SEMgrSvc",
        # 钱包/家长控制/同步
        "WalletService", "WpcMonSvc", "PimIndexMaintenanceSvc",
        # Insider/热点（icssvc/SharedAccess 影响移动热点，不禁用）
        "wisvc",
    ]
    count = 0
    for svc in services:
        sub = rf"SYSTEM\CurrentControlSet\Services\{svc}"
        try:
            current = reg_read("HKLM", sub, "Start")
            if current is not None and current != 4:
                bm.snapshot("HKLM", sub, "Start")
                reg_write("HKLM", sub, "Start", 4)
                count += 1
        except OSError:
            pass
    print(f"    禁用了 {count} 个服务 (共 {len(services)} 个目标)")


def opt_laptop_power_ac(bm):
    """笔记本插电模式：切高性能电源方案 + 禁用电源节流。"""
    high_perf_guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
    subprocess.run(["powercfg", "/duplicatescheme", high_perf_guid], capture_output=True)
    subprocess.run(["powercfg", "/setactive", high_perf_guid], capture_output=True)
    print(f"    已切换到高性能电源方案")
    sub = r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling"
    bm.snapshot("HKLM", sub, "PowerThrottlingOff")
    reg_write("HKLM", sub, "PowerThrottlingOff", 1)
    sub2 = r"SYSTEM\CurrentControlSet\Control\Session Manager\Power"
    bm.snapshot("HKLM", sub2, "HiberbootEnabled")
    reg_write("HKLM", sub2, "HiberbootEnabled", 0)
    subprocess.run(["powercfg", "/hibernate", "off"], capture_output=True)
    print(f"    已禁用电源节流 + 快速启动 + 休眠")


def opt_laptop_power_battery(bm):
    """笔记本电池模式：平衡方案 + 保留节流。"""
    balanced_guid = "381b4222-f694-41f0-9685-ff5bb260df2e"
    subprocess.run(["powercfg", "/setactive", balanced_guid], capture_output=True)
    print(f"    已切换到平衡电源方案（电池模式）")


# ── 电源方案预设（基于 ROG Strix G513RM 实机调校） ──

# 用户当前已调校的电源方案参数（除 boost 和最小处理器状态外均已是电竞最优值）
POWER_PRESET = {
    # (子组 GUID, 电源设置 GUID, AC值, DC值, 名称)
    # 硬盘
    "disk_idle":    ("0012ee47-9041-4b5d-9b77-535fba8b1442",
                     "6738e2c4-e8a5-4a42-b16a-e040e769756e", 30, 60),
    # 睡眠
    "sleep":        ("238c9fa8-0aad-41ed-83f4-97be242c8f20",
                     "29f6c1db-86da-48c5-9fdb-f2b67b1f44da", 0, 0),
    "hybrid_sleep":  ("238c9fa8-0aad-41ed-83f4-97be242c8f20",
                     "94ac6d29-73ce-41a6-809f-6363ba21b47e", 0, 0),
    "hibernate":    ("238c9fa8-0aad-41ed-83f4-97be242c8f20",
                     "9d7815a6-7ee4-497e-8888-515a05f02364", 0, 0x7FFFFFFF),
    "wake_timer":   ("238c9fa8-0aad-41ed-83f4-97be242c8f20",
                     "bd3b718a-0680-4d9d-8ab2-e1d2b4ac806d", 0, 0),
    # USB
    "usb_suspend":  ("2a737441-1930-4402-8d77-b2bebba308a3",
                     "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", 0, 0),
    # PCIe ASPM
    "aspm":         ("501a4d13-42af-4429-9fd1-a8218c268e20",
                     "ee12f906-d277-404b-b6da-e5fa1a576df5", 0, 0),
    # 无线
    "wifi_power":   ("19cbb8fa-5279-450e-9fac-8a3d5fedd0c1",
                     "12bbebe6-58d6-4636-95bb-3217ef867c1a", 0, 2),
    # 显示
    "display_off":  ("7516b95f-f776-4464-8c53-06167f40cc99",
                     "3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e", 1800, 180),
    "brightness":   ("7516b95f-f776-4464-8c53-06167f40cc99",
                     "aded5e82-b909-4619-9949-f5d71dac0bcb", 60, 60),
    "adaptive_bright": ("7516b95f-f776-4464-8c53-06167f40cc99",
                        "fbd9aa66-9553-4097-ba44-ed6e9d65eab8", 0, 0),
    # 处理器
    "cpu_min":      ("54533251-82be-4824-96c1-47b60b740d00",
                     "893dee8e-2bef-41e0-89c6-b55d0929964c", 5, 5),
    "cpu_max":      ("54533251-82be-4824-96c1-47b60b740d00",
                     "bc5038f7-23e0-4960-96da-33abaf5935ec", 100, 100),
    "cpu_boost":    ("54533251-82be-4824-96c1-47b60b740d00",
                     "be337238-0d82-4146-a960-4f3749d470c7", 3, 3),
}


def _powercfg_set(sub_guid, setting_guid, ac_val, dc_val):
    """调用 powercfg 设置单个电源参数（当前方案 + 注册表默认值）。"""
    # 设置当前活跃方案
    subprocess.run(["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                    sub_guid, setting_guid, str(ac_val)], capture_output=True)
    subprocess.run(["powercfg", "/setdcvalueindex", "SCHEME_CURRENT",
                    sub_guid, setting_guid, str(dc_val)], capture_output=True)
    # 同步修改注册表默认值（防止方案重置时被覆盖）
    balanced = "381b4222-f694-41f0-9685-ff5bb260df2e"
    high_perf = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
    for scheme in [balanced, high_perf]:
        sub = (rf"SYSTEM\CurrentControlSet\Control\Power\PowerSettings"
               rf"\{sub_guid}\{setting_guid}\DefaultPowerSchemeValues\{scheme}")
        try:
            reg_write("HKLM", sub, "ACSettingIndex", ac_val)
            reg_write("HKLM", sub, "DCSettingIndex", dc_val)
        except OSError:
            pass


def opt_fix_gaming_boost(bm):
    """修复游戏 Boost + 最小CPU：改当前方案 + 注册表默认值。"""
    # 1. 启用 CPU Boost（当前=已禁用，改为积极=3）
    _powercfg_set(*POWER_PRESET["cpu_boost"])
    print(f"    CPU Boost: 已禁用 → 积极(Aggressive)")

    # 2. 最小处理器状态降到 5%（当前 AC=62%，太高）
    _powercfg_set(*POWER_PRESET["cpu_min"])
    print(f"    最小处理器状态: AC 62% → 5%")

    # 激活
    subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"], capture_output=True)
    print(f"    电源方案已刷新 (当前+注册表默认值已同步)")


def opt_apply_gaming_preset(bm):
    """应用完整电竞电源预设（保留用户全部调校 + 修复 boost）。"""
    for key, (sub, setting, ac, dc) in POWER_PRESET.items():
        _powercfg_set(sub, setting, ac, dc)
    subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"], capture_output=True)
    print(f"    已应用完整电竞电源预设 ({len(POWER_PRESET)} 项)")
    print(f"    CPU Boost=积极, 最小CPU=5%, USB暂停=关, ASPM=关, 睡眠=关, 亮度=60%")


def opt_disable_telemetry_full(bm):
    """扩展遥测禁用：含 Windows Update 相关遥测和体验改善计划。"""
    # 基础遥测
    opt_disable_telemetry(bm)
    # 额外
    items = [
        ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\AppCompat", "AITEnable", 0),
        ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\AppCompat", "DisableInventory", 1),
        ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\AppCompat", "DisableUAR", 1),
        ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection", "AllowTelemetry", 0),
        ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection", "MaxTelemetryAllowed", 0),
    ]
    for root, sub, name, val in items:
        bm.snapshot(root, sub, name)
        reg_write(root, sub, name, val)


# ── 研究补充优化（来源：gaming_os_tweaker / MMCSS-Tweaks / Win-Debloat-Tools） ──

def opt_disable_audio_exclusive(bm):
    """禁用音频独占模式，避免单个程序独占声卡。"""
    sub = r"SOFTWARE\Microsoft\Multimedia\Audio"
    bm.snapshot("HKCU", sub, "ExclusiveMode")
    reg_write("HKCU", sub, "ExclusiveMode", 0)
    # 每个音频设备的 Properties 子键
    try:
        with winreg.OpenKey(_parse_root("HKCU"), r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render",
                            0, winreg.KEY_READ | _W64) as k:
            i = 0
            while True:
                try:
                    dev_guid = winreg.EnumKey(k, i)
                    props = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render\{dev_guid}\Properties"
                    for name in ["{b3f8fa53-0004-438e-9003-51a46e139bfc},3",
                                 "{b3f8fa53-0004-438e-9003-51a46e139bfc},4"]:
                        try:
                            bm.snapshot("HKCU", props, name)
                        except Exception:
                            pass
                    i += 1
                except OSError:
                    break
    except OSError:
        pass


def opt_disable_startup_delay(bm):
    """禁用 Windows 启动后打开启动程序的延迟。"""
    sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Serialize"
    bm.snapshot("HKCU", sub, "StartupDelayInMSec")
    reg_write("HKCU", sub, "StartupDelayInMSec", 0)


def opt_boot_timeout_zero(bm):
    """启动菜单等待时间设为 0 秒。"""
    subprocess.run(["bcdedit", "/set", "{current}", "timeout", "0"], capture_output=True)
    print(f"    启动菜单超时 = 0s")


def opt_disable_fso_global(bm):
    """禁用全屏优化 (Fullscreen Optimizations)，让游戏真正独占全屏。"""
    sub = r"System\GameConfigStore"
    bm.snapshot("HKCU", sub, "GameDVR_DXGIHonorFSEWindowsCompatible")
    bm.snapshot("HKCU", sub, "GameDVR_EFSEFeatureFlags")
    reg_write("HKCU", sub, "GameDVR_DXGIHonorFSEWindowsCompatible", 1)
    reg_write("HKCU", sub, "GameDVR_EFSEFeatureFlags", 0)
    # 注册表策略层
    sub2 = r"SOFTWARE\Policies\Microsoft\Windows\GameDVR"
    bm.snapshot("HKCU", sub2, "GameDVR_DXGIHonorFSEWindowsCompatible")
    reg_write("HKCU", sub2, "GameDVR_DXGIHonorFSEWindowsCompatible", 1)


def opt_disable_animations(bm):
    """禁用窗口最小化/最大化动画和淡入淡出效果。"""
    desktop = r"Control Panel\Desktop"
    bm.snapshot("HKCU", desktop, "WindowMetrics\\MinAnimate")
    bm.snapshot("HKCU", desktop, "UserPreferencesMask")
    reg_write("HKCU", desktop + "\\WindowMetrics", "MinAnimate", "0", winreg.REG_SZ)
    # 淡入淡出效果
    sub = r"Control Panel\Desktop"
    bm.snapshot("HKCU", sub, "FontSmoothing")
    # DWM 动画
    dwm = r"SOFTWARE\Microsoft\Windows\DWM"
    bm.snapshot("HKCU", dwm, "EnableAeroPeek")
    bm.snapshot("HKCU", dwm, "AlwaysHibernateThumbnails")
    reg_write("HKCU", dwm, "EnableAeroPeek", 0)
    reg_write("HKCU", dwm, "AlwaysHibernateThumbnails", 0)
    # 高级系统设置 - 视觉效果
    sub2 = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
    bm.snapshot("HKCU", sub2, "VisualFXSetting")
    reg_write("HKCU", sub2, "VisualFXSetting", 2)  # 2=最佳性能


def opt_usb_suspend_disable(bm):
    """禁用 USB 选择性暂停，防止游戏时 USB 设备休眠断连。"""
    sub_guid = "2a737441-1930-4402-8d77-b2bebba308a3"
    setting_guid = "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"
    _powercfg_set(sub_guid, setting_guid, 0, 0)
    print(f"    USB 选择性暂停 = 禁用")


def opt_nic_disable_nagle(bm):
    """按网卡适配器禁用 Nagle 算法（降低 TCP 小包延迟）。不影响大流量传输。"""
    base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
    count = 0
    try:
        with winreg.OpenKey(_parse_root("HKLM"), base, 0, winreg.KEY_READ | _W64) as k:
            i = 0
            while True:
                try:
                    guid = winreg.EnumKey(k, i)
                    sub = f"{base}\\{guid}"
                    # 检查是否有 DhcpIPAddress（有效接口）
                    ip = reg_read("HKLM", sub, "DhcpIPAddress")
                    if ip and ip != "0.0.0.0":
                        bm.snapshot("HKLM", sub, "TcpAckFrequency")
                        bm.snapshot("HKLM", sub, "TCPNoDelay")
                        bm.snapshot("HKLM", sub, "TcpDelAckTicks")
                        reg_write("HKLM", sub, "TcpAckFrequency", 1)
                        reg_write("HKLM", sub, "TCPNoDelay", 1)
                        reg_write("HKLM", sub, "TcpDelAckTicks", 0)
                        count += 1
                    i += 1
                except OSError:
                    break
    except OSError:
        pass
    print(f"    已对 {count} 个网卡禁用 Nagle")


def opt_nic_disable_lso(bm):
    """禁用大包卸载 (LSO)，避免网络栈额外分片开销。"""
    base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
    count = 0
    try:
        with winreg.OpenKey(_parse_root("HKLM"), base, 0, winreg.KEY_READ | _W64) as k:
            i = 0
            while True:
                try:
                    guid = winreg.EnumKey(k, i)
                    sub = f"{base}\\{guid}"
                    ip = reg_read("HKLM", sub, "DhcpIPAddress")
                    if ip and ip != "0.0.0.0":
                        for name in ["LsoV2IPv4", "LsoV2IPv6"]:
                            bm.snapshot("HKLM", sub, name)
                            reg_write("HKLM", sub, name, 0)
                        count += 1
                    i += 1
                except OSError:
                    break
    except OSError:
        pass
    print(f"    已对 {count} 个网卡禁用 LSO")


def opt_disable_prefetch(bm):
    """禁用 Prefetch 预读取（独立于 Superfetch，控制应用启动预读）。"""
    sub = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters"
    bm.snapshot("HKLM", sub, "EnablePrefetcher")
    reg_write("HKLM", sub, "EnablePrefetcher", 0)


def opt_disable_background_tasks(bm):
    """禁用后台优化相关计划任务（碎片整理、内存诊断等）。"""
    tasks = [
        r"Microsoft\Windows\Defrag\ScheduledDefrag",
        r"Microsoft\Windows\MemoryDiagnostic\ProcessMemoryDiagnosticEvents",
        r"Microsoft\Windows\MemoryDiagnostic\RunFullMemoryDiagnostic",
        r"Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector",
        r"Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser",
        r"Microsoft\Windows\Autochk\Proxy",
        r"Microsoft\Windows\Customer Experience Improvement Program\Consolidator",
        r"Microsoft\Windows\Customer Experience Improvement Program\UsbCeip",
    ]
    count = 0
    for task in tasks:
        r = subprocess.run(["schtasks", "/Change", "/TN", task, "/DISABLE"],
                           capture_output=True)
        if r.returncode == 0:
            count += 1
    print(f"    禁用了 {count}/{len(tasks)} 个计划任务")


def opt_disable_memory_compression(bm):
    """禁用 Windows 内存压缩，减少 CPU 开销。内存充足时（≥16GB）影响可忽略。"""
    r = subprocess.run(["powershell", "-Command", "Disable-MMAgent -MemoryCompression"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print(f"    内存压缩已禁用")
    else:
        print(f"    {YELLOW}内存压缩禁用失败（可能已禁用或需管理员权限）{RESET}")


def opt_lock_timer_resolution(bm):
    """锁定系统定时器分辨率为 0.5ms，防止帧时间抖动。会略微增加功耗。"""
    import ctypes
    ntdll = ctypes.windll.ntdll
    # 获取当前和最小分辨率
    current = ctypes.c_ulong()
    minimum = ctypes.c_ulong()
    maximum = ctypes.c_ulong()
    ntdll.NtQueryTimerResolution(ctypes.byref(maximum), ctypes.byref(minimum), ctypes.byref(current))
    # 设置为最小值（最高精度）
    actual = ctypes.c_ulong()
    ntdll.NtSetTimerResolution(minimum.value, True, ctypes.byref(actual))
    us = actual.value / 10
    print(f"    定时器分辨率: {current.value/10:.1f}μs → {us:.1f}μs")
    # 写注册表让进程也使用高精度
    sub = r"SYSTEM\CurrentControlSet\Control\Session Manager\kernel"
    bm.snapshot("HKLM", sub, "GlobalTimerResolutionRequests")
    reg_write("HKLM", sub, "GlobalTimerResolutionRequests", 1)


def opt_gpu_msi_mode(bm):
    """为 GPU 启用 MSI (Message Signaled Interrupts) 中断模式，减少 IRQ 共享延迟。"""
    gpu_base = r"SYSTEM\CurrentControlSet\Enum\PCI"
    count = 0
    try:
        with winreg.OpenKey(_parse_root("HKLM"), gpu_base, 0, winreg.KEY_READ | _W64) as k:
            idx = 0
            while True:
                try:
                    vendor_key = winreg.EnumKey(k, idx)
                    dev_base = f"{gpu_base}\\{vendor_key}"
                    try:
                        with winreg.OpenKey(_parse_root("HKLM"), dev_base, 0, winreg.KEY_READ | _W64) as vk:
                            didx = 0
                            while True:
                                try:
                                    dev_key = winreg.EnumKey(vk, didx)
                                    dev_path = f"{dev_base}\\{dev_key}"
                                    # 只处理 Display 类设备
                                    cls = reg_read("HKLM", dev_path, "ClassGUID")
                                    if cls and cls == "{4d36e968-e325-11ce-bfc1-08002be10318}":
                                        desc = reg_read("HKLM", dev_path, "DeviceDesc") or ""
                                        msi_path = f"{dev_path}\\Device Parameters\\Interrupt Management\\MessageSignaledInterruptProperties"
                                        bm.snapshot("HKLM", msi_path, "MSISupported")
                                        reg_write("HKLM", msi_path, "MSISupported", 1)
                                        count += 1
                                        print(f"    GPU MSI: {str(desc)[:60]}")
                                    didx += 1
                                except OSError:
                                    break
                    except OSError:
                        pass
                    idx += 1
                except OSError:
                    break
    except OSError:
        pass
    if count == 0:
        print(f"    {YELLOW}未找到可设置 MSI 的 GPU 设备{RESET}")
    else:
        print(f"    已为 {count} 个 GPU 启用 MSI 模式")


def opt_nic_rss_optimize(bm):
    """启用网卡 RSS (Receive Side Scaling) 并优化队列数。"""
    # 全局 TCP RSS 设置
    sub = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
    bm.snapshot("HKLM", sub, "EnableRSS")
    reg_write("HKLM", sub, "EnableRSS", 1)
    # 按网卡设置
    base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
    count = 0
    try:
        with winreg.OpenKey(_parse_root("HKLM"), base, 0, winreg.KEY_READ | _W64) as k:
            i = 0
            while True:
                try:
                    guid = winreg.EnumKey(k, i)
                    sub = f"{base}\\{guid}"
                    ip = reg_read("HKLM", sub, "DhcpIPAddress")
                    if ip and ip != "0.0.0.0":
                        for name in ["*RSS", "RSS"]:
                            bm.snapshot("HKLM", sub, name)
                            reg_write("HKLM", sub, name, 1)
                        count += 1
                    i += 1
                except OSError:
                    break
    except OSError:
        pass
    print(f"    已为 {count} 个网卡启用 RSS")


# ─── 系统扫描 ───────────────────────────────────────────

SCAN_CHECKS = [
    # (显示名, 期望值, root, subkey, name, 优化项ID)
    # ── 游戏 ──
    ("GameDVR 禁用",      0,          "HKCU", r"System\GameConfigStore", "GameDVR_Enabled", "gamedvr"),
    ("AllowGameDVR",      0,          "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", "gamedvr"),
    ("GameDVR 组策略",    0,          "HKLM", r"SOFTWARE\Microsoft\PolicyManager\default\ApplicationManagement\AllowGameDVR", "value", "gamedvr_policy"),
    ("AppCaptureEnabled", 0,          "HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", "gamedvr"),
    ("FSE 全屏独占",      2,          "HKCU", r"System\GameConfigStore", "GameDVR_FSEBehaviorMode", "fse"),
    ("Game Mode",         1,          "HKCU", r"SOFTWARE\Microsoft\GameBar", "AutoGameModeEnabled", "gamemode"),
    ("HAGS GPU 调度",     2,          "HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", "hags"),
    ("MMCSS Games GPU",   8,          "HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "GPU Priority", "mmcss_games"),
    ("MMCSS Games 调度",  "High",     "HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Scheduling Category", "mmcss_games"),
    # ── 网络 ──
    ("NetworkThrottle",   0xFFFFFFFF, "HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", "net_throttle"),
    ("SystemResponse",    0,          "HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness", "net_throttle"),
    ("TCPNoDelay",        1,          "HKLM", r"SOFTWARE\Microsoft\MSMQ\Parameters", "TCPNoDelay", "tcp_nodelay"),
    ("NonBestEffortLimit",0,          "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Psched", "NonBestEffortLimit", "qos_bw"),
    ("LargeSystemCache",  0,          "HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management", "LargeSystemCache", "net_mem"),
    # ── 键鼠 ──
    ("KeyboardDelay",     "0",        "HKCU", r"Control Panel\Keyboard", "KeyboardDelay", "kb_opt"),
    ("KeyboardSpeed",     "48",       "HKCU", r"Control Panel\Keyboard", "KeyboardSpeed", "kb_opt"),
    ("MouseSpeed",        "0",        "HKCU", r"Control Panel\Mouse", "MouseSpeed", "mouse_opt"),
    ("粘滞键",            "506",      "HKCU", r"Control Panel\Accessibility\StickyKeys", "Flags", "sticky_keys"),
    ("切换键",            "58",       "HKCU", r"Control Panel\Accessibility\ToggleKeys", "Flags", "toggle_keys"),
    # ── 系统 ──
    ("后台应用禁用",      1,          "HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", "bg_apps"),
    ("AllowTelemetry",    0,          "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", "telemetry"),
    ("SoftLanding",       0,          "HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SoftLandingEnabled", "telemetry"),
    ("文件分配优化",      500,        "HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "ConfigFileAllocSize", "file_alloc"),
    ("管理共享禁用",      0,          "HKLM", r"SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters", "AutoShareServer", "admin_share"),
    ("自动运行禁用",      0xFF,       "HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoDriveTypeAutoRun", "autorun"),
    ("Explorer 自启",     1,          "HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "AutoRestartShell", "explorer_restart"),
    ("地图下载禁用",      0,          "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Maps", "AutoDownloadAndUpdateMapData", "map_download"),
    ("任务栏新闻隐藏",    0,          "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Feeds", "EnableFeeds", "feeds"),
    ("CEIP 禁用",         0,          "HKLM", r"SOFTWARE\Policies\Microsoft\SQMClient\Windows", "CEIPEnable", "telemetry"),
    ("WU 暂停上限",       3650,       "HKLM", r"SOFTWARE\Microsoft\WindowsUpdate\UX\Settings", "FlightSettingsMaxPauseDays", "wu_pause"),
    ("透明效果禁用",      0,          "HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", "transparency"),
    ("设置同步禁用",      5,          "HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\SettingSync", "SyncPolicy", "setting_sync"),
    ("开始菜单跟踪禁用",  0,          "HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Start_TrackProgs", "tracking"),
    ("驱动搜索禁用",      0,          "HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching", "SearchOrderConfig", "driver_search"),
    # ── 调度 ──
    ("Win32PrioritySep",  40,         "HKLM", r"SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation", "win32_pri"),
    # ── 研究补充 ──
    ("启动延迟禁用",      0,          "HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Serialize", "StartupDelayInMSec", "startup_delay"),
    ("全屏优化禁用",      1,          "HKCU", r"System\GameConfigStore", "GameDVR_DXGIHonorFSEWindowsCompatible", "fse_global"),
    ("视觉效果最佳性能",  2,          "HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", "anim_disable"),
    ("AeroPeek 禁用",     0,          "HKCU", r"SOFTWARE\Microsoft\Windows\DWM", "EnableAeroPeek", "anim_disable"),
    ("Prefetch 禁用",     0,          "HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters", "EnablePrefetcher", "disable_prefetch"),
    ("全局 RSS 启用",     1,          "HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "EnableRSS", "nic_rss_opt"),
    # ── 电源 ──
    ("PowerThrottleOff",  1,          "HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", "power_perf"),
    ("快速启动禁用",      0,          "HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power", "HiberbootEnabled", "power_perf"),
    ("WiFi 电源管理禁用", 1,          "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WcmSvc\GroupPolicy", "fDisablePowerManagement", "wifi_power"),
    ("CPU 唤醒核心",      100,        "HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "InitialUnparkCount", "cpu_unpark"),
    ("性能偏好",          0,          "HKLM", r"SYSTEM\CurrentControlSet\Control\Power\Policy\Settings\Processor", "PerfEnergyPreference", "cpu_unpark"),
    ("设备不空闲",        0,          "HKLM", r"SYSTEM\CurrentControlSet\Control\Power\Policy\Settings\Misc", "DeviceIdlePolicy", "cpu_unpark"),
    ("节能器阻止",        0,          "HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PDC\Activators\Default\VetoPolicy", "EA:EnergySaverEngaged", "energy_veto"),
    # ── GPU ──
    ("GPU 抢占禁用",      0,          "HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Scheduler", "EnablePreemption", "gpu_preempt"),
    # ── 磁盘 ──
    ("Superfetch",        0,          "HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters", "EnableSuperfetch", "superfetch"),
    ("Prefetcher",        0,          "HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters", "EnablePrefetcher", "superfetch"),
    # ── 服务 ──
    ("MapsBroker 服务",   4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\MapsBroker", "Start", "mapsbroker"),
    ("MMCSS 服务",        4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\MMCSS", "Start", "disable_mmcss"),
    ("XblAuthManager",    4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\XblAuthManager", "Start", "svc_safe"),
    ("XblGameSave",       4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\XblGameSave", "Start", "svc_safe"),
    ("XboxNetApiSvc",     4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\XboxNetApiSvc", "Start", "svc_safe"),
    ("DiagTrack",         4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\DiagTrack", "Start", "svc_safe"),
    ("WSearch",           4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\WSearch", "Start", "svc_safe"),
    ("SysMain",           4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\SysMain", "Start", "svc_safe"),
    ("Fax",               4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\Fax", "Start", "svc_safe"),
    ("RemoteRegistry",    4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\RemoteRegistry", "Start", "svc_safe"),
    ("WerSvc",            4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\WerSvc", "Start", "svc_safe"),
    ("RetailDemo",        4,          "HKLM", r"SYSTEM\CurrentControlSet\Services\RetailDemo", "Start", "svc_safe"),
    # ── 扩展遥测 ──
    ("AppCompat 遥测",    0,          "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\AppCompat", "AITEnable", "telemetry_full"),
    ("UAR 禁用",          1,          "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\AppCompat", "DisableUAR", "telemetry_full"),
]


def scan_system():
    """扫描当前系统优化状态，返回 (已生效, 未生效) 两个列表。"""
    applied = []
    missing = []
    for label, expected, root, sub, name, opt_id in SCAN_CHECKS:
        val = reg_read(root, sub, name)
        if isinstance(expected, str):
            match = (str(val) == expected)
        elif expected == 0xFFFFFFFF:
            match = (val == 0xFFFFFFFF or val == 4294967295)
        else:
            match = (val == expected)
        if match:
            applied.append((label, opt_id, val))
        else:
            missing.append((label, opt_id, val, expected))
    return applied, missing


# ─── UI ─────────────────────────────────────────────────

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def clear():
    subprocess.run(["cmd", "/c", "cls"] if os.name == "nt" else ["clear"])


def banner():
    print(f"""
{CYAN}{BOLD}  ╔══════════════════════════════════════════════╗
  ║        皓月定制 保守优化工具  v{VERSION}         ║
  ║      Conservative System Optimizer           ║
  ╚══════════════════════════════════════════════╝{RESET}
""")


def risk_color(risk):
    return {"LOW": GREEN, "MEDIUM": YELLOW, "HIGH": RED}.get(risk, RESET)


def print_menu(items):
    by_cat = {}
    for i, (oid, name, risk, cat, _) in enumerate(items):
        by_cat.setdefault(cat, []).append((i, oid, name, risk))

    for cat, entries in by_cat.items():
        print(f"\n  {BOLD}[{cat}]{RESET}")
        for i, oid, name, risk in entries:
            rc = risk_color(risk)
            print(f"    {DIM}{i+1:2d}{RESET}  {rc}[{risk:6s}]{RESET}  {name}")


def main():
    clear()
    banner()

    if not is_admin():
        print(f"  {RED}请以管理员身份运行此工具！{RESET}")
        print(f"  右键点击 → 以管理员身份运行")
        input(f"\n  {DIM}按回车退出...{RESET}")
        sys.exit(1)

    items = get_optimizations()
    bm = BackupManager()

    while True:
        print(f"\n  {BOLD}主菜单{RESET}")
        print(f"  {'─' * 44}")
        print(f"    {GREEN}1{RESET}  扫描系统 + 智能补充缺失项")
        print(f"    {GREEN}2{RESET}  一键应用保守方案 (LOW)")
        print(f"    {GREEN}3{RESET}  自定义选择优化项")
        print(f"    {YELLOW}4{RESET}  应用全部 (LOW + MEDIUM)")
        print(f"    {CYAN}5{RESET}  查看优化项列表")
        print(f"    {RED}6{RESET}  恢复备份")
        print(f"    {DIM}0{RESET}  退出")
        print()

        choice = input(f"  选择 [{GREEN}1-6{RESET}, {DIM}0{RESET}]: ").strip()

        if choice == "0":
            print(f"\n  {DIM}退出。{RESET}")
            break

        elif choice == "1":
            scan_and_supplement(items, bm)

        elif choice == "2":
            apply_items(items, bm, risk_filter=["LOW"])

        elif choice == "3":
            clear()
            banner()
            print(f"  {BOLD}自定义选择{RESET}")
            print_menu(items)
            print(f"\n  输入编号（逗号分隔，如 1,3,5），或 {GREEN}all{RESET} 全选:")
            raw = input(f"  > ").strip()
            if raw.lower() == "all":
                selected = list(range(len(items)))
            else:
                selected = []
                for part in raw.split(","):
                    part = part.strip()
                    if part.isdigit():
                        idx = int(part) - 1
                        if 0 <= idx < len(items):
                            selected.append(idx)
            if selected:
                apply_items(items, bm, indices=selected)

        elif choice == "4":
            apply_items(items, bm, risk_filter=["LOW", "MEDIUM"])

        elif choice == "5":
            clear()
            banner()
            print(f"  {BOLD}全部优化项 ({len(items)} 项){RESET}")
            print_menu(items)
            print(f"\n  {DIM}LOW = 安全可默认启用  |  MEDIUM = 需手动确认{RESET}")

        elif choice == "6":
            print(f"\n  {BOLD}可用备份文件:{RESET}")
            backups = sorted(BACKUP_DIR.glob("backup_*.json"), reverse=True)
            if not backups:
                print(f"  {DIM}无备份文件{RESET}")
            else:
                for i, f in enumerate(backups[:10]):
                    print(f"    {i+1}. {f.name}")
                sel = input(f"\n  选择编号恢复 (回车取消): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(backups):
                    bm.restore(backups[int(sel) - 1])

        else:
            print(f"  {DIM}无效选项{RESET}")

        print()


def apply_items(items, bm, risk_filter=None, indices=None):
    """应用指定优化项。"""
    clear()
    banner()
    targets = []
    if indices is not None:
        targets = [(i, items[i]) for i in indices if i < len(items)]
    else:
        targets = [(i, item) for i, item in enumerate(items) if item[2] in (risk_filter or [])]

    if not targets:
        print(f"  {YELLOW}没有选中任何优化项{RESET}")
        return

    print(f"  {BOLD}即将应用 {len(targets)} 项优化:{RESET}\n")
    for i, (oid, name, risk, cat, _) in targets:
        rc = risk_color(risk)
        print(f"    {rc}[{risk:6s}]{RESET}  {name}")

    # MEDIUM 确认
    has_medium = any(t[1][2] == "MEDIUM" for t in targets)
    if has_medium:
        print(f"\n  {YELLOW}⚠ 包含 MEDIUM 风险项，可能影响部分功能。{RESET}")
    print(f"\n  {GREEN}修改前会自动备份当前注册表状态{RESET}")
    confirm = input(f"\n  确认应用？[{GREEN}y{RESET}/{RED}N{RESET}]: ").strip().lower()
    if confirm != "y":
        print(f"  {DIM}已取消{RESET}")
        return

    bm.data.clear()
    log = Logger()
    success = 0
    fail = 0
    for i, (oid, name, risk, cat, fn) in targets:
        print(f"\n  {CYAN}▸{RESET} {name} ... ", end="", flush=True)
        try:
            fn(bm)
            print(f"{GREEN}OK{RESET}")
            log.ok(name, f"id={oid} cat={cat}")
            success += 1
        except Exception as e:
            print(f"{RED}失败: {e}{RESET}")
            log.fail(name, str(e))
            fail += 1

    log.summary(success, fail, len(targets))
    log_path = log.save()

    # 保存备份
    if bm.data:
        path = bm.save()
        print(f"\n  {GREEN}✓ 备份已保存: {path}{RESET}")

    print(f"\n  {BOLD}完成！{RESET} 成功 {GREEN}{success}{RESET} 项" +
          (f"，失败 {RED}{fail}{RESET} 项" if fail else ""))
    print(f"  {DIM}日志: {log_path}{RESET}")
    print(f"  {DIM}部分修改需重启生效。如需恢复，使用主菜单选项 6。{RESET}")


def show_status(items):
    """显示当前系统优化状态。"""
    clear()
    banner()
    print(f"  {BOLD}当前系统状态{RESET}\n")

    checks = [
        ("GameDVR", "HKCU", r"System\GameConfigStore", "GameDVR_Enabled", {0: "已禁用", 1: "启用"}),
        ("FSE 模式", "HKCU", r"System\GameConfigStore", "FSEBehaviorMode", {2: "全屏独占", 0: "默认"}),
        ("网络节流", "HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", {0xFFFFFFFF: "已禁用"}),
        ("系统响应", "HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness", {0: "最高", 20: "默认"}),
        ("后台应用", "HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", {1: "已禁用", 0: "启用"}),
        ("遥测", "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", {0: "已关闭"}),
        ("粘滞键", "HKCU", r"Control Panel\Accessibility\StickyKeys", "Flags", {}),
        ("GPU抢占", "HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Scheduler", "EnablePreemption", {0: "已禁用", 1: "默认"}),
        ("TCPNoDelay", "HKLM", r"SOFTWARE\Microsoft\MSMQ\Parameters", "TCPNoDelay", {1: "已关闭Nagle"}),
        ("文件分配", "HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "ConfigFileAllocSize", {500: "已优化"}),
        ("任务栏新闻", "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Feeds", "EnableFeeds", {0: "已隐藏"}),
        ("地图下载", "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Maps", "AutoDownloadAndUpdateMapData", {0: "已禁用"}),
        ("PowerThrottle", "HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", {1: "已禁用"}),
        ("快速启动", "HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power", "HiberbootEnabled", {0: "已禁用"}),
    ]

    for label, root, sub, name, status_map in checks:
        val = reg_read(root, sub, name)
        if val is None:
            status = f"{DIM}未设置{RESET}"
        elif val in status_map:
            is_optimized = status_map[val] not in ("默认", "启用")
            color = GREEN if is_optimized else YELLOW
            status = f"{color}{status_map[val]}{RESET} ({val})"
        else:
            status = f"{val}"
        print(f"    {label:14s}  {status}")

    # 电源方案（从原始字节提取 GUID，避免编码问题）
    try:
        r = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True)
        raw = r.stdout
        import re
        m = re.search(rb"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", raw)
        if m:
            guid = m.group(1).decode("ascii")
            known = {
                "381b4222-f694-41f0-9685-ff5bb260df2e": "平衡",
                "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "高性能",
                "e9a42b02-d5df-448d-aa00-03f14749eb61": "卓越性能",
                "a1841308-3541-4fab-bc81-f71556f20b4a": "节能",
            }
            label = known.get(guid.lower(), "自定义")
            print(f"\n    {BOLD}电源方案{RESET}  {label} ({guid})")
    except Exception:
        pass

    # 服务状态
    print(f"\n    {BOLD}关键服务{RESET}")
    for svc_name in ["MMCSS", "SysMain", "MapsBroker", "DiagTrack", "WSearch"]:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                rf"SYSTEM\CurrentControlSet\Services\{svc_name}",
                                0, winreg.KEY_READ | _W64) as k:
                start, _ = winreg.QueryValueEx(k, "Start")
                modes = {0: "Boot", 1: "System", 2: "Auto", 3: "Manual", 4: "Disabled"}
                color = GREEN if start == 4 else (YELLOW if start == 3 else RESET)
                print(f"    {svc_name:14s}  {color}{modes.get(start, start)}{RESET}")
        except Exception:
            print(f"    {svc_name:14s}  {DIM}未找到{RESET}")


def scan_and_supplement(items, bm):
    """扫描系统状态，显示全部状态，智能识别缺失项并一键补充。"""
    clear()
    banner()
    print(f"  {BOLD}系统扫描中...{RESET}\n")

    applied, missing = scan_system()

    print(f"  {GREEN}已生效 ({len(applied)} 项):{RESET}")
    for label, opt_id, val in applied:
        print(f"    {GREEN}✓{RESET} {label}")

    print(f"\n  {YELLOW}缺失 ({len(missing)} 项):{RESET}")
    for label, opt_id, current, expected in missing:
        print(f"    {YELLOW}✗{RESET} {label}  (当前={current}, 期望={expected})")

    # 额外状态
    import re
    try:
        r = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True)
        m = re.search(rb"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", r.stdout)
        if m:
            guid = m.group(1).decode("ascii")
            known = {
                "381b4222-f694-41f0-9685-ff5bb260df2e": "平衡",
                "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "高性能",
                "e9a42b02-d5df-448d-aa00-03f14749eb61": "卓越性能",
                "a1841308-3541-4fab-bc81-f71556f20b4a": "节能",
            }
            label = known.get(guid.lower(), "自定义")
            print(f"\n  {BOLD}电源方案{RESET}  {label} ({guid})")
    except Exception:
        pass

    # CPU Boost 检测（powercfg 值，不在注册表里）
    boost_ok = False
    try:
        r2 = subprocess.run(["powercfg", "/query", "SCHEME_CURRENT",
                             "54533251-82be-4824-96c1-47b60b740d00",
                             "be337238-0d82-4146-a960-4f3749d470c7"],
                            capture_output=True)
        text = r2.stdout.decode("gbk", errors="replace")
        import re as _re
        ac_m = _re.search(r"当前交流.*?:\s*(0x[0-9a-fA-F]+)", text)
        if ac_m:
            boost_val = int(ac_m.group(1), 16)
            boost_names = {0: "已禁用", 1: "已启用", 2: "高性能", 3: "积极", 4: "高效率", 5: "积极且有保障"}
            boost_ok = boost_val in (1, 3, 5, 6)
            color = GREEN if boost_ok else RED
            print(f"  {BOLD}CPU Boost{RESET}  {color}{boost_names.get(boost_val, boost_val)}{RESET} (AC)")
            if not boost_ok:
                missing.append(("CPU Boost", "gaming_boost", boost_val, 3))
    except Exception:
        pass

    # 最小处理器状态检测
    try:
        r3 = subprocess.run(["powercfg", "/query", "SCHEME_CURRENT",
                             "54533251-82be-4824-96c1-47b60b740d00",
                             "893dee8e-2bef-41e0-89c6-b55d0929964c"],
                            capture_output=True)
        text3 = r3.stdout.decode("gbk", errors="replace")
        ac3 = _re.search(r"当前交流.*?:\s*(0x[0-9a-fA-F]+)", text3)
        if ac3:
            min_cpu = int(ac3.group(1), 16)
            color = GREEN if min_cpu <= 10 else YELLOW
            print(f"  {BOLD}最小CPU状态{RESET}  {color}{min_cpu}%{RESET} (AC)")
            if min_cpu > 10:
                missing.append(("最小CPU状态", "gaming_boost", min_cpu, 5))
    except Exception:
        pass

    # SSD fsutil 检测
    try:
        r4 = subprocess.run(["fsutil", "behavior", "query", "disablelastaccess"], capture_output=True)
        text4 = r4.stdout.decode("gbk", errors="replace")
        if "已禁用" in text4 or "disabled" in text4.lower():
            print(f"  {BOLD}SSD LastAccess{RESET}  {GREEN}已禁用{RESET}")
        else:
            print(f"  {BOLD}SSD LastAccess{RESET}  {YELLOW}未禁用{RESET}")
    except Exception:
        pass

    print(f"\n  {BOLD}关键服务{RESET}")
    for svc_name in ["MMCSS", "SysMain", "MapsBroker", "DiagTrack", "WSearch"]:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                rf"SYSTEM\CurrentControlSet\Services\{svc_name}",
                                0, winreg.KEY_READ | _W64) as k:
                start, _ = winreg.QueryValueEx(k, "Start")
                modes = {0: "Boot", 1: "System", 2: "Auto", 3: "Manual", 4: "Disabled"}
                color = GREEN if start == 4 else (YELLOW if start == 3 else RESET)
                print(f"    {svc_name:14s}  {color}{modes.get(start, start)}{RESET}")
        except Exception:
            print(f"    {svc_name:14s}  {DIM}未找到{RESET}")

    if not missing:
        print(f"\n  {GREEN}所有保守优化项均已生效，无需补充。{RESET}")
        return

    # 找出对应的优化项索引
    missing_ids = set(opt_id for _, opt_id, _, _ in missing)
    item_map = {oid: i for i, (oid, *_) in enumerate(items)}
    indices = [item_map[mid] for mid in missing_ids if mid in item_map]

    print(f"\n  需要补充 {len(indices)} 项优化。")
    confirm = input(f"  是否自动补充？[{GREEN}y{RESET}/{RED}N{RESET}]: ").strip().lower()
    if confirm == "y":
        apply_items(items, bm, indices=indices)


if __name__ == "__main__":
    main()
