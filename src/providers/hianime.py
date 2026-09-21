"""
HiAnime English Anime Provider for ani-cli-arabic
Replaces AniDB following the upstream ani-cli v5.1 migration.
"""

import re
import json
import base64
import requests
from typing import List, Optional, Dict, Any
from .base import BaseAnimeProvider
from ..models import AnimeResult, Episode, QualityOption
from ..logger import logger

class HiAnimeProvider(BaseAnimeProvider):
    id = "hianime"
    name = "HiAnime"
    description = "English Anime Provider (Upstream ani-cli)"

    BASE_URL = "https://hianime.at"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    def _get(self, url: str) -> Optional[requests.Response]:
        try:
            return self.session.get(url, timeout=10)
        except Exception as e:
            logger.error("HIANIME", f"Request failed: {e}")
            return None

    def _parse_list(self, html: str) -> List[AnimeResult]:
        results = []
        seen = set()
        for m in re.finditer(r'<h3 class="film-name">\s*<a href="([^"]+)"\s*title="([^"]+)"', html):
            url = m.group(1).split("?")[0]
            slug = url.split("/")[-1]
            title = m.group(2).replace("&#039;", "'").replace("&quot;", '"').replace("&amp;", "&")
            if slug in seen:
                continue
            seen.add(slug)
            
            # Try to get thumbnail (optional, might need broader regex but keep it simple for now)
            # In HiAnime thumbnails are usually above the h3, let's just leave it empty if we can't extract easily.
            # Actually let's use a dummy or just empty for now, or match it better:
            
            results.append(AnimeResult(
                id=slug,
                title_en=title.strip(),
                title_ar=title.strip(),
                thumbnail="", 
                score="N/A",
                type="SERIES"
            ))
        return results

    def search_anime(self, query: str) -> List[AnimeResult]:
        resp = self._get(f"{self.BASE_URL}/search?keyword={query}")
        if not resp:
            return []
        # Exclude sidebar
        html = resp.text.split('id="main-sidebar"')[0]
        return self._parse_list(html)

    def get_anime_details(self, anime_id: str) -> AnimeResult:
        return AnimeResult(id=anime_id, title_en=anime_id.replace('-', ' ').title(), title_ar="", thumbnail="")

    def get_episodes(self, anime_id: str) -> List[Episode]:
        num_id = anime_id.split("-")[-1]
        resp = self._get(f"{self.BASE_URL}/api/theme/episode/list/{num_id}")
        if not resp or not resp.json().get('html'):
            return []
        html = resp.json().get('html')
        eps = []
        for m in re.finditer(r'data-number="([^"]+)"[\s\S]*?data-id="([0-9]+)"', html):
            eps.append(Episode(number=m.group(1), display_num=m.group(1), url=m.group(2)))
        return eps

    def get_streaming_servers(self, anime_id: str, episode_num: str, anime_type: str = "SERIES") -> Optional[Dict[str, Any]]:
        # In get_episodes, url holds the data-id
        # We just need to search our episodes for this num to get the data-id, but we are passed episode_num.
        # Wait, the CLI doesn't pass the episode object url to get_streaming_servers! It passes episode_num.
        # So we must fetch the episodes again to find the data-id, or we hack it by passing data-id as display_num? No.
        
        num_id = anime_id.split("-")[-1]
        resp = self._get(f"{self.BASE_URL}/api/theme/episode/list/{num_id}")
        if not resp: return None
        html = resp.json().get('html')
        data_id = None
        for m in re.finditer(r'data-number="([^"]+)"[\s\S]*?data-id="([0-9]+)"', html):
            if m.group(1) == episode_num or m.group(1).rstrip(".0") == episode_num:
                data_id = m.group(2)
                break
                
        if not data_id: return None
        
        servers_resp = self._get(f"{self.BASE_URL}/api/theme/episode/servers?episodeId={data_id}")
        if not servers_resp: return None
        
        shtml = servers_resp.json().get('html', '')
        
        # We need ZokoAnime hash for SUB or DUB
        # For simplicity, let's grab sub
        zoko_hash = None
        for m in re.finditer(r'data-type="([^"]+)".*?data-server-name="ZokoAnime".*?data-hash="([^"]+)"', shtml, flags=re.DOTALL | re.IGNORECASE):
            # Prefer sub, but take dub if it's the only one
            if m.group(1).lower() == "sub":
                zoko_hash = m.group(2)
                break
            zoko_hash = m.group(2)
            
        if not zoko_hash:
            return None
            
        embed_url = base64.b64decode(zoko_hash).decode('utf-8')
        embed_resp = self._get(embed_url)
        if not embed_resp: return None
        
        blob = re.search(r'window\.__P="([^"]+)"', embed_resp.text)
        if not blob: return None
        
        decoded = base64.b64decode(blob.group(1))
        key = b"otaku-embed-v1"
        output = bytearray()
        for i in range(len(decoded)):
            output.append(decoded[i] ^ key[i % len(key)])
            
        try:
            data = json.loads(output.decode('utf-8'))
        except Exception:
            return None
            
        m3u8 = data.get('src')
        if not m3u8: return None
        
        return {
            "CurrentEpisode": {"zoko": m3u8},
            "Qualities": [
                QualityOption("Auto", "zoko", "info", m3u8)
            ]
        }

    def get_episode_streams(self, episode: Episode) -> List[QualityOption]:
        return []

    def get_latest_episodes(self, limit: int = 20) -> List[AnimeResult]:
        return self._parse_list(self._get(f"{self.BASE_URL}/home").text if self._get(f"{self.BASE_URL}/home") else "")

    def get_pinned_anime(self, limit: int = 20) -> List[AnimeResult]:
        return self.get_latest_episodes()

    def get_trending_anime(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.get_latest_episodes()

    def get_top_rated_anime(self, from_index: int = 0, limit: int = 20, rate_tier: str = "") -> List[AnimeResult]:
        return self.get_latest_episodes()

    def get_movies(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.get_latest_episodes()

    def get_genre_anime(self, genre_slug: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.get_latest_episodes()

    def get_studio_anime(self, studio_name: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.get_latest_episodes()

    def get_anime_list(self, filter_type: str = "", filter_data: str = "", anime_type: str = "SERIES", from_index: int = 0, limit: int = 30) -> List[AnimeResult]:
        return self.get_latest_episodes()

