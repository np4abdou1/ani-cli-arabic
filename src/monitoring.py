"""
Monitoring / Telemetry stub (Privacy-preserving, zero external tracking)
"""

class MonitoringSystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MonitoringSystem, cls).__new__(cls)
        return cls._instance

    def track_app_start(self):
        pass

    def track_video_play(self, anime_title: str, episode: str, mode: str = "stream"):
        pass

monitor = MonitoringSystem()
