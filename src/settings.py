import json
import os
from pathlib import Path

class SettingsManager:
    def __init__(self):
        self.config_file = self._get_config_path()
        self.settings = self._load_settings()

    def _get_config_path(self) -> Path:
        home_dir = Path.home()
        db_dir = home_dir / ".ani-cli-arabic" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "config.json"

    def _load_settings(self) -> dict:
        defaults = {
            "default_quality": "1080p",  # 1080p, 720p, 480p
            "player": "mpv",             # mpv, vlc
            "auto_next": False,          # Auto-play next episode
            "check_updates": True,
            "theme": "blue"              # Theme color
        }
        
        if not self.config_file.exists():
            return defaults
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**defaults, **saved}
        except Exception:
            return defaults

    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception:
            pass

    def get(self, key):
        return self.settings.get(key)

    def set(self, key, value):
        self.settings[key] = value
        self.save()
