"""
Tier 4: Real-World Application Scenarios E2E Tests (>= 10 Tests)
Simulates realistic end-to-end user and administrator workflows.
"""

import os
import sys
import unittest
import uuid

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tests.e2e.server import EdgeWorkerEmulatorServer
from tests.e2e.client_driver import E2EClient


class TestTier4Scenarios(unittest.TestCase):
    server = None
    client = None

    @classmethod
    def setUpClass(cls):
        base_url = os.environ.get("E2E_BASE_URL")
        if not base_url:
            cls.server = EdgeWorkerEmulatorServer(port=0)
            cls.server.start()
            base_url = cls.server.base_url
        cls.client = E2EClient(base_url=base_url)

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.stop()

    def setUp(self):
        base_url = (
            getattr(self, "base_url", None)
            or (self.client.base_url if hasattr(self, "client") and self.client else None)
            or (self.__class__.client.base_url if hasattr(self.__class__, "client") and self.__class__.client else None)
            or os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8787")
        )
        self.client = E2EClient(base_url=base_url)

    def test_scenario_a_full_anime_watch_session(self):
        """Simulates full CLI anime watch sequence: launch, stream ep 1, stream ep 2, download ep 3."""
        fp = f"user_session_{uuid.uuid4().hex[:8]}"

        # Step 1: User launches CLI application
        launch_resp = self.client.send_telemetry({
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "distro": "Arch Linux",
            "base": "Arch",
            "os_version": "6.12.1",
            "python_version": "3.12.0",
            "client_version": "v2.0.0"
        })
        self.assertEqual(launch_resp.status_code, 200)

        # Step 2: User streams Episode 1 of Frieren (duration 1420s)
        ep1_resp = self.client.send_telemetry({
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Sousou no Frieren",
            "episode": "1",
            "provider": "anime3rb",
            "mode": "stream",
            "duration": 1420,
            "os_name": "Linux",
            "distro": "Arch Linux",
            "base": "Arch"
        })
        self.assertEqual(ep1_resp.status_code, 200)

        # Step 3: User streams Episode 2 of Frieren (duration 1380s)
        ep2_resp = self.client.send_telemetry({
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Sousou no Frieren",
            "episode": "2",
            "provider": "anime3rb",
            "mode": "stream",
            "duration": 1380,
            "os_name": "Linux",
            "distro": "Arch Linux",
            "base": "Arch"
        })
        self.assertEqual(ep2_resp.status_code, 200)

        # Step 4: User downloads Episode 3 for offline viewing
        ep3_resp = self.client.send_telemetry({
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Sousou no Frieren",
            "episode": "3",
            "provider": "anime3rb",
            "mode": "download",
            "duration": 0,
            "os_name": "Linux",
            "distro": "Arch Linux",
            "base": "Arch"
        })
        self.assertEqual(ep3_resp.status_code, 200)

        # Step 5: Verify user dossier in dashboard
        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        user_data = user_resp.json()
        self.assertEqual(user_data["fingerprint"], fp)
        history = user_data.get("history", [])
        self.assertEqual(len(history), 3)

        episodes = [h["episode"] for h in history]
        self.assertIn("1", episodes)
        self.assertIn("2", episodes)
        self.assertIn("3", episodes)

    def test_scenario_b_cli_crash_dump_and_admin_diagnostics_workflow(self):
        """Simulates CLI fatal crash, transmission of dump, and administrator diagnostics inspection."""
        fp = f"crash_diag_{uuid.uuid4().hex[:8]}"

        # Step 1: User launches CLI
        self.client.send_telemetry({
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "distro": "Ubuntu",
            "base": "Debian"
        })

        # Step 2: Unhandled exception occurs during stream extraction
        traceback_content = """Traceback (most recent call last):
  File "src/extractor.py", line 124, in extract_stream
    raise StreamExtractionError("Provider cloudflare challenge failed")
src.exceptions.StreamExtractionError: Provider cloudflare challenge failed"""

        crash_resp = self.client.send_crash({
            "fingerprint": fp,
            "error_type": "StreamExtractionError",
            "message": "Provider cloudflare challenge failed",
            "traceback": traceback_content,
            "os_name": "Linux",
            "distro": "Ubuntu",
            "base": "Debian",
            "os_version": "24.04",
            "client_version": "v2.0.0",
            "command_args": ["ani-cli-arabic", "-q", "1080p", "One Piece", "1080"]
        })
        self.assertEqual(crash_resp.status_code, 200)

        # Step 3: Admin navigates to Crash Diagnostics Center
        self.client.login()
        crashes_resp = self.client.get_crashes(type_filter="StreamExtractionError", search=fp)
        self.assertEqual(crashes_resp.status_code, 200)
        crashes_data = crashes_resp.json().get("crashes", [])
        self.assertTrue(len(crashes_data) >= 1)

        found_crash = next((c for c in crashes_data if c["fingerprint"] == fp), None)
        self.assertIsNotNone(found_crash)
        self.assertEqual(found_crash["error_type"], "StreamExtractionError")
        self.assertIn("challenge failed", found_crash["message"])
        self.assertIn("src/extractor.py", found_crash["traceback"])

    def test_scenario_c_admin_executive_dashboard_audit(self):
        """Simulates administrator logging in and auditing executive overview KPIs and leaderboards."""
        # Step 1: Admin logs in
        login_resp = self.client.login()
        self.assertEqual(login_resp.status_code, 200)

        # Step 2: Fetch executive overview statistics
        stats_resp = self.client.get_stats(range_val="30d")
        self.assertEqual(stats_resp.status_code, 200)
        stats = stats_resp.json()

        # Step 3: Verify KPIs presence and structure
        kpis = stats.get("kpis", {})
        self.assertIn("totalUsers", kpis)
        self.assertIn("dau", kpis)
        self.assertIn("totalStreams", kpis)
        self.assertIn("appLaunches", kpis)
        self.assertIn("totalHours", kpis)

        # Step 4: Verify leaderboard and breakdown structures
        self.assertIsInstance(stats.get("topAnime", []), list)
        self.assertIsInstance(stats.get("providers", []), list)
        self.assertIsInstance(stats.get("osDistribution", []), list)

    def test_scenario_d_emergency_service_announcement_push(self):
        """Simulates pushing an emergency broadcast notice from Broadcast Hub and client receiving popup."""
        # Step 1: Admin composes and deploys emergency notice
        self.client.login()
        notice_id = f"notice-{uuid.uuid4().hex[:6]}"
        notice_title = "Scheduled Database Migration"
        deploy_resp = self.client.update_broadcast({
            "id": notice_id,
            "active": True,
            "type": "both",
            "title": notice_title,
            "message": "Servers will undergo brief maintenance at 04:00 UTC.",
            "link": "https://ani-cli-arabic.dev/status",
            "style": "amber"
        })
        self.assertEqual(deploy_resp.status_code, 200)

        # Step 2: Modern v2 CLI client checks broadcast
        v2_resp = self.client.get_broadcast(user_agent="AniCliAr-Monitor/2.0 ani-cli-arabic/2.0.0")
        self.assertEqual(v2_resp.status_code, 200)
        v2_data = v2_resp.json()
        self.assertTrue(v2_data["active"])
        self.assertEqual(v2_data["type"], "popup")
        self.assertEqual(v2_data["title"], notice_title)

        # Step 3: Legacy v1.x client checks broadcast
        legacy_resp = self.client.get_broadcast(user_agent="AniCliAr-Monitor/1.0 ani-cli-arabic/1.8.4")
        self.assertEqual(legacy_resp.status_code, 200)
        legacy_data = legacy_resp.json()
        self.assertTrue(legacy_data["active"])
        self.assertEqual(legacy_data["type"], "banner")

        # Step 4: Admin deactivates notice after incident resolution
        deactivate_resp = self.client.update_broadcast({
            "id": notice_id,
            "active": False,
            "type": "both",
            "title": "",
            "message": ""
        })
        self.assertEqual(deactivate_resp.status_code, 200)

        # Client confirms inactive
        confirm_resp = self.client.get_broadcast()
        self.assertFalse(confirm_resp.json()["active"])

    def test_scenario_e_changelog_release_and_outdated_client_alert(self):
        """Simulates publishing new release highlights and verifying changelog delivery."""
        self.client.login()
        target_version = "2.1.0"
        upd_resp = self.client.update_changelog({
            "active": True,
            "title": f"What's New in {target_version}",
            "body": "- Enhanced Arabic font shaping\n- Faster episode resolution",
            "outdated_notice": f"Your ani-cli-arabic is outdated! Update to {target_version}.",
            "latest_version": target_version
        })
        self.assertEqual(upd_resp.status_code, 200)

        # CLI client fetches changelog
        cl_resp = self.client.get_changelog()
        self.assertEqual(cl_resp.status_code, 200)
        cl_data = cl_resp.json()
        self.assertTrue(cl_data["active"])
        self.assertEqual(cl_data["latest_version"], target_version)
        self.assertIn("outdated", cl_data["outdated_notice"].lower())

    def test_scenario_f_archival_database_explorer_workflow(self):
        """Simulates administrator querying and browsing legacy monitoring_events."""
        self.client.login()
        # Query first page of historical monitoring_events
        legacy_resp = self.client.get_legacy(page=1, limit=10)
        self.assertEqual(legacy_resp.status_code, 200)
        data = legacy_resp.json()
        self.assertIn("rows", data)
        self.assertGreater(data.get("total", 0), 0)

        # Query filtered by action
        play_resp = self.client.get_legacy(page=1, limit=5, action="video_play")
        self.assertEqual(play_resp.status_code, 200)
        for row in play_resp.json().get("rows", []):
            self.assertEqual(row["action"], "video_play")

    def test_scenario_g_disaster_recovery_under_d1_quota_exhaustion(self):
        """Simulates system behavior when D1 daily read quota is exhausted."""
        q_res = self.client.set_quota_limit(enabled=True)
        if q_res.status_code != 200:
            self.skipTest("Target does not support simulated quota control")
        try:
            # 1. Dashboard requests stats - must serve verified snapshot without error
            resp_limited = self.client.get_stats(range_val="dr_test")
            self.assertEqual(resp_limited.status_code, 200)
            data = resp_limited.json()
            self.assertTrue(data.get("d1_limited"))
            self.assertTrue(data.get("is_snapshot"))
            self.assertIn("kpis", data)

            # 4. Crash diagnostics requests - serves from KV recent_crashes buffer
            crashes_resp = self.client.get_crashes()
            self.assertEqual(crashes_resp.status_code, 200)
            self.assertTrue(crashes_resp.json().get("d1_limited"))
        finally:
            self.client.set_quota_limit(enabled=False)

    def test_scenario_h_privacy_conscious_user_complete_run(self):
        """Simulates a user with analytics turned off; verifies no telemetry is ingested."""
        fp = f"priv_user_{uuid.uuid4().hex[:8]}"
        user_analytics_enabled = False

        # In application code:
        # if SettingsManager().get('analytics', True):
        #     monitor.track_app_start()
        #     monitor.track_video_play(...)
        if user_analytics_enabled:
            self.client.send_telemetry({"event_type": "launch", "fingerprint": fp})
            self.client.send_telemetry({"event_type": "watch", "fingerprint": fp, "anime_title": "Private Anime"})

        # Verify nothing was written to server for this fingerprint
        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        self.assertIsNone(user_resp.json().get("summary"))
        self.assertEqual(len(user_resp.json().get("history", [])), 0)

    def test_scenario_i_multi_distro_ecosystem_telemetry(self):
        """Simulates clients across diverse distros; verifies OS breakdown captures base families."""
        fleet = [
            ("arch_fp", "Linux", "Arch Linux", "Arch"),
            ("ubuntu_fp", "Linux", "Ubuntu 24.04", "Debian"),
            ("fedora_fp", "Linux", "Fedora 40", "RedHat"),
            ("alpine_fp", "Linux", "Alpine Linux", "Independent"),
            ("mac_fp", "macOS", "macOS Sonoma", "Darwin")
        ]
        for tag, os_name, distro, base in fleet:
            fp = f"fleet_{tag}_{uuid.uuid4().hex[:6]}"
            self.client.send_telemetry({
                "event_type": "launch",
                "fingerprint": fp,
                "os_name": os_name,
                "distro": distro,
                "base": base
            })

        stats_resp = self.client.get_stats(range_val=f"fleet_{uuid.uuid4().hex[:6]}")
        self.assertEqual(stats_resp.status_code, 200)
        os_dist = stats_resp.json().get("osDistribution", [])
        bases_found = [o.get("base") for o in os_dist]
        self.assertTrue(any(b in ["Arch", "Debian", "RedHat", "Independent", "Darwin"] for b in bases_found))

    def test_scenario_j_end_to_end_user_lifecycle(self):
        """Simulates a new user first launch, watching 3 episodes across different days, checking history."""
        fp = f"lifecycle_{uuid.uuid4().hex[:8]}"

        # First Launch
        self.client.send_telemetry({
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "distro": "EndeavourOS",
            "base": "Arch",
            "client_version": "v2.0.0"
        })

        # Watch Episode 1
        self.client.send_telemetry({
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Solo Leveling",
            "episode": "1",
            "provider": "anime3rb",
            "mode": "stream",
            "duration": 1400
        })

        # Next day: Watch Episode 2
        self.client.send_telemetry({
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Solo Leveling",
            "episode": "2",
            "provider": "anime3rb",
            "mode": "stream",
            "duration": 1410
        })

        # Verify full user dossier
        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        data = user_resp.json()
        summary = data.get("summary")
        self.assertIsNotNone(summary)
        self.assertEqual(summary["distro"], "EndeavourOS")
        self.assertEqual(len(data.get("history", [])), 2)


if __name__ == "__main__":
    unittest.main()
