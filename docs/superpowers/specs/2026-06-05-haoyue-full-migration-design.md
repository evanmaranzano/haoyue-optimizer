# 皓月定制优化工具旧版全量迁移设计

日期：2026-06-05

## 1. 背景与目标

旧版 `C:/Users/Administrator/Desktop/皓月定制优化工具.py` 包含 73 项优化。新版 `C:/Users/Administrator/haoyue_optimizer/optimizations/catalog.py` 当前只有 8 个 `Optimization` 对象，约覆盖旧版 9 项，仍缺约 64 项。

本轮目标不是把旧版 73 项无脑搬运到新版，而是做一次全量盘点、重新分级、可审计迁移。旧版每一项都必须进入新版迁移矩阵，并获得明确去向：迁移、合并、计划后续实现、实验区保留或废弃。

新版继续坚持以下定位：

> 可审计、可回滚、风险分级的 Windows 游戏 / 性能 / 隐私优化 CLI，而不是激进一键 debloat。

## 2. 范围

### 2.1 本轮要做

- 建立旧版 73 项的完整迁移矩阵。
- 为每个旧版项记录行为、目标、风险、可回滚性、验证方式和新去向。
- 补强 `apply` 安全闸门：管理员检查、plan 校验、确认机制、experimental 阻断。
- 按类别迁移可检测、可回滚、可验证的优化项。
- 把高风险或证据弱的项放入 experimental 或 deprecated。
- 保留旧版 exe，新版 exe 单独输出。
- 补齐单元测试和只读验证流程。

### 2.2 本轮不做

- 不默认禁用 Defender、防火墙、SmartScreen、UAC、Core Isolation。
- 不默认关闭 Windows Update 主链路。
- 不删除系统组件、不卸载 Appx、不清 WinSxS/DriverStore。
- 不无检测地改 HPET、CPU mitigations、GPU MSI、NIC offload、timer resolution。
- 不把清理类项目做成无提示删除。
- 不为了保留数量牺牲回滚和验证。

## 3. 迁移矩阵

### 3.1 文件

机器可测格式：

```text
C:/Users/Administrator/haoyue_optimizer/data/migration_matrix.json
```

人工审阅格式：

```text
C:/Users/Administrator/docs/haoyue_optimizer_migration_matrix.md
```

### 3.2 记录格式

每个旧版优化项一条记录：

```json
{
  "legacy_id": "gamedvr",
  "legacy_name": "禁用 Game DVR",
  "legacy_category": "游戏",
  "legacy_risk": "LOW",
  "legacy_apply_fn": "apply_gamedvr",
  "targets": [
    {
      "type": "registry_set",
      "path": "HKCU\\System\\GameConfigStore",
      "name": "GameDVR_Enabled",
      "desired": 0
    }
  ],
  "new_status": "migrated",
  "new_id": "disable_gamedvr",
  "new_preset": "safe",
  "new_risk": "green",
  "requires_admin": false,
  "requires_reboot": false,
  "side_effects": [
    "Xbox 录制、回放和截图功能不可用"
  ],
  "verify": "读取注册表值等于 desired",
  "rollback": "恢复备份值；原本不存在则删除",
  "decision_reason": "低副作用、可检测、可回滚，适合 safe。"
}
```

### 3.3 `new_status`

| 状态 | 含义 |
|---|---|
| `migrated` | 已作为新版 Optimization 实现 |
| `merged` | 合并到某个新版 Optimization |
| `planned` | 本批不实现，但保留后续计划 |
| `experimental` | 实现或保留为高风险实验项 |
| `deprecated` | 明确不再保留 |

### 3.4 矩阵约束

- 旧版 73 项必须全部出现。
- 每项必须有 `decision_reason`。
- 非 deprecated 项必须有 `side_effects`。
- `migrated`、`merged`、`experimental` 必须有 `new_id`。
- `migrated`、`experimental` 必须有可测试 target 或 advisory/noop 说明。
- 没有 rollback 的项不能进入 safe、gaming、privacy。

## 4. 分类规则

### 4.1 safe

只能放低副作用、可检测、可回滚、不影响安全/登录/更新/驱动/常用外设的项目。

典型项：GameDVR、Game Mode、广告 ID、推荐内容、可逆 UI 设置、低副作用 Explorer 或输入辅助设置。

### 4.2 gaming

