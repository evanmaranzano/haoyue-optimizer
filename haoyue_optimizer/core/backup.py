from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def backup_root() -> Path:
    return Path.home() / "AppData" / "Local" / "HY_Optimizer" / "backups"


def write_backup(backup: dict[str, Any], backup_dir: Path | None = None) -> Path:
    root = backup_dir or backup_root()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = root / f"{stamp}-{uuid4().hex[:8]}.json"
    path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def latest_backup(backup_dir: Path | None = None) -> Path | None:
    root = backup_dir or backup_root()
    if not root.exists():
        return None
    files = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def read_backup(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
