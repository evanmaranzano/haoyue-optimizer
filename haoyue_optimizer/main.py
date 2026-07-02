from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from haoyue_optimizer import PRESETS, VERSION
from haoyue_optimizer.core.admin import is_admin
from haoyue_optimizer.core.backup import latest_backup, read_backup
from haoyue_optimizer.core.executor import apply_plan, rollback_backup
from haoyue_optimizer.core.planner import build_plan
from haoyue_optimizer.core.report import export_report
from haoyue_optimizer.core.service import repair_store_safe_services
from haoyue_optimizer.core.compat import STORE_SAFE_PROTECTED_SERVICES
from haoyue_optimizer.core.validation import PlanValidationError, validate_plan_for_apply

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def main(argv: list[str] | None = None) -> int:
    if argv is None and len(sys.argv) == 1:
        from haoyue_optimizer.ui.cli import run_interactive
        return run_interactive()

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

    rollback_parser = sub.add_parser("rollback", help="按备份回滚")
    rollback_parser.add_argument("target", nargs="?", default="latest")

    report_parser = sub.add_parser("export-report", help="从 plan 和 backup 导出报告")
    report_parser.add_argument("--plan", required=True)
    report_parser.add_argument("--backup", required=True)

    repair_parser = sub.add_parser("repair-store-safe", help="修复被禁用 Store-safe 服务为推荐启动类型")
    repair_parser.add_argument("--yes", action="store_true", help="跳过确认")

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
            summary = validate_plan_for_apply(plan)
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

    if args.command == "repair-store-safe":
        if not is_admin():
            print("repair-store-safe 需要管理员权限，请用管理员 PowerShell 重新运行。", file=sys.stderr)
            return 3
        if not args.yes:
            print(f"  即将检查 {len(STORE_SAFE_PROTECTED_SERVICES)} 个受保护服务")
            print("  修复规则: 仅将 Disabled → 推荐启动类型，不动其他状态\n")
            confirm = input(f"  输入 {RED}REPAIR{RESET} 确认: ").strip()
            if confirm != "REPAIR":
                print(f"  {YELLOW}已取消{RESET}", file=sys.stderr)
                return 4
        repairs = repair_store_safe_services()
        fixed = [r for r in repairs if r["status"] == "repaired"]
        failed = [r for r in repairs if r["status"] == "failed"]
        if fixed:
            print(f"\n  {GREEN}已修复 {len(fixed)} 个服务:{RESET}")
            for r in fixed:
                print(f"    {r['service']}: Disabled → {r['after']}")
        if failed:
            print(f"\n  {RED}修复失败 {len(failed)} 个:{RESET}")
            for r in failed:
                print(f"    {r['service']}: {r.get('detail', 'unknown error')}")
        if not fixed and not failed:
            print(f"  {GREEN}无需修复，所有受保护服务状态正常{RESET}")
        return 0

    return 1


def _format_scan(plan: dict) -> str:
    preset = plan["preset"]
    items = plan["items"]
    risk_counts: dict[str, int] = {}
    lines = []
    lines.append(f"  {BOLD}预设: {preset}{RESET}  ({len(items)} 项)")
    lines.append("")
    for item in items:
        r = item["risk"]
        risk_counts[r] = risk_counts.get(r, 0) + 1
        rc = RISK_COLOR.get(r, RESET)
        lines.append(f"    {rc}[{r:8s}]{RESET}  {item['title']}")
    lines.append("")
    parts = []
    for r in ("green", "yellow", "red"):
        if r in risk_counts:
            rc = RISK_COLOR.get(r, RESET)
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


RISK_COLOR = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m"}


if __name__ == "__main__":
    raise SystemExit(main())