适合游戏场景，但不默认静默启用。包括 HAGS、VRR、MMCSS Games、USB 选择性暂停、游戏电源计划、游戏相关 GPU 偏好、部分全屏优化策略。

要求：必须写副作用；不能承诺 FPS 提升；需要硬件/系统支持检测的，检测不到则输出 `skipped` 或 `unsupported`。

### 4.3 privacy

隐私强化但可能影响体验。包括更严格遥测、CEIP 任务、活动历史、Tailored Experiences、Bing/Web Search、Feedback frequency。

要求：不能影响 Defender、SmartScreen、Windows Update 主链路；不能删除系统组件；只允许可回滚配置更改。

### 4.4 experimental

高风险、证据弱、场景依赖强的项目。包括 HPET、timer resolution、GPU MSI、NIC offload、Nagle、RSS、CPU core parking、memory compression、prefetch/SysMain、bcdedit 相关项。

要求：默认不可 apply；plan 可以生成但标红；apply 必须同时传 `--allow-experimental --yes`；优先做 advisory/detect-only，而不是直接写系统。

### 4.5 deprecated

不建议新版继续做的项目。包括禁用 Defender、防火墙、SmartScreen、永久禁用 UAC、关闭 Windows Update 主服务、删除系统组件、无法回滚的删除操作、证据弱且副作用大的玄学优化。

## 5. 多代理分工

### 5.1 旧版解析 / 迁移矩阵代理

只读旧版源码，提取 73 项事实信息：`legacy_id`、名称、分类、风险、apply 函数、写入目标、是否有 rollback。输出迁移矩阵草稿，不直接改新版 catalog。

### 5.2 风险分类 / 产品策略代理

基于矩阵把 73 项重新分到 safe、gaming、privacy、experimental、deprecated。每项必须写保留/废弃原因、副作用、是否二次确认、是否重启、默认是否启用。

### 5.3 Action 模型代理

审查旧版项需要哪些 action 类型表达。已有 action 包括 registry、service、scheduled task、powercfg。可能新增：`RegistryDeleteValueAction`、`RegistryEnsureKeyAction`、`CommandAction`、`FileCleanupAction`、`DnsFlushAction`、`PowerCfgDuplicateSchemeAction`、`Noop/AdvisoryAction`。

没有 rollback 的 action 不允许进入 safe/gaming/privacy；没有 verify 的 action 只能进入 experimental 或 deprecated；删除类 action 默认不进自动 apply。

### 5.4 Catalog 迁移代理

根据已批准矩阵，把可迁移项写入类别文件。每个 Optimization 必须包含稳定新 ID、`legacy_ids`、title、category、preset、risk、evidence、benefit、side_effects、applicability、requires_admin、requires_reboot、actions。

多个旧版项可以合并到一个新版 Optimization，但必须记录所有 `legacy_ids`。

### 5.5 安全闸门 / CLI 代理

修改 `main.py`、executor、planner：管理员检查、`apply --yes`、`apply --allow-experimental`、交互确认、plan schema 校验、experimental 阻断、状态汇总、backup 文件名防碰撞。

### 5.6 测试 / 验证代理

扩展 fake backend 测试，覆盖 migration matrix、catalog、plan、executor、CLI smoke。修正测试运行方式，避免必须手动设置 `PYTHONPATH`。

### 5.7 主线程职责

主线程负责审阅矩阵、批准分类、合并代码、处理冲突、跑测试、跑只读 scan/plan、决定是否进入管理员真实 apply/rollback 验证。

## 6. 模块边界

建议结构：

```text
haoyue_optimizer/
  main.py
  core/
    models.py
    registry.py
    service.py
    scheduled_task.py
    power.py
    command.py
    cleanup.py
    planner.py
    executor.py
    backup.py
    report.py
    admin.py
    validation.py
    system_info.py
  optimizations/
    catalog.py
    gaming.py
    privacy.py
    services.py
    network.py
    power.py
    input.py
    disk.py
    display.py
    cleanup.py
  data/
    migration_matrix.json
```

`catalog.py` 只负责聚合，不继续塞全部 73 项。优化项按类别拆分到独立文件。

## 7. apply 安全闸门

### 7.1 权限检查

如果 plan 中有任何 `requires_admin=true` 的项，当前进程不是管理员则直接失败，并提示用管理员 PowerShell 重新运行。

### 7.2 plan 校验

apply 前校验：

