"""
Base Anime Provider Interface for ani-cli-arabic
Defines the standard abstract contract for multi-provider support (Anime3rb, AnimeSlayer, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ..models import AnimeResult, Episode, QualityOption


class BaseAnimeProvider(ABC):
    """Abstract Base Class that every anime provider must implement."""

    id: str = "base"
    name: str = "Base Provider"
    description: str = "Base abstract anime provider"

    @abstractmethod
    def search_anime(self, query: str) -> List[AnimeResult]:
        """Search for anime by keyword or title."""
        pass

    @abstractmethod
    def get_anime_details(self, anime_id: str) -> AnimeResult:
        """Fetch rich metadata, synopsis, genre tags, and info for an anime."""
        pass

    @abstractmethod
    def get_episodes(self, anime_id: str) -> List[Episode]:
        """Fetch all available episodes for an anime."""
        pass

    @abstractmethod
    def get_episode_streams(self, episode: Episode) -> List[QualityOption]:
        """Extract all direct playable streaming links and resolutions (1080p, 720p, 480p) for an episode."""
        pass

    @abstractmethod
    def get_streaming_servers(self, anime_id: str, episode_num: str, anime_type: str = "SERIES") -> Optional[Dict[str, Any]]:
        """Extract direct CDN stream URLs and return mapped qualities for player/downloader."""
        pass

    @abstractmethod
    def get_latest_episodes(self, limit: int = 20) -> List[Episode]:
        """Fetch recent newly released episodes across all anime."""
        pass

    @abstractmethod
    def get_pinned_anime(self, limit: int = 20) -> List[AnimeResult]:
        """Fetch pinned / spotlight / top featured anime."""
        pass

    @abstractmethod
    def get_trending_anime(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch popular / trending anime."""
        pass

    @abstractmethod
    def get_top_rated_anime(self, from_index: int = 0, limit: int = 20, rate_tier: str = "9-10") -> List[AnimeResult]:
        """Fetch masterpiece / top rated anime."""
        pass

    @abstractmethod
    def get_movies(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime movies collection."""
        pass

    @abstractmethod
    def get_genre_anime(self, genre_slug: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime by genre category."""
        pass

    @abstractmethod
    def get_studio_anime(self, studio_name: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime produced by a studio."""
        pass

    @abstractmethod
    def get_anime_list(
        self,
        filter_type: str = "",
        filter_data: str = "",
        anime_type: str = "SERIES",
        from_index: int = 0,
        limit: int = 30
    ) -> List[AnimeResult]:
        """Unified query dispatcher for generic lists."""
        pass
