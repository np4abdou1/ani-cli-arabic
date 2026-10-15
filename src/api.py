"""
AnimeAPI - Modular Browserless Anime3rb Engine for ani-cli-arabic
Self-contained, fast, TLS-impersonated scraper providing multi-quality streams (1080p/720p/480p),
rich Arabic/English metadata, exact episode titles, and zero external infrastructure dependencies.
"""

import json
import re
import os
import socket
import ssl
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
from curl_cffi import requests
from bs4 import BeautifulSoup
from functools import wraps

from .models import AnimeResult, Episode, QualityOption
from .config import GENRE_NAME_TO_SLUG, POPULAR_STUDIOS_MAP
from .logger import logger

BASE_URL = "https://anime3rb.com"
DEFAULT_IMPERSONATE = "chrome120"
DEFAULT_TIMEOUT = 15


class CDNHealthManager:
    """
    Dynamically tracks, probes, and caches CDN host health to ensure streams
    never route to dead, stalled, or lagging CDN nodes (such as the 100s-stalling
    files-5.vid3rb.com node).
    """
    def __init__(self):
        self._lock = threading.Lock()
        # Seed known problematic hosts with a long expiration
        self._cache: Dict[str, Tuple[bool, float]] = {
            "files-5.vid3rb.com": (False, time.time() + 86400 * 7),
        }

    def is_host_healthy(self, host: str, timeout: float = 1.2) -> bool:
        if not host:
            return False
        host = host.split(":")[0].strip().lower()
        now = time.time()
        with self._lock:
            if host in self._cache:
                healthy, exp = self._cache[host]
                if now < exp:
                    return healthy

        # Fast socket TLS probe to ensure the server responds to TLS ClientHello in <1.2s
        healthy = False
        try:
            ctx = ssl.create_default_context()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, 443))
            ss = ctx.wrap_socket(s, server_hostname=host)
            ss.close()
            s.close()
            healthy = True
        except Exception:
            healthy = False

        ttl = 600.0 if healthy else 1800.0
        with self._lock:
            self._cache[host] = (healthy, now + ttl)
        return healthy

    def mark_unhealthy(self, host: str, duration: float = 1800.0):
        if not host:
            return
        host = host.split(":")[0].strip().lower()
        with self._lock:
            self._cache[host] = (False, time.time() + duration)


_cdn_health_manager = CDNHealthManager()

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}


