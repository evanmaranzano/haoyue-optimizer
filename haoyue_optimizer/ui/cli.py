from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from haoyue_optimizer import PRESETS, VERSION
from haoyue_optimizer.core.admin import is_admin
from haoyue_optimizer.core.backup import backup_root, latest_backup, read_backup
from haoyue_optimizer.core.executor import apply_plan, rollback_backup
from haoyue_optimizer.core.planner import build_plan
from haoyue_optimizer.core.report import export_report
from haoyue_optimizer.core.validation import PlanValidationError, validate_plan_for_apply
from haoyue_optimizer.ui.format import BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW, banner, clear_screen, pause, risk_label, section
from haoyue_optimizer.ui.scan import summarize_plan_status
from haoyue_optimizer.ui.selection import ask_preset, newest_plan_files, parse_selection


def run_interactive() -> int:
    clear_screen()
    print(banner())
    if not is_admin():
        print(f"  {RED}请以管理员身份运行此工具！{RESET}")
        print("  右键点击 → 以管理员身份运行")
        pause()
        return 1
    while True:
        print_main_menu()
        choice = input(f"  选择 [{GREEN}1-8{RESET}, {DIM}0{RESET}]: ").strip()
        if choice == "0":
            print(f"\n  {DIM}退出。{RESET}")
            return 0
        if choice == "1":
            scan_and_supplement()
        elif choice == "2":
            apply_preset("safe")
        elif choice == "3":
            custom_select()
        elif choice == "4":
            generate_plan()
        elif choice == "5":
            show_items()
        elif choice == "6":
            rollback_menu()
        elif choice == "7":
            print(section("系统体检"))
            print_doctor()
        elif choice == "8":
            show_presets()
        else:
            print(f"  {DIM}无效选项{RESET}")
        pause()


def print_main_menu() -> None:
    print(section("主菜单 [管理员]"))
    print(f"    {GREEN}1{RESET}  扫描系统 + 智能补充缺失项")
    print(f"    {GREEN}2{RESET}  一键应用 safe 方案")
    print(f"    {YELLOW}3{RESET}  自定义选择优化项")
    print(f"    {CYAN}4{RESET}  生成 / 查看 JSON 计划")
    print(f"    {CYAN}5{RESET}  查看全部优化项")
    print(f"    {RED}6{RESET}  恢复备份")
    print(f"    {DIM}7{RESET}  系统体检 doctor")
    print(f"    {DIM}8{RESET}  预设说明")
    print(f"    {DIM}0{RESET}  退出")
    print()


def print_scan_summary(preset: str, summary: dict) -> None:
    print(section(f"扫描结果: {preset}"))
    print(f"  {GREEN}已生效: {len(summary['applied'])}{RESET}")
    for item in summary["applied"][:20]:
        print(f"    {GREEN}✓{RESET} {item['title']}")
    print(f"\n  {YELLOW}缺失: {len(summary['missing'])}{RESET}")
    for item in summary["missing"][:30]:
        print(f"    {YELLOW}✗{RESET} {item['title']}")
    print(f"\n  {DIM}提示项: {len(summary['advisory'])}{RESET}")
    for item in summary["advisory"][:20]:
        print(f"    {DIM}! {item['title']}{RESET}")


def print_items(items: list[dict]) -> None:
    by_cat: dict[str, list[tuple[int, dict]]] = {}
    for i, item in enumerate(items):
        by_cat.setdefault(item.get("category", "other"), []).append((i, item))
    for cat, entries in by_cat.items():
        print(f"\n  {BOLD}[{cat}]{RESET}")
        for i, item in entries:
            print(f"    {DIM}{i + 1:3d}{RESET}  {risk_label(item['risk'])}  {item['title']}")


def scan_and_supplement() -> None:
    clear_screen()
    print(banner())
    preset = ask_preset()
    if not preset:
        return
    plan = build_plan(preset)
    summary = summarize_plan_status(plan)
    print_scan_summary(preset, summary)
    if not summary["missing"]:
        print(f"\n  {GREEN}没有缺失项。{RESET}")
        return
    if preset == "experimental":
        print(f"\n  {RED}experimental 不能通过智能补充直接应用，请生成计划后走高风险流程。{RESET}")
        return
    confirm = input(f"\n  是否补充缺失项？[{GREEN}y{RESET}/{DIM}N{RESET}]: ").strip().lower()
    if confirm != "y":
        print(f"  {YELLOW}已取消{RESET}")
        return
    missing_plan = {**plan, "items": summary["missing"]}
    execute_plan(missing_plan, allow_experimental=False)


