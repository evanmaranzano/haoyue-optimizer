# CLAUDE.md

## 项目定位

皓月定制优化工具 v2：Windows 系统/游戏/隐私优化 CLI，从旧版单文件迁移为模块化结构。

## 关键命令

```powershell
# 测试
python -m unittest discover -s F:/haoyue-optimizer/tests -t F:/haoyue-optimizer -v

# 只读运行
$env:PYTHONPATH='F:/haoyue-optimizer'
python -m haoyue_optimizer.main doctor
python -m haoyue_optimizer.main plan --preset safe --out safe-plan.json

# 打包
C:/Users/Administrator/build_env/Scripts/pyinstaller.exe F:/haoyue-optimizer/皓月定制优化工具-v2.spec --distpath F:/haoyue-optimizer/dist --workpath F:/haoyue-optimizer/build
```

## 安全边界

- 不默认执行 `experimental`；交互和 CLI 都必须显式允许高风险项。
- 写系统设置前必须生成 plan，并通过 `validate_plan_for_apply()`。
- apply/rollback 需要管理员权限。
- 不删除旧版 exe / spec；旧版文件在 `legacy/`。
- `temp_clean` 只删除超过 7 天临时文件，并跳过锁定文件。

## 结构

- `haoyue_optimizer/core/`：Action、backend、planner、executor、backup、report。
- `haoyue_optimizer/optimizations/`：按类别组织 catalog。
- `haoyue_optimizer/data/migration_matrix.json`：旧版 73 项迁移矩阵。
- `docs/haoyue_optimizer_migration_matrix.md`：人工审阅矩阵。
