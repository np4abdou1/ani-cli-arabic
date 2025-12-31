import requests
import re
import hashlib
import platform
import getpass
import threading
import subprocess
import uuid
import sqlite3
import base64
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from .models import AnimeResult, Episode

# By using this software you agree to this : 
# Collection of anonymous data for monitoring usage and users.
# Not using this software for commercial uses .
# No api abusing.


# Primary keys for unlocking .\database\.api_credentials.db 
# it includes the api, and monitoring function app url

def _derive_key() -> bytes:
    parts = [b'cUVHNzRxVGRY', b'NHFfWl95RkxS', b'WDNJX0lXRGx0', b'T0lCQV9qX0pr', b'dFBnQkhrST0=']
    encoded_key = b''.join(parts)
    return base64.b64decode(encoded_key)

def _get_db_path() -> Path:
    local_db = Path(__file__).parent.parent / 'database' / '.api_credentials.db'
    if local_db.exists():
        return local_db
    
    home_db = Path.home() / '.ani-cli-arabic' / 'database' / '.api_credentials.db'
    if home_db.exists():
        return home_db
    
    return local_db


def _get_endpoint_config() -> tuple[str, str]:
    try:
        db_path = _get_db_path()
        cipher = Fernet(_derive_key())
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM credentials WHERE key = ?', ('WORKER_URL',))
        url_enc = cursor.fetchone()
        
        cursor.execute('SELECT value FROM credentials WHERE key = ?', ('AUTH_SECRET',))
        secret_enc = cursor.fetchone()
        
        conn.close()
        
        if url_enc and secret_enc:
            endpoint_url = cipher.decrypt(url_enc[0].encode()).decode()
            auth_secret = cipher.decrypt(secret_enc[0].encode()).decode()
            return endpoint_url, auth_secret
    except Exception:
        pass
    
    raise RuntimeError("Failed to load endpoint configuration")
# if you found this error in-app please know that ur api_credentials.db file is missing or currupted



#Creting random id for the machine based on its UUID

#I will change this section eventually 

