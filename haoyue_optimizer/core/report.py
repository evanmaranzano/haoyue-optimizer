from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

REPORT_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "HY_Optimizer" / "reports"


def export_report(plan: dict[str, Any], backup: dict[str, Any], report_dir: Path | None = None) -> Path:
    report_dir = report_dir or REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = _summarize(backup)
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "plan": {
            "preset": plan.get("preset"),
            "item_count": len(plan.get("items", [])),
        },
        "summary": summary,
        "backup": backup,
    }
    path = report_dir / f"report_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _summarize(backup: dict[str, Any]) -> dict[str, int]:
    result = {"passed": 0, "failed": 0, "partial": 0, "pending_reboot": 0, "unsupported": 0, "skipped": 0}
    for item in backup.get("items", []):
        for action in item.get("actions", []):
            status = action.get("verify", {}).get("status", "failed")
            if status in result:
                result[status] += 1
            else:
                result["failed"] += 1
    return result
