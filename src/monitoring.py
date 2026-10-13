"""
Monitoring / Telemetry System for ani-cli-arabic.
Privacy-preserving, anonymous system metrics for dashboard analytics.
"""

import os
import platform
import hashlib
import threading
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from .version import APP_VERSION

ANALYTICS_ENDPOINTS = [
    "https://anicliar-dashboard.pages.dev/api/v2/telemetry",
    "https://ani-cli-arabic-analytics.talego4955.workers.dev/api/v2/telemetry",
    "https://analytics.ani-cli-arabic.dev/api/v2/telemetry"
]
CLIENT_AUTH_KEY = "6rK9z0XyW8vQ3J7pL2mN4sB1tH5gD0fA"


def get_base_dir() -> Path:
    """Retrieve or initialize the base configuration directory."""
    try:
        base = Path.home() / ".ani-cli-arabic"
    except Exception:
        import tempfile
        base = Path(tempfile.gettempdir()) / ".ani-cli-arabic"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_os_info() -> Dict[str, str]:
    """
    Deep OS detection returning structured environment dictionary:
    {
        "os_name": str,     # Linux, macOS, Windows, Android
        "distro": str,      # Arch Linux, Ubuntu, Windows 11, macOS, Termux, etc.
        "base": str,        # Arch, Debian, RedHat, SUSE, Darwin, Windows NT, Independent
        "os_version": str   # kernel / build version (e.g. 7.1.9-arch1-2, 10.0.22631)
    }
    """
    try:
        # 1. Android (Termux)
        if "ANDROID_ROOT" in os.environ or "com.termux" in os.environ.get("PREFIX", ""):
            return {
                "os_name": "Android",
                "distro": "Termux",
                "base": "Linux",
                "os_version": platform.release() or "unknown"
            }

        sys_name = platform.system()

        # 2. macOS
        if sys_name == "Darwin":
            mac_ver = platform.mac_ver()[0]
            return {
                "os_name": "macOS",
                "distro": "macOS",
                "base": "Darwin",
                "os_version": mac_ver or platform.release() or "unknown"
            }

        # 3. Windows
        if sys_name == "Windows":
            rel = platform.release()
            distro_name = f"Windows {rel}" if rel else "Windows"
            return {
                "os_name": "Windows",
                "distro": distro_name,
                "base": "Windows NT",
                "os_version": platform.version() or rel or "unknown"
            }

        # 4. Linux
        if sys_name == "Linux":
            os_data: Dict[str, str] = {}
            if hasattr(platform, "freedesktop_os_release"):
                try:
                    os_data = platform.freedesktop_os_release()
                except Exception:
                    os_data = {}

            if not os_data:
                for release_path in ("/etc/os-release", "/usr/lib/os-release"):
                    if os.path.exists(release_path):
                        try:
                            with open(release_path, "r", encoding="utf-8", errors="ignore") as f:
                                for line in f:
                                    line = line.strip()
                                    if "=" in line and not line.startswith("#"):
                                        k, v = line.split("=", 1)
                                        os_data[k.strip()] = v.strip().strip("\"'")
                            if os_data:
                                break
                        except Exception:
                            pass

            raw_name = os_data.get("NAME") or os_data.get("PRETTY_NAME") or os_data.get("ID") or "Linux"
            clean = (
                raw_name.replace(" GNU/Linux", "")
                .replace(" Linux", "")
                .replace("linux", "")
                .strip()
            )
            clean_lower = clean.lower()

            if "arch" in clean_lower:
                distro = "Arch Linux"
            elif "ubuntu" in clean_lower:
                distro = "Ubuntu"
            elif "debian" in clean_lower:
                distro = "Debian"
            elif "kali" in clean_lower:
                distro = "Kali"
            elif "fedora" in clean_lower:
                distro = "Fedora"
            elif "manjaro" in clean_lower:
                distro = "Manjaro"
            elif "mint" in clean_lower:
                distro = "Linux Mint"
            elif "nixos" in clean_lower:
                distro = "NixOS"
            elif "void" in clean_lower:
                distro = "Void"
            elif "alpine" in clean_lower:
                distro = "Alpine"
            elif "gentoo" in clean_lower:
                distro = "Gentoo"
            elif "pop" in clean_lower:
                distro = "Pop!_OS"
            elif "opensuse" in clean_lower or "suse" in clean_lower:
                distro = "openSUSE"
            elif "rocky" in clean_lower:
                distro = "Rocky Linux"
            elif "alma" in clean_lower:
                distro = "AlmaLinux"
            elif "centos" in clean_lower:
                distro = "CentOS"
            elif "rhel" in clean_lower or "red hat" in clean_lower:
                distro = "RHEL"
            elif raw_name and raw_name != "Linux":
                distro = raw_name.strip()
            else:
                distro = "Linux"

            # Derive upstream base family
            id_val = (os_data.get("ID") or "").lower().strip()
            id_like = (os_data.get("ID_LIKE") or "").lower().strip()
            like_tokens = id_like.split()

            if "arch" in like_tokens or id_val in ("arch", "manjaro", "endeavouros", "arcolinux", "garuda", "artix", "parabola"):
                base = "Arch"
            elif "debian" in like_tokens or "ubuntu" in like_tokens or id_val in ("debian", "ubuntu", "kali", "mint", "linuxmint", "pop", "elementary", "zorin", "raspbian", "devuan"):
                base = "Debian"
            elif "rhel" in like_tokens or "fedora" in like_tokens or "centos" in like_tokens or id_val in ("rhel", "fedora", "centos", "rocky", "almalinux", "ol", "amzn"):
                base = "RedHat"
            elif "suse" in like_tokens or "opensuse" in like_tokens or id_val in ("suse", "opensuse", "opensuse-tumbleweed", "opensuse-leap", "sles"):
                base = "SUSE"
            elif id_val in ("alpine", "void", "gentoo", "nixos", "solus", "slackware", "mageia", "clear-linux-os"):
                base = "Independent"
            elif "arch" in clean_lower:
                base = "Arch"
            elif "debian" in clean_lower or "ubuntu" in clean_lower:
                base = "Debian"
            elif "fedora" in clean_lower or "redhat" in clean_lower:
                base = "RedHat"
            elif "suse" in clean_lower:
                base = "SUSE"
            else:
                base = "Independent"

            return {
                "os_name": "Linux",
                "distro": distro,
                "base": base,
                "os_version": platform.release() or "unknown"
            }

        fallback_sys = sys_name or "Unknown"
        return {
            "os_name": fallback_sys,
            "distro": fallback_sys,
            "base": fallback_sys,
            "os_version": platform.release() or "unknown"
        }
    except Exception:
        fallback_sys = platform.system() or "Unknown"
        return {
            "os_name": fallback_sys,
            "distro": fallback_sys,
            "base": fallback_sys,
            "os_version": platform.release() or "unknown"
        }


