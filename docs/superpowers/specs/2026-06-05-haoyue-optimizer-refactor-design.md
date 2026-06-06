# 皓月定制优化工具深度重构设计

日期：2026-06-05
调研来源：deep-research workflow `wf_d36705a5-36a`，覆盖 Atlas、Chris Titus Tech WinUtil、Sophia Script、Win-Debloat-Tools、O&O ShutUp10++、Windows10GamingFocus、Win11Debloat 等项目。

## 1. 目标

将当前单文件版“皓月定制优化工具”重构为模块化 Windows 电竞优化 CLI。最终仍交付单个 exe，但内部支持完整的 `scan -> plan -> apply -> verify -> rollback -> report` 流程。

核心定位：

> 可审计、可回滚、风险分级的 Windows 游戏 / 性能 / 隐私优化 CLI，而不是激进一键 debloat。

每一项优化都必须包含：当前状态检测、目的、证据等级、适用系统、风险等级、预期收益、副作用、可回滚性、验证方式、默认是否启用。

## 2. 设计原则

调研结论要求皓月采用以下原则：

- 不收集所有流行 tweak；只纳入可解释、可检测、可回滚的项。
- 不承诺 FPS 或延迟收益；对 GameDVR、HAGS、HPET、Nagle、NIC offload、核心停放等只作为候选项或实验项。
- 默认不是“一键极限优化”，而是分层 preset + 逐项预览。
- 执行前生成可审计 JSON plan。
- 执行时写入变更日志和动作级备份。
- 执行后逐项验证，不验证则不显示成功。
- 回滚优先按动作日志恢复，而不是靠猜测默认值。
- Windows build、驱动、游戏反作弊、Windows Update 策略都可能改变 tweak 效果，因此需要系统信息快照。

## 3. 明确边界

默认不做：

- 不禁用 Defender、防火墙、SmartScreen。
- 不永久禁用 UAC。
- 不关闭 Core Isolation。
- 不关闭 CPU mitigations。
- 不关闭 Windows Update 主服务和自动更新主链路。
- 不删除系统组件、不卸载 Appx 包、不清 WinSxS/DriverStore。
- 不修改反作弊相关服务和驱动。
- 不批量删除计划任务，只允许禁用并记录原状态。
- 不盲目 kill 进程。
- 不默认禁用蓝牙、打印、通知、OneDrive、输入法、商店。
- 不做无依据的 MTU/RWIN/TTL 大规模写入。
- 不默认关闭 HPET。
- 不默认修改网络协议栈、NIC offload、CPU 核心停放、GPU MSI、定时器分辨率。

谨慎项可以存在，但必须进入高风险实验区并二次确认。

## 4. 推荐架构

采用“内部模块化，最终仍单 exe”的方案。

```text
haoyue_optimizer/
  main.py
  core/
    admin.py
    backup.py
    command.py
    registry.py
    service.py
    scheduled_task.py
    power.py
    system_info.py
    verify.py
    models.py
  optimizations/
    catalog.py
    gaming.py
    telemetry.py
    services.py
    network.py
    power.py
    input.py
    gpu.py
    privacy.py
    cleanup.py
  ui/
    cli.py
    format.py
```

理由：当前单文件已超过 1800 行，继续堆功能会失控。模块化能支撑服务、计划任务、powercfg、注册表、命令型动作的统一备份和回滚，同时 PyInstaller 仍可打包为单 exe。

## 5. CLI 命令与菜单

### 5.1 命令结构

支持交互菜单，也支持命令模式：

```text
皓月定制优化工具.exe scan
皓月定制优化工具.exe doctor
皓月定制优化工具.exe presets
皓月定制优化工具.exe plan --preset safe --out plan.json
皓月定制优化工具.exe apply --plan plan.json
皓月定制优化工具.exe rollback latest
皓月定制优化工具.exe export-report
```

管理员权限原则：

