"""
AniDB English Anime Provider for ani-cli-arabic
Reverse-engineered engine based on pystardust/ani-cli and anidb.app
Supports English Sub and English Dub tracks, multi-resolution adaptive HLS streams (1080p, 720p, 480p, 360p),
and complete discovery filters (trending, top rated, popular, movies, genres, seasonal, etc.).
"""

import re
import json
import threading
import urllib.parse
from typing import List, Optional, Dict, Any
import requests

from .base import BaseAnimeProvider
from ..models import AnimeResult, Episode, QualityOption
from ..logger import logger


ANIDB_GENRE_MAP: Dict[str, str] = {
    "action": "1",
    "adventure": "3",
    "avant-garde": "19",
    "award-winning": "12",
    "boys-love": "16",
    "comedy": "5",
    "drama": "2",
    "ecchi": "13",
    "erotica": "17",
    "fantasy": "4",
    "girls-love": "20",
    "gourmet": "8",
    "hentai": "15",
    "horror": "21",
    "mystery": "7",
    "romance": "14",
    "sci-fi": "6",
    "slice-of-life": "9",
    "sports": "11",
    "supernatural": "10",
    "suspense": "18",
    # Arabic / slug aliases
    "shounen": "1",
    "shojo": "14",
    "isekai": "4",
    "magic": "4",
    "martial-arts": "1",
    "military": "1",
    "psychological": "18",
    "school": "9",
}


