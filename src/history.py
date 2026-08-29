import json
from pathlib import Path
from datetime import datetime
from .storage import atomic_write_json

def format_seconds(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS format."""
    if not seconds or seconds < 0:
        return "00:00"
    seconds = int(round(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

class HistoryManager:
    # Maximum history entries to maintain reasonable file size and load times
    MAX_HISTORY_SIZE = 100
    
    def __init__(self):
        self.history_file = self._get_history_path()
        self.history = self._load_history()

    def _get_history_path(self) -> Path:
        home_dir = Path.home()
        db_dir = home_dir / ".ani-cli-arabic" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "history.json"

    def _load_history(self) -> dict:
        if not self.history_file.exists():
            return {}
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except (json.JSONDecodeError, IOError, OSError):
            return {}

    def save_history(self):
        try:
            if len(self.history) > self.MAX_HISTORY_SIZE:
                sorted_items = sorted(
                    self.history.items(),
                    key=lambda x: x[1].get('last_updated', ''),
                    reverse=True
                )
                self.history = dict(sorted_items[:self.MAX_HISTORY_SIZE])

            atomic_write_json(self.history_file, self.history, indent=4, ensure_ascii=False)
        except (IOError, OSError, ValueError, TypeError) as e:
            import sys
            print(f"Warning: Failed to save history: {e}", file=sys.stderr)

    def mark_watched(self, anime_id, episode_num, anime_title, time_pos: float = 0.0, duration: float = 0.0, percent: float = 0.0):
        """
        Record watch progress for an episode and series.
        """
        anime_id_str = str(anime_id)
        ep_num_str = str(episode_num)
        
        # Calculate percentage if duration is known
        if percent <= 0 and duration > 0 and time_pos > 0:
            percent = round((time_pos / duration) * 100, 1)
            
        percent_val = max(0, min(100, int(round(percent or 0))))
        completed = percent_val >= 90 or (duration > 0 and duration - time_pos < 30)
        
        # Retrieve existing entry to preserve other episode history
        entry = self.history.get(anime_id_str, {})
        episodes_prog = entry.get('episodes_progress', {})
        if not isinstance(episodes_prog, dict):
            episodes_prog = {}
            
        # Update episode-specific record
        episodes_prog[ep_num_str] = {
            'time_pos': round(float(time_pos or 0.0), 1),
            'duration': round(float(duration or 0.0), 1),
            'percent': percent_val,
            'completed': completed,
            'last_updated': datetime.now().isoformat()
        }
        
        # Update main series record
        self.history[anime_id_str] = {
            'episode': ep_num_str,
            'title': anime_title,
            'time_pos': round(float(time_pos or 0.0), 1),
            'duration': round(float(duration or 0.0), 1),
            'percent': percent_val,
            'completed': completed,
            'last_updated': datetime.now().isoformat(),
            'episodes_progress': episodes_prog
        }
        self.save_history()

    def get_last_watched(self, anime_id):
        """Get the episode number string of the most recently watched episode."""
        data = self.history.get(str(anime_id))
        if data:
            return data.get('episode')
        return None

    def get_episode_progress(self, anime_id, episode_num) -> dict:
        """Get progress dict for a specific episode."""
        data = self.history.get(str(anime_id), {})
        episodes_prog = data.get('episodes_progress', {})
        if isinstance(episodes_prog, dict) and str(episode_num) in episodes_prog:
            return episodes_prog[str(episode_num)]
            
        # Fallback to series-level record if it matches episode
        if str(data.get('episode')) == str(episode_num):
            return {
                'time_pos': data.get('time_pos', 0.0),
                'duration': data.get('duration', 0.0),
                'percent': data.get('percent', 0),
                'completed': data.get('completed', False),
                'last_updated': data.get('last_updated', '')
            }
        return {'time_pos': 0.0, 'duration': 0.0, 'percent': 0, 'completed': False}

    def get_all_episodes_progress(self, anime_id) -> dict:
        """Get dictionary mapping episode numbers to progress dicts for an anime."""
        data = self.history.get(str(anime_id), {})
        episodes_prog = data.get('episodes_progress', {})
        result = {}
        if isinstance(episodes_prog, dict):
            result.update(episodes_prog)
            
        # Ensure the active episode is also represented
        if 'episode' in data:
            active_ep = str(data['episode'])
            if active_ep not in result:
                result[active_ep] = {
                    'time_pos': data.get('time_pos', 0.0),
                    'duration': data.get('duration', 0.0),
                    'percent': data.get('percent', 0),
                    'completed': data.get('completed', False),
                    'last_updated': data.get('last_updated', '')
                }
        return result

    def remove(self, anime_id):
        if str(anime_id) in self.history:
            del self.history[str(anime_id)]
            self.save_history()

    def get_history(self):
        items = []
        for anime_id, data in self.history.items():
            time_pos = data.get('time_pos', 0.0)
            duration = data.get('duration', 0.0)
            percent = int(data.get('percent', 0))
            completed = data.get('completed', False) or (percent >= 90)
            
            items.append({
                'anime_id': anime_id,
                'title': data.get('title', 'Unknown'),
                'episode': data.get('episode', '?'),
                'time_pos': time_pos,
                'duration': duration,
                'percent': percent,
                'completed': completed,
                'time_str': format_seconds(time_pos),
                'duration_str': format_seconds(duration),
                'last_updated': data.get('last_updated', '')
            })
        # Sort by last_updated, most recent first
        items.sort(key=lambda x: x['last_updated'], reverse=True)
        return items