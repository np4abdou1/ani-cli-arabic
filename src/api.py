import requests
import platform
import base64
import hashlib
import subprocess
import uuid
import re
import getpass
from pathlib import Path
from typing import List, Optional, Dict
from .models import AnimeResult, Episode

# Note: This software collects anonymous usage data (app start, video play)
# to help improve the application. No personal data is collected.

def _get_endpoint_config() -> tuple[str, str]:
    # Hardcoded configuration for the remote worker
    endpoint_url = "https://ani-cli-arabic-analytics.talego4955.workers.dev" 
    auth_secret = "8GltlSgyTHwNJ-77n8R4T2glZ_EDQHcU4AB4Wjuu75M"
    
    return endpoint_url, auth_secret


class APICache:
    def __init__(self):
        pass
    
    def _fetch_from_remote(self) -> dict:
        endpoint_url, auth_secret = _get_endpoint_config()
        
        try:
            response = requests.get(
                f"{endpoint_url}/credentials",
                headers={
                    'X-Auth-Key': auth_secret,
                    'User-Agent': 'AniCliAr/2.0'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Remote endpoint returned status {response.status_code}")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch credentials: {e}")
    
    def get_keys(self) -> dict:
        # Simply fetch credentials from remote, no local caching encryption needed for now
        # as we are moving away from local DB storage.
        return self._fetch_from_remote()


def get_credentials():
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = APICache()
    return _credential_manager.get_keys()


_credential_manager = None



#___________________________

#Jikan api is free and opensource 

class AnimeAPI:
    def __init__(self):
        pass
    
    def get_mal_season_now(self) -> List[AnimeResult]:
        url = "https://api.jikan.moe/v4/seasons/now"
        try:
            response = requests.get(url, params={'sfw': 'true'}, timeout=10)
            response.raise_for_status()
            data = response.json().get('data', [])
            
            results = []
            for item in data:
                rating_str = item.get('rating', '')
                if rating_str and 'Rx' in rating_str:
                    continue

                title = item.get('title_english') or item.get('title')
                title_romaji = item.get('title') or ''
                images = item.get('images', {}).get('jpg', {})
                thumbnail_url = images.get('large_image_url') or images.get('image_url', '')
                genres = ", ".join([g['name'] for g in item.get('genres', [])])
                studios = ", ".join([s['name'] for s in item.get('studios', [])])
                
                score = item.get('score')
                score = str(score) if score is not None else 'N/A'

                rank = item.get('rank')
                rank = str(rank) if rank is not None else 'N/A'

                popularity = item.get('popularity')
                popularity = str(popularity) if popularity is not None else 'N/A'

                results.append(AnimeResult(
                    id="",
                    title_en=title,
                    title_jp=item.get('title_japanese') or '',
                    type=item.get('type') or 'TV',
                    episodes=str(item.get('episodes') or '?'),
                    status=item.get('status') or 'N/A',
                    genres=genres,
                    mal_id=str(item.get('mal_id') or ''),
                    relation_id='',
                    score=score,
                    rank=rank,
                    popularity=popularity,
                    rating=item.get('rating') or 'N/A',
                    premiered=f"{item.get('season') or ''} {item.get('year') or ''}".strip(),
                    creators=studios,
                    duration=item.get('duration') or 'N/A',
                    thumbnail=thumbnail_url,
                    title_romaji=title_romaji
                ))
            return results
        except Exception:
            return []

    def search_anime(self, query: str) -> List[AnimeResult]:
        endpoint = ANI_CLI_AR_API_BASE + "anime/load_anime_list_v2.php"
        payload = {
            'UserId': '0',
            'Language': 'English',
            'FilterType': 'SEARCH',
            'FilterData': query,
            'Type': 'SERIES',
            'From': '0',
            'Token': ANI_CLI_AR_TOKEN
        }
        
        try:
            response = requests.post(endpoint, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data:
                thumbnail_filename = item.get('Thumbnail', '')
                thumbnail_url = THUMBNAILS_BASE_URL + thumbnail_filename if thumbnail_filename else ''
                
                results.append(AnimeResult(
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
                    creators=item.get('Studios', 'N/A'),
                    duration=item.get('Duration', 'N/A'),
                    thumbnail=thumbnail_url,
                    title_romaji=item.get('EN_Title', '')
                ))
            return results
        except Exception:
            return []

    def load_episodes(self, anime_id: str) -> List[Episode]:
        endpoint = ANI_CLI_AR_API_BASE + "episodes/load_episodes.php"
        payload = {
            'AnimeID': anime_id,
            'Token': ANI_CLI_AR_TOKEN
        }
        
        try:
            response = requests.post(endpoint, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            episodes = []
            for idx, ep in enumerate(data, 1):
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
        except Exception:
            return []

    def get_streaming_servers(self, anime_id: str, episode_num: str) -> Optional[Dict]:
        endpoint = ANI_CLI_AR_API_BASE + "anime/load_servers.php"
        payload = {
            'UserId': '0',
            'AnimeId': anime_id,
            'Episode': str(episode_num),
            'AnimeType': 'SERIES',
            'Token': ANI_CLI_AR_TOKEN
        }
        
        try:
            response = requests.post(endpoint, data=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception:
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
        except Exception:
            return None

    def build_mediafire_url(self, server_id: str) -> str:
        if server_id.startswith('http'):
            return server_id
        return f'https://www.mediafire.com/file/{server_id}'





#important credentials for the app to work
_creds = get_credentials()
ANI_CLI_AR_API_BASE = _creds['ANI_CLI_AR_API_BASE']
ANI_CLI_AR_TOKEN = _creds['ANI_CLI_AR_TOKEN']
THUMBNAILS_BASE_URL = _creds['THUMBNAILS_BASE_URL']
