from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from haoyue_optimizer import VERSION
from haoyue_optimizer.core.admin import is_admin
from haoyue_optimizer.core.backup import latest_backup, read_backup
from haoyue_optimizer.core.executor import apply_plan, rollback_backup
from haoyue_optimizer.core.planner import build_plan
from haoyue_optimizer.core.report import export_report
from haoyue_optimizer.core.validation import PlanValidationError, validate_plan_for_apply

PRESETS = {
    "safe": "安全默认：低副作用、可直接恢复的注册表和服务项",
    "gaming": "游戏优化：电源、输入、游戏模式等需要确认的项",
    "privacy": "隐私强化：遥测、CEIP、兼容性任务等需要确认的项",
    "experimental": "高风险实验：默认不应用，仅生成计划和提示",
}

RISK_COLOR = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m"}
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _clear():
    subprocess.run(["cmd", "/c", "cls"] if os.name == "nt" else ["clear"])


def _banner():
    print(f"""
{CYAN}{BOLD}  ╔══════════════════════════════════════════════════╗
  ║          皓月定制优化工具  v{VERSION:<10s}             ║
  ║        Haoyue System Optimizer v2                 ║
  ╚══════════════════════════════════════════════════╝{RESET}
""")


def _risk_color(risk: str) -> str:
    return RISK_COLOR.get(risk, RESET)


def _pause():
    input(f"\n  {DIM}按回车继续...{RESET}")


def _format_scan(plan: dict) -> str:
    preset = plan["preset"]
    items = plan["items"]
    risk_counts: dict[str, int] = {}
    side_effect_total = 0
    lines = []
    lines.append(f"  {BOLD}预设: {preset}{RESET}  ({len(items)} 项)")
    lines.append("")
    for item in items:
        r = item["risk"]
        risk_counts[r] = risk_counts.get(r, 0) + 1
        rc = _risk_color(r)
        lines.append(f"    {rc}[{r:8s}]{RESET}  {item['title']}")
        for eff in item.get("side_effects", []):
            lines.append(f"    {DIM}  副作用: {eff}{RESET}")
            side_effect_total += 1
    lines.append("")
    parts = []
    for r in ("green", "yellow", "red"):
        if r in risk_counts:
            rc = _risk_color(r)
            parts.append(f"{rc}{r}={risk_counts[r]}{RESET}")
    lines.append(f"  风险分布: {' / '.join(parts)}")
    return "\n".join(lines)


def _format_presets() -> str:
    lines = []
    for name, desc in PRESETS.items():
        lines.append(f"    {CYAN}{name:14s}{RESET}  {desc}")
    return "\n".join(lines)


def _format_doctor() -> str:
    lines = []
    lines.append(f"  {BOLD}系统体检{RESET}")
    lines.append(f"  {'─' * 48}")
    for preset in PRESETS:
        plan = build_plan(preset)
        item_count = len(plan["items"])
        action_count = sum(len(item["actions"]) for item in plan["items"])
        lines.append(f"    {CYAN}{preset:14s}{RESET}  {item_count} 项 / {action_count} 动作")
    return "\n".join(lines)


def _format_apply_summary(summary: dict) -> str:
    lines = [
        f"\n  {BOLD}即将应用计划{RESET}",
        f"  {'─' * 48}",
        f"    优化项: {summary['item_count']}",
        f"    动作数: {summary['action_count']}",
        f"    风险分布: {summary['risk_counts']}",
    ]
    if summary["requires_reboot"]:
        lines.append(f"    {YELLOW}需要重启的项: {summary['requires_reboot']}{RESET}")
    if summary["side_effects"]:
        lines.append(f"\n  {BOLD}副作用{RESET}")
        for eff in summary["side_effects"][:15]:
            lines.append(f"    {YELLOW}• {eff}{RESET}")
        if len(summary["side_effects"]) > 15:
            lines.append(f"    {DIM}... 等 {len(summary['side_effects'])} 条{RESET}")
    return "\n".join(lines)


def _print_menu(items: list[dict]):
    by_cat: dict[str, list] = {}
    for i, item in enumerate(items):
        cat = item.get("category", "other")
        by_cat.setdefault(cat, []).append((i, item))

    for cat, entries in by_cat.items():
        print(f"\n  {BOLD}[{cat}]{RESET}")
        for i, item in entries:
            rc = _risk_color(item["risk"])
            print(f"    {DIM}{i + 1:3d}{RESET}  {rc}[{item['risk']:8s}]{RESET}  {item['title']}")


