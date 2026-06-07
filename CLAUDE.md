# CLAUDE.md

## 项目定位

皓月定制优化工具：Windows 系统优化 CLI，两档预设（safe/aggressive），从旧版单文件迁移为模块化结构。

## 关键命令

```powershell
# 测试
python -m unittest discover -s F:/haoyue-optimizer/tests -t F:/haoyue-optimizer -v

# 只读运行
$env:PYTHONPATH='F:/haoyue-optimizer'
python -m haoyue_optimizer.main doctor
python -m haoyue_optimizer.main plan --preset safe --out safe-plan.json

# 打包（spec 文件名含版本号，版本号变了要改 spec 文件名和 exe name）
C:/Users/Administrator/build_env/Scripts/pyinstaller.exe F:/haoyue-optimizer/皓月定制优化工具-v3.spec --distpath F:/haoyue-optimizer/dist --workpath F:/haoyue-optimizer/build
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
- Defender WMI Autologgers（`DefenderApiLogger`/`DefenderAuditLogger`）ACL 保护，管理员也写不进去，必须排除
- 电源方案优化必须先切平衡（`PowerCfgSetActiveAction`）再改参数，不能直接改当前方案
- 批量替换 preset：`sed -i 's/preset="old"/preset="new"/g' file1.py file2.py`
- 测试命令：`cd F:/haoyue-optimizer && $env:PYTHONPATH='F:/haoyue-optimizer'; python -m unittest discover -s tests -t . -v`

## 构建注意事项

- PyInstaller 缓存：修改 `core/` 下文件后必须 `rm -rf build/` 再构建，否则 exe 内含旧代码
- exe 被占用：关闭运行中的 exe 再构建；或先用临时文件名构建再 rename
- spec 动态版本：已从 `__init__.py` 读取 VERSION，改版本号后构建自动对齐文件名

## Windows 保护服务（Tamper Protection）

- wscsvc/AppXSvc/ClipSVC/WaaSMedicSvc 等被 Tamper Protection 锁死
- `sc config` 返回 exit 5，注册表 `CreateKeyEx(KEY_WRITE)` 也返回 WinError 5
- 处理方式：`ServiceNotModifiable` 异常 → executor 标记 skipped（非 failed）
- 不要静默 pass 异常，否则 verify 会误报 failed

## Action ID 唯一性

- `RegistrySetAction` 的 action_id = `{qualifier}:registry:{root}\{path}\{name}`
- 同一注册表路径在不同 Optimization 中出现时，必须用 `qualifier` 区分
- 添加新 optimization 后跑 `python -m pytest tests/` 检查 action ID 唯一性

## 注册表类型注意事项

- `binary` 类型（如 `UserPreferencesMask`）在测试中导致 JSON 序列化失败，避免使用或单独处理
- `ServiceStartTypeAction` 的 start_type 映射：`"manual"` → sc 的 `"demand"`，不要直接传 `"demand"`
- `SystemResponsiveness` 推荐值 10（AtlasOS/ReviOS 对齐），非 0

## 添加新优化项的标准流程

1. 在对应 `optimizations/*.py` 文件中添加 `Optimization(...)`
2. 确保 action_id 全局唯一（检查是否有 qualifier 冲突）
3. `cd F:/haoyue-optimizer && python -m pytest tests/` 验证
4. 更新 `__init__.py` 的 VERSION
5. `rm -rf build/` + 重新构建 exe