class AniDBProvider(BaseAnimeProvider):
    """
    AniDB / ani-cli English Anime Provider.
    Extracts English Sub and English Dub video streams from anidb.app.
    """

    id: str = "anidb"
    name: str = "AniDB (English)"
    description: str = "English Sub & Dub anime provider powered by the ani-cli / AniDB engine"

    BASE_URL: str = "https://anidb.app"
    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(self):
        self._local = threading.local()
        self._cache_lock = threading.Lock()
        self._anime_cache: Dict[str, AnimeResult] = {}
        self._episode_cache: Dict[str, List[Episode]] = {}

    @property
    def session(self) -> requests.Session:
        """Thread-local requests session."""
        if not hasattr(self._local, "session"):
            s = requests.Session()
            s.headers.update({
                "User-Agent": self.DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })
            self._local.session = s
        return self._local.session

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 12) -> Optional[requests.Response]:
        """Safe HTTP GET with graceful error handling."""
        try:
            full_url = url if url.startswith("http") else f"{self.BASE_URL}/{url.lstrip('/')}"
            resp = self.session.get(full_url, params=params, timeout=timeout)
            if resp.status_code == 200:
                return resp
            logger.warning(f"[AniDB] GET {full_url} returned status {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"[AniDB] Request error on {url}: {e}")
            return None

    def _extract_anime_cards(self, html: str) -> List[AnimeResult]:
        """Extract anime cards from anidb browse HTML."""
        if not html:
            return []

        results: List[AnimeResult] = []
        seen_ids = set()

        card_matches = re.findall(
            r'<a[^>]+href=[\"\'](?:https://anidb\.app)?/anime/([^\"]+)[\"\'][^>]*title=[\"\']([^\"]+)[\"\']',
            html
        )

        for slug, title in card_matches:
            slug = slug.strip()
            if not slug or slug in seen_ids:
                continue
            seen_ids.add(slug)

            clean_title = (
                title.replace("&#039;", "'")
                .replace("&quot;", '"')
                .replace("&amp;", "&")
                .strip()
            )

            num_id = slug.split("-")[-1] if "-" in slug else slug
            poster = f"https://cdn.xlsbox.com/poster/small/1782735600/{num_id}.jpg"

            results.append(AnimeResult(
                id=slug,
                title_en=clean_title,
                title_ar=clean_title,
                thumbnail=poster,
                score="N/A",
                type="TV"
            ))

        return results

    def search_anime(self, query: str) -> List[AnimeResult]:
        """Search for anime by keyword or title on AniDB."""
        if not query or not query.strip():
            return []

        query = query.strip()
        resp = self._get("browse", params={"q": query})
        if not resp:
            return []

        results = self._extract_anime_cards(resp.text)
        if not results and query:
            resp_alt = self._get("browse", params={"q": query.replace("-", " ")})
            if resp_alt:
                results = self._extract_anime_cards(resp_alt.text)

        return results

    def get_anime_details(self, anime_id: str) -> AnimeResult:
        """Fetch complete anime details and metadata from AniDB."""
        aid = str(anime_id).strip()
        with self._cache_lock:
            if aid in self._anime_cache:
                return self._anime_cache[aid]

        slug = aid
        if aid.isdigit():
            search_hits = self.search_anime(aid)
            if search_hits:
                slug = search_hits[0].id

        resp = self._get(f"anime/{slug}")
        if not resp:
            return AnimeResult(id=slug, title_en=slug, thumbnail="")

        html = resp.text

        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        title_en = title_match.group(1).strip() if title_match else slug

        poster_match = re.search(r'<img[^>]+src=[\"\']([^\"]+poster[^\"]+)[\"\']', html)
        poster = poster_match.group(1) if poster_match else ""

        mal_match = re.search(r'myanimelist\.net/anime/(\d+)', html)
        mal_id = mal_match.group(1) if mal_match else "0"

        score_match = re.search(r'viewBox=\"0 0 20 20\"[^\>]*>.*?<\/svg>\s*([\d\.]+)', html, re.DOTALL)
        score = score_match.group(1).strip() if score_match else "N/A"

        desc_match = re.search(r'<meta name=[\"\']description[\"\'] content=[\"\']([^\"]+)[\"\']', html)
        synopsis = desc_match.group(1).strip() if desc_match else ""

        genres_list = re.findall(r'href=[\"\']/browse\?genres=\d+[\"\'][^>]*>([^<]+)</a>', html)
        genres_str = ", ".join(genres_list) if genres_list else "N/A"

        badges = re.findall(r'<span[^>]*class=[\"\'][^\"]*badge[^\"]*[\"\'][^>]*>(.*?)</span>', html, re.DOTALL)
        clean_badges = [re.sub(r'<[^>]+>', '', b).strip() for b in badges if re.sub(r'<[^>]+>', '', b).strip()]
        atype = clean_badges[0] if clean_badges else "TV"
        status = clean_badges[1] if len(clean_badges) > 1 else "Finished Airing"

        res = AnimeResult(
            id=slug,
            title_en=title_en,
            title_ar=title_en,
            thumbnail=poster,
            score=score,
            genres=genres_str,
            mal_id=mal_id,
            type=atype,
            status=status,
            synopsis=synopsis
        )

        with self._cache_lock:
            self._anime_cache[slug] = res
            self._anime_cache[aid] = res

        return res

    def get_episodes(self, anime_id: str) -> List[Episode]:
        """Fetch all available episodes for an anime from AniDB API."""
        aid = str(anime_id).strip()
        with self._cache_lock:
            if aid in self._episode_cache:
                return self._episode_cache[aid]

        num_id = aid.split("-")[-1] if "-" in aid else aid

        resp = self._get(f"api/frontend/anime/{num_id}/episodes")
        if not resp:
            details = self.get_anime_details(aid)
            if details.id != aid:
                num_id = details.id.split("-")[-1]
                resp = self._get(f"api/frontend/anime/{num_id}/episodes")

        if not resp:
            return []

        try:
            data = resp.json()
            raw_list = data.get("episodes", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            episodes = []

            for it in raw_list:
                ep_id = str(it.get("id") or "")
                num_raw = it.get("number") or 1
                try:
                    ep_num = int(float(str(num_raw)))
                except ValueError:
                    ep_num = 1

                episodes.append(Episode(
                    number=str(ep_num),
                    display_num=ep_num,
                    title=f"Episode {ep_num}",
                    url=ep_id,
                    servers=[{"episode_id": ep_id, "number": ep_num}]
                ))

            episodes.sort(key=lambda x: x.display_num)
            with self._cache_lock:
                self._episode_cache[aid] = episodes
                self._episode_cache[num_id] = episodes
            return episodes
        except Exception as e:
            logger.error(f"[AniDB] Error parsing episodes JSON for {aid}: {e}")
            return []

    def _resolve_master_m3u8(self, master_url: str) -> List[tuple]:
        """Fetch master M3U8 and parse available resolutions and direct child playlist URLs."""
        try:
            resp = self.session.get(master_url, timeout=8)
            if resp.status_code != 200:
                return [("Auto", master_url)]

            lines = resp.text.strip().splitlines()
            qualities = []
            curr_res = "Auto"

            for line in lines:
                line = line.strip()
                if line.startswith("#EXT-X-STREAM-INF"):
                    m = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
                    if m:
                        height = m.group(2)
                        curr_res = f"{height}p"
                elif line.startswith("http") or line.endswith(".m3u8"):
                    stream_url = line if line.startswith("http") else master_url.rsplit("/", 1)[0] + "/" + line
                    qualities.append((curr_res, stream_url))
                    curr_res = "Auto"

            if not qualities:
                qualities.append(("Auto", master_url))

            return qualities
        except Exception as e:
            logger.warning(f"[AniDB] Failed to resolve master m3u8 {master_url}: {e}")
            return [("Auto", master_url)]

    def get_episode_streams(self, episode: Episode) -> List[QualityOption]:
        """
        Extract English Dub and Japanese Sub HLS streams for an episode.
        """
        ep_id = episode.url
        if not ep_id and episode.servers:
            ep_id = str(episode.servers[0].get("episode_id", ""))

        if not ep_id:
            return []

        resp = self._get(f"api/frontend/episode/{ep_id}/languages")
        if not resp:
            return []

        try:
            data = resp.json()
            languages = data.get("languages", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        except Exception:
            return []

        qualities: List[QualityOption] = []
        res_rank = {"1080p": 4, "720p": 3, "480p": 2, "360p": 1, "Auto": 0}

        for lang in languages:
            code = (lang.get("code") or lang.get("language") or "sub").lower()
            name = lang.get("name") or ("English Dub" if "eng" in code else "Japanese Sub")
            embed_url = lang.get("embed_url") or lang.get("url") or ""

            if not embed_url:
                continue

            try:
                r_embed = self.session.get(embed_url, timeout=8)
                if r_embed.status_code != 200:
                    continue

                m3u8_matches = re.findall(r"file:\s*['\"]([^'\"]+)['\"]", r_embed.text)
                if not m3u8_matches:
                    continue

                master_m3u8 = m3u8_matches[0]
                parsed_streams = self._resolve_master_m3u8(master_m3u8)

                for res_label, stream_url in parsed_streams:
                    display_name = f"{name} > {res_label}"
                    qualities.append(QualityOption(
                        name=display_name,
                        server_key=res_label,
                        direct_url=stream_url,
                        res=res_label
                    ))
            except Exception as e:
                logger.warning(f"[AniDB] Error resolving embed {embed_url}: {e}")

        # Sort: English Dub / Japanese Sub grouped with 1080p at top
        qualities.sort(key=lambda q: (1 if "Dub" in q.name else 0, res_rank.get(q.resolution, 0)), reverse=True)
        return qualities

    def get_streaming_servers(self, anime_id: str, episode_num: str, anime_type: str = "SERIES") -> Optional[Dict[str, Any]]:
        """Extract direct CDN stream URLs and return mapped qualities for player and downloader."""
        episodes = self.get_episodes(anime_id)
        if not episodes:
            return None

        # Find target episode matching episode_num
        target_ep = None
        target_raw = str(episode_num).strip()
        num_digits = re.search(r"\d+", target_raw)
        target_int = int(num_digits.group(0)) if num_digits else 1

        for ep in episodes:
            if str(ep.number) == target_raw or str(ep.display_num) == target_raw or ep.display_num == target_int:
                target_ep = ep
                break

        if not target_ep:
            target_ep = episodes[0]

        streams = self.get_episode_streams(target_ep)
        if not streams:
            return None

        current_ep: Dict[str, str] = {}
        qualities = []

        for s in streams:
            res = s.resolution or "720p"
            if "1080" in res and "FRFhdQ" not in current_ep:
                current_ep["FRFhdQ"] = s.url
            elif "720" in res and "FRLink" not in current_ep:
                current_ep["FRLink"] = s.url
            elif ("480" in res or "360" in res) and "FRLowQ" not in current_ep:
                current_ep["FRLowQ"] = s.url

            qualities.append(s)

        if not current_ep and streams:
            current_ep["FRLink"] = streams[0].url

        return {
            "current_ep": current_ep,
            "Qualities": qualities
        }

    def get_latest_episodes(self, limit: int = 20) -> List[Episode]:
        """Fetch newly updated anime episodes from AniDB."""
        resp = self._get("browse", params={"sort": "order_updated"})
        if not resp:
            return []

        cards = self._extract_anime_cards(resp.text)
        episodes = []
        for card in cards[:limit]:
            episodes.append(Episode(
                number="1",
                display_num=1,
                title=card.title_en,
                thumbnail=card.thumbnail,
                url=card.id
            ))
        return episodes

    def get_pinned_anime(self, limit: int = 20) -> List[AnimeResult]:
        """Fetch popular & spotlight anime."""
        resp = self._get("browse", params={"sort": "order_popular"})
        if not resp:
            return []
        cards = self._extract_anime_cards(resp.text)
        return cards[:limit]

    def get_trending_anime(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch trending anime from AniDB."""
        page = (from_index // 28) + 1
        resp = self._get("browse", params={"sort": "order_trending", "page": page})
        if not resp:
            return []
        cards = self._extract_anime_cards(resp.text)
        offset = from_index % 28
        return cards[offset:offset + limit]

    def get_top_rated_anime(self, from_index: int = 0, limit: int = 20, rate_tier: str = "9-10") -> List[AnimeResult]:
        """Fetch top-rated masterpieces from AniDB."""
        page = (from_index // 28) + 1
        resp = self._get("browse", params={"sort": "order_top", "page": page})
        if not resp:
            return []
        cards = self._extract_anime_cards(resp.text)
        offset = from_index % 28
        return cards[offset:offset + limit]

    def get_movies(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime movies collection from AniDB."""
        page = (from_index // 28) + 1
        resp = self._get("browse", params={"type": "Movie", "page": page})
        if not resp:
            return []
        cards = self._extract_anime_cards(resp.text)
        offset = from_index % 28
        return cards[offset:offset + limit]

    def get_genre_anime(self, genre_slug: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime by genre category from AniDB."""
        g_clean = genre_slug.lower().strip().replace(" ", "-")
        genre_id = ANIDB_GENRE_MAP.get(g_clean, "1")

        page = (from_index // 28) + 1
        resp = self._get("browse", params={"genres": genre_id, "page": page})
        if not resp:
            return []
        cards = self._extract_anime_cards(resp.text)
        offset = from_index % 28
        return cards[offset:offset + limit]

    def get_studio_anime(self, studio_name: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime produced by a studio."""
        page = (from_index // 28) + 1
        resp = self._get("browse", params={"q": studio_name, "page": page})
        if not resp:
            return []
        cards = self._extract_anime_cards(resp.text)
        offset = from_index % 28
        return cards[offset:offset + limit]

    def get_seasonal_anime(self, season: str, year: int, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch seasonal anime (Winter, Spring, Summer, Fall)."""
        page = (from_index // 28) + 1
        resp = self._get("browse", params={"season": season.lower(), "year": year, "page": page})
        if not resp:
            return []
        cards = self._extract_anime_cards(resp.text)
        offset = from_index % 28
        return cards[offset:offset + limit]

    def get_ovas_and_specials(self, subtype: str = "ova", from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch OVAs and Specials."""
        stype = "OVA" if "ova" in subtype.lower() else "Special"
        page = (from_index // 28) + 1
        resp = self._get("browse", params={"type": stype, "page": page})
        if not resp:
            return []
        cards = self._extract_anime_cards(resp.text)
        offset = from_index % 28
        return cards[offset:offset + limit]

    def get_top_currently_airing(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch top currently airing anime."""
        page = (from_index // 28) + 1
        resp = self._get("browse", params={"sort": "order_top_airing", "page": page})
        if not resp:
            return []
        cards = self._extract_anime_cards(resp.text)
        offset = from_index % 28
        return cards[offset:offset + limit]

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
        """Unified query dispatcher for generic lists."""
        ft = filter_type.upper()
        if ft in ["GENRE", "GENRES"]:
            return self.get_genre_anime(filter_data, from_index, limit)
        if ft in ["STUDIO", "STUDIOS"]:
            return self.get_studio_anime(filter_data, from_index, limit)
        if ft in ["MOVIES", "MOVIE"]:
            return self.get_movies(from_index, limit)
        if ft in ["TRENDING"]:
            return self.get_trending_anime(from_index, limit)
        if ft in ["POPULAR", "PINNED"]:
            return self.get_pinned_anime(limit)
        if ft in ["TOP_RATED", "RATED"]:
            return self.get_top_rated_anime(from_index, limit)
        return self.search_anime(filter_data)