def main(argv: list[str] | None = None) -> int:
    if argv is None and len(sys.argv) == 1:
        return _interactive_menu()

    parser = argparse.ArgumentParser(prog="皓月定制优化工具")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_parser = sub.add_parser("scan", help="扫描指定预设当前状态")
    scan_parser.add_argument("--preset", default="safe", choices=PRESETS.keys())

    sub.add_parser("doctor", help="只读体检全部预设")
    sub.add_parser("presets", help="查看预设说明")

    plan_parser = sub.add_parser("plan", help="生成 JSON 变更计划")
    plan_parser.add_argument("--preset", default="safe", choices=PRESETS.keys())
    plan_parser.add_argument("--out")

    apply_parser = sub.add_parser("apply", help="应用 JSON 变更计划")
    apply_parser.add_argument("--plan", required=True)
    apply_parser.add_argument("--report", action="store_true")
    apply_parser.add_argument("--yes", action="store_true", help="跳过交互确认")
    apply_parser.add_argument("--allow-experimental", action="store_true", help="允许应用 experimental 计划")

    rollback_parser = sub.add_parser("rollback", help="按备份回滚")
    rollback_parser.add_argument("target", nargs="?", default="latest")

    report_parser = sub.add_parser("export-report", help="从 plan 和 backup 导出报告")
    report_parser.add_argument("--plan", required=True)
    report_parser.add_argument("--backup", required=True)

    args = parser.parse_args(argv)

    if args.command == "scan":
        plan = build_plan(args.preset)
        print(_format_scan(plan))
        return 0

    if args.command == "doctor":
        print(_format_doctor())
        return 0

    if args.command == "presets":
        print(_format_presets())
        return 0

    if args.command == "plan":
        plan = build_plan(args.preset)
        text = json.dumps(plan, ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        else:
            print(text)
        return 0

    if args.command == "apply":
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        try:
            summary = validate_plan_for_apply(plan, allow_experimental=args.allow_experimental)
        except PlanValidationError as exc:
            print(f"计划校验失败: {exc}", file=sys.stderr)
            return 2
        if summary["requires_admin"] and not is_admin():
            print("此计划需要管理员权限，请用管理员 PowerShell 重新运行。", file=sys.stderr)
            return 3
        if not args.yes:
            print(_format_apply_summary(summary))
            confirm = input(f"\n  输入 {RED}APPLY{RESET} 确认执行: ").strip()
            if confirm != "APPLY":
                print(f"  {YELLOW}已取消{RESET}", file=sys.stderr)
                return 4
        backup = apply_plan(plan)
        if args.report:
            report_path = export_report(plan, backup)
            backup["report_path"] = str(report_path)
        print(json.dumps(backup, ensure_ascii=False, indent=2))
        return 0

    if args.command == "rollback":
        path = latest_backup() if args.target == "latest" else Path(args.target)
        if path is None:
            print("未找到备份", file=sys.stderr)
            return 1
        backup = read_backup(path)
        rollback_backup(backup)
        print(f"已回滚: {path}")
        return 0

    if args.command == "export-report":
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        backup = json.loads(Path(args.backup).read_text(encoding="utf-8"))
        print(export_report(plan, backup))
        return 0

    return 1


# ─── 交互菜单 ───────────────────────────────────────────


def _interactive_menu() -> int:
    _clear()
    _banner()

    if not is_admin():
        print(f"  {RED}请以管理员身份运行此工具！{RESET}")
        print(f"  右键点击 → 以管理员身份运行")
        _pause()
        return 1

    while True:
        admin_tag = f" {GREEN}[管理员]{RESET}" if is_admin() else f" {YELLOW}[普通用户]{RESET}"
        print(f"\n  {BOLD}主菜单{RESET}{admin_tag}")
        print(f"  {'─' * 48}")
        print(f"    {GREEN}1{RESET}  扫描系统状态 + 智能补充缺失项")
        print(f"    {GREEN}2{RESET}  一键应用 safe 方案")
        print(f"    {YELLOW}3{RESET}  生成变更计划（预览不修改）")
        print(f"    {CYAN}4{RESET}  系统体检 doctor")
        print(f"    {CYAN}5{RESET}  查看全部优化项")
        print(f"    {RED}6{RESET}  恢复备份")
        print(f"    {DIM}7{RESET}  查看预设说明")
        print(f"    {DIM}0{RESET}  退出")
        print()

        choice = input(f"  选择 [{GREEN}1-7{RESET}, {DIM}0{RESET}]: ").strip()

        if choice == "0":
            print(f"\n  {DIM}退出。{RESET}")
            return 0

        elif choice == "1":
            _do_scan_and_apply()

        elif choice == "2":
            _do_apply_preset("safe")

        elif choice == "3":
            _do_generate_plan()

        elif choice == "4":
            _clear()
            _banner()
            print(_format_doctor())

        elif choice == "5":
            _do_show_all_items()

        elif choice == "6":
            _do_rollback()

        elif choice == "7":
            _clear()
            _banner()
            print(f"  {BOLD}预设说明{RESET}")
            print(f"  {'─' * 48}")
            print(_format_presets())

        else:
            print(f"  {DIM}无效选项{RESET}")

        _pause()


def _do_scan_and_apply():
    """扫描系统状态，按预设展示，确认后应用。"""
    _clear()
    _banner()

    preset = _ask_preset()
    if not preset:
        return

    print(f"\n  {BOLD}扫描中...{RESET}")
    plan = build_plan(preset)
    print(_format_scan(plan))

    if not plan["items"]:
        print(f"\n  {GREEN}该预设无优化项。{RESET}")
        return

    print(f"\n  {BOLD}是否应用此方案？{RESET}")
    print(f"    {GREEN}y{RESET}  应用 ({len(plan['items'])} 项)")
    print(f"    {DIM}n{RESET}  取消")
    confirm = input(f"\n  选择: ").strip().lower()
    if confirm != "y":
        print(f"  {YELLOW}已取消{RESET}")
        return

    _execute_plan(plan, preset)


def _do_apply_preset(preset: str):
    """直接生成并应用指定预设。"""
    _clear()
    _banner()

    print(f"  {BOLD}生成 {preset} 计划...{RESET}")
    plan = build_plan(preset)
    print(_format_scan(plan))

    if not plan["items"]:
        print(f"\n  {GREEN}该预设无优化项。{RESET}")
        return

    try:
        summary = validate_plan_for_apply(plan, allow_experimental=False)
    except PlanValidationError as exc:
        print(f"\n  {RED}计划校验失败: {exc}{RESET}")
        return

    print(_format_apply_summary(summary))
    confirm = input(f"\n  输入 {RED}APPLY{RESET} 确认执行: ").strip()
    if confirm != "APPLY":
        print(f"  {YELLOW}已取消{RESET}")
        return

    _execute_plan(plan, preset)


def _do_generate_plan():
    """生成 JSON 计划文件，不应用。"""
    _clear()
    _banner()

    preset = _ask_preset()
    if not preset:
        return

    out = Path.cwd() / f"{preset}-plan.json"
    plan = build_plan(preset)
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    out.write_text(text, encoding="utf-8")
    print(f"\n  {GREEN}计划已保存: {out}{RESET}")
    print(f"    预设: {preset}")
    print(f"    优化项: {len(plan['items'])}")
    print(f"    {DIM}可用选项 1 扫描查看，或用选项 5 查看详情{RESET}")


def _do_show_all_items():
    """展示全部优化项，按类别分组，带风险色标。"""
    _clear()
    _banner()

    preset = _ask_preset()
    if not preset:
        return

    plan = build_plan(preset)
    print(f"\n  {BOLD}全部优化项 ({preset} 预设, {len(plan['items'])} 项){RESET}")
    _print_menu(plan["items"])
    print(f"\n  {DIM}green = 安全  |  yellow = 需确认  |  red = 高风险{RESET}")


def _do_rollback():
    """展示可用备份并回滚。"""
    _clear()
    _banner()

    from haoyue_optimizer.core.backup import backup_root
    root = backup_root()
    if not root.exists():
        print(f"  {DIM}无备份文件{RESET}")
        return

    backups = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        print(f"  {DIM}无备份文件{RESET}")
        return

    print(f"  {BOLD}可用备份 ({len(backups)} 个):{RESET}")
    for i, f in enumerate(backups[:10]):
        size_kb = f.stat().st_size / 1024
        print(f"    {DIM}{i + 1}{RESET}  {f.name}  ({size_kb:.1f} KB)")

    sel = input(f"\n  选择编号恢复 (回车取消): ").strip()
    if not sel.isdigit() or int(sel) < 1 or int(sel) > len(backups[:10]):
        print(f"  {YELLOW}已取消{RESET}")
        return

    path = backups[int(sel) - 1]
    backup = read_backup(path)
    rollback_backup(backup)
    print(f"\n  {GREEN}已回滚: {path.name}{RESET}")


def _execute_plan(plan: dict, preset: str):
    """执行计划，显示进度和结果。"""
    import time

    print(f"\n  {BOLD}执行中...{RESET}")
    start = time.time()
    backup = apply_plan(plan)
    elapsed = time.time() - start

    report_path = export_report(plan, backup)

    ok = 0
    fail = 0
    skip = 0
    for item in backup.get("items", []):
        for act in item.get("actions", []):
            status = act.get("verify", {}).get("status", "failed")
            if status == "passed":
                ok += 1
            elif status in ("skipped", "unsupported"):
                skip += 1
            else:
                fail += 1

    print(f"\n  {BOLD}执行完成{RESET} ({elapsed:.1f}s)")
    print(f"  {'─' * 48}")
    print(f"    {GREEN}✓ 成功: {ok}{RESET}")
    if skip:
        print(f"    {DIM}⊘ 跳过: {skip}{RESET}")
    if fail:
        print(f"    {RED}✗ 失败: {fail}{RESET}")
    print(f"\n    {DIM}报告: {report_path}{RESET}")
    print(f"    {DIM}备份: {backup.get('backup_path', '内存')}{RESET}")
    if fail:
        print(f"\n    {YELLOW}部分项失败，可使用菜单 6 回滚{RESET}")


def _ask_preset() -> str | None:
    """让用户选择预设。"""
    print(f"\n  {BOLD}选择预设:{RESET}")
    presets = list(PRESETS.keys())
    for i, name in enumerate(presets, 1):
        desc = PRESETS[name]
        print(f"    {GREEN}{i}{RESET}  {CYAN}{name}{RESET}  {DIM}{desc}{RESET}")
    choice = input(f"\n  选择编号 (回车取消): ").strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(presets):
        return None
    return presets[int(choice) - 1]


if __name__ == "__main__":
    raise SystemExit(main())
