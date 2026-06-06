from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path("C:/Users/Administrator")
MATRIX = ROOT / "haoyue_optimizer" / "data" / "migration_matrix.json"

EXPECTED_LEGACY_IDS = {
    "gamedvr", "gamedvr_policy", "fse", "gamemode", "hags", "vrr", "mmcss_games",
    "net_throttle", "tcp_nodelay", "dns_priority", "dns_negative", "qos_bw", "qos_nla", "net_mem",
    "kb_opt", "mouse_opt", "sticky_keys", "toggle_keys", "access_all",
    "ssd_opt", "bg_apps", "transparency", "setting_sync", "content_del", "tracking",
    "driver_search", "telemetry", "svchost_thresh", "file_alloc", "admin_share", "autorun",
    "explorer_restart", "map_download", "feeds", "soft_landing", "wu_pause",
    "mapsbroker", "svc_safe",
    "wifi_power", "cpu_unpark", "unlock_ppm", "energy_veto",
    "win32_pri", "low_latency2",
    "dns_flush", "temp_clean",
    "gaming_boost", "gaming_preset", "power_perf", "laptop_ac", "laptop_bat",
    "gpu_preempt", "superfetch", "large_cache", "disable_mmcss", "disk_no_sleep",
    "low_latency3", "wu_cache", "telemetry_full", "audio_no_excl", "startup_delay",
    "boot_timeout", "fse_global", "anim_disable", "usb_suspend_dis", "nic_nagle",
    "nic_lso_disable", "disable_prefetch", "disable_bg_tasks", "disable_mem_compress",
    "timer_res", "gpu_msi_mode", "nic_rss_opt",
}


class MigrationMatrixTests(unittest.TestCase):
    def load_matrix(self):
        return json.loads(MATRIX.read_text(encoding="utf-8"))

    def test_matrix_contains_every_legacy_id_once(self):
        payload = self.load_matrix()
        ids = [item["legacy_id"] for item in payload["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), EXPECTED_LEGACY_IDS)
        self.assertEqual(payload["legacy_count"], len(EXPECTED_LEGACY_IDS))

    def test_every_item_has_decision_fields(self):
        allowed_status = {"migrated", "merged", "planned", "experimental", "deprecated"}
        for item in self.load_matrix()["items"]:
            self.assertIn(item["new_status"], allowed_status, item["legacy_id"])
            self.assertTrue(item["decision_reason"].strip(), item["legacy_id"])
            self.assertTrue(item["verify"].strip(), item["legacy_id"])
            self.assertTrue(item["rollback"].strip(), item["legacy_id"])
            if item["new_status"] != "deprecated":
                self.assertTrue(item["side_effects"], item["legacy_id"])
            if item["new_status"] in {"migrated", "merged", "experimental"}:
                self.assertTrue(item["new_id"].strip(), item["legacy_id"])

    def test_safe_gaming_privacy_items_are_declared_rollbackable(self):
        for item in self.load_matrix()["items"]:
            if item.get("new_preset") in {"safe", "gaming", "privacy"} and item["new_status"] != "deprecated":
                self.assertNotIn("无法回滚", item["rollback"], item["legacy_id"])
                self.assertNotEqual(item["rollback"], "advisory only", item["legacy_id"])


if __name__ == "__main__":
    unittest.main()
