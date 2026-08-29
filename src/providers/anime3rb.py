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
    name: str = "Anime3rb (أنمي عرب)"
    description: str = "Fast browserless scraper with 1080p/720p/480p streams and rich metadata"

    def __init__(self, api: Optional[AnimeAPI] = None):
        self.api = api or AnimeAPI()

    def search_anime(self, query: str) -> List[AnimeResult]:
        return self.api.search_anime(query)

    def get_anime_details(self, anime_id: str) -> AnimeResult:
        return self.api.get_anime_details(anime_id)

    def get_episodes(self, anime_id: str) -> List[Episode]:
        return self.api.get_episodes(anime_id)

    def get_episode_streams(self, episode: Episode) -> List[QualityOption]:
        return self.api.get_episode_streams(episode)

    def get_streaming_servers(self, anime_id: str, episode_num: str, anime_type: str = "SERIES") -> Optional[Dict[str, Any]]:
        return self.api.get_streaming_servers(anime_id, episode_num, anime_type)

    def get_latest_episodes(self, limit: int = 20) -> List[Episode]:
        return self.api.get_latest_episodes(limit)

    def get_pinned_anime(self, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_pinned_anime(limit)

    def get_trending_anime(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_trending_anime(from_index, limit)

    def get_top_rated_anime(self, from_index: int = 0, limit: int = 20, rate_tier: str = "9-10") -> List[AnimeResult]:
        return self.api.get_top_rated_anime(from_index, limit, rate_tier)

    def get_movies(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_movies(from_index, limit)

    def get_genre_anime(self, genre_slug: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_genre_anime(genre_slug, from_index, limit)

    def get_studio_anime(self, studio_name: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_studio_anime(studio_name, from_index, limit)

    def get_seasonal_anime(self, season: str = None, year: int = None, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_seasonal_anime(season, year, from_index, limit)

    def get_ovas_and_specials(self, category: str = "ova", from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self.api.get_ovas_and_specials(category, from_index, limit)

    def get_anime_list(
        self,
        filter_type: str = "",
        filter_data: str = "",
        anime_type: str = "SERIES",
        from_index: int = 0,
        limit: int = 30
    ) -> List[AnimeResult]:
        return self.api.get_anime_list(filter_type, filter_data, anime_type, from_index, limit)
