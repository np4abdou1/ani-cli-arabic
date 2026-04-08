import json
from pathlib import Path
from .storage import atomic_write_json

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
            "default_quality": "1080p",
            "default_download_quality": "1080p",
            "download_mode": "internal",
            "download_directory": "downloads",
            "player": "mpv",
            "auto_next": False,
            "discord_rpc": True,
            "theme": "blue",
            "analytics": True  # Allow users to opt-out of analytics
        }
        
        if not self.config_file.exists():
            return defaults
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                if not isinstance(saved, dict):
                    return defaults
                return {**defaults, **saved}
        except (json.JSONDecodeError, IOError, OSError):
            return defaults

    def save(self):
        try:
            atomic_write_json(self.config_file, self.settings, indent=4, ensure_ascii=False)
        except (IOError, OSError, ValueError, TypeError) as e:
            import sys
            print(f"Warning: Failed to save settings: {e}", file=sys.stderr)

    def get(self, key):
        return self.settings.get(key)

    def set(self, key, value):
        self.settings[key] = value
        self.save()