def apply_preset(preset: str) -> None:
    clear_screen()
    print(banner())
    plan = build_plan(preset)
    summary = summarize_plan_status(plan)
    print_scan_summary(preset, summary)
    if not plan["items"]:
        print(f"\n  {GREEN}该预设无优化项。{RESET}")
        return
    execute_plan(plan, allow_experimental=False)


def custom_select() -> None:
    clear_screen()
    print(banner())
    preset = ask_preset()
    if not preset:
        return
    if preset == "experimental":
        print(f"\n  {RED}experimental 需要走高风险计划流程，不能在普通自定义选择中直接应用。{RESET}")
        return
    plan = build_plan(preset)
    print(section(f"自定义选择: {preset}"))
    print_items(plan["items"])
    raw = input(f"\n  输入编号（如 1,3,5），{GREEN}all{RESET} 全选，{GREEN}safe{RESET} 只选 green: ").strip()
    indices = parse_selection(raw, len(plan["items"]), plan["items"])
    if not indices:
        print(f"  {YELLOW}没有选中任何优化项{RESET}")
        return
    selected_items = [plan["items"][i] for i in indices]
    selected_plan = {**plan, "items": selected_items}
    execute_plan(selected_plan, allow_experimental=False)


def generate_plan() -> None:
    clear_screen()
    print(banner())
    preset = ask_preset()
    if not preset:
        return
    out = plan_output_path(preset)
    plan = build_plan(preset)
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    out.write_text(text, encoding="utf-8")
    print(f"\n  {GREEN}计划已保存: {out}{RESET}")
    print(f"    预设: {preset}")
    print(f"    优化项: {len(plan['items'])}")


def show_items() -> None:
    clear_screen()
    print(banner())
    preset = ask_preset()
    if not preset:
        return
    plan = build_plan(preset)
    print(f"\n  {BOLD}全部优化项 ({preset} 预设, {len(plan['items'])} 项){RESET}")
    print_items(plan["items"])
    print(f"\n  {DIM}green = 安全  |  yellow = 需确认  |  red = 高风险{RESET}")


def rollback_menu() -> None:
    clear_screen()
    print(banner())
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
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"    {DIM}{i + 1}{RESET}  {f.name}  ({size_kb:.1f} KB, {mtime})")
    sel = input(f"\n  选择编号恢复 (回车取消): ").strip()
    if not sel.isdigit() or int(sel) < 1 or int(sel) > min(len(backups), 10):
        print(f"  {YELLOW}已取消{RESET}")
        return
    path = backups[int(sel) - 1]
    backup = read_backup(path)
    rollback_backup(backup)
    print(f"\n  {GREEN}已回滚: {path.name}{RESET}")


def show_presets() -> None:
    print(section("预设说明"))
    for name, desc in PRESETS.items():
        print(f"    {CYAN}{name:14s}{RESET}  {desc}")


def print_doctor() -> None:
    for preset in PRESETS:
        plan = build_plan(preset)
        item_count = len(plan["items"])
        action_count = sum(len(item["actions"]) for item in plan["items"])
        print(f"    {CYAN}{preset:14s}{RESET}  {item_count} 项 / {action_count} 动作")


def execute_plan(plan: dict, allow_experimental: bool) -> None:
    try:
        summary = validate_plan_for_apply(plan, allow_experimental=allow_experimental)
    except PlanValidationError as exc:
        print(f"\n  {RED}计划校验失败: {exc}{RESET}")
        return
    print(format_apply_summary(summary))
    if summary["has_experimental"]:
        token = input(f"\n  输入 {RED}EXPERIMENTAL{RESET} 确认进入高风险执行: ").strip()
        if token != "EXPERIMENTAL":
            print(f"  {YELLOW}已取消{RESET}")
            return
    confirm = input(f"\n  输入 {RED}APPLY{RESET} 确认执行: ").strip()
    if confirm != "APPLY":
        print(f"  {YELLOW}已取消{RESET}")
        return
    print(f"\n  {BOLD}执行中...{RESET}")
    start = time.time()
    backup = apply_plan(plan)
    elapsed = time.time() - start
    report_path = export_report(plan, backup)
    print_execution_result(backup, report_path, elapsed)


def format_apply_summary(summary: dict) -> str:
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


def print_execution_result(backup: dict, report_path: Path, elapsed: float) -> None:
    ok = fail = skip = 0
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


def plan_output_path(preset: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path.cwd() / f"{preset}-plan-{stamp}.json"