def get_detailed_os() -> str:
    """Legacy helper returning formatted string (e.g. 'Linux (Arch Linux)', 'Windows 11', 'macOS')."""
    info = get_os_info()
    if info["os_name"] == "Linux":
        return f"Linux ({info['distro']})"
    elif info["os_name"] == "Android":
        return "Android (Termux)"
    elif info["os_name"] == "Windows":
        return info["distro"]
    elif info["os_name"] == "macOS":
        return "macOS"
    return info["os_name"]


def get_hardware_fingerprint() -> str:
    """
    Deterministic hardware fingerprinting:
    Stable, anonymous 16-hex hash of machine identifiers:
    (/etc/machine-id or DBus machine-id, CPU architecture, OS system, hardware MAC node;
    fallback to persistent ~/.ani-cli-arabic/fingerprint).
    """
    try:
        machine_id = ""
        for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        machine_id = f.read().strip()
                        if machine_id:
                            break
                except Exception:
                    pass

        import uuid
        mac_node = str(uuid.getnode())
        cpu_arch = platform.machine()
        os_sys = platform.system()

        if machine_id:
            raw = f"{machine_id}:{cpu_arch}:{os_sys}:{mac_node}"
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

        # In containerized/chroot/non-Linux environments lacking /etc/machine-id
        cache_file = get_base_dir() / "fingerprint"
        if cache_file.exists():
            try:
                cached = cache_file.read_text(encoding="utf-8").strip()
                if cached and len(cached) >= 16:
                    return cached[:16]
            except Exception:
                pass

        raw = f"{machine_id}:{cpu_arch}:{os_sys}:{mac_node}"
        fp = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        try:
            cache_file.write_text(fp, encoding="utf-8")
        except Exception:
            pass
        return fp
    except Exception:
        try:
            cache_file = get_base_dir() / "fingerprint"
            if cache_file.exists():
                return cache_file.read_text(encoding="utf-8").strip()[:16]
            import uuid
            generated = uuid.uuid4().hex[:16]
            cache_file.write_text(generated, encoding="utf-8")
            return generated
        except Exception:
            return "unknown_user"


class MonitoringSystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MonitoringSystem, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.user_fingerprint = self._generate_fingerprint()

    def _generate_fingerprint(self) -> str:
        return get_hardware_fingerprint()

    def _send_payload(self, payload: dict):
        """Asynchronously dispatches event telemetry to the analytics endpoints."""
        try:
            from .settings import SettingsManager
            if not SettingsManager().get("analytics", True):
                return
        except Exception:
            pass

        def _worker():
            try:
                data = json.dumps(payload).encode("utf-8")
                headers = {
                    "Content-Type": "application/json",
                    "X-Auth-Key": CLIENT_AUTH_KEY,
                    "User-Agent": f"AniCliAr-Monitor/2.0 ani-cli-arabic/{APP_VERSION}"
                }
                for endpoint in ANALYTICS_ENDPOINTS:
                    try:
                        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
                        with urllib.request.urlopen(req, timeout=2.0) as resp:
                            if resp.status in (200, 201, 202, 204):
                                return
                    except Exception:
                        continue
            except Exception:
                pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _send_data(self, action: str, details: dict):
        """Backward compatibility handler for legacy _send_data calls."""
        if action == "app_start":
            self.track_app_start()
        elif action == "video_play":
            self.track_video_play(
                anime_title=details.get("anime", details.get("anime_title", "Unknown")),
                episode=str(details.get("episode", "1")),
                mode=details.get("mode", "stream"),
                provider=details.get("provider", "anime3rb"),
                duration=int(details.get("duration", 0))
            )
        else:
            payload = {
                "event_type": action,
                "fingerprint": self.user_fingerprint,
                "details": details,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self._send_payload(payload)

    def track_app_start(self):
        """Sends 'launch' event to /api/v2/telemetry."""
        os_info = get_os_info()
        payload = {
            "event_type": "launch",
            "fingerprint": self.user_fingerprint,
            "os_name": os_info["os_name"],
            "distro": os_info["distro"],
            "base": os_info["base"],
            "os_version": os_info["os_version"],
            "python_version": platform.python_version(),
            "client_version": APP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._send_payload(payload)

    def track_video_play(
        self,
        anime_title: str,
        episode: Any,
        mode: str = "stream",
        provider: str = "",
        duration: int = 0
    ):
        """Sends 'watch' event to /api/v2/telemetry."""
        os_info = get_os_info()
        payload = {
            "event_type": "watch",
            "fingerprint": self.user_fingerprint,
            "anime_title": str(anime_title or "Unknown"),
            "episode": str(episode if episode is not None else "1"),
            "provider": str(provider or "anime3rb"),
            "mode": str(mode or "stream"),
            "duration": int(duration) if duration else 0,
            "os_name": os_info["os_name"],
            "distro": os_info["distro"],
            "base": os_info["base"],
            "os_version": os_info["os_version"],
            "client_version": APP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._send_payload(payload)


monitor = MonitoringSystem()
