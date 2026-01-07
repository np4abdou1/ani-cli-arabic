import time
import threading
import importlib
import os
import sys
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
from rich.box import HEAVY
from rich.spinner import Spinner

from .config import (
    COLOR_BORDER, COLOR_PROMPT, COLOR_PRIMARY_TEXT, COLOR_TITLE,
    COLOR_SECONDARY_TEXT, COLOR_HIGHLIGHT_FG, COLOR_HIGHLIGHT_BG,
    COLOR_ERROR, COLOR_LOADING_SPINNER, COLOR_ASCII, HEADER_ART
)
from .utils import get_key, RawTerminal, restore_terminal_for_input, enter_raw_mode_after_input
from . import config as config_module

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

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.console.clear()

    def print(self, *args, **kwargs):
        self.console.print(*args, **kwargs)

    def get_header_renderable(self) -> Text:
        return Text(HEADER_ART, style=COLOR_ASCII)

    def render_message(self, title: str, message: str, style_name: str):
        self.clear()
        
        # Create styled message text
        message_text = Text()
        for line in message.split('\n'):
            if line.strip():
                message_text.append(line + "\n", style="info" if not line.startswith('•') else "secondary")
            else:
                message_text.append("\n")
        
        panel = Panel(
            Align.center(message_text, vertical="middle"),
            title=Text(title, style="title"),
            box=HEAVY,
            border_style="#FF6B6B" if style_name == "error" else COLOR_BORDER,
            padding=(2, 4),
            width=60
        )
        
        self.console.print(Align.center(panel, vertical="middle", height=self.console.height))
        Prompt.ask(f" {Text('Press ENTER to continue...', style='dim')} ", console=self.console)

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

        spinner = Spinner("dots", text=Text(f" {message}", style=COLOR_LOADING_SPINNER))
        loading_panel = Panel(
            Align.center(spinner, vertical="middle"),
            box=HEAVY,
            border_style=COLOR_BORDER,
            padding=(2, 4),
            title=Text("LOADING", style="title")
        )

        try:
            with Live(Align.center(loading_panel, vertical="middle", height=self.console.height), console=self.console, refresh_per_second=12, screen=True):
                while not thread_done.is_set():
                    time.sleep(0.05)
        except KeyboardInterrupt:
            thread_done.set()
            raise

        self.clear()

        if 'error' in result_container:
            raise result_container['error']
        
        return result_container.get('result')

    def anime_selection_menu(self, results, load_more_callback=None):
        selected = 0
        scroll_offset = 0
        is_loading_more = False
        has_more = True
        loading_dots = 0
        details_cache = {}
        results_lock = threading.Lock()  # Cache for anime details to avoid regeneration
        
        screen_height = self.console.height
        target_height = min(screen_height, 35)
        if target_height < 20:
            target_height = screen_height
        
        vertical_pad = (screen_height - target_height) // 6

        def create_layout():
            layout = Layout(name="root")
            
            if vertical_pad > 0:
                layout.split_column(
                    Layout(size=vertical_pad),
                    Layout(name="content", size=target_height),
                    Layout(size=vertical_pad)
                )
                children = list(layout["root"].children)
                children[0].update(Text(""))
                children[2].update(Text(""))
                content_area = layout["content"]
            else:
                content_area = layout

            content_area.split_column(
                Layout(name="header", size=11),
                Layout(name="body"),
                Layout(name="footer", size=3)
            )
            content_area["body"].split_row(
                Layout(name="left", ratio=1),
                Layout(name="right", ratio=1)
            )
            return layout

        header_renderable = self.get_header_renderable()
        layout = create_layout()
        content_layout = layout["content"] if vertical_pad > 0 else layout

        def generate_renderable():
            nonlocal loading_dots
            content_layout["header"].update(Align.center(header_renderable))
            
            # Show loading indicator in footer if loading more
            if is_loading_more:
                theme_fade = [COLOR_PROMPT, COLOR_TITLE, COLOR_SECONDARY_TEXT]
                base_text = " Loading more... "
                animated = Text(justify="center")
                for idx, ch in enumerate(base_text):
                    color_idx = (loading_dots + idx) % len(theme_fade)
                    animated.append(ch, style=theme_fade[color_idx])
                loading_dots += 1
                footer_render = Panel(animated, box=HEAVY, border_style=COLOR_BORDER)
            else:
                footer_text = "↑↓ Navigate | ENTER Select | b Back | q Quit"
                footer_render = Panel(Text(footer_text, justify="center", style="secondary"), box=HEAVY, border_style=COLOR_BORDER)
            content_layout["footer"].update(footer_render)
            
            max_display = target_height - 11 - 3 - 3
            left_content = Text()
            
            start = scroll_offset
            end = min(start + max_display, len(results))
            
            for idx in range(start, end):
                anime = results[idx]
                is_selected = idx == selected
                
                if is_selected:
                    left_content.append(f"▶ {anime.title_en}\n", style="highlight")
                else:
                    left_content.append(f"  {anime.title_en}\n", style="info")
            
            content_layout["left"].update(Panel(
                left_content,
                title=Text(f"Search Results: {len(results)}", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(0, 1)
            ))
            
            selected_anime = results[selected]
            
            # Use cached details if same anime is selected
            if selected not in details_cache:
                container = Table.grid(padding=1)
                container.add_column()
            else:
                container = details_cache[selected]
                content_layout["right"].update(Panel(
                    container, 
                    title=Text("Details", style="title"),
                    box=HEAVY,
                    border_style=COLOR_BORDER
                ))
                return layout
            
            container = Table.grid(padding=(0, 1))
            container.add_column()
            
            container.add_row(Text(selected_anime.title_en, style="title", justify="center"))
            if selected_anime.title_jp and selected_anime.title_jp not in ["N/A", "None", None, ""]:
                container.add_row(Text(selected_anime.title_jp, style="secondary", justify="center"))
            
            container.add_row(Text(" "))
            
            details_grid = Table.grid(padding=(0, 2), expand=True)
            details_grid.add_column(min_width=25)
            details_grid.add_column()
            
            stats_table = Table.grid(padding=(0, 1), expand=False)
            stats_table.add_column(style="secondary", no_wrap=True, min_width=12)
            stats_table.add_column(style="info", no_wrap=True)
            
            score_val = selected_anime.score
            if score_val in ["0", 0, "N/A", "None", None]:
                score_text = "Not found."
            else:
                score_text = f"⭐ {score_val}/10"
            
            rank_val = selected_anime.rank
            rank_text = "N/A" if rank_val in ["N/A", "None", None] else f"#{rank_val}"

            pop_val = selected_anime.popularity
            pop_text = "N/A" if pop_val in ["N/A", "None", None] else f"#{pop_val}"

            stats_table.add_row("Score:", Text(score_text, style="#FFA500"))
            stats_table.add_row("Rank:", Text(rank_text, style="title"))
            stats_table.add_row("Popularity:", Text(pop_text, style="title"))
            stats_table.add_row("Rating:", selected_anime.rating if selected_anime.rating not in ["N/A", "None", None, ""] else "Unknown")
            stats_table.add_row("Type:", selected_anime.type if selected_anime.type not in ["N/A", "None", None, ""] else "Unknown")
            stats_table.add_row("Episodes:", selected_anime.episodes if selected_anime.episodes not in ["N/A", "None", None, ""] else "Unknown")
            stats_table.add_row("Status:", selected_anime.status if selected_anime.status not in ["N/A", "None", None, ""] else "Unknown")
            
            # Add Studio field - always show with fallback
            studio_val = selected_anime.creators
            studio_display = "Unknown" if studio_val in ["N/A", "None", None, "", "Unknown"] else studio_val
            stats_table.add_row("Studio:", studio_display)

            # Add Trailer status
            trailer_val = selected_anime.trailer or selected_anime.yt_trailer
            if trailer_val and trailer_val not in ["N/A", "None", None, ""]:
                stats_table.add_row("Trailer:", Text("Found", style="bold green"))
            else:
                stats_table.add_row("Trailer:", Text("Not Found", style="dim"))
            
            # Add Season/Aired with fallback
            season_val = selected_anime.premiered
            if season_val and season_val not in ["N/A", "None", None, "", "0", "Unknown"]:
                stats_table.add_row("Season:", season_val)
            
            # Add Duration with fallback
            duration_val = selected_anime.duration
            if duration_val and duration_val not in ["N/A", "None", None, "", "0", "Unknown"]:
                # Handle duration format
                if "min" in duration_val.lower():
                    stats_table.add_row("Duration:", duration_val)
                else:
                    stats_table.add_row("Duration:", f"{duration_val} min/ep")
            
            text_container = Table.grid()
            text_container.add_column()
            text_container.add_row(Text("Genres", style="title", justify="center"))
            genres_text = selected_anime.genres if selected_anime.genres not in ["N/A", "None", None, ""] else "Unknown"
            text_container.add_row(Text(genres_text, style="secondary", justify="center"))
            
            details_grid.add_row(Align(stats_table, vertical="top"), text_container)
            container.add_row(details_grid)
            
            content_layout["right"].update(Panel(
                container, 
                title=Text("Details", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER
            ))
            
            return layout

        self.clear()
        
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    max_display = target_height - 11 - 3 - 3
                    needs_update = False
                    
                    if key == 'UP' and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        needs_update = True
                    elif key == 'DOWN' and selected < len(results) - 1:
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
                                            with results_lock:
                                                results.extend(new_results)
                                            live.update(generate_renderable(), refresh=True)
                                        else:
                                            has_more = False
                                    except Exception:
                                        has_more = False
                                    finally:
                                        is_loading_more = False
                                        live.update(generate_renderable(), refresh=True)
                                
                                thread = threading.Thread(target=load_in_background, daemon=True)
                                thread.start()
                    elif key == 'ENTER':
                        return selected
                    elif key == 'b':
                        return None
                    elif key == 'q' or key == 'ESC':
                        return -1
                    
                    if needs_update:
                        live.update(generate_renderable(), refresh=True)
                    # No sleep needed - get_key() already has built-in timeout

    @lru_cache(maxsize=50)
    def _generate_poster_ansi(self, url, max_height):
        """Generate ANSI art from poster URL with automatic LRU caching."""
        if not url:
            return Text("No poster available", style="secondary")
        
        try:
            # Download with timeout
            res = requests.get(url, timeout=5)
            img = Image.open(BytesIO(res.content)).convert("RGB")
            
            # Enhance for terminal display
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.8)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.15)
            
            # Calculate dimensions
            target_pixel_height = max_height * 2
            new_height = target_pixel_height
            new_width = int((img.width / img.height) * new_height * 2.0)
            
            # Ensure even dimensions
            if new_width % 2 != 0:
                new_width -= 1
            if new_height % 2 != 0:
                new_height -= 1
            
            # Use BILINEAR for speed (still good quality)
            img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)
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
                    
                    # Fast 2-color quantization using luminance
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
        target_height = min(screen_height, 25)

        def generate_renderable():
            max_display = target_height - 5
            content = Text()
            
            start = scroll_offset
            end = min(start + max_display, len(items))
            
            for idx in range(start, end):
                item = items[idx]
                is_selected = idx == selected
                
                if is_selected:
                    content.append(f"▶ {item}\n", style="highlight")
                else:
                    content.append(f"  {item}\n", style="info")
            
            panel = Panel(
                content,
                title=Text(title, style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(1, 2)
            )
            
            return Align.center(panel, vertical="middle", height=self.console.height)

        self.clear()
        
        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True) as live:
                while True:
                    key = get_key()
                    max_display = target_height - 5
                    
                    if key == 'UP' and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'DOWN' and selected < len(items) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'ENTER':
                        return items[selected]
                    elif key == 'q' or key == 'b':
                        return None

    def episode_selection_menu(self, anime_title, episodes, rpc_manager=None, anime_poster=None, last_watched_ep=None, is_favorite=False, anime_details=None):
        selected = 0
        scroll_offset = 0
        
        if rpc_manager:
            rpc_manager.update_selecting_episode(anime_title, anime_poster)

        screen_height = self.console.height
        target_height = min(screen_height, 35)
        if target_height < 15:
            target_height = screen_height
        
        vertical_pad = (screen_height - target_height) // 2
        poster_height = target_height - 8

        # Get poster from cache (already pre-generated during loading)
        poster_renderable = None
        poster_width = 30
        if anime_poster and poster_height > 0:
            poster_renderable = self._generate_poster_ansi(anime_poster, poster_height)
            if poster_renderable:
                try:
                    lines = poster_renderable.plain.split('\n')
                    if lines:
                        poster_width = max(len(line) for line in lines)
                except Exception:
                    pass

        def create_layout():
            layout = Layout(name="root")
            
            if vertical_pad > 0:
                layout.split_column(
                    Layout(size=vertical_pad),
                    Layout(name="content", size=target_height),
                    Layout(size=vertical_pad)
                )
                children = list(layout["root"].children)
                children[0].update(Text(""))
                children[2].update(Text(""))
                content_area = layout["content"]
            else:
                content_area = layout

            content_area.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
                Layout(name="footer", size=3)
            )
            
            poster_size = poster_width + 4 if poster_renderable else 20

            content_area["body"].split_row(
                Layout(name="left", ratio=1),
                Layout(name="details_panel", ratio=2),
                Layout(name="poster_panel", size=poster_size)
            )
            return layout

        layout = create_layout()
        content_layout = layout["content"] if vertical_pad > 0 else layout

        def generate_renderable():
            content_layout["header"].update(Panel(Text(anime_title, justify="center", style="title"), box=HEAVY, border_style=COLOR_BORDER))
            content_layout["footer"].update(Panel(Text("↑↓ Navigate | ENTER Select | g Jump | F Fav | M Batch | b Back", justify="center", style="secondary"), box=HEAVY, border_style=COLOR_BORDER))
            
            max_display = target_height - 3 - 3 - 2
            left_content = Text()
            
            start = scroll_offset
            end = min(start + max_display, len(episodes))
            
            for idx in range(start, end):
                ep = episodes[idx]
                is_selected = idx == selected
                
                type_text = str(ep.type).strip() if ep.type else ""
                if type_text and type_text.lower() != "episode":
                    ep_type_str = f" [{type_text}]"
                else:
                    ep_type_str = ""
                
                # Logic to check if this episode is the last watched
                is_last_watched = False
                if last_watched_ep is not None and str(ep.display_num) == str(last_watched_ep):
                    is_last_watched = True

                # Suffix and style setup
                suffix = ""
                if is_last_watched:
                    suffix = " 👁" # Eye icon to indicate watched
                
                if is_selected:
                    left_content.append(f"▶ {ep.display_num}{ep_type_str}{suffix}\n", style="highlight")
                else:
                    style = "bold green" if is_last_watched else "info"
                    left_content.append(f"  {ep.display_num}{ep_type_str}{suffix}\n", style=style)
            
            content_layout["left"].update(Panel(
                left_content,
                title=Text(f"Episodes: {len(episodes)}", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(0, 1)
            ))
            
            # Poster Panel
            if poster_renderable:
                content_layout["poster_panel"].update(Panel(
                    Align.center(poster_renderable, vertical="middle"),
                    title=Text("Poster", style="title"),
                    box=HEAVY,
                    border_style=COLOR_BORDER,
                    padding=(0, 0)
                ))
            else:
                content_layout["poster_panel"].update(Panel(
                    Align.center(Text("No Poster", style="dim"), vertical="middle"),
                    title=Text("Poster", style="title"),
                    box=HEAVY,
                    border_style=COLOR_BORDER
                ))

            # Show anime details in right panel
            fav_icon = "★" if is_favorite else "☆"
            
            if anime_details:
                details_container = Table.grid(expand=True)
                details_container.add_column()
                
                # Stats table
                stats_table = Table.grid(padding=(0, 2))
                stats_table.add_column(style="secondary", no_wrap=True, min_width=10)
                stats_table.add_column(style="info", no_wrap=True)
                
                score_val = anime_details.get('score')
                if score_val in ["0", 0, "N/A", "None", None]:
                    score_text = "Not found."
                else:
                    score_text = f"⭐ {score_val}/10"

                rank_val = anime_details.get('rank')
                rank_text = "N/A" if rank_val in ["N/A", "None", None] else f"#{rank_val}"
                
                pop_val = anime_details.get('popularity')
                pop_text = "N/A" if pop_val in ["N/A", "None", None] else f"#{pop_val}"

                stats_table.add_row("Score:", Text(score_text, style="#FFA500"))
                stats_table.add_row("Rank:", Text(rank_text, style="title"))
                stats_table.add_row("Popularity:", Text(pop_text, style="title"))
                stats_table.add_row("Rating:", anime_details.get('rating', 'N/A') if anime_details.get('rating') not in ["N/A", "None", None, ""] else "Unknown")
                stats_table.add_row("Type:", anime_details.get('type', 'N/A'))
                stats_table.add_row("Episodes:", str(anime_details.get('episodes', 'N/A')))
                stats_table.add_row("Status:", anime_details.get('status', 'N/A'))
                
                # Add Studio field
                studio_val = anime_details.get('studio')
                studio_display = "Unknown" if studio_val in ["N/A", "None", None, "", "Unknown"] else studio_val
                stats_table.add_row("Studio:", studio_display)

                # Add Trailer status
                trailer_val = anime_details.get('trailer') or anime_details.get('yt_trailer')
                if trailer_val and trailer_val not in ["N/A", "None", None, ""]:
                    stats_table.add_row("Trailer:", Text("Found (Press T)", style="bold green"))
                else:
                    stats_table.add_row("Trailer:", Text("Not Found", style="dim"))
                
                if last_watched_ep:
                    stats_table.add_row("Last Watched:", Text(f"Episode {last_watched_ep}", style="bold green"))
                stats_table.add_row("Favorite:", Text(fav_icon + (" Yes" if is_favorite else " No"), style="title"))
                
                details_container.add_row(stats_table)
                details_container.add_row(Text(""))
                details_container.add_row(Text("Genres", style="title", justify="center"))
                details_container.add_row(Text(anime_details.get('genres', 'N/A'), style="secondary", justify="center"))
                
                content_layout["details_panel"].update(Panel(
                    details_container,
                    title=Text(f"{fav_icon} Info", style="title"),
                    box=HEAVY,
                    border_style=COLOR_BORDER,
                    padding=(1, 4)
                ))
            else:
                # Fallback if no anime_details
                selected_ep = episodes[selected]
                right_content = Text(f"Episode {selected_ep.display_num}\n", style="title", justify="center")
                right_content.append("\n")

                if selected_ep.type and str(selected_ep.type).strip().lower() != "episode":
                    right_content.append(f"Type: {selected_ep.type}\n", style="info", justify="center")
                
                if last_watched_ep is not None and str(selected_ep.display_num) == str(last_watched_ep):
                    right_content.append(Text("\n[Last Watched]\n", style="bold green", justify="center"))
                
                right_content.append("\n")
                right_content.append(Text(f"{fav_icon}\n", style="title", justify="center"))
                right_content.append(Text("Favorite: " + ("Yes" if is_favorite else "No"), style="secondary", justify="center"))
                
                content_layout["details_panel"].update(Panel(
                    Align.center(right_content, vertical="middle"),
                    title=Text(f"{fav_icon} Info", style="title"),
                    box=HEAVY,
                    border_style=COLOR_BORDER
                ))
            return layout

        self.clear()

        with RawTerminal():
            with Live(generate_renderable(), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    max_display = target_height - 3 - 3 - 2
                    
                    if key == 'UP' and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'DOWN' and selected < len(episodes) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(generate_renderable(), refresh=True)
                    elif key == 'ENTER':
                        return selected
                    elif key == 'f' or key == 'F':
                        return 'toggle_fav'
                    elif key == 'm' or key == 'M':
                        return 'batch_mode'
                    elif key == 't' or key == 'T':
                        return 'trailer'
                    elif key == 'g':
                        live.stop()
                        try:
                            # Restore terminal for normal input
                            restore_terminal_for_input()
                            
                            prompt_panel = Panel(
                                Text("Jump to episode number:", style="info", justify="center"), 
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
                                else:
                                    self.console.print(Text(f"Episode {ep_input} not found.", style="error"))
                                    input("Press Enter to continue...")
                            except ValueError:
                                self.console.print(Text("Invalid number.", style="error"))
                                input("Press Enter to continue...")

                        except Exception:
                            pass
                        finally:
                            # Re-enter raw mode for key handling
                            enter_raw_mode_after_input()
                        
                        self.clear()
                        live.start()
                        live.update(generate_renderable(), refresh=True)
                
                    elif key == 'b':
                        return None
                    elif key == 'q' or key == 'ESC':
                        return -1
                    # No sleep needed - get_key() already has built-in timeout

    def batch_selection_menu(self, episodes):
        selected = 0
        scroll_offset = 0
        marked = set()
        
        def generate_renderable():
            content = Text()
            max_display = self.console.height - 10
            visible_episodes = episodes[scroll_offset:scroll_offset + max_display]
            
            for idx, ep in enumerate(visible_episodes):
                real_idx = idx + scroll_offset
                is_selected = real_idx == selected
                is_marked = real_idx in marked
                
                prefix = "▶" if is_selected else " "
                mark = "[x]" if is_marked else "[ ]"
                style = "highlight" if is_selected else "info"
                if is_marked and not is_selected:
                    style = "secondary"
                
                content.append(f"{prefix} {mark} Episode {ep.display_num}\n", style=style)
            
            return Panel(
                Align.center(content, vertical="middle"),
                title=Text(f"Batch Download ({len(marked)} selected)", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                subtitle=Text("SPACE Toggle | A All | N None | ENTER Download | B Back", style="secondary")
            )

        self.clear()
        
        with RawTerminal():
            with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    max_display = self.console.height - 10
                    
                    if key == 'UP' and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'DOWN' and selected < len(episodes) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == ' ':
                        if selected in marked:
                            marked.remove(selected)
                        else:
                            marked.add(selected)
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'a' or key == 'A':
                        marked = set(range(len(episodes)))
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'n' or key == 'N':
                        marked.clear()
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'ENTER':
                        return sorted(list(marked))
                    elif key == 'b' or key == 'ESC':
                        return None
                    # No sleep needed - get_key() already has built-in timeout

    def history_menu(self, history_items):
        selected = 0
        scroll_offset = 0
        
        def generate_renderable():
            table = Table(box=None, show_header=False, padding=(0, 1), expand=True)
            table.add_column("Title", style="info")
            table.add_column("Last Ep", style="secondary", justify="right", width=15)
            table.add_column("Date", style="secondary", justify="right", width=20)
            
            max_display = self.console.height - 10
            visible_items = history_items[scroll_offset:scroll_offset + max_display]
            
            for idx, item in enumerate(visible_items):
                real_idx = idx + scroll_offset
                is_selected = real_idx == selected
                
                title = item['title'][:50] + "..." if len(item['title']) > 50 else item['title']
                date_str = item.get('last_updated', '').split('T')[0]
                
                if is_selected:
                    table.add_row(
                        Text(f"▶ {title}", style="highlight"),
                        Text(f"Ep {item.get('episode', '?')}", style="highlight"),
                        Text(date_str, style="highlight")
                    )
                else:
                    table.add_row(
                        f"  {title}",
                        f"Ep {item.get('episode', '?')}",
                        date_str
                    )
            
            return Panel(
                table,
                title=Text(f"Continue Watching ({len(history_items)})", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                subtitle=Text("ENTER Resume | B Back", style="secondary")
            )

        self.clear()
        
        with RawTerminal():
            with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    max_display = self.console.height - 10
                    
                    if key == 'UP' and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'DOWN' and selected < len(history_items) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'ENTER':
                        return selected
                    elif key == 'b' or key == 'ESC':
                        return None
                    # No sleep needed - get_key() already has built-in timeout

    def favorites_menu(self, fav_items):
        selected = 0
        scroll_offset = 0
        
        def generate_renderable():
            table = Table(box=None, show_header=False, padding=(0, 1), expand=True)
            table.add_column("Title", style="info")
            table.add_column("Added", style="secondary", justify="right", width=20)
            
            max_display = self.console.height - 10
            visible_items = fav_items[scroll_offset:scroll_offset + max_display]
            
            for idx, item in enumerate(visible_items):
                real_idx = idx + scroll_offset
                is_selected = real_idx == selected
                
                title = item['title'][:60] + "..." if len(item['title']) > 60 else item['title']
                date_str = item.get('added_at', '').split('T')[0]
                
                if is_selected:
                    table.add_row(
                        Text(f"▶ {title}", style="highlight"),
                        Text(date_str, style="highlight")
                    )
                else:
                    table.add_row(
                        f"  {title}",
                        date_str
                    )
            
            return Panel(
                table,
                title=Text(f"Favorites ({len(fav_items)})", style="title"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                subtitle=Text("ENTER Watch | R Remove | B Back", style="secondary")
            )

        self.clear()
        
        with RawTerminal():
            with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    max_display = self.console.height - 10
                    
                    if key == 'UP' and selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset = selected
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'DOWN' and selected < len(fav_items) - 1:
                        selected += 1
                        if selected >= scroll_offset + max_display:
                            scroll_offset = selected - max_display + 1
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'ENTER':
                        return (selected, 'watch')
                    elif key == 'r' or key == 'R':
                        return (selected, 'remove')
                    elif key == 'b' or key == 'ESC':
                        return None
                    # No sleep needed - get_key() already has built-in timeout

    def settings_menu(self, settings_mgr):
        options = [
            ("Default Quality", ["1080p", "720p", "480p"], "default_quality"),
            ("Player", ["mpv", "vlc"], "player"),
            ("Auto Next Episode", [True, False], "auto_next"),
            ("Discord Rich Presence", [True, False], "discord_rpc"),
            ("Analytics", [True, False], "analytics"),
            ("Theme", ["blue", "red", "green", "purple", "cyan", "yellow", "pink", "orange", "teal", "magenta", "lime", "coral", "lavender", "gold", "mint", "rose", "sunset"], "theme")
        ]
        selected = 0
        theme_changed = False  # Track if theme was changed
        rpc_changed = False    # Track if Discord RPC was changed
        
        def generate_renderable():
            content = Text()
            
            for idx, (label, choices, key) in enumerate(options):
                current_val = settings_mgr.get(key)
                is_selected = idx == selected
                
                prefix = "▶" if is_selected else " "
                style = "highlight" if is_selected else "info"
                
                val_str = str(current_val)
                if isinstance(current_val, bool):
                    val_str = "Enabled" if current_val else "Disabled"
                
                content.append(f"{prefix} {label}: {val_str}\n", style=style)
            
            return Panel(
                Align.center(content, vertical="middle"),
                title=Text("Settings", style="title"),
                box=HEAVY,
                padding=(2, 4),
                border_style=config_module.COLOR_BORDER,
                subtitle=Text("ENTER Toggle | B Back", style="secondary")
            )

        self.clear()
        
        with RawTerminal():
            with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    
                    if key == 'UP' and selected > 0:
                        selected -= 1
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'DOWN' and selected < len(options) - 1:
                        selected += 1
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'ENTER':
                        label, choices, key_name = options[selected]
                        current_val = settings_mgr.get(key_name)
                        
                        # Cycle through choices
                        try:
                            curr_idx = choices.index(current_val)
                            new_val = choices[(curr_idx + 1) % len(choices)]
                        except ValueError:
                            new_val = choices[0]
                            
                        settings_mgr.set(key_name, new_val)
                        
                        # Track if Discord RPC was changed
                        if key_name == "discord_rpc":
                            rpc_changed = True
                        
                        # Reload colors if theme changed and apply immediately
                        if key_name == "theme":
                            theme_changed = True  # Mark that theme was changed
                            importlib.reload(config_module)
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
                            })
                            self.console = Console(theme=self.theme)
                        
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'b' or key == 'B' or key == 'ESC':
                        # Exit the Live context first
                        live.stop()
                        
                        # If theme was changed, exit app to apply globally
                        if theme_changed:
                            self.console.clear()
                            message = Text()
                            message.append("Theme changed! Exiting application...\n\n", style=COLOR_TITLE)
                            message.append("Please run the application again to apply the new theme.", style="secondary")
                            panel = Panel(
                                Align.center(message, vertical="middle"),
                                box=HEAVY,
                                border_style=COLOR_BORDER,
                                padding=(2, 4)
                            )
                            self.console.print(Align.center(panel, vertical="middle", height=self.console.height))
                            time.sleep(2)
                            sys.exit(0)
                        # If Discord RPC was changed, notify user
                        if rpc_changed:
                            self.console.clear()
                            message = Text()
                            message.append("Discord Rich Presence setting changed!\n\n", style=COLOR_TITLE)
                            message.append("Please restart the application for changes to take effect.", style="secondary")
                            panel = Panel(
                                Align.center(message, vertical="middle"),
                                box=HEAVY,
                                border_style=COLOR_BORDER,
                                padding=(2, 4)
                            )
                            self.console.print(Align.center(panel, vertical="middle", height=self.console.height))
                            time.sleep(2)
                        
                        # Clear the screen before returning
                        self.clear()
                        return
                    # No sleep needed - get_key() already has built-in timeout

    def quality_selection_menu(self, anime_title, episode_num, available_qualities, rpc_manager=None, anime_poster=None):
        if rpc_manager:
            rpc_manager.update_choosing_quality(anime_title, episode_num, anime_poster)
        
        selected = 0
        
        def generate_renderable():
            content = Text()
            
            for idx, quality in enumerate(available_qualities):
                is_selected = idx == selected
                
                if is_selected:
                    content.append(f"▶ {quality.name}\n", style="highlight")
                else:
                    content.append(f"  {quality.name}\n", style=quality.style)
            
            return Panel(
                content,
                title=Text(f"Episode {episode_num} - Select Quality", style="title"), 
                box=HEAVY,
                padding=(2, 4),
                border_style=COLOR_BORDER,
                subtitle=Text("ENTER Watch | D Download | b Back", style="secondary")
            )

        self.clear()
        
        with RawTerminal():
            with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    
                    if key == 'UP' and selected > 0:
                        selected -= 1
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'DOWN' and selected < len(available_qualities) - 1:
                        selected += 1
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'ENTER':
                        return (selected, 'watch')
                    elif key == 'd' or key == 'D':
                        return (selected, 'download')
                    elif key == 'b':
                        return None
                    elif key == 'q' or key == 'ESC':
                        return -1
                    # No sleep needed - get_key() already has built-in timeout

    def post_watch_menu(self):
        options = ["Next Episode", "Previous Episode", "Replay", "Back to List"]
        selected = 0
        
        def generate_renderable():
            content = Text()
            for idx, option in enumerate(options):
                if idx == selected:
                    content.append(f"▶ {option}\n", style="highlight")
                else:
                    content.append(f"  {option}\n", style="info")
            
            return Panel(
                Align.center(content, vertical="middle"),
                title=Text("Finished Watching", style="title"),
                box=HEAVY,
                padding=(1, 4),
                border_style=COLOR_BORDER,
                subtitle=Text("Select Next Action", style="secondary")
            )

        self.clear()
        with RawTerminal():
            with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True, refresh_per_second=10) as live:
                while True:
                    key = get_key()
                    if key == 'UP' and selected > 0:
                        selected -= 1
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'DOWN' and selected < len(options) - 1:
                        selected += 1
                        live.update(Align.center(generate_renderable(), vertical="middle", height=self.console.height), refresh=True)
                    elif key == 'ENTER':
                        return options[selected]
                    elif key == 'q' or key == 'b' or key == 'ESC':
                        return "Back to List"
                    # No sleep needed - get_key() already has built-in timeout

    def show_credits(self):
        """Display credits and contributors."""
        from .version import __version__
        
        def generate_renderable():
            content = Text()
            
            content.append(f"ani-cli-arabic v{__version__}\n\n", style="bold " + COLOR_TITLE)
            
            content.append("Abdollah", style="bold")
            content.append(" • ", style="dim")
            content.append("github.com/np4abdou1\n", style=COLOR_PROMPT)
            
            content.append("Anas Tourari", style="bold")
            content.append(" • ", style="dim")
            content.append("github.com/Anas-Tou\n\n", style=COLOR_PROMPT)
            
            content.append("github.com/np4abdou1/ani-cli-arabic", style="dim")
            
            panel = Panel(
                Align.center(content, vertical="middle"),
                title=Text("CREDITS", style="bold " + COLOR_TITLE),
                subtitle=Text("press any key to go back", style="dim"),
                box=HEAVY,
                border_style=COLOR_BORDER,
                padding=(2, 4),
                width=50
            )
            
            return panel
        
        self.clear()
        
        with RawTerminal():
            with Live(Align.center(generate_renderable(), vertical="middle", height=self.console.height), console=self.console, auto_refresh=False, screen=True):
                while True:
                    key = get_key()
                    if key:
                        break