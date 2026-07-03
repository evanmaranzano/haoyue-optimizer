# 皓月定制优化工具

Windows 系统/游戏/隐私优化 CLI，模块化架构，支持：

- `scan → plan → apply → verify → rollback → report`
- 147 个 catalog 优化项 / 374 个 actions
- 73 个旧版 legacy 项完整迁移矩阵
- safe / aggressive 两档预设（aggressive 包含全部 safe）
- 动作级 backup 和 rollback
- `no_printer` / `kiosk` / `server_no_print` / `extreme_only` 场景必须通过 `--profile` 显式启用

## 快速运行

```powershell
# 只读
python -m haoyue_optimizer.main doctor
python -m haoyue_optimizer.main plan --preset safe --out safe-plan.json
python -m haoyue_optimizer.main plan --preset aggressive --profile no_printer --out no-printer-plan.json

# 应用计划需要管理员 PowerShell
python -m haoyue_optimizer.main apply --plan safe-plan.json --yes
python -m haoyue_optimizer.main rollback latest

# 仅修复当前处于 Disabled 的 Store-safe 受保护服务；同样生成备份
python -m haoyue_optimizer.main repair-store-safe
```

## 打包

```powershell
C:/Users/Administrator/build_env/Scripts/pyinstaller.exe F:/haoyue-optimizer/皓月定制优化工具-v3.spec --distpath F:/haoyue-optimizer/dist --workpath F:/haoyue-optimizer/build
```

## 测试

```powershell
python -m unittest discover -s F:/haoyue-optimizer/tests -t F:/haoyue-optimizer -v
```

## 目录

```text
haoyue_optimizer/              # 源码
haoyue_optimizer/data/         # migration_matrix.json
haoyue_optimizer/core/         # action/backend/planner/executor/backup/report
haoyue_optimizer/optimizations/ # catalog + 分类优化项
tests/                         # 单元测试
docs/                          # 设计、计划、迁移矩阵
legacy/                        # 旧版单文件与旧 spec 备份
```

## 注意

- 真实管理员 apply/rollback 仍需按最小 safe plan 单独验证。
- 普通 safe/aggressive 不包含显式场景项；交互式“自定义选择”会展示这些项，但仍需逐项选择。