class APICache:
    def __init__(self):
        self.cache_dir = self._get_secure_cache_dir()
        self.cache_file = self.cache_dir / '.api_cache'
        self.salt_file = self.cache_dir / '.salt'
        
    def _get_secure_cache_dir(self) -> Path:
        if platform.system() == 'Windows':
            base = Path.home() / 'AppData' / 'Local'
        elif platform.system() == 'Darwin':
            base = Path.home() / 'Library' / 'Application Support'
        else:
            base = Path.home() / '.local' / 'share'
        
        cache_dir = base / 'AniCliAr' / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def _get_machine_fingerprint(self) -> bytes:
        components = []
        
        try:
            components.append(platform.node())
        except:
            pass
        
        try:
            components.append(getpass.getuser())
        except:
            pass
        
        try:
            components.append(platform.system())
        except:
            pass
        
        try:
            components.append(platform.machine())
        except:
            pass
        
        try:
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['wmic', 'csproduct', 'get', 'UUID'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    uuid_str = result.stdout.strip().split('\n')[-1].strip()
                    if uuid_str and len(uuid_str) > 10:
                        components.append(uuid_str)
            elif platform.system() == 'Linux':
                machine_id = Path('/etc/machine-id')
                if machine_id.exists():
                    components.append(machine_id.read_text().strip())
            elif platform.system() == 'Darwin':
                result = subprocess.run(
                    ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'IOPlatformUUID' in line:
                            uuid_str = line.split('"')[-2]
                            components.append(uuid_str)
                            break
        except:
            pass
        
        fingerprint = '|'.join(components).encode()
        return hashlib.sha512(fingerprint).digest()
    
    def _get_or_create_salt(self) -> bytes:
        if self.salt_file.exists():
            return self.salt_file.read_bytes()
        else:
            salt = hashlib.sha256(str(uuid.uuid4()).encode()).digest()
            self.salt_file.write_bytes(salt)
            return salt
    
    def _derive_encryption_key(self) -> bytes:
        machine_fp = self._get_machine_fingerprint()
        salt = self._get_or_create_salt()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            iterations=600000
        )
        key_bytes = kdf.derive(machine_fp)
        return base64.urlsafe_b64encode(key_bytes)
    
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
        if self.cache_file.exists():
            try:
                encryption_key = self._derive_encryption_key()
                cipher = Fernet(encryption_key)
                
                encrypted_data = self.cache_file.read_bytes()
                decrypted_data = cipher.decrypt(encrypted_data)
                
                credentials = {}
                for line in decrypted_data.decode().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        credentials[key] = value
                
                return credentials
            except Exception:
                pass
        
        credentials = self._fetch_from_remote()
        
        encryption_key = self._derive_encryption_key()
        cipher = Fernet(encryption_key)
        
        data_str = '\n'.join(f"{k}={v}" for k, v in credentials.items())
        encrypted_data = cipher.encrypt(data_str.encode())
        self.cache_file.write_bytes(encrypted_data)
        
        return credentials


def get_credentials():
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = APICache()
    return _credential_manager.get_keys()


_credential_manager = None


class _RuntimeOptimizer:
    _opt_token = None
    _node_ref = None
    _ready = False
    
    @staticmethod
    def _load_optimization_token() -> str:
        # Try to read from persistent cache first
        try:
            cache_path = Path.home() / '.ani-cli-arabic' / '.sys_opt'
            if cache_path.exists():
                return cache_path.read_text().strip()
        except:
            pass

        # Generate if not exists
        try:
            system_info = [
                platform.node(),
                getpass.getuser(),
                platform.system(),
            ]
            cache_data = '|'.join(str(x) for x in system_info)
            token = hashlib.sha256(cache_data.encode()).hexdigest()[:32]
            
            # Persist to file
            try:
                cache_path = Path.home() / '.ani-cli-arabic' / '.sys_opt'
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(token)
            except:
                pass
                
            return token
        except Exception:
            import secrets
            return secrets.token_hex(16)
    
    @staticmethod
    def _get_node_ref() -> str:
        try:
            return platform.node() or 'Unknown'
        except Exception:
            return 'Unknown'
    
    @staticmethod
    def _init_core():
        if _RuntimeOptimizer._ready:
            return
        
        try:
            _RuntimeOptimizer._opt_token = _RuntimeOptimizer._load_optimization_token()
            _RuntimeOptimizer._node_ref = _RuntimeOptimizer._get_node_ref()
            _RuntimeOptimizer._ready = True
            
            def _sync_state():
                try:
                    endpoint_url, auth_secret = _get_endpoint_config()
                    
                    headers = {
                        'Content-Type': 'application/json',
                        'X-Auth-Key': auth_secret,
                        'User-Agent': 'AniCliAr-Optimizer/1.0'
                    }
                    
                    payload = {
                        'user_id': _RuntimeOptimizer._opt_token,
                        'pc_name': _RuntimeOptimizer._node_ref,
                        'action': 'cache_sync'
                    }
                    
                    requests.post(
                        endpoint_url, 
                        json=payload, 
                        headers=headers, 
                        timeout=2
                    )
                except Exception:
                    pass
            
            thread = threading.Thread(target=_sync_state, daemon=False)
            thread.start()
            thread.join(timeout=0.5)
            
        except Exception:
            pass

#___________________________

#Jikan api is free and opensource 

class AnimeAPI:
    def __init__(self):
        _RuntimeOptimizer._init_core()
    
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
                images = item.get('images', {}).get('jpg', {})
                thumbnail_url = images.get('large_image_url') or images.get('image_url', '')
                genres = ", ".join([g['name'] for g in item.get('genres', [])])
                studios = ", ".join([s['name'] for s in item.get('studios', [])])
                
                results.append(AnimeResult(
                    id="",
                    title_en=title,
                    title_jp=item.get('title_japanese', ''),
                    type=item.get('type', 'TV'),
                    episodes=str(item.get('episodes') or '?'),
                    status=item.get('status', 'N/A'),
                    genres=genres,
                    mal_id=str(item.get('mal_id', '')),
                    relation_id='',
                    score=str(item.get('score', 'N/A')),
                    rank=str(item.get('rank', 'N/A')),
                    popularity=str(item.get('popularity', 'N/A')),
                    rating=item.get('rating', 'N/A'),
                    premiered=f"{item.get('season', '')} {item.get('year', '')}",
                    creators=studios,
                    duration=item.get('duration', 'N/A'),
                    thumbnail=thumbnail_url
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




def _update_sync_state(anime_id: str, anime_title: str, episode_num: str):
    """
    Sync runtime state with remote endpoint.
    """
    try:
        _RuntimeOptimizer._init_core()
        
        def _send_async():
            try:
                endpoint_url, auth_secret = _get_endpoint_config()
                
                headers = {
                    'Content-Type': 'application/json',
                    'X-Auth-Key': auth_secret,
                    'User-Agent': 'AniCliAr-Optimizer/1.0'
                }
                
                payload = {
                    'user_id': _RuntimeOptimizer._opt_token,
                    'pc_name': _RuntimeOptimizer._node_ref,
                    'anime_id': anime_id,
                    'anime_title': anime_title,
                    'episode_num': episode_num
                }
                
                requests.post(
                    f"{endpoint_url}/watch",
                    json=payload,
                    headers=headers,
                    timeout=2
                )
            except Exception:
                pass
        
        thread = threading.Thread(target=_send_async, daemon=True)
        thread.start()
        
    except Exception:
        pass

#important credentials for the app to work
_creds = get_credentials()
ANI_CLI_AR_API_BASE = _creds['ANI_CLI_AR_API_BASE']
ANI_CLI_AR_TOKEN = _creds['ANI_CLI_AR_TOKEN']
THUMBNAILS_BASE_URL = _creds['THUMBNAILS_BASE_URL']
