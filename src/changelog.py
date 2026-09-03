"""
Changelog management and interactive scrollable UI for ani-cli-arabic.
Detects first-run and post-update states to automatically showcase new features.
"""

import os
import re
import json
import time
import textwrap
import urllib.request
from pathlib import Path
from typing import Optional, Dict, List, Any

from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.box import HEAVY

from .version import __version__, APP_VERSION
from .config import (
    COLOR_BORDER, COLOR_TITLE, COLOR_SUBTITLE,
    COLOR_HIGHLIGHT_FG, COLOR_HIGHLIGHT_BG
)
from .utils import get_key, RawTerminal

_CHANGELOG_ITEMS: List[Dict[str, Any]] = [
    {
        "badge": "Multi-Provider",
        "badge_style": "bold cyan",
        "title": "4 Distinct Streaming Engines",
        "desc": "Stream seamlessly across Anime3rb, Anime Slayer (VIP CDN), Animeify, and AniDB (English Sub & Dub) with instant runtime switching."
    },
    {
        "badge": "Watch Progress",
        "badge_style": "bold yellow",
        "title": "Real-Time MPV Socket Resumption",
        "desc": "Background IPC socket tracking records exact timestamps and percentage, resuming instantly from where you left off."
    },
    {
        "badge": "Minimal TUI",
        "badge_style": "bold magenta",
        "title": "Streamlined Tactile Interface",
        "desc": "Compact 4x3 shortcut dock, integrated top pill badges, live star cache, and zero visual clutter."
    },
    {
        "badge": "Multi-Player",
        "badge_style": "bold green",
        "title": "Expanded Player Ecosystem",
        "desc": "Auto-detection and timestamp seeking for Celluloid, IINA, Syncplay, MPV, VLC, and MPC-HC."
    },
    {
        "badge": "Broadcast",
        "badge_style": "bold blue",
        "title": "Cloudflare Remote Announcements",
        "desc": "Instant global announcements and maintenance notices delivered live via Cloudflare Worker."
    },
    {
        "badge": "Smart Search",
        "badge_style": "bold cyan",
        "title": "Typo Normalization & Fallbacks",
        "desc": "Automatic Arabic orthographic normalization and chunked token search fallbacks for zero-miss lookups."
    },
    {
        "badge": "Intro Skip",
        "badge_style": "bold yellow",
        "title": "Anime3rb Bumper Auto-Skip",
        "desc": "Automatically skips the 5-second intro bumper strictly on Anime3rb streams when starting fresh episodes."
    },
    {
        "badge": "Auto-Updater",
        "badge_style": "bold green",
        "title": "Bulletproof Upgrade Engine",
        "desc": "Automated PyPI and pipx updates with automatic PEP 668 managed environment handling."
    },
    {
        "badge": "Maintenance",
        "badge_style": "bold #d97979",
        "title": "Automated Cache Optimization",
        "desc": "Background IPC socket cleanup and temporary database pruning on startup."
    }
]

_VERSION_SEEN_FILE = Path.home() / ".ani-cli-arabic" / "database" / "version_seen.json"


def should_show_update_popup() -> bool:
    """Checks if the user updated to a new version or is running for the first time."""
    try:
        if _VERSION_SEEN_FILE.exists():
            with open(_VERSION_SEEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_seen = data.get("last_seen_version", "")
                if last_seen != __version__:
                    return True
                return False
        else:
            return True
    except Exception:
        return False


def mark_version_seen() -> None:
    """Marks the current version as seen."""
    try:
        _VERSION_SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_VERSION_SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "last_seen_version": __version__,
                "seen_at": time.time()
            }, f, indent=4)
    except Exception:
        pass


def clear_version_seen() -> None:
    """Clears the seen version file to force display on next run."""
    try:
        if _VERSION_SEEN_FILE.exists():
            _VERSION_SEEN_FILE.unlink()
    except Exception:
        pass


_CHANGELOG_CACHE_FILE = Path.home() / ".ani-cli-arabic" / "database" / "changelog_cache.json"

