"""
Changelog management and interactive scrollable UI for ani-cli-arabic.
Detects first-run and post-update states to automatically showcase new features.
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, List

from .version import __version__, APP_VERSION
from .config import (
    COLOR_BORDER, COLOR_TITLE, COLOR_SUBTITLE,
    COLOR_HIGHLIGHT_FG, COLOR_HIGHLIGHT_BG
)
from .utils import get_key, RawTerminal

_CHANGELOG_DATA: Dict[str, Dict[str, any]] = {
    "2.0.0": {
        "title": "v2.0.0 — The Ultimate Multi-Provider & UI Evolution",
        "date": "2026-08-30",
        "highlights": [
            "⚡ 4 Distinct Providers: Anime3rb, Anime Slayer (VIP CDN), Animeify, and AniDB (English Sub & Dub).",
            "🕒 Real-Time Watch Progress & IPC Resumption: MPV tracking saves exact position & resumes instantly.",
            "🎨 Streamlined Minimal TUI: Clean 4x3 tactile keycaps, integrated provider pills, and zero clutter.",
            "🎬 Extended Player Ecosystem: Native support for Celluloid, IINA, Syncplay, MPV, VLC, and MPC-HC.",
            "📡 Remote Broadcast Engine: Live global announcements, domain updates, and server notices via Cloudflare Worker.",
            "🔍 Smart Search Normalization: Automatic typo correction and Arabic orthographic variations.",
            "🧹 Background Maintenance: Automated socket cleanup and disk storage optimization."
        ]
    },
    "1.6.0": {
        "title": "v1.6.0 — Discovery & Anime Slayer Integration",
        "date": "2026-08-25",
        "highlights": [
            "✨ Complete Discovery Engine: Trending, Popular, Top Rated, Movies, Genres, and Studios.",
            "🛡️ Anime Slayer Provider: AES & RNCryptor CDN link extraction.",
            "📥 Batch Downloader: Multi-episode download queue with Aria2 and IDM support.",
            "🎮 Discord Rich Presence: Live watching status, episode counts, and anime poster art."
        ]
    },
    "1.5.0": {
        "title": "v1.5.0 — Core Architecture Refactor",
        "date": "2026-08-10",
        "highlights": [
            "🚀 High-performance multi-threaded search and stream resolver.",
            "💾 Atomic JSON database storage for history, favorites, and settings.",
            "🌐 Comprehensive English anime support via AniDB engine."
        ]
    }
}

_VERSION_SEEN_FILE = Path.home() / ".ani-cli-arabic" / "database" / "version_seen.json"


def get_latest_changelog() -> Dict[str, any]:
    """Returns the latest changelog entry."""
    return _CHANGELOG_DATA.get(__version__, list(_CHANGELOG_DATA.values())[0])


def get_all_changelogs() -> Dict[str, Dict[str, any]]:
    """Returns all changelogs."""
    return _CHANGELOG_DATA


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


def render_changelog_popup(console, force: bool = False) -> None:
    """
    Renders an interactive, scrollable changelog modal.
    """
    if not force and not should_show_update_popup():
        return

    from rich.text import Text
    from rich.panel import Panel
    from rich.table import Table
    from rich.align import Align
    from rich.live import Live
    from rich.box import HEAVY

    scroll_offset = 0
    lines = []

    # Build formatted content lines
    for ver, data in _CHANGELOG_DATA.items():
        is_current = (ver == __version__)
        badge_style = f"bold {COLOR_TITLE}" if is_current else "bold white"
        
        lines.append(Text(""))
        title_t = Text()
        title_t.append("━━━ ", style=f"bold {COLOR_BORDER}")
        title_t.append(data.get("title", f"v{ver}"), style=badge_style)
        title_t.append(f" ({data.get('date', '')})", style="dim")
        title_t.append(" ━━━", style=f"bold {COLOR_BORDER}")
        lines.append(title_t)
        lines.append(Text(""))

        for h in data.get("highlights", []):
            hl_text = Text()
            hl_text.append("  • ", style=f"bold {COLOR_TITLE}")
            hl_text.append(h, style="white")
            lines.append(hl_text)

    screen_h = console.height
    max_display = max(6, min(18, screen_h - 12))
    box_w = min(84, console.width - 4)

    def generate_renderable():
        visible_lines = lines[scroll_offset:scroll_offset + max_display]
        content = Text()
        for idx, l in enumerate(visible_lines):
            content.append_text(l)
            if idx < len(visible_lines) - 1:
                content.append("\n")

        panel = Panel(
            content,
            title=f"[bold {COLOR_TITLE}]What's New in {APP_VERSION}[/bold {COLOR_TITLE}]",
            subtitle=f"[dim]Use ↑/↓ or j/k to scroll • Press Enter / Esc to close[/dim]",
            box=HEAVY,
            border_style=COLOR_BORDER,
            padding=(1, 2),
            width=box_w
        )

        # Dock
        dock = Text()
        dock.append("[ ", style="dim")
        dock.append("↵ / Esc", style=f"bold {COLOR_TITLE}")
        dock.append(" Close", style="white")
        dock.append(" ]   [ ", style="dim")
        dock.append("↑↓ / jk", style=f"bold {COLOR_TITLE}")
        dock.append(" Scroll", style="white")
        dock.append(" ]", style="dim")

        root = Table.grid(expand=False)
        root.add_column(justify="center")
        root.add_row(Align.center(panel))
        root.add_row(Text(""))
        root.add_row(Align.center(dock))

        return Align.center(root, vertical="middle", height=console.height)

    with RawTerminal():
        with Live(generate_renderable(), console=console, auto_refresh=False, screen=True, refresh_per_second=15) as live:
            while True:
                key = get_key()
                if key in ('UP', 'k') and scroll_offset > 0:
                    scroll_offset -= 1
                    live.update(generate_renderable(), refresh=True)
                elif key in ('DOWN', 'j') and scroll_offset < max(0, len(lines) - max_display):
                    scroll_offset += 1
                    live.update(generate_renderable(), refresh=True)
                elif key in ('PAGE_UP',):
                    scroll_offset = max(0, scroll_offset - 5)
                    live.update(generate_renderable(), refresh=True)
                elif key in ('PAGE_DOWN',):
                    scroll_offset = min(max(0, len(lines) - max_display), scroll_offset + 5)
                    live.update(generate_renderable(), refresh=True)
                elif key in ('ENTER', 'ESC', 'b', 'q', ' '):
                    break

    mark_version_seen()
