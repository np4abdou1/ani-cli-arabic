"""
Anime Slayer Provider Implementation
Reverse-engineered Android API client with first-party CDN decryption,
multi-server direct link extraction, and high-compatibility streaming for ani-cli-arabic.
"""

import base64
import hashlib
import html
import json
import re
import urllib.parse
import threading
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad

from curl_cffi import requests
import time
from .base import BaseAnimeProvider
from ..models import AnimeResult, Episode, QualityOption
from ..config import POPULAR_STUDIOS_MAP, GENRE_NAME_TO_SLUG
from ..logger import logger

# Complete official Anime Slayer Genre Map (from animes/get-anime-dropdowns)
SLAYER_GENRE_MAP: Dict[str, str] = {
    "action": "1", "adventure": "2", "cars": "3", "comedy": "4", "dementia": "5",
    "demons": "6", "mystery": "7", "drama": "8", "ecchi": "9", "fantasy": "10",
    "game": "11", "historical": "12", "horror": "13", "kids": "14", "magic": "15",
    "martial-arts": "16", "martial arts": "16", "mecha": "17", "music": "18",
    "parody": "19", "samurai": "20", "romance": "21", "school": "22", "sci-fi": "23",
    "scifi": "23", "shoujo": "24", "shounen": "25", "space": "26", "sports": "27",
    "super-power": "28", "super power": "28", "vampire": "29", "harem": "30",
    "slice-of-life": "31", "slice of life": "31", "supernatural": "32", "military": "33",
    "police": "34", "detective": "34", "psychological": "35", "suspense": "36",
    "thriller": "36", "seinen": "37", "josei": "38", "isekai": "39",
    # Arabic mappings
    "اكشن": "1", "أكشن": "1", "مغامرات": "2", "مغامرة": "2", "سيارات": "3",
    "كوميديا": "4", "كوميدي": "4", "جنون": "5", "شياطين": "6", "غموض": "7",
    "دراما": "8", "ايتشي": "9", "إيتشي": "9", "خيال": "10", "العاب": "11", "ألعاب": "11",
    "تاريخي": "12", "رعب": "13", "اطفال": "14", "أطفال": "14", "سحر": "15",
    "فنون قتالية": "16", "ميكا": "17", "موسيقى": "18", "محاكاة ساخرة": "19",
    "ساموراي": "20", "رومانسي": "21", "مدرسي": "22", "خيال علمي": "23",
    "شوجو": "24", "شوچو": "24", "شونين": "25", "فضاء": "26", "رياضي": "27",
    "قوى خارقة": "28", "مصاص دماء": "29", "مصاصي دماء": "29", "حريم": "30",
    "شريحة من الحياة": "31", "الحياة اليومية": "31", "خارق للطبيعة": "32",
    "عسكري": "33", "بوليسي": "34", "نفسي": "35", "اثارة": "36", "إثارة": "36",
    "تشويق": "36", "سينين": "37", "جوسي": "38", "ايسيكاي": "39", "إيسيكاي": "39",
}

# Complete official Anime Slayer Studio Map (from animes/get-anime-dropdowns)
SLAYER_STUDIO_MAP: Dict[str, str] = {
    "mappa": "132", "ufotable": "52", "madhouse": "24", "wit studio": "144", "wit": "144",
    "bones": "41", "kyoto animation": "47", "toei animation": "2", "studio pierrot": "447",
    "pierrot": "447", "a-1 pictures": "82", "a1 pictures": "82", "cloverworks": "192",
    "white fox": "101", "david production": "93", "shaft": "42", "trigger": "137",
    "production i.g": "23", "production ig": "23", "j.c.staff": "22", "jcstaff": "22",
    "tms entertainment": "30", "studio deen": "15", "deen": "15", "lerche": "108",
    "p.a. works": "87", "pa works": "87", "comix wave films": "70", "gainax": "20",
    "sunrise": "12", "studio ghibli": "4", "ghibli": "4", "8bit": "124", "doga kobo": "71",
    "silver link.": "95", "silver link": "95", "kinema citrus": "92", "studio bind": "253",
    "lidenfilms": "134", "feel.": "48", "feel": "48", "brain's base": "33", "troyca": "147",
    "passione": "119", "science saru": "236", "bandai namco pictures": "125",
    "studio colorido": "189", "orange": "138", "gonzo": "39", "tezuka productions": "131",
    "nippon animation": "6"
}


