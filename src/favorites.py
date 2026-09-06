import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from .storage import atomic_write_json


class FavoritesManager:
    MAX_FAVORITES = 100

    def __init__(self):
        self.file_path = self._get_path()
        self.favorites = self._load()

    def _get_path(self) -> Path:
        home_dir = Path.home()
        db_dir = home_dir / ".ani-cli-arabic" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "favorites.json"

    def _get_legacy_paths(self) -> List[Path]:
        """Find legacy favorites database paths used by versions 1.8.2, 1.8.4, and older."""
        home = Path.home()
        paths = [
            home / ".ani-cli-arabic" / "favorites.json",
            home / ".config" / "ani-cli-arabic" / "favorites.json",
            home / ".local" / "share" / "ani-cli-arabic" / "favorites.json",
            Path(__file__).resolve().parent.parent / "database" / "favorites.json"
        ]
        return [p for p in paths if p.exists() and p != self.file_path]

    def _load(self) -> Dict[str, Dict[str, Any]]:
        raw_data = None
        migrated = False

        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
            except Exception:
                raw_data = None

        if not raw_data:
            for leg_path in self._get_legacy_paths():
                try:
                    with open(leg_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data:
                            raw_data = data
                            migrated = True
                            break
                except Exception:
                    continue

        if not raw_data:
            return {}

        normalized: Dict[str, Dict[str, Any]] = {}
        if isinstance(raw_data, list):
            migrated = True
            for item in raw_data:
                if isinstance(item, dict):
                    aid = str(item.get('anime_id') or item.get('id') or '')
                    if aid:
                        normalized[aid] = self._normalize_entry(item)
        elif isinstance(raw_data, dict):
            for k, v in raw_data.items():
                if isinstance(v, dict):
                    normalized[str(k)] = self._normalize_entry(v)
                elif isinstance(v, str):
                    migrated = True
                    normalized[str(k)] = self._normalize_entry({'title': v})

        if migrated and normalized:
            try:
                atomic_write_json(self.file_path, normalized, indent=4, ensure_ascii=False)
            except Exception:
                pass

        return normalized

    def _normalize_entry(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': str(raw.get('title') or 'Unknown'),
            'thumbnail': str(raw.get('thumbnail') or ''),
            'added_at': str(raw.get('added_at') or datetime.now().isoformat())
        }

    def save(self):
        try:
            atomic_write_json(self.file_path, self.favorites, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save favorites: {e}", file=sys.stderr)

    def add(self, anime_id, title, thumbnail):
        anime_id_str = str(anime_id)
        now_iso = datetime.now().isoformat()
        if anime_id_str in self.favorites:
            self.favorites[anime_id_str]['added_at'] = now_iso
            self.save()
            return

        if len(self.favorites) >= self.MAX_FAVORITES:
            oldest = min(self.favorites.items(), key=lambda x: str(x[1].get('added_at') or ''))
            del self.favorites[oldest[0]]

        self.favorites[anime_id_str] = {
            'title': str(title or 'Unknown'),
            'thumbnail': str(thumbnail or ''),
            'added_at': now_iso
        }
        self.save()

    def remove(self, anime_id):
        aid = str(anime_id)
        if aid in self.favorites:
            del self.favorites[aid]
            self.save()

    def is_favorite(self, anime_id) -> bool:
        return str(anime_id) in self.favorites

    def get_all(self) -> List[Dict[str, Any]]:
        items = []
        for k, v in self.favorites.items():
            if not isinstance(v, dict):
                continue
            items.append({
                'anime_id': str(k),
                'id': str(k),
                'title': str(v.get('title') or 'Unknown'),
                'thumbnail': str(v.get('thumbnail') or ''),
                'added_at': str(v.get('added_at') or '')
            })
        return sorted(items, key=lambda x: x['added_at'], reverse=True)
