import requests
import re
import sqlite3
import base64
import hashlib
from typing import List, Optional, Dict
from cryptography.fernet import Fernet
from pathlib import Path
from .models import AnimeResult, Episode

class AnimeAPI:
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
                    thumbnail=thumbnail_url
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


class _CredentialManager:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
        self.db_path = self._get_db_path()
        self._db_key = hashlib.sha256(key).digest()
        self._ensure_db_exists()
    
    def _get_db_path(self) -> Path:
        base_dir = Path(__file__).parent.parent
        return base_dir / "database" / ".credentials.db"
    
    def _ensure_db_exists(self):
        if not self.db_path.exists():
            self._create_db()
    
    def _verify_db_access(self, conn):
        cursor = conn.cursor()
        cursor.execute('PRAGMA user_version')
        version = cursor.fetchone()[0]
        expected = int.from_bytes(self._db_key[:4], 'big') % 1000000
        if version != 0 and version != expected:
            raise RuntimeError("Database access denied")
        if version == 0:
            cursor.execute(f'PRAGMA user_version = {expected}')
            conn.commit()
    
    def _create_db(self):
        conn = sqlite3.connect(self.db_path)
        self._verify_db_access(conn)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        credentials = {
            'ANI_CLI_AR_API_BASE': 'https://animeify.net/animeify/apis_v4/',
            'ANI_CLI_AR_TOKEN': '8cnY80AZSbUCmR26Vku1VUUY4',
            'THUMBNAILS_BASE_URL': 'https://animeify.net/animeify/files/thumbnails/'
        }
        for key, value in credentials.items():
            encrypted_value = self.cipher.encrypt(value.encode()).decode()
            cursor.execute('INSERT OR REPLACE INTO credentials (key, value) VALUES (?, ?)',
                         (key, encrypted_value))
        conn.commit()
        conn.close()
    
    def get_credential(self, key: str) -> str:
        try:
            conn = sqlite3.connect(self.db_path)
            self._verify_db_access(conn)
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM credentials WHERE key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            if result:
                encrypted_value = result[0]
                decrypted_value = self.cipher.decrypt(encrypted_value.encode()).decode()
                return decrypted_value
            raise ValueError(f"Credential '{key}' not found")
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve credential '{key}': {e}")
    
    def get_all_credentials(self) -> dict:
        return {
            'ANI_CLI_AR_API_BASE': self.get_credential('ANI_CLI_AR_API_BASE'),
            'ANI_CLI_AR_TOKEN': self.get_credential('ANI_CLI_AR_TOKEN'),
            'THUMBNAILS_BASE_URL': self.get_credential('THUMBNAILS_BASE_URL')
        }


def _derive_key() -> bytes:
    parts = [b'cUVHNzRxVGRY', b'NHFfWl95RkxS', b'WDNJX0lXRGx0', b'T0lCQV9qX0pr', b'dFBnQkhrST0=']
    encoded_key = b''.join(parts)
    try:
        return base64.b64decode(encoded_key)
    except Exception:
        return Fernet.generate_key()


def _get_credentials():
    try:
        key = _derive_key()
        manager = _CredentialManager(key)
        return manager.get_all_credentials()
    except Exception:
        return {'ANI_CLI_AR_API_BASE': '', 'ANI_CLI_AR_TOKEN': '', 'THUMBNAILS_BASE_URL': ''}


_creds = _get_credentials()
ANI_CLI_AR_API_BASE = _creds['ANI_CLI_AR_API_BASE']
ANI_CLI_AR_TOKEN = _creds['ANI_CLI_AR_TOKEN']
THUMBNAILS_BASE_URL = _creds['THUMBNAILS_BASE_URL']
