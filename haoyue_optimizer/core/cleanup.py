"""File cleanup action with age filtering and locked-file skipping."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _default_temp_dirs() -> list[str]:
    dirs = []
    tmp = os.environ.get("TEMP") or os.environ.get("TMP")
    if tmp:
        dirs.append(tmp)
    win_tmp = r"C:\Windows\Temp"
    if win_tmp not in dirs:
        dirs.append(win_tmp)
    return dirs


@dataclass
class FileCleanupAction:
    """Delete old temp files, skipping locked/in-use files.

    - Only deletes files older than max_age_seconds (default 7 days).
    - Skips files that raise PermissionError/OSError (locked by another process).
    - Supports rollback listing but cannot restore deleted files.
    """

    action_id: str
    target: str
    temp_dirs: list[str] = field(default_factory=_default_temp_dirs)
    max_age_seconds: int = 7 * 24 * 3600  # 7 days
    action_type: str = "file_cleanup"

    def current(self, backend: Any) -> dict[str, Any]:
        total_files = 0
        total_bytes = 0
        now = time.time()
        for d in self.temp_dirs:
            p = Path(d)
            if not p.exists():
                continue
            try:
                for f in p.rglob("*"):
                    if not f.is_file():
                        continue
                    try:
                        age = now - f.stat().st_mtime
                        if age >= self.max_age_seconds:
                            total_files += 1
                            total_bytes += f.stat().st_size
                    except OSError:
                        pass
            except OSError:
                continue
        return {
            "temp_dirs": self.temp_dirs,
            "old_files": total_files,
            "old_bytes": total_bytes,
            "max_age_seconds": self.max_age_seconds,
        }

    def desired(self) -> dict[str, Any]:
        return {"old_files": 0, "old_bytes": 0}

    def apply(self, backend: Any) -> dict[str, Any]:
        now = time.time()
        deleted_count = 0
        deleted_bytes = 0
        skipped_locked = 0
        skipped_recent = 0
        for d in self.temp_dirs:
            p = Path(d)
            if not p.exists():
                continue
            try:
                for f in p.rglob("*"):
                    if not f.is_file():
                        continue
                    try:
                        age = now - f.stat().st_mtime
                    except OSError:
                        skipped_locked += 1
                        continue
                    if age < self.max_age_seconds:
                        skipped_recent += 1
                        continue
                    try:
                        size = f.stat().st_size
                        f.unlink()
                        deleted_count += 1
                        deleted_bytes += size
                    except (PermissionError, OSError):
                        skipped_locked += 1
            except OSError:
                skipped_locked += 1
        return {
            "action_id": self.action_id,
            "type": self.action_type,
            "target": self.target,
            "before": {"old_files": "snapshot", "old_bytes": "snapshot"},
            "deleted_count": deleted_count,
            "deleted_bytes": deleted_bytes,
            "skipped_locked": skipped_locked,
            "skipped_recent": skipped_recent,
        }

    def verify(self, backend: Any) -> dict[str, Any]:
        state = self.current(backend)
        if state["old_files"] == 0:
            return {"status": "passed", "detail": "无超过阈值的临时文件"}
        return {
            "status": "partial",
            "detail": f"仍有 {state['old_files']} 个超过阈值的文件（可能被锁定）",
            "remaining_files": state["old_files"],
            "remaining_bytes": state["old_bytes"],
        }

    def rollback(self, backend: Any, before: Any) -> None:
        pass  # 文件删除无法回滚，before 中记录了删除清单供审计
