import platform
import hashlib
import threading
import requests
from datetime import datetime
from .api import _get_endpoint_config
from .config import CURRENT_VERSION

class MonitoringSystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MonitoringSystem, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
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
            return hashlib.sha256(raw_str.encode()).hexdigest()[:16]
        except Exception:
            return "unknown_user"

    def _send_data(self, action: str, details: dict):
        """Send analytics data only if user has opted in."""
        try:
            from .settings import SettingsManager
            settings = SettingsManager()
            if not settings.get('analytics'):
                return
        except Exception:
            return
        
        def worker():
            try:
                endpoint_url, auth_secret = _get_endpoint_config()
                
                payload = {
                    "fingerprint": self.user_fingerprint,
                    "timestamp": datetime.now().isoformat(),
                    "action": action,
                    "details": details
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'X-Auth-Key': auth_secret,
                    'User-Agent': 'AniCliAr-Monitor/1.0'
                }
                
                requests.post(
                    f"{endpoint_url}/monitor", 
                    json=payload, 
                    headers=headers, 
                    timeout=3
                )
            except (requests.RequestException, ValueError, KeyError):
                pass

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def track_app_start(self):
        self._send_data("app_start", {
            "version": CURRENT_VERSION,
            "os": platform.system()
        })

    def track_video_play(self, anime_title: str, episode: str, mode: str = "stream"):
        self._send_data("video_play", {
            "anime": anime_title,
            "episode": episode,
            "mode": mode
        })

# Global instance
monitor = MonitoringSystem()
