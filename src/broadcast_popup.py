"""
Remote broadcast interactive scrollable modal popup for ani-cli-arabic.
Displays server-driven rich announcements, markdown messages, and community alerts on startup.
"""

import os
import re
import textwrap
import webbrowser
from typing import Optional, Dict, List, Any

from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.box import HEAVY

from .config import (
    COLOR_BORDER, COLOR_TITLE, COLOR_SUBTITLE,
    COLOR_HIGHLIGHT_FG, COLOR_HIGHLIGHT_BG
)
from .utils import get_key, RawTerminal


STYLE_COLOR_MAP = {
    "cyan": "bold #7dcfff",
    "green": "bold #9ece6a",
    "yellow": "bold #e0af68",
    "magenta": "bold #bb9af7",
    "red": "bold #f7768e",
    "blue": "bold #7aa2f7"
}

STYLE_BORDER_MAP = {
    "cyan": "#7dcfff",
    "green": "#9ece6a",
    "yellow": "#e0af68",
    "magenta": "#bb9af7",
    "red": "#f7768e",
    "blue": "#7aa2f7"
}


def _parse_markdown_line(raw_line: str, accent_color: str) -> Text:
    """Parses simple markdown tokens (bold, bullets, links) into a Rich Text object."""
    t = Text()
    line = raw_line.strip()

    if not line:
        return Text("")

    # Bullet line
    if line.startswith("◆") or line.startswith("•") or line.startswith("- "):
        bullet_char = "  ◆ "
        content = re.sub(r'^[◆•\-]\s*', '', line)
        t.append(bullet_char, style=accent_color)
    else:
        content = "  " + line

    # Parse **bold** tokens
    parts = re.split(r'(\*\*.*?\*\*)', content)
    for part in parts:
        if part.startswith("**") and part.endswith("**") and len(part) >= 4:
            bold_text = part[2:-2]
            t.append(bold_text, style="bold white")
        elif part:
            t.append(part, style="white")

    return t


def _build_broadcast_lines(message: str, content_w: int, accent_color: str) -> List[Text]:
    """Wraps and formats message lines into scrollable Rich Text objects."""
    all_lines: List[Text] = []
    paragraphs = message.split("\n")

    for p in paragraphs:
        p_clean = p.rstrip()
        if not p_clean:
            all_lines.append(Text(""))
            continue

        # Wrap long lines while preserving markdown
        # If line is a bullet
        is_bullet = p_clean.strip().startswith(("◆", "•", "- "))
        wrap_w = max(20, content_w - (8 if is_bullet else 4))
        
        # Simple wrap
        wrapped = textwrap.wrap(p_clean, width=wrap_w)
        if not wrapped:
            all_lines.append(_parse_markdown_line(p_clean, accent_color))
        else:
            for idx, w in enumerate(wrapped):
                if idx > 0 and is_bullet:
                    # Indent continuation of bullet
                    t = Text("      ")
                    # Parse bold in continuation
                    parts = re.split(r'(\*\*.*?\*\*)', w)
                    for part in parts:
                        if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                            t.append(part[2:-2], style="bold white")
                        elif part:
                            t.append(part, style="white")
                    all_lines.append(t)
                else:
                    all_lines.append(_parse_markdown_line(w, accent_color))

    return all_lines


def render_broadcast_popup(console, broadcast_data: Dict[str, Any]) -> None:
    """
    Renders an interactive, closable, scrollable remote announcement modal
    at application startup.
    """
    if not broadcast_data:
        return

    title = broadcast_data.get("title") or "🚨 Remote Broadcast Announcement"
    message = broadcast_data.get("message") or ""
    link = (broadcast_data.get("link") or "").strip()
    style_key = str(broadcast_data.get("style") or "cyan").lower()
    
    accent_style = STYLE_COLOR_MAP.get(style_key, "bold #7dcfff")
    border_color = STYLE_BORDER_MAP.get(style_key, COLOR_BORDER)

    screen_h = max(16, console.height)
    screen_w = max(40, console.width)

    # Calculate bounded dimensions
    panel_w = min(84, screen_w - 4)
    content_w = panel_w - 6
    viewport_h = min(14, max(6, screen_h - 10))

    lines = _build_broadcast_lines(message, content_w, accent_style)
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
            sb_style = accent_style if is_thumb else "dim #333333"

            body.append_text(line_text)
            body.append(" " * pad_len)
            body.append(sb_char, style=sb_style)
            if r < viewport_h - 1:
                body.append("\n")

        panel = Panel(
            body,
            title=f"[{accent_style}] {title} [/{accent_style}]",
            subtitle=f"[dim]↑/↓ to scroll • [{accent_style}]{pct_str}[/{accent_style}] • Enter / Esc to close[/dim]",
            box=HEAVY,
            border_style=border_color,
            padding=(0, 1),
            width=panel_w,
            height=viewport_h + 2
        )

        # Bottom Keycaps
        dock = Text()
        dock.append("[ ", style="dim")
        dock.append("↵ / Esc", style=accent_style)
        dock.append(" Close", style="white")
        dock.append(" ]", style="dim")

        if link:
            dock.append("   [ ", style="dim")
            dock.append("o", style=accent_style)
            dock.append(" Open Link", style="white")
            dock.append(" ]", style="dim")

        if total_lines > viewport_h:
            dock.append("   [ ", style="dim")
            dock.append("↑↓ / jk", style=accent_style)
            dock.append(" Scroll", style="white")
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
                elif key in ('o', 'O') and link:
                    try:
                        webbrowser.open(link)
                    except Exception:
                        pass
                elif key in ('ENTER', 'ESC', 'b', 'q', ' '):
                    break
