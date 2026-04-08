import json
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional

import requests
from .models import AnimeResult, Episode
from .storage import atomic_write_json

# Default credentials - can be overridden with environment variables
# This is for analytics and also api credentials fetching.
ENDPOINT_URL = "https://api.ani-cli-arabic.dev"
AUTH_SECRET = "6rK9z0XyW8vQ3J7pL2mN4sB1tH5gD0fA"

def _get_endpoint_config() -> tuple[str, str]:
    """Get API endpoint configuration from environment or hardcoded defaults."""
    import os
    endpoint_url = os.getenv('ANI_CLI_AR_ENDPOINT', ENDPOINT_URL)
    auth_secret = os.getenv('ANI_CLI_AR_AUTH_SECRET', AUTH_SECRET)
    return endpoint_url, auth_secret


class APICache:
    CACHE_FILENAME = "api_credentials.json"

    def __init__(self):
        home_dir = Path.home()
        db_dir = home_dir / ".ani-cli-arabic" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = db_dir / self.CACHE_FILENAME

    @staticmethod
    def _default_keys() -> dict:
        return {
            'ANI_CLI_AR_API_BASE': '',
            'ANI_CLI_AR_TOKEN': '',
            'THUMBNAILS_BASE_URL': '',
            'TRAILERS_BASE_URL': ''
        }

    @staticmethod
    def _normalize_keys(data: dict) -> dict:
        defaults = APICache._default_keys()
        if not isinstance(data, dict):
            return defaults
        return {key: str(data.get(key, defaults[key]) or '') for key in defaults}

    def _load_cached_keys(self) -> Optional[dict]:
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as cache_handle:
                cached = json.load(cache_handle)

            normalized = self._normalize_keys(cached)
            if normalized['ANI_CLI_AR_API_BASE'] and normalized['ANI_CLI_AR_TOKEN']:
                return normalized
        except (json.JSONDecodeError, OSError, IOError, ValueError, TypeError):
            return None

        return None

    def _save_cached_keys(self, keys: dict) -> None:
        normalized = self._normalize_keys(keys)
        if not normalized['ANI_CLI_AR_API_BASE'] or not normalized['ANI_CLI_AR_TOKEN']:
            return

        try:
            atomic_write_json(self.cache_file, normalized, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def _fetch_from_remote(self) -> dict:
        endpoint_url, auth_secret = _get_endpoint_config()
        cached = self._load_cached_keys()
        
        try:
            response = requests.get(
                f"{endpoint_url}/credentials",
                headers={
                    'X-Auth-Key': auth_secret,
                    'User-Agent': 'AniCliAr/2.0'
                },
                timeout=10
            )
            
            response.raise_for_status()
            remote_keys = self._normalize_keys(response.json())
            if remote_keys['ANI_CLI_AR_API_BASE'] and remote_keys['ANI_CLI_AR_TOKEN']:
                self._save_cached_keys(remote_keys)
                return remote_keys
        except (requests.RequestException, ValueError, TypeError):
            pass

        if cached:
            return cached
        return self._default_keys()
    
    def get_keys(self) -> dict:
        return self._fetch_from_remote()


def get_credentials():
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = APICache()
    return _credential_manager.get_keys()


_credential_manager = None
_creds = None
_creds_lock = threading.Lock()

def _ensure_creds():
    global _creds, _credential_manager
    if _creds is not None:
        return

    with _creds_lock:
        if _creds is not None:
            return
        if _credential_manager is None:
            _credential_manager = APICache()
        _creds = _credential_manager.get_keys()

def get_api_base():
    _ensure_creds()
    return _creds.get('ANI_CLI_AR_API_BASE', '')

def get_api_token():
    _ensure_creds()
    return _creds.get('ANI_CLI_AR_TOKEN', '')

def get_thumbnails_base():
    _ensure_creds()
    return _creds.get('THUMBNAILS_BASE_URL', '')

def get_trailers_base():
    _ensure_creds()
    return _creds.get('TRAILERS_BASE_URL', '')

class AnimeAPI:
    
    def _parse_anime_result(self, item: dict) -> AnimeResult:
        thumbnail_filename = item.get('Thumbnail', '')
        thumbnail_url = get_thumbnails_base() + thumbnail_filename if thumbnail_filename else ''
        
        return AnimeResult(
            id=item.get('AnimeId', ''),
            title_en=item.get('EN_Title', 'Unknown'),
            title_jp=item.get('JP_Title', ''),
            type=item.get('Type', 'N/A'),
            episodes=str(item.get('Episodes', 'N/A')),
            status=item.get('Status', 'N/A'),
            genres=item.get('Genres', 'N/A'),
            mal_id=item.get('MalId', '0'),
            relation_id=item.get('RelationId', ''),
            score=str(item.get('Score', 'N/A')),
            rank=str(item.get('Rank', 'N/A')),
            popularity=str(item.get('Popularity', 'N/A')),
            rating=item.get('Rating', 'N/A'),
            premiered=item.get('Season', 'N/A'),
            creators=item.get('Creators', 'N/A'),
            duration=str(item.get('Duration', 'N/A')),
            thumbnail=thumbnail_url,
            title_romaji=item.get('EN_Title', ''),
            trailer=item.get('Trailer', ''),
            yt_trailer=item.get('YTTrailer', '')
        )

    def _paginate_requests(self, endpoint: str, limit: int, from_index: int, base_payload: dict) -> List[AnimeResult]:
        all_results = []
        current_from = from_index
        
        while len(all_results) < limit:
            payload = base_payload.copy()
            payload['From'] = str(current_from)
            payload['Token'] = get_api_token()
            
            try:
                response = requests.post(endpoint, data=payload, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if not isinstance(data, list) or not data:
                    break
                    
                batch = [self._parse_anime_result(item) for item in data if isinstance(item, dict)]
                all_results.extend(batch)
                
                if len(batch) < 10: 
                    break
                    
                current_from += len(batch)
                
            except Exception:
                break
                
        return all_results[:limit]

    def get_anime_list(self, filter_type: str = "", filter_data: str = "", anime_type: str = "SERIES", from_index: int = 0, limit: int = 30) -> List[AnimeResult]:
        endpoint = get_api_base() + "anime/load_anime_list_v2.php"
        payload = {
            'UserId': '0',
            'Language': 'English',
            'FilterType': filter_type,
            'FilterData': filter_data,
            'Type': anime_type,
        }
        return self._paginate_requests(endpoint, limit, from_index, payload)

    def get_latest_anime(self, from_index: int = 0, limit: int = 30) -> List[AnimeResult]:
        endpoint = get_api_base() + "anime/load_latest_anime.php"
        payload = {
            'UserId': '0',
            'Language': 'English',
        }
        return self._paginate_requests(endpoint, limit, from_index, payload)

    def search_anime(self, query: str) -> List[AnimeResult]:
        series_results = self.get_anime_list(filter_type="SEARCH", filter_data=query, anime_type="SERIES", limit=20)
        movie_results = self.get_anime_list(filter_type="SEARCH", filter_data=query, anime_type="MOVIE", limit=20)
        return series_results + movie_results

    def get_trending_anime(self, from_index: int = 0, limit: int = 15) -> List[AnimeResult]:
        fetch_limit = limit + from_index + 20
        results = self.get_latest_anime(limit=fetch_limit)
        results_with_pop = [r for r in results if r.popularity and r.popularity.isdigit()]
        results_with_pop.sort(key=lambda x: int(x.popularity))
        return results_with_pop[from_index:from_index + limit]

    def get_top_rated_anime(self, from_index: int = 0, limit: int = 15) -> List[AnimeResult]:
        return self.get_anime_list(filter_type="SORT", filter_data="HIGHEST_RATE", anime_type="SERIES", from_index=from_index, limit=limit)

    def get_episodes(self, anime_id: str) -> List[Episode]:
        endpoint = get_api_base() + "episodes/load_episodes.php"
        payload = {
            'AnimeID': anime_id,
            'Token': get_api_token()
        }
        
        try:
            response = requests.post(endpoint, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list):
                return []
            
            episodes = []
            for idx, ep in enumerate(data, 1):
                if not isinstance(ep, dict):
                    continue
                    
                ep_num = ep.get('Episode', str(idx))
                ep_type = ep.get('Type', 'Episode')
                
                if not ep_type or ep_type.strip() == "":
                    ep_type = "Episode"
                    
                try:
                    display_num_str = str(ep_num)
                    if '.' in display_num_str:
                        display_num = float(display_num_str)
                    else:
                        display_num = int(float(display_num_str))
                except (ValueError, TypeError):
                    display_num = idx
                episodes.append(Episode(ep_num, ep_type, display_num))
            return episodes
        except (requests.RequestException, ValueError, TypeError):
            return []

    def get_streaming_servers(self, anime_id: str, episode_num: str, anime_type: str = 'SERIES') -> Optional[Dict]:
        endpoint = get_api_base() + "anime/load_servers.php"
        payload = {
            'UserId': '0',
            'AnimeId': anime_id,
            'Episode': str(episode_num),
            'AnimeType': anime_type,
            'Token': get_api_token()
        }
        
        try:
            response = requests.post(endpoint, data=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError, TypeError):
            return None

    def extract_mediafire_direct(self, mf_url: str) -> Optional[str]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(mf_url, headers=headers, timeout=10)
            response.raise_for_status()
            match = re.search(r'(https://download[^"]+)', response.text)
            return match.group(1) if match else None
        except (requests.RequestException, AttributeError):
            return None

    def build_mediafire_url(self, server_id: str) -> str:
        if server_id.startswith('http'):
            return server_id
        return f'https://www.mediafire.com/file/{server_id}'

