"""
Native Downloader for ani-cli-arabic.
Provides resumable chunked downloads, speed throttling, concurrent workers,
and interactive batch link resolution without external tools (aria2/IDM).
"""

import re
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import requests
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn
)

from .models import Episode
from .utils import get_stream_referer
from .logger import logger


@dataclass
class DownloadConfig:
    save_dir: Path
    max_parallel: int = 2
    speed_limit_bytes: Optional[int] = None
    quality: str = "1080p"


def parse_batch_ranges(prompt: str, max_eps: Optional[int] = None) -> List[int]:
    """Parse episode range expressions like '1-12', '1, 3, 5', '5-1', 'all' into sorted episode numbers."""
    if not prompt:
        return []
    p = prompt.strip().lower()
    if p in ("all", "*"):
        if max_eps and max_eps > 0:
            return list(range(1, max_eps + 1))
        return []

    tokens = re.split(r"[\s,;]+", p)
    nums = set()

    for token in tokens:
        if not token:
            continue
        range_match = re.match(r"^(\d+)(?:-|\.\.)(\d+)$", token)
        if range_match:
            s, e = int(range_match.group(1)), int(range_match.group(2))
            low, high = min(s, e), max(s, e)
            if max_eps:
                high = min(high, max_eps)
            nums.update(range(low, high + 1))
            continue

        prefix_match = re.match(r"^-(?:\.\.)?(\d+)$", token)
        if prefix_match:
            high = int(prefix_match.group(1))
            if max_eps:
                high = min(high, max_eps)
            nums.update(range(1, max(1, high) + 1))
            continue

        if max_eps and re.match(r"^(\d+)(?:-|\.\.)$", token):
            low = int(token.rstrip("-.").rstrip("."))
            if low <= max_eps:
                nums.update(range(low, max_eps + 1))
            continue

        if token.isdigit():
            val = int(token)
            if not max_eps or val <= max_eps:
                nums.add(val)

    return sorted(nums)


def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename).strip()
    return cleaned or "download.mp4"


def parse_speed_limit(input_str: Optional[str]) -> Optional[int]:
    """Parse speed limit input like '2M', '500K', '1.5MB' into bytes/sec."""
    if not input_str:
        return None
    val = input_str.strip().upper()
    if val in ("0", "NONE", "UNLIMITED", "NO", "OFF", ""):
        return None
    m = re.match(r"^([\d.]+)\s*(K|KB|M|MB|G|GB)?$", val)
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "K").upper()
    if "G" in unit:
        return int(num * 1024 * 1024 * 1024)
    if "M" in unit:
        return int(num * 1024 * 1024)
    if "K" in unit:
        return int(num * 1024)
    return int(num)


def format_speed(bytes_per_sec: Optional[int]) -> str:
    if not bytes_per_sec or bytes_per_sec <= 0:
        return "Unlimited"
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    return f"{bytes_per_sec / 1024:.0f} KB/s"


def prompt_download_options(
    console: Console,
    default_dir: str = "downloads",
    default_quality: str = "1080p",
    batch_mode: bool = False
) -> Optional[DownloadConfig]:
    """Interactive CLI prompt to ask for download preferences."""
    console.print()
    console.print("[bold cyan]─── Download Options ───[/bold cyan]")

    try:
        # 1. Save Directory
        path_prompt = console.input(f"  [cyan]Save Directory[/cyan] [dim]({default_dir})[/dim]: ").strip()
        save_path = Path(path_prompt or default_dir).expanduser().resolve()
        save_path.mkdir(parents=True, exist_ok=True)

        # 2. Quality
        q_prompt = console.input(f"  [cyan]Preferred Quality[/cyan] [dim]({default_quality} / 720p / 480p / best)[/dim]: ").strip()
        quality = q_prompt or default_quality

        # 3. Parallel workers (if multiple episodes)
        parallel = 2
        if batch_mode:
            p_prompt = console.input("  [cyan]Parallel Downloads[/cyan] [dim](1-5, default 2)[/dim]: ").strip()
            if p_prompt.isdigit():
                parallel = max(1, min(6, int(p_prompt)))

        # 4. Speed Limit
        s_prompt = console.input("  [cyan]Speed Limit[/cyan] [dim](0=Unlimited, or e.g. 2M, 500K)[/dim]: ").strip()
        speed_limit = parse_speed_limit(s_prompt)

        console.print(
            f"  [dim]Settings: Dir={save_path.name} | Quality={quality} | Parallel={parallel} | Speed={format_speed(speed_limit)}[/dim]\n"
        )
        return DownloadConfig(
            save_dir=save_path,
            max_parallel=parallel,
            speed_limit_bytes=speed_limit,
            quality=quality
        )
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Download cancelled.[/yellow]")
        return None


