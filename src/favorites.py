import json
from pathlib import Path
from datetime import datetime

class FavoritesManager:
    # Maximum favorites to prevent database bloat and ensure performance
    MAX_FAVORITES = 100
    
    def __init__(self):
        self.file_path = self._get_path()
        self.favorites = self._load()

    def _get_path(self) -> Path:
        home_dir = Path.home()
        db_dir = home_dir / ".ani-cli-arabic" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "favorites.json"

    def _load(self) -> dict:
        if not self.file_path.exists():
            return {}
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except (json.JSONDecodeError, IOError, OSError):
            return {}

    def save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=4, ensure_ascii=False)
        except (IOError, OSError) as e:
            import sys
            print(f"Warning: Failed to save favorites: {e}", file=sys.stderr)

    def add(self, anime_id, title, thumbnail):
        anime_id_str = str(anime_id)
        if anime_id_str in self.favorites:
            # Update existing favorite
            self.favorites[anime_id_str]['added_at'] = datetime.now().isoformat()
            self.save()
            return
        
        if len(self.favorites) >= self.MAX_FAVORITES:
            oldest = min(self.favorites.items(), key=lambda x: x[1]['added_at'])
            del self.favorites[oldest[0]]
        
        self.favorites[str(anime_id)] = {
            'title': title,
            'thumbnail': thumbnail,
            'added_at': datetime.now().isoformat()
        }
        self.save()

    def remove(self, anime_id):
        if str(anime_id) in self.favorites:
            del self.favorites[str(anime_id)]
            self.save()

    def is_favorite(self, anime_id):
        return str(anime_id) in self.favorites

    def get_all(self):
        # Return list sorted by added date (newest first)
        return sorted(
            [{'id': k, **v} for k, v in self.favorites.items()],
            key=lambda x: x['added_at'],
            reverse=True
        )
