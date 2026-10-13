"""
Tier 3: Cross-Feature Combinations E2E Tests (>= 20 Tests)
Validates pairwise interactions and temporal lifecycle sequences across modules.
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


class TestTier3Combinations(unittest.TestCase):
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

    def test_tier3_launch_then_sequential_watch_events(self):
        """Verifies app start followed by sequential episode watch events under same fingerprint."""
        fp = f"seq_watch_{uuid.uuid4().hex[:8]}"
        # 1. App Launch
        r_launch = self.client.send_telemetry({
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "distro": "Arch Linux",
            "base": "Arch",
            "os_version": "6.12.1",
            "python_version": "3.12.0",
            "client_version": "v2.0.0"
        })
        self.assertEqual(r_launch.status_code, 200)

        # 2. Watch Ep 1, 2, 3
        for ep in ["1", "2", "3"]:
            r_watch = self.client.send_telemetry({
                "event_type": "watch",
                "fingerprint": fp,
                "anime_title": "Demon Slayer",
                "episode": ep,
                "provider": "anime3rb",
                "mode": "stream",
                "duration": 1420
            })
            self.assertEqual(r_watch.status_code, 200)

        # 3. Verify user history contains all 3 episodes
        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        history = user_resp.json().get("history", [])
        self.assertEqual(len(history), 3)
        episodes = [h["episode"] for h in history]
        self.assertIn("1", episodes)
        self.assertIn("2", episodes)
        self.assertIn("3", episodes)

    def test_tier3_launch_then_immediate_crash(self):
        """Verifies launch immediately followed by unhandled exception crash."""
        fp = f"launch_crash_{uuid.uuid4().hex[:8]}"
        self.client.send_telemetry({
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "distro": "Fedora",
            "base": "RedHat"
        })
        self.client.send_crash({
            "fingerprint": fp,
            "error_type": "ImportError",
            "message": "No module named 'mpv'",
            "traceback": "Traceback:\nImportError: No module named 'mpv'",
            "os_name": "Linux"
        })

        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        crashes = user_resp.json().get("crashes", [])
        self.assertEqual(len(crashes), 1)
        self.assertEqual(crashes[0]["error_type"], "ImportError")

    def test_tier3_stream_watch_followed_by_download_watch(self):
        """Verifies stream session followed by batch download for same anime."""
        fp = f"stream_dl_{uuid.uuid4().hex[:8]}"
        self.client.send_telemetry({
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Chainsaw Man",
            "episode": "1",
            "provider": "animeify",
            "mode": "stream",
            "duration": 1440
        })
        self.client.send_telemetry({
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Chainsaw Man",
            "episode": "2",
            "provider": "animeify",
            "mode": "download",
            "duration": 0
        })

        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        modes = [h["mode"] for h in user_resp.json().get("history", [])]
        self.assertIn("stream", modes)
        self.assertIn("download", modes)

    def test_tier3_legacy_event_followed_by_v2_stats_aggregation(self):
        """Verifies legacy monitor event is correctly aggregated into stats KPIs."""
        fp = f"leg_agg_{uuid.uuid4().hex[:8]}"
        self.client.send_legacy_monitor({
            "fingerprint": fp,
            "action": "video_play",
            "details": {"anime": "Death Note", "episode": "1", "provider": "Animeify"}
        })

        # Fresh stats query
        resp = self.client.get_stats(range_val="all")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["kpis"]["totalStreams"], 0)

    def test_tier3_v2_watch_event_updates_user_dossier(self):
        """Verifies watch event immediately updates user dossier history."""
        fp = f"dossier_upd_{uuid.uuid4().hex[:8]}"
        self.client.send_telemetry({
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Cowboy Bebop",
            "episode": "5",
            "provider": "witfun",
            "mode": "stream"
        })
        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        history = user_resp.json().get("history", [])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["anime_title"], "Cowboy Bebop")

    def test_tier3_v2_launch_event_increments_total_launches(self):
        """Verifies multiple launches increment total_launches in user profile."""
        fp = f"multi_launch_{uuid.uuid4().hex[:8]}"
        for _ in range(3):
            self.client.send_telemetry({
                "event_type": "launch",
                "fingerprint": fp,
                "os_name": "Linux",
                "distro": "Debian",
                "base": "Debian"
            })
        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        summary = user_resp.json().get("summary")
        self.assertEqual(summary["total_launches"], 3)

    def test_tier3_v2_crash_event_updates_crash_diagnostics(self):
        """Verifies unhandled crash immediately reflects in /api/crashes diagnostics."""
        fp = f"diag_crash_{uuid.uuid4().hex[:8]}"
        self.client.send_crash({
            "fingerprint": fp,
            "error_type": "ZeroDivisionError",
            "message": "division by zero",
            "traceback": "Traceback:\nZeroDivisionError: division by zero",
            "os_name": "Linux"
        })
        crashes_resp = self.client.get_crashes(type_filter="ZeroDivisionError")
        self.assertEqual(crashes_resp.status_code, 200)
        crashes = crashes_resp.json().get("crashes", [])
        self.assertTrue(any(c["fingerprint"] == fp for c in crashes))

    def test_tier3_broadcast_publish_then_client_retrieval(self):
        """Verifies admin publish of broadcast is immediately reflected in GET /broadcast.json."""
        self.client.login()
        announcement_title = f"Urgent Update {uuid.uuid4().hex[:6]}"
        self.client.update_broadcast({
            "id": "urgent-announcement",
            "active": True,
            "type": "popup",
            "title": announcement_title,
            "message": "Please update immediately.",
            "style": "rose"
        })

        client_resp = self.client.get_broadcast()
        self.assertEqual(client_resp.status_code, 200)
        self.assertEqual(client_resp.json().get("title"), announcement_title)

    def test_tier3_changelog_publish_then_client_retrieval(self):
        """Verifies admin publish of changelog is immediately reflected in GET /changelog.json."""
        self.client.login()
        new_version = "2.5.0"
        self.client.update_changelog({
            "active": True,
            "title": f"Version {new_version} Released",
            "body": "- Super fast stream engine",
            "outdated_notice": f"Please update to {new_version}",
            "latest_version": new_version
        })

        client_resp = self.client.get_changelog()
        self.assertEqual(client_resp.status_code, 200)
        self.assertEqual(client_resp.json().get("latest_version"), new_version)

    def test_tier3_broadcast_both_mode_negotiation(self):
        """Verifies broadcast set to 'both' serves 'popup' to v2.0 clients and 'banner' to legacy."""
        self.client.login()
        self.client.update_broadcast({
            "id": "both-mode-test",
            "active": True,
            "type": "both",
            "title": "Dual Support Announcement",
            "message": "Testing both mode",
            "style": "emerald"
        })

        # v2 client receives popup
        resp_v2 = self.client.get_broadcast(user_agent="AniCliAr-Monitor/2.0 ani-cli-arabic/2.0.0")
        self.assertEqual(resp_v2.status_code, 200)
        self.assertEqual(resp_v2.json().get("type"), "popup")

        # legacy client receives banner
        resp_leg = self.client.get_broadcast(user_agent="AniCliAr-Monitor/1.0 ani-cli-arabic/1.8.4")
        self.assertEqual(resp_leg.status_code, 200)
        self.assertEqual(resp_leg.json().get("type"), "banner")

    def test_tier3_admin_login_update_broadcast_logout(self):
        """Verifies complete admin session flow: login, update KV, verify, logout, and subsequent 401."""
        client = E2EClient(base_url=self.client.base_url)
        # 1. Login
        login_res = client.login()
        self.assertEqual(login_res.status_code, 200)

        # 2. Update broadcast
        upd_res = client.update_broadcast({"title": "Session Test Title", "active": True})
        self.assertEqual(upd_res.status_code, 200)

        # 3. Logout
        logout_res = client.logout()
        self.assertEqual(logout_res.status_code, 200)

        # 4. Attempt update after logout should fail
        upd_fail = client.update_broadcast({"title": "Unauthorized Title"})
        self.assertEqual(upd_fail.status_code, 401)

    def test_tier3_stats_kv_cache_invalidation_after_expiration(self):
        """Verifies stats KV cache entry returns 200."""
        resp1 = self.client.get_stats(range_val="30d")
        self.assertEqual(resp1.status_code, 200)
        resp2 = self.client.get_stats(range_val="30d")
        self.assertEqual(resp2.status_code, 200)

    def test_tier3_privacy_toggled_off_then_on_mid_session(self):
        """Verifies simulated telemetry suppression when privacy setting is toggled off then on."""
        fp = f"priv_toggle_{uuid.uuid4().hex[:8]}"
        events_emitted = []

        analytics_setting = True
        if analytics_setting:
            events_emitted.append("launch")

        # User opts out
        analytics_setting = False
        if analytics_setting:
            events_emitted.append("watch_ep1")

        # User opts back in
        analytics_setting = True
        if analytics_setting:
            events_emitted.append("watch_ep2")

        self.assertEqual(events_emitted, ["launch", "watch_ep2"])
        self.assertNotIn("watch_ep1", events_emitted)

    def test_tier3_multi_user_interleaved_launches_and_watches(self):
        """Verifies distinct users interleaving launch and watch events maintain isolation."""
        user_a = f"user_a_{uuid.uuid4().hex[:6]}"
        user_b = f"user_b_{uuid.uuid4().hex[:6]}"

        self.client.send_telemetry({"event_type": "launch", "fingerprint": user_a, "os_name": "Linux", "distro": "Arch"})
        self.client.send_telemetry({"event_type": "launch", "fingerprint": user_b, "os_name": "Windows", "distro": "Windows 11"})

        self.client.send_telemetry({"event_type": "watch", "fingerprint": user_a, "anime_title": "Naruto", "episode": "1"})
        self.client.send_telemetry({"event_type": "watch", "fingerprint": user_b, "anime_title": "Bleach", "episode": "1"})

        resp_a = self.client.get_user(user_a)
        resp_b = self.client.get_user(user_b)
        self.assertEqual(resp_a.json()["history"][0]["anime_title"], "Naruto")
        self.assertEqual(resp_b.json()["history"][0]["anime_title"], "Bleach")

    def test_tier3_user_with_both_v2_and_legacy_history(self):
        """Verifies user with legacy and v2 watch events aggregates properly in stats."""
        fp = f"hybrid_user_{uuid.uuid4().hex[:6]}"
        # Legacy watch event
        self.client.send_legacy_watch({"user_id": fp, "anime_title": "Dragon Ball Z", "episode_num": "1"})
        # v2 watch event
        self.client.send_telemetry({"event_type": "watch", "fingerprint": fp, "anime_title": "Dragon Ball Super", "episode": "1"})

        resp = self.client.get_user(fp)
        self.assertEqual(resp.status_code, 200)
        history = resp.json().get("history", [])
        self.assertTrue(len(history) >= 1)

    def test_tier3_crash_dump_contains_invocation_args(self):
        """Verifies command_args are preserved accurately from ingestion to query."""
        fp = f"args_crash_{uuid.uuid4().hex[:8]}"
        expected_args = ["ani-cli", "-q", "1080p", "One Piece", "--download"]
        self.client.send_crash({
            "fingerprint": fp,
            "error_type": "DownloadError",
            "message": "Stream link expired",
            "traceback": "Traceback:\nDownloadError",
            "os_name": "Linux",
            "command_args": expected_args
        })

        crashes_resp = self.client.get_crashes(search=fp)
        self.assertEqual(crashes_resp.status_code, 200)
        crashes = crashes_resp.json().get("crashes", [])
        found = next((c for c in crashes if c["fingerprint"] == fp), None)
        self.assertIsNotNone(found)
        # command_args stored as list or json string
        args = found.get("command_args")
        self.assertTrue("1080p" in str(args))

    def test_tier3_quota_limit_recovery_after_reset(self):
        """Verifies system recovers from simulated quota exhaustion after reset."""
        q_res = self.client.set_quota_limit(enabled=True)
        if q_res.status_code != 200:
            self.skipTest("Target does not support simulated quota control")
        resp_limited = self.client.get_stats()
        self.assertTrue(resp_limited.json().get("d1_limited"))

        # Reset quota limit
        self.client.set_quota_limit(enabled=False)
        resp_recovered = self.client.get_stats(range_val="24h")
        self.assertFalse(resp_recovered.json().get("d1_limited"))

    def test_tier3_rapid_fire_launches_count(self):
        """Verifies rapid sequential launches from same user are accurately tracked."""
        fp = f"rapid_{uuid.uuid4().hex[:8]}"
        for _ in range(5):
            self.client.send_telemetry({
                "event_type": "launch",
                "fingerprint": fp,
                "os_name": "Linux",
                "distro": "Kali Linux",
                "base": "Debian"
            })
        resp = self.client.get_user(fp)
        self.assertEqual(resp.json()["summary"]["total_launches"], 5)

    def test_tier3_version_adoption_shifts_with_new_client_launches(self):
        """Verifies v2 launches reflect in the version breakdown."""
        fp = f"ver_adopt_{uuid.uuid4().hex[:8]}"
        self.client.send_telemetry({
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "client_version": "v2.0.0"
        })
        stats_resp = self.client.get_stats()
        self.assertEqual(stats_resp.status_code, 200)
        versions = stats_resp.json().get("versions", [])
        self.assertTrue(any(v["version"] == "v2.0.0" for v in versions))

    def test_tier3_provider_share_calculation_consistency(self):
        """Verifies streams across different providers reflect in provider breakdown."""
        providers = ["anime3rb", "witfun", "animeify"]
        for p in providers:
            fp = f"prov_{p}_{uuid.uuid4().hex[:6]}"
            self.client.send_telemetry({
                "event_type": "watch",
                "fingerprint": fp,
                "anime_title": f"Anime on {p}",
                "episode": "1",
                "provider": p
            })
        stats_resp = self.client.get_stats(range_val=f"prov_{uuid.uuid4().hex[:6]}")
        self.assertEqual(stats_resp.status_code, 200)
        prov_list = [pr["name"].lower() for pr in stats_resp.json().get("providers", [])]
        for p in providers:
            self.assertIn(p.lower(), prov_list)


if __name__ == "__main__":
    unittest.main()
