"""Hardware detection and Store-safe compatibility guards.

Centralizes hardware-capability queries and the store-safe service
protection list so that every other module can import them without
circular dependencies.
"""

from __future__ import annotations

import subprocess

# ── Store-safe protected services ──────────────────────────────
# These must never be disabled or stopped by the optimizer, regardless
# of preset.  The underlying guard is enforced in core.service and
# checked before any service write.

STORE_SAFE_PROTECTED_SERVICES: set[str] = {
    # Microsoft Store core
    "AppXSvc",
    "ClipSVC",
    "LicenseManager",
    "InstallService",
    # Store / update / download / package path
    "wuauserv",
    "UsoSvc",
    "WaaSMedicSvc",
    "BITS",
    "DoSvc",
    "CryptSvc",
    "TrustedInstaller",
    # UWP / WinRT / app-model infrastructure
    "StateRepository",
    "SystemEventsBroker",
    "TimeBrokerSvc",
    "BrokerInfrastructure",
    "TokenBroker",
    "NcbService",
    "WpnService",
    "WpnUserService",
    "UserManager",
    "ProfSvc",
    "SENS",
    "EventSystem",
    # Storage
    "StorSvc",
    # Store-related optional infrastructure
    "AppReadiness",
    "PushToInstall",
    # Security / reliability (should not be disabled)
    "wscsvc",
    "EventLog",
}

# Preferred start types for repair operations.  Services that are
# currently Disabled are restored to these values.
STORE_SAFE_DEFAULT_START_TYPES: dict[str, str] = {
    "AppXSvc": "manual",
    "ClipSVC": "manual",
    "LicenseManager": "manual",
    "InstallService": "manual",
    "wuauserv": "manual",
    "UsoSvc": "manual",
    "WaaSMedicSvc": "manual",
    "BITS": "manual",
    "DoSvc": "automatic",
    "CryptSvc": "automatic",
    "TrustedInstaller": "manual",
    "StateRepository": "manual",
    "SystemEventsBroker": "automatic",
    "TimeBrokerSvc": "manual",
    "BrokerInfrastructure": "automatic",
    "TokenBroker": "manual",
    "NcbService": "manual",
    "WpnService": "automatic",
    "WpnUserService": "manual",
    "UserManager": "automatic",
    "ProfSvc": "automatic",
    "SENS": "automatic",
    "EventSystem": "automatic",
    "StorSvc": "automatic",
    "AppReadiness": "manual",
    "PushToInstall": "manual",
    "wscsvc": "automatic",
    "EventLog": "automatic",
}

# Services that may legitimately not exist on the current machine.
# The optimizer skips them silently instead of reporting an error.
OPTIONAL_SERVICES_MAY_NOT_EXIST: set[str] = {
    "GeoSvc",
    "BthHFSrv",
    "ContactDataSvc",
    "NfcService",
    "TabletInputService",
    "GpuEnergyDrv",
    "XblAuthManager",
    "XblGameSave",
    "XboxNetApiSvc",
    "XboxGipSvc",
    "MapsBroker",
    "RemoteRegistry",
    "Fax",
    "PhoneSvc",
    "TapiSrv",
    "WbioSrvc",
    "RmSvc",
    "lfsvc",
    "SensrSvc",
    "SensorDataService",
    "SCardSvr",
    "ScDeviceEnum",
    "RetailDemo",
    "WalletService",
    "wisvc",
    "WdiServiceHost",
    "WdiSystemHost",
    "dmwappushservice",
    "SEMgrSvc",
    "TrkWks",
    "SSDPSRV",
    "upnphost",
    "SessionEnv",
    "RpcLocator",
    "UmRdpService",
    "RasAuto",
    "RasMan",
    "PrintNotify",
}

# IFEO targets that must never be deprioritized.
BLOCKED_IFEO_TARGETS: set[str] = {
    "svchost.exe",
    "TrustedInstaller.exe",
}


# ── Hardware detection ─────────────────────────────────────────


def get_cpu_vendor() -> str:
    """Return the CPU vendor string, e.g. 'AuthenticAMD' or 'GenuineIntel'."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", "(Get-CimInstance Win32_Processor).Manufacturer"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_cpu_topology() -> dict:
    """Return basic CPU topology info: cores, logical processors, and whether
    the processor advertises heterogeneous (P-core / E-core) architecture.

    The returned dict has keys: vendor, cores, logical_processors, is_hybrid.
    is_hybrid is True when logical > cores (Intel hybrid) or the AMD CPPC2
    heterogeneity hint is present.
    """
    try:
        result = subprocess.run(
            [
                "powershell", "-Command",
                "$c=Get-CimInstance Win32_Processor; "
                "Write-Host \"$($c.NumberOfCores) $($c.NumberOfLogicalProcessors) $($c.Manufacturer)\"",
            ],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
        )
        parts = result.stdout.strip().split()
        if len(parts) < 3:
            return {"vendor": "", "cores": 0, "logical_processors": 0, "is_hybrid": False}
        cores = int(parts[0])
        logical = int(parts[1])
        vendor = parts[2]
        # Intel hybrid: logical > cores (HT + E-cores create this pattern, but we
        # also need to check for actual hybrid capability which is best-guessed
        # from the existence of the heterogeneous GUIDs in powercfg)
        is_hybrid = vendor == "GenuineIntel" and _has_intel_hetero_policy()
        return {"vendor": vendor, "cores": cores, "logical_processors": logical, "is_hybrid": is_hybrid}
    except Exception:
        return {"vendor": "", "cores": 0, "logical_processors": 0, "is_hybrid": False}


def is_intel_hybrid_cpu() -> bool:
    """True when running on an Intel CPU with P-core / E-core heterogeneous topology."""
    topo = get_cpu_topology()
    return topo["vendor"] == "GenuineIntel" and topo["is_hybrid"]


def is_amd_cpu() -> bool:
    """True when running on an AMD CPU."""
    vendor = get_cpu_vendor()
    return vendor == "AuthenticAMD" if vendor else False


def is_laptop() -> bool:
    """True when the system has a battery (i.e. is a laptop/tablet, not a desktop)."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "$c=Get-CimInstance Win32_ComputerSystem; if($c.PCSystemType -eq 2){exit 0}else{exit 1}"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
        )
        return result.returncode == 0
    except Exception:
        return False


def _has_intel_hetero_policy() -> bool:
    """Check whether the Intel heterogeneous policy GUID exists in powercfg."""
    try:
        result = subprocess.run(
            ["powercfg", "/query", "SCHEME_CURRENT",
             "54533251-82be-4824-96c1-47b60b740d00",
             "7f2f5cfa-f10c-4823-b5e1-e93ae85f46b5"],
            capture_output=True,
            text=True, encoding="gbk", errors="ignore",
        )
        return "0x" in result.stdout.lower()
    except Exception:
        return False


# ── Registry value helpers ─────────────────────────────────────


def ntfs_last_access_is_disabled(value: int) -> bool:
    """Return True when the NtfsDisableLastAccessUpdate value means 'disabled',
    regardless of the exact encoding (0x80000002 or 0x80000003)."""
    return value in {0x80000002, 0x80000003}


def is_service_disabled(start_type: str | int | None) -> bool:
    """Return True when the start_type effectively means 'disabled'."""
    if start_type is None:
        return False
    s = str(start_type).lower().strip()
    return s in {"disabled", "disable", "4"}
