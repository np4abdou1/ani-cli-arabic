import time
import threading
import importlib
import os
import sys
import re
import requests
from io import BytesIO
from functools import lru_cache
import numpy as np
from PIL import Image, ImageEnhance
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.prompt import Prompt
from rich.layout import Layout
from rich.table import Table
from rich.theme import Theme
from rich.box import HEAVY, ROUNDED
from rich.spinner import Spinner
from rich.cells import cell_len

from .version import APP_VERSION
from .config import (
    COLOR_BORDER, COLOR_PROMPT, COLOR_PRIMARY_TEXT, COLOR_TITLE, COLOR_SUBTITLE,
    COLOR_SECONDARY_TEXT, COLOR_HIGHLIGHT_FG, COLOR_HIGHLIGHT_BG,
    COLOR_ERROR, COLOR_LOADING_SPINNER, COLOR_ASCII, HEADER_ART, POPULAR_GENRES,
    BOUNCING_BAR_FRAMES, COLOR_BOLT, COLOR_BOLT_GLOW
)
from .utils import (
    get_key, RawTerminal, restore_terminal_for_input, enter_raw_mode_after_input,
    ar, ar_wrap, MouseTerminal, get_home_input_event,
    clean_genre, clean_type, clean_status, hide_cursor, show_cursor
)
from .logger import logger
from . import config as config_module

_stars_cache = {"count": 58, "last_fetch": 0}

def get_github_stars():
    global _stars_cache
    now = time.time()
    if now - _stars_cache["last_fetch"] > 1800:
        _stars_cache["last_fetch"] = now
        def _fetch():
            try:
                import urllib.request
                import json
                req = urllib.request.Request(
                    "https://api.github.com/repos/np4abdou1/ani-cli-arabic",
                    headers={"User-Agent": "ani-cli-arabic"}
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode())
                    if "stargazers_count" in data:
                        _stars_cache["count"] = data["stargazers_count"]
            except Exception:
                pass
        threading.Thread(target=_fetch, daemon=True).start()
    return _stars_cache["count"]

