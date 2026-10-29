#!/usr/bin/env python3
"""
Build the Stardima anime/cartoon/live-action classification cache.

Usage:
    STARDIMA_TMDB_KEY=... python scripts/build_stardima_cache.py

The generated `src/providers/stardima_catalog.json` is committed so the app
does not need a TMDB key at runtime.  TMDB responses are cached under
`scripts/.cache/tmdb/` so reruns are cheap.

Classification rule (validated against the site's `anmy` category):
    * tags contain an exact "anime" token       -> anime
    * TMDB genres contain Animation:
        original_language in {ja, zh, ko}       -> anime
        otherwise                               -> cartoon
    * TMDB genres do not contain Animation      -> live_action
    * no TMDB match                             -> tags/category fallback
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.providers.stardima_client import (  # noqa: E402
    APP_UA,
    CARTOON_CATEGORY_SLUGS,
    StardimaAuth,
    StardimaClient,
)

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_CACHE = ROOT / "scripts" / ".cache" / "tmdb"
OUT_FILE = ROOT / "src" / "providers" / "stardima_catalog.json"
ANIMATION_GENRE = 16
ANIME_LANGUAGES = {"ja", "zh", "ko"}


def _fetch_catalog(client: StardimaClient) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for path in ("/api/series", "/api/movies"):
        page = 1
        while page <= 100:
            response = client.get(path, params={"page": page, "per_page": 100})
            if not isinstance(response, dict):
                break
            videos = response.get("videos") or response.get("data") or []
            if not isinstance(videos, list) or not videos:
                break
            items.extend(video for video in videos if isinstance(video, dict))
            pagination = response.get("pagination") or {}
            last_page = pagination.get("last_page")
            if last_page is not None and page >= int(last_page):
                break
            if len(videos) < 100:
                break
            page += 1
    return items


def _fetch_details(
    api_key: str,
    server_url: str,
    video_ids: Iterable[Any],
    workers: int = 8,
) -> Dict[str, Dict[str, Any]]:
    session = requests.Session()
    session.headers.update(
        {
            "X-API-KEY": api_key,
            "Accept": "application/json",
            "User-Agent": APP_UA,
        }
    )
    base = server_url.rstrip("/")

    def fetch(video_id: Any) -> Tuple[str, Optional[Dict[str, Any]]]:
        key = str(video_id)
        try:
            response = session.get(f"{base}/api/video/{key}", timeout=30)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and isinstance(data.get("data"), dict):
                    data = data["data"]
                return key, data if isinstance(data, dict) else None
        except (requests.RequestException, ValueError):
            pass
        return key, None

    results: Dict[str, Dict[str, Any]] = {}
    ids = list(video_ids)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, video_id): video_id for video_id in ids}
        for index, future in enumerate(as_completed(futures), start=1):
            key, detail = future.result()
            if detail:
                results[key] = detail
            if index % 100 == 0 or index == len(ids):
                print(f"  details: {index}/{len(ids)}", flush=True)
    return results


def _tmdb_lookup(
    tmdb_key: str,
    tmdb_id: Any,
    media_type: str,
    session: requests.Session,
    refresh: bool = False,
) -> Optional[Dict[str, Any]]:
    if not tmdb_id:
        return None
    try:
        tmdb_id = int(tmdb_id)
    except (TypeError, ValueError):
        return None

    TMDB_CACHE.mkdir(parents=True, exist_ok=True)
    candidates = ["tv", "movie"] if media_type == "series" else ["movie", "tv"]
    for kind in candidates:
        cache_file = TMDB_CACHE / f"{kind}_{tmdb_id}.json"
        if cache_file.exists() and not refresh:
            try:
                with open(cache_file, "r", encoding="utf-8") as handle:
                    return json.load(handle)
            except (OSError, ValueError):
                pass
        try:
            response = session.get(
                f"{TMDB_BASE}/{kind}/{tmdb_id}",
                params={"api_key": tmdb_key, "language": "en-US"},
                timeout=20,
            )
        except requests.RequestException:
            continue
        if response.status_code == 200:
            data = response.json()
            try:
                with open(cache_file, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False)
            except OSError:
                pass
            return data
    return None


def _tmdb_search(
    tmdb_key: str,
    title: str,
    tags: str,
    media_type: str,
    session: requests.Session,
) -> Optional[Dict[str, Any]]:
    """Resolve a missing/invalid TMDB id by searching the site title and tags."""
    queries: List[Tuple[str, str]] = []
    if title:
        queries.append((title, "ar"))

    latin_tokens = re.findall(r"[A-Za-z][A-Za-z0-9'&:.\- ]{2,}", tags or "")
    latin_tokens.sort(key=len, reverse=True)
    for token in latin_tokens[:4]:
        token = token.strip(" -:.")
        if len(token) >= 3:
            queries.append((token, "en-US"))

    for token in re.findall(r"[A-Za-z][A-Za-z0-9'&:.\- ]{2,}", title or ""):
        token = token.strip(" -:.")
        if len(token) >= 3:
            queries.append((token, "en-US"))

    seen_queries = set()
    kinds = ["tv", "movie"] if media_type == "series" else ["movie", "tv"]
    for query, language in queries:
        query_key = (query.lower(), language)
        if query_key in seen_queries:
            continue
        seen_queries.add(query_key)
        for kind in kinds:
            try:
                response = session.get(
                    f"{TMDB_BASE}/search/{kind}",
                    params={
                        "api_key": tmdb_key,
                        "query": query,
                        "language": language,
                    },
                    timeout=20,
                )
            except requests.RequestException:
                continue
            if response.status_code != 200:
                continue
            for result in (response.json().get("results") or [])[:3]:
                genre_ids = result.get("genre_ids") or []
                original_language = str(result.get("original_language") or "").lower()
                if ANIMATION_GENRE not in genre_ids and original_language not in ANIME_LANGUAGES:
                    continue
                tmdb_id = result.get("id")
                if not tmdb_id:
                    continue
                full = _tmdb_lookup(
                    tmdb_key,
                    tmdb_id,
                    "series" if kind == "tv" else "movie",
                    session,
                )
                if full:
                    return full
                return result
    return None


def _classify(
    detail: Dict[str, Any],
    tmdb_data: Optional[Dict[str, Any]],
) -> str:
    tag_tokens = {
        token.strip().lower()
        for token in str(detail.get("tags") or "").split(",")
        if token.strip()
    }
    if tag_tokens & {"anime", "انمي", "أنمي"}:
        return "anime"

    if tmdb_data:
        genres = {
            int(genre.get("id"))
            for genre in (tmdb_data.get("genres") or [])
            if isinstance(genre, dict) and genre.get("id") is not None
        }
        if ANIMATION_GENRE not in genres:
            return "live_action"
        language = str(tmdb_data.get("original_language") or "").lower()
        return "anime" if language in ANIME_LANGUAGES else "cartoon"

    slugs = {
        str(category.get("slug") or "").lower()
        for category in (detail.get("category") or [])
        if isinstance(category, dict)
    }
    if "anmy" in slugs:
        return "anime"
    if slugs & {slug.lower() for slug in CARTOON_CATEGORY_SLUGS}:
        return "cartoon"
    return "unknown"


def _display_title(detail: Dict[str, Any], tmdb_data: Optional[Dict[str, Any]]) -> str:
    if tmdb_data:
        return str(tmdb_data.get("name") or tmdb_data.get("title") or "")
    return str(detail.get("title") or "")


def _original_name(tmdb_data: Optional[Dict[str, Any]]) -> str:
    if not tmdb_data:
        return ""
    return str(
        tmdb_data.get("original_name")
        or tmdb_data.get("original_title")
        or ""
    )


def _vote(tmdb_data: Optional[Dict[str, Any]]) -> float:
    if not tmdb_data:
        return 0.0
    try:
        return round(float(tmdb_data.get("vote_average") or 0.0), 2)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Stardima classification cache.")
    parser.add_argument("--out", type=Path, default=OUT_FILE)
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N titles.")
    parser.add_argument("--refresh", action="store_true", help="Ignore TMDB response cache.")
    parser.add_argument("--tmdb-key", default=os.environ.get("STARDIMA_TMDB_KEY", ""))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    if not args.tmdb_key:
        print(
            "ERROR: set STARDIMA_TMDB_KEY or pass --tmdb-key.\n"
            "The TMDB key is only used by this dev script and is never written to the cache.",
            file=sys.stderr,
        )
        return 2

    auth = StardimaAuth()
    api_key, server_url = auth.get()
    if not api_key or not server_url:
        print("ERROR: could not resolve Stardima credentials.", file=sys.stderr)
        return 1

    client = StardimaClient(auth=auth)
    print("Fetching catalog...", flush=True)
    catalog = _fetch_catalog(client)
    if args.limit:
        catalog = catalog[: args.limit]
    print(f"Catalog titles: {len(catalog)}", flush=True)

    print("Fetching details...", flush=True)
    details = _fetch_details(
        api_key,
        server_url,
        [video.get("id") for video in catalog if video.get("id") is not None],
        workers=args.workers,
    )

    tmdb_session = requests.Session()
    items: Dict[str, Dict[str, Any]] = {}
    total = len(details)

    def build_one(video_id: str, detail: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        media_type = str(detail.get("type") or "series").lower()
        tmdb_data = _tmdb_lookup(
            args.tmdb_key,
            detail.get("tmdbid"),
            media_type,
            tmdb_session,
            refresh=args.refresh,
        )
        if not tmdb_data:
            tmdb_data = _tmdb_search(
                args.tmdb_key,
                str(detail.get("title") or ""),
                str(detail.get("tags") or ""),
                media_type,
                tmdb_session,
            )
        content_type = _classify(detail, tmdb_data)
        item = {
            "t": content_type,
            "lang": str((tmdb_data or {}).get("original_language") or ""),
            "title": _display_title(detail, tmdb_data),
            "original_name": _original_name(tmdb_data),
            "vote": _vote(tmdb_data),
            "year": str(detail.get("year") or ""),
        }
        return str(video_id), item

    print("Classifying with TMDB...", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(build_one, video_id, detail): video_id
            for video_id, detail in details.items()
        }
        for index, future in enumerate(as_completed(futures), start=1):
            try:
                video_id, item = future.result()
                items[video_id] = item
            except Exception as exc:  # noqa: BLE001
                print(f"  classify failed: {exc}", file=sys.stderr)
            if index % 100 == 0 or index == total:
                print(f"  classified: {index}/{total}", flush=True)

    payload = {
        "version": 1,
        "generated_at": time.strftime("%Y-%m-%d"),
        "source": "tmdb+stardima",
        "items": items,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {args.out} ({len(items)} items)", flush=True)

    counts: Dict[str, int] = {}
    for item in items.values():
        counts[item["t"]] = counts.get(item["t"], 0) + 1
    print("Classification counts:", counts, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
