"""
Animeify Arabic Anime Provider for ani-cli-arabic
Original backend provider with dynamic credentials management from api.ani-cli-arabic.dev,
Mediafire direct stream extraction, Fembed/Google Drive/OK.ru servers, and comprehensive discovery.
"""

import os
import re
import json
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
import requests

from .base import BaseAnimeProvider
from ..models import AnimeResult, Episode, QualityOption
from ..storage import atomic_write_json
from ..logger import logger


DEFAULT_ENDPOINT_URL = "https://api.ani-cli-arabic.dev"
DEFAULT_AUTH_SECRET = "6rK9z0XyW8vQ3J7pL2mN4sB1tH5gD0fA"

FALLBACK_API_BASE = "https://animeify.net/animeify/apis_v4/"
FALLBACK_TOKEN = "8cnY80AZSbUCmR26Vku1VUUY4"
FALLBACK_THUMBNAILS_BASE = "https://animeify.net/animeify/files/thumbnails/"
FALLBACK_TRAILERS_BASE = "https://animeify.net/animeify/files/trailers/"


class AnimeifyAPICache:
    CACHE_FILENAME = "api_credentials.json"

    def __init__(self):
        home_dir = Path.home()
        db_dir = home_dir / ".ani-cli-arabic" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = db_dir / self.CACHE_FILENAME

    @staticmethod
    def _default_keys() -> dict:
        return {
            'ANI_CLI_AR_API_BASE': FALLBACK_API_BASE,
            'ANI_CLI_AR_TOKEN': FALLBACK_TOKEN,
            'THUMBNAILS_BASE_URL': FALLBACK_THUMBNAILS_BASE,
            'TRAILERS_BASE_URL': FALLBACK_TRAILERS_BASE
        }

    @staticmethod
    def _normalize_keys(data: dict) -> dict:
        defaults = AnimeifyAPICache._default_keys()
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
        except Exception:
            return None
        return None

    def _save_cached_keys(self, keys: dict) -> None:
        normalized = self._normalize_keys(keys)
        if not normalized['ANI_CLI_AR_API_BASE'] or not normalized['ANI_CLI_AR_TOKEN']:
            return
        try:
            atomic_write_json(self.cache_file, normalized, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_keys(self) -> dict:
        endpoint_url = os.getenv('ANI_CLI_AR_ENDPOINT', DEFAULT_ENDPOINT_URL)
        auth_secret = os.getenv('ANI_CLI_AR_AUTH_SECRET', DEFAULT_AUTH_SECRET)
        cached = self._load_cached_keys()

        try:
            response = requests.get(
                f"{endpoint_url}/credentials",
                headers={
                    'X-Auth-Key': auth_secret,
                    'User-Agent': 'AniCliAr/2.0'
                },
                timeout=8
            )
            if response.status_code == 200:
                remote_keys = self._normalize_keys(response.json())
                if remote_keys['ANI_CLI_AR_API_BASE'] and remote_keys['ANI_CLI_AR_TOKEN']:
                    self._save_cached_keys(remote_keys)
                    return remote_keys
        except Exception:
            pass

        if cached:
            return cached
        return self._default_keys()


class AnimeifyProvider(BaseAnimeProvider):
    """
    Animeify Anime Provider.
    Extracts direct Mediafire, Fembed, and multi-resolution streams using the Animeify v4 API.
    """

    id: str = "animeify"
    name: str = "Animeify"
    description: str = "Original Animeify API provider with remote credential authentication"

    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(self):
        self._local = threading.local()
        self._cache_lock = threading.Lock()
        self._credential_manager = AnimeifyAPICache()
        self._creds: Optional[Dict[str, str]] = None
        self._anime_cache: Dict[str, AnimeResult] = {}
        self._episode_cache: Dict[str, List[Episode]] = {}

    @property
    def session(self) -> requests.Session:
        """Thread-local requests session."""
        if not hasattr(self._local, "session"):
            s = requests.Session()
            s.headers.update({
                "User-Agent": self.DEFAULT_USER_AGENT,
                "Accept": "*/*",
            })
            self._local.session = s
        return self._local.session

    def _ensure_creds(self) -> Dict[str, str]:
        """Ensure API base and token are loaded and valid."""
        if self._creds is not None:
            return self._creds
        with self._cache_lock:
            if self._creds is not None:
                return self._creds
            self._creds = self._credential_manager.get_keys()
            return self._creds

    @property
    def api_base(self) -> str:
        return self._ensure_creds().get('ANI_CLI_AR_API_BASE', FALLBACK_API_BASE)

    @property
    def api_token(self) -> str:
        return self._ensure_creds().get('ANI_CLI_AR_TOKEN', FALLBACK_TOKEN)

    @property
    def thumbnails_base(self) -> str:
        return self._ensure_creds().get('THUMBNAILS_BASE_URL', FALLBACK_THUMBNAILS_BASE)

    @property
    def trailers_base(self) -> str:
        return self._ensure_creds().get('TRAILERS_BASE_URL', FALLBACK_TRAILERS_BASE)

    def _post(self, endpoint: str, payload: Dict[str, Any], timeout: int = 10) -> Optional[requests.Response]:
        """Safe HTTP POST with graceful error handling and token injection."""
        try:
            full_url = f"{self.api_base.rstrip('/')}/{endpoint.lstrip('/')}"
            req_payload = payload.copy()
            if 'Token' not in req_payload:
                req_payload['Token'] = self.api_token

            resp = self.session.post(full_url, data=req_payload, timeout=timeout)
            if resp.status_code == 200:
                return resp
            logger.warning(f"[Animeify] POST {full_url} returned status {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"[Animeify] Request error on {endpoint}: {e}")
            return None

    def _parse_anime_result(self, item: dict) -> AnimeResult:
        """Parse raw Animeify API dictionary into standard AnimeResult model."""
        thumb_filename = item.get('Thumbnail', '') or item.get('CoverImage', '')
        thumb_url = f"{self.thumbnails_base}{thumb_filename}" if thumb_filename and not thumb_filename.startswith("http") else thumb_filename
        
        anime_id = str(item.get('AnimeId') or item.get('id') or '')
        title_en = item.get('EN_Title') or item.get('Title') or item.get('anime_name') or 'Unknown'
        title_ar = item.get('AR_Title') or item.get('anime_name') or title_en

        return AnimeResult(
            id=anime_id,
            title_en=title_en,
            title_ar=title_ar,
            title_jp=item.get('JP_Title', ''),
            type=item.get('Type', 'TV'),
            episodes=str(item.get('Episodes', 'N/A')),
            status=item.get('Status', 'N/A'),
            genres=item.get('Genres', 'N/A'),
            mal_id=str(item.get('MalId', '0')),
            relation_id=str(item.get('RelationId', '')),
            score=str(item.get('Score', 'N/A')),
            rank=str(item.get('Rank', 'N/A')),
            popularity=str(item.get('Popularity', 'N/A')),
            rating=item.get('Rating', 'N/A'),
            premiered=item.get('Season', 'N/A'),
            creators=item.get('Creators', 'N/A'),
            duration=str(item.get('Duration', 'N/A')),
            thumbnail=thumb_url,
            title_romaji=item.get('EN_Title', ''),
            trailer=item.get('Trailer', ''),
            yt_trailer=item.get('YTTrailer', ''),
            synopsis=item.get('Story', '') or item.get('Synopsis', '')
        )

    def _paginate(self, endpoint: str, limit: int, from_index: int, base_payload: dict) -> List[AnimeResult]:
        """Iteratively fetch paginated Animeify results up to limit."""
        all_results: List[AnimeResult] = []
        current_from = from_index

        while len(all_results) < limit:
            payload = base_payload.copy()
            payload['From'] = str(current_from)

            resp = self._post(endpoint, payload)
            if not resp:
                break

            try:
                data = resp.json()
                if not isinstance(data, list) or not data:
                    break

                batch = [self._parse_anime_result(it) for it in data if isinstance(it, dict)]
                all_results.extend(batch)

                if len(batch) < 10:
                    break

                current_from += len(batch)
            except Exception as e:
                logger.error(f"[Animeify] Error parsing JSON during pagination: {e}")
                break

        return all_results[:limit]

    def search_anime(self, query: str) -> List[AnimeResult]:
        """Search for anime by keyword or title."""
        if not query or not query.strip():
            return []

        q = query.strip()
        series_results = self.get_anime_list(filter_type="SEARCH", filter_data=q, anime_type="SERIES", limit=20)
        movie_results = self.get_anime_list(filter_type="SEARCH", filter_data=q, anime_type="MOVIE", limit=20)
        return series_results + movie_results

    def get_anime_details(self, anime_id: str) -> AnimeResult:
        """Fetch rich metadata, synopsis, genre tags, and info for an anime."""
        aid = str(anime_id).strip()
        with self._cache_lock:
            if aid in self._anime_cache:
                return self._anime_cache[aid]

        # Search by ID to fetch complete model
        results = self.get_anime_list(filter_type="SEARCH", filter_data=aid, limit=10)
        for r in results:
            if r.id.lower() == aid.lower() or aid.lower() in r.id.lower():
                with self._cache_lock:
                    self._anime_cache[aid] = r
                return r

        if results:
            with self._cache_lock:
                self._anime_cache[aid] = results[0]
            return results[0]

        return AnimeResult(id=aid, title_en=aid, thumbnail="")

    def get_episodes(self, anime_id: str) -> List[Episode]:
        """Fetch all available episodes for an anime."""
        aid = str(anime_id).strip()
        with self._cache_lock:
            if aid in self._episode_cache:
                return self._episode_cache[aid]

        resp = self._post("episodes/load_episodes.php", {'AnimeID': aid})
        data = []
        if resp:
            try:
                data = resp.json()
            except Exception:
                data = []

        if not isinstance(data, list) or not data:
            details = self.get_anime_details(aid)
            if details and details.id != aid and not details.id.isdigit():
                resp2 = self._post("episodes/load_episodes.php", {'AnimeID': details.id})
                if resp2:
                    try:
                        data = resp2.json()
                    except Exception:
                        data = []

        if not isinstance(data, list) or not data:
            return []

        try:
            episodes = []
            for idx, ep in enumerate(data, 1):
                if not isinstance(ep, dict):
                    continue

                ep_num = str(ep.get('Episode', str(idx)))
                ep_type = ep.get('Type', 'Episode') or 'Episode'

                try:
                    display_num = int(float(ep_num))
                except (ValueError, TypeError):
                    display_num = idx

                episodes.append(Episode(
                    number=ep_num,
                    type=ep_type,
                    display_num=display_num,
                    title=f"Episode {ep_num}",
                    url=str(ep.get('eId') or ''),
                    servers=[ep]
                ))

            episodes.sort(key=lambda x: x.display_num)
            with self._cache_lock:
                self._episode_cache[aid] = episodes
            return episodes
        except Exception as e:
            logger.error(f"[Animeify] Error parsing episodes: {e}")
            return []

    def _extract_mediafire_direct(self, mf_url: str) -> Optional[str]:
        """Extract direct video stream link from Mediafire URL or key."""
        try:
            url = mf_url if mf_url.startswith("http") else f"https://www.mediafire.com/file/{mf_url}"
            resp = self.session.get(url, timeout=8)
            if resp.status_code == 200:
                match = re.search(r'(https://download[^"\'\s>]+)', resp.text)
                if match:
                    return match.group(1)
            return None
        except Exception:
            return None

    def get_episode_streams(self, episode: Episode) -> List[QualityOption]:
        """Extract direct playable streaming links and resolutions for an episode."""
        if not episode.servers:
            return []

        server_dict = episode.servers[0]
        qualities: List[QualityOption] = []

        # 1. 1080p Mediafire (FRFhdQ)
        fr_fhd = server_dict.get('FRFhdQ')
        if fr_fhd:
            direct = self._extract_mediafire_direct(fr_fhd)
            if direct:
                qualities.append(QualityOption(
                    name="Mediafire > 1080p (FHD)",
                    server_key="FRFhdQ",
                    direct_url=direct,
                    res="1080p"
                ))

        # 2. 720p Mediafire (FRLink)
        fr_hd = server_dict.get('FRLink')
        if fr_hd:
            direct = self._extract_mediafire_direct(fr_hd)
            if direct:
                qualities.append(QualityOption(
                    name="Mediafire > 720p (HD)",
                    server_key="FRLink",
                    direct_url=direct,
                    res="720p"
                ))

        # 3. 480p Mediafire (FRLowQ)
        fr_sd = server_dict.get('FRLowQ')
        if fr_sd:
            direct = self._extract_mediafire_direct(fr_sd)
            if direct:
                qualities.append(QualityOption(
                    name="Mediafire > 480p (SD)",
                    server_key="FRLowQ",
                    direct_url=direct,
                    res="480p"
                ))

        return qualities

    def get_streaming_servers(self, anime_id: str, episode_num: str, anime_type: str = "SERIES") -> Optional[Dict[str, Any]]:
        """Extract direct CDN stream URLs and return mapped qualities for player and downloader."""
        resp = self._post("anime/load_servers.php", {
            'UserId': '0',
            'AnimeId': str(anime_id),
            'Episode': str(episode_num),
            'AnimeType': anime_type,
        })
        
        data = None
        if resp:
            try:
                data = resp.json()
            except Exception:
                data = None

        qualities: List[QualityOption] = []
        current_ep: Dict[str, str] = {}

        if isinstance(data, dict):
            current_ep = data.get('CurrentEpisode', {})
            # 1. 1080p Mediafire
            if current_ep.get('FRFhdQ'):
                direct = self._extract_mediafire_direct(current_ep['FRFhdQ'])
                if direct:
                    current_ep['FRFhdQ'] = direct
                    qualities.append(QualityOption("Mediafire > 1080p (FHD)", "FRFhdQ", "info", direct_url=direct, res="1080p"))

            # 2. 720p Mediafire
            if current_ep.get('FRLink'):
                direct = self._extract_mediafire_direct(current_ep['FRLink'])
                if direct:
                    current_ep['FRLink'] = direct
                    qualities.append(QualityOption("Mediafire > 720p (HD)", "FRLink", "info", direct_url=direct, res="720p"))

            # 3. 480p Mediafire
            if current_ep.get('FRLowQ'):
                direct = self._extract_mediafire_direct(current_ep['FRLowQ'])
                if direct:
                    current_ep['FRLowQ'] = direct
                    qualities.append(QualityOption("Mediafire > 480p (SD)", "FRLowQ", "info", direct_url=direct, res="480p"))

        if not current_ep and qualities:
            current_ep["FRLink"] = qualities[0].url

        return {
            'CurrentEpisode': current_ep,
            'Qualities': qualities
        }

    def get_latest_episodes(self, limit: int = 20) -> List[Episode]:
        """Fetch newly updated anime episodes."""
        anime_list = self.get_latest_anime(limit=limit)
        episodes = []
        for a in anime_list[:limit]:
            episodes.append(Episode(
                number="1",
                display_num=1,
                title=a.title_en,
                thumbnail=a.thumbnail,
                url=a.id
            ))
        return episodes

    def get_latest_anime(self, from_index: int = 0, limit: int = 30) -> List[AnimeResult]:
        """Fetch latest anime entries."""
        endpoint = "anime/load_latest_anime.php"
        payload = {
            'UserId': '0',
            'Language': 'English',
        }
        return self._paginate(endpoint, limit, from_index, payload)

    def get_pinned_anime(self, limit: int = 20) -> List[AnimeResult]:
        """Fetch pinned / spotlight / top featured anime."""
        return self.get_anime_list(filter_type="SORT", filter_data="POPULARITY", limit=limit)

    def get_trending_anime(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch popular / trending anime."""
        fetch_limit = limit + from_index + 20
        results = self.get_latest_anime(limit=fetch_limit)
        results_with_pop = [r for r in results if r.popularity and r.popularity.isdigit()]
        results_with_pop.sort(key=lambda x: int(x.popularity))
        return results_with_pop[from_index:from_index + limit]

    def get_top_rated_anime(self, from_index: int = 0, limit: int = 20, rate_tier: str = "9-10") -> List[AnimeResult]:
        """Fetch masterpiece / top rated anime."""
        return self.get_anime_list(filter_type="SORT", filter_data="HIGHEST_RATE", anime_type="SERIES", from_index=from_index, limit=limit)

    def get_movies(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime movies collection."""
        return self.get_anime_list(filter_type="", filter_data="", anime_type="MOVIE", from_index=from_index, limit=limit)

    def get_genre_anime(self, genre_slug: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime by genre category."""
        return self.get_anime_list(filter_type="GENRE", filter_data=genre_slug.title(), anime_type="SERIES", from_index=from_index, limit=limit)

    def get_studio_anime(self, studio_name: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime produced by a studio."""
        return self.get_anime_list(filter_type="STUDIOS", filter_data=studio_name, anime_type="SERIES", from_index=from_index, limit=limit)

    def get_seasonal_anime(self, season: str, year: int, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch seasonal anime."""
        return self.get_anime_list(filter_type="SEASON", filter_data=f"{season}_{year}", anime_type="SERIES", from_index=from_index, limit=limit)

    def get_ovas_and_specials(self, subtype: str = "ova", from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch OVAs and Specials."""
        stype = "OVA" if "ova" in subtype.lower() else "SPECIAL"
        return self.get_anime_list(filter_type="", filter_data="", anime_type=stype, from_index=from_index, limit=limit)

    def get_top_currently_airing(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch top currently airing anime."""
        return self.get_anime_list(filter_type="STATUS", filter_data="AIRING", anime_type="SERIES", from_index=from_index, limit=limit)

    def get_top_anime_mal(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch top rated anime."""
        return self.get_top_rated_anime(from_index, limit)

    def get_anime_list(
        self,
        filter_type: str = "",
        filter_data: str = "",
        anime_type: str = "SERIES",
        from_index: int = 0,
        limit: int = 30
    ) -> List[AnimeResult]:
        """Unified query dispatcher for generic Animeify lists."""
        endpoint = "anime/load_anime_list_v2.php"
        payload = {
            'UserId': '0',
            'Language': 'English',
            'FilterType': filter_type,
            'FilterData': filter_data,
            'Type': anime_type,
        }
        return self._paginate(endpoint, limit, from_index, payload)