class UIManager:
    def __init__(self):
        self.theme = Theme({
            "panel.border": COLOR_BORDER,
            "prompt.prompt": COLOR_PROMPT,
            "prompt.default": COLOR_PRIMARY_TEXT,
            "title": COLOR_TITLE,
            "secondary": COLOR_SECONDARY_TEXT,
            "highlight": f"{COLOR_HIGHLIGHT_FG} on {COLOR_HIGHLIGHT_BG}",
            "error": COLOR_ERROR,
            "info": COLOR_PRIMARY_TEXT,
            "loading": COLOR_LOADING_SPINNER,
        })
        self.console = Console(theme=self.theme)
        hide_cursor()
        self.console.show_cursor(False)

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.console.clear()
        hide_cursor()
        self.console.show_cursor(False)

    def print(self, *args, **kwargs):
        self.console.print(*args, **kwargs)

    def get_header_renderable(self) -> Text:
        return Text(HEADER_ART, style=COLOR_ASCII)

    def _get_torlink_ascii_logo(self, frame_idx=0):
        """
        Returns a fixed-width (32 columns) renderable of the ANICLI AR ASCII art
        with Torlink two-tone split shading and neon green lightning bolt precisely
        locked at column 5 directly above the letter 'N'.
        """
        grid = Table.grid(padding=0)
        grid.add_column(width=32, justify="left")
        bolt_colors = getattr(config_module, "COLOR_BOLT_GLOW", COLOR_BOLT_GLOW)
        bolt_col = bolt_colors[frame_idx % len(bolt_colors)] if frame_idx > 0 else getattr(config_module, "COLOR_BOLT", COLOR_BOLT)
        title_col = getattr(config_module, "COLOR_TITLE", COLOR_TITLE)
        border_col = getattr(config_module, "COLOR_BORDER", COLOR_BORDER)
        grid.add_row(Text("     ⚡", style=f"bold {bolt_col}"))
        grid.add_row(Text("█▀█ █▄ █ █   █▀▀ █   █   █▀█ █▀▄", style=f"bold {title_col}"))
        grid.add_row(Text("█▀█ █ ▀█ █   █▄▄ █▄▄ █   █▀█ █▀▄", style=f"bold {border_col}"))
        return grid

    def render_message(self, title: str, message: str, style_name: str = "info"):
        self.clear()
        
        c_title = getattr(config_module, 'COLOR_TITLE', COLOR_TITLE)
        c_border = getattr(config_module, 'COLOR_BORDER', COLOR_BORDER)
        c_error = getattr(config_module, 'COLOR_ERROR', COLOR_ERROR)
        
        border_col = c_error if style_name == "error" else c_border
        icon = "✗" if style_name == "error" else "ℹ"
        
        # Clean title to prevent double icons
        clean_title = title.replace("✗", "").replace("ℹ", "").replace("✔", "").strip()
        
        # Create styled message text
        message_text = Text()
        for line in message.split('\n'):
            if line.strip():
                if line.startswith('•'):
                    message_text.append(f"  {line}\n", style="white")
                else:
                    message_text.append(f"{line}\n", style="bold white" if style_name == "error" else f"bold {c_border}")
            else:
                message_text.append("\n")
        
        box_width = min(64, self.console.width - 4)
        
        panel = Panel(
            Align.center(message_text, vertical="middle"),
            title=f"[bold {border_col}] {icon} {clean_title} [/bold {border_col}]",
            box=ROUNDED,
            border_style=border_col,
            padding=(1, 4),
            width=box_width
        )
        
        # Header with Logo
        header_table = Table.grid(expand=False)
        header_table.add_column(justify="center")
        header_table.add_row(Align.center(self._get_torlink_ascii_logo()))

        hint_text = Text()
        hint_text.append("[↵/Space] ", style=f"bold {c_title}")
        hint_text.append("Continue", style="dim white")

        root = Table.grid(expand=False)
        root.add_column(justify="center")
        root.add_row(Align.center(header_table))
        root.add_row(Text(""))
        root.add_row(Align.center(panel))
        root.add_row(Text(""))
        root.add_row(Align.center(hint_text))

        self.console.print(Align.center(root, vertical="middle", height=self.console.height))
        
        # We need a proper key wait here rather than Prompt.ask, which requires terminal enter
        with RawTerminal():
            while True:
                key = get_key()
                if key in ['ENTER', ' ', 'ESC', 'q', 'b']:
                    break

    def render_timed_message(self, title: str, message: str, style_name: str = "info", duration: float = 1.4):
        self.clear()

        c_title = getattr(config_module, 'COLOR_TITLE', COLOR_TITLE)
        c_border = getattr(config_module, 'COLOR_BORDER', COLOR_BORDER)
        c_error = getattr(config_module, 'COLOR_ERROR', COLOR_ERROR)
        
        border_col = c_error if style_name == "error" else c_border
        icon = "✗" if style_name == "error" else "ℹ"
        
        clean_title = title.replace("✗", "").replace("ℹ", "").replace("✔", "").strip()
        
        message_text = Text()
        for line in message.split('\n'):
            if line.strip():
                if line.startswith('•'):
                    message_text.append(f"  {line}\n", style="white")
                else:
                    message_text.append(f"{line}\n", style="bold white" if style_name == "error" else f"bold {c_border}")
            else:
                message_text.append("\n")

        box_width = min(64, self.console.width - 4)

        panel = Panel(
            Align.center(message_text, vertical="middle"),
            title=f"[bold {border_col}] {icon} {clean_title} [/bold {border_col}]",
            box=ROUNDED,
            border_style=border_col,
            padding=(1, 4),
            width=box_width
        )

        header_table = Table.grid(expand=False)
        header_table.add_column(justify="center")
        header_table.add_row(Align.center(self._get_torlink_ascii_logo()))

        root = Table.grid(expand=False)
        root.add_column(justify="center")
        root.add_row(Align.center(header_table))
        root.add_row(Text(""))
        root.add_row(Align.center(panel))

        with Live(
            Align.center(root, vertical="middle", height=self.console.height),
            console=self.console,
            refresh_per_second=10,
            screen=True
        ):
            time.sleep(max(0.5, duration))

    def run_with_loading(self, message: str, target_func, *args):
        self.clear()
        
        result_container = {}
        thread_done = threading.Event()

        def worker():
            try:
                result = target_func(*args)
                result_container['result'] = result
            except Exception as e:
                result_container['error'] = e
            finally:
                thread_done.set()

        loading_thread = threading.Thread(target=worker, daemon=True)
        loading_thread.start()

        bouncing_frames = getattr(config_module, "BOUNCING_BAR_FRAMES", BOUNCING_BAR_FRAMES)
        b_col = getattr(config_module, "COLOR_BOLT", COLOR_BOLT)
        t_col = getattr(config_module, "COLOR_TITLE", COLOR_TITLE)
        sub_col = getattr(config_module, "COLOR_SUBTITLE", COLOR_SUBTITLE)
        bor_col = getattr(config_module, "COLOR_BORDER", COLOR_BORDER)
        spin_col = getattr(config_module, "COLOR_LOADING_SPINNER", COLOR_LOADING_SPINNER)
        accent_colors = [b_col, t_col, spin_col, sub_col, bor_col, b_col]
        
        clean_msg = "Searching..."
        if message:
            clean = re.sub(r"(?i)\s*from\s+anime3rb|anime3rb", "", message).strip()
            if not clean.endswith("..."):
                clean = clean + "..."
            clean_msg = clean

        frame_idx = 0

        def generate_loading_renderable():
            frame = bouncing_frames[frame_idx % len(bouncing_frames)]
            color = accent_colors[frame_idx % len(accent_colors)]

            msg_text = Text()
            msg_text.append(f"{frame} ", style=f"bold {color}")
            msg_text.append(clean_msg, style="bold white")

            root = Table.grid(expand=False)
            root.add_column(justify="center")
            root.add_row(Align.center(self._get_torlink_ascii_logo(frame_idx)))
            root.add_row(Text(""))
            root.add_row(Align.center(msg_text))

            return Align.center(root, vertical="middle", height=self.console.height)

        try:
            with Live(generate_loading_renderable(), console=self.console, refresh_per_second=15, screen=True) as live:
                while not thread_done.is_set():
                    frame_idx += 1
                    live.update(generate_loading_renderable())
                    time.sleep(0.08)
        except KeyboardInterrupt:
            thread_done.set()
            raise

        self.clear()

        if 'error' in result_container:
            raise result_container['error']
        
        return result_container.get('result')

    def home_screen_menu(self, rpc_status=None, version_info=None, active_provider=None):
        """
        Interactive, ultra-minimal home screen with live character input,
        tactile mechanical keycaps, mouse click & hover support, and zero box clutter.
        """
        query = ""
        hovered_btn = None

        shortcut_items = [
            {"key": "e", "label": "Latest", "action": "latest"},
            {"key": "m", "label": "Movies", "action": "movies"},
            {"key": "t", "label": "Trending", "action": "trending"},
            {"key": "p", "label": "Popular", "action": "popular"},
            {"key": "r", "label": "Top Rated", "action": "top_rated"},
            {"key": "g", "label": "Genres", "action": "genres"},
            {"key": "s", "label": "Studios", "action": "studios"},
            {"key": "l", "label": "History", "action": "history"},
            {"key": "f", "label": "Favorites", "action": "favorites"},
            {"key": "c", "label": "Settings", "action": "settings"},
            {"key": "d", "label": "Donate", "action": "donate"},
            {"key": "q", "label": "Quit", "action": "quit"},
        ]

        def generate_renderable(cur_query, hovered):
            screen_w = max(40, self.console.width)
            table = Table.grid(expand=False)
            table.add_column(justify="center")
            # 1. Centered Header Logo with Lightning Bolt precisely on letter 'N'
            table.add_row(Align.center(self._get_torlink_ascii_logo()))
            table.add_row(Text(""))

            # 2. Clean Tagline
            tagline = Text("Direct Terminal Anime Streamer", style=f"bold {COLOR_SUBTITLE}")
            table.add_row(Align.center(tagline))

            # 3. Reimagined Metadata Badges (No yellow, clean bracket badges)
            meta = Text()

            meta.append("[ ", style="dim")
            meta.append(f"{APP_VERSION}", style="bold white")
            meta.append(" ]   ", style="dim")
            meta.append("[ ", style="dim")
            meta.append("@np4abdou1", style=f"bold {COLOR_TITLE}")
            meta.append(" ]   ", style="dim")
            meta.append("[ ", style="dim")
            meta.append(f"★ {get_github_stars()}", style=f"bold {COLOR_TITLE}")
            meta.append(" ]", style="dim")
            
            table.add_row(Align.center(meta))
            table.add_row(Text(""))

            # 4. Compact Search Box with Embedded Title Border
            box_width = min(68, screen_w - 4)
            input_text = Text()
            input_text.append("> ", style=f"bold {COLOR_TITLE}")
            if cur_query:
                input_text.append(cur_query, style="bold white")
                input_text.append("█", style=f"bold {COLOR_TITLE}")
            else:
                input_text.append("Search anime or type shortcut (e, m, t, p, r, g)...", style="dim")
                input_text.append("█", style=f"bold {COLOR_TITLE}")

            search_panel = Panel(
                Align.center(input_text),
                title=f"[bold {COLOR_TITLE}]Search[/bold {COLOR_TITLE}]",
                title_align="center",
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(0, 1),
                width=box_width
            )
            table.add_row(Align.center(search_panel))
            table.add_row(Text(""))

            # 5. Clean Keybinds Grid (4 columns x 3 rows)
            grid = Table.grid(padding=(0, 3))
            grid.add_column(justify="left")
            grid.add_column(justify="left")
            grid.add_column(justify="left")
            grid.add_column(justify="left")

            def format_item(key, label, action_key, fg):
                is_hov = (hovered == action_key)
                t = Text()
                if is_hov:
                    if key == "↵":
                        t.append("↵ search", style=f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    elif key == "q":
                        t.append("^c quit", style="bold black on #d97979")
                    else:
                        t.append(f"[{key}] {label}", style=f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                else:
                    if key == "↵":
                        t.append("↵", style=f"bold {fg}")
                        t.append(f" {label}", style="dim")
                    elif key == "q":
                        t.append("^c", style=f"bold {fg}")
                        t.append(f" {label}", style="dim")
                    else:
                        t.append("[", style="dim")
                        t.append(key, style=f"bold {fg}")
                        t.append("]", style="dim")
                        t.append(f" {label}", style="dim")
                return t

            row1 = [
                format_item("↵", "search", "search", COLOR_TITLE),
                format_item("e", "latest eps", "e", COLOR_TITLE),
                format_item("m", "movies", "m", COLOR_TITLE),
                format_item("t", "trending", "t", COLOR_TITLE),
            ]
            row2 = [
                format_item("p", "popular", "p", COLOR_TITLE),
                format_item("r", "top rated", "r", COLOR_TITLE),
                format_item("g", "genres", "g", COLOR_TITLE),
                format_item("s", "studios", "s", COLOR_TITLE),
            ]
            row3 = [
                format_item("l", "history", "l", COLOR_TITLE),
                format_item("f", "favorites", "f", COLOR_TITLE),
                format_item("c", "settings", "c", COLOR_TITLE),
                format_item("q", "quit", "q", "#d97979"),
            ]
            grid.add_row(*row1)
            grid.add_row(*row2)
            grid.add_row(*row3)

            table.add_row(Align.center(grid))
            table.add_row(Text(""))

            # 6. Status Bar (Provider & RPC) - Greyed out
            status_text = Text()
            if active_provider:
                status_text.append(f"provider: {active_provider.lower()}   ", style="dim")
            if rpc_status is not None:
                rpc_state = "on" if rpc_status else "off"
                status_text.append(f"rpc: {rpc_state}", style="dim")
                
            if status_text.plain:
                table.add_row(Align.center(status_text))

            return Align.center(table, vertical="middle", height=self.console.height)

        self.clear()

        with MouseTerminal():
            with Live(
                generate_renderable(query, hovered_btn),
                console=self.console,
                auto_refresh=False,
                screen=True,
                refresh_per_second=20
            ) as live:
                while True:
                    ev = get_home_input_event()
                    if not ev:
                        time.sleep(0.02)
                        continue

                    ev_type, payload = ev[0], ev[1] if len(ev) > 1 else None

                    if ev_type == 'ESC':
                        if query:
                            query = ""
                            live.update(generate_renderable(query, hovered_btn), refresh=True)
                        else:
                            return ("quit", None)

                    elif ev_type == 'ENTER':
                        clean_q = query.strip()
                        if clean_q:
                            for it in shortcut_items:
                                if clean_q.lower() == it["key"] or clean_q.lower() == it["label"].lower():
                                    return (it["action"], None)
                            return ("search", clean_q)
                        else:
                            if hovered_btn:
                                for it in shortcut_items:
                                    if hovered_btn == it["key"]:
                                        return (it["action"], None)

                    elif ev_type == 'BACKSPACE':
                        if query:
                            query = query[:-1]
                            live.update(generate_renderable(query, hovered_btn), refresh=True)

                    elif ev_type == 'CHAR':
                        char = payload
                        query += char
                        live.update(generate_renderable(query, hovered_btn), refresh=True)

                    elif ev_type == 'MOUSE_MOVE':
                        x, y = ev[1], ev[2]
                        screen_h = self.console.height
                        screen_w = self.console.width
                        new_hover = None
                        box_row = screen_h // 2 + 4
                        if abs(y - box_row) <= 4:
                            footer_span = 74
                            start_x = max(1, (screen_w - footer_span) // 2)
                            if start_x <= x <= start_x + footer_span:
                                rel_x = x - start_x
                                col_idx = min(3, max(0, int(rel_x / (footer_span / 4))))
                                row_offset = y - (box_row - 1)
                                if 0 <= row_offset < 3:
                                    action_map = [
                                        ["search", "e", "m", "t"],
                                        ["p", "r", "g", "s"],
                                        ["l", "f", "c", "q"]
                                    ]
                                    new_hover = action_map[row_offset][col_idx]

                        if new_hover != hovered_btn:
                            hovered_btn = new_hover
                            live.update(generate_renderable(query, hovered_btn), refresh=True)

                    elif ev_type == 'MOUSE_CLICK':
                        if hovered_btn:
                            for it in shortcut_items:
                                if hovered_btn == it["key"] or (hovered_btn == "search" and it["action"] == "search"):
                                    return (it["action"], None)

    def latest_episodes_menu(self, episodes):
        selected = 0
        scroll_offset = 0
        screen_height = self.console.height
        max_display = min(12, max(5, screen_height - 14))

        def generate_renderable():
            box_width = min(88, self.console.width - 4)
            inner_w = box_width - 6
            content = Text()

            start = scroll_offset
            end = min(start + max_display, len(episodes))

            for idx in range(start, end):
                ep = episodes[idx]
                is_selected = (idx == selected)

                ep_badge = f"[ EP {str(ep.get('ep_num', '?')).zfill(2)} ]"
                raw_title = ep.get('title', 'Unknown')
                avail_title = max(10, inner_w - len(ep_badge) - 8)
                disp_title = raw_title[:avail_title-3] + "..." if len(raw_title) > avail_title else raw_title
                pad = " " * max(1, inner_w - len(disp_title) - len(ep_badge) - 5)

                if is_selected:
                    row = Text()
                    row.append(" ▶ ")
                    row.append(disp_title)
                    row.append(pad)
                    row.append(ep_badge)
                    row.stylize(f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    content.append_text(row)
                    content.append("\n")
                else:
                    content.append("   ", style="white")
                    content.append(disp_title, style="white")
                    content.append(pad)
                    content.append(ep_badge, style=f"bold {COLOR_TITLE}")
                    content.append("\n")

            panel = Panel(
                content,
                title=f"[bold {COLOR_TITLE}]⚡ Latest Released Episodes[/bold {COLOR_TITLE}]",
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(1, 2),
                width=box_width
            )

            header_table = Table.grid(expand=False)
            header_table.add_column(justify="center")
            header_table.add_row(Align.center(self._get_torlink_ascii_logo()))
            header_table.add_row(Text(""))

            title_badge = Text()
            title_badge.append("[ ", style=f"bold {COLOR_BORDER}")
            title_badge.append(f"Newly Added Episodes • {len(episodes)} releases", style="bold white")
            title_badge.append(" ]", style=f"bold {COLOR_BORDER}")
            header_table.add_row(Align.center(title_badge))
            header_table.add_row(Text(""))
            header_table.add_row(Align.center(panel))
            header_table.add_row(Text(""))

            dock_grid = Table.grid(padding=(0, 3))
            dock_grid.add_column(justify="left")
            dock_grid.add_column(justify="left")
            dock_grid.add_column(justify="left")

            def format_k(k, flabel, fg):
                t = Text()
                if k == "↵":
                    t.append("↵", style=f"bold {fg}")
                    t.append(f" {flabel}", style="white")
                else:
                    t.append("[", style=f"bold {COLOR_BORDER}")
                    t.append(k, style=f"bold {fg}")
                    t.append("]", style=f"bold {COLOR_BORDER}")
                    t.append(f" {flabel}", style="white")
                return t

            row1 = [
                format_k("↵", "play episode", COLOR_TITLE),
                format_k("s", "anime details", COLOR_TITLE),
                format_k("b", "back", "#ff79c6"),
            ]
            dock_grid.add_row(*row1)
            header_table.add_row(Align.center(dock_grid))

            return Align.center(header_table, vertical="middle", height=self.console.height)

        self.clear()

        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=15) as live:
                while True:
                    key = get_key()
                    if key in ['UP', 'k', 'K'] and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(generate_renderable(), refresh=True)
                    elif key in ['DOWN', 'j', 'J'] and selected < len(episodes) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(generate_renderable(), refresh=True)
                    elif key in ['ENTER', ' ']:
                        return (selected, 'play')
                    elif key in ['s', 'S']:
                        return (selected, 'details')
                    elif key in ['b', 'B', 'ESC', 'q', 'Q']:
                        return None

    def genre_selection_menu(self, genres_list=None):
        genres = genres_list or POPULAR_GENRES
        selected = 0
        scroll_offset = 0
        screen_height = self.console.height
        max_display = min(12, max(6, screen_height - 14))

        def generate_renderable():
            box_width = min(72, self.console.width - 4)
            inner_w = box_width - 6
            content = Text()

            start = scroll_offset
            end = min(start + max_display, len(genres))

            for idx in range(start, end):
                g = genres[idx]
                is_selected = (idx == selected)
                num_tag = f"[ {str(idx + 1).zfill(2)} ]"
                name_en = g.get("name_en", "") if isinstance(g, dict) else str(g)
                name_ar = g.get("name_ar", "") if isinstance(g, dict) else ""

                label_text = f"{name_en} • {ar(name_ar)}" if name_ar else name_en
                pad = " " * max(1, inner_w - len(num_tag) - cell_len(label_text) - 4)

                if is_selected:
                    row = Text()
                    row.append(" ▶ ")
                    row.append(num_tag, style=f"bold {COLOR_HIGHLIGHT_FG}")
                    row.append(f"  {label_text}")
                    row.append(pad)
                    row.stylize(f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    content.append_text(row)
                    content.append("\n")
                else:
                    content.append("   ", style="white")
                    content.append(num_tag, style=f"bold {COLOR_TITLE}")
                    content.append(f"  {label_text}", style="white")
                    content.append(pad)
                    content.append("\n")

            panel = Panel(
                content,
                title=f"[bold {COLOR_TITLE}]Categories & Genres (التصنيفات)[/bold {COLOR_TITLE}]",
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(1, 2),
                width=box_width
            )

            header_table = Table.grid(expand=False)
            header_table.add_column(justify="center")
            header_table.add_row(Align.center(self._get_torlink_ascii_logo()))
            header_table.add_row(Text(""))

            title_badge = Text()
            title_badge.append("[ ", style=f"bold {COLOR_BORDER}")
            title_badge.append(f"Select Genre • {len(genres)} categories", style="bold white")
            title_badge.append(" ]", style=f"bold {COLOR_BORDER}")
            header_table.add_row(Align.center(title_badge))
            header_table.add_row(Text(""))
            header_table.add_row(Align.center(panel))
            header_table.add_row(Text(""))

            dock_grid = Table.grid(padding=(0, 3))
            dock_grid.add_column(justify="left")
            dock_grid.add_column(justify="left")

            def format_k(k, flabel, fg):
                t = Text()
                if k == "↵":
                    t.append("↵", style=f"bold {fg}")
                    t.append(f" {flabel}", style="white")
                else:
                    t.append("[", style=f"bold {COLOR_BORDER}")
                    t.append(k, style=f"bold {fg}")
                    t.append("]", style=f"bold {COLOR_BORDER}")
                    t.append(f" {flabel}", style="white")
                return t

            row1 = [
                format_k("↵", "explore genre", COLOR_TITLE),
                format_k("b", "back", "#ff79c6"),
            ]
            dock_grid.add_row(*row1)
            header_table.add_row(Align.center(dock_grid))

            return Align.center(header_table, vertical="middle", height=self.console.height)

        self.clear()

        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=15) as live:
                while True:
                    key = get_key()
                    if key in ['UP', 'k', 'K'] and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(generate_renderable(), refresh=True)
                    elif key in ['DOWN', 'j', 'J'] and selected < len(genres) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(generate_renderable(), refresh=True)
                    elif key in ['ENTER', ' ']:
                        return genres[selected]
                    elif key in ['b', 'B', 'ESC', 'q', 'Q']:
                        return None


    def anime_selection_menu(self, results, load_more_callback=None, api=None):
        selected = 0
        scroll_offset = 0
        is_loading_more = False
        has_more = True
        
        screen_height = self.console.height
        max_display = min(12, max(5, screen_height - 14))

        def generate_renderable():
            nonlocal is_loading_more
            box_w = min(104, self.console.width - 4)
            inner_w = box_w - 4
            
            content = Text()
            start = scroll_offset
            end = min(start + max_display, len(results))
            
            for idx in range(start, end):
                anime = results[idx]
                is_selected = (idx == selected)
                
                display_t = anime.title_en or getattr(anime, "title", "Unknown")
                
                score_val = getattr(anime, "score", "") or ""
                score_b = f"[ ★ {score_val:>4} ]" if score_val and str(score_val).strip() not in ["N/A", "None", "0"] else " " * 10
                
                type_val = getattr(anime, "type", "") or ""
                type_text = clean_type(str(type_val)) if type_val and str(type_val).strip() not in ["N/A", "None", ""] else "TV"
                type_b = f"[ {type_text:^7} ]" if type_text else " " * 11
                
                premiered_val = getattr(anime, "premiered", "") or getattr(anime, "year", "") or ""
                year_match = re.search(r"\b(19\d\d|20\d\d)\b", str(premiered_val))
                year_text = year_match.group(1) if year_match else (str(premiered_val) if premiered_val and str(premiered_val).strip() not in ["N/A", "None", ""] else "")
                year_b = f"[ {year_text:^4} ]" if year_text else " " * 8
                
                badges_str = f"{year_b}  {type_b}  {score_b}"
                badges_w = cell_len(badges_str)
                
                prefix = " ▶ " if is_selected else "   "
                prefix_w = cell_len(prefix)
                
                avail_title = inner_w - prefix_w - badges_w - 1
                display_title = display_t
                if cell_len(display_title) > avail_title:
                    while cell_len(display_title) > avail_title - 3 and len(display_title) > 0:
                        display_title = display_title[:-1]
                    display_title += "..."
                
                title_w = cell_len(display_title)
                pad_len = max(1, inner_w - prefix_w - title_w - badges_w)
                pad_spaces = " " * pad_len
                
                if is_selected:
                    row_text = Text()
                    row_text.append(prefix, style=f"bold {COLOR_HIGHLIGHT_FG}")
                    row_text.append(display_title, style=f"bold {COLOR_HIGHLIGHT_FG}")
                    row_text.append(pad_spaces)
                    row_text.append(year_b, style=f"bold {COLOR_HIGHLIGHT_FG}")
                    row_text.append("  ")
                    row_text.append(type_b, style=f"bold {COLOR_HIGHLIGHT_FG}")
                    row_text.append("  ")
                    row_text.append(score_b, style=f"bold {COLOR_HIGHLIGHT_FG}")
                    row_text.stylize(f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    content.append_text(row_text)
                    content.append("\n")
                else:
                    content.append(prefix, style="white")
                    content.append(display_title, style="white")
                    content.append(pad_spaces)
                    content.append(year_b, style=f"bold {COLOR_SUBTITLE}")
                    content.append("  ")
                    content.append(type_b, style="bold white")
                    content.append("  ")
                    content.append(score_b, style=f"bold {COLOR_TITLE}")
                    content.append("\n")
            
            panel = Panel(
                content,
                title=f"[bold {COLOR_TITLE}]Search Results ({len(results)} items)[/bold {COLOR_TITLE}]",
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(0, 1),
                width=box_w
            )
            
            if is_loading_more:
                dock = Align.center(Text("[====] Loading more anime... ", style=f"bold {COLOR_TITLE}"))
            else:
                dock_text = Text()
                items = [
                    ("↵", "select", COLOR_TITLE),
                    ("↑↓/jk", "navigate", COLOR_TITLE),
                    ("b", "back", "#ff79c6"),
                    ("q", "quit", "#d97979"),
                ]
                for idx, (k, flabel, fg) in enumerate(items):
                    if k == "↵":
                        dock_text.append("↵", style=f"bold {fg}")
                        dock_text.append(f" {flabel}", style="white")
                    else:
                        dock_text.append("[", style=f"bold {COLOR_BORDER}")
                        dock_text.append(k, style=f"bold {fg}")
                        dock_text.append("]", style=f"bold {COLOR_BORDER}")
                        dock_text.append(f" {flabel}", style="white")
                    if idx < len(items) - 1:
                        dock_text.append("  •  ", style=f"bold {COLOR_BORDER}")
                dock = Align.center(dock_text)
            
            root = Table.grid(expand=False)
            root.add_column(justify="center")
            root.add_row(Align.center(self._get_torlink_ascii_logo()))
            root.add_row(Text(""))
            root.add_row(Align.center(panel))
            root.add_row(Text(""))
            root.add_row(dock)
            
            return Align.center(root, vertical="middle", height=self.console.height)

        self.clear()
        
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    needs_update = False
                    
                    if (key == 'UP' or key == 'k') and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        needs_update = True
                    elif (key == 'DOWN' or key == 'j') and selected < len(results) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        needs_update = True
                        
                        # Predictive loading: when user is 5 items from the end, load more
                        if load_more_callback and has_more and not is_loading_more:
                            if selected >= len(results) - 5:
                                is_loading_more = True
                                live.update(generate_renderable(), refresh=True)
                                
                                def load_in_background():
                                    nonlocal is_loading_more, has_more
                                    try:
                                        new_results = load_more_callback(len(results))
                                        if new_results:
                                            seen_ids = {r.id for r in results}
                                            for r in new_results:
                                                if r.id not in seen_ids:
                                                    results.append(r)
                                                    seen_ids.add(r.id)
                                        else:
                                            has_more = False
                                    except Exception:
                                        pass
                                    finally:
                                        is_loading_more = False
                                        live.update(generate_renderable(), refresh=True)
                                
                                threading.Thread(target=load_in_background, daemon=True).start()
                    elif key == 'ENTER':
                        return selected
                    elif key == 'b' or key == 'ESC':
                        return None
                    elif key == 'q':
                        return -1
                    
                    if needs_update:
                        live.update(generate_renderable(), refresh=True)

    @lru_cache(maxsize=50)
    def _generate_poster_ansi(self, url, max_height):
        """Generate ANSI art from poster URL with automatic LRU caching."""
        if not url:
            return Text("No poster available", style="secondary")
        
        try:
            res = requests.get(url, timeout=5)
            img = Image.open(BytesIO(res.content)).convert("RGB")
            
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.8)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.15)
            
            target_pixel_height = max_height * 2
            new_height = target_pixel_height
            new_width = int((img.width / img.height) * new_height * 2.0)
            
            if new_width % 2 != 0:
                new_width -= 1
            if new_height % 2 != 0:
                new_height -= 1
            
            # Use LANCZOS for better downsampling quality (prevent pixelation)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            arr = np.array(img, dtype=np.uint8)
            
            quadrants = [' ', '▘', '▝', '▀', '▖', '▌', '▞', '▛', '▗', '▚', '▐', '▜', '▄', '▙', '▟', '█']
            output_lines = []
            
            # Process in batches for speed
            for y in range(0, new_height, 2):
                line_parts = []  # No padding to fit outline
                for x in range(0, new_width, 2):
                    # Get 2x2 block
                    p0 = arr[y, x]
                    p1 = arr[y, x+1] if x+1 < new_width else p0
                    p2 = arr[y+1, x] if y+1 < new_height else p0
                    p3 = arr[y+1, x+1] if (y+1 < new_height and x+1 < new_width) else p0
                    
                    def calculate_luminance(p):
                        return 0.299*p[0] + 0.587*p[1] + 0.114*p[2]
                    lums = [calculate_luminance(p0), calculate_luminance(p1), calculate_luminance(p2), calculate_luminance(p3)]
                    avg_lum = sum(lums) / 4
                    
                    # Split by luminance threshold
                    mask = [lum_val > avg_lum for lum_val in lums]
                    
                    # Calculate average colors for each group
                    bright = [p for i, p in enumerate([p0, p1, p2, p3]) if mask[i]]
                    dark = [p for i, p in enumerate([p0, p1, p2, p3]) if not mask[i]]
                    
                    if bright:
                        fg = np.mean(bright, axis=0).astype(int)
                    else:
                        fg = np.mean([p0, p1, p2, p3], axis=0).astype(int)
                    
                    if dark:
                        bg = np.mean(dark, axis=0).astype(int)
                    else:
                        bg = fg
                    
                    # Determine quadrant character
                    if all(mask):
                        char_idx = 15
                    elif not any(mask):
                        char_idx = 15
                    else:
                        q_val = 0
                        if mask[0]:
                            q_val += 1
                        if mask[1]:
                            q_val += 2
                        if mask[2]:
                            q_val += 4
                        if mask[3]:
                            q_val += 8
                        char_idx = q_val
                    
                    char = quadrants[char_idx]
                    line_parts.append(f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m\033[48;2;{bg[0]};{bg[1]};{bg[2]}m{char}")
                
                line_parts.append("\033[0m")
                output_lines.append("".join(line_parts))
            
            result = Text.from_ansi("\n".join(output_lines))
            
            return result
            
        except Exception:
            return Text("Poster unavailable", style="dim")

    def selection_menu(self, items, title="Select Item"):
        selected = 0
        scroll_offset = 0
        
        screen_height = self.console.height
        max_display = max(6, min(14, screen_height - 14))

        def generate_renderable():
            content = Text()
            start = scroll_offset
            end = min(start + max_display, len(items))
            
            for idx in range(start, end):
                item = items[idx]
                is_selected = (idx == selected)
                
                if is_selected:
                    row_text = Text()
                    row_text.append(" ▶ ")
                    row_text.append(f"{item}")
                    row_text.stylize(f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    content.append_text(row_text)
                    content.append("\n")
                else:
                    content.append(f"   {item}\n", style="white")
            
            box_width = min(60, self.console.width - 4)
            panel = Panel(
                content,
                title=f"[bold {COLOR_TITLE}]{title}[/bold {COLOR_TITLE}]",
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(1, 3),
                width=box_width
            )

            # Header with Logo & Title Badge
            header_table = Table.grid(expand=False)
            header_table.add_column(justify="center")
            header_table.add_row(Align.center(self._get_torlink_ascii_logo()))
            header_table.add_row(Text(""))

            title_badge = Text()
            title_badge.append("[ ", style=f"bold {COLOR_BORDER}")
            title_badge.append(f"{title}", style="bold white")
            title_badge.append(" ]", style=f"bold {COLOR_BORDER}")
            header_table.add_row(Align.center(title_badge))

            # Clean Keycaps Dock
            dock = Text()
            dock_items = [("↵", "select", COLOR_TITLE), ("↑↓/jk", "navigate", COLOR_TITLE), ("b", "back", "#ff79c6")]
            for idx, (k, flabel, fg) in enumerate(dock_items):
                if k == "↵":
                    dock.append("↵", style=f"bold {fg}")
                    dock.append(f" {flabel}", style="white")
                else:
                    dock.append("[", style=f"bold {COLOR_BORDER}")
                    dock.append(k, style=f"bold {fg}")
                    dock.append("]", style=f"bold {COLOR_BORDER}")
                    dock.append(f" {flabel}", style="white")
                if idx < len(dock_items) - 1:
                    dock.append("   •   ", style=f"bold {COLOR_BORDER}")

            root = Table.grid(expand=False)
            root.add_column(justify="center")
            root.add_row(Align.center(header_table))
            root.add_row(Text(""))
            root.add_row(Align.center(panel))
            root.add_row(Text(""))
            root.add_row(Align.center(dock))
            
            return Align.center(root, vertical="middle", height=self.console.height)

        self.clear()
        
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    
                    if (key == 'UP' or key == 'k') and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(generate_renderable(), refresh=True)
                    elif (key == 'DOWN' or key == 'j') and selected < len(items) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'ENTER':
                        return items[selected]
                    elif key == 'q' or key == 'b' or key == 'ESC':
                        return None

    def episode_selection_menu(
        self,
        anime_title,
        episodes,
        rpc_manager=None,
        anime_poster=None,
        last_watched_ep=None,
        is_favorite=False,
        anime_details=None,
        default_download_quality="1080p",
        download_mode="internal",
        download_path="downloads",
        initial_selected=0
    ):
        selected = max(0, min(int(initial_selected or 0), len(episodes) - 1)) if episodes else 0
        scroll_offset = 0
        
        if rpc_manager:
            rpc_manager.update_selecting_episode(anime_title, anime_poster)

        screen_height = self.console.height
        max_display = min(14, max(6, screen_height - 14))

        if selected >= max_display:
            scroll_offset = max(0, selected - (max_display // 2))

        poster_height = max_display + 2
        poster_renderable = None
        poster_width = 26
        if anime_poster and poster_height > 0:
            poster_renderable = self._generate_poster_ansi(anime_poster, poster_height)
            if poster_renderable:
                try:
                    lines = poster_renderable.plain.split('\n')
                    if lines:
                        poster_width = max(cell_len(line) for line in lines if line.strip())
                except Exception:
                    pass

        poster_box_w = (poster_width + 4) if poster_renderable else 0
        max_title_w = max((cell_len(ar(ep.title)) if ep.title else 0) for ep in episodes) if episodes else 20
        
        MIN_EP_W = 46
        avail_for_ep = self.console.width - (poster_box_w + 8 if poster_renderable else 6)
        MAX_EP_W = max(52, min(84, avail_for_ep))
        ep_box_w = max(MIN_EP_W, min(MAX_EP_W, max_title_w + 18))
        inner_w = ep_box_w - 4

        def generate_renderable():
            content = Text()
            start = scroll_offset
            end = min(start + max_display, len(episodes))

            for idx in range(start, end):
                ep = episodes[idx]
                is_sel = (idx == selected)

                prefix = " ▶ " if is_sel else "   "
                prefix_w = cell_len(prefix)

                is_last_watched = (last_watched_ep is not None and str(ep.display_num) == str(last_watched_ep))
                suffix = " 👁" if is_last_watched else ""
                suffix_w = cell_len(suffix)

                type_str = f" [{ep.type}]" if (ep.type and str(ep.type).lower() != "episode") else ""
                type_w = cell_len(type_str)

                ep_num_str = f"#{str(ep.display_num).zfill(2)}" if len(episodes) > 9 else f"#{ep.display_num}"
                
                clean_title = (ep.title or "").strip()
                clean_title = re.sub(r'^(الحلقة|الحلقه|Episode|Ep|EP)\s*[:\s\-]*\d+\s*[:\s\-]*', '', clean_title, flags=re.IGNORECASE).strip()
                if clean_title and not re.fullmatch(r'^\d+$', clean_title) and clean_title != str(ep.display_num):
                    title_part = f" • {ar(clean_title)}"
                else:
                    title_part = ""

                full_title = f"{ep_num_str}{title_part}"
                avail_title_w = max(10, inner_w - prefix_w - type_w - suffix_w)

                disp_title = full_title
                if cell_len(disp_title) > avail_title_w:
                    while cell_len(disp_title) > avail_title_w - 3 and len(disp_title) > 0:
                        disp_title = disp_title[:-1]
                    disp_title += "..."

                title_w = cell_len(disp_title)
                pad_len = max(0, inner_w - prefix_w - title_w - type_w - suffix_w)
                pad_spaces = " " * pad_len

                if is_sel:
                    row = Text()
                    row.append(prefix, style=f"bold {COLOR_HIGHLIGHT_FG}")
                    row.append(disp_title, style=f"bold {COLOR_HIGHLIGHT_FG}")
                    if type_str:
                        row.append(type_str, style=f"bold {COLOR_HIGHLIGHT_FG}")
                    if suffix:
                        row.append(suffix, style=f"bold {COLOR_HIGHLIGHT_FG}")
                    row.append(pad_spaces)
                    row.stylize(f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    content.append_text(row)
                    content.append("\n")
                else:
                    content.append(prefix, style="white")
                    bolt_color = getattr(config_module, "COLOR_BOLT", COLOR_BOLT)
                    style = f"bold {bolt_color}" if is_last_watched else "white"
                    content.append(disp_title, style=style)
                    if type_str:
                        content.append(type_str, style=f"bold {COLOR_SUBTITLE}")
                    if suffix:
                        content.append(suffix, style=f"bold {bolt_color}")
                    content.append(pad_spaces)
                    content.append("\n")

            ep_panel = Panel(
                content,
                title=f"[bold {COLOR_TITLE}]Episode List ({len(episodes)} eps)[/bold {COLOR_TITLE}]",
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(0, 1),
                width=ep_box_w
            )

            if poster_renderable:
                poster_panel = Panel(
                    Align.center(poster_renderable, vertical="middle"),
                    title=f"[bold {COLOR_TITLE}]Poster[/bold {COLOR_TITLE}]",
                    box=HEAVY,
                    border_style=COLOR_BORDER,
                    padding=(0, 0),
                    width=poster_box_w
                )
                body = Table.grid(padding=(0, 2))
                body.add_column()
                body.add_column()
                body.add_row(ep_panel, poster_panel)
            else:
                body = ep_panel

            # Enhanced Title Badge under Header Logo
            title_badge = Text()
            title_badge.append("[ ", style=f"bold {COLOR_BORDER}")
            title_badge.append(f"{ar(anime_title)}", style="bold white")
            title_badge.append(" ]", style=f"bold {COLOR_BORDER}")
            if is_favorite:
                title_badge.append("   [ ", style="bold #ff79c6")
                title_badge.append("★ Favorited", style="bold #ff79c6")
                title_badge.append(" ]", style="bold #ff79c6")

            header_table = Table.grid(expand=False)
            header_table.add_column(justify="center")
            header_table.add_row(Align.center(self._get_torlink_ascii_logo()))
            header_table.add_row(Text(""))
            header_table.add_row(Align.center(title_badge))

            # Organized 2-Row Keybinds Grid (4 columns x 2 rows)
            dock_grid = Table.grid(padding=(0, 3))
            dock_grid.add_column(justify="left")
            dock_grid.add_column(justify="left")
            dock_grid.add_column(justify="left")
            dock_grid.add_column(justify="left")

            def format_ep_key(k, flabel, fg):
                t = Text()
                if k == "↵":
                    t.append("↵", style=f"bold {fg}")
                    t.append(f" {flabel}", style="white")
                else:
                    t.append("[", style=f"bold {COLOR_BORDER}")
                    t.append(k, style=f"bold {fg}")
                    t.append("]", style=f"bold {COLOR_BORDER}")
                    t.append(f" {flabel}", style="white")
                return t

            row1 = [
                format_ep_key("↵", "play", COLOR_TITLE),
                format_ep_key("↑↓/jk", "navigate", COLOR_TITLE),
                format_ep_key("d", "download", COLOR_TITLE),
                format_ep_key("g", "jump", COLOR_TITLE),
            ]
            row2 = [
                format_ep_key("f", "favorite", "#ff79c6"),
                format_ep_key("m", "batch", COLOR_TITLE),
                format_ep_key("b", "back", "#ff79c6"),
                format_ep_key("q", "quit", "#d97979"),
            ]
            dock_grid.add_row(*row1)
            dock_grid.add_row(*row2)

            root = Table.grid(expand=False)
            root.add_column(justify="center")
            root.add_row(Align.center(header_table))
            root.add_row(Text(""))
            root.add_row(Align.center(body))
            root.add_row(Text(""))
            root.add_row(Align.center(dock_grid))

            return Align.center(root, vertical="middle", height=self.console.height)

        self.clear()

        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    
                    if (key == 'UP' or key == 'k') and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(generate_renderable(), refresh=True)
                    elif (key == 'DOWN' or key == 'j') and selected < len(episodes) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'ENTER':
                        return selected
                    elif key == 'f' or key == 'F':
                        return 'toggle_fav'
                    elif key == 'd' or key == 'D':
                        return ('download_current', selected)
                    elif key == 'm' or key == 'M':
                        return 'batch_mode'
                    elif key == 't' or key == 'T':
                        return 'trailer'
                    elif key == 'b' or key == 'ESC' or key == 'q':
                        return None
                    elif key == 'g' or key == 'G':
                        live.stop()
                        try:
                            restore_terminal_for_input()
                            prompt_panel = Panel(
                                Text("Jump to episode number:", style=f"bold {COLOR_SUBTITLE}", justify="center"), 
                                box=HEAVY, 
                                border_style=COLOR_BORDER,
                            )
                            self.console.print(Align.center(prompt_panel, vertical="middle", height=7))
                            
                            prompt_string = f" {Text('›', style=COLOR_PROMPT)} "
                            pad_width = (self.console.width - 30) // 2
                            padding = " " * max(0, pad_width)
                            ep_input = Prompt.ask(f"{padding}{prompt_string}", console=self.console)
                            
                            try:
                                ep_num_float = float(ep_input)
                                target_idx = -1
                                for idx, ep in enumerate(episodes):
                                    if float(ep.display_num) == ep_num_float:
                                        target_idx = idx
                                        break
                                
                                if target_idx != -1:
                                    selected = target_idx
                                    scroll_offset = max(0, selected - (max_display // 2))
                            except ValueError:
                                pass

                        except Exception:
                            pass
                        finally:
                            enter_raw_mode_after_input()
                        
                        self.clear()
                        live.start()
                        live.update(generate_renderable(), refresh=True)

    def batch_selection_menu(self, episodes):
        selected = 0
        scroll_offset = 0
        marked = set()

        def _episode_value(ep, idx):
            try:
                return float(ep.display_num)
            except (TypeError, ValueError):
                return float(idx + 1)

        def _find_episode_index(ep_input):
            ep_input = (ep_input or "").strip()
            if not ep_input:
                return -1

            try:
                target = float(ep_input)
                for idx, ep in enumerate(episodes):
                    if _episode_value(ep, idx) == target:
                        return idx
                return -1
            except ValueError:
                if ep_input.isdigit():
                    idx = int(ep_input) - 1
                    if 0 <= idx < len(episodes):
                        return idx
                return -1

        def _prompt_centered(title_text):
            prompt_panel = Panel(
                Text(title_text, style=f"bold {COLOR_SUBTITLE}", justify="center"),
                box=HEAVY,
                border_style=COLOR_BORDER,
            )

            self.console.print(Align.center(prompt_panel, vertical="middle", height=7))
            prompt_string = f" {Text('›', style=COLOR_PROMPT)} "
            pad_width = (self.console.width - 30) // 2
            padding = " " * max(0, pad_width)
            return Prompt.ask(f"{padding}{prompt_string}", console=self.console).strip()

        def _mark_episode_range(range_text):
            match = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)\s*$", range_text or "")
            if not match:
                return 0

            start_val = float(match.group(1))
            end_val = float(match.group(2))
            if start_val > end_val:
                start_val, end_val = end_val, start_val

            added = 0
            for idx, ep in enumerate(episodes):
                ep_val = _episode_value(ep, idx)
                if start_val <= ep_val <= end_val:
                    if idx not in marked:
                        added += 1
                    marked.add(idx)
            return added
        
        def generate_renderable():
            content = Text()
            max_display = max(6, self.console.height - 12)
            visible_episodes = episodes[scroll_offset:scroll_offset + max_display]
            
            for idx, ep in enumerate(visible_episodes):
                real_idx = idx + scroll_offset
                is_selected = (real_idx == selected)
                is_marked = (real_idx in marked)
                
                mark = "[●]" if is_marked else "[○]"
                
                ep_num_fmt = f"#{str(ep.display_num).zfill(2)}" if len(episodes) > 9 else f"#{ep.display_num}"
                if is_selected:
                    content.append(" ▶ ", style=f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    content.append(f"{mark} {ep_num_fmt}\n", style=f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    bolt_color = getattr(config_module, "COLOR_BOLT", COLOR_BOLT)
                    style = f"bold {bolt_color}" if is_marked else "white"
                    content.append(f"   {mark} {ep_num_fmt}\n", style=style)

            panel_content = Table.grid(expand=True)
            panel_content.add_column(justify="center")
            panel_content.add_row(content)
            panel_content.add_row(Text(f"Marked: {len(marked)} / {len(episodes)} episodes", style=f"bold {COLOR_SUBTITLE}", justify="center"))
            panel_content.add_row(Text(""))
            
            # Clean Keycaps Grid (3 columns x 2 rows)
            dock_grid = Table.grid(padding=(0, 3))
            dock_grid.add_column(justify="left")
            dock_grid.add_column(justify="left")
            dock_grid.add_column(justify="left")

            def format_batch_key(k, flabel, fg):
                t = Text()
                if k == "↵":
                    t.append("↵", style=f"bold {fg}")
                    t.append(f" {flabel}", style="white")
                else:
                    t.append("[", style=f"bold {COLOR_BORDER}")
                    t.append(k, style=f"bold {fg}")
                    t.append("]", style=f"bold {COLOR_BORDER}")
                    t.append(f" {flabel}", style="white")
                return t

            row1 = [
                format_batch_key("↵", "download", COLOR_TITLE),
                format_batch_key("space", "toggle", COLOR_TITLE),
                format_batch_key("r", "range", COLOR_TITLE),
            ]
            row2 = [
                format_batch_key("a", "select all", COLOR_TITLE),
                format_batch_key("n", "clear", COLOR_TITLE),
                format_batch_key("b", "back", "#ff79c6"),
            ]
            dock_grid.add_row(*row1)
            dock_grid.add_row(*row2)
            panel_content.add_row(Align.center(dock_grid))
            
            panel = Panel(
                panel_content,
                title=f"[bold {COLOR_TITLE}]⚡ Batch Download ({len(marked)} selected)[/bold {COLOR_TITLE}]",
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(1, 3),
                width=min(68, self.console.width - 4)
            )
            return Align.center(panel, vertical="middle", height=self.console.height)

        self.clear()
        
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    max_display = max(6, self.console.height - 12)
                    
                    if (key == 'UP' or key == 'k') and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(generate_renderable(), refresh=True)
                    elif (key == 'DOWN' or key == 'j') and selected < len(episodes) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(generate_renderable(), refresh=True)
                    elif key == ' ':
                        if selected in marked:
                            marked.remove(selected)
                        else:
                            marked.add(selected)
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'a' or key == 'A':
                        marked = set(range(len(episodes)))
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'n' or key == 'N':
                        marked.clear()
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'g' or key == 'G':
                        live.stop()
                        try:
                            restore_terminal_for_input()
                            ep_input = _prompt_centered("Jump to episode number:")
                            target_idx = _find_episode_index(ep_input)
                            if target_idx != -1:
                                selected = target_idx
                                scroll_offset = max(0, selected - (max_display // 2))
                        except Exception:
                            pass
                        finally:
                            enter_raw_mode_after_input()

                        self.clear()
                        live.start()
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'r' or key == 'R':
                        live.stop()
                        try:
                            restore_terminal_for_input()
                            range_text = _prompt_centered("Mark range (example: 1-24):")
                            _mark_episode_range(range_text)
                        except Exception:
                            pass
                        finally:
                            enter_raw_mode_after_input()

                        self.clear()
                        live.start()
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'ENTER':
                        return sorted(list(marked))
                    elif key == 'b' or key == 'ESC' or key == 'q':
                        return None

    def history_menu(self, history_items):
        selected = 0
        scroll_offset = 0
        max_display = max(4, min(10, self.console.height - 14))
        
        def generate_renderable():
            content = Text()
            visible_items = history_items[scroll_offset:scroll_offset + max_display]
            box_width = min(74, self.console.width - 4)
            inner_w = box_width - 8
            
            for idx, item in enumerate(visible_items):
                real_idx = idx + scroll_offset
                is_selected = (real_idx == selected)
                
                raw_title = item.get('title', 'Unknown')
                date_str = item.get('last_updated', '').split('T')[0]
                ep_str = f"[ Ep {item.get('episode', '?')} ]"
                date_b = f"[ {date_str} ]"
                
                avail_for_title = max(10, inner_w - len(ep_str) - len(date_b) - 8)
                disp_title = raw_title[:avail_for_title-3] + "..." if len(raw_title) > avail_for_title else raw_title
                pad = " " * max(1, inner_w - len(disp_title) - len(ep_str) - len(date_b) - 5)

                if is_selected:
                    row_text = Text()
                    row_text.append(" ▶ ")
                    row_text.append(disp_title)
                    row_text.append(pad)
                    row_text.append(f"{ep_str}  {date_b}")
                    row_text.stylize(f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    content.append_text(row_text)
                    content.append("\n")
                else:
                    content.append("   ", style="white")
                    content.append(disp_title, style="white")
                    content.append(pad)
                    content.append(ep_str, style=f"bold {COLOR_SUBTITLE}")
                    content.append("  ")
                    content.append(date_b, style=f"bold {COLOR_TITLE}")
                    content.append("\n")
            
            panel = Panel(
                content,
                title=f"[bold {COLOR_TITLE}]Watch History[/bold {COLOR_TITLE}]",
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(1, 2),
                width=box_width
            )

            # Header with Logo & Title Badge
            header_table = Table.grid(expand=False)
            header_table.add_column(justify="center")
            header_table.add_row(Align.center(self._get_torlink_ascii_logo()))
            header_table.add_row(Text(""))

            title_badge = Text()
            title_badge.append("[ ", style=f"bold {COLOR_BORDER}")
            title_badge.append(f"Continue Watching • {len(history_items)} items", style="bold white")
            title_badge.append(" ]", style=f"bold {COLOR_BORDER}")
            header_table.add_row(Align.center(title_badge))

            # Organized Keycaps Dock
            dock_grid = Table.grid(padding=(0, 3))
            dock_grid.add_column(justify="left")
            dock_grid.add_column(justify="left")

            def format_h_key(k, flabel, fg):
                t = Text()
                if k == "↵":
                    t.append("↵", style=f"bold {fg}")
                    t.append(f" {flabel}", style="white")
                else:
                    t.append("[", style=f"bold {COLOR_BORDER}")
                    t.append(k, style=f"bold {fg}")
                    t.append("]", style=f"bold {COLOR_BORDER}")
                    t.append(f" {flabel}", style="white")
                return t

            row1 = [
                format_h_key("↵", "resume", COLOR_TITLE),
                format_h_key("↑↓/jk", "navigate", COLOR_TITLE),
            ]
            row2 = [
                format_h_key("r", "remove", "#d97979"),
                format_h_key("b", "back", "#ff79c6"),
            ]
            dock_grid.add_row(*row1)
            dock_grid.add_row(*row2)

            root = Table.grid(expand=False)
            root.add_column(justify="center")
            root.add_row(Align.center(header_table))
            root.add_row(Text(""))
            root.add_row(Align.center(panel))
            root.add_row(Text(""))
            root.add_row(Align.center(dock_grid))

            return Align.center(root, vertical="middle", height=self.console.height)

        self.clear()
        
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    
                    if (key == 'UP' or key == 'k') and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(generate_renderable(), refresh=True)
                    elif (key == 'DOWN' or key == 'j') and selected < len(history_items) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'ENTER':
                        return (selected, 'resume')
                    elif key == 'r' or key == 'R':
                        return (selected, 'remove')
                    elif key == 'b' or key == 'ESC' or key == 'q':
                        return None

    def favorites_menu(self, fav_items):
        selected = 0
        scroll_offset = 0
        max_display = max(4, min(10, self.console.height - 14))
        
        def generate_renderable():
            content = Text()
            visible_items = fav_items[scroll_offset:scroll_offset + max_display]
            box_width = min(74, self.console.width - 4)
            inner_w = box_width - 8
            
            for idx, item in enumerate(visible_items):
                real_idx = idx + scroll_offset
                is_selected = (real_idx == selected)
                
                raw_title = item.get('title', 'Unknown')
                date_str = item.get('added_at', '').split('T')[0]
                date_b = f"[ {date_str} ]"
                
                avail_for_title = max(10, inner_w - len(date_b) - 8)
                disp_title = raw_title[:avail_for_title-3] + "..." if len(raw_title) > avail_for_title else raw_title
                pad = " " * max(1, inner_w - len(disp_title) - len(date_b) - 5)

                if is_selected:
                    row_text = Text()
                    row_text.append(" ▶ ")
                    row_text.append(disp_title)
                    row_text.append(pad)
                    row_text.append(date_b)
                    row_text.stylize(f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    content.append_text(row_text)
                    content.append("\n")
                else:
                    content.append("   ", style="white")
                    content.append(disp_title, style="white")
                    content.append(pad)
                    content.append(date_b, style=f"bold {COLOR_SUBTITLE}")
                    content.append("\n")
            
            panel = Panel(
                content,
                title=f"[bold {COLOR_TITLE}]Saved Favorites[/bold {COLOR_TITLE}]",
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(1, 2),
                width=box_width
            )

            # Header with Logo & Title Badge
            header_table = Table.grid(expand=False)
            header_table.add_column(justify="center")
            header_table.add_row(Align.center(self._get_torlink_ascii_logo()))
            header_table.add_row(Text(""))

            title_badge = Text()
            title_badge.append("[ ", style=f"bold {COLOR_BORDER}")
            title_badge.append(f"Favorites • {len(fav_items)} anime", style="bold white")
            title_badge.append(" ]", style=f"bold {COLOR_BORDER}")
            header_table.add_row(Align.center(title_badge))

            # Organized Keycaps Dock
            dock_grid = Table.grid(padding=(0, 3))
            dock_grid.add_column(justify="left")
            dock_grid.add_column(justify="left")

            def format_f_key(k, flabel, fg):
                t = Text()
                if k == "↵":
                    t.append("↵", style=f"bold {fg}")
                    t.append(f" {flabel}", style="white")
                else:
                    t.append("[", style=f"bold {COLOR_BORDER}")
                    t.append(k, style=f"bold {fg}")
                    t.append("]", style=f"bold {COLOR_BORDER}")
                    t.append(f" {flabel}", style="white")
                return t

            row1 = [
                format_f_key("↵", "watch", COLOR_TITLE),
                format_f_key("↑↓/jk", "navigate", COLOR_TITLE),
            ]
            row2 = [
                format_f_key("r", "remove", "#d97979"),
                format_f_key("b", "back", "#ff79c6"),
            ]
            dock_grid.add_row(*row1)
            dock_grid.add_row(*row2)

            root = Table.grid(expand=False)
            root.add_column(justify="center")
            root.add_row(Align.center(header_table))
            root.add_row(Text(""))
            root.add_row(Align.center(panel))
            root.add_row(Text(""))
            root.add_row(Align.center(dock_grid))

            return Align.center(root, vertical="middle", height=self.console.height)

        self.clear()
        
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    
                    if (key == 'UP' or key == 'k') and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(generate_renderable(), refresh=True)
                    elif (key == 'DOWN' or key == 'j') and selected < len(fav_items) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'ENTER':
                        return (selected, 'watch')
                    elif key == 'r' or key == 'R':
                        return (selected, 'remove')
                    elif key == 'b' or key == 'ESC' or key == 'q':
                        return None

    def settings_menu(self, settings_mgr):
        tabs = [
            ("General", [
                ("Provider", ["anime3rb", "anime_slayer", "animeify", "anidb"], "anime_provider"),
                ("Default Player", ["mpv", "vlc"], "player"),
                ("Color Theme", ["auto", "blue", "purple", "cyan", "rose", "sunset", "gold", "mint", "lavender", "pink", "coral", "teal", "magenta", "red", "green"], "theme"),
                ("Show Donation Link", [True, False], "show_donation"),
            ]),
            ("Playback", [
                ("Auto Next Episode", [True, False], "auto_next"),
                ("Skip Intro Offset", ["00:05", "00:00", "00:10", "00:15"], "skip_intro"),
                ("Streaming Quality", ["1080p", "720p", "480p"], "default_quality"),
            ]),
            ("Downloads", [
                ("Download Quality", ["1080p", "720p", "480p"], "default_download_quality"),
                ("Download Engine", ["internal", "aria2c", "idm", "auto"], "download_mode"),
                ("Download Directory", [], "download_directory"),
            ]),
            ("System", [
                ("Discord Rich Presence", [True, False], "discord_rpc"),
                ("Debug Logging", [False, True], "debug_logging"),
                ("Anonymous Telemetry", [False, True], "analytics"),
            ])
        ]
        
        cur_tab = 0
        selected_row = 0
        theme_changed = False
        rpc_changed = False
        provider_changed = False
        
        # Track initial values to highlight changes in a distinct color
        initial_values = {}
        for _, tab_options in tabs:
            for item in tab_options:
                key_name = item[2]
                initial_values[key_name] = settings_mgr.get(key_name)

        last_notification = ""
        last_notification_time = 0

        def format_provider_name(pid):
            if pid == "anime3rb":
                return "Anime3rb"
            elif pid == "anime_slayer":
                return "Anime Slayer"
            elif pid in ["animeify", "animefy"]:
                return "Animeify"
            elif pid in ["anidb", "ani-cli"]:
                return "AniDB (English)"
            return str(pid).title()

        def generate_renderable():
            tab_name, options = tabs[cur_tab]
            box_width = min(72, self.console.width - 4)
            
            c_title = getattr(config_module, 'COLOR_TITLE', COLOR_TITLE)
            c_border = getattr(config_module, 'COLOR_BORDER', COLOR_BORDER)
            c_sub = getattr(config_module, 'COLOR_SUBTITLE', COLOR_SUBTITLE)
            c_hl_fg = getattr(config_module, 'COLOR_HIGHLIGHT_FG', COLOR_HIGHLIGHT_FG)
            c_hl_bg = getattr(config_module, 'COLOR_HIGHLIGHT_BG', COLOR_HIGHLIGHT_BG)
            c_bolt = getattr(config_module, 'COLOR_BOLT', COLOR_BOLT)
            
            # Modern Horizontal Segmented Tabs Bar
            tabs_bar = Text()
            for idx, (tname, _) in enumerate(tabs):
                num_badge = f"{idx+1}"
                if idx == cur_tab:
                    tabs_bar.append(f" [{num_badge}] {tname} ", style=f"bold {c_hl_fg} on {c_hl_bg}")
                else:
                    tabs_bar.append(f" [{num_badge}] {tname} ", style=f"dim {c_sub}")
                if idx < len(tabs) - 1:
                    tabs_bar.append(" ")

            # Key-Value Options List Table
            list_table = Table.grid(expand=True, padding=(0, 2))
            list_table.add_column("label", justify="left")
            list_table.add_column("value", justify="right")

            for idx, item in enumerate(options):
                label, choices, key_name = item
                current_val = settings_mgr.get(key_name)
                is_selected = (idx == selected_row)
                is_modified = (current_val != initial_values.get(key_name))

                # Label part
                label_text = Text()
                if is_selected:
                    label_text.append("▌ ", style=f"bold {c_title}")
                    label_text.append(label, style=f"bold {c_title}")
                else:
                    label_text.append("  ", style="dim")
                    label_text.append(label, style="white")

                # Value part
                val_text = Text()
                if isinstance(current_val, bool):
                    if current_val:
                        v_style = "bold #ff79c6" if is_modified else f"bold {c_bolt}"
                        tag = "[● ON] *" if is_modified else "[● ON]"
                        val_text.append(tag, style=v_style)
                    else:
                        v_style = "bold #ff79c6" if is_modified else "dim #505a6c"
                        tag = "[○ OFF] *" if is_modified else "[○ OFF]"
                        val_text.append(tag, style=v_style)
                else:
                    if key_name == "anime_provider":
                        display_str = format_provider_name(current_val)
                    else:
                        display_str = str(current_val or "default")
                    
                    if is_modified:
                        val_text.append(f"⟨ {display_str} ⟩ *", style="bold #ff79c6")
                    else:
                        val_style = f"bold {c_title}" if is_selected else "bold white"
                        val_text.append(f"⟨ {display_str} ⟩", style=val_style)

                list_table.add_row(label_text, val_text)

            panel_content = Table.grid(expand=True)
            panel_content.add_column(justify="center")
            panel_content.add_row(Align.center(tabs_bar))
            panel_content.add_row(Text(""))
            panel_content.add_row(list_table)

            panel = Panel(
                panel_content,
                title=f"[bold {c_title}] ⚙ Settings & Preferences • {tab_name} [/bold {c_title}]",
                box=ROUNDED,
                border_style=c_border,
                padding=(1, 2),
                width=box_width
            )

            # Header with Logo
            header_table = Table.grid(expand=False)
            header_table.add_column(justify="center")
            header_table.add_row(Align.center(self._get_torlink_ascii_logo()))

            # Toast Notification Popup (if recently changed)
            toast_table = Table.grid(expand=False)
            toast_table.add_column(justify="center")
            if last_notification and (time.time() - last_notification_time < 2.5):
                toast_text = Text()
                toast_text.append(f" {last_notification} ", style=f"bold #1a1b26 on {c_bolt}")
                toast_table.add_row(Align.center(toast_text))
                toast_table.add_row(Text("")) # padding under toast!
            else:
                toast_table.add_row(Text(""))
                toast_table.add_row(Text(""))

            # Organized Keycaps Dock
            dock = Text()
            dock.append("[←/→] ", style=f"bold {c_title}")
            dock.append("Tabs   ", style="dim white")
            dock.append("[↑/↓] ", style=f"bold {c_title}")
            dock.append("Navigate   ", style="dim white")
            dock.append("[Space/↵] ", style=f"bold {c_title}")
            dock.append("Toggle   ", style="dim white")
            dock.append("[Esc/B] ", style="bold #ff79c6")
            dock.append("Save & Exit", style="dim white")

            root = Table.grid(expand=False)
            root.add_column(justify="center")
            root.add_row(Align.center(header_table))
            root.add_row(Text(""))
            root.add_row(Align.center(panel))
            root.add_row(Align.center(toast_table))
            root.add_row(Align.center(dock))

            return Align.center(root, vertical="middle", height=self.console.height)

        hide_cursor()
        self.clear()
        
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    _, options = tabs[cur_tab]
                    
                    if key in ['1', '2', '3', '4', '5']:
                        new_tab = int(key) - 1
                        if 0 <= new_tab < len(tabs):
                            cur_tab = new_tab
                            selected_row = 0
                            live.update(generate_renderable(), refresh=True)
                    elif key == 'TAB' or key == 'RIGHT' or key == 'l':
                        cur_tab = (cur_tab + 1) % len(tabs)
                        selected_row = 0
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'LEFT' or key == 'h':
                        cur_tab = (cur_tab - 1) % len(tabs)
                        selected_row = 0
                        live.update(generate_renderable(), refresh=True)
                    elif (key == 'UP' or key == 'k') and selected_row > 0:
                        selected_row -= 1
                        live.update(generate_renderable(), refresh=True)
                    elif (key == 'DOWN' or key == 'j') and selected_row < len(options) - 1:
                        selected_row += 1
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'ENTER' or key == ' ' or key == 'SPACE':
                        label, choices, key_name = options[selected_row]
                        current_val = settings_mgr.get(key_name)

                        if key_name == "download_directory":
                            live.stop()
                            try:
                                restore_terminal_for_input()
                                self.clear()
                                prompt_panel = Panel(
                                    Text("Set custom download path\n(absolute or relative)", style=f"bold {COLOR_SUBTITLE}", justify="center"),
                                    box=HEAVY,
                                    border_style=COLOR_BORDER,
                                    padding=(1, 3),
                                )
                                self.console.print(Align.center(prompt_panel, vertical="middle", height=7))

                                prompt_string = f" {Text('›', style=COLOR_PROMPT)} "
                                pad_width = (self.console.width - 30) // 2
                                padding = " " * max(0, pad_width)
                                new_path = Prompt.ask(
                                    f"{padding}{prompt_string}",
                                    console=self.console,
                                    default=str(current_val or "downloads")
                                ).strip()

                                settings_mgr.set("download_directory", new_path or "downloads")
                                last_notification = f"✔ Set Download Directory → {new_path or 'downloads'}"
                                last_notification_time = time.time()
                            except Exception:
                                pass
                            finally:
                                enter_raw_mode_after_input()
                                hide_cursor()

                            self.clear()
                            live.start()
                            live.update(generate_renderable(), refresh=True)
                            continue
                        
                        if choices:
                            try:
                                curr_idx = choices.index(current_val)
                                new_val = choices[(curr_idx + 1) % len(choices)]
                            except ValueError:
                                new_val = choices[0]
                                
                            settings_mgr.set(key_name, new_val)
                            
                            disp_new = format_provider_name(new_val) if key_name == "anime_provider" else ("ON" if new_val is True else ("OFF" if new_val is False else str(new_val)))
                            last_notification = f"✔ Set {label} → {disp_new}"
                            last_notification_time = time.time()
                            
                            if key_name == "anime_provider":
                                provider_changed = True
                            
                            if key_name == "debug_logging":
                                if new_val:
                                    logger.enable()
                                else:
                                    logger.disable()
                            
                            if key_name == "discord_rpc":
                                rpc_changed = True
                            
                            if key_name == "theme":
                                theme_changed = True
                                importlib.reload(config_module)
                                
                                # Universal In-Memory Theme Propagation
                                # This ensures any module (like app.py) that did `from .config import COLOR_X` 
                                # gets their local namespace updated instantly.
                                import sys
                                for mod_name, mod in list(sys.modules.items()):
                                    if mod and (mod_name.startswith('src.') or mod_name == '__main__'):
                                        for attr_name in dir(config_module):
                                            if attr_name.startswith('COLOR_') or attr_name in ['HEADER_ART', 'GOODBYE_ART']:
                                                if hasattr(mod, attr_name):
                                                    setattr(mod, attr_name, getattr(config_module, attr_name))
                                                    
                                self.theme = Theme({
                                    "panel.border": config_module.COLOR_BORDER,
                                    "prompt.prompt": config_module.COLOR_PROMPT,
                                    "prompt.default": config_module.COLOR_PRIMARY_TEXT,
                                    "title": config_module.COLOR_TITLE,
                                    "secondary": config_module.COLOR_SECONDARY_TEXT,
                                    "highlight": f"{config_module.COLOR_HIGHLIGHT_FG} on {config_module.COLOR_HIGHLIGHT_BG}",
                                    "error": config_module.COLOR_ERROR,
                                    "info": config_module.COLOR_PRIMARY_TEXT,
                                    "loading": config_module.COLOR_LOADING_SPINNER,
                                    "border": config_module.COLOR_BORDER,
                                    "dock.item": config_module.COLOR_TITLE,
                                    "dock.bracket": config_module.COLOR_SUBTITLE,
                                    "dock.badge": f"bold {config_module.COLOR_HIGHLIGHT_FG} on {config_module.COLOR_BORDER}",
                                })
                                self.console = Console(theme=self.theme)
                            
                            live.update(generate_renderable(), refresh=True)
                    elif key == 'b' or key == 'B' or key == 'ESC' or key == 'q':
                        live.stop()
                        hide_cursor()
                        
                        has_any_change = (
                            theme_changed or provider_changed or rpc_changed or
                            any(settings_mgr.get(k) != initial_values.get(k) for k in initial_values)
                        )
                        
                        if has_any_change:
                            # Dynamic colors for apply animation
                            c_title = getattr(config_module, 'COLOR_TITLE', COLOR_TITLE)
                            c_bolt = getattr(config_module, 'COLOR_BOLT', COLOR_BOLT)
                            bolt_palette = getattr(config_module, "COLOR_BOLT_GLOW", [c_bolt])
                            
                            # 1. Smooth Bouncing Bar Apply Animation
                            for i in range(8):
                                c = bolt_palette[i % len(bolt_palette)]
                                frame = BOUNCING_BAR_FRAMES[i % len(BOUNCING_BAR_FRAMES)]
                                
                                anim_text = Text()
                                anim_text.append(f"{frame} ", style=f"bold {c}")
                                anim_text.append("Applying & Saving Preferences...", style="bold white")
                                
                                panel = Panel(
                                    Align.center(anim_text, vertical="middle"),
                                    title=f"[bold {c_title}] ⚙ Settings [/bold {c_title}]",
                                    box=ROUNDED,
                                    border_style=c,
                                    padding=(1, 3),
                                    width=min(56, self.console.width - 4)
                                )
                                self.clear()
                                self.console.print(Align.center(panel, vertical="middle", height=self.console.height))
                                time.sleep(0.06)

                            # 2. Render Saved Changes Summary Panel
                            self.clear()
                            msg_lines = []
                            if provider_changed:
                                msg_lines.append(f"Provider: {format_provider_name(settings_mgr.get('anime_provider'))}")
                            if theme_changed:
                                msg_lines.append(f"Theme: {str(settings_mgr.get('theme') or 'Auto').capitalize()}")
                            if rpc_changed:
                                rpc_status = "Enabled" if settings_mgr.get("discord_rpc") else "Disabled"
                                msg_lines.append(f"Discord RPC: {rpc_status}")

                            for k, v0 in initial_values.items():
                                v1 = settings_mgr.get(k)
                                if v1 != v0 and k not in ["anime_provider", "theme", "discord_rpc"]:
                                    disp_val = "ON" if v1 is True else ("OFF" if v1 is False else str(v1))
                                    msg_lines.append(f"{k.replace('_', ' ').title()}: {disp_val}")

                            msg_text = Text()
                            msg_text.append("✔ Preferences Saved Successfully\n\n", style=f"bold {c_bolt}")
                            for line in msg_lines[:5]:
                                msg_text.append(f" • {line}\n", style="white")

                            panel = Panel(
                                Align.center(msg_text, vertical="middle"),
                                title=f"[bold {c_title}] ⚙ Saved [/bold {c_title}]",
                                box=ROUNDED,
                                border_style=c_bolt,
                                padding=(1, 3),
                                width=min(56, self.console.width - 4)
                            )
                            self.console.print(Align.center(panel, vertical="middle", height=self.console.height))
                            time.sleep(0.7)

                        hide_cursor()
                        self.clear()
                        return {"theme_changed": theme_changed, "rpc_changed": rpc_changed, "provider_changed": provider_changed}

    def quality_selection_menu(self, anime_title, episode_num, available_qualities, rpc_manager=None, anime_poster=None):
        if rpc_manager:
            rpc_manager.update_choosing_quality(anime_title, episode_num, anime_poster)
        
        selected = 0
        
        def generate_renderable():
            content = Text()
            max_name_len = max((cell_len(getattr(q, 'name', str(q))) for q in available_qualities), default=24)
            box_width = min(56, max(38, max_name_len + 12))
            inner_w = box_width - 6
            
            for idx, quality in enumerate(available_qualities):
                is_selected = (idx == selected)
                q_name = getattr(quality, 'name', str(quality))
                
                prefix = " ▸ " if is_selected else "   "
                line_str = f"{prefix}{q_name}"
                pad = " " * max(0, inner_w - len(line_str))
                
                if is_selected:
                    row_text = Text(line_str + pad)
                    row_text.stylize(f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    content.append_text(row_text)
                    content.append("\n")
                else:
                    content.append(f"{line_str}\n", style="bold white")
            
            panel = Panel(
                content,
                title=f"[bold {COLOR_TITLE}]Select Server / Quality[/bold {COLOR_TITLE}]", 
                box=HEAVY,
                padding=(1, 2),
                border_style=COLOR_BORDER,
                width=box_width
            )

            # Header with Logo & Title Badge
            header_table = Table.grid(expand=False)
            header_table.add_column(justify="center")
            header_table.add_row(Align.center(self._get_torlink_ascii_logo()))
            header_table.add_row(Text(""))

            title_badge = Text()
            title_badge.append("[ ", style=f"bold {COLOR_BORDER}")
            title_badge.append(f"{ar(anime_title)} • Ep {episode_num}", style="bold white")
            title_badge.append(" ]", style=f"bold {COLOR_BORDER}")
            header_table.add_row(Align.center(title_badge))

            # Clean Keycaps Dock
            dock = Text()
            items = [("↵", "watch", COLOR_TITLE), ("d", "download", COLOR_TITLE), ("b", "back", "#ff79c6")]
            for idx, (k, flabel, fg) in enumerate(items):
                if k == "↵":
                    dock.append("↵", style=f"bold {fg}")
                    dock.append(f" {flabel}", style="white")
                else:
                    dock.append("[", style=f"bold {COLOR_BORDER}")
                    dock.append(k, style=f"bold {fg}")
                    dock.append("]", style=f"bold {COLOR_BORDER}")
                    dock.append(f" {flabel}", style="white")
                if idx < len(items) - 1:
                    dock.append("   •   ", style=f"bold {COLOR_BORDER}")

            root = Table.grid(expand=False)
            root.add_column(justify="center")
            root.add_row(Align.center(header_table))
            root.add_row(Text(""))
            root.add_row(Align.center(panel))
            root.add_row(Text(""))
            root.add_row(Align.center(dock))

            return Align.center(root, vertical="middle", height=self.console.height)

        self.clear()
        
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    
                    if (key == 'UP' or key == 'k') and selected > 0:
                        selected -= 1
                        live.update(generate_renderable(), refresh=True)
                    elif (key == 'DOWN' or key == 'j') and selected < len(available_qualities) - 1:
                        selected += 1
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'ENTER':
                        return (selected, 'watch')
                    elif key == 'd' or key == 'D':
                        return (selected, 'download')
                    elif key == 'b' or key == 'ESC' or key == 'q':
                        return None

    def render_now_playing(self, anime_title: str, episode_info: str, quality_name: str = ""):
        self.clear()
        
        q_clean = ""
        if quality_name:
            m = re.search(r"\b(\d{3,4}p)\b", quality_name)
            q_clean = m.group(1) if m else quality_name

        header_table = Table.grid(expand=False)
        header_table.add_column(justify="center")
        header_table.add_row(Align.center(self._get_torlink_ascii_logo()))
        header_table.add_row(Text(""))

        title_badge = Text()
        title_badge.append("[ ", style=f"bold {COLOR_BORDER}")
        title_badge.append(f"{ar(anime_title)} • {episode_info}", style="bold white")
        if q_clean:
            title_badge.append(f" • {q_clean}", style=f"bold {COLOR_TITLE}")
        title_badge.append(" ]", style=f"bold {COLOR_BORDER}")
        header_table.add_row(Align.center(title_badge))

        body_text = Text()
        body_text.append("▶ Playing in MPV window\n", style="bold white")
        body_text.append("Close player window to return", style=f"bold {COLOR_SUBTITLE}")

        box_width = min(46, self.console.width - 4)
        panel = Panel(
            Align.center(body_text, vertical="middle"),
            title=f"[bold {COLOR_TITLE}]Now Playing[/bold {COLOR_TITLE}]",
            box=HEAVY,
            border_style=COLOR_BORDER,
            padding=(1, 2),
            width=box_width
        )

        root = Table.grid(expand=False)
        root.add_column(justify="center")
        root.add_row(Align.center(header_table))
        root.add_row(Text(""))
        root.add_row(Align.center(panel))

        self.console.print(Align.center(root, vertical="middle", height=self.console.height))

    def post_watch_menu(self, anime_title: str = "", episode_num: str = ""):
        options = ["Next Episode", "Previous Episode", "Replay", "Back to Episodes"]
        selected = 0
        
        def generate_renderable():
            content = Text()
            box_width = min(40, self.console.width - 4)
            inner_w = box_width - 6
            
            for idx, option in enumerate(options):
                is_selected = (idx == selected)
                prefix = " ▶ " if is_selected else "   "
                line_str = f"{prefix}{option}"
                pad = " " * max(0, inner_w - len(line_str))
                
                if is_selected:
                    row_text = Text(line_str + pad)
                    row_text.stylize(f"bold {COLOR_HIGHLIGHT_FG} on {COLOR_BORDER}")
                    content.append_text(row_text)
                    content.append("\n")
                else:
                    content.append(f"{line_str}\n", style="bold white")
            
            panel = Panel(
                content,
                title=f"[bold {COLOR_TITLE}]Select Action[/bold {COLOR_TITLE}]",
                box=HEAVY,
                padding=(1, 2),
                border_style=COLOR_BORDER,
                width=box_width
            )

            header_table = Table.grid(expand=False)
            header_table.add_column(justify="center")
            header_table.add_row(Align.center(self._get_torlink_ascii_logo()))
            header_table.add_row(Text(""))

            title_badge = Text()
            title_badge.append("[ ", style=f"bold {COLOR_BORDER}")
            if anime_title and episode_num:
                title_badge.append(f"{ar(anime_title)} • Ep {episode_num} Finished", style="bold white")
            elif episode_num:
                title_badge.append(f"Ep {episode_num} Finished", style="bold white")
            else:
                title_badge.append("Finished Watching", style="bold white")
            title_badge.append(" ]", style=f"bold {COLOR_BORDER}")
            header_table.add_row(Align.center(title_badge))

            # Clean Keycaps Dock
            dock = Text()
            dock_items = [("↵", "select", COLOR_TITLE), ("↑↓/jk", "navigate", COLOR_TITLE), ("b", "back", "#ff79c6")]
            for idx, (k, flabel, fg) in enumerate(dock_items):
                if k == "↵":
                    dock.append("↵", style=f"bold {fg}")
                    dock.append(f" {flabel}", style="white")
                else:
                    dock.append("[", style=f"bold {COLOR_BORDER}")
                    dock.append(k, style=f"bold {fg}")
                    dock.append("]", style=f"bold {COLOR_BORDER}")
                    dock.append(f" {flabel}", style="white")
                if idx < len(dock_items) - 1:
                    dock.append("   •   ", style=f"bold {COLOR_BORDER}")

            root = Table.grid(expand=False)
            root.add_column(justify="center")
            root.add_row(Align.center(header_table))
            root.add_row(Text(""))
            root.add_row(Align.center(panel))
            root.add_row(Text(""))
            root.add_row(Align.center(dock))

            return Align.center(root, vertical="middle", height=self.console.height)

        self.clear()
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    if (key == 'UP' or key == 'k') and selected > 0:
                        selected -= 1
                        live.update(generate_renderable(), refresh=True)
                    elif (key == 'DOWN' or key == 'j') and selected < len(options) - 1:
                        selected += 1
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'ENTER':
                        return options[selected]
                    elif key == 'q' or key == 'b' or key == 'ESC':
                        return "Back to Episodes"

    def show_credits(self):
        """Display credits and contributors."""
        from .version import __version__
        
        def generate_renderable():
            content = Text()
            
            content.append(f"ani-cli-arabic v{__version__}\n\n", style="bold " + COLOR_TITLE)
            
            content.append("Abdollah", style="bold white")
            content.append("  •  ", style=f"bold {COLOR_BORDER}")
            content.append("github.com/np4abdou1\n", style=f"bold {COLOR_SUBTITLE}")
            
            content.append("Anas Tourari", style="bold white")
            content.append("  •  ", style=f"bold {COLOR_BORDER}")
            content.append("github.com/Anas-Tou\n\n", style=f"bold {COLOR_SUBTITLE}")
            
            content.append("https://github.com/np4abdou1/ani-cli-arabic", style=f"bold {COLOR_TITLE}")
            
            box_width = min(60, self.console.width - 4)
            panel = Panel(
                Align.center(content, vertical="middle"),
                title=f"[bold {COLOR_TITLE}]Credits & Contributors[/bold {COLOR_TITLE}]",
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(1, 4),
                width=box_width
            )

            # Header with Logo & Title Badge
            header_table = Table.grid(expand=False)
            header_table.add_column(justify="center")
            header_table.add_row(Align.center(self._get_torlink_ascii_logo()))
            header_table.add_row(Text(""))

            title_badge = Text()
            title_badge.append("[ ", style=f"bold {COLOR_BORDER}")
            title_badge.append("Project Credits", style="bold white")
            title_badge.append(" ]", style=f"bold {COLOR_BORDER}")
            header_table.add_row(Align.center(title_badge))

            # Clean Keycaps Dock
            dock = Text()
            dock.append("↵ / any key", style=f"bold {COLOR_TITLE}")
            dock.append(" return", style="white")

            root = Table.grid(expand=False)
            root.add_column(justify="center")
            root.add_row(Align.center(header_table))
            root.add_row(Text(""))
            root.add_row(Align.center(panel))
            root.add_row(Text(""))
            root.add_row(Align.center(dock))
            
            return Align.center(root, vertical="middle", height=self.console.height)
        
        self.clear()
        
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True):
                while True:
                    key = get_key()
                    if key:
                        break