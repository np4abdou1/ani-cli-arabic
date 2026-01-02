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
        if self._initialized:
            return
        self.user_fingerprint = self._generate_fingerprint()
        self._initialized = True

    def _generate_fingerprint(self) -> str:
        # Generates a basic anonymous fingerprint based on system properties.
        # Does NOT use hardware UUIDs to respect privacy while maintaining uniqueness.
        try:
            # Combine basic system info
            components = [
                platform.node(),      # Hostname
                platform.machine(),   # Machine type (e.g. AMD64)
                platform.system(),    # OS Name
                platform.release(),   # OS Version
                platform.processor()  # Processor info
            ]
            
            # Create a hash
            raw_str = "|".join(str(c) for c in components)
            # Use SHA256 and take first 16 chars for a concise ID
            return hashlib.sha256(raw_str.encode()).hexdigest()[:16]
        except Exception:
            return "unknown_user"

    def _send_data(self, action: str, details: dict):
        # Sends data to the remote endpoint asynchronously.
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
            except Exception:
                pass # Fail silently to not disrupt user experience

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def track_app_start(self):
        # Tracks when the application is started.
        self._send_data("app_start", {
            "version": CURRENT_VERSION,
            "os": platform.system()
        })

    def track_video_play(self, anime_title: str, episode: str, mode: str = "stream"):
        # Tracks when a video is played.
        self._send_data("video_play", {
            "anime": anime_title,
            "episode": episode,
            "mode": mode
        })

# Global instance
monitor = MonitoringSystem()


#users_count is shown on github page of the repository.
