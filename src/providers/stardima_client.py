"""
Stardima API client, auth bootstrap, classification cache, and stream extraction.

The Stardima mobile app discovers its API key and host at runtime through
Firebase Remote Config.  We mirror that flow so the provider keeps working
when the key or host rotates, and cache the result locally for 24 hours.

No secrets are committed to the repository.  The Firebase *web* API key below
is a public client identifier used only to read Remote Config; the Stardima
`X-API-KEY` is fetched at runtime.
"""

from __future__ import annotations

import concurrent.futures
import html
import json
import os
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlsplit

import requests

from ..logger import logger
from ..storage import atomic_write_json


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIREBASE_PROJECT = "jcartoon2026"
FIREBASE_APP_ID = "1:823307516616:android:d596b0be539ba5b59083fd"
FIREBASE_WEB_API_KEY = "AIzaSyD7W_oU5CGLwrFhcFU_-p-pL1f8ayzatDE"
REMOTE_CONFIG_URL = (
    "https://firebaseremoteconfig.googleapis.com/v1/projects/"
    f"{FIREBASE_PROJECT}/namespaces/firebase:fetch?key={FIREBASE_WEB_API_KEY}"
)

# The production host is discovered through /api/app/info, but keep known
# fallbacks so a cold start can still work if the app-info host is slow.
APP_INFO_URLS = [
    "https://www.stardima.com/api/app/info",
    "https://f5f-efgeg59852-zfz2d-mmltizwwcvb5567r2r63e-zd46.stardima.app/api/app/info",
]
DEFAULT_SERVER_URL = (
    "https://f5f-efgeg59852-zfz2d-mmltizwwcvb5567r2r63e-zd46.stardima.app"
)

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
)
APP_UA = "jcartoonApp/1.0.8 (Android)"

CACHE_DIR = Path.home() / ".ani-cli-arabic" / "database"
AUTH_CACHE_FILE = CACHE_DIR / "stardima_auth.json"
AUTH_TTL = 24 * 60 * 60

ANIME_CATEGORY_SLUGS = {"anmy", "anime", "انمي", "أنمي"}

# Cartoon / kids brands and categories used by the site.  These are only a
# fallback when the precomputed TMDB cache has no entry for a title.
CARTOON_CATEGORY_SLUGS = {
    "cartoon",
    "cartoons",
    "kids",
    "spacetoon",
    "سبيستون",
    "كرتون",
    "اطفال",
    "أطفال",
    "disney",
    "ديزني",
    "marvel",
    "dc",
    "cn",
    "cartoon-network",
    "nickelodeon",
    "nick",
    "pixar",
    "dreamworks",
    "sony-pictures-animation",
    "warner-bros-animation",
    "boomerang",
    "manga",
    "مانجا",
    # Stardima's transliterated brand slugs
    "krton",
    "krton-zman",
    "krton-ntork",
    "krton-aslamy",
    "sbyston",
    "asdarat-sbyston",
    "sby-baor",
    "tom-and-jerry",
    "ben10",
    "mbc3",
}

# ---------------------------------------------------------------------------
# Dean Edwards unpacker (used by several host extractors)
# ---------------------------------------------------------------------------

_BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _to_base(n: int, base: int) -> str:
    if n == 0:
        return "0"
    out = ""
    while n:
        out = _BASE62[n % base] + out
        n //= base
    return out


def _find_packer_call(source: str) -> Optional[str]:
    marker = "eval(function(p,a,c,k,e,d)"
    start = source.find(marker)
    if start < 0:
        return None
    args_start = source.find("}(", start)
    if args_start < 0:
        return None
    i = args_start + 2
    depth = 1
    quote: Optional[str] = None
    escaped = False
    while i < len(source):
        ch = source[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if ch == "\\":
            escaped = True
            i += 1
            continue
        if quote:
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return source[args_start + 2 : i]
        i += 1
    return None


def _split_args(raw: str) -> List[str]:
    parts: List[str] = []
    current = ""
    quote: Optional[str] = None
    escaped = False
    depth = 0
    for ch in raw:
        if escaped:
            current += ch
            escaped = False
            continue
        if ch == "\\":
            current += ch
            escaped = True
            continue
        if quote:
            current += ch
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            current += ch
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
            continue
        current += ch
    parts.append(current.strip())
    return parts


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] in "'\"" and value[-1] == value[0]:
        return value[1:-1]
    return value


