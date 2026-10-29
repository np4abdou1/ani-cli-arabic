"""
Stardima providers for ani-cli-arabic.

Two separate provider entries share this implementation:

* ``stardima``      -> dubbed anime
* ``stardima_kids`` -> dubbed cartoons / kids

The site itself is mostly a cartoon dub library, so the anime provider filters
the catalog with the precomputed TMDB classification cache.
"""

from __future__ import annotations

import re
import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .base import BaseAnimeProvider
from ..models import AnimeResult, Episode, QualityOption
from ..logger import logger
from .stardima_client import (
    StardimaClassifier,
    StardimaClient,
    StardimaExtractor,
)


# Backup-only MVP.  Flip to True to try Mixdrop / Uqload / Lulustream when a
# backup URL is missing or unreachable.
ENABLE_FALLBACKS = False

# Stardima's category slugs are brand-based, not genre-based.  Map the few
# genre names the UI exposes to the slugs that actually exist on the site.
GENRE_SLUG_MAP = {
    "action": "akshn",
    "adventure": "mghamrat",
    "ninja": "nynga",
    "anime": "anmy",
    "cartoon": "krton",
    "cartoons": "krton",
    "kids": "krton",
    "family": "aflam-aaayly",
    "movies": "aflam-aaayly",
}

_EPISODE_NUM_RE = re.compile(r"(?:ح|الحلقة|الحلقه|E|EP|Episode)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_number(value: Any) -> Any:
    number = _as_float(value)
    if number is None:
        return value
    if number.is_integer():
        return int(number)
    return number


def _videos_from_response(data: Any) -> List[Dict[str, Any]]:
    """Extract the list of video objects from the API's several envelopes."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []

    for key in ("videos", "data", "results", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            for nested_key in ("videos", "data", "results", "items"):
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]
    return []


def _pagination_from_response(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        pagination = data.get("pagination") or data.get("meta")
        if isinstance(pagination, dict):
            return pagination
    return {}


class StardimaProvider(BaseAnimeProvider):
    """Dubbed anime provider backed by Stardima."""

    id: str = "stardima"
    name: str = "Stardima Anime (Dub)"
    description: str = "Arabic dubbed anime with direct backup streams"

    content_scope: str = "anime"

    supported_features: Set[str] = {
        "search",
        "latest",
        "movies",
        "trending",
        "popular",
        "top_rated",
        "genres",
    }

    def __init__(
        self,
        client: Optional[StardimaClient] = None,
        classifier: Optional[StardimaClassifier] = None,
        extractor: Optional[StardimaExtractor] = None,
        settings: Optional[Any] = None,
    ):
        self.client = client or StardimaClient()
        self.classifier = classifier or StardimaClassifier()
        self.extractor = extractor or StardimaExtractor()
        self._settings = settings
        self._detail_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._episode_cache: Dict[str, Tuple[float, List[Episode], Dict[str, str]]] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Settings / scoping helpers
    # ------------------------------------------------------------------

    def _setting(self, key: str, default: Any = None) -> Any:
        if self._settings is not None:
            return self._settings.get(key, default)
        try:
            from ..settings import SettingsManager

            self._settings = SettingsManager()
            return self._settings.get(key, default)
        except Exception:
            return default

    def _refresh_settings(self) -> None:
        """Reload config.json so UI setting changes apply without a restart."""
        if self._settings is None:
            try:
                from ..settings import SettingsManager

                self._settings = SettingsManager()
            except Exception:
                return
            return
        reload = getattr(self._settings, "reload", None)
        if callable(reload):
            try:
                reload()
            except Exception:
                pass

    def _language(self) -> str:
        value = str(self._setting("stardima_language", "dub") or "dub").lower()
        return value if value in ("dub", "sub", "both") else "dub"

    def _include_unknown(self) -> bool:
        return bool(self._setting("stardima_include_unknown", False))

    def _in_scope(self, content_type: str) -> bool:
        return StardimaClassifier.matches_scope(
            content_type,
            self.content_scope,
            self._include_unknown(),
        )

    # ------------------------------------------------------------------
    # Caches
    # ------------------------------------------------------------------

    def _detail(self, anime_id: Any, force: bool = False) -> Optional[Dict[str, Any]]:
        key = str(anime_id).strip()
        if not key:
            return None
        now = time.time()
        with self._lock:
            cached = self._detail_cache.get(key)
            if cached and not force and now - cached[0] < 600:
                return cached[1]

        detail = self.client.video(key)
        if isinstance(detail, dict):
            with self._lock:
                self._detail_cache[key] = (now, detail)
            return detail
        return None

    def _invalidate(self, anime_id: Any) -> None:
        key = str(anime_id).strip()
        with self._lock:
            self._detail_cache.pop(key, None)
            self._episode_cache.pop(key, None)

    def refresh_anime_cache(self, anime_id: Any) -> None:
        """Drop cached detail/episodes so newly added episodes appear."""
        self._invalidate(anime_id)

    def _episode_data(
        self,
        anime_id: Any,
        force: bool = False,
    ) -> Tuple[List[Episode], Dict[str, str]]:
        key = str(anime_id).strip()
        now = time.time()
        with self._lock:
            cached = self._episode_cache.get(key)
            if cached and not force and now - cached[0] < 1800:
                return cached[1], cached[2]

        detail = self._detail(key, force=force)
        if not detail:
            return [], {}

        poster = str(detail.get("poster_url") or detail.get("background_url") or "")
        is_movie = str(detail.get("type") or "").lower() == "movie"

        if is_movie:
            episode = Episode(
                number="1",
                type="Movie",
                display_num=1,
                title=str(detail.get("title") or "Movie"),
                duration="",
                thumbnail=poster,
                url=str(detail.get("id") or key),
                anime_id=key,
            )
            mapping = {"1": episode.url}
            with self._lock:
                self._episode_cache[key] = (now, [episode], mapping)
            return [episode], mapping

        raw_episodes: List[Dict[str, Any]] = []
        for season in detail.get("seasons") or []:
            if not isinstance(season, dict):
                continue
            season_id = season.get("id")
            if season_id is None:
                continue
            page = 1
            season_items: List[Dict[str, Any]] = []
            while page <= 20:
                response = self.client.episodes(season_id, page=page, per_page=100)
                items = _videos_from_response(response)
                if not items:
                    break
                season_items.extend(items)
                total = response.get("total") if isinstance(response, dict) else None
                if total is not None and len(season_items) >= int(total):
                    break
                if len(items) < 100:
                    break
                page += 1
            raw_episodes.extend(season_items)

        # Keep a stable order before assigning fallback numbers.
        raw_episodes.sort(
            key=lambda item: (
                _as_float(item.get("season_number")) or 0,
                _as_float(item.get("episode_number")) or 0,
                str(item.get("id") or ""),
            )
        )

        # Some series use global episode numbers (Naruto, Mashle), while
        # long-running cartoons reset the number every season (SpongeBob).
        # Keep raw numbers when they are globally unique; otherwise flatten
        # to a stable 1..N index.  The title still carries the S/E label.
        prepared: List[Tuple[Dict[str, Any], Any]] = []
        seen_ids = set()
        for index, item in enumerate(raw_episodes, start=1):
            episode_id = item.get("id")
            if episode_id is None or episode_id in seen_ids:
                continue
            seen_ids.add(episode_id)

            title = str(item.get("title") or "").strip()
            number = _as_number(item.get("episode_number"))
            title_match = _EPISODE_NUM_RE.search(title)
            if title_match:
                number = _as_number(title_match.group(1))
            if number is None:
                number = index
            prepared.append((item, number))

        raw_numbers = [number for _, number in prepared]
        use_raw_numbers = len(set(raw_numbers)) == len(raw_numbers)

        episodes: List[Episode] = []
        mapping: Dict[str, str] = {}
        for index, (item, raw_number) in enumerate(prepared, start=1):
            episode_id = item.get("id")
            number = raw_number if use_raw_numbers else index
            number_str = str(number)
            title = str(item.get("title") or "").strip()
            episode = Episode(
                number=number_str,
                type="Episode",
                display_num=number,
                title=title or f"Episode {number_str}",
                duration=str(item.get("duration") or ""),
                thumbnail=poster,
                url=str(episode_id),
                anime_id=key,
            )
            episodes.append(episode)
            mapping[number_str] = str(episode_id)

        with self._lock:
            self._episode_cache[key] = (now, episodes, mapping)
        return episodes, mapping

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _map_anime(self, video: Dict[str, Any], detail: Optional[Dict[str, Any]] = None) -> AnimeResult:
        detail = detail or {}
        video_id = str(video.get("id") or detail.get("id") or "")
        title_ar = str(video.get("title") or detail.get("title") or "")
        cached_title = self.classifier.title_en(video_id)
        title_en = cached_title or title_ar
        original_name = self.classifier.original_name(video_id)
        quality = video.get("video_quality") or detail.get("video_quality") or ""
        content_type = self.classifier.classify(video_id, detail or video)

        is_movie = (
            video.get("is_series") is False
            or str(video.get("type") or detail.get("type") or "").lower() == "movie"
        )
        anime_type = "MOVIE" if is_movie else "SERIES"

        categories = video.get("category") or detail.get("category") or []
        genres = ", ".join(
            str(category.get("name") or "")
            for category in categories
            if isinstance(category, dict) and category.get("name")
        ) or "N/A"

        review_stats = detail.get("review_stats") or {}
        score: Any = review_stats.get("average") if isinstance(review_stats, dict) else None
        if not score:
            score = video.get("video_rating") or self.classifier.vote(video_id)
        if not score:
            score = "N/A"

        episodes_value = "1" if is_movie else "N/A"

        return AnimeResult(
            id=video_id,
            title_en=title_en,
            title_ar=title_ar,
            title_jp=original_name,
            title_romaji=original_name,
            type=anime_type,
            episodes=episodes_value,
            status=str(video.get("status_text") or detail.get("status_text") or "N/A"),
            genres=genres,
            score=str(score),
            premiered=str(video.get("year") or detail.get("year") or "N/A"),
            thumbnail=str(video.get("poster_url") or detail.get("poster_url") or ""),
            synopsis=str(video.get("description") or detail.get("description") or ""),
            language=self.classifier.language_of(quality),
            content_type=content_type,
        )

    # ------------------------------------------------------------------
    # Browse / search
    # ------------------------------------------------------------------

    def search_anime(self, query: str) -> List[AnimeResult]:
        self._refresh_settings()
        query = (query or "").strip()
        if not query:
            return []

        language = self._language()
        results: List[AnimeResult] = []
        seen = set()
        for page in range(1, 4):
            response = self.client.search(
                query=query,
                language=None if language == "both" else language,
                page=page,
                per_page=50,
            )
            videos = _videos_from_response(response)
            if not videos:
                break
            for video in videos:
                anime = self._map_anime(video)
                if not anime.id or anime.id in seen:
                    continue
                if not self._in_scope(anime.content_type):
                    continue
                if language in ("dub", "sub") and anime.language != language:
                    continue
                seen.add(anime.id)
                results.append(anime)
            if len(results) >= 30:
                break
            pagination = _pagination_from_response(response)
            last_page = _as_float(pagination.get("last_page"))
            if last_page and page >= last_page:
                break
        return results

    def _browse_option(
        self,
        option_type: str,
        from_index: int = 0,
        limit: int = 20,
        pages: int = 5,
        sort_by_vote: bool = False,
    ) -> List[AnimeResult]:
        self._refresh_settings()
        language = self._language()
        results: List[AnimeResult] = []
        seen = set()
        for page in range(1, pages + 1):
            response = self.client.search_by_option(
                option_type,
                page=page,
                per_page=30,
            )
            videos = _videos_from_response(response)
            if not videos:
                break
            for video in videos:
                anime = self._map_anime(video)
                if not anime.id or anime.id in seen:
                    continue
                if not self._in_scope(anime.content_type):
                    continue
                if language in ("dub", "sub") and anime.language != language:
                    continue
                seen.add(anime.id)
                results.append(anime)
            pagination = _pagination_from_response(response)
            last_page = _as_float(pagination.get("last_page"))
            if last_page and page >= last_page:
                break
            if len(results) >= from_index + limit + 10:
                break

        if sort_by_vote:
            results.sort(key=lambda anime: self.classifier.vote(anime.id), reverse=True)
        return results[from_index : from_index + limit]

    def _browse_search(
        self,
        from_index: int = 0,
        limit: int = 20,
        media: Optional[str] = None,
        categories: Optional[Iterable[str]] = None,
        pages: int = 5,
    ) -> List[AnimeResult]:
        self._refresh_settings()
        language = self._language()
        results: List[AnimeResult] = []
        seen = set()
        for page in range(1, pages + 1):
            response = self.client.search(
                language=None if language == "both" else language,
                media=media,
                categories=categories,
                page=page,
                per_page=50,
            )
            videos = _videos_from_response(response)
            if not videos:
                break
            for video in videos:
                anime = self._map_anime(video)
                if not anime.id or anime.id in seen:
                    continue
                if not self._in_scope(anime.content_type):
                    continue
                if language in ("dub", "sub") and anime.language != language:
                    continue
                seen.add(anime.id)
                results.append(anime)
            pagination = _pagination_from_response(response)
            last_page = _as_float(pagination.get("last_page"))
            if last_page and page >= last_page:
                break
            if len(results) >= from_index + limit + 10:
                break
        return results[from_index : from_index + limit]

    # ------------------------------------------------------------------
    # Details / episodes
    # ------------------------------------------------------------------

    def get_anime_details(self, anime_id: str) -> AnimeResult:
        key = str(anime_id).strip()
        detail = self._detail(key)
        if not detail:
            return AnimeResult(id=key, title_en=key, title_ar=key)
        return self._map_anime(detail, detail)

    def get_episodes(self, anime_id: str) -> List[Episode]:
        episodes, _ = self._episode_data(anime_id)
        return episodes

    # ------------------------------------------------------------------
    # Streams
    # ------------------------------------------------------------------

    def _find_episode(self, episodes: List[Episode], episode_num: Any) -> Optional[Episode]:
        target = str(episode_num).strip()
        for episode in episodes:
            if str(episode.number) == target or str(episode.display_num) == target or str(episode.url) == target:
                return episode

        target_float = _as_float(target)
        if target_float is not None:
            for episode in episodes:
                if _as_float(episode.display_num) == target_float:
                    return episode
        return None

    def _fallback(
        self,
        servers: List[Dict[str, Any]],
    ) -> Tuple[Optional[str], Dict[str, str]]:
        for server in servers:
            label = str(server.get("label") or "").lower()
            url = str(server.get("url") or "").strip()
            if not url.startswith("http"):
                continue
            if "mixdrop" in label:
                result = self.extractor.mixdrop(url)
                if result:
                    return result
            if "uqload" in label or "lulustream" in label:
                result = self.extractor.hls_from_page(url, url)
                if result:
                    return result
        return None, {}

    def get_streaming_servers(
        self,
        anime_id: str,
        episode_num: str,
        anime_type: str = "SERIES",
    ) -> Optional[Dict[str, Any]]:
        key = str(anime_id).strip()
        detail = self._detail(key)
        if not detail:
            return None

        is_movie = (
            str(detail.get("type") or "").lower() == "movie"
            or str(anime_type).upper() == "MOVIE"
        )
        if is_movie:
            servers = detail.get("servers") or []
            episode_label = "Movie"
        else:
            episodes, _ = self._episode_data(key)
            episode = self._find_episode(episodes, episode_num)
            if not episode:
                episodes, _ = self._episode_data(key, force=True)
                episode = self._find_episode(episodes, episode_num)
            if not episode:
                logger.debug(
                    "STARDIMA",
                    f"Episode {episode_num} not found for video {key}.",
                )
                return None
            servers = self.client.servers(episode.url)
            episode_label = f"Episode {episode.display_num}"

        if not isinstance(servers, list):
            servers = []
        servers = [server for server in servers if isinstance(server, dict)]
        if not servers:
            return None

        extracted_servers: List[Dict[str, Any]] = []
        if hasattr(self.extractor, "extract_all"):
            extracted_servers = self.extractor.extract_all(servers)
        else:
            backup = self.extractor.backup_url(servers)
            if backup and self.extractor.verify(backup):
                extracted_servers.append({
                    "label": "Backup",
                    "url": backup,
                    "headers": {},
                    "res": self.extractor.guess_res(backup),
                    "server_key": "FRFhdQ",
                })
            elif ENABLE_FALLBACKS:
                fb_url, fb_headers = self._fallback(servers)
                if fb_url:
                    extracted_servers.append({
                        "label": "Direct",
                        "url": fb_url,
                        "headers": fb_headers,
                        "res": self.extractor.guess_res(fb_url),
                        "server_key": "FRFhdQ",
                    })

        if not extracted_servers:
            logger.debug(
                "STARDIMA",
                f"No playable direct URL for video {key} ({episode_label}).",
            )
            return None

        language = self.classifier.language_of(detail.get("video_quality"))
        audio_lang = "ara,ar" if language == "dub" else ("jpn,ja" if language == "sub" else "")

        qualities: List[QualityOption] = []
        current_episode: Dict[str, str] = {}
        direct_streams: Dict[str, str] = {}

        inspect_fn = getattr(self.extractor, "inspect_resolution", None)
        guess_ext_fn = getattr(self.extractor, "guess_ext", StardimaExtractor.guess_ext)
        guess_res_fn = getattr(self.extractor, "guess_res", StardimaExtractor.guess_res)

        for s in extracted_servers:
            stream_url = s["url"]
            label = s["label"]
            headers = s.get("headers") or {}
            res = s.get("res")
            if not res or res == "Auto":
                if inspect_fn:
                    res = inspect_fn(stream_url, headers=headers)
                else:
                    res = guess_res_fn(stream_url)
            if not res or res == "Auto":
                res = "720p"

            ext = guess_ext_fn(stream_url)
            key_name = s.get("server_key") or label.replace(" ", "_")

            name = f"{res} • {label}"
            quality = QualityOption(
                name=name,
                server_key=key_name,
                style="info",
                direct_url=stream_url,
                res=res,
                headers=headers,
                audio_lang=audio_lang,
                ext=ext,
            )
            qualities.append(quality)
            current_episode[key_name] = stream_url
            if res not in direct_streams:
                direct_streams[res] = stream_url

        primary_url = qualities[0].direct_url
        current_episode.setdefault("FRFhdQ", primary_url)
        current_episode.setdefault("FRLink", primary_url)
        current_episode.setdefault("FRLowQ", primary_url)

        return {
            "CurrentEpisode": current_episode,
            "Qualities": qualities,
            "DirectStreams": direct_streams,
        }

    def get_episode_streams(self, episode: Episode) -> List[QualityOption]:
        anime_id = getattr(episode, "anime_id", "") or ""
        episode_num = getattr(episode, "number", "1")
        if not anime_id:
            return []
        data = self.get_streaming_servers(anime_id, episode_num)
        if not data:
            return []
        return list(data.get("Qualities") or [])

    # ------------------------------------------------------------------
    # Discovery rails
    # ------------------------------------------------------------------

    def get_latest_episodes(self, limit: int = 20) -> List[Episode]:
        self._refresh_settings()
        language = self._language()
        results: List[Episode] = []
        seen = set()

        for page in range(1, 6):
            response = self.client.latest_episodes(page=page, per_page=100)
            videos = _videos_from_response(response)
            if not videos:
                break
            for video in videos:
                video_id = str(video.get("id") or video.get("video_episode") or "")
                if not video_id:
                    continue
                quality = str(video.get("video_quality") or "")
                if language == "dub" and "مدبلج" not in quality:
                    continue
                if language == "sub" and "مترجم" not in quality:
                    continue
                if not self._in_scope(self.classifier.classify(video_id)):
                    continue

                number = _as_number(video.get("episode_number"))
                if number is None:
                    continue
                season_number = video.get("season_number")
                dedupe_key = (video_id, str(season_number), str(number))
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                series_title = str(video.get("series_title") or video.get("title") or "")
                results.append(
                    Episode(
                        number=str(number),
                        type="Episode",
                        display_num=number,
                        title=series_title or f"Episode {number}",
                        duration="",
                        thumbnail=str(video.get("poster_url") or ""),
                        url=str(video.get("episode_id") or video_id),
                        anime_id=video_id,
                    )
                )
                if len(results) >= limit:
                    return results

            pagination = _pagination_from_response(response)
            last_page = _as_float(pagination.get("last_page"))
            if last_page and page >= last_page:
                break
        return results

    def get_pinned_anime(self, limit: int = 20) -> List[AnimeResult]:
        return self._browse_option("trending", 0, limit, pages=3)

    def get_trending_anime(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self._browse_option("trending", from_index, limit, pages=5)

    def get_top_rated_anime(
        self,
        from_index: int = 0,
        limit: int = 20,
        rate_tier: str = "9-10",
    ) -> List[AnimeResult]:
        return self._browse_option(
            "trending",
            from_index,
            limit,
            pages=5,
            sort_by_vote=True,
        )

    def get_movies(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        return self._browse_search(
            from_index,
            limit,
            media="movies",
            pages=4,
        )

    def get_genre_anime(
        self,
        genre_slug: str,
        from_index: int = 0,
        limit: int = 20,
    ) -> List[AnimeResult]:
        slug = str(genre_slug or "").strip().lower()
        slug = GENRE_SLUG_MAP.get(slug, slug)
        if not slug:
            return []
        return self._browse_search(
            from_index,
            limit,
            categories=[slug],
            pages=3,
        )

    def get_studio_anime(
        self,
        studio_name: str,
        from_index: int = 0,
        limit: int = 20,
    ) -> List[AnimeResult]:
        return []

    def get_anime_list(
        self,
        filter_type: str = "",
        filter_data: str = "",
        anime_type: str = "SERIES",
        from_index: int = 0,
        limit: int = 30,
    ) -> List[AnimeResult]:
        filter_key = str(filter_type or "").upper()
        if filter_key == "SEARCH":
            return self.search_anime(filter_data)[from_index : from_index + limit]
        if filter_key == "GENRE":
            return self.get_genre_anime(filter_data, from_index, limit)
        if filter_key in ("MOVIE", "MOVIES"):
            return self.get_movies(from_index, limit)
        if filter_key in ("TRENDING", "POPULAR"):
            return self.get_trending_anime(from_index, limit)
        if filter_key in ("TOP_RATED", "TOPRATED"):
            return self.get_top_rated_anime(from_index, limit)
        if filter_key == "PINNED":
            return self.get_pinned_anime(limit)
        if filter_data:
            return self.search_anime(filter_data)[from_index : from_index + limit]
        return self.get_trending_anime(from_index, limit)


class StardimaKidsProvider(StardimaProvider):
    """Dubbed cartoon / kids provider backed by Stardima."""

    id: str = "stardima_kids"
    name: str = "Stardima Kids (Cartoon)"
    description: str = "Arabic dubbed cartoons for kids with direct backup streams"

    content_scope: str = "cartoon"
