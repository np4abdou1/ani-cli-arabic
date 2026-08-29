"""
Anime3rb Provider Implementation
Self-contained, TLS-impersonated scraper for Anime3rb.
"""

from typing import List, Optional, Dict, Any

from .base import BaseAnimeProvider
from ..models import AnimeResult, Episode, QualityOption
from ..api import AnimeAPI


class Anime3rbProvider(BaseAnimeProvider):
    """Anime3rb Provider delivering high-speed multi-quality streams and rich Arabic/English metadata."""

    id: str = "anime3rb"
    name: str = "Anime3rb"
    description: str = "Official web provider for Anime3rb (أنمي بالترجمة والدبلجة العربية)"

    def __init__(self, api: Optional[AnimeAPI] = None):
        self.api = api or AnimeAPI()

    def search_anime(self, query: str) -> List[AnimeResult]:
        return self.api.search_anime(query) or []

    def get_anime_details(self, anime_id: str) -> AnimeResult:
        return self.api.get_anime_details(str(anime_id).strip())

    def get_episodes(self, anime_id: str) -> List[Episode]:
        return self.api.get_episodes(str(anime_id).strip()) or []

    def get_episode_streams(self, episode: Episode) -> List[QualityOption]:
        return self.api.get_episode_streams(episode) or []

    def get_streaming_servers(self, anime_id: str, episode_num: str, anime_type: str = "SERIES") -> Optional[Dict[str, Any]]:
        return self.api.get_streaming_servers(str(anime_id).strip(), str(episode_num), anime_type)

    def get_latest_episodes(self, limit: int = 20) -> List[Episode]:
        raw_eps = self.api.get_latest_episodes(limit) or []
        results = []
        for it in raw_eps:
            if isinstance(it, dict):
                results.append(Episode(
                    number=str(it.get("ep_num", 1)),
                    display_num=int(it.get("ep_num", 1)),
                    title=it.get("title", ""),
                    thumbnail=it.get("thumbnail", ""),
                    url=it.get("url", "")
                ))
            elif isinstance(it, Episode):
                results.append(it)
        return results

    def get_pinned_anime(self, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_pinned_anime(limit) or []

    def get_trending_anime(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_trending_anime(from_index, limit) or []

    def get_top_rated_anime(self, from_index: int = 0, limit: int = 20, rate_tier: str = "9-10") -> List[AnimeResult]:
        return self.api.get_top_rated_anime(from_index, limit, rate_tier) or []

    def get_movies(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_movies(from_index, limit) or []

    def get_genre_anime(self, genre_slug: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_genre_anime(genre_slug, from_index, limit) or []

    def get_studio_anime(self, studio_name: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_studio_anime(studio_name, from_index, limit) or []

    def get_seasonal_anime(self, season: str = None, year: int = None, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_seasonal_anime(season, year, from_index, limit) or []

    def get_ovas_and_specials(self, category: str = "ova", from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_ovas_and_specials(category, from_index, limit) or []

    def get_anime_list(
        self,
        filter_type: str = "",
        filter_data: str = "",
        anime_type: str = "SERIES",
        from_index: int = 0,
        limit: int = 30
    ) -> List[AnimeResult]:
        ftype = (filter_type or "").upper()
        if ftype == "SEARCH":
            return (self.search_anime(filter_data) or [])[from_index:from_index + limit]
        elif ftype == "GENRE":
            return self.get_genre_anime(filter_data, from_index, limit)
        elif ftype in ("STUDIOS", "STUDIO"):
            return self.get_studio_anime(filter_data, from_index, limit)
        elif ftype == "MOVIE":
            return self.get_movies(from_index, limit)
        elif ftype == "TOP_RATED":
            return self.get_top_rated_anime(from_index, limit)
        elif ftype == "TRENDING":
            return self.get_trending_anime(from_index, limit)
        elif ftype == "SEASONAL":
            return self.get_seasonal_anime(None, None, from_index, limit)
        elif ftype == "OVA":
            return self.get_ovas_and_specials("ova", from_index, limit)
        elif ftype == "SPECIAL":
            return self.get_ovas_and_specials("special", from_index, limit)
        return self.api.get_anime_list(filter_type, filter_data, anime_type, from_index, limit) or []