def unpack_dean_edwards(source: str) -> Optional[str]:
    """Unpack `eval(function(p,a,c,k,e,d){...}('...',62,..))` payloads."""
    raw = _find_packer_call(source)
    if not raw:
        return None
    parts = _split_args(raw)
    if len(parts) < 4:
        return None
    try:
        payload = _unquote(parts[0])
        base = int(parts[1])
        count = int(parts[2])
        raw_words = parts[3].strip()
        if raw_words.endswith(".split('|')"):
            raw_words = raw_words[:-11]
        elif raw_words.endswith('.split("|")'):
            raw_words = raw_words[:-11]
        elif ".split(" in raw_words:
            raw_words = raw_words.split(".split(", 1)[0]
        words = _unquote(raw_words).split("|")
    except (ValueError, IndexError):
        return None

    for index in range(count - 1, -1, -1):
        if index < len(words) and words[index]:
            payload = re.sub(
                r"\b" + re.escape(_to_base(index, base)) + r"\b",
                lambda _m, word=words[index]: word,
                payload,
            )
    return payload


def unpack_html(source: str) -> str:
    """Return the unpacked source when a packer is present, else the original."""
    unpacked = unpack_dean_edwards(source)
    return unpacked if unpacked else source


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class StardimaAuth:
    """Resolve `(api_key, server_url)` from env, cache, or Remote Config."""

    def __init__(self, cache_file: Optional[Path] = None, timeout: int = 12):
        self.cache_file = Path(cache_file) if cache_file else AUTH_CACHE_FILE
        self.timeout = timeout
        self._lock = threading.Lock()

    # -- public ---------------------------------------------------------

    def get(self, force_refresh: bool = False) -> Tuple[Optional[str], Optional[str]]:
        env_key = (os.environ.get("STARDIMA_API_KEY") or "").strip()
        env_server = (os.environ.get("STARDIMA_SERVER_URL") or "").strip().rstrip("/")
        if env_key:
            server = env_server or self._discover_server(env_key) or DEFAULT_SERVER_URL
            return env_key, server

        with self._lock:
            cached = self._read_cache()
            if cached and not force_refresh:
                age = time.time() - cached.get("fetched_at", 0)
                if age < AUTH_TTL:
                    return cached["api_key"], cached["server_url"]

            key = self._fetch_remote_config()
            if key:
                server = self._discover_server(key)
                if server:
                    self._write_cache(key, server)
                    return key, server

            if cached:
                logger.debug(
                    "STARDIMA",
                    "Remote Config refresh failed; using stale auth cache.",
                )
                return cached["api_key"], cached["server_url"]

        logger.error(
            "STARDIMA",
            "Unable to resolve Stardima API credentials (Remote Config + app info failed).",
        )
        return None, None

    # -- internals ------------------------------------------------------

    def _fetch_remote_config(self) -> Optional[str]:
        payload = {
            "app_instance_id": str(uuid.uuid4()),
            "app_id": FIREBASE_APP_ID,
            "language_code": "ar",
        }
        try:
            response = requests.post(
                REMOTE_CONFIG_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            if response.status_code != 200:
                logger.debug(
                    "STARDIMA",
                    f"Remote Config HTTP {response.status_code}",
                )
                return None
            data = response.json()
            entries = data.get("entries") or {}
            key = entries.get("API_KEY") or entries.get("api_key")
            if not key:
                logger.debug("STARDIMA", "Remote Config response has no API_KEY entry.")
            return key
        except (requests.RequestException, ValueError) as exc:
            logger.debug("STARDIMA", f"Remote Config request failed: {exc}")
            return None

    def _discover_server(self, api_key: str) -> Optional[str]:
        headers = {
            "X-API-KEY": api_key,
            "Accept": "application/json",
            "User-Agent": APP_UA,
        }
        for url in APP_INFO_URLS:
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                if response.status_code != 200:
                    continue
                data = response.json()
                payload = data.get("data") if isinstance(data, dict) else None
                if isinstance(payload, dict):
                    server = payload.get("server_url") or payload.get("api_url")
                    if server:
                        return str(server).rstrip("/")
                server = data.get("server_url") if isinstance(data, dict) else None
                if server:
                    return str(server).rstrip("/")
            except (requests.RequestException, ValueError):
                continue
        return None

    def _read_cache(self) -> Optional[Dict[str, Any]]:
        try:
            with open(self.cache_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return None
            if not data.get("api_key") or not data.get("server_url"):
                return None
            return data
        except (OSError, ValueError):
            return None

    def _write_cache(self, api_key: str, server_url: str) -> None:
        try:
            atomic_write_json(
                self.cache_file,
                {
                    "api_key": api_key,
                    "server_url": server_url,
                    "fetched_at": time.time(),
                },
                indent=2,
            )
            try:
                os.chmod(self.cache_file, 0o600)
            except OSError:
                pass
        except (OSError, ValueError, TypeError) as exc:
            logger.debug("STARDIMA", f"Could not write auth cache: {exc}")


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


class StardimaClient:
    """Small retrying wrapper around the Stardima Laravel API."""

    def __init__(
        self,
        auth: Optional[StardimaAuth] = None,
        session: Optional[requests.Session] = None,
        timeout: int = 30,
    ):
        self.auth = auth or StardimaAuth()
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": APP_UA,
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        self._base: Optional[str] = None
        self._key: Optional[str] = None
        self._auth_lock = threading.Lock()

    # -- auth -----------------------------------------------------------

    def _ensure_auth(self, force_refresh: bool = False) -> bool:
        if self._base and self._key and not force_refresh:
            return True
        with self._auth_lock:
            if self._base and self._key and not force_refresh:
                return True
            key, base = self.auth.get(force_refresh=force_refresh)
            if not key or not base:
                return False
            self._key = key
            self._base = base.rstrip("/")
            self.session.headers["X-API-KEY"] = key
            return True

    # -- low level ------------------------------------------------------

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        if not self._ensure_auth():
            return None
        if not path.startswith("/"):
            path = "/" + path
        url = (self._base or DEFAULT_SERVER_URL) + path

        for attempt in range(3):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                logger.debug("STARDIMA", f"GET {path} failed (attempt {attempt + 1}): {exc}")
                time.sleep(0.4 * (attempt + 1))
                continue

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    logger.debug("STARDIMA", f"GET {path} returned non-JSON.")
                    return None

            if response.status_code == 401 and attempt == 0:
                logger.debug("STARDIMA", "API key rejected; refreshing auth.")
                if self._ensure_auth(force_refresh=True):
                    url = (self._base or DEFAULT_SERVER_URL) + path
                    continue
                return None

            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(0.6 * (attempt + 1))
                continue

            logger.debug(
                "STARDIMA",
                f"GET {path} returned HTTP {response.status_code}.",
            )
            return None

        return None

    # -- endpoints ------------------------------------------------------

    def app_info(self) -> Optional[Dict[str, Any]]:
        return self.get("/api/app/info")

    def search(
        self,
        query: str = "",
        language: Optional[str] = None,
        media: Optional[str] = None,
        categories: Optional[Iterable[str]] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "query": query or "",
            "page": page,
            "per_page": per_page,
        }
        if language:
            params["language"] = language
        if media:
            params["media"] = media
        if categories:
            params["categories[]"] = list(categories)
        return self.get("/api/search", params=params)

    def video(self, video_id: Any) -> Optional[Dict[str, Any]]:
        data = self.get(f"/api/video/{video_id}")
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            return data["data"]
        return data if isinstance(data, dict) else None

    def episodes(
        self,
        season_id: Any,
        page: int = 1,
        per_page: int = 100,
    ) -> Optional[Dict[str, Any]]:
        return self.get(
            f"/api/episodes/{season_id}",
            params={"page": page, "per_page": per_page},
        )

    def servers(self, episode_id: Any) -> List[Dict[str, Any]]:
        data = self.get(f"/api/episodes/{episode_id}/servers")
        if isinstance(data, dict):
            # The endpoint returns the episode object itself:
            # {"id": 104257, ..., "servers": [...]}
            servers = data.get("servers")
            if isinstance(servers, list):
                return [item for item in servers if isinstance(item, dict)]
            servers = data.get("data")
            if isinstance(servers, list):
                return [item for item in servers if isinstance(item, dict)]
            if isinstance(servers, dict):
                nested = servers.get("servers")
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    def latest_episodes(self, page: int = 1, per_page: int = 100) -> Optional[Dict[str, Any]]:
        return self.get(
            "/api/episodes",
            params={"page": page, "per_page": per_page},
        )

    def search_by_option(
        self,
        option_type: str = "trending",
        page: int = 1,
        per_page: int = 30,
    ) -> Optional[Dict[str, Any]]:
        return self.get(
            "/api/searchByOption",
            params={"type": option_type, "page": page, "per_page": per_page},
        )


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class StardimaClassifier:
    """Classify titles as anime / cartoon / live-action using the shipped cache."""

    CACHE_FILE = Path(__file__).with_name("stardima_catalog.json")

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = Path(cache_file) if cache_file else self.CACHE_FILE
        self.items: Dict[str, Dict[str, Any]] = {}
        self.generated_at: str = ""
        self._load()

    def _load(self) -> None:
        try:
            with open(self.cache_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                raw_items = data.get("items") or {}
                if isinstance(raw_items, dict):
                    self.items = {
                        str(key): value
                        for key, value in raw_items.items()
                        if isinstance(value, dict)
                    }
                self.generated_at = str(data.get("generated_at") or "")
        except (OSError, ValueError) as exc:
            logger.warning(
                "STARDIMA",
                f"Classification cache unavailable ({self.cache_file}): {exc}",
            )
            self.items = {}
            self.generated_at = ""

    def get(self, video_id: Any) -> Optional[Dict[str, Any]]:
        return self.items.get(str(video_id))

    def title_en(self, video_id: Any) -> str:
        item = self.get(video_id) or {}
        return str(item.get("title") or "")

    def original_name(self, video_id: Any) -> str:
        item = self.get(video_id) or {}
        return str(item.get("original_name") or "")

    def vote(self, video_id: Any) -> float:
        item = self.get(video_id) or {}
        try:
            return float(item.get("vote") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def classify(
        self,
        video_id: Any,
        detail: Optional[Dict[str, Any]] = None,
    ) -> str:
        cached = self.get(video_id)
        if cached and cached.get("t"):
            return str(cached["t"])

        if detail:
            tag_tokens = {
                token.strip().lower()
                for token in str(detail.get("tags") or "").split(",")
                if token.strip()
            }
            if tag_tokens & {"anime", "انمي", "أنمي"}:
                return "anime"

            slugs = {
                str(category.get("slug") or "").lower()
                for category in (detail.get("category") or [])
                if isinstance(category, dict)
            }
            if slugs & {slug.lower() for slug in ANIME_CATEGORY_SLUGS}:
                return "anime"
            if slugs & {slug.lower() for slug in CARTOON_CATEGORY_SLUGS}:
                return "cartoon"

        return "unknown"

    @staticmethod
    def language_of(quality: Any) -> str:
        text = str(quality or "")
        if "مدبلج" in text:
            return "dub"
        if "مترجم" in text:
            return "sub"
        return ""

    @staticmethod
    def is_dub(quality: Any) -> bool:
        return StardimaClassifier.language_of(quality) == "dub"

    @staticmethod
    def matches_scope(content_type: str, scope: str, include_unknown: bool = True) -> bool:
        if content_type == scope:
            return True
        if content_type == "unknown":
            return include_unknown
        return False


# ---------------------------------------------------------------------------
# Stream extraction
# ---------------------------------------------------------------------------


class StardimaExtractor:
    """Resolve direct media URLs from Stardima's server list across multiple hosts."""

    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": BROWSER_UA,
            "Accept": "*/*",
        })

    @staticmethod
    def backup_url(servers: Iterable[Dict[str, Any]]) -> Optional[str]:
        for server in servers or []:
            label = str(server.get("label") or "").strip().lower()
            url = str(server.get("url") or "").strip()
            if label == "backup" and url.startswith("http"):
                return url
        return None

    @staticmethod
    def guess_res(url: str, text: Optional[str] = None, hint: Optional[str] = None) -> str:
        lowered = (url or "").lower()
        for resolution in ("1080", "720", "480", "360"):
            if resolution in lowered:
                return f"{resolution}p"
        if text:
            matches = re.findall(r"RESOLUTION=\d+x(\d+)", text)
            if matches:
                top = max(int(m) for m in matches if m.isdigit())
                if top >= 1000:
                    return "1080p"
                elif top >= 700:
                    return "720p"
                elif top >= 450:
                    return "480p"
                else:
                    return f"{top}p"
        if hint:
            h_low = str(hint).lower()
            if "1080" in h_low or "fhd" in h_low:
                return "1080p"
            if "720" in h_low or "hd" in h_low:
                return "720p"
            if "480" in h_low or "sd" in h_low:
                return "480p"
            if "360" in h_low:
                return "360p"
        return "720p"

    def inspect_resolution(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        text_content: Optional[str] = None,
        hint: Optional[str] = None,
    ) -> str:
        """Accurately determine the stream resolution instead of returning 'Auto'."""
        if not url:
            return "720p"

        lowered = url.lower()
        if "1080" in lowered or "fhd" in lowered:
            return "1080p"
        if "720" in lowered or "hd" in lowered:
            return "720p"
        if "480" in lowered or "sd" in lowered:
            return "480p"
        if "360" in lowered:
            return "360p"

        if ".m3u8" in lowered:
            content = text_content
            if not content:
                try:
                    r = self.session.get(url, headers=headers or {}, timeout=3)
                    if r.status_code == 200:
                        content = r.text
                except Exception:
                    pass

            if content:
                matches = re.findall(r"RESOLUTION=\d+x(\d+)", content)
                if matches:
                    top = max(int(m) for m in matches if m.isdigit())
                    if top >= 1000:
                        return "1080p"
                    elif top >= 700:
                        return "720p"
                    elif top >= 450:
                        return "480p"
                    else:
                        return f"{top}p"

        if text_content:
            m_res = re.search(r'\b(1080|720|480|360)p?\b', text_content, re.IGNORECASE)
            if m_res:
                return f"{m_res.group(1)}p"

        if hint:
            h_low = str(hint).lower()
            if "1080" in h_low or "fhd" in h_low:
                return "1080p"
            if "720" in h_low or "hd" in h_low:
                return "720p"
            if "480" in h_low or "sd" in h_low:
                return "480p"
            if "360" in h_low:
                return "360p"

        if any(ext in lowered for ext in (".mkv", ".mp4")):
            try:
                cmd = [
                    "ffprobe", "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=height",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    url
                ]
                if headers and "Referer" in headers:
                    cmd.insert(4, "-headers")
                    cmd.insert(5, f"Referer: {headers['Referer']}\r\n")
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                if proc.returncode == 0 and proc.stdout.strip().isdigit():
                    h = int(proc.stdout.strip())
                    if h >= 1000:
                        return "1080p"
                    elif h >= 700:
                        return "720p"
                    elif h >= 450:
                        return "480p"
                    else:
                        return f"{h}p"
            except Exception:
                pass

        return "720p"

    @staticmethod
    def guess_ext(url: str) -> str:
        path = (url or "").split("?", 1)[0].lower()
        if ".m3u8" in path:
            return "m3u8"
        for extension in ("mkv", "mpg", "mpeg", "webm", "mp4"):
            if path.endswith("." + extension):
                return "mpg" if extension == "mpeg" else extension
        return "mp4"

    def verify(self, url: str) -> bool:
        """Cheap availability probe; backup URLs are plain nginx files."""
        if not url or not url.startswith("http"):
            return False
        headers = {"User-Agent": BROWSER_UA, "Accept": "*/*"}

        for attempt in range(2):
            try:
                response = self.session.head(
                    url,
                    headers=headers,
                    timeout=min(6, self.timeout),
                    allow_redirects=True,
                )
                if response.status_code in (200, 206):
                    return True
            except requests.RequestException:
                pass

            try:
                response = self.session.get(
                    url,
                    headers={**headers, "Range": "bytes=0-0"},
                    timeout=min(6, self.timeout),
                    stream=True,
                )
                ok = response.status_code in (200, 206)
                response.close()
                if ok:
                    return True
            except requests.RequestException:
                pass

            if attempt == 0:
                time.sleep(0.2)
        return False

    def extract_backup(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        if not url or not url.startswith("http"):
            return None
        if self.verify(url):
            headers = {"User-Agent": BROWSER_UA}
            res = self.inspect_resolution(url, headers=headers)
            return url, headers, res
        return None

    def extract_uqload(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        if not url:
            return None
        m = re.search(r"(?:e/|embed-|embed/|embed\.php\?id=)?([a-zA-Z0-9]{12})", url)
        if not m:
            return None
        code = m.group(1)
        parsed = urlsplit(url)
        host = parsed.netloc or "uqload.vc"
        norm_url = f"https://{host}/{code}.html"
        headers = {
            "User-Agent": BROWSER_UA,
            "Referer": f"https://{host}/",
            "Origin": f"https://{host}",
        }
        try:
            r = self.session.get(norm_url, headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                return None
            text = r.text
        except requests.RequestException:
            return None

        m_direct = re.search(r'sources:\s*\[\s*"([^"]+)"', text)
        if m_direct:
            stream_url = m_direct.group(1)
            res = self.inspect_resolution(stream_url, headers=headers, text_content=text)
            return stream_url, headers, res

        unpacked = unpack_html(text)
        m_stream = re.search(r'https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*', unpacked)
        if not m_stream:
            m_stream = re.search(r'file\s*:\s*["\'](https?://[^"\']+)["\']', unpacked)
        if not m_stream:
            return None

        stream_url = m_stream.group(1 if m_stream.groups() else 0)
        stream_url = stream_url.replace("' + '", "").replace("'+'", "")
        res = self.inspect_resolution(stream_url, headers=headers, text_content=unpacked)
        return stream_url, headers, res

    def extract_savefiles(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        if not url:
            return None
        m = re.search(r"/(?:e|v|d)/([a-zA-Z0-9_-]+)", url)
        if not m:
            return None
        file_code = m.group(1)
        parsed = urlsplit(url)
        host = parsed.netloc or "savefiles.com"
        post_url = f"https://{host}/dl"
        headers = {
            "Referer": url,
            "Origin": f"https://{host}",
            "User-Agent": BROWSER_UA,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "op": "embed",
            "file_code": file_code,
            "auto": "1",
            "referer": url,
        }
        try:
            r = self.session.post(post_url, data=data, headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                return None
            text = r.text
        except requests.RequestException:
            return None

        m_src = re.search(r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+)["\']', text)
        if not m_src:
            m_src = re.search(r'https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*', text)
        if not m_src:
            return None

        stream_url = m_src.group(1 if m_src.groups() else 0)
        result_headers = {
            "Referer": f"https://{host}/",
            "Origin": f"https://{host}",
            "User-Agent": BROWSER_UA,
        }
        res = self.inspect_resolution(stream_url, headers=result_headers, text_content=text)
        return stream_url, result_headers, res

    def extract_mixdrop(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        res = self.mixdrop(url)
        if not res:
            return None
        stream_url, headers = res
        res_str = self.inspect_resolution(stream_url, headers=headers)
        return stream_url, headers, res_str

    def mixdrop(self, url: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """Extract a Mixdrop direct URL (verified working with cookie + referer)."""
        if not url:
            return None
        session = requests.Session()
        parsed = urlsplit(url)
        origin = (
            f"{parsed.scheme}://{parsed.netloc}"
            if parsed.scheme and parsed.netloc
            else "https://mixdrop.top"
        )
        headers = {"User-Agent": BROWSER_UA, "Referer": origin + "/"}
        try:
            response = session.get(url, headers=headers, timeout=self.timeout)
            if response.status_code != 200:
                return None
            text = response.text
        except requests.RequestException:
            return None

        match = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', text)
        if not match:
            unpacked = unpack_html(text)
            match = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', unpacked)
        if not match:
            return None

        stream = html.unescape(match.group(1)).replace("\\/", "/")
        if stream.startswith("//"):
            stream = "https:" + stream
        elif stream.startswith("/"):
            stream = urljoin(origin + "/", stream)

        result_headers = {
            "Referer": origin + "/",
            "User-Agent": BROWSER_UA,
        }
        cookie = "; ".join(f"{c.name}={c.value}" for c in session.cookies)
        if cookie:
            result_headers["Cookie"] = cookie
        return stream, result_headers

    def extract_lulustream(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        if not url:
            return None
        m = re.search(r"(?:e/|embed-|embed/)?([a-zA-Z0-9]{12})", url)
        code = m.group(1) if m else ""
        parsed = urlsplit(url)
        host = parsed.netloc or "luluvdo.com"
        target_url = f"https://{host}/e/{code}" if code else url
        headers = {"User-Agent": BROWSER_UA, "Referer": target_url}
        try:
            r = self.session.get(target_url, headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                return None
            text = unpack_html(r.text)
        except requests.RequestException:
            return None

        m_stream = re.search(r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+)["\']', text)
        if not m_stream:
            m_stream = re.search(r'https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*', text)
        if not m_stream:
            return None

        stream_url = m_stream.group(1 if m_stream.groups() else 0)
        res = self.inspect_resolution(stream_url, headers=headers, text_content=text)
        return stream_url, headers, res

    def extract_streamhg(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        if not url:
            return None
        if any(d in url for d in ("davioad.com", "auvexiug.com", "guxhag.com")):
            url = re.sub(r"https?://(www\.)?(davioad|auvexiug|guxhag)\.com", "https://haxloppd.com", url)
        headers = {"User-Agent": BROWSER_UA, "Referer": url}
        try:
            r = self.session.get(url, headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                return None
            text = unpack_html(r.text)
        except requests.RequestException:
            return None

        m_stream = re.search(r"""(?:file|source|src)\s*:\s*["'](https?://[^"']*?(?:master\.txt|master\.m3u8|\.m3u8)[^"']*?)["']""", text, re.IGNORECASE)
        if not m_stream:
            m_stream = re.search(r'https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*', text)
        if not m_stream:
            return None

        stream_url = m_stream.group(1 if m_stream.groups() else 0)
        res = self.inspect_resolution(stream_url, headers=headers, text_content=text)
        return stream_url, headers, res

    def extract_mp4upload(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        if not url:
            return None
        headers = {"User-Agent": BROWSER_UA, "Referer": url}
        try:
            r = self.session.get(url, headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                return None
            text = unpack_html(r.text)
        except requests.RequestException:
            return None

        m = re.search(r'src:\s*"(https?://[^"\']+\.mp4)"', text)
        if not m:
            m = re.search(r'player\.src\(\s*["\'](https?://[^"\']+\.mp4)["\']\s*\)', text)
        if not m:
            return None
        stream_url = m.group(1)
        res = self.inspect_resolution(stream_url, headers=headers, text_content=text)
        return stream_url, headers, res

    def extract_forafile(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        if not url:
            return None
        headers = {"User-Agent": BROWSER_UA, "Referer": url}
        try:
            r = self.session.get(url, headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                return None
            text = unpack_html(r.text)
        except requests.RequestException:
            return None

        m = re.search(r'file\s*:\s*["\'](https?://[^"\']+)["\']', text)
        if not m:
            return None
        stream_url = m.group(1)
        res = self.inspect_resolution(stream_url, headers=headers, text_content=text)
        return stream_url, headers, res

    def extract_firestream(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        if not url:
            return None
        headers = {"User-Agent": BROWSER_UA, "Referer": url}
        try:
            r = self.session.get(url, headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                return None
            text = r.text
        except requests.RequestException:
            return None

        m = re.search(r'<script\s+id=["\']video-data["\']\s+type=["\']application/json["\']>(.*?)</script>', text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                stream_url = data.get("file")
                if stream_url and stream_url.startswith("http"):
                    res = self.inspect_resolution(stream_url, headers=headers, text_content=text)
                    return stream_url, headers, res
            except Exception:
                pass
        return None

    def extract_vidtube(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        if not url:
            return None
        headers = {"User-Agent": BROWSER_UA, "Referer": url}
        try:
            r = self.session.get(url, headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                return None
            text = unpack_html(r.text)
        except requests.RequestException:
            return None

        m = re.search(r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+)["\']', text)
        if not m:
            m = re.search(r'https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*', text)
        if not m:
            return None
        stream_url = m.group(1 if m.groups() else 0)
        res = self.inspect_resolution(stream_url, headers=headers, text_content=text)
        return stream_url, headers, res

    def extract_generic(self, url: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        if not url or not url.startswith("http"):
            return None
        lowered = url.lower()
        if any(ext in lowered for ext in (".mp4", ".m3u8", ".mkv")):
            res = self.inspect_resolution(url, headers={"User-Agent": BROWSER_UA})
            return url, {"User-Agent": BROWSER_UA}, res
        headers = {"User-Agent": BROWSER_UA, "Referer": url}
        try:
            r = self.session.get(url, headers=headers, timeout=min(6, self.timeout))
            if r.status_code != 200:
                return None
            text = unpack_html(r.text)
        except requests.RequestException:
            return None

        m = re.search(r'https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*', text)
        if m:
            stream_url = m.group(0)
            res = self.inspect_resolution(stream_url, headers=headers, text_content=text)
            return stream_url, headers, res
        return None

    def hls_from_page(
        self,
        url: str,
        referer: str,
    ) -> Optional[Tuple[str, Dict[str, str]]]:
        """Best-effort Uqload/Lulustream extraction (HLS)."""
        res = self.extract_uqload(url) or self.extract_lulustream(url)
        if res:
            return res[0], res[1]
        return None

    def extract_server(self, server: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raw_label = str(server.get("label") or "").strip()
        url = str(server.get("url") or "").strip()
        if not url or not url.startswith("http"):
            return None

        lowered_label = raw_label.lower()
        lowered_url = url.lower()
        result: Optional[Tuple[str, Dict[str, str], str]] = None

        if "backup" in lowered_label:
            result = self.extract_backup(url)
        elif "uqload" in lowered_label or "uqload" in lowered_url:
            result = self.extract_uqload(url)
        elif "savefiles" in lowered_label or "savefiles" in lowered_url:
            result = self.extract_savefiles(url)
        elif "mixdrop" in lowered_label or "mixdrop" in lowered_url:
            result = self.extract_mixdrop(url)
        elif "lulustream" in lowered_label or "lulustream" in lowered_url or "luluvdo" in lowered_url:
            result = self.extract_lulustream(url)
        elif "streamhg" in lowered_label or "streamhg" in lowered_url or "hgcloud" in lowered_url:
            result = self.extract_streamhg(url)
        elif "mp4upload" in lowered_label or "mp4upload" in lowered_url:
            result = self.extract_mp4upload(url)
        elif "forafile" in lowered_label or "forafile" in lowered_url:
            result = self.extract_forafile(url)
        elif "firestream" in lowered_label or "firestream" in lowered_url:
            result = self.extract_firestream(url)
        elif "vidtube" in lowered_label or "vidtube" in lowered_url or "watchtube" in lowered_url:
            result = self.extract_vidtube(url)
        else:
            result = self.extract_generic(url)

        if not result or not result[0]:
            return None

        stream_url, headers, res_hint = result
        if not res_hint or res_hint == "Auto":
            res_hint = self.inspect_resolution(stream_url, headers=headers)
        if not res_hint or res_hint == "Auto":
            res_hint = "720p"

        display_label = raw_label or "Server"
        display_label = display_label.capitalize() if display_label.islower() else display_label

        return {
            "label": display_label,
            "url": stream_url,
            "headers": headers,
            "res": res_hint,
            "server_key": display_label.replace(" ", "_"),
        }

    def extract_all(
        self,
        servers: Iterable[Dict[str, Any]],
        max_workers: int = 5,
    ) -> List[Dict[str, Any]]:
        server_list = [
            s for s in (servers or [])
            if isinstance(s, dict) and str(s.get("url") or "").strip().startswith("http")
        ]
        if not server_list:
            return []

        results: List[Optional[Dict[str, Any]]] = [None] * len(server_list)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(self.extract_server, s): idx
                for idx, s in enumerate(server_list)
            }
            for future in concurrent.futures.as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    res = future.result()
                    if res:
                        results[idx] = res
                except Exception as exc:
                    logger.debug("STARDIMA", f"Extractor error for server {server_list[idx]}: {exc}")

        extracted = []
        seen_urls = set()

        for item in results:
            if item and item.get("label", "").lower() == "backup":
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    extracted.append(item)

        for item in results:
            if item and item.get("label", "").lower() != "backup":
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    extracted.append(item)

        return extracted
