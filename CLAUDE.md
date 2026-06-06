# CLAUDE.md

## 项目定位

皓月定制优化工具 v2：Windows 系统优化 CLI，两档预设（safe/aggressive），从旧版单文件迁移为模块化结构。

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

- 两档预设：`safe`（green 风险项）和 `aggressive`（yellow/red 风险项）。
- aggressive 项需输入 `AGGRESSIVE` 确认风险，再输入 `APPLY` 执行。
- 写系统设置前必须生成 plan，并通过 `validate_plan_for_apply()`。
- apply/rollback 需要管理员权限。
- 不删除旧版 exe / spec；旧版文件在 `legacy/`。
- `temp_clean` 只删除超过 7 天临时文件，并跳过锁定文件。

## 结构

- `haoyue_optimizer/core/`：Action、backend、planner、executor、backup、report。
- `haoyue_optimizer/optimizations/`：按类别组织 catalog。
- `haoyue_optimizer/ui/`：交互式终端 UI（format、scan、selection、cli）。
- `haoyue_optimizer/data/migration_matrix.json`：旧版 73 项迁移矩阵。
- `docs/haoyue_optimizer_migration_matrix.md`：人工审阅矩阵。

## 预设

两档：`safe`（安全，green 风险项）和 `aggressive`（激进，yellow/red 风险项）。

## 已知坑点

- CJK 双宽字符：Python `f"{text:<10s}"` 不感知全角字符宽度，banner 对齐需手动计算 `sum(2 if ord(c)>0x7f else 1 for c in text)`
- 循环导入：UI 模块需要共享常量时，把常量放到 `__init__.py`（如 PRESETS），不要从 main.py 导入
- 测试路径：用 `Path(__file__).resolve().parent.parent` 做相对引用，不要硬编码绝对路径
- MINGW64 终端 exe 输出中文乱码，Windows cmd/PowerShell 正常
- 批量替换 preset：`sed -i 's/preset="old"/preset="new"/g' file1.py file2.py`
- 测试命令：`cd F:/haoyue-optimizer && $env:PYTHONPATH='F:/haoyue-optimizer'; python -m unittest discover -s tests -t . -v`
