import json
import os
from pathlib import Path

class SettingsManager:
    def __init__(self):
        self.config_file = self._get_config_path()
        self.settings = self._load_settings()

    def _get_config_path(self) -> Path:
        base_dir = Path(__file__).parent.parent
        db_dir = base_dir / "database"
        db_dir.mkdir(exist_ok=True)
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
        
        # If theme changed, update themes.py
        if key == "theme":
            self._update_theme_file(value)
    
    def _update_theme_file(self, theme_name):
        """Update CURRENT_THEME in themes.py file"""
        try:
            base_dir = Path(__file__).parent.parent
            themes_file = base_dir / "themes.py"
            
            if themes_file.exists():
                with open(themes_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace CURRENT_THEME line
                import re
                new_content = re.sub(
                    r'CURRENT_THEME = "[^"]*"',
                    f'CURRENT_THEME = "{theme_name}"',
                    content
                )
                
                with open(themes_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                # Force reload of config module
                import importlib
                from . import config
                importlib.reload(config)
        except Exception as e:
            pass
