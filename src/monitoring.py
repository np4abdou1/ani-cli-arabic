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
    "https://anicliar-dashboard.pages.dev/monitor",
    "https://analytics.ani-cli-arabic.dev/monitor"
]
CLIENT_AUTH_KEY = "6rK9z0XyW8vQ3J7pL2mN4sB1tH5gD0fA"


import os


def get_detailed_os() -> str:
    """Detect detailed operating system with Linux distribution identification."""
    try:
        sys_name = platform.system()
        if sys_name == "Windows":
            rel = platform.release()
            return f"Windows {rel}" if rel else "Windows"
        elif sys_name == "Darwin":
            return "macOS"
        elif "ANDROID_ROOT" in os.environ or "com.termux" in os.environ.get("PREFIX", ""):
            return "Android (Termux)"
        elif sys_name == "Linux":
            distro = None
            try:
                os_info = platform.freedesktop_os_release()
                distro = os_info.get("NAME") or os_info.get("ID")
            except Exception:
                pass

            if not distro and os.path.exists("/etc/os-release"):
                try:
                    with open("/etc/os-release", "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("NAME="):
                                distro = line.split("=", 1)[1].strip("\"'")
                                break
                            elif line.startswith("ID="):
                                distro = line.split("=", 1)[1].strip("\"'").capitalize()
                except Exception:
                    pass

            if distro:
                clean = (
                    distro.replace(" GNU/Linux", "")
                    .replace(" Linux", "")
                    .replace("linux", "")
                    .strip()
                )
                distro_lower = clean.lower()
                if "arch" in distro_lower:
                    clean = "Arch"
                elif "ubuntu" in distro_lower:
                    clean = "Ubuntu"
                elif "debian" in distro_lower:
                    clean = "Debian"
                elif "kali" in distro_lower:
                    clean = "Kali"
                elif "fedora" in distro_lower:
                    clean = "Fedora"
                elif "manjaro" in distro_lower:
                    clean = "Manjaro"
                elif "mint" in distro_lower:
                    clean = "Mint"
                elif "nixos" in distro_lower:
                    clean = "NixOS"
                elif "void" in distro_lower:
                    clean = "Void"
                elif "alpine" in distro_lower:
                    clean = "Alpine"
                elif "gentoo" in distro_lower:
                    clean = "Gentoo"
                elif "pop" in distro_lower:
                    clean = "Pop!_OS"
                elif "opensuse" in distro_lower or "suse" in distro_lower:
                    clean = "openSUSE"

                return f"Linux ({clean})"
            return "Linux"
        return sys_name or "Unknown"
    except Exception:
        return platform.system() or "Unknown"


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
            "os": get_detailed_os()
        })

    def track_video_play(self, anime_title: str, episode: str, mode: str = "stream", provider: str = ""):
        self._send_data("video_play", {
            "anime": anime_title,
            "episode": str(episode),
            "mode": mode,
            "provider": provider or "Unknown",
            "os": get_detailed_os(),
            "version": APP_VERSION
        })


monitor = MonitoringSystem()


