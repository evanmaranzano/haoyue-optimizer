# 皓月定制优化工具

Windows 系统/游戏/隐私优化 CLI，模块化架构，支持：

- `scan → plan → apply → verify → rollback → report`
- 101 个 catalog 优化项 / 282 个 actions
- 73 个旧版 legacy 项完整迁移矩阵
- safe / aggressive 两档预设（aggressive 包含全部 safe）
- 动作级 backup 和 rollback
- 高风险项默认拦截，需 `--allow-experimental` 显式启用

## 快速运行

```powershell
# 只读
python -m haoyue_optimizer.main doctor
python -m haoyue_optimizer.main plan --preset safe --out safe-plan.json

# 应用计划需要管理员 PowerShell
python -m haoyue_optimizer.main apply --plan safe-plan.json --yes
python -m haoyue_optimizer.main rollback latest
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
- `experimental` 默认不可直接应用。
