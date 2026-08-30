"""
Remote broadcast and banner messaging system for ani-cli-arabic.
Enables server-driven global announcements, domain switch alerts, and emergency updates
via Cloudflare Worker / JSON endpoint without requiring user client updates.
"""

import os
import json
import time
import urllib.request
import threading
from pathlib import Path
from typing import Optional, Dict, Any

from .version import __version__, parse_version
from .logger import logger

# Remote Broadcast JSON Endpoints (Primary: Deployed Cloudflare Worker, Secondary: Custom Domain, Fallback: Raw GitHub)
BROADCAST_URLS = [
    "https://ani-cli-broadcast.talego4955.workers.dev/broadcast.json",
    "https://broadcast.ani-cli-arabic.dev/broadcast.json",
    "https://raw.githubusercontent.com/np4abdou1/ani-cli-arabic/main/broadcast.json"
]

_CACHE_FILE = Path.home() / ".ani-cli-arabic" / "database" / "broadcast_cache.json"
_DISMISSED_FILE = Path.home() / ".ani-cli-arabic" / "database" / "dismissed_broadcasts.json"


class BroadcastManager:
    _cached_broadcast: Optional[Dict[str, Any]] = None
    _last_fetch_time: float = 0.0

    @classmethod
    def load_cached(cls) -> Optional[Dict[str, Any]]:
        """Loads cached broadcast from disk."""
        try:
            if _CACHE_FILE.exists():
                with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cls._cached_broadcast = data.get("broadcast")
                    cls._last_fetch_time = float(data.get("fetched_at", 0))
                    return cls._cached_broadcast
        except Exception:
            pass
        return None

    @classmethod
    def fetch_remote(cls, force: bool = False) -> Optional[Dict[str, Any]]:
        """Fetches remote broadcast message in the background."""
        now = time.time()
        if not force and cls._cached_broadcast and (now - cls._last_fetch_time < 30):  # 30s cache
            return cls._cached_broadcast

        def _fetch_worker():
            for url in BROADCAST_URLS:
                try:
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": f"ani-cli-arabic/{__version__}"}
                    )
                    with urllib.request.urlopen(req, timeout=3) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode("utf-8"))
                            if isinstance(data, dict):
                                cls._cached_broadcast = data
                                cls._last_fetch_time = time.time()
                                try:
                                    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                                    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
                                        json.dump({
                                            "broadcast": data,
                                            "fetched_at": cls._last_fetch_time
                                        }, f, indent=4)
                                except Exception:
                                    pass
                                return
                except Exception:
                    continue

        threading.Thread(target=_fetch_worker, daemon=True).start()
        return cls._cached_broadcast or cls.load_cached()

    @classmethod
    def get_active_banner(cls) -> Optional[Dict[str, Any]]:
        """
        Returns active banner if it matches current client version
        and is enabled.
        """
        b = cls._cached_broadcast or cls.load_cached()
        if not b:
            return None

        is_active = b.get("active")
        if isinstance(is_active, str):
            is_active = is_active.lower() in ("true", "1", "yes")

        msg = str(b.get("message") or "").strip()
        if not is_active or not msg:
            return None

        # Check version constraints
        min_ver = b.get("min_version")
        max_ver = b.get("max_version")
        from .version import parse_version
        cur = parse_version(__version__)

        if min_ver and cur < parse_version(min_ver):
            return None
        if max_ver and cur > parse_version(max_ver):
            return None

        b_id = b.get("id", "")
        if b_id and cls.is_dismissed(b_id):
            return None

        return b

    @classmethod
    def is_dismissed(cls, broadcast_id: str) -> bool:
        """Checks if a broadcast ID has been dismissed by user."""
        try:
            if _DISMISSED_FILE.exists():
                with open(_DISMISSED_FILE, "r", encoding="utf-8") as f:
                    dismissed = json.load(f)
                    return broadcast_id in dismissed
        except Exception:
            pass
        return False

    @classmethod
    def dismiss(cls, broadcast_id: str) -> None:
        """Marks a broadcast as dismissed."""
        try:
            dismissed = []
            if _DISMISSED_FILE.exists():
                with open(_DISMISSED_FILE, "r", encoding="utf-8") as f:
                    dismissed = json.load(f)
            if broadcast_id not in dismissed:
                dismissed.append(broadcast_id)
            _DISMISSED_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_DISMISSED_FILE, "w", encoding="utf-8") as f:
                json.dump(dismissed, f, indent=4)
        except Exception:
            pass
