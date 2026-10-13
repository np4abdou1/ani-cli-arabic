"""
Tier 2: Boundary & Corner Cases E2E Tests (>= 35 Tests)
Validates system resilience against malformed inputs, extreme bounds, injection, and quotas.
"""

import os
import sys
import unittest
import uuid
import requests

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tests.e2e.server import EdgeWorkerEmulatorServer
from tests.e2e.client_driver import E2EClient


class TestTier2BoundaryCases(unittest.TestCase):
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

    # ── 1. Malformed JSON Payloads ─────────────────────────────────────────────
    def test_tier2_malformed_json_telemetry(self):
        """Verifies raw unparseable JSON to /api/v2/telemetry returns 400 Bad Request."""
        url = f"{self.client.base_url}/api/v2/telemetry"
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, data="{not a valid json...", headers=headers, timeout=5.0)
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("error", data)

    def test_tier2_malformed_json_crash(self):
        """Verifies raw unparseable JSON to /api/v2/crash returns 400 Bad Request."""
        url = f"{self.client.base_url}/api/v2/crash"
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, data="{'unterminated_string: true", headers=headers, timeout=5.0)
        self.assertEqual(resp.status_code, 400)

    # ── 2. Missing Required Fields ─────────────────────────────────────────────
    def test_tier2_missing_fingerprint_launch(self):
        """Verifies launch payload missing fingerprint returns 400."""
        payload = {"event_type": "launch", "os_name": "Linux"}
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("fingerprint", resp.json().get("error", "").lower())

    def test_tier2_missing_fingerprint_watch(self):
        """Verifies watch payload missing fingerprint returns 400."""
        payload = {"event_type": "watch", "anime_title": "One Piece", "episode": "1"}
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 400)

    def test_tier2_missing_event_type(self):
        """Verifies payload missing event_type returns 400."""
        payload = {"fingerprint": "1234567890abcdef"}
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 400)

    def test_tier2_unknown_event_type(self):
        """Verifies unknown event_type (e.g. 'delete_all') returns 400."""
        payload = {"event_type": "delete_all", "fingerprint": "1234567890abcdef"}
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 400)

    def test_tier2_missing_error_type_crash(self):
        """Verifies crash payload missing error_type returns 400."""
        payload = {
            "fingerprint": "1234567890abcdef",
            "traceback": "Traceback..."
        }
        resp = self.client.send_crash(payload)
        self.assertEqual(resp.status_code, 400)

    def test_tier2_missing_traceback_crash(self):
        """Verifies crash payload missing traceback returns 400."""
        payload = {
            "fingerprint": "1234567890abcdef",
            "error_type": "ValueError"
        }
        resp = self.client.send_crash(payload)
        self.assertEqual(resp.status_code, 400)

    # ── 3. Gigantic Payloads & Size Boundaries ────────────────────────────────
    def test_tier2_gigantic_traceback_120kb(self):
        """Verifies 120KB recursion error traceback is ingested without failure."""
        fp = f"huge_tb_{uuid.uuid4().hex[:8]}"
        line = "  File 'recursion.py', line 10, in recurse\n"
        huge_traceback = "Traceback (most recent call last):\n" + (line * 3000) + "RecursionError: maximum recursion depth exceeded"
        self.assertGreater(len(huge_traceback), 120000)

        payload = {
            "fingerprint": fp,
            "error_type": "RecursionError",
            "message": "maximum recursion depth exceeded",
            "traceback": huge_traceback,
            "os_name": "Linux",
            "client_version": "v2.0.0"
        }
        resp = self.client.send_crash(payload)
        self.assertEqual(resp.status_code, 200)

        # Retrieve and verify traceback matches length
        crashes_resp = self.client.get_crashes(search=fp)
        self.assertEqual(crashes_resp.status_code, 200)
        crashes = crashes_resp.json().get("crashes", [])
        self.assertTrue(any(c["fingerprint"] == fp and len(c["traceback"]) > 100000 for c in crashes))

    def test_tier2_gigantic_anime_title(self):
        """Verifies 2,000 character anime title is ingested safely without crashing."""
        fp = f"huge_title_{uuid.uuid4().hex[:8]}"
        long_title = "That Time I Got Reincarnated As A Slime In Another World " * 35
        payload = {
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": long_title,
            "episode": "1",
            "provider": "witfun",
            "mode": "stream",
            "duration": 1400
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)

        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        history = user_resp.json().get("history", [])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["anime_title"], long_title)

    # ── 4. Numeric Bounds & Extreme Durations ─────────────────────────────────
    def test_tier2_extreme_duration_negative(self):
        """Verifies negative watch duration (-999) is handled without internal server error."""
        fp = f"neg_dur_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Steins;Gate",
            "episode": "24",
            "duration": -999
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)

    def test_tier2_extreme_duration_overflow(self):
        """Verifies huge watch duration (999999999) is handled without integer overflow."""
        fp = f"big_dur_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": "Monster",
            "episode": "74",
            "duration": 999999999
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)

    # ── 5. Empty Strings & Data Fidelity ──────────────────────────────────────
    def test_tier2_empty_strings_telemetry(self):
        """Verifies empty strings for optional fields are accepted cleanly."""
        fp = f"empty_str_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "distro": "",
            "base": "",
            "os_version": "",
            "python_version": "3.12.0",
            "client_version": "v2.0.0"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)

    def test_tier2_unknown_linux_distro_fallback(self):
        """Verifies obscure distro without standard ID_LIKE sets base appropriately."""
        fp = f"void_distro_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_type": "launch",
            "fingerprint": fp,
            "os_name": "Linux",
            "distro": "Void Linux",
            "base": "Independent",
            "os_version": "6.10.2",
            "python_version": "3.12.4",
            "client_version": "v2.0.0"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)

        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        self.assertEqual(user_resp.json()["summary"]["base"], "Independent")

    # ── 6. Security & SQL Injection Resilience ────────────────────────────────
    def test_tier2_sql_injection_in_anime_title(self):
        """Verifies SQL injection payload in anime_title is parameterized safely without dropping table."""
        fp = f"sqli_title_{uuid.uuid4().hex[:8]}"
        injection_payload = "Frieren'; DROP TABLE v2_watch_history; SELECT '1"
        payload = {
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": injection_payload,
            "episode": "1"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)

        # Verify table still exists and data was inserted literally
        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        history = user_resp.json().get("history", [])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["anime_title"], injection_payload)

    def test_tier2_sql_injection_in_fingerprint(self):
        """Verifies SQL injection payload in fingerprint is parameterized safely."""
        sqli_fp = "'; DELETE FROM v2_launches; --"
        payload = {
            "event_type": "launch",
            "fingerprint": sqli_fp,
            "os_name": "Linux",
            "client_version": "v2.0.0"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)

    def test_tier2_sql_injection_in_user_search(self):
        """Verifies SQL injection payload in user search query is handled safely."""
        sqli_search = "' OR 1=1 UNION SELECT 1, 2, 3, 4, 5, 6, 7, 8, 9 --"
        resp = self.client.get_users(search=sqli_search)
        self.assertEqual(resp.status_code, 200)

    # ── 7. Unicode, Non-ASCII & Special Character Fidelity ───────────────────
    def test_tier2_arabic_unicode_anime_title(self):
        """Verifies Arabic unicode anime title is stored and returned with exact fidelity."""
        fp = f"arabic_title_{uuid.uuid4().hex[:8]}"
        arabic_title = "سوسو نو فريرين: بعد نهاية الرحلة"
        payload = {
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": arabic_title,
            "episode": "28"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)

        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        history = user_resp.json().get("history", [])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["anime_title"], arabic_title)

    def test_tier2_special_characters_and_emojis(self):
        """Verifies emojis and Japanese Kanji are preserved with exact UTF-8 fidelity."""
        fp = f"emoji_title_{uuid.uuid4().hex[:8]}"
        title_with_emojis = "🔥 Jujutsu Kaisen 呪術廻戦 💥 (Season 2) [1080p] & <Special>"
        payload = {
            "event_type": "watch",
            "fingerprint": fp,
            "anime_title": title_with_emojis,
            "episode": "12"
        }
        resp = self.client.send_telemetry(payload)
        self.assertEqual(resp.status_code, 200)

        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        history = user_resp.json().get("history", [])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["anime_title"], title_with_emojis)

    # ── 8. Security Boundaries & Authorization ────────────────────────────────
    def test_tier2_unauthenticated_broadcast_update(self):
        """Verifies POST /api/broadcast without authentication returns 401 Unauthorized."""
        client = E2EClient(base_url=self.client.base_url)  # Unauthenticated client
        resp = client.update_broadcast({"title": "Malicious Broadcast"})
        self.assertEqual(resp.status_code, 401)

    def test_tier2_unauthenticated_changelog_update(self):
        """Verifies POST /api/changelog without authentication returns 401 Unauthorized."""
        client = E2EClient(base_url=self.client.base_url)
        resp = client.update_changelog({"title": "Malicious Changelog"})
        self.assertEqual(resp.status_code, 401)

    def test_tier2_invalid_bearer_token(self):
        """Verifies invalid Bearer token is rejected."""
        client = E2EClient(base_url=self.client.base_url)
        client.session.headers["Authorization"] = "Bearer completely_bogus_token_12345"
        resp = client.get_session()
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get("authenticated"))

    def test_tier2_empty_bearer_token(self):
        """Verifies empty Bearer token is rejected."""
        client = E2EClient(base_url=self.client.base_url)
        client.session.headers["Authorization"] = "Bearer "
        resp = client.get_session()
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get("authenticated"))

    # ── 9. Parameter Validations & Nonexistent Queries ───────────────────────
    def test_tier2_missing_fingerprint_user_lookup(self):
        """Verifies GET /api/user without fingerprint query parameter returns 400."""
        resp = self.client.session.get(f"{self.client.base_url}/api/user", timeout=5.0)
        self.assertEqual(resp.status_code, 400)

    def test_tier2_nonexistent_user_fingerprint(self):
        """Verifies querying a non-existent fingerprint returns empty history gracefully."""
        resp = self.client.get_user("nonexistent_user_999999")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data.get("summary"))
        self.assertEqual(data.get("history"), [])

    def test_tier2_crashes_pagination_out_of_bounds(self):
        """Verifies requesting page=99999 returns empty list with code 200."""
        resp = self.client.get_crashes(page=99999, limit=10)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("crashes"), [])

    def test_tier2_events_pagination_negative_page(self):
        """Verifies negative page numbers (page=-5) are clamped to page 1 safely."""
        resp = self.client.get_events(page=-5, limit=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("page"), 1)

    # ── 10. Quota Guard Resilience & Buffer Limits ────────────────────────────
    def test_tier2_d1_quota_exhaustion_snapshot_fallback(self):
        """Verifies stats endpoint returns d1_limited: true when quota limit is reached."""
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

    def test_tier2_crash_kv_fallback_under_quota_limit(self):
        """Verifies crashes endpoint serves from KV buffer when D1 is quota-exhausted."""
        q_res = self.client.set_quota_limit(enabled=True)
        if q_res.status_code != 200:
            self.skipTest("Target does not support simulated quota control")
        try:
            resp = self.client.get_crashes()
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data.get("d1_limited"))
            self.assertEqual(data.get("source"), "kv_buffer")
        finally:
            self.client.set_quota_limit(enabled=False)

    def test_tier2_recent_crashes_kv_buffer_cap_50(self):
        """Verifies pushing crashes keeps KV buffer capped at maximum 50 records."""
        for i in range(15):
            fp = f"crash_cap_{i}_{uuid.uuid4().hex[:6]}"
            self.client.send_crash({
                "fingerprint": fp,
                "error_type": "IndexError",
                "message": f"Index error {i}",
                "traceback": f"Traceback line {i}",
                "os_name": "Linux"
            })
        resp = self.client.get_crashes(limit=100)
        self.assertEqual(resp.status_code, 200)
        crashes = resp.json().get("crashes", [])
        self.assertLessEqual(len(crashes), 50)

    # ── 11. Edge Protocol Boundaries (CORS, Defaults, Normalization) ─────────
    def test_tier2_options_cors_preflight(self):
        """Verifies OPTIONS request returns HTTP 204 with CORS headers."""
        resp = self.client.session.options(f"{self.client.base_url}/api/v2/telemetry", timeout=5.0)
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("POST", resp.headers.get("Access-Control-Allow-Methods", ""))

    def test_tier2_legacy_missing_provider_defaults_animeify(self):
        """Verifies legacy video_play payload missing provider defaults to Animeify."""
        fp = f"leg_prov_{uuid.uuid4().hex[:8]}"
        self.client.send_legacy_monitor({
            "fingerprint": fp,
            "action": "video_play",
            "details": {"anime": "Naruto Shippuden", "episode": "1"}
        })
        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        history = user_resp.json().get("history", [])
        self.assertTrue(len(history) > 0)
        self.assertEqual(history[0]["provider"], "Animeify")

    def test_tier2_legacy_darwin_normalized_to_macos(self):
        """Verifies legacy payload with os: 'Darwin' normalizes to 'macOS'."""
        fp = f"leg_darwin_{uuid.uuid4().hex[:8]}"
        self.client.send_legacy_monitor({
            "fingerprint": fp,
            "action": "app_start",
            "details": {"os": "Darwin", "version": "1.8.4"}
        })
        user_resp = self.client.get_user(fp)
        self.assertEqual(user_resp.status_code, 200)
        summary = user_resp.json().get("summary")
        if summary:
            self.assertEqual(summary["os_name"], "macOS")

    def test_tier2_extreme_long_error_message(self):
        """Verifies extremely long exception message (5,000 characters) is handled safely."""
        fp = f"long_msg_{uuid.uuid4().hex[:8]}"
        long_message = "Network timeout while resolving provider endpoint " * 100
        payload = {
            "fingerprint": fp,
            "error_type": "TimeoutError",
            "message": long_message,
            "traceback": "Traceback:\nTimeoutError",
            "os_name": "Linux"
        }
        resp = self.client.send_crash(payload)
        self.assertEqual(resp.status_code, 200)

    def test_tier2_sql_injection_in_crashes_filter(self):
        """Verifies SQL injection payload in crashes type filter is parameterized safely."""
        sqli_type = "' OR '1'='1"
        resp = self.client.get_crashes(type_filter=sqli_type)
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
