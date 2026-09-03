"""
Monitoring / Telemetry System for ani-cli-arabic.
Privacy-preserving, anonymous system metrics for dashboard analytics.
"""

import platform
import hashlib
import threading
import json
import urllib.request
from datetime import datetime, timezone

from .version import APP_VERSION

ANALYTICS_ENDPOINTS = [
    "https://ani-cli-arabic-analytics.talego4955.workers.dev/monitor",
    "https://analytics.ani-cli-arabic.dev/monitor"
]
CLIENT_AUTH_KEY = "6rK9z0XyW8vQ3J7pL2mN4sB1tH5gD0fA"


class MonitoringSystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MonitoringSystem, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.user_fingerprint = self._generate_fingerprint()

    def _generate_fingerprint(self) -> str:
        try:
            components = [
                platform.node(),
                platform.machine(),
                platform.system(),
                platform.release(),
                platform.processor()
            ]
            raw_str = "|".join(str(c) for c in components)
            return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]
        except Exception:
            return "unknown_user"

    def _send_data(self, action: str, details: dict):
        """Asynchronously dispatches event telemetry to the analytics worker."""
        try:
            from .settings import SettingsManager
            settings = SettingsManager()
            if not settings.get('analytics', True):
                return
        except Exception:
            pass

        def _worker():
            payload = json.dumps({
                "fingerprint": self.user_fingerprint,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "details": details
            }).encode("utf-8")

            headers = {
                "Content-Type": "application/json",
                "X-Auth-Key": CLIENT_AUTH_KEY,
                "User-Agent": f"AniCliAr-Monitor/1.0 ani-cli-arabic/{APP_VERSION}"
            }

            for endpoint in ANALYTICS_ENDPOINTS:
                try:
                    req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=2.0) as resp:
                        if resp.status == 200:
                            return
                except Exception:
                    continue

        threading.Thread(target=_worker, daemon=True).start()

    def track_app_start(self):
        self._send_data("app_start", {
            "version": APP_VERSION,
            "os": platform.system()
        })

    def track_video_play(self, anime_title: str, episode: str, mode: str = "stream", provider: str = ""):
        self._send_data("video_play", {
            "anime": anime_title,
            "episode": str(episode),
            "mode": mode,
            "provider": provider or "Unknown"
        })


monitor = MonitoringSystem()