- `scan`、`doctor`、`presets`、`plan` 尽量只读，不强制管理员。
- `apply`、`rollback` 需要写系统设置，必须管理员。

### 5.2 交互菜单

```text
1. 扫描系统状态
2. 系统体检 doctor
3. 查看预设方案
4. 生成变更计划
5. 应用计划
6. 查看历史备份 / 回滚
7. 导出诊断报告
0. 退出
```

## 6. Preset 分层

调研后采用四个 preset，而不是单纯 LOW/MEDIUM：

### 6.1 safe：安全默认

默认推荐。仅包含低副作用、可读写当前值、可直接恢复的项。

要求：

- 不影响 Windows Update 主流程。
- 不影响 Defender、防火墙、SmartScreen。
- 不影响账号登录、商店、驱动安装、蓝牙、打印、输入法。
- 不影响常见反作弊。
- 可直接验证注册表、服务或任务状态。

### 6.2 gaming：游戏优化

默认不自动应用，用户确认后应用。

候选：GameDVR、Game Mode、HAGS 检测/启用、全屏优化策略、MMCSS Games、Power Throttling、电竞电源计划、USB 选择性暂停、指定游戏高性能 GPU 偏好。

### 6.3 privacy：隐私强化

默认不自动应用，用户确认后应用。

候选：遥测、CEIP、广告 ID、Content Delivery、Tailored Experiences、活动历史、反馈频率、Bing/开始菜单 Web 搜索、兼容性遥测计划任务。

### 6.4 experimental：高风险实验

默认不选，逐项二次确认。

候选：GPU MSI、定时器分辨率、内存压缩禁用、NIC offload/EEE、Nagle、RSS、HPET 检测提示、CPU 核心停放策略、进程优先级自动切换。

## 7. 风险等级

每个 tweak 至少标注绿色 / 黄色 / 红色三级。

| 等级 | 含义 | 默认行为 |
|---|---|---|
| green | 可读写当前值、可直接恢复、低副作用 | 可进入 safe 默认推荐 |
| yellow | 服务/计划任务/遥测/隐私/GPU 游戏设置/电源计划等可能影响功能 | 需要确认 |
| red | 安全功能关闭、Windows Update 强改、组件删除、网络协议栈修改、HPET/mitigations/UAC/Core Isolation | 默认不做或实验区二次确认 |

## 8. 优化项数据模型

```python
Optimization(
    id="disable_gamedvr",
    title="禁用 Game DVR / Xbox 录制",
    category="gaming",
    preset="safe",
    risk="green",
    evidence="medium",
    benefit=["减少后台录制占用", "降低游戏内叠加层干扰"],
    side_effects=["Xbox 录制、截图、回放功能不可用"],
    applicability=["Windows 10/11"],
    requires_admin=True,
    requires_reboot=False,
    actions=[...],
)
```

必填字段：

| 字段 | 作用 |
|---|---|
| `id` | 稳定唯一 ID，用于备份、日志、扫描、回滚 |
| `title` | 用户可读名称 |
| `category` | gaming / privacy / services / network / power / gpu / input / cleanup |
| `preset` | safe / gaming / privacy / experimental |
| `risk` | green / yellow / red |
| `evidence` | high / medium / low，表示证据强度，不等于收益承诺 |
| `benefit` | 预期收益类型 |
| `side_effects` | 可能副作用 |
| `applicability` | 适用条件 |
| `requires_admin` | 是否需要管理员 |
| `requires_reboot` | 是否需要重启 |
| `actions` | detect/current/apply/rollback/verify 动作列表 |

## 9. 动作模型

每个 action 实现五段：

```text
detect -> current -> apply -> rollback -> verify
```

### 9.1 RegistrySet

用于注册表值写入。修改前备份旧值和是否存在；回滚时恢复旧值或删除原本不存在的值。

### 9.2 ServiceSetStartType

用于服务启动类型和运行状态调整。备份服务是否存在、原启动类型、原运行状态；回滚时恢复启动类型，并在原本运行时尝试启动。

