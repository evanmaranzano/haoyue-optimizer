# 皓月定制优化工具 v2

Windows 系统/游戏/隐私优化 CLI。v2 从旧版单文件工具迁移为模块化结构，支持：

- `scan -> plan -> apply -> verify -> rollback -> report`
- 65 个 catalog 优化项 / 151 个 actions
- 73 个旧版 legacy 项完整迁移矩阵（69 个非 deprecated 已入 catalog，4 个 deprecated 不自动执行）
- safe / gaming / privacy / experimental 四档预设
- 动作级 backup 和 rollback
- experimental 高风险项默认拦截

## 快速运行

```powershell
# 只读
$env:PYTHONPATH='F:/haoyue-optimizer'
python -m haoyue_optimizer.main doctor
python -m haoyue_optimizer.main plan --preset safe --out safe-plan.json

# 应用计划需要管理员 PowerShell
python -m haoyue_optimizer.main apply --plan safe-plan.json --yes
python -m haoyue_optimizer.main rollback latest
```

## 打包

```powershell
C:/Users/Administrator/build_env/Scripts/pyinstaller.exe F:/haoyue-optimizer/皓月定制优化工具-v2.spec --distpath F:/haoyue-optimizer/dist --workpath F:/haoyue-optimizer/build
```

## 测试

```powershell
python -m unittest discover -s F:/haoyue-optimizer/tests -t F:/haoyue-optimizer -v
```

## 目录

```text
haoyue_optimizer/           # v2 源码
haoyue_optimizer/data/      # migration_matrix.json
haoyue_optimizer/core/      # action/backend/planner/executor/backup/report
haoyue_optimizer/optimizations/ # catalog + 分类优化项
tests/                      # 单元测试
docs/                       # 设计、计划、迁移矩阵
legacy/                     # 旧版单文件与旧 spec 备份
```

## 注意

- 真实管理员 apply/rollback 仍需按最小 safe plan 单独验证。
- `experimental` 默认不可直接应用。
- `temp_clean` 只删除超过 7 天的临时文件，并跳过锁定/占用文件。