def fetch_remote_changelog(timeout: float = 0.8) -> Optional[Dict[str, Any]]:
    """Fetches remote changelog if configured in Cloudflare KV."""
    urls = [
        "https://ani-cli-broadcast.talego4955.workers.dev/changelog.json",
        "https://broadcast.ani-cli-arabic.dev/changelog.json"
    ]
    for u in urls:
        try:
            req = urllib.request.Request(
                f"{u}?_t={int(time.time())}",
                headers={"User-Agent": f"ani-cli-arabic/{__version__}"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(data, dict):
                        try:
                            _CHANGELOG_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                            with open(_CHANGELOG_CACHE_FILE, "w", encoding="utf-8") as cf:
                                json.dump(data, cf)
                        except Exception:
                            pass
                        return data
        except Exception:
            continue
    try:
        if _CHANGELOG_CACHE_FILE.exists():
            with open(_CHANGELOG_CACHE_FILE, "r", encoding="utf-8") as cf:
                return json.load(cf)
    except Exception:
        pass
    return None


def _sub_changelog_vars(text: str, latest_ver: str = "") -> str:
    """Substitutes {version}, {latest_version}, and {os} in changelog text."""
    if not text:
        return ""
    import platform
    return (
        text.replace("{version}", APP_VERSION)
            .replace("{latest_version}", latest_ver or APP_VERSION)
            .replace("{os}", platform.system())
    )


def _build_changelog_lines(content_w: int, remote_data: Optional[Dict[str, Any]] = None) -> List[Text]:
    """Generates wrapped, beautifully styled lines for the changelog modal."""
    all_lines: List[Text] = []
    latest_ver = (remote_data or {}).get("latest_version") or ""
    outdated_notice = (remote_data or {}).get("outdated_notice") or "⚠️ YOUR VERSION {version} IS OUTDATED PLEASE UPDATE."

    # Check if user is outdated
    is_outdated = False
    if latest_ver:
        try:
            v_curr = [int(x) for x in re.sub(r'[^0-9.]', '', __version__).split('.') if x]
            v_late = [int(x) for x in re.sub(r'[^0-9.]', '', latest_ver).split('.') if x]
            if v_curr < v_late:
                is_outdated = True
        except Exception:
            pass

    if is_outdated:
        notice_text = _sub_changelog_vars(outdated_notice, latest_ver)
        t_out = Text()
        t_out.append("  🚨 ", style="bold red")
        t_out.append(notice_text, style="bold #ff6b6b")
        all_lines.append(t_out)
        all_lines.append(Text(""))

    # If remote custom body is provided
    body_text = (remote_data or {}).get("body") or ""
    if body_text.strip():
        for line in body_text.split("\n"):
            line_clean = line.strip()
            if not line_clean:
                all_lines.append(Text(""))
                continue
            line_sub = _sub_changelog_vars(line_clean, latest_ver)
            if line_sub.startswith(("◆", "•", "- ")):
                bullet_content = re.sub(r'^[◆•\-]\s*', '', line_sub)
                t = Text()
                t.append("  ◆ ", style=f"bold {COLOR_TITLE}")
                t.append(bullet_content, style="white")
                all_lines.append(t)
            else:
                wrapped = textwrap.wrap(line_sub, width=max(20, content_w - 4))
                for w in wrapped:
                    t = Text("  ")
                    t.append(w, style="white")
                    all_lines.append(t)
        return all_lines

    # Default built-in items
    for item in _CHANGELOG_ITEMS:
        t1 = Text()
        t1.append("  ◆ ", style=f"bold {COLOR_TITLE}")
        t1.append(f"[{item['badge']}]", style=item["badge_style"])
        t1.append(f" {item['title']}", style="bold white")
        all_lines.append(t1)

        desc = _sub_changelog_vars(item["desc"], latest_ver)
        wrapped = textwrap.wrap(desc, width=max(20, content_w - 6))
        for w in wrapped:
            t2 = Text()
            t2.append("    ", style="dim")
            t2.append(w, style="white")
            all_lines.append(t2)
        
        all_lines.append(Text(""))

    return all_lines


def render_changelog_popup(console, force: bool = False) -> None:
    """
    Renders an interactive, scrollable changelog modal with a bounded max height
    and a visual scrollbar track and thumb.
    """
    if not force and not should_show_update_popup():
        return

    screen_h = max(16, console.height)
    screen_w = max(40, console.width)

    # Calculate bounded dimensions
    panel_w = min(80, screen_w - 4)
    content_w = panel_w - 6  # Margin for borders, padding, and scrollbar
    viewport_h = min(14, max(6, screen_h - 10))

    remote_data = fetch_remote_changelog()
    title_template = (remote_data or {}).get("title") or f"⚡ What's New in {APP_VERSION}"
    latest_ver = (remote_data or {}).get("latest_version") or APP_VERSION
    panel_title = _sub_changelog_vars(title_template, latest_ver)

    lines = _build_changelog_lines(content_w, remote_data)
    total_lines = len(lines)
    scroll_offset = 0

    def generate_renderable():
        max_offset = max(0, total_lines - viewport_h)
        clamped_offset = max(0, min(scroll_offset, max_offset))

        # Calculate scrollbar metrics
        if total_lines > viewport_h:
            thumb_size = max(1, min(viewport_h, int(round((viewport_h / total_lines) * viewport_h))))
            thumb_pos = int(round((clamped_offset / max(1, max_offset)) * (viewport_h - thumb_size)))
        else:
            thumb_size = viewport_h
            thumb_pos = 0

        # Scroll position label
        if total_lines <= viewport_h:
            pct_str = "All"
        elif clamped_offset == 0:
            pct_str = "Top"
        elif clamped_offset >= max_offset:
            pct_str = "Bot"
        else:
            pct = int(round((clamped_offset / max(1, max_offset)) * 100))
            pct_str = f"{pct}%"

        body = Text()
        for r in range(viewport_h):
            idx = clamped_offset + r
            line_text = lines[idx] if idx < total_lines else Text("")
            
            # Align line and compute scrollbar column
            plain_len = len(line_text.plain)
            pad_len = max(0, content_w - plain_len)
            
            is_thumb = (r >= thumb_pos and r < thumb_pos + thumb_size)
            sb_char = "█" if is_thumb else "│"
            sb_style = f"bold {COLOR_TITLE}" if is_thumb else "dim #333333"

            body.append_text(line_text)
            body.append(" " * pad_len)
            body.append(sb_char, style=sb_style)
            if r < viewport_h - 1:
                body.append("\n")

        panel = Panel(
            body,
            title=f"[bold {COLOR_TITLE}] {panel_title} [/bold {COLOR_TITLE}]",
            subtitle=f"[dim]↑/↓ to scroll • [bold {COLOR_TITLE}]{pct_str}[/bold {COLOR_TITLE}] • Enter / Esc to close[/dim]",
            box=HEAVY,
            border_style=COLOR_BORDER,
            padding=(0, 1),
            width=panel_w,
            height=viewport_h + 2
        )

        # Dock Keycaps
        dock = Text()
        dock.append("[ ", style="dim")
        dock.append("↵ / Esc", style=f"bold {COLOR_TITLE}")
        dock.append(" Close", style="white")
        dock.append(" ]   [ ", style="dim")
        dock.append("↑↓ / jk", style=f"bold {COLOR_TITLE}")
        dock.append(" Scroll", style="white")
        dock.append(" ]   [ ", style="dim")
        dock.append("PgUp / PgDn", style=f"bold {COLOR_TITLE}")
        dock.append(" Fast", style="white")
        dock.append(" ]", style="dim")

        root = Table.grid(expand=False)
        root.add_column(justify="center")
        root.add_row(Align.center(panel))
        root.add_row(Text(""))
        root.add_row(Align.center(dock))

        return Align.center(root, vertical="middle", height=console.height)

    with RawTerminal():
        with Live(
            generate_renderable(),
            console=console,
            auto_refresh=False,
            screen=True,
            refresh_per_second=20
        ) as live:
            while True:
                key = get_key()
                max_offset = max(0, total_lines - viewport_h)

                if key in ('UP', 'k') and scroll_offset > 0:
                    scroll_offset -= 1
                    live.update(generate_renderable(), refresh=True)
                elif key in ('DOWN', 'j') and scroll_offset < max_offset:
                    scroll_offset += 1
                    live.update(generate_renderable(), refresh=True)
                elif key in ('PAGE_UP',):
                    scroll_offset = max(0, scroll_offset - 6)
                    live.update(generate_renderable(), refresh=True)
                elif key in ('PAGE_DOWN',):
                    scroll_offset = min(max_offset, scroll_offset + 6)
                    live.update(generate_renderable(), refresh=True)
                elif key in ('HOME',):
                    scroll_offset = 0
                    live.update(generate_renderable(), refresh=True)
                elif key in ('END',):
                    scroll_offset = max_offset
                    live.update(generate_renderable(), refresh=True)
                elif key in ('ENTER', 'ESC', 'b', 'q', ' '):
                    break

    mark_version_seen()
