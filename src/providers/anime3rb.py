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
        results = self.api.search_anime(query)
        if results:
            return results
        # Fallback to Anime Slayer if Anime3rb is rate limited (HTTP 429) or empty
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            return slayer.search_anime(query)
        except Exception:
            return []

    def get_anime_details(self, anime_id: str) -> AnimeResult:
        aid = str(anime_id).strip()
        if aid.isdigit():
            try:
                from .manager import ProviderManager
                return ProviderManager.get_provider("anime_slayer").get_anime_details(aid)
            except Exception:
                pass

        res = self.api.get_anime_details(aid)
        if res and res.thumbnail and res.title_en and res.title_en != aid:
            return res
        # Fallback to Anime Slayer if Anime3rb is blocked/429
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            slayer_res = slayer.search_anime(aid.replace("-", " "))
            if slayer_res:
                return slayer.get_anime_details(slayer_res[0].id)
        except Exception:
            pass
        return res

    def get_episodes(self, anime_id: str) -> List[Episode]:
        aid = str(anime_id).strip()
        if aid.isdigit():
            try:
                from .manager import ProviderManager
                return ProviderManager.get_provider("anime_slayer").get_episodes(aid)
            except Exception:
                pass

        eps = self.api.get_episodes(aid)
        if eps:
            return eps
        # Fallback to Anime Slayer if Anime3rb is blocked/429
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            slayer_res = slayer.search_anime(aid.replace("-", " "))
            if slayer_res:
                return slayer.get_episodes(slayer_res[0].id)
        except Exception:
            pass
        return []

    def get_episode_streams(self, episode: Episode) -> List[QualityOption]:
        streams = self.api.get_episode_streams(episode)
        if streams:
            return streams
        
        # Cross-provider stream fallback
        try:
            from .manager import ProviderManager
            title = episode.title or ""
            if title:
                slayer = ProviderManager.get_provider("anime_slayer")
                slayer_results = slayer.search_anime(title)
                if slayer_results:
                    return slayer.get_streaming_servers(slayer_results[0].id, episode.number or "1").get("Qualities", [])
        except Exception:
            pass
        return []

    def get_streaming_servers(self, anime_id: str, episode_num: str, anime_type: str = "SERIES") -> Optional[Dict[str, Any]]:
        aid = str(anime_id).strip()
        if aid.isdigit():
            try:
                from .manager import ProviderManager
                return ProviderManager.get_provider("anime_slayer").get_streaming_servers(aid, episode_num, anime_type)
            except Exception:
                pass

        streams = self.api.get_streaming_servers(aid, episode_num, anime_type)
        if streams and streams.get("Qualities"):
            return streams
        
        # Smart Cross-Provider Fallback: Resolve via Anime Slayer by title
        try:
            from .manager import ProviderManager
            details = self.get_anime_details(aid)
            title = (details.title_en or details.title_ar or anime_id).strip()
            slayer = ProviderManager.get_provider("anime_slayer")
            slayer_results = slayer.search_anime(title)
            if slayer_results:
                best_match = slayer_results[0]
                fallback_streams = slayer.get_streaming_servers(best_match.id, episode_num, anime_type)
                if fallback_streams and fallback_streams.get("Qualities"):
                    return fallback_streams
        except Exception:
            pass

        return streams

    def get_latest_episodes(self, limit: int = 20) -> List[Episode]:
        raw_eps = self.api.get_latest_episodes(limit)
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
        if not results:
            try:
                from .manager import ProviderManager
                slayer = ProviderManager.get_provider("anime_slayer")
                return slayer.get_latest_episodes(limit)
            except Exception:
                pass
        return results

    def get_pinned_anime(self, limit: int = 20) -> List[AnimeResult]:
        items = self.api.get_pinned_anime(limit)
        if items:
            return items
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            return slayer.get_pinned_anime(limit)
        except Exception:
            return []

    def get_trending_anime(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        items = self.api.get_trending_anime(from_index, limit)
        if items:
            return items
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            return slayer.get_trending_anime(from_index, limit)
        except Exception:
            return []

    def get_top_rated_anime(self, from_index: int = 0, limit: int = 20, rate_tier: str = "9-10") -> List[AnimeResult]:
        items = self.api.get_top_rated_anime(from_index, limit, rate_tier)
        if items:
            return items
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            return slayer.get_top_rated_anime(from_index, limit)
        except Exception:
            return []

    def get_movies(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        items = self.api.get_movies(from_index, limit)
        if items:
            return items
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            return slayer.get_movies(from_index, limit)
        except Exception:
            return []

    def get_genre_anime(self, genre_slug: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        items = self.api.get_genre_anime(genre_slug, from_index, limit)
        if items:
            return items
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            return slayer.get_genre_anime(genre_slug, from_index, limit)
        except Exception:
            return []

    def get_studio_anime(self, studio_name: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        items = self.api.get_studio_anime(studio_name, from_index, limit)
        if items:
            return items
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            return slayer.get_studio_anime(studio_name, from_index, limit)
        except Exception:
            return []

    def get_seasonal_anime(self, season: str = None, year: int = None, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        items = self.api.get_seasonal_anime(season, year, from_index, limit)
        if items:
            return items
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            return slayer.get_seasonal_anime(season, year, from_index, limit)
        except Exception:
            return []

    def get_ovas_and_specials(self, category: str = "ova", from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        items = self.api.get_ovas_and_specials(category, from_index, limit)
        if items:
            return items
        try:
            from .manager import ProviderManager
            slayer = ProviderManager.get_provider("anime_slayer")
            return slayer.get_ovas_and_specials(category, from_index, limit)
        except Exception:
            return []

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
            return self.search_anime(filter_data)[from_index:from_index + limit]
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
        return self.api.get_anime_list(filter_type, filter_data, anime_type, from_index, limit)
