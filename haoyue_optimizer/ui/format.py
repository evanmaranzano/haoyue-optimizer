from __future__ import annotations

import os
import subprocess

from haoyue_optimizer import VERSION

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

RISK_COLORS = {"green": GREEN, "yellow": YELLOW, "red": RED}


def clear_screen() -> None:
    subprocess.run(["cmd", "/c", "cls"] if os.name == "nt" else ["clear"])


def pause() -> None:
    input(f"\n  {DIM}按回车继续...{RESET}")


def risk_color(risk: str) -> str:
    return RISK_COLORS.get(risk, RESET)


def banner() -> str:
    title = f"皓月定制优化工具  v{VERSION}"
    title_en = "Haoyue System Optimizer v2"
    w = 50
    title_cols = sum(2 if ord(c) > 0x7f else 1 for c in title)
    l1 = (w - title_cols) // 2
    r1 = w - title_cols - l1
    l2 = (w - len(title_en)) // 2
    r2 = w - len(title_en) - l2
    return (
        f"\n{CYAN}{BOLD}  ╔{'═' * w}╗\n"
        f"  ║{' ' * l1}{title}{' ' * r1}║\n"
        f"  ║{' ' * l2}{title_en}{' ' * r2}║\n"
        f"  ╚{'═' * w}╝{RESET}\n"
    )


def print_banner() -> None:
    print(banner())


def section(title: str) -> str:
    return f"\n  {BOLD}{title}{RESET}\n  {'─' * 48}"


def risk_label(risk: str) -> str:
    color = risk_color(risk)
    return f"{color}[{risk:8s}]{RESET}"