### 9.3 ScheduledTaskSetEnabled

用于计划任务启用/禁用。备份是否存在和原启用状态；回滚时恢复原状态。

### 9.4 PowerCfgSet

用于 powercfg 参数。备份当前活动方案 GUID、原 AC 值、原 DC 值；回滚时写回原值。

### 9.5 CommandAction

只允许白名单命令，例如：

- `fsutil behavior`。
- `bcdedit /enum` 和受控 `/set`。
- `powershell Disable-MMAgent` / `Enable-MMAgent`。
- `netsh` 查询和受控设置。

没有检测和回滚的命令不进入默认方案。

## 10. Plan / Backup / Report

### 10.1 JSON plan

`plan` 命令输出：

```json
{
  "version": "2.0.0",
  "created_at": "2026-06-05T16:00:00",
  "preset": "safe",
  "system": {
    "windows_build": "...",
    "is_admin": false
  },
  "items": [
    {
      "id": "disable_gamedvr",
      "title": "禁用 Game DVR / Xbox 录制",
      "risk": "green",
      "side_effects": ["Xbox 录制、截图、回放功能不可用"],
      "actions": [
        {
          "type": "registry_set",
          "target": "HKCU\\System\\GameConfigStore\\GameDVR_Enabled",
          "current": 1,
          "desired": 0
        }
      ]
    }
  ]
}
```

### 10.2 备份

备份目录：

```text
%LOCALAPPDATA%/HY_Optimizer/backups/
```

备份文件升级为动作级备份，并兼容旧 v1 注册表备份。

### 10.3 报告

报告目录：

```text
%LOCALAPPDATA%/HY_Optimizer/reports/
```

报告包含：系统信息、计划、执行结果、验证结果、失败项、需重启项、备份路径。

## 11. 第一阶段落地范围

第一阶段只做可工作的垂直切片，不一次性迁移全部 68 项。

必须完成：

- 模块化包结构。
- `Optimization` 和 action 模型。
- `RegistrySet` 完整 detect/current/apply/rollback/verify。
- `ServiceSetStartType` 完整 detect/current/apply/rollback/verify。
- `ScheduledTaskSetEnabled` 只读扫描和计划输出；写入可放第二阶段。
- JSON plan 输出。
- 动作级 backup 输出。
- `scan` / `plan --preset safe` / `apply --plan` / `rollback latest` 命令。
- 首批 safe catalog：GameDVR、Game Mode、基础遥测、广告 ID、Content Delivery、Xbox 服务、DiagTrack、MapsBroker、RemoteRegistry、Fax。

第二阶段再迁移 powercfg、计划任务写入、gaming/privacy 全量、报告和打包。

## 12. 测试策略

优先写无副作用单元测试：

- registry action 用 fake backend 测试备份、应用、回滚。
- service action 用 fake backend 测试启动类型和运行状态恢复。
- catalog 测试所有优化项 ID 唯一、风险合法、必须有副作用说明。
- plan 测试输出 JSON 可解析、包含当前值和 desired 值。
- rollback 测试从 backup 恢复 fake state。

本机真实验证顺序：

1. `python -m haoyue_optimizer.main scan` 只读。
2. `python -m haoyue_optimizer.main plan --preset safe --out safe-plan.json` 只读。
3. 人工检查 plan。
4. 管理员模式应用最小 safe plan。
5. `verify`。
6. `rollback latest`。
7. 再次 `scan`。

## 13. 完成标准

- 新版 CLI 可以 scan、plan、apply、rollback。
- plan 是 JSON 且可审计。
- 应用前能展示风险和副作用。
- 注册表和服务改动都进入统一备份。
- 应用后报告区分 success / failed / skipped / pending_reboot。
- rollback 能恢复第一阶段涉及的注册表和服务。
- 旧单文件不被删除，可作为 fallback。
- 第一阶段代码能通过单元测试。
