from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from haoyue_optimizer.core.backup import latest_backup, write_backup
from haoyue_optimizer.core.report import export_report


class BackupReportTests(unittest.TestCase):
    def test_write_backup_uses_unique_names(self):
        backup = {"items": []}
        with TemporaryDirectory() as tmp:
            first = write_backup(backup, backup_dir=Path(tmp))
            second = write_backup(backup, backup_dir=Path(tmp))
            self.assertNotEqual(first.name, second.name)
            self.assertTrue(first.name.endswith(".json"))
            self.assertTrue(second.name.endswith(".json"))

    def test_latest_backup_reads_newest_file(self):
        with TemporaryDirectory() as tmp:
            first = write_backup({"name": "first", "items": []}, backup_dir=Path(tmp))
            time.sleep(1.1)
            second = write_backup({"name": "second", "items": []}, backup_dir=Path(tmp))
            latest = latest_backup(backup_dir=Path(tmp))
            self.assertEqual(latest, second)
            self.assertNotEqual(first, second)

    def test_report_counts_all_statuses(self):
        backup = {
            "items": [
                {"actions": [
                    {"verify": {"status": "passed"}},
                    {"verify": {"status": "failed"}},
                    {"verify": {"status": "skipped"}},
                    {"verify": {"status": "unsupported"}},
                    {"verify": {"status": "pending_reboot"}},
                    {"verify": {"status": "partial"}},
                    {"verify": {"status": "blocked"}},
                ]}
            ]
        }
        with TemporaryDirectory() as tmp:
            path = export_report({"preset": "safe", "items": []}, backup, report_dir=Path(tmp))
            payload = json.loads(path.read_text(encoding="utf-8"))
        for status in ("passed", "failed", "skipped", "unsupported", "pending_reboot", "partial", "blocked"):
            self.assertEqual(payload["summary"][status], 1)

    def test_unknown_status_counts_as_failed(self):
        backup = {
            "items": [
                {"actions": [
                    {"verify": {"status": "unknown_status"}},
                    {"verify": {"status": "passed"}},
                ]}
            ]
        }
        with TemporaryDirectory() as tmp:
            path = export_report({"preset": "safe", "items": []}, backup, report_dir=Path(tmp))
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["failed"], 1)
        self.assertEqual(payload["summary"]["passed"], 1)
        self.assertNotIn("unknown_status", payload["summary"])


if __name__ == "__main__":
    unittest.main()