class AnimeSlayerProvider(BaseAnimeProvider):
    """
    Official Anime Slayer Android API Provider.
    Includes native token flow, AES encryption, RNCryptor v3 payload decryption,
    and multi-provider direct stream extractors (MediaFire, Google Drive, Mp4Upload, OK.ru).
    """

    id: str = "anime_slayer"
    name: str = "Anime Slayer"
    description: str = "Official mobile API provider for Anime Slayer (أنمي سلاير)"

    BASE_URL = "https://anslayer.com/anime/public/"
    CLIENT_ID = "android-app2"
    CLIENT_SECRET = "7befba6263cc14c90d2f1d6da2c5cf9b251bfbbd"
    APK_CERT_SHA1 = "44D8B79265DDBB9C887320F64521A76D72F6D7D4"
    RNC_PASSWORD = b"android-app9>E>VBa=X%;[5BX~=Q~K"

    HEADERS = {
        "Client-Id": CLIENT_ID,
        "Client-Secret": CLIENT_SECRET,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }

    def __init__(self):
        self._local = threading.local()
        self._cache_lock = threading.Lock()
        self._anime_cache: Dict[str, AnimeResult] = {}
        self._episode_cache: Dict[str, List[Episode]] = {}

    def _get_session(self) -> requests.Session:
        if not hasattr(self._local, "session") or self._local.session is None:
            self._local.session = requests.Session(
                impersonate="chrome120",
                timeout=12
            )
        return self._local.session

    def _api_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        s = self._get_session()
        url = f"{self.BASE_URL}{endpoint}" if not endpoint.startswith("http") else endpoint
        t0 = time.time()
        try:
            r = s.get(url, params=params, headers=self.HEADERS, timeout=10)
            logger.log_request("GET", url, params=params, status_code=r.status_code, duration=time.time() - t0)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.log_request("GET", url, params=params, duration=time.time() - t0, error=e)
        return None

    def _api_post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        s = self._get_session()
        url = f"{self.BASE_URL}{endpoint}" if not endpoint.startswith("http") else endpoint
        headers = {**self.HEADERS, "Content-Type": "application/x-www-form-urlencoded"}
        t0 = time.time()
        try:
            r = s.post(url, data=data, headers=headers, timeout=10)
            logger.log_request("POST", url, data=data, status_code=r.status_code, duration=time.time() - t0)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.log_request("POST", url, data=data, duration=time.time() - t0, error=e)
        return None

    def _clean_episode_title(self, raw_name: str, ep_num: int) -> str:
        """Strip redundant 'Episode X' / 'الحلقة X' prefix and doubled numbering."""
        if not raw_name:
            return ""
        name = str(raw_name).strip()
        # Remove patterns like "الحلقة : 1", "الحلقة 1", "Episode 1", "Ep 1", "الحلقه : 1"
        cleaned = re.sub(r'^(الحلقة|الحلقه|Episode|Ep|EP)\s*[:\s\-]*\d+\s*[:\s\-]*', '', name, flags=re.IGNORECASE).strip()
        # If what remains is just digits or identical to ep_num, return empty string (only show number in UI)
        if not cleaned or re.fullmatch(r'^\d+$', cleaned) or cleaned == str(ep_num):
            return ""
        return cleaned

    def search_anime(self, query: str) -> List[AnimeResult]:
        """Search Anime Slayer catalog using the official published animes API."""
        query = query.strip()
        if not query:
            return []

        payload = {"list_type": "anime_list", "anime_name": query, "limit": 30}
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        return self._parse_results(data)

    def get_anime_details(self, anime_id: str) -> AnimeResult:
        """Fetch complete anime details and metadata."""
        aid = str(anime_id).strip()
        with self._cache_lock:
            if aid in self._anime_cache:
                return self._anime_cache[aid]

        # If anime_id is not numeric (e.g. slug "death-note"), resolve by search first
        if not aid.isdigit():
            clean_title = aid.replace("-", " ")
            search_hits = self.search_anime(clean_title)
            if search_hits:
                resolved_aid = search_hits[0].id
                details = self.get_anime_details(resolved_aid)
                with self._cache_lock:
                    self._anime_cache[aid] = details
                return details
            # Fallback to Anime3rb
            try:
                from .manager import ProviderManager
                details = ProviderManager.get_provider("anime3rb").get_anime_details(aid)
                if details and details.thumbnail and details.title_en != aid:
                    with self._cache_lock:
                        self._anime_cache[aid] = details
                    return details
            except Exception:
                pass

        data = self._api_get("anime/get-anime-details", params={
            "anime_id": aid,
            "fetch_episodes": "Yes",
            "more_info": "Yes"
        })

        if not data or "response" not in data:
            # Fallback to Anime3rb
            try:
                from .manager import ProviderManager
                return ProviderManager.get_provider("anime3rb").get_anime_details(aid)
            except Exception:
                return AnimeResult(id=aid, title_en=aid, thumbnail="")

        d = data["response"]
        title_ar = d.get("anime_name") or ""
        title_en = d.get("anime_english_title") or title_ar
        score = str(d.get("anime_rating") or "N/A")
        cover = d.get("anime_cover_image_url") or ""
        story = d.get("anime_story") or ""
        atype = d.get("anime_type") or "مسلسل"

        # Cache episodes if present
        eps_raw = d.get("episodes")
        if isinstance(eps_raw, dict):
            eps_data = eps_raw.get("data", []) or []
        elif isinstance(eps_raw, list):
            eps_data = eps_raw
        else:
            eps_data = []
        if eps_data:
            episodes = []
            for it in eps_data:
                ep_id = str(it.get("episode_id") or "")
                ep_name = it.get("episode_name") or ""
                num_raw = str(it.get("episode_number") or "1")
                try:
                    ep_num = int(float(num_raw))
                except ValueError:
                    ep_num = 1
                
                cleaned_title = self._clean_episode_title(ep_name, ep_num)
                servers = it.get("episode_urls") or []
                servers_json = json.dumps(servers)
                
                episodes.append(Episode(
                    number=str(ep_num),
                    display_num=ep_num,
                    title=cleaned_title,
                    url=servers_json,
                    servers=servers
                ))
            episodes.sort(key=lambda x: x.display_num)
            with self._cache_lock:
                self._episode_cache[aid] = episodes

        res = AnimeResult(
            id=aid,
            title_en=title_en,
            title_ar=title_ar,
            thumbnail=cover,
            score=score,
            type=atype,
            synopsis=story
        )
        with self._cache_lock:
            self._anime_cache[aid] = res
        return res

    def get_episodes(self, anime_id: str) -> List[Episode]:
        """Fetch all episodes with server links for the anime."""
        aid = str(anime_id).strip()
        with self._cache_lock:
            if aid in self._episode_cache:
                return self._episode_cache[aid]

        # If anime_id is not numeric (e.g. slug "death-note"), resolve by search first
        if not aid.isdigit():
            clean_title = aid.replace("-", " ")
            search_hits = self.search_anime(clean_title)
            if search_hits:
                resolved_aid = search_hits[0].id
                eps = self.get_episodes(resolved_aid)
                if eps:
                    with self._cache_lock:
                        self._episode_cache[aid] = eps
                    return eps
            # Fallback to Anime3rb
            try:
                from .manager import ProviderManager
                eps = ProviderManager.get_provider("anime3rb").get_episodes(aid)
                if eps:
                    with self._cache_lock:
                        self._episode_cache[aid] = eps
                    return eps
            except Exception:
                pass

        self.get_anime_details(aid)
        with self._cache_lock:
            eps = self._episode_cache.get(aid, [])

        # Fallback to Anime3rb if Slayer returned 0 eps
        if not eps:
            try:
                from .manager import ProviderManager
                eps = ProviderManager.get_provider("anime3rb").get_episodes(aid)
                if eps:
                    with self._cache_lock:
                        self._episode_cache[aid] = eps
            except Exception:
                pass
        return eps

    def get_episode_streams(self, episode: Episode) -> List[QualityOption]:
        """
        Extract direct CDN and third-party streaming links for an episode.
        CDN servers are named 'CDN > 1080p', 'CDN > 720p', 'CDN > 480p' and grouped at top.
        """
        cdn_qualities = []
        other_qualities = []
        multi_urls = []

        server_list = episode.servers or []
        if not server_list and episode.url:
            try:
                server_list = json.loads(episode.url)
            except Exception:
                if episode.url.startswith("http"):
                    server_list = [{"episode_server_name": "cdn", "episode_url": episode.url}]

        for srv in server_list:
            srv_name = (srv.get("episode_server_name") or "").lower().strip()
            srv_url = srv.get("episode_url") or ""

            if not srv_url:
                continue

            # 1. First-Party CDN Token Resolver
            if srv_name == "cdn" or "vq.php" in srv_url or "v-qs.php" in srv_url:
                cdn_streams = self._resolve_cdn_stream(srv_url)
                cdn_qualities.extend(cdn_streams)

                # Synthesize fallback muilt URL if missing
                try:
                    parsed = urllib.parse.urlparse(srv_url)
                    params = urllib.parse.parse_qs(parsed.query)
                    f_val = params.get("f", [""])[0]
                    e_val = params.get("e", [""])[0].split("|")[0]
                    if f_val and e_val:
                        multi_urls.append(f"https://anslayer.com/la/public/api/f2?n={f_val}\\{e_val}")
                except Exception:
                    pass

            # 2. Multi-Server Array Resolver
            elif srv_name == "muilt" or "/api/f" in srv_url:
                multi_urls.append(srv_url)

        # Resolve all external multi-server links (strictly once per episode slug)
        queried_slugs = set()
        for m_url in multi_urls:
            parsed = urllib.parse.urlparse(m_url)
            params = urllib.parse.parse_qs(parsed.query)
            n_val = params.get("n", [""])[0]
            if not n_val:
                m = re.search(r"n=([^&]+)", m_url)
                n_val = m.group(1) if m else ""

            if n_val and n_val not in queried_slugs:
                queried_slugs.add(n_val)
                multi_streams = self._resolve_multi_servers(m_url)
                other_qualities.extend(multi_streams)

        # Sort CDN streams by resolution (1080p -> 720p -> 480p)
        res_rank = {"1080p": 3, "720p": 2, "480p": 1, "360p": 0}
        cdn_qualities.sort(key=lambda q: res_rank.get(q.resolution, 0), reverse=True)

        # Combine: CDN streams first, followed by third-party direct streams (deduplicated by canonical key)
        seen_keys = set()
        qualities = []
        for q in cdn_qualities:
            k = q.url
            if k and k not in seen_keys:
                seen_keys.add(k)
                qualities.append(q)

        for q in other_qualities:
            k = self._canonical_host_key(q.url)
            if k and k not in seen_keys:
                seen_keys.add(k)
                qualities.append(q)

        if not qualities and episode.url and episode.url.startswith("http"):
            qualities.append(QualityOption(
                name="CDN > Direct Stream",
                server_key="Auto",
                direct_url=episode.url,
                res="Auto"
            ))

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

        current_ep = {}
        qualities = []
        direct_streams = {}

        for s in streams:
            res = s.resolution or "720p"
            if "1080" in res and "FRFhdQ" not in current_ep:
                current_ep["FRFhdQ"] = s.url
            elif "720" in res and "FRLink" not in current_ep:
                current_ep["FRLink"] = s.url
            elif ("480" in res or "360" in res) and "FRLowQ" not in current_ep:
                current_ep["FRLowQ"] = s.url

            qualities.append(s)
            direct_streams[res] = s.url

        if not current_ep and streams:
            current_ep["FRLink"] = streams[0].url

        return {
            "CurrentEpisode": current_ep,
            "Qualities": qualities,
            "DirectStreams": direct_streams
        }

    def _resolve_cdn_stream(self, cdn_url: str) -> List[QualityOption]:
        """Decrypt first-party signed backup CDN streams named CDN > 1080p, CDN > 720p, CDN > 480p."""
        results = []
        try:
            parsed = urllib.parse.urlparse(cdn_url)
            params = urllib.parse.parse_qs(parsed.query)
            f_val = params.get("f", [""])[0]
            e_val = params.get("e", [""])[0]

            if not f_val or not e_val:
                return results

            s = self._get_session()
            
            # 1. Fetch dynamic google.php seed
            seed_res = s.get(f"{self.BASE_URL}google.php", headers=self.HEADERS, timeout=6)
            if seed_res.status_code != 200:
                logger.error("CRYPTO", f"Failed to fetch dynamic seed from google.php (HTTP {seed_res.status_code})")
                return results
            seed = seed_res.text.strip()
            logger.log_crypto("Fetched dynamic google.php seed", f"seed={seed}")

            # 2. Derive AES Key: (seed[0:10] + certSha1[0:22])[0:16]
            key_str = (seed[:10] + self.APK_CERT_SHA1[:22])[:16]
            key_bytes = key_str.encode("utf-8")

            # 3. Encrypt compact native payload
            native_json = json.dumps({
                "uhy": "com.anslayer",
                "dma": 47,
                "mvd": "1.5.10",
                "vko": self.APK_CERT_SHA1
            }, separators=(",", ":"))

            cipher = AES.new(key_bytes, AES.MODE_ECB)
            encrypted = cipher.encrypt(pad(native_json.encode("utf-8"), 16))
            b64_enc = base64.b64encode(encrypted).decode("utf-8")
            logger.log_crypto("Generated native AES token", f"inf_len={len(b64_enc)}")

            inf_str = json.dumps({"a": b64_enc, "b": seed}, separators=(",", ":"))

            # 4. POST to v-qs.php
            post_data = {
                "f": f_val,
                "e": e_val,
                "inf": inf_str
            }
            vqs_res = s.post(f"{self.BASE_URL}v-qs.php", data=post_data, headers={
                **self.HEADERS,
                "Content-Type": "application/x-www-form-urlencoded"
            }, timeout=8)

            if vqs_res.status_code == 200 and vqs_res.text.strip():
                raw_b64 = vqs_res.text.strip()
                envelope = base64.b64decode(raw_b64)

                # 5. Decrypt RNCryptor v3 envelope
                if len(envelope) > 66:
                    enc_salt = envelope[2:10]
                    iv = envelope[18:34]
                    ciphertext = envelope[34:-32]

                    enc_key = hashlib.pbkdf2_hmac("sha1", self.RNC_PASSWORD, enc_salt, 10000, 32)
                    aes_dec = AES.new(enc_key, AES.MODE_CBC, iv)
                    plaintext = unpad(aes_dec.decrypt(ciphertext), 16)
                    stream_list = json.loads(plaintext.decode("utf-8"))
                    logger.log_crypto("Decrypted RNCryptor v3 payload", f"{len(stream_list)} direct streams found")

                    for item in stream_list:
                        file_url = item.get("file") or ""
                        if not file_url:
                            continue

                        # Determine quality from filename
                        res = "720p"
                        server_label = "CDN > 720p"
                        if "hh.mp4" in file_url:
                            res = "1080p"
                            server_label = "CDN > 1080p HQ"
                        elif "h.mp4" in file_url:
                            res = "1080p"
                            server_label = "CDN > 1080p"
                        elif "s.mp4" in file_url:
                            res = "720p"
                            server_label = "CDN > 720p"
                        elif "m.mp4" in file_url:
                            res = "480p"
                            server_label = "CDN > 480p"

                        results.append(QualityOption(
                            name=server_label,
                            server_key=res,
                            direct_url=file_url,
                            res=res,
                            style="success" if res == "1080p" else "info"
                        ))
        except Exception:
            pass

        return results

    def _extract_mediafire_direct(self, url: str) -> Optional[str]:
        """Scrape direct download stream from MediaFire page."""
        try:
            s = self._get_session()
            r = s.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=6)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                btn = soup.find("a", {"id": "downloadButton"}) or soup.find("a", {"aria-label": "Download file"})
                if btn and btn.get("href") and btn.get("href").startswith("http"):
                    return btn.get("href")
                m = re.search(r'href=[\"\'](https?://download[^\"]+)[\"\']', r.text)
                if m:
                    return m.group(1).replace("&amp;", "&")
        except Exception:
            pass
        return None

    def _extract_gdrive_direct(self, url: str) -> Optional[str]:
        """Verify, resolve, and extract authenticated direct streaming link for Google Drive."""
        m = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url) or re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if not m:
            return None
        fid = m.group(1)

        s = self._get_session()
        probe_url = f"https://drive.google.com/uc?export=download&id={fid}"
        try:
            r = s.get(probe_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
            }, timeout=4, allow_redirects=True)

            # If 404 or dead, do not return dead link
            if r.status_code == 404:
                return None

            ctype = r.headers.get("Content-Type", "").lower()
            if "video" in ctype or "octet-stream" in ctype or (".mp4" in r.url and "text/html" not in ctype):
                return r.url

            # Handle virus scan / large file confirmation page
            if "confirm=" in r.text or "download_warning" in r.text or "uc-download-link" in r.text or "download-form" in r.text:
                # 1. Look for form action
                m_form = re.search(r'<form[^>]+action=[\"\']([^\"\']+)[\"\']', r.text)
                if m_form:
                    action = m_form.group(1)
                    if action.startswith("/"):
                        action = "https://drive.usercontent.google.com" + action
                    # Extract input tokens
                    inputs = dict(re.findall(r'<input[^>]+name=[\"\']([^\"\']+)[\"\'][^>]+value=[\"\']([^\"\']*)[\"\']', r.text))
                    if "id" in inputs or "confirm" in inputs or "uuid" in inputs:
                        r_post = s.post(action, data=inputs, timeout=4, stream=True, allow_redirects=True)
                        if r_post.status_code in (200, 206) and "text/html" not in r_post.headers.get("Content-Type", ""):
                            return r_post.url

                # 2. Look for confirm token in query
                m_conf = re.search(r'confirm=([a-zA-Z0-9_-]+)', r.text)
                if m_conf:
                    token = m_conf.group(1)
                    direct_url = f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm={token}"
                    r_tok = s.get(direct_url, timeout=4, stream=True, allow_redirects=True)
                    if r_tok.status_code in (200, 206) and "text/html" not in r_tok.headers.get("Content-Type", ""):
                        return r_tok.url

            # If Google Drive file view page returned HTTP 200 and is alive
            if r.status_code == 200 and "drive.google.com" in r.url and "Google Drive - Page Not Found" not in r.text:
                return f"https://drive.google.com/uc?export=download&id={fid}"
        except Exception:
            pass

        return None

    def _extract_mp4upload_direct(self, url: str) -> Optional[str]:
        """Extract direct mp4 link from Mp4Upload page."""
        try:
            s = self._get_session()
            r = s.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=6)
            if r.status_code == 200:
                m = re.search(r'player\.src\({\s*type:\s*[\"\']video/mp4[\"\'],\s*src:\s*[\"\'](https?://[^\"]+)[\"\']', r.text)
                if m:
                    return m.group(1)
                m2 = re.search(r'src:\s*[\"\'](https?://[^\"]+\.mp4[^\"]*)[\"\']', r.text)
                if m2:
                    return m2.group(1)
        except Exception:
            pass
        return None

    def _extract_goodstream_direct(self, url: str) -> Optional[str]:
        """Extract master HLS stream playlist from Goodstream embed."""
        try:
            s = self._get_session()
            r = s.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=6)
            if r.status_code == 200:
                m = re.search(r'[\"\'](https?://[^\"\']+\.m3u8[^\"\']*)[\"\']', r.text)
                if m:
                    return m.group(1)
        except Exception:
            pass
        return None

    def _extract_okru_direct(self, url: str) -> Optional[str]:
        """Extract direct video stream from OK.ru embed."""
        try:
            mid_match = re.search(r'/video/(\d+)', url)
            if mid_match:
                mid = mid_match.group(1)
                s = self._get_session()
                r = s.get(f"https://ok.ru/videoembed/{mid}", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=6)
                if r.status_code == 200:
                    m = re.search(r'data-options=[\"\'](\{.*?\})[\"\']', r.text)
                    if m:
                        data = json.loads(html.unescape(m.group(1)))
                        videos = data.get("videos", []) or data.get("flashvars", {}).get("metadata", {}).get("videos", [])
                        if videos:
                            return videos[-1].get("url")
        except Exception:
            pass
        return None

    def _check_stream_live(self, url: str, timeout: float = 2.0) -> bool:
        """Fast check to verify if a video stream URL is actually reachable and not 404."""
        if not url or not url.startswith("http"):
            return False
        try:
            s = self._get_session()
            r = s.head(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=timeout, allow_redirects=True)
            if r.status_code in (200, 206, 302):
                ctype = r.headers.get("Content-Type", "").lower()
                if "video" in ctype or "octet-stream" in ctype or ".mp4" in url or "ab-hunter" in url or "mediafire" in url or ".m3u8" in url:
                    return True
            elif r.status_code == 404:
                return False
        except Exception:
            pass
        return False

    def _canonical_host_key(self, url: str) -> str:
        """Extract canonical unique host key to prevent duplicate network scraping across mirrors."""
        u = url.strip()
        m = re.search(r"mediafire\.com/(?:file_premium/|file/|\?)?([a-zA-Z0-9]+)", u)
        if m:
            return f"mediafire:{m.group(1)}"
        m = re.search(r"(?:drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)|drive\.usercontent\.google\.com/download\?id=)([a-zA-Z0-9_-]+)", u)
        if m:
            return f"gdrive:{m.group(1)}"
        m = re.search(r"ok\.ru/(?:video/|videoembed/)(\d+)", u)
        if m:
            return f"okru:{m.group(1)}"
        m = re.search(r"mp4upload\.com/(?:embed-)?([a-zA-Z0-9]+)", u)
        if m:
            return f"mp4upload:{m.group(1)}"
        m = re.search(r"mixdrop\.(?:co|to|ch)/(?:e/|f/)?([a-zA-Z0-9]+)", u)
        if m:
            return f"mixdrop:{m.group(1)}"
        m = re.search(r"uptostream\.com/(?:iframe/)?([a-zA-Z0-9]+)", u)
        if m:
            return f"uptostream:{m.group(1)}"
        m = re.search(r"(?:fembed\.com|vcdn\.io)/api/source/([a-zA-Z0-9]+)", u)
        if m:
            return f"fembed:{m.group(1)}"
        m = re.search(r"streamtape\.(?:to|com|net)/[ve]/([a-zA-Z0-9]+)", u)
        if m:
            return f"streamtape:{m.group(1)}"
        m = re.search(r"goodstream\.one/video/embed/([a-zA-Z0-9]+)", u)
        if m:
            return f"goodstream:{m.group(1)}"
        m = re.search(r"vinovo\.to/e/([a-zA-Z0-9]+)", u)
        if m:
            return f"vinovo:{m.group(1)}"
        m = re.search(r"dood\.(?:to|watch|so|pm|ws)/[ed]/([a-zA-Z0-9]+)", u)
        if m:
            return f"dood:{m.group(1)}"
        m = re.search(r"filemoon\.(?:sx|to|in)/[ed]/([a-zA-Z0-9]+)", u)
        if m:
            return f"filemoon:{m.group(1)}"
        m = re.search(r"pixeldrain\.com/[ul]/([a-zA-Z0-9]+)", u)
        if m:
            return f"pixeldrain:{m.group(1)}"
        m = re.search(r"lulustream\.com/[ed]/([a-zA-Z0-9]+)", u)
        if m:
            return f"lulustream:{m.group(1)}"
        m = re.search(r"vidmoly\.(?:me|to)/[we]/([a-zA-Z0-9]+)", u)
        if m:
            return f"vidmoly:{m.group(1)}"
        m = re.search(r"vidoza\.net/(?:embed-)?([a-zA-Z0-9]+)", u)
        if m:
            return f"vidoza:{m.group(1)}"
        m = re.search(r"streamwish\.(?:to|com)/[ed]/([a-zA-Z0-9]+)", u)
        if m:
            return f"streamwish:{m.group(1)}"
        m = re.search(r"filelions\.(?:online|to|com)/[ed]/([a-zA-Z0-9]+)", u)
        if m:
            return f"filelions:{m.group(1)}"
        return re.sub(r"^https?://(?:www\.)?", "", u).rstrip("/")

    def _detect_resolution(self, url: str, default: str = "1080p") -> str:
        """Accurately detect video resolution from stream filename or direct URL."""
        u_lower = url.lower()
        if "1080" in u_lower or "fhd" in u_lower or "uhd" in u_lower or re.search(r"[/_.-]hh\.mp4", u_lower):
            return "1080p"
        if "720" in u_lower or "hd" in u_lower or re.search(r"[/_.-]h\.mp4", u_lower):
            return "720p"
        if "480" in u_lower or "sd" in u_lower or re.search(r"[/_.-]s\.mp4", u_lower):
            return "480p"
        if "360" in u_lower or "mobile" in u_lower or re.search(r"[/_.-]m\.mp4", u_lower):
            return "360p"
        return default

    def _resolve_multi_servers(self, multi_url: str) -> List[QualityOption]:
        """Expand third-party stream servers from Anime Slayer multi arrays with strict deduplication and quality detection."""
        results = []
        parsed = urllib.parse.urlparse(multi_url)
        params = urllib.parse.parse_qs(parsed.query)
        n_val = params.get("n", [""])[0]
        if not n_val:
            m = re.search(r"n=([^&]+)", multi_url)
            n_val = m.group(1) if m else ""

        if not n_val:
            return results

        target_urls = [
            f"https://anslayer.com/la/public/api/f2?n={n_val}",
            f"https://anslayer.com/la/public/api/f?n={n_val}",
            f"https://a-reslayer.com/la/public/api/f?n={n_val}",
            f"https://a-reslayer.com/la/public/api/f2?n={n_val}",
        ]

        all_raw_links = set()
        s = self._get_session()

        def _fetch_endpoint(u):
            try:
                r = s.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, str) and item.startswith("http"):
                                all_raw_links.add(item)
            except Exception:
                pass

        try:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(_fetch_endpoint, target_urls))
        except Exception:
            for u in target_urls:
                _fetch_endpoint(u)

        # Deduplicate input links by canonical host key before scraping
        seen_keys = set()
        deduped_raw = []
        for link in all_raw_links:
            # Filter dead / parked hosts
            if any(d in link for d in ("tune.pk", "vidlox.me", "jawcloud.co", "streamvid.net", "streamhub.ink", "highstream.tv")):
                continue
            k = self._canonical_host_key(link)
            if k not in seen_keys:
                seen_keys.add(k)
                deduped_raw.append(link)

        # Track quality names per host to prevent duplicate labels
        used_labels = set()

        for link in deduped_raw:
            # 1. MediaFire direct resolution
            if "mediafire" in link:
                direct_link = self._extract_mediafire_direct(link)
                if direct_link:
                    res = self._detect_resolution(direct_link, default="1080p")
                    label = f"MediaFire > {res}"
                    if label in used_labels:
                        idx = 2
                        while f"MediaFire #{idx} > {res}" in used_labels:
                            idx += 1
                        label = f"MediaFire #{idx} > {res}"
                    used_labels.add(label)
                    results.append(QualityOption(
                        name=label,
                        server_key=res,
                        direct_url=direct_link,
                        res=res
                    ))
            # 2. Google Drive direct resolution
            elif "drive.google" in link:
                direct_link = self._extract_gdrive_direct(link)
                if direct_link:
                    res = self._detect_resolution(direct_link, default="1080p")
                    label = f"Google Drive > {res}" if res != "1080p" else "Google Drive > Direct"
                    if label in used_labels:
                        idx = 2
                        while f"Google Drive #{idx} > Direct" in used_labels:
                            idx += 1
                        label = f"Google Drive #{idx} > Direct"
                    used_labels.add(label)
                    results.append(QualityOption(
                        name=label,
                        server_key=res,
                        direct_url=direct_link,
                        res=res
                    ))
            # 3. Mp4Upload direct resolution
            elif "mp4upload" in link:
                direct_link = self._extract_mp4upload_direct(link) or link
                res = self._detect_resolution(direct_link, default="1080p")
                label = f"Mp4Upload > {res}"
                if label in used_labels:
                    idx = 2
                    while f"Mp4Upload #{idx} > {res}" in used_labels:
                        idx += 1
                    label = f"Mp4Upload #{idx} > {res}"
                used_labels.add(label)
                results.append(QualityOption(
                    name=label,
                    server_key=res,
                    direct_url=direct_link,
                    res=res
                ))
            # 4. OK.ru direct resolution
            elif "ok.ru" in link:
                direct_link = self._extract_okru_direct(link) or link
                res = self._detect_resolution(direct_link, default="720p")
                label = f"OK.ru > {res}"
                if label in used_labels:
                    idx = 2
                    while f"OK.ru #{idx} > {res}" in used_labels:
                        idx += 1
                    label = f"OK.ru #{idx} > {res}"
                used_labels.add(label)
                results.append(QualityOption(
                    name=label,
                    server_key=res,
                    direct_url=direct_link,
                    res=res
                ))
            # 5. Goodstream direct resolution (master HLS playlist)
            elif "goodstream" in link:
                direct_link = self._extract_goodstream_direct(link) or link
                label = "Goodstream > Direct"
                if label in used_labels:
                    idx = 2
                    while f"Goodstream #{idx} > Direct" in used_labels:
                        idx += 1
                    label = f"Goodstream #{idx} > Direct"
                used_labels.add(label)
                results.append(QualityOption(
                    name=label,
                    server_key="Auto",
                    direct_url=direct_link,
                    res="Auto"
                ))
            # 6. Streamtape direct resolution
            elif "streamtape" in link:
                label = "Streamtape > Direct"
                if label in used_labels:
                    idx = 2
                    while f"Streamtape #{idx} > Direct" in used_labels:
                        idx += 1
                    label = f"Streamtape #{idx} > Direct"
                used_labels.add(label)
                results.append(QualityOption(
                    name=label,
                    server_key="Auto",
                    direct_url=link,
                    res="Auto"
                ))
            # 7. Vinovo direct resolution
            elif "vinovo" in link:
                label = "Vinovo > Direct"
                if label in used_labels:
                    idx = 2
                    while f"Vinovo #{idx} > Direct" in used_labels:
                        idx += 1
                    label = f"Vinovo #{idx} > Direct"
                used_labels.add(label)
                results.append(QualityOption(
                    name=label,
                    server_key="Auto",
                    direct_url=link,
                    res="Auto"
                ))
            # 8. Mixdrop direct resolution
            elif "mixdrop" in link:
                label = "Mixdrop > Direct"
                if label in used_labels:
                    idx = 2
                    while f"Mixdrop #{idx} > Direct" in used_labels:
                        idx += 1
                    label = f"Mixdrop #{idx} > Direct"
                used_labels.add(label)
                results.append(QualityOption(
                    name=label,
                    server_key="Auto",
                    direct_url=link,
                    res="Auto"
                ))
            # 9. Uptostream direct resolution
            elif "uptostream" in link:
                label = "Uptostream > Direct"
                if label in used_labels:
                    idx = 2
                    while f"Uptostream #{idx} > Direct" in used_labels:
                        idx += 1
                    label = f"Uptostream #{idx} > Direct"
                used_labels.add(label)
                results.append(QualityOption(
                    name=label,
                    server_key="Auto",
                    direct_url=link,
                    res="Auto"
                ))
            # 10. Fembed direct resolution
            elif "fembed" in link or "vcdn" in link:
                label = "Fembed > 720p"
                if label in used_labels:
                    idx = 2
                    while f"Fembed #{idx} > 720p" in used_labels:
                        idx += 1
                    label = f"Fembed #{idx} > 720p"
                used_labels.add(label)
                results.append(QualityOption(
                    name=label,
                    server_key="720p",
                    direct_url=link,
                    res="720p"
                ))
            # 11. Doodstream
            elif "dood" in link:
                label = "DoodStream > Direct"
                used_labels.add(label)
                results.append(QualityOption(name=label, server_key="Auto", direct_url=link, res="Auto"))
            # 12. Filemoon
            elif "filemoon" in link:
                label = "Filemoon > Direct"
                used_labels.add(label)
                results.append(QualityOption(name=label, server_key="Auto", direct_url=link, res="Auto"))
            # 13. Pixeldrain
            elif "pixeldrain" in link:
                label = "Pixeldrain > Direct"
                used_labels.add(label)
                results.append(QualityOption(name=label, server_key="Auto", direct_url=link, res="Auto"))
            # 14. Lulustream
            elif "lulustream" in link or "luluvdo" in link:
                label = "Lulustream > Direct"
                used_labels.add(label)
                results.append(QualityOption(name=label, server_key="Auto", direct_url=link, res="Auto"))
            # 15. Vidmoly
            elif "vidmoly" in link:
                label = "Vidmoly > Direct"
                used_labels.add(label)
                results.append(QualityOption(name=label, server_key="Auto", direct_url=link, res="Auto"))
            # 16. StreamWish
            elif "streamwish" in link:
                label = "StreamWish > Direct"
                used_labels.add(label)
                results.append(QualityOption(name=label, server_key="Auto", direct_url=link, res="Auto"))

        # Sort results descending by resolution
        res_order = {"1080p UHD": 5, "1080p": 4, "720p": 3, "480p": 2, "360p": 1, "Auto": 0}
        results.sort(key=lambda q: res_order.get(q.resolution, 0), reverse=True)
        return results

    def get_latest_episodes(self, limit: int = 20) -> List[Episode]:
        """Fetch newly released episodes across anime."""
        payload = {"list_type": "latest_episodes", "limit": limit}
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        
        episodes = []
        if not data:
            return episodes

        items = data.get("response", {}).get("data", []) or []
        for it in items:
            aid = str(it.get("anime_id") or "")
            title = it.get("anime_name") or ""
            ep_name = it.get("latest_episode_name") or "1"
            num_match = re.search(r"(\d+)", ep_name)
            ep_num = int(num_match.group(1)) if num_match else 1

            episodes.append(Episode(
                number=str(ep_num),
                display_num=ep_num,
                title=f"{title}",
                url=aid
            ))

        return episodes

    def get_pinned_anime(self, limit: int = 20) -> List[AnimeResult]:
        payload = {"list_type": "featured", "limit": limit}
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        items = self._parse_results(data)
        if not items:
            return self.get_top_rated_anime(0, limit)
        return items[:limit]

    def get_trending_anime(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        payload = {"list_type": "top_tv", "limit": limit, "offset": from_index}
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        return self._parse_results(data)

    def get_top_rated_anime(self, from_index: int = 0, limit: int = 20, rate_tier: str = "9-10") -> List[AnimeResult]:
        payload = {"list_type": "top_anime", "limit": limit, "offset": from_index}
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        return self._parse_results(data)

    def get_top_currently_airing(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        payload = {"list_type": "top_currently_airing", "limit": limit, "offset": from_index}
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        return self._parse_results(data)

    def get_top_anime_mal(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        payload = {"list_type": "top_anime_mal", "limit": limit, "offset": from_index}
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        return self._parse_results(data)

    def get_movies(self, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        payload = {"list_type": "top_movie", "limit": limit, "offset": from_index}
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        return self._parse_results(data)

    def get_genre_anime(self, genre_slug: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        g_key = (genre_slug or "").strip().lower()
        genre_id = SLAYER_GENRE_MAP.get(g_key) or SLAYER_GENRE_MAP.get(g_key.replace("-", " ")) or SLAYER_GENRE_MAP.get(g_key.replace(" ", "-"))
        
        if genre_id:
            payload = {"list_type": "filter", "anime_genre_ids": str(genre_id), "limit": limit, "offset": from_index}
        else:
            payload = {"list_type": "anime_list", "anime_name": genre_slug, "limit": limit, "offset": from_index}
            
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        return self._parse_results(data)

    def get_studio_anime(self, studio_name: str, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        s_key = (studio_name or "").strip().lower()
        studio_id = SLAYER_STUDIO_MAP.get(s_key) or SLAYER_STUDIO_MAP.get(s_key.replace(" ", ""))
        
        results = []
        seen = set()

        if from_index == 0:
            curated_items = POPULAR_STUDIOS_MAP.get(studio_name) or POPULAR_STUDIOS_MAP.get(studio_name.title())
            if not curated_items:
                for k, v in POPULAR_STUDIOS_MAP.items():
                    if k.lower() == s_key:
                        curated_items = v
                        break
            if curated_items:
                for item in curated_items:
                    if isinstance(item, dict):
                        slug = str(item.get("id") or "")
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

        # Query Anime Slayer native studio filter
        if studio_id:
            payload = {"list_type": "filter", "anime_studio_ids": str(studio_id), "limit": limit, "offset": from_index}
            data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
            live_items = self._parse_results(data)
            for it in live_items:
                if it.id not in seen:
                    results.append(it)
                    seen.add(it.id)
        else:
            search_hits = self.search_anime(studio_name)
            for h in search_hits:
                if h.id not in seen:
                    results.append(h)
                    seen.add(h.id)

        return results

    def get_seasonal_anime(self, season: str = None, year: int = None, from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        import datetime
        now = datetime.datetime.now()
        if not year:
            year = now.year
        if not season:
            month = now.month
            if month in [1, 2, 3]:
                season = "Winter"
            elif month in [4, 5, 6]:
                season = "Spring"
            elif month in [7, 8, 9]:
                season = "Summer"
            else:
                season = "Fall"
        else:
            season = season.capitalize()

        payload = {
            "list_type": "filter",
            "anime_season": season,
            "anime_release_year": str(year),
            "limit": limit,
            "offset": from_index
        }
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        return self._parse_results(data)

    def get_ovas_and_specials(self, category: str = "ova", from_index: int = 0, limit: int = 20) -> List[AnimeResult]:
        atype = "OVA" if category.lower() == "ova" else "Special"
        payload = {"list_type": "filter", "anime_type": atype, "limit": limit, "offset": from_index}
        data = self._api_get("animes/get-published-animes", params={"json": json.dumps(payload)})
        return self._parse_results(data)

    def _parse_results(self, data: Optional[Any]) -> List[AnimeResult]:
        results = []
        if not data:
            return results

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            resp = data.get("response")
            if isinstance(resp, dict):
                items = resp.get("data", []) or []
            elif isinstance(resp, list):
                items = resp
            else:
                items = data.get("data", []) or []
        else:
            items = []

        if not isinstance(items, list):
            return results

        for it in items:
            if not isinstance(it, dict):
                continue
            aid = str(it.get("anime_id") or "")
            title_ar = it.get("anime_name") or ""
            title_en = it.get("anime_english_title") or title_ar
            score = str(it.get("anime_rating") or "N/A")
            cover = it.get("anime_cover_image_url") or it.get("anime_cover_image_full_url") or ""
            story = it.get("anime_story") or it.get("anime_description") or ""
            atype = it.get("anime_type") or "مسلسل"

            if aid:
                results.append(AnimeResult(
                    id=aid,
                    title_en=title_en,
                    title_ar=title_ar,
                    thumbnail=cover,
                    score=score,
                    type=atype,
                    synopsis=story
                ))
        return results

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
        elif ftype in ("AIRING", "CURRENTLY_AIRING"):
            return self.get_top_currently_airing(from_index, limit)
        elif ftype == "MAL":
            return self.get_top_anime_mal(from_index, limit)
        return self.get_trending_anime(from_index, limit)
