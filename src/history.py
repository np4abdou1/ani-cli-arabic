import json
import os
from pathlib import Path
from datetime import datetime

class HistoryManager:
    def __init__(self):
        self.history_file = self._get_history_path()
        self.history = self._load_history()

    def _get_history_path(self) -> Path:
        # Save in user home directory
        home_dir = Path.home()
        db_dir = home_dir / ".ani-cli-arabic" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "history.json"

    def _load_history(self) -> dict:
        if not self.history_file.exists():
            return {}
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def mark_watched(self, anime_id, episode_num, anime_title):
        """Saves the last watched episode for a specific anime."""
        self.history[str(anime_id)] = {
            'episode': str(episode_num),
            'title': anime_title,
            'last_updated': datetime.now().isoformat()
        }
        self.save_history()

    def get_last_watched(self, anime_id):
        """Returns the episode number of the last watched episode."""
        data = self.history.get(str(anime_id))
        if data:
            return data.get('episode')
        return None
    
    def get_history(self):
        """Returns all history as a list sorted by last_updated."""
        items = []
        for anime_id, data in self.history.items():
            items.append({
                'anime_id': anime_id,
                'title': data.get('title', 'Unknown'),
                'episode': data.get('episode', '?'),
                'last_updated': data.get('last_updated', '')
            })
        # Sort by last_updated, most recent first
        items.sort(key=lambda x: x['last_updated'], reverse=True)
        return items