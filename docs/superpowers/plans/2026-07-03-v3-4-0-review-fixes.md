# v3.4.0 Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 3.4.0 深度审查发现的系统写入测试、Store-safe、安全计划、硬件过滤、显式场景和参数语义问题，并循环复审至无已知缺陷。

**Architecture:** 为 subprocess 动作贯通可注入 backend，保证测试只记录命令；Store-safe repair 复用 plan、validation、executor 和 backup 主链。规划器通过显式 profile 与硬件上下文共同过滤，注册表动作负责等价值语义。

**Tech Stack:** Python 3、unittest、Windows service/registry/powercfg backends、argparse。

---

### Task 1: 隔离 subprocess 测试

**Files:**
- Modify: `haoyue_optimizer/core/planner.py`
- Modify: `haoyue_optimizer/core/executor.py`
- Modify: `haoyue_optimizer/core/subprocess_action.py`
- Modify: `tests/test_actions.py`

- [ ] 写失败测试：planner、executor 收到 `FakeSubprocessBackend` 后只记录命令，完整测试不产生真实 subprocess 调用。
- [ ] 单独运行失败测试，确认失败来自 backend 未贯通。
- [ ] 给 `build_plan()`、`apply_plan()`、`rollback_backup()` 和 `_backend_for()` 增加 subprocess backend 注入。
- [ ] 运行测试，确认 Fake backend 同时覆盖 current/apply/verify/rollback。

### Task 2: 修复 Store-safe guard 与状态传播

**Files:**
- Modify: `haoyue_optimizer/core/compat.py`
- Modify: `haoyue_optimizer/core/service.py`
- Modify: `haoyue_optimizer/core/executor.py`
- Modify: `tests/test_actions.py`

- [ ] 写失败测试：大小写不同的受保护服务仍被阻止；停止失败不能 verify passed；executor 保留 blocked/skipped。
- [ ] 单独运行失败测试并确认失败原因。
- [ ] 对服务名使用 `casefold()`；修正 stop verify；executor 不覆盖 action 返回的终态。
- [ ] 删除本次变更产生且没有调用点的 marker/helper。
- [ ] 运行相关测试。

### Task 3: 将 repair 纳入安全主链

**Files:**
- Modify: `haoyue_optimizer/core/planner.py`
- Modify: `haoyue_optimizer/core/executor.py`
- Modify: `haoyue_optimizer/core/service.py`
- Modify: `haoyue_optimizer/main.py`
- Modify: `tests/test_cli_safety.py`
- Modify: `tests/test_backup_report.py`

- [ ] 写失败测试：repair 先生成可验证 plan，只包含 Disabled 服务；执行后产生 backup；持久化 backup 可 rollback。
- [ ] 单独运行失败测试并确认当前直接写服务实现不满足要求。
- [ ] 实现 repair plan 与补充 action registry，调用 `validate_plan_for_apply()` 和 `apply_plan()`。
- [ ] 为 service backup 增加可重建 rollback 路径；main 输出 backup 路径和失败状态。
- [ ] 运行 repair、validation、rollback 测试。

### Task 4: 修复参数与适用性语义

**Files:**
- Modify: `haoyue_optimizer/core/registry.py`
- Modify: `haoyue_optimizer/core/planner.py`
- Modify: `haoyue_optimizer/core/compat.py`
- Modify: `haoyue_optimizer/optimizations/disk.py`
- Modify: `haoyue_optimizer/optimizations/network.py`
- Modify: `haoyue_optimizer/optimizations/power.py`
- Modify: `haoyue_optimizer/main.py`
- Modify: `haoyue_optimizer/ui/cli.py`
- Modify: `tests/test_actions.py`
- Modify: `tests/test_ui_scan.py`

- [ ] 写失败测试：SystemResponsiveness 为 10；NTFS 两种禁用值均不重写；桌面排除 laptop 项；Slate 判为移动设备；显式 profile 只在 opt-in 后出现。
- [ ] 单独运行失败测试并确认对应根因。
- [ ] 实现等价值、`enabled_profiles`、`laptop_only` 和 Mobile/Slate 检测。
- [ ] CLI 增加可重复 `--profile`；自定义选择显式展示 opt-in 项。
- [ ] 运行相关测试。

### Task 5: 全量复审和发布前验证

**Files:**
- Modify: `README.md`
- Modify: tests discovered during review

- [ ] 更新 CLI/profile/repair 文档，不创建 tag、commit 或 push。
- [ ] 搜索未使用的新常量、不可达分支、真实 subprocess 测试调用和安全旁路。
- [ ] 运行 `git diff --check`。
- [ ] 运行完整 unittest，确认 38+ 项全部通过且不触碰真实系统。
- [ ] 运行只读 CLI smoke、编译检查和必要的最小复现。
- [ ] 再审 diff；若发现问题，新增失败测试并重复修复循环。