class StreamDownloader:
    """Handles chunked resumable downloads with optional speed throttling."""

    def __init__(self, speed_limit_bytes: Optional[int] = None):
        self.speed_limit = speed_limit_bytes
        self.stop_requested = threading.Event()

    def download(
        self,
        url: str,
        dest_path: Path,
        progress: Progress,
        task_id: Any,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        if self.stop_requested.is_set():
            return False

        part_path = dest_path.with_suffix(dest_path.suffix + ".part")

        # Skip if file already complete and valid
        if dest_path.exists() and dest_path.stat().st_size > 0 and not part_path.exists():
            file_size = dest_path.stat().st_size
            if progress and task_id is not None:
                progress.update(task_id, total=file_size, completed=file_size)
            return True

        auto_referer = get_stream_referer(url)
        req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", **(headers or {})}
        if auto_referer and "Referer" not in req_headers:
            req_headers["Referer"] = auto_referer

        resume_byte_pos = 0
        if part_path.exists():
            resume_byte_pos = part_path.stat().st_size
            if resume_byte_pos > 0:
                req_headers["Range"] = f"bytes={resume_byte_pos}-"

        try:
            with requests.get(url, headers=req_headers, stream=True, timeout=15) as resp:
                if self.stop_requested.is_set():
                    return False

                if resp.status_code == 416:
                    # Range not satisfiable, file might be complete
                    part_path.replace(dest_path)
                    return True

                if resp.status_code not in (200, 206):
                    # Direct retry without range
                    req_headers.pop("Range", None)
                    with requests.get(url, headers=req_headers, stream=True, timeout=15) as r_full:
                        if self.stop_requested.is_set():
                            return False
                        r_full.raise_for_status()
                        return self._stream_to_disk(r_full, part_path, dest_path, progress, task_id, 0)

                total_length = resp.headers.get("Content-Length")
                if resp.status_code == 206:
                    initial_offset = resume_byte_pos
                    total_size = int(total_length) + resume_byte_pos if total_length else None
                else:
                    # Server returned 200 (full content from start)
                    initial_offset = 0
                    resume_byte_pos = 0
                    total_size = int(total_length) if total_length else None

                progress.update(task_id, total=total_size, completed=resume_byte_pos)
                return self._stream_to_disk(resp, part_path, dest_path, progress, task_id, initial_offset)

        except Exception as e:
            logger.error("DOWNLOAD", f"Download failed for {dest_path.name}: {e}")
            return False

    def _stream_to_disk(
        self,
        resp: requests.Response,
        part_path: Path,
        final_path: Path,
        progress: Progress,
        task_id: Any,
        initial_offset: int
    ) -> bool:
        chunk_size = 64 * 1024  # 64KB
        mode = "ab" if initial_offset > 0 else "wb"

        with open(part_path, mode) as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if self.stop_requested.is_set():
                    return False
                if not chunk:
                    continue

                t0 = time.time()
                f.write(chunk)
                progress.update(task_id, advance=len(chunk))

                # Rate limiting
                if self.speed_limit and self.speed_limit > 0:
                    expected_time = len(chunk) / self.speed_limit
                    elapsed = time.time() - t0
                    if expected_time > elapsed:
                        time.sleep(expected_time - elapsed)

        part_path.replace(final_path)
        return True


def resolve_episode_download_url(
    api: Any,
    anime: Any,
    ep: Episode,
    preferred_quality: str = "1080p"
) -> Optional[str]:
    """Extract direct download stream URL for an episode with multi-provider fallback."""
    try:
        ep_num = getattr(ep, "number", "1")
        anime_id = getattr(anime, "id", "")
        anime_type = getattr(anime, "type", "SERIES")
        s_data = api.get_streaming_servers(anime_id, ep_num, anime_type)
        if not s_data:
            return None

        clean_pref = preferred_quality.lower().replace("p", "")

        # 1. Try explicit Qualities list
        qualities = s_data.get("Qualities", []) if isinstance(s_data, dict) else []
        if qualities:
            target = None
            for q in qualities:
                q_name = getattr(q, "name", "").lower()
                if clean_pref in q_name:
                    target = q
                    break
            if not target and qualities:
                target = qualities[0]

            direct_url = getattr(target, "direct_url", None)
            if not direct_url and isinstance(s_data, dict):
                current_ep = s_data.get("CurrentEpisode", {})
                direct_url = current_ep.get(getattr(target, "server_key", ""))
            if direct_url and direct_url.startswith("http"):
                return direct_url

        # 2. Fallback to DirectStreams dict
        if isinstance(s_data, dict) and "DirectStreams" in s_data:
            direct_streams = s_data["DirectStreams"]
            if preferred_quality in direct_streams:
                return direct_streams[preferred_quality]
            for k in [f"{clean_pref}p", "1080p", "720p", "480p"]:
                if k in direct_streams:
                    return direct_streams[k]
            if direct_streams:
                return next(iter(direct_streams.values()))

        # 3. Fallback to CurrentEpisode dict keys (legacy keys)
        if isinstance(s_data, dict) and "CurrentEpisode" in s_data:
            cur_ep = s_data["CurrentEpisode"]
            key_map = {"1080": "FRFhdQ", "720": "FRLink", "480": "FRLowQ"}
            target_key = key_map.get(clean_pref, "FRFhdQ")
            if target_key in cur_ep and cur_ep[target_key]:
                return cur_ep[target_key]
            for fallback_key in ["FRFhdQ", "FRLink", "FRLowQ"]:
                if fallback_key in cur_ep and cur_ep[fallback_key]:
                    return cur_ep[fallback_key]

        return None
    except Exception as e:
        title = getattr(anime, "title_en", "") or getattr(anime, "title_ar", "") or "Anime"
        logger.error("DOWNLOAD", f"Error resolving link for {title} ep {getattr(ep, 'number', '?')}: {e}")
        return None


def execute_batch_download(
    api: Any,
    anime: Any,
    episodes: List[Episode],
    config: DownloadConfig,
    console: Console,
    history_manager: Optional[Any] = None
) -> Dict[str, int]:
    """Resolves links and runs concurrent downloads with Rich progress dashboard."""
    console.print(f"\n[cyan]Resolving stream links for {len(episodes)} episodes...[/cyan]")

    targets = []
    with console.status("[bold blue]Fetching direct download URLs...[/bold blue]"):
        for ep in episodes:
            url = resolve_episode_download_url(api, anime, ep, config.quality)
            if url:
                fn = sanitize_filename(f"{anime.title_en} - Ep {ep.display_num} [{config.quality}].mp4")
                targets.append((ep, url, config.save_dir / fn))
            else:
                console.print(f"  [yellow]⚠ Warning: Could not resolve link for Episode {ep.display_num}[/yellow]")

    if not targets:
        console.print("[bold red]✖ No playable stream links could be resolved.[/bold red]\n")
        return {"success": 0, "failed": len(episodes)}

    console.print(f"[green]✓ Successfully resolved {len(targets)}/{len(episodes)} stream links.[/green]\n")

    downloader = StreamDownloader(speed_limit_bytes=config.speed_limit_bytes)
    results = {"success": 0, "failed": len(episodes) - len(targets)}

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=30),
        "[progress.percentage]{task.percentage:>3.0f}%",
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False
    ) as progress:
        overall_task = progress.add_task(
            f"[bold green]Overall Progress ({len(targets)} eps)",
            total=len(targets)
        )

        def _worker(ep, url, dest_path):
            task_id = progress.add_task(f"Ep {ep.display_num}", total=None)
            ok = downloader.download(url, dest_path, progress, task_id)
            progress.remove_task(task_id)
            progress.advance(overall_task, 1)
            return ep, ok

        try:
            with ThreadPoolExecutor(max_workers=config.max_parallel) as executor:
                futures = [executor.submit(_worker, ep, url, path) for ep, url, path in targets]
                for fut in as_completed(futures):
                    ep, ok = fut.result()
                    if ok:
                        results["success"] += 1
                        if history_manager:
                            try:
                                history_manager.mark_watched(anime.id, ep.display_num, anime.title_en)
                            except Exception:
                                pass
                    else:
                        results["failed"] += 1
        except KeyboardInterrupt:
            downloader.stop_requested.set()
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            console.print("\n[yellow]Batch download cancelled by user.[/yellow]")

    console.print(
        f"\n[bold green]Download finished:[/bold green] {results['success']} succeeded, {results['failed']} failed."
    )
    console.print(f"[dim]Saved to: {config.save_dir}[/dim]\n")
    return results