- `version` 是否支持。
- `items` 是否存在。
- 每个 item 是否有 `id`、`preset`、`risk`、`actions`。
- 每个 action 是否有 `action_id`、`type`、`target`、`desired`。
- action type 是否在白名单。
- 是否包含 experimental。

无效 plan 直接拒绝。

### 7.3 确认机制

交互模式展示项目数量、action 数量、risk 分布、requires reboot 数量和 side effects 汇总，然后要求用户输入：

```text
APPLY
```

非交互模式必须传 `--yes`。

experimental plan 默认拒绝 apply，必须同时传：

```powershell
--yes --allow-experimental
```

## 8. 输出状态

apply 输出状态包括：

| 状态 | 含义 |
|---|---|
| `passed` | 写入后验证成功 |
| `failed` | 写入或验证失败 |
| `skipped` | 目标不存在或不适用 |
| `unsupported` | 当前系统不支持 |
| `pending_reboot` | 已写入但需重启后验证 |
| `partial` | 一个优化项内部分 action 成功，部分失败 |

报告目录：

```text
%LOCALAPPDATA%/HY_Optimizer/reports/
```

备份目录：

```text
%LOCALAPPDATA%/HY_Optimizer/backups/
```

备份文件名格式：

```text
YYYYMMDD-HHMMSS-<short_uuid>.json
```

## 9. 实现顺序

### Phase 1：迁移矩阵

生成 `migration_matrix.json` 和 Markdown 审阅版。73 项全部出现，deprecated 必须写原因，migrated/merged 必须写新版 ID。

### Phase 2：模型和安全闸门

补 `legacy_ids`、`applicability`、管理员检测、plan schema 校验、per-action error isolation、experimental 阻断、`--yes` 和 `--allow-experimental`。

### Phase 3：按类别迁 catalog

按类别并行迁移：gaming/input/display、privacy/system、services/scheduled-task、network、power/scheduling、disk/memory/cleanup、gpu/experimental。

### Phase 4：测试和只读验证

新增矩阵完整性、catalog、plan、executor、CLI smoke 测试。跑只读 scan/plan/doctor。

### Phase 5：真实管理员验证

只验证最小 safe plan。流程：生成 1-2 个 HKCU 低风险项的最小 plan，管理员 apply，检查 backup 和 verify，rollback latest，再 scan 确认恢复。

暂不真实验证服务停止、scheduled task 禁用、powercfg、experimental。

### Phase 6：打包

保留两个 exe：

```text
dist/皓月定制优化工具-v1-legacy.exe
dist/皓月定制优化工具-v2.exe
```

不直接覆盖桌面旧版，直到用户确认。

## 10. 测试策略

必跑测试建议改为：

```powershell
python -m unittest discover -s C:/Users/Administrator/tests -t C:/Users/Administrator -v
```

禁止默认跑真实改系统的测试。任何真实写系统测试必须满足：用户明确确认、管理员终端、最小 plan、有 backup、立即 rollback、输出完整结果。

## 11. 完成标准

### 覆盖

- 旧版 73 项全部出现在迁移矩阵。
- 每项状态为 migrated、merged、planned、experimental 或 deprecated。
- 没有悄悄丢失的旧版项目。

### 安全

- `apply` 有管理员检查。
- `apply` 有 plan schema 校验。
- 默认不能 apply experimental。
- 非交互必须 `--yes`。
- 高风险项必须有副作用和确认。
- 没有 rollback 的项不能进入 safe/gaming/privacy。

### 功能

- safe/gaming/privacy/experimental 都能生成 plan。
- 新版 catalog 至少覆盖所有可安全迁移的旧版项。
- deprecated 项有明确原因。
- backup 文件名不会同秒碰撞。
- apply 输出状态汇总。
- report 可导出。

### 验证

- 单元测试通过。
- 只读 scan/plan/doctor 通过。
- 最小真实 apply/rollback 验证通过，或明确记录未执行原因。
- 新版 PyInstaller exe 生成成功。

### 交付

- 旧版 exe 保留。
- 新版 exe 单独输出。
- spec、plan、migration matrix 可审阅。
- 用户可根据矩阵看到每个旧版项目的去向。

## 12. 自检结果

- 无 TBD/TODO 占位。
- 范围聚焦于旧版 73 项全量迁移与新版安全交付。
- 明确区分迁移、合并、计划、实验区和废弃。
- 明确禁止默认执行高风险或不可回滚项目。
- 明确测试和真实写系统验证边界。