def retry_with_backoff(retries=3, initial_delay=0.4, backoff_factor=1.5):
    """Decorator to retry network calls on failure with progressive backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    result = func(*args, **kwargs)
                    if result is not None:
                        return result
                except Exception:
                    pass
                attempt += 1
                if attempt < retries:
                    delay = initial_delay * (backoff_factor ** (attempt - 1))
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class AnimeAPI:
    """Core API provider connecting directly to Anime3rb with TLS fingerprinting."""
    
    def __init__(self):
        self._cache_lock = threading.Lock()
        self._local = threading.local()
        self._anime_cache: Dict[str, AnimeResult] = {}
        self._episodes_cache: Dict[str, List[Episode]] = {}
        self._search_cache: Dict[str, List[AnimeResult]] = {}
        self._lw_token: Optional[str] = None
        self._lw_snapshot: Optional[str] = None
        self._lw_cookies: Dict[str, str] = {}
        self._lw_token_time: float = 0
        
        # Pre-warm Livewire session & context in a background daemon thread
        threading.Thread(target=self._prewarm_context, daemon=True).start()

    def _get_session(self) -> requests.Session:
        if not hasattr(self._local, "session") or self._local.session is None:
            proxies = None
            http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
            https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            if http_proxy or https_proxy:
                proxies = {"http": http_proxy, "https": https_proxy}
            
            self._local.session = requests.Session(
                impersonate=DEFAULT_IMPERSONATE,
                timeout=DEFAULT_TIMEOUT,
                proxies=proxies
            )
        
        # Ensure session on any thread has active Livewire cookies
        if self._lw_cookies:
            for k, v in self._lw_cookies.items():
                self._local.session.cookies.set(k, v)

        return self._local.session

    def _prewarm_context(self):
        try:
            self._ensure_livewire_context()
        except Exception:
            pass

    def _ensure_livewire_context(self):
        import time
        now = time.time()
        with self._cache_lock:
            if self._lw_token and self._lw_snapshot and (now - self._lw_token_time < 1800):
                return self._lw_token, self._lw_snapshot, self._lw_cookies
            
            s = self._get_session()
            try:
                r_home = s.get(BASE_URL, headers=DEFAULT_HEADERS, timeout=8)
                if r_home.status_code != 200:
                    return None, None, {}
                
                csrf_match = re.search(r'csrf-token.*?content="(.*?)"', r_home.text)
                self._lw_token = csrf_match.group(1) if csrf_match else ""
                
                for m in re.finditer(r'wire:snapshot=(["\'])([^"\']+?)\1', r_home.text):
                    dec = m.group(2).replace('&quot;', '"').replace('&amp;', '&')
                    if '"name":"search"' in dec:
                        self._lw_snapshot = dec
                        break
                
                self._lw_cookies = dict(r_home.cookies)
                self._lw_token_time = now
                return self._lw_token, self._lw_snapshot, self._lw_cookies
            except Exception:
                return None, None, {}

    @retry_with_backoff()
    def search_anime(self, query: str) -> List[AnimeResult]:
        """Search anime with sub-millisecond RAM caching and high-speed single-pass Livewire query."""
        query = query.strip()
        if not query:
            return []

        q_key = query.lower()
        with self._cache_lock:
            if q_key in self._search_cache:
                return self._search_cache[q_key]

        token, snapshot, cookies = self._ensure_livewire_context()
        s = self._get_session()
        if cookies:
            for k, v in cookies.items():
                s.cookies.set(k, v)

        if token and snapshot:
            lw_headers = {
                "Referer": BASE_URL + "/",
                "X-Livewire": "true",
                "X-CSRF-TOKEN": token,
                "Content-Type": "application/json",
                **DEFAULT_HEADERS
            }

            # 1. Fast Primary Search pass
            payload = {
                "_token": token,
                "components": [
                    {
                        "snapshot": snapshot,
                        "updates": {"query": query, "deep": False},
                        "calls": []
                    }
                ]
            }

            try:
                r_lw = s.post(f"{BASE_URL}/livewire/update", json=payload, headers=lw_headers, timeout=6)
                if r_lw.status_code == 200:
                    data = r_lw.json()
                    comp = data.get("components", [{}])[0]
                    if "snapshot" in comp:
                        self._lw_snapshot = comp["snapshot"]
                    if "html" in comp.get("effects", {}):
                        items = self._parse_search_html(comp["effects"]["html"])
                        if items:
                            with self._cache_lock:
                                self._search_cache[q_key] = items
                            return items
            except Exception:
                pass

            # 2. Fallback: clean sub-query
            words = [w for w in query.split() if len(w) >= 3 and w.lower() not in ["the", "and", "for", "with", "season", "movie"]]
            if words:
                for sub_q in [" ".join(words[:2]), words[0]]:
                    if sub_q.lower() == q_key:
                        continue
                    try:
                        payload = {
                            "_token": token,
                            "components": [
                                {
                                    "snapshot": self._lw_snapshot or snapshot,
                                    "updates": {"query": sub_q, "deep": False},
                                    "calls": []
                                }
                            ]
                        }
                        r_lw = s.post(f"{BASE_URL}/livewire/update", json=payload, headers=lw_headers, timeout=5)
                        if r_lw.status_code == 200:
                            data = r_lw.json()
                            comp = data.get("components", [{}])[0]
                            if "html" in comp.get("effects", {}):
                                items = self._parse_search_html(comp["effects"]["html"])
                                if items:
                                    with self._cache_lock:
                                        self._search_cache[q_key] = items
                                    return items
                    except Exception:
                        pass

        # 3. Direct HTML search fallback if Livewire is temporarily blocked or unavailable
        try:
            r_fallback = s.get(f"{BASE_URL}/titles?q={query}", headers=DEFAULT_HEADERS, timeout=6)
            if r_fallback.status_code == 200:
                items = self._parse_search_html(r_fallback.text)
                if items:
                    with self._cache_lock:
                        self._search_cache[q_key] = items
                    return items
        except Exception:
            pass

        return []

    def _parse_search_html(self, html: str) -> List[AnimeResult]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        cards = soup.find_all("a", href=re.compile(r"/titles/([^/]+)$"))
        seen_slugs = set()

        for card in cards:
            href = card.get("href", "")
            slug_match = re.search(r"/titles/([^/]+)$", href)
            if not slug_match:
                continue
            slug = slug_match.group(1)
            if slug in seen_slugs or slug in ["list", "tv", "movie", "ova", "ona", "special"]:
                continue
            seen_slugs.add(slug)

            # Titles
            title_el = card.find("h4")
            title = title_el.text.strip() if title_el else slug
            alt_el = card.find("h5")
            alt_title = alt_el.text.strip() if alt_el else ""

            # Poster
            img = card.find("img")
            poster = img.get("src") or img.get("data-src") or "" if img else ""

            # Details
            card_text = card.text
            rating_match = re.search(r"التقييم\s*([0-9\.]+)", card_text)
            score = rating_match.group(1) if rating_match else "N/A"

            eps_match = re.search(r"(\d+)\s*حلقات?", card_text)
            episodes_count = eps_match.group(1) if eps_match else "N/A"

            season_match = re.search(r"(شتاء|ربيع|صيف|خريف)\s*(\d{4})", card_text)
            premiered = f"{season_match.group(1)} {season_match.group(2)}" if season_match else "N/A"

            # Determine anime type from title/slug/alt_title/episodes
            full_search_text = f"{title} {alt_title} {slug}".lower()
            if any(w in full_search_text for w in ["movie", "film", "فيلم"]):
                anime_type = "Movie"
            elif any(w in full_search_text for w in ["ova", "أوفا"]):
                anime_type = "OVA"
            elif any(w in full_search_text for w in ["ona", "أونا"]):
                anime_type = "ONA"
            elif any(w in full_search_text for w in ["special", "خاصة"]):
                anime_type = "Special"
            elif episodes_count == "1":
                anime_type = "Movie" if any(w in full_search_text for w in ["movie", "film"]) else "Special"
            else:
                anime_type = "TV"

            res = AnimeResult(
                id=slug,
                title_en=title,
                title_jp=alt_title,
                title_ar=title,
                title_romaji=alt_title or title,
                type=anime_type,
                episodes=episodes_count,
                status="N/A",
                genres="N/A",
                score=score,
                premiered=premiered,
                thumbnail=poster
            )
            results.append(res)

        return results

    @retry_with_backoff()
    def get_anime_details(self, anime_id: str) -> AnimeResult:
        """Fetch rich details, metadata, synopsis, genres, and external links for an anime."""
        slug = anime_id.strip().lstrip("/").replace("titles/", "")
        
        with self._cache_lock:
            if slug in self._anime_cache and getattr(self._anime_cache[slug], "thumbnail", None):
                return self._anime_cache[slug]

        url = f"{BASE_URL}/titles/{slug}"
        s = self._get_session()
        r = s.get(url, headers=DEFAULT_HEADERS)
        if r.status_code != 200:
            return AnimeResult(id=slug, title_en=slug, thumbnail="")

        soup = BeautifulSoup(r.text, "html.parser")

        # Titles & Type
        h1 = soup.find("h1")
        h1_raw = h1.text.strip() if h1 else slug
        type_match = re.search(r"\(\s*([^)]+)\s*\)", h1_raw)
        anime_type = type_match.group(1).strip() if type_match else "SERIES"
        clean_title = re.sub(r"\s*\([^)]*\)", "", h1_raw).strip()

        h2 = soup.find("h2")
        alt_title = h2.text.strip() if h2 else ""

        # Poster
        poster = ""
        poster_img = soup.find("img", alt=re.compile(r"بوستر")) or soup.find("img", class_=re.compile(r"poster|cover"))
        if poster_img:
            poster = poster_img.get("src") or poster_img.get("data-src") or ""
        if not poster:
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or ""
                if "images.anime3rb.com" in src and "logo" not in src and "favicon" not in src:
                    poster = src
                    break

        # Synopsis
        synopsis = ""
        for p in soup.find_all("p"):
            text = p.text.strip()
            if len(text) > 40 and "جافاسكريبت" not in text and "Cookies" not in text and "IPTV" not in text:
                synopsis = text
                break

        score = "N/A"
        status = "N/A"
        season = "N/A"
        studio = ""
        author = ""
        age_rating = "N/A"
        genres = []
        other_names = []
        external_links = {}
        batch_download_url = ""

        full_text = soup.text

        status_match = re.search(r"الحالة\s*:\s*([^\n\r]+)", full_text)
        if status_match:
            status = status_match.group(1).strip()

        season_match = re.search(r"إصدار\s*:\s*([^\n\r]+)", full_text)
        if season_match:
            season = season_match.group(1).strip()

        studio_match = re.search(r"الاستديو\s*:\s*([^\n\r]+)", full_text)
        if studio_match:
            studio = studio_match.group(1).strip()

        author_match = re.search(r"المؤلف\s*:\s*([^\n\r]+)", full_text)
        if author_match:
            author = author_match.group(1).strip()

        score_match = re.search(r"التقييم\s*([0-9\.]+)", full_text)
        if score_match:
            score = score_match.group(1).strip()

        age_match = re.search(r"التصنيف العمري\s*([^\n\r]+)", full_text)
        if age_match:
            age_rating = age_match.group(1).strip()

        main_container = soup.find("main") or soup
        for a in main_container.find_all("a", href=re.compile(r"/genre/[a-zA-Z0-9\-]+$")):
            if not a.find_parent("aside") and not a.find_parent("footer") and not a.find_parent("nav"):
                clean_genre = a.text.strip().split("\n")[0].strip()
                if clean_genre and clean_genre not in genres and not clean_genre.isdigit():
                    genres.append(clean_genre)

        other_names_block = re.search(r"أسماء أخرى\s*:\s*(.*?)(?:الحالة|المصادر|العروض|$)", full_text, re.DOTALL)
        if other_names_block:
            other_names = [n.strip() for n in other_names_block.group(1).split("\n") if n.strip()]

        for a in soup.find_all("a", href=re.compile(r"myanimelist|anidb|animenewsnetwork|wikipedia|syoboi|bangumi|baidu|douban")):
            site_name = a.text.strip().lower()
            href = a.get("href")
            if site_name and href:
                external_links[site_name] = href

        batch_a = soup.find("a", href=re.compile(rf"/titles/{re.escape(slug)}/download"))
        if batch_a:
            batch_download_url = urljoin(BASE_URL, batch_a.get("href"))

        # Also extract and cache episodes
        episodes = []
        seen_ep_nums = set()
        for a in soup.find_all("a", href=re.compile(rf"/episode/{re.escape(slug)}/\d+")):
            ep_href = a.get("href", "")
            ep_num_match = re.search(r"/episode/[^/]+/(\d+)", ep_href)
            if not ep_num_match:
                continue
            ep_num = int(ep_num_match.group(1))
            if ep_num in seen_ep_nums:
                continue
            seen_ep_nums.add(ep_num)

            p_title = a.find("p")
            specific_title = p_title.text.strip() if p_title else ""

            dur_span = a.find("span", class_=re.compile(r"bg-dark"))
            duration = dur_span.text.strip() if dur_span else ""

            img = a.find("img")
            thumb = img.get("src") or img.get("data-src") or "" if img else ""

            is_last = "الأخيرة" in a.text

            episodes.append(Episode(
                number=str(ep_num),
                type="Episode",
                display_num=ep_num,
                title=specific_title or f"الحلقة {ep_num}",
                duration=duration,
                thumbnail=thumb,
                is_last=is_last,
                url=f"{BASE_URL}/episode/{slug}/{ep_num}",
                anime_id=slug
            ))

        episodes.sort(key=lambda x: x.display_num)
        self._episodes_cache[slug] = episodes

        result = AnimeResult(
            id=slug,
            title_en=clean_title,
            title_jp=alt_title,
            title_ar=clean_title,
            title_romaji=alt_title or clean_title,
            type=anime_type,
            episodes=str(len(episodes)) if episodes else "N/A",
            status=status,
            genres=", ".join(genres) if genres else "N/A",
            score=score,
            rating=age_rating,
            premiered=season,
            creators=author or studio,
            thumbnail=poster,
            synopsis=synopsis,
            studio=studio,
            author=author,
            batch_download_url=batch_download_url,
            other_names=other_names,
            external_links=external_links
        )

        with self._cache_lock:
            self._anime_cache[slug] = result
        return result

    @retry_with_backoff()
    def get_episodes(self, anime_id: str) -> List[Episode]:
        """Get full list of episodes with Arabic subtitle titles, durations, and thumbnails."""
        slug = anime_id.strip().lstrip("/").replace("titles/", "")
        with self._cache_lock:
            if slug in self._episodes_cache:
                return self._episodes_cache[slug]

        self.get_anime_details(slug)
        with self._cache_lock:
            return self._episodes_cache.get(slug, [])

    def get_episode_streams(self, episode: Episode) -> List[QualityOption]:
        """Extract all direct playable streaming links and resolutions for an episode."""
        anime_id = getattr(episode, 'anime_id', '')
        if not anime_id and getattr(episode, 'url', ''):
            parts = [p for p in episode.url.strip('/').split('/') if p]
            if len(parts) >= 2 and parts[-2] != 'episode':
                anime_id = parts[-2]
            elif len(parts) >= 1:
                anime_id = parts[-1]
        if not anime_id:
            return []
        server_data = self.get_streaming_servers(anime_id, episode.number)
        if server_data and "Qualities" in server_data:
            return server_data["Qualities"]
        return []

    def _extract_player_url(self, html_text: str) -> Optional[str]:
        """
        Multi-tier extraction for Vid3rb player embed URL from Anime3rb episode HTML.
        Resilient against Livewire upgrades, minification, and DOM layout changes.
        """
        if not html_text:
            return None

        # Tier 1: Parse wire:snapshot (Livewire 3)
        for m in re.finditer(r'wire:snapshot=(["\'])([^"\']+?)\1', html_text):
            try:
                raw_snap = m.group(2).replace('&quot;', '"').replace('&amp;', '&')
                snap_data = json.loads(raw_snap)
                data_dict = snap_data.get("data", {})
                v_url = data_dict.get("video_url")
                if v_url and "vid3rb" in v_url:
                    return v_url
            except Exception:
                pass

        # Tier 2: Universal URL pattern regex for Vid3rb player embed
        m_regex = re.search(
            r'https?://[a-zA-Z0-9\.\-]*vid3rb\.com/player/[a-zA-Z0-9\-_]+(?:\?[^"\'<>\s]+)?',
            html_text
        )
        if m_regex:
            return m_regex.group(0).replace('&amp;', '&').replace('&quot;', '')

        # Tier 3: BeautifulSoup DOM iframe extraction
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            for iframe in soup.find_all("iframe"):
                src = iframe.get("src") or iframe.get("data-src") or iframe.get(":src") or ""
                if "vid3rb.com/player/" in src or ("player" in src and "token=" in src):
                    return src.replace('&amp;', '&')
        except Exception:
            pass

        # Tier 4: Search for any video_url in inline scripts or Livewire 2 wire:initial-data
        for m in re.finditer(r'["\']video_url["\']\s*:\s*["\'](https?://[^"\']+)["\']', html_text):
            candidate = m.group(1).replace('\\/', '/').replace('&amp;', '&')
            if "vid3rb" in candidate:
                return candidate

        return None

    def _extract_player_sources(self, player_html: str) -> List[Dict[str, Any]]:
        """
        Multi-tier extraction for video stream definitions from the Vid3rb player page.
        Tolerant to minified JS, changed variable names, and varying array placements.
        """
        if not player_html:
            return []

        # Tier 1: video_sources declaration (var/let/const/window.video_sources = [...])
        for vs in re.findall(r'(?:video_sources\s*=\s*)?(\[\s*\{.*?\}\s*\])', player_html, re.DOTALL):
            if "src" in vs and ("1080" in vs or "720" in vs or "480" in vs or "video/mp4" in vs):
                try:
                    parsed = json.loads(vs.replace('\\/', '/'))
                    if isinstance(parsed, list):
                        valid = [x for x in parsed if isinstance(x, dict) and x.get("src")]
                        if valid:
                            return parsed
                except Exception:
                    pass

        # Tier 2: Broader regex matching any array containing video objects with 'src'
        for vs in re.findall(r'(\[\s*\{[^{}]*?"src"[^{}]*?\}\s*(?:,\s*\{[^{}]*?\}\s*)*\])', player_html, re.DOTALL):
            try:
                parsed = json.loads(vs.replace('\\/', '/'))
                if isinstance(parsed, list) and any(isinstance(x, dict) and x.get("src") for x in parsed):
                    return parsed
            except Exception:
                pass

        # Tier 3: Direct URL scan for vid3rb stream endpoints in player script
        stream_urls = re.findall(r'https?://[a-zA-Z0-9\.\-]*vid3rb\.com/video/[a-zA-Z0-9\-_]+(?:\?[^"\'<>\s]+)?', player_html)
        if stream_urls:
            discovered = []
            seen_urls = set()
            for u in stream_urls:
                cleaned_u = u.replace('\\/', '/').replace('&amp;', '&')
                if cleaned_u in seen_urls:
                    continue
                seen_urls.add(cleaned_u)
                discovered.append({
                    "src": cleaned_u,
                    "type": "video/mp4",
                    "label": "Direct Stream",
                    "res": "",
                    "premium": False
                })
            return discovered

        return []

    def _resolve_direct_stream_url(self, session, raw_url: str, player_url: str, max_retries: int = 10) -> str:
        """
        Follows 302 redirects to obtain the direct CDN file URL while validating
        target CDN host health via _cdn_health_manager. Ensures MPV never stalls
        on dead or lagging CDN servers.
        """
        redir_headers = {
            "Referer": player_url or "https://video.vid3rb.com/",
            **DEFAULT_HEADERS
        }
        best_candidate = raw_url

        for _ in range(max_retries):
            try:
                session.cookies.clear()
                r_redirect = session.get(raw_url, headers=redir_headers, allow_redirects=False, timeout=3.5)
                if r_redirect.status_code in [301, 302, 307, 308]:
                    loc = r_redirect.headers.get("Location") or r_redirect.headers.get("location")
                    if loc:
                        parsed = urlparse(loc)
                        host = parsed.netloc.split(":")[0].strip()
                        if _cdn_health_manager.is_host_healthy(host):
                            return loc
                        best_candidate = loc
            except Exception:
                pass

        return best_candidate

    @retry_with_backoff()
    def get_streaming_servers(self, anime_id: str, episode_num: str, anime_type: str = 'SERIES') -> Optional[Dict]:
        """
        Extract direct CDN stream URLs and return mapped qualities.
        Returns a dict structured for full backward compatibility + direct URL support.
        """
        slug = anime_id.strip().lstrip("/").replace("episode/", "").split("/")[0]
        ep_num = int(re.search(r"\d+", str(episode_num)).group(0)) if re.search(r"\d+", str(episode_num)) else 1
        ep_url = f"{BASE_URL}/episode/{slug}/{ep_num}"

        s = self._get_session()
        try:
            r = s.get(ep_url, headers=DEFAULT_HEADERS, timeout=6)
            if r.status_code != 200:
                return None

            player_url = self._extract_player_url(r.text)
            if not player_url:
                return None

            player_headers = {
                "Referer": "https://anime3rb.com/",
                **DEFAULT_HEADERS
            }
            r_player = s.get(player_url, headers=player_headers, timeout=6)
            sources = []
            if r_player.status_code == 200:
                sources = self._extract_player_sources(r_player.text)

            # Optional proxy fallback (e.g. for datacenter VPS environments where Cloudflare blocks server IPs)
            custom_proxy = os.environ.get("TOR_PROXY") or os.environ.get("ALL_PROXY") or os.environ.get("HTTPS_PROXY")
            if not sources and custom_proxy:
                try:
                    s_proxy = requests.Session(impersonate=DEFAULT_IMPERSONATE)
                    s_proxy.proxies = {"https": custom_proxy, "http": custom_proxy}
                    r_proxy = s_proxy.get(player_url, headers=player_headers, timeout=6)
                    if r_proxy.status_code == 200:
                        sources = self._extract_player_sources(r_proxy.text)
                        if sources:
                            s = s_proxy
                except Exception:
                    pass

            if not sources:
                return None

            # Resolve direct CDN links with dynamic health verification
            server_dict = {
                "CurrentEpisode": {},
                "Qualities": [],
                "DirectStreams": {}
            }

            for src_item in sources:
                label = src_item.get("label", "Unknown")
                res = str(src_item.get("res", ""))
                is_premium = src_item.get("premium", False)
                raw_src = src_item.get("src", "")

                if is_premium or not raw_src:
                    continue

                direct_url = self._resolve_direct_stream_url(s, raw_src, player_url)

                # Map quality keys
                key = f"{res}p" if res else label
                if "1080" in res or "1080" in label:
                    server_dict["CurrentEpisode"]["FRFhdQ"] = direct_url
                    server_dict["DirectStreams"]["1080p"] = direct_url
                elif "720" in res or "720" in label:
                    server_dict["CurrentEpisode"]["FRLink"] = direct_url
                    server_dict["DirectStreams"]["720p"] = direct_url
                elif "480" in res or "480" in label:
                    server_dict["CurrentEpisode"]["FRLowQ"] = direct_url
                    server_dict["DirectStreams"]["480p"] = direct_url
                else:
                    server_dict["CurrentEpisode"][key] = direct_url
                    server_dict["DirectStreams"][key] = direct_url

                server_dict["Qualities"].append(QualityOption(
                    name=f"{label} ({res}p)" if res else label,
                    server_key=key,
                    style="info",
                    direct_url=direct_url,
                    res=res,
                    premium=is_premium
                ))

            return server_dict

        except Exception as e:
            logger.error("AnimeAPI", f"Error getting streaming servers for {slug} ep {ep_num}: {e}")
            return None

    def extract_direct_stream(self, anime_id: str, episode_num: str, quality_key: str = "1080p") -> Optional[str]:
        """Direct stream resolver shortcut."""
        server_data = self.get_streaming_servers(anime_id, episode_num)
        if not server_data:
            return None
        streams = server_data.get("DirectStreams", {})
        if quality_key in streams:
            return streams[quality_key]
        for q in ["1080p", "720p", "480p"]:
            if q in streams:
                return streams[q]
        if streams:
            return next(iter(streams.values()))
        return None

    # Backward compatibility helpers for Mediafire scraping (now directly returns stream URL)
    def build_mediafire_url(self, server_id: str) -> str:
        return server_id

    def extract_mediafire_direct(self, mf_url: str) -> Optional[str]:
        return mf_url if mf_url and mf_url.startswith("http") else None

    def _parse_anime_cards_from_html(self, html: str) -> List[AnimeResult]:
        """Universal parser for cards on Anime3rb list, genre, search, and home pages."""
        soup = BeautifulSoup(html, "html.parser")
        results = []
        seen_slugs = set()

        for a in soup.find_all("a", href=re.compile(r"/titles/([a-zA-Z0-9\-]+)$")):
            href = a.get("href", "")
            slug_match = re.search(r"/titles/([a-zA-Z0-9\-]+)$", href)
            if not slug_match:
                continue
            slug = slug_match.group(1)
            if slug in seen_slugs or slug in ["list", "tv", "movie", "ova", "ona", "special", "music", "cm"]:
                continue

            img = a.find("img")
            poster = img.get("src") or img.get("data-src") or "" if img else ""

            # Title extraction
            title_el = a.find(["h4", "h3", "h2", "span", "p"]) or a
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                title = slug.replace("-", " ").title()

            alt_el = a.find(["h5", "small"])
            alt_title = alt_el.get_text(strip=True) if alt_el else ""

            # Metadata extraction
            card_el = a.find_parent(["article", "div"]) or a
            card_text = card_el.get_text(" ", strip=True) if card_el else a.get_text(" ", strip=True)

            score_m = re.search(r"التقييم\s*([0-9\.]+)", card_text) or re.search(r"([0-9]\.[0-9]{1,2})", card_text)
            score = score_m.group(1) if score_m else "N/A"

            eps_m = re.search(r"(\d+)\s*حلقات?", card_text)
            eps_count = eps_m.group(1) if eps_m else "N/A"

            season_m = re.search(r"(شتاء|ربيع|صيف|خريف)\s*(\d{4})", card_text)
            premiered = f"{season_m.group(1)} {season_m.group(2)}" if season_m else "N/A"

            # Determine type
            full_text = f"{title} {alt_title} {slug}".lower()
            if any(w in full_text for w in ["movie", "film", "فيلم"]):
                atype = "Movie"
            elif any(w in full_text for w in ["ova", "أوفا"]):
                atype = "OVA"
            elif any(w in full_text for w in ["ona", "أونا"]):
                atype = "ONA"
            elif any(w in full_text for w in ["special", "خاصة"]):
                atype = "Special"
            elif eps_count == "1":
                atype = "Movie" if any(w in full_text for w in ["movie", "film"]) else "Special"
            else:
                atype = "TV"

            seen_slugs.add(slug)
            results.append(AnimeResult(
                id=slug,
                title_en=title,
                title_jp=alt_title,
                title_ar=title,
                title_romaji=alt_title or title,
                type=atype,
                episodes=eps_count,
                status="N/A",
                genres="N/A",
                score=score,
                premiered=premiered,
                thumbnail=poster
            ))
        return results

    @retry_with_backoff()
    def get_latest_episodes(self, limit: int = 40) -> List[Dict[str, Any]]:
        """Fetch latest released episodes stream directly from Anime3rb homepage."""
        s = self._get_session()
        try:
            r = s.get(BASE_URL, headers=DEFAULT_HEADERS, timeout=10)
            if r.status_code != 200:
                return []
            soup = BeautifulSoup(r.text, "html.parser")
            episodes = []
            seen = set()

            for a in soup.find_all("a", href=re.compile(r"/episode/([^/]+)/(\d+)")):
                href = a.get("href", "")
                m = re.search(r"/episode/([^/]+)/(\d+)", href)
                if not m:
                    continue
                slug, ep_num = m.group(1), int(m.group(2))
                key = f"{slug}:{ep_num}"
                if key in seen:
                    continue
                seen.add(key)

                img = a.find("img")
                thumb = img.get("src") or img.get("data-src") or "" if img else ""

                text = a.get_text(" ", strip=True)
                title = re.sub(r"الحلقة\s*\d+", "", text).strip()
                if not title:
                    title = slug.replace("-", " ").title()

                episodes.append({
                    "slug": slug,
                    "ep_num": ep_num,
                    "title": title,
                    "thumbnail": thumb,
                    "url": href
                })
                if len(episodes) >= limit:
                    break

            return episodes
        except Exception:
            return []

    @retry_with_backoff()
    def get_pinned_anime(self, limit: int = 20) -> List[AnimeResult]:
        """Fetch pinned / spotlight featured anime from homepage."""
        s = self._get_session()
        try:
            r = s.get(BASE_URL, headers=DEFAULT_HEADERS, timeout=10)
            if r.status_code != 200:
                return []
            
            soup = BeautifulSoup(r.text, "html.parser")
            results = []
            seen = set()

            # 1. Search in "الأنميات المثبتة" (Pinned Anime) section
            pinned_header = None
            for el in soup.find_all(string=lambda t: t and "الأنميات المثبتة" in t):
                pinned_header = el
                break

            if pinned_header:
                container = pinned_header.find_parent("section") or pinned_header.find_parent("div")
                cards = container.find_all("a", href=True) if container else []
                for card in cards:
                    href = card.get("href", "")
                    ep_match = re.search(r"/episode/([^/]+)/(\d+)", href)
                    if ep_match:
                        slug = ep_match.group(1)
                        if slug in seen or slug in ["list", "tv", "movie", "ova", "special"]:
                            continue
                        seen.add(slug)

                        title_el = card.find("h3") or card.find("h4") or card.find("h2") or card.find("h5")
                        title = title_el.text.strip() if title_el else slug.replace("-", " ").title()

                        img = card.find("img")
                        poster = img.get("src") or img.get("data-src") or "" if img else ""
                        ep_num = ep_match.group(2)

                        res = AnimeResult(
                            id=slug,
                            title_en=title,
                            title_jp=title,
                            title_ar=title,
                            title_romaji=title,
                            type="TV",
                            episodes=ep_num,
                            status="Ongoing",
                            genres="Pinned",
                            score="9.0",
                            premiered="Spotlight",
                            thumbnail=poster
                        )
                        results.append(res)
                        if len(results) >= limit:
                            break

            # 2. If nothing found in pinned container, fallback to slider cards
            if not results:
                for a in soup.select("ul.titles-slider a[href*='/titles/']"):
                    href = a.get("href", "")
                    slug_match = re.search(r"/titles/([^/]+)$", href)
                    if slug_match:
                        slug = slug_match.group(1)
                        if slug in seen or slug in ["list", "tv", "movie", "ova", "special"]:
                            continue
                        seen.add(slug)
                        img = a.find("img")
                        poster = img.get("src") or img.get("data-src") or "" if img else ""
                        title = a.get_text(strip=True) or slug.replace("-", " ").title()
                        results.append(AnimeResult(
                            id=slug,
                            title_en=title,
                            title_jp=title,
                            title_ar=title,
                            title_romaji=title,
                            type="TV",
                            episodes="N/A",
                            status="Pinned",
                            genres="Spotlight",
                            score="9.0",
                            premiered="Spotlight",
                            thumbnail=poster
                        ))
                        if len(results) >= limit:
                            break

            return results[:limit]
        except Exception:
            return []

    @retry_with_backoff()
    def get_latest_anime(self, from_index: int = 0, limit: int = 30) -> List[AnimeResult]:
        """Fetch latest releases from Anime3rb homepage."""
        s = self._get_session()
        try:
            r = s.get(BASE_URL, headers=DEFAULT_HEADERS, timeout=10)
            if r.status_code != 200:
                return []
            items = self._parse_anime_cards_from_html(r.text)
            return items[from_index:from_index + limit]
        except Exception:
            return []

    @retry_with_backoff()
    def get_trending_anime(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch trending and most active anime with pagination."""
        page = (from_index // max(1, limit)) + 1
        url = f"{BASE_URL}/titles/list?sort=views&sort_dir=desc&page={page}"
        s = self._get_session()
        try:
            r = s.get(url, headers=DEFAULT_HEADERS, timeout=10)
            if r.status_code != 200:
                return []
            items = self._parse_anime_cards_from_html(r.text)
            return items[:limit]
        except Exception:
            return []

    @retry_with_backoff()
    def get_top_rated_anime(self, from_index: int = 0, limit: int = 20, rate_tier: str = "9-10") -> List[AnimeResult]:
        """Fetch masterpiece / top rated anime (9-10 rating)."""
        page = (from_index // max(1, limit)) + 1
        url = f"{BASE_URL}/titles/list?rate={rate_tier}&sort=score&sort_dir=desc&page={page}"
        s = self._get_session()
        try:
            r = s.get(url, headers=DEFAULT_HEADERS, timeout=10)
            if r.status_code != 200:
                return []
            items = self._parse_anime_cards_from_html(r.text)
            return items[:limit]
        except Exception:
            return []

    @retry_with_backoff()
    def get_movies(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime movies collection with pagination."""
        page = (from_index // max(1, limit)) + 1
        url = f"{BASE_URL}/titles/list/movie?page={page}"
        s = self._get_session()
        try:
            r = s.get(url, headers=DEFAULT_HEADERS, timeout=10)
            if r.status_code != 200:
                return []
            items = self._parse_anime_cards_from_html(r.text)
            return items[:limit]
        except Exception:
            return []

    @retry_with_backoff()
    def get_seasonal_anime(self, season: str = None, year: int = None, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch current seasonal anime."""
        import datetime
        now = datetime.datetime.now()
        if not year:
            year = now.year
        if not season:
            month = now.month
            if month in [1, 2, 3]:
                season = "WINTER"
            elif month in [4, 5, 6]:
                season = "SPRING"
            elif month in [7, 8, 9]:
                season = "SUMMER"
            else:
                season = "FALL"

        page = (from_index // max(1, limit)) + 1
        url = f"{BASE_URL}/titles/list?season={season}&year={year}&page={page}"
        s = self._get_session()
        try:
            r = s.get(url, headers=DEFAULT_HEADERS, timeout=10)
            if r.status_code != 200:
                return []
            items = self._parse_anime_cards_from_html(r.text)
            return items[:limit]
        except Exception:
            return []

    @retry_with_backoff()
    def get_genre_anime(self, genre_slug: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime by genre slug with pagination."""
        page = (from_index // max(1, limit)) + 1
        url = f"{BASE_URL}/genre/{genre_slug}?page={page}"
        s = self._get_session()
        try:
            r = s.get(url, headers=DEFAULT_HEADERS, timeout=10)
            if r.status_code != 200:
                return []
            items = self._parse_anime_cards_from_html(r.text)
            return items[:limit]
        except Exception:
            return []

    @retry_with_backoff()
    def get_ovas_and_specials(self, category: str = "ova", from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch OVAs or Specials."""
        page = (from_index // max(1, limit)) + 1
        url = f"{BASE_URL}/titles/list/{category}?page={page}"
        s = self._get_session()
        try:
            r = s.get(url, headers=DEFAULT_HEADERS, timeout=10)
            if r.status_code != 200:
                return []
            items = self._parse_anime_cards_from_html(r.text)
            return items[:limit]
        except Exception:
            return []

    @retry_with_backoff()
    def get_studio_anime(self, studio_name: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        """Fetch anime produced by a studio using Anime3rb native taxonomy and curated masterpieces with full infinite scrolling."""
        studio_slug_map = {
            "toei animation": "toei-animation",
            "studio pierrot": "pierrot",
            "pierrot": "pierrot",
            "madhouse": "madhouse",
            "bones": "bones",
            "wit studio": "wit-studio",
            "mappa": "mappa",
            "tms entertainment": "tms-entertainment",
            "white fox": "white-fox",
            "comix wave films": "comix-wave-films",
            "cloverworks": "cloverworks",
            "studio deen": "studio-deen",
            "a-1 pictures": "a-1-pictures",
            "shaft": "shaft",
            "production i.g": "production-ig",
            "production ig": "production-ig",
            "sunrise": "sunrise",
            "kyoto animation": "kyoto-animation",
            "ufotable": "ufotable",
            "lerche": "lerche",
            "p.a. works": "pa-works",
            "pa works": "pa-works",
            "j.c.staff": "jcstaff",
            "jcstaff": "jcstaff",
            "gainax": "gainax",
            "david production": "david-production",
            "trigger": "trigger",
            "studio ghibli": "studio-ghibli"
        }
        
        s_slug = studio_slug_map.get(studio_name.lower(), studio_name.lower().replace(" ", "-").replace(".", ""))
        page = (from_index // max(1, limit)) + 1
        results = []
        seen = set()

        # 1. On initial load (page 1), inject curated masterpieces for this studio
        if from_index == 0:
            curated_items = POPULAR_STUDIOS_MAP.get(studio_name) or POPULAR_STUDIOS_MAP.get(studio_name.title())
            if not curated_items:
                for k, v in POPULAR_STUDIOS_MAP.items():
                    if k.lower() == studio_name.lower():
                        curated_items = v
                        break

            if curated_items:
                for item in curated_items:
                    if isinstance(item, dict):
                        slug = item.get("id") or item.get("slug")
                        if slug and slug not in seen:
                            results.append(AnimeResult(
                                id=slug,
                                title_en=item.get("title_en", slug),
                                title_ar=item.get("title_ar", ""),
                                score=str(item.get("score", "N/A")),
                                type=item.get("type", "مسلسل"),
                                thumbnail=item.get("thumbnail", "")
                            ))
                            seen.add(slug)

        # 2. Fetch live additions from native Anime3rb studio taxonomy filter for this page
        s = self._get_session()
        url = f"{BASE_URL}/titles/list?creators[studio][]={s_slug}&page={page}"
        try:
            r = s.get(url, headers=DEFAULT_HEADERS, timeout=8)
            if r.status_code == 200:
                cards = self._parse_anime_cards_from_html(r.text)
                for c in cards:
                    if c.id not in seen:
                        results.append(c)
                        seen.add(c.id)
        except Exception:
            pass

        # 3. Fallback to search if nothing found on page 1
        if not results and from_index == 0:
            results = self.search_anime(studio_name)

        return results

    @retry_with_backoff()
    def get_anime_list(self, filter_type: str = "", filter_data: str = "", anime_type: str = "SERIES", from_index: int = 0, limit: int = 30) -> List[AnimeResult]:
        ftype = (filter_type or "").upper()
        if ftype == "SEARCH":
            return self.search_anime(filter_data)[from_index:from_index + limit]
        elif ftype == "GENRE":
            slug = GENRE_NAME_TO_SLUG.get(filter_data.lower(), filter_data.lower().replace(" ", "-"))
            return self.get_genre_anime(slug, from_index, limit)
        elif ftype == "STUDIOS" or ftype == "STUDIO":
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
        return self.get_trending_anime(from_index, limit)


