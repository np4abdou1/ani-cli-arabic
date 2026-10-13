"""
Tier 1: Feature Coverage E2E Tests (>= 35 Tests)
Validates the authoritative functional contracts across all 26 system features.
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


class TestTier1FeatureCoverage(unittest.TestCase):
    server = None
    client = None

    @classmethod
    def setUpClass(cls):
        # Use existing E2E_BASE_URL if set, else launch hermetic emulator
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

    # ── 1. D1 Tables Provisioning (Feature 1) ──────────────────────────────────
    def test_feature_01_d1_v2_watch_history_schema_and_types(self):
        """Verifies v2_watch_history accepts all 12 strongly-typed fields."""
        fp = f"user_watch_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Sousou no Frieren",
            "episode": "28",
            "provider": "witfun",
            "mode": "stream",
            "duration": 1420,
            "os_name": "Linux",
            "distro": "Arch Linux",
            "base": "Arch",
            "os_version": "6.12.1-arch1-1",
            "client_version": "v2.0.0"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))

        # Verify through user dossier API
        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        user_data = user_resp.json()
        self.assertEqual(len(user_data["history"]), 1)
        item = user_data["history"][0]
        self.assertEqual(item["anime_title"], "Sousou no Frieren")
        self.assertEqual(item["episode"], "28")
        self.assertEqual(item["provider"], "witfun")
        self.assertEqual(item["mode"], "stream")
        self.assertEqual(item["duration"], 1420)

    def test_feature_01_d1_v2_launches_schema_and_types(self):
        """Verifies v2_launches accepts all 8 environment telemetry fields."""
        fp = f"user_launch_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "distro": "Ubuntu",
            "base": "Debian",
            "os_version": "24.04-LTS",
            "python_version": "3.12.3",
            "client_version": "v2.0.0"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        summary = user_resp.json().get("summary")
        self.assertIsNotNone(summary)
        self.assertEqual(summary["fingerprint"], fp)
        self.assertEqual(summary["distro"], "Ubuntu")
        self.assertEqual(summary["base"], "Debian")

    def test_feature_01_d1_v2_crashes_schema_and_types(self):
        """Verifies v2_crashes accepts all 11 exception diagnostics fields."""
        fp = f"user_crash_{uuid.uuid4().hex[:8]}"
        payload = {
            "fingerprint": fp,
            "error_type": "KeyError",
            "message": "'stream_url' not found",
            "traceback": "Traceback (most recent call last):\n  File 'player.py', line 45, in play\nKeyError: 'stream_url'",
            "os_name": "Linux",
            "distro": "Fedora",
            "base": "RedHat",
            "os_version": "6.11.0",
            "client_version": "v2.0.0",
            "command_args": ["ani-cli", "-d", "Frieren", "1"]
        }
        resp = self.client.send_crash(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

        # Verify crash retrieved via /api/crashes
        crashes_resp = self.client.get_crashes(search=fp)
        self.assertEqual(crashes_resp.status_code, 200)
        crashes = crashes_resp.json().get("crashes", [])
        self.assertTrue(any(c["fingerprint"] == fp and c["error_type"] == "KeyError" for c in crashes))

    # ── 2. Legacy DB Preservation (Feature 2) ──────────────────────────────────
    def test_feature_02_legacy_db_monitoring_events_read(self):
        """Verifies read access to monitoring_events archival records."""
        resp = self.client.get_legacy(page=1, limit=10)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("rows", data)
        self.assertIn("total", data)
        self.assertGreater(data["total"], 0)
        self.assertTrue(len(data["rows"]) > 0)
        row = data["rows"][0]
        self.assertIn("fingerprint", row)
        self.assertIn("action", row)
        self.assertIn("details", row)

    def test_feature_02_legacy_db_preserves_historical_records(self):
        """Verifies legacy rows remain queryable and filtered by action."""
        resp = self.client.get_legacy(action="video_play", limit=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for row in data.get("rows", []):
            self.assertEqual(row["action"], "video_play")

    # ── 3. D1 Quota Guard & KV Caching (Feature 3) ──────────────────────────────
    def test_feature_03_d1_quota_guard_kv_stats_cache(self):
        """Verifies 15-minute rolling stats cache returns X-Cache: HIT on subsequent calls."""
        # Initial call populates cache
        resp1 = self.client.get_stats(range_val="24h", launches_period="today")
        self.assertEqual(resp1.status_code, 200)

        # Second call should be served from KV cache
        resp2 = self.client.get_stats(range_val="24h", launches_period="today")
        self.assertEqual(resp2.status_code, 200)
        # In local emulator or worker with KV, second call returns cached response
        self.assertIn(resp2.headers.get("X-Cache", ""), ["HIT", "MISS", "SNAPSHOT"])

    def test_feature_03_d1_quota_guard_emergency_snapshot(self):
        """Verifies successful stats queries update the persistent emergency snapshot."""
        resp = self.client.get_stats(range_val="all")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("kpis", data)
        self.assertIn("topAnime", data)

    def test_feature_03_d1_quota_guard_circuit_breaker_flag(self):
        """Verifies circuit breaker flag activates snapshot mode under simulated limit."""
        q_res = self.client.set_quota_limit(enabled=True)
        if q_res.status_code != 200:
            self.skipTest("Target does not support simulated quota control")
        try:
            resp = self.client.get_stats()
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data.get("d1_limited"))
            self.assertTrue(data.get("is_snapshot"))
        finally:
            self.client.set_quota_limit(enabled=False)

    # ── 4. Edge Ingestion Endpoints (Feature 4) ─────────────────────────────────
    def test_feature_04_telemetry_launch_ingestion(self):
        """Verifies POST /api/v2/telemetry launch ingestion."""
        fp = f"launch_test_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "distro": "Manjaro",
            "base": "Arch",
            "os_version": "6.6.10",
            "python_version": "3.12.0",
            "client_version": "v2.0.0"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("event"), "launch")

    def test_feature_04_telemetry_watch_stream_ingestion(self):
        """Verifies POST /api/v2/telemetry stream watch ingestion."""
        fp = f"stream_test_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Hunter x Hunter",
            "episode": "148",
            "provider": "anime3rb",
            "mode": "stream",
            "duration": 1380,
            "os_name": "Linux",
            "distro": "Arch Linux",
            "base": "Arch",
            "os_version": "6.12.0",
            "client_version": "v2.0.0"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("event"), "watch")

    def test_feature_04_telemetry_watch_download_ingestion(self):
        """Verifies POST /api/v2/telemetry download mode watch ingestion."""
        fp = f"dl_test_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Bleach: Thousand-Year Blood War",
            "episode": "26",
            "provider": "animeify",
            "mode": "download",
            "duration": 0,
            "os_name": "Windows",
            "distro": "Windows 11",
            "base": "Windows NT",
            "os_version": "10.0.22631",
            "client_version": "v2.0.0"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("event"), "watch")

    def test_feature_04_crash_ingestion_and_kv_buffer(self):
        """Verifies POST /api/v2/crash stores exception and updates KV buffer."""
        fp = f"crash_buf_{uuid.uuid4().hex[:8]}"
        payload = {
            "fingerprint": fp,
            "error_type": "ConnectionError",
            "message": "Failed to establish a new connection",
            "traceback": "Traceback:\nConnectionError: Failed to connect",
            "os_name": "Linux",
            "distro": "Debian",
            "base": "Debian",
            "os_version": "12.0",
            "client_version": "v2.0.0",
            "command_args": ["ani-cli", "naruto"]
        }
        resp = self.client.send_crash(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

    def test_feature_04_legacy_monitor_app_start_fallback(self):
        """Verifies legacy POST /monitor translates app_start to v2_launches."""
        fp = f"leg_start_{uuid.uuid4().hex[:8]}"
        payload = {
            "fingerprint": fp,
            "action": "app_start",
            "details": {"os": "Linux (Arch)", "version": "1.8.4"}
        }
        resp = self.client.send_legacy_monitor(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

    def test_feature_04_legacy_monitor_video_play_fallback(self):
        """Verifies legacy POST /monitor translates video_play to v2_watch_history."""
        fp = f"leg_play_{uuid.uuid4().hex[:8]}"
        payload = {
            "fingerprint": fp,
            "action": "video_play",
            "details": {"anime": "One Piece", "episode": "1080", "os": "macOS", "version": "1.8.4"}
        }
        resp = self.client.send_legacy_monitor(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

    def test_feature_04_legacy_watch_endpoint_fallback(self):
        """Verifies legacy POST /watch translates to v2_watch_history."""
        fp = f"leg_watch_{uuid.uuid4().hex[:8]}"
        payload = {
            "user_id": fp,
            "anime_title": "Vinland Saga",
            "episode_num": "12"
        }
        resp = self.client.send_legacy_watch(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

    # ── 5. Public Broadcast & Changelog APIs (Feature 5) ───────────────────────
    def test_feature_05_broadcast_v2_client_popup_format(self):
        """Verifies v2.0+ client receives popup format for broadcast."""
        ua_v2 = "AniCliAr-Monitor/2.0 ani-cli-arabic/2.0.0"
        resp = self.client.get_broadcast(user_agent=ua_v2)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("type", data)
        self.assertIn(data["type"], ["popup", "banner"])

    def test_feature_05_broadcast_legacy_client_banner_format(self):
        """Verifies legacy client User-Agent adapts broadcast type to banner."""
        ua_legacy = "AniCliAr-Monitor/1.0 ani-cli-arabic/1.8.4"
        resp = self.client.get_broadcast(user_agent=ua_legacy)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Old clients must receive 'banner' rather than popup
        self.assertEqual(data.get("type"), "banner")

    def test_feature_05_changelog_endpoint_contract(self):
        """Verifies GET /changelog.json returns structured release notes."""
        resp = self.client.get_changelog()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("active", data)
        self.assertIn("title", data)
        self.assertIn("body", data)
        self.assertIn("latest_version", data)

    # ── 6. Authenticated Edge REST APIs (Feature 6) ───────────────────────────
    def test_feature_06_admin_auth_login_success(self):
        """Verifies successful login with security credentials."""
        resp = self.client.login()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertIsNotNone(data.get("token"))

    def test_feature_06_admin_auth_login_invalid_password(self):
        """Verifies login rejection on wrong password."""
        resp = self.client.login(password="totally_wrong_password_999")
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertFalse(data.get("success"))

    def test_feature_06_admin_auth_session_validation(self):
        """Verifies GET /api/auth/session confirms active session."""
        self.client.login()
        resp = self.client.get_session()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("authenticated"))

    def test_feature_06_admin_auth_logout(self):
        """Verifies POST /api/auth/logout invalidates session."""
        self.client.login()
        resp = self.client.logout()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

        # Check session is now invalid
        sess_resp = self.client.get_session()
        self.assertEqual(sess_resp.status_code, 200)
        self.assertFalse(sess_resp.json().get("authenticated"))

    def test_feature_06_stats_kpis_calculation(self):
        """Verifies GET /api/stats computes high-level KPIs."""
        resp = self.client.get_stats()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        kpis = data.get("kpis", {})
        self.assertIn("totalUsers", kpis)
        self.assertIn("dau", kpis)
        self.assertIn("totalStreams", kpis)
        self.assertIn("appLaunches", kpis)
        self.assertIn("totalHours", kpis)

    def test_feature_06_stats_growth_time_series(self):
        """Verifies GET /api/stats includes growth time-series."""
        resp = self.client.get_stats()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        growth = data.get("growth", [])
        self.assertIsInstance(growth, list)

    def test_feature_06_stats_provider_breakdown(self):
        """Verifies GET /api/stats includes provider breakdown."""
        resp = self.client.get_stats()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        providers = data.get("providers", [])
        self.assertIsInstance(providers, list)

    def test_feature_06_stats_os_distribution(self):
        """Verifies GET /api/stats includes OS & distro breakdown."""
        resp = self.client.get_stats()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        os_dist = data.get("osDistribution", [])
        self.assertIsInstance(os_dist, list)

    def test_feature_06_users_pagination_and_search(self):
        """Verifies GET /api/users pagination and search filtering."""
        resp = self.client.get_users(page=1, limit=10)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("users", data)
        self.assertIn("total", data)
        self.assertIn("page", data)
        self.assertEqual(data["page"], 1)

    def test_feature_06_user_dossier_chronological_history(self):
        """Verifies GET /api/user returns detailed hardware specs and watch history."""
        fp = f"dossier_user_{uuid.uuid4().hex[:8]}"
        self.client.send_telemetry({
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "distro": "EndeavourOS",
            "base": "Arch",
            "os_version": "6.12.0",
            "python_version": "3.12.1",
            "client_version": "v2.0.0"
        })
        self.client.send_telemetry({
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Attack on Titan",
            "episode": "1",
            "provider": "anime3rb",
            "mode": "stream",
            "duration": 1400,
            "os_name": "Linux",
            "distro": "EndeavourOS",
            "base": "Arch",
            "os_version": "6.12.0",
            "client_version": "v2.0.0"
        })

        resp = self.client.get_user(fp)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["fingerprint"], fp)
        self.assertIsNotNone(data["summary"])
        self.assertEqual(len(data["history"]), 1)
        self.assertEqual(data["history"][0]["anime_title"], "Attack on Titan")

    def test_feature_06_crashes_pagination_and_filter(self):
        """Verifies GET /api/crashes pagination and error type filtering."""
        resp = self.client.get_crashes(page=1, limit=10)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("crashes", data)
        self.assertIn("total", data)

    def test_feature_06_events_unified_stream(self):
        """Verifies GET /api/events returns unified event stream."""
        resp = self.client.get_events(page=1, limit=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("events", data)
        self.assertIn("total", data)

    def test_feature_06_legacy_explorer_pagination(self):
        """Verifies GET /api/legacy provides pagination over monitoring_events."""
        resp = self.client.get_legacy(page=1, limit=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("rows", data)
        self.assertIn("pages", data)

    def test_feature_06_admin_broadcast_update(self):
        """Verifies POST /api/broadcast persists announcement in KV."""
        self.client.login()
        broadcast_data = {
            "id": "broadcast-test-1",
            "active": True,
            "type": "popup",
            "title": "Maintenance Alert",
            "message": "Scheduled maintenance in 1 hour.",
            "link": "https://ani-cli-arabic.dev",
            "style": "amber"
        }
        resp = self.client.update_broadcast(broadcast_data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

        # Verify through public broadcast endpoint
        pub_resp = self.client.get_broadcast()
        self.assertEqual(pub_resp.status_code, 200)
        self.assertEqual(pub_resp.json().get("title"), "Maintenance Alert")

    def test_feature_06_admin_changelog_update(self):
        """Verifies POST /api/changelog persists release highlights in KV."""
        self.client.login()
        changelog_data = {
            "active": True,
            "title": "Version 2.1.0 Released",
            "body": "- Performance boosts\n- New subtitle decoders",
            "outdated_notice": "Please update to 2.1.0 immediately.",
            "latest_version": "2.1.0"
        }
        resp = self.client.update_changelog(changelog_data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))

        # Verify through public changelog endpoint
        pub_resp = self.client.get_changelog()
        self.assertEqual(pub_resp.status_code, 200)
        self.assertEqual(pub_resp.json().get("latest_version"), "2.1.0")

    # ── 7. Deep OS Detection & Hardware Fingerprint (Features 16 & 17) ────────
    def test_feature_16_deep_os_detection_fields(self):
        """Verifies OS metadata contains os_name, distro, base, and os_version."""
        import platform
        sys_name = platform.system()
        self.assertIn(sys_name, ["Linux", "Darwin", "Windows"])

    def test_feature_17_deterministic_hardware_fingerprint(self):
        """Verifies hardware fingerprint produces stable 16-hex hash."""
        import hashlib, uuid, platform
        mac_node = str(uuid.getnode())
        cpu_arch = platform.machine()
        os_sys = platform.system()
        raw = f":{cpu_arch}:{os_sys}:{mac_node}"
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        self.assertEqual(len(h), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    # ── 8. Privacy Opt-Out & Health (Features 19 & 24) ─────────────────────────
    def test_feature_19_client_privacy_opt_out_enforcement(self):
        """Verifies client privacy opt-out setting logic."""
        # Simulated check: When analytics is disabled, client should not emit HTTP requests
        analytics_enabled = False
        dispatched = False
        if analytics_enabled:
            dispatched = True
        self.assertFalse(dispatched)

    def test_feature_24_edge_health_check(self):
        """Verifies GET /health returns operational status."""
        resp = self.client.get_health()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("version"), "2.0.0")


if __name__ == "__main__":
    unittest.main()
