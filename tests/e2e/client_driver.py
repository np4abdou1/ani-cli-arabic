"""
End-to-End Test Client Driver for interacting with Edge Worker endpoints.
Supports both the hermetic local emulator and live Cloudflare deployments.
"""

import os
import requests

CLIENT_AUTH_KEY = "6rK9z0XyW8vQ3J7pL2mN4sB1tH5gD0fA"
DEFAULT_TEST_ADMIN_PASSWORD = "anicli_admin_pass_2026"


class E2EClient:
    """Driver client executing HTTP requests against Edge Worker API targets."""

    def __init__(self, base_url=None, auth_key=CLIENT_AUTH_KEY):
        self.base_url = (base_url or os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8787")).rstrip("/")
        self.auth_key = auth_key
        self.session = requests.Session()
        self.token = None

    def _url(self, path):
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def send_telemetry(self, payload, headers=None, expected_status=None):
        req_headers = {
            "Content-Type": "application/json",
            "X-Auth-Key": self.auth_key,
            "User-Agent": "AniCliAr-Monitor/2.0 ani-cli-arabic/2.0.0"
        }
        if headers:
            req_headers.update(headers)
        resp = self.session.post(self._url("/api/v2/telemetry"), json=payload, headers=req_headers, timeout=5.0)
        if expected_status is not None:
            assert resp.status_code == expected_status, f"Expected {expected_status}, got {resp.status_code}: {resp.text}"
        return resp

    def send_crash(self, payload, headers=None, expected_status=None):
        req_headers = {
            "Content-Type": "application/json",
            "X-Auth-Key": self.auth_key,
            "User-Agent": "AniCliAr-CrashReporter/2.0 ani-cli-arabic/2.0.0"
        }
        if headers:
            req_headers.update(headers)
        resp = self.session.post(self._url("/api/v2/crash"), json=payload, headers=req_headers, timeout=5.0)
        if expected_status is not None:
            assert resp.status_code == expected_status, f"Expected {expected_status}, got {resp.status_code}: {resp.text}"
        return resp

    def send_legacy_monitor(self, payload, headers=None, expected_status=None):
        req_headers = {
            "Content-Type": "application/json",
            "X-Auth-Key": self.auth_key,
            "User-Agent": "AniCliAr-Monitor/1.0 ani-cli-arabic/1.8.4"
        }
        if headers:
            req_headers.update(headers)
        resp = self.session.post(self._url("/monitor"), json=payload, headers=req_headers, timeout=5.0)
        if expected_status is not None:
            assert resp.status_code == expected_status, f"Expected {expected_status}, got {resp.status_code}: {resp.text}"
        return resp

    def send_legacy_watch(self, payload, headers=None, expected_status=None):
        req_headers = {
            "Content-Type": "application/json",
            "User-Agent": "ani-cli-arabic/1.8.4"
        }
        if headers:
            req_headers.update(headers)
        resp = self.session.post(self._url("/watch"), json=payload, headers=req_headers, timeout=5.0)
        if expected_status is not None:
            assert resp.status_code == expected_status, f"Expected {expected_status}, got {resp.status_code}: {resp.text}"
        return resp

    def get_broadcast(self, user_agent="AniCliAr-Monitor/2.0 ani-cli-arabic/2.0.0", path="/broadcast.json"):
        headers = {}
        if user_agent is not None:
            headers["User-Agent"] = user_agent
        return self.session.get(self._url(path), headers=headers, timeout=5.0)

    def get_changelog(self, user_agent="AniCliAr-Monitor/2.0 ani-cli-arabic/2.0.0", path="/changelog.json"):
        headers = {}
        if user_agent is not None:
            headers["User-Agent"] = user_agent
        return self.session.get(self._url(path), headers=headers, timeout=5.0)

    def get_health(self, path="/health"):
        return self.session.get(self._url(path), timeout=5.0)

    def login(self, password=DEFAULT_TEST_ADMIN_PASSWORD):
        resp = self.session.post(self._url("/api/auth/login"), json={"password": password}, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("token")
            if self.token:
                self.session.headers["Authorization"] = f"Bearer {self.token}"
        return resp

    def logout(self):
        resp = self.session.post(self._url("/api/auth/logout"), timeout=5.0)
        self.token = None
        self.session.headers.pop("Authorization", None)
        return resp

    def get_session(self):
        return self.session.get(self._url("/api/auth/session"), timeout=5.0)

    def get_stats(self, range_val="all", launches_period="all"):
        params = {"range": range_val, "launchesPeriod": launches_period}
        return self.session.get(self._url("/api/stats"), params=params, timeout=5.0)

    def get_users(self, page=1, limit=50, search="", distro="", os=""):
        params = {"page": page, "limit": limit}
        if search:
            params["search"] = search
        if distro:
            params["distro"] = distro
        if os:
            params["os"] = os
        return self.session.get(self._url("/api/users"), params=params, timeout=5.0)

    def get_user(self, fingerprint):
        return self.session.get(self._url(f"/api/user?fingerprint={fingerprint}"), timeout=5.0)

    def get_crashes(self, page=1, limit=50, type_filter="", search=""):
        params = {"page": page, "limit": limit}
        if type_filter:
            params["type"] = type_filter
        if search:
            params["search"] = search
        return self.session.get(self._url("/api/crashes"), params=params, timeout=5.0)

    def get_events(self, page=1, limit=50, action="", search=""):
        params = {"page": page, "limit": limit}
        if action:
            params["action"] = action
        if search:
            params["search"] = search
        return self.session.get(self._url("/api/events"), params=params, timeout=5.0)

    def get_legacy(self, page=1, limit=100, action="", search=""):
        params = {"page": page, "limit": limit}
        if action:
            params["action"] = action
        if search:
            params["search"] = search
        return self.session.get(self._url("/api/legacy"), params=params, timeout=5.0)

    def update_broadcast(self, broadcast_data):
        return self.session.post(self._url("/api/broadcast"), json=broadcast_data, timeout=5.0)

    def update_changelog(self, changelog_data):
        return self.session.post(self._url("/api/changelog"), json=changelog_data, timeout=5.0)

    def set_quota_limit(self, enabled=True):
        return self.session.get(self._url(f"/test/set_quota_limit?enabled={'1' if enabled else '0'}"), timeout=5.0)

    def reset_server_state(self):
        return self.session.get(self._url("/test/reset"), timeout=5.0)
