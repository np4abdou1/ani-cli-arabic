import sys
import atexit
import re
from pathlib import Path
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.box import HEAVY

from .config import COLOR_PROMPT, COLOR_BORDER
from .ui import UIManager
from .api import AnimeAPI, get_trailers_base
from .monitoring import monitor
from .player import PlayerManager
from .discord_rpc import DiscordRPCManager
from .models import QualityOption
from .utils import download_file, flush_stdin
from .history import HistoryManager
from .settings import SettingsManager
from .favorites import FavoritesManager
from .updater import check_for_updates, get_version_status
from .deps import ensure_dependencies
from .cli import run_simple_cli
from .config import GOODBYE_ART
import shutil
import argparse

class AniCliArApp:
    def __init__(self):
        self.ui = UIManager()
        self.api = AnimeAPI()
        self.rpc = DiscordRPCManager()
        self.settings = SettingsManager()
        self.player = PlayerManager(rpc_manager=self.rpc, console=self.ui.console)
        self.history = HistoryManager()
        self.favorites = FavoritesManager()
        self.version_info = None
        self.current_mode = "tui"
        self.force_cli = False

    def run(self):
        # Argument parsing
        parser = argparse.ArgumentParser(
            description="ani-cli-arabic: A CLI tool to browse and watch anime in Arabic.",
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument('-i', '--interactive', action='store_true', help="Force minimal interactive CLI mode")
        parser.add_argument('-v', '--version', action='store_true', help="Show version information")
        parser.add_argument('query', nargs='*', help="Anime name to search for")
        
        args = parser.parse_args()
        
        if args.version:
            from .version import __version__
            print(f"ani-cli-arabic v{__version__}")
            sys.exit(0)
            
        self.force_cli = args.interactive
        initial_query = " ".join(args.query) if args.query else None

        if not ensure_dependencies():
            print("\n[!] Cannot start without required dependencies.")
            input("Press ENTER to exit...")
            sys.exit(1)
        
        atexit.register(self.cleanup)
        
        import threading
        rpc_connected = {'status': None}
        
        if self.settings.get('discord_rpc'):
            def connect_rpc():
                rpc_connected['status'] = self.rpc.connect()
            threading.Thread(target=connect_rpc, daemon=True).start()
        
        threading.Thread(target=lambda: monitor.track_app_start(), daemon=True).start()
        
        def check_updates_bg():
            try:
                check_for_updates(auto_update=True)
            except Exception:
                pass
        threading.Thread(target=check_updates_bg, daemon=True).start()
        
        def check_version_bg():
            try:
                self.version_info = get_version_status()
            except Exception:
                pass
        threading.Thread(target=check_version_bg, daemon=True).start()
        
        self.rpc_status = rpc_connected

        try:
            self.unified_loop(initial_query)
        except KeyboardInterrupt:
            self.handle_exit()
        except Exception as e:
            self.handle_error(e)
        finally:
            self.cleanup()

    def unified_loop(self, query=None):
        while True:
            is_narrow = shutil.get_terminal_size().columns < 80
            
            if self.force_cli or is_narrow:
                self.current_mode = "cli"
                result = self.run_cli_mode(query)
                query = None # Clear query after first run
                if result == "SWITCH_TO_TUI":
                    if self.force_cli:
                         pass
                    continue
                break
            else:
                self.current_mode = "tui"
                result = self.run_tui_mode(query)
                query = None
                if result == "SWITCH_TO_CLI":
                    continue
                break

    def run_cli_mode(self, query=None):
        deps = {
            'api': self.api,
            'player': self.player,
            'history': self.history,
            'settings': self.settings,
            'rpc': self.rpc
        }
        return run_simple_cli(query, deps=deps)

    def run_tui_mode(self, query=None):
        while True:
            if '-i' not in sys.argv and shutil.get_terminal_size().columns < 80:
                return "SWITCH_TO_CLI"

            self.ui.clear()
            
            vertical_space = self.ui.console.height - 14
            top_padding = (vertical_space // 2) - 2
            
            if top_padding > 0:
                self.ui.print(Text("\n" * top_padding))

            self.ui.print(Align.center(self.ui.get_header_renderable()))
            self.ui.print()
            
            if self.settings.get('discord_rpc'):
                if hasattr(self, 'rpc_status'):
                    if self.rpc_status['status'] is True:
                        self.ui.print(Align.center(Text.from_markup("Discord Rich Presence ✅", style="secondary")))
                    elif self.rpc_status['status'] is None:
                        self.ui.print(Align.center(Text.from_markup("Discord Rich Presence [dim](connecting...)[/dim]", style="dim")))
                    else:
                        self.ui.print(Align.center(Text.from_markup("Discord Rich Presence [dim](enabled, not connected)[/dim]", style="dim")))
            else:
                self.ui.print(Align.center(Text.from_markup("Discord Rich Presence [dim](disabled)[/dim]", style="dim")))
            self.ui.print()
            
            keybinds_panel = Panel(
                Text("S: Search | T: Trending | P: Popular | G: Genres | D: Studios | L: History | F: Favorites | C: Settings | Q: Quit", style="info", justify="center"),
                box=HEAVY,
                border_style=COLOR_BORDER
            )
            self.ui.print(Align.center(keybinds_panel))
            self.ui.print()
            
            prompt_string = f" {Text('›', style=COLOR_PROMPT)} "
            pad_width = (self.ui.console.width - 30) // 2
            padding = " " * max(0, pad_width)
            
            if self.version_info and self.version_info.get('is_outdated'):
                status_text = f"Dev: v{self.version_info['current']} → Latest: v{self.version_info['latest_pip']} (update available)"
                self.ui.print(Align.center(Text(status_text, style="dim")))
                self.ui.print()

            flush_stdin()
            
            query = Prompt.ask(f"{padding}{prompt_string}", console=self.ui.console).strip().lower()
            
            if query in ['q', 'quit', 'exit']:
                break
            
            results = []
            
            if query == 't':
                self.rpc.update_trending()
                results = self.ui.run_with_loading(
                    "Fetching trending anime...",
                    self.api.get_trending_anime,
                    0,
                    15
                )
                if results:
                    def load_more_trending(current_count):
                        return self.api.get_trending_anime(current_count, 15)
                    self.handle_anime_selection_with_lazy_load(results, load_more_trending)
                    continue
            elif query == 'p':
                self.rpc.update_popular()
                results = self.ui.run_with_loading(
                    "Fetching popular anime...",
                    self.api.get_top_rated_anime,
                    0,
                    15
                )
                if results:
                    def load_more_popular(current_count):
                        return self.api.get_top_rated_anime(current_count, 15)
                    self.handle_anime_selection_with_lazy_load(results, load_more_popular)
                    continue
            elif query == 'g':
                self.rpc.update_genres()
                self.handle_genres()
                continue
            elif query == 'd':
                self.rpc.update_studios()
                self.handle_studios()
                continue
            elif query == 's':
                 term = Prompt.ask(f"{padding} Enter Search Term: ", console=self.ui.console).strip()
                 if term:
                    self.rpc.update_searching()
                    results = self.ui.run_with_loading("Searching...", self.api.search_anime, term)
            elif query == 'l':
                self.rpc.update_history()
                self.handle_history()
                continue
            elif query == 'f':
                self.rpc.update_favorites()
                self.handle_favorites()
                continue
            elif query == 'c':
                self.rpc.update_settings()
                self.ui.settings_menu(self.settings)
                continue
            elif query == 'a':
                self.ui.show_credits()
                continue
            elif query:
                self.rpc.update_searching()
                results = self.ui.run_with_loading("Searching...", self.api.search_anime, query)
            else:
                continue
            
            if not results:
                self.ui.render_message(
                    "✗ No Anime Found", 
                    f"No anime matching '{query}' was found.\n\nTry:\n• Checking spelling\n• Using English name\n• Using alternative titles", 
                    "error"
                )
                continue
            
            self.handle_anime_selection(results)

    def handle_anime_selection_with_lazy_load(self, results, load_more_callback):
        while True:
            anime_idx = self.ui.anime_selection_menu(results, load_more_callback=load_more_callback)
            
            if anime_idx == -1:
                sys.exit(0)
            if anime_idx is None:
                return
            
            selected_anime = results[anime_idx]

            self.rpc.update_viewing_anime(selected_anime.title_en, selected_anime.thumbnail)
            
            def load_episodes_and_poster():
                eps = self.api.get_episodes(selected_anime.id)
                if selected_anime.thumbnail:
                    screen_height = self.ui.console.height
                    target_height = min(screen_height, 35)
                    poster_height = target_height - 8
                    if poster_height > 0:
                        self.ui._generate_poster_ansi(selected_anime.thumbnail, poster_height)
                return eps
            
            episodes = self.ui.run_with_loading(
                "Loading episodes & poster...",
                load_episodes_and_poster
            )
            
            if not episodes:
                self.ui.render_message(
                    "✗ No Episodes",
                    f"No episodes found for '{selected_anime.title_en}'.",
                    "error"
                )
                continue
            
            self.handle_episode_selection(selected_anime, episodes)

    def handle_genres(self):
        genres = [
            "Action", "Adventure", "Comedy", "Drama", "Fantasy", 
            "Horror", "Mystery", "Romance", "Sci-Fi", "Slice of Life", 
            "Sports", "Supernatural", "Thriller", "Isekai", "School"
        ]
        
        selected_genre = self.ui.selection_menu(genres, title="Select Genre")
        if selected_genre:
            results = self.ui.run_with_loading(
                f"Fetching {selected_genre} anime...",
                self.api.get_anime_list,
                "GENRE",
                selected_genre,
                "SERIES",
                0,
                15
            )
            if results:
                def load_more_genre(current_count):
                    return self.api.get_anime_list("GENRE", selected_genre, "SERIES", current_count, 15)
                self.handle_anime_selection_with_lazy_load(results, load_more_genre)
            else:
                self.ui.render_message("Info", f"No anime found for genre: {selected_genre}", "info")

    def handle_studios(self):
        studios = [
            "Toei Animation", "Sunrise", "Madhouse", "Production I.G", "J.C.Staff", 
            "TMS Entertainment", "Studio Pierrot", "Studio Deen", "A-1 Pictures", 
            "Bones", "Kyoto Animation", "MAPPA", "Wit Studio", "ufotable", 
            "White Fox", "David Production", "Shaft", "Trigger", "CloverWorks", 
            "Lerche", "P.A. Works", "CoMix Wave Films", "Gainax", "Tatsunoko Production"
        ]
        studios.sort()
        
        selected_studio = self.ui.selection_menu(studios, title="Select Studio")
        if selected_studio:
            results = self.ui.run_with_loading(
                f"Fetching {selected_studio} anime...",
                self.api.get_anime_list,
                "STUDIOS",
                selected_studio,
                "SERIES",
                0,
                15
            )
            if results:
                def load_more_studio(current_count):
                    return self.api.get_anime_list("STUDIOS", selected_studio, "SERIES", current_count, 15)
                self.handle_anime_selection_with_lazy_load(results, load_more_studio)
            else:
                self.ui.render_message("Info", f"No anime found for studio: {selected_studio}", "info")

    def handle_history(self):
        history_items = self.history.get_history()
        if not history_items:
            self.ui.render_message("Info", "No history found.", "info")
            return

        while True:
            selected_idx = self.ui.history_menu(history_items)
            if selected_idx is None:
                break
            
            item = history_items[selected_idx]
            # Resume directly without nested loading screen
            self.resume_anime(item)
            # Refresh history after watching
            history_items = self.history.get_history()

    def resume_anime(self, history_item):
        # We need to fetch anime details first
        results = self.ui.run_with_loading("Resuming...", self.api.search_anime, history_item['title'])
        if not results:
            self.ui.render_message("Error", "Could not find anime details.", "error")
            return

        # Find the matching anime
        selected_anime = None
        for res in results:
            if str(res.id) == str(history_item['anime_id']):
                selected_anime = res
                break
        
        if not selected_anime:
            selected_anime = results[0] # Fallback

        self.rpc.update_viewing_anime(selected_anime.title_en, selected_anime.thumbnail)
        episodes = self.api.get_episodes(selected_anime.id)
        
        if episodes:
            self.handle_episode_selection(selected_anime, episodes)

    def handle_favorites(self):
        while True:
            fav_items = self.favorites.get_all()
            if not fav_items:
                self.ui.render_message("Info", "No favorites added yet.", "info")
                return

            result = self.ui.favorites_menu(fav_items)
            if result is None:
                break
            
            idx, action = result
            item = fav_items[idx]
            
            if action == 'remove':
                self.favorites.remove(item['anime_id'])
                continue
            elif action == 'watch':
                try:
                    self.resume_anime(item)
                except Exception as e:
                    self.ui.render_message("Error", f"Failed to resume anime: {str(e)}", "error")

    def handle_anime_selection(self, results):
        while True:
            anime_idx = self.ui.anime_selection_menu(results)
            
            if anime_idx == -1:
                sys.exit(0)
            if anime_idx is None:
                return
            
            selected_anime = results[anime_idx]

            self.rpc.update_viewing_anime(selected_anime.title_en, selected_anime.thumbnail)
            
            def load_episodes_and_poster():
                eps = self.api.get_episodes(selected_anime.id)
                # Cache poster if possible
                if selected_anime.thumbnail:
                    screen_height = self.ui.console.height
                    target_height = min(screen_height, 35)
                    poster_height = target_height - 8
                    if poster_height > 0:
                        self.ui._generate_poster_ansi(selected_anime.thumbnail, poster_height)
                return eps
            
            episodes = self.ui.run_with_loading(
                "Loading episodes & poster...",
                load_episodes_and_poster
            )
            
            if not episodes:
                self.ui.render_message(
                    "✗ No Episodes", 
                    f"No episodes found for '{selected_anime.title_en}'", 
                    "error"
                )
                continue
            
            back_pressed = self.handle_episode_selection(selected_anime, episodes)
            if not back_pressed:
                break
    
    def play_trailer(self, anime):
        import requests
        import time
        
        trailer_url = None
        
        if anime.trailer and anime.trailer not in ["N/A", "None", None, ""]:
            if anime.trailer.startswith(('http://', 'https://')):
                trailer_url = anime.trailer
            else:
                trailer_url = get_trailers_base() + anime.trailer
            
            try:
                check = requests.head(trailer_url, timeout=5)
                if check.status_code == 404:
                    trailer_url = None
            except Exception:
                trailer_url = None
        
        if not trailer_url and anime.yt_trailer and anime.yt_trailer not in ["N/A", "None", None, ""]:
            if anime.yt_trailer.startswith(('http://', 'https://')):
                trailer_url = anime.yt_trailer
            else:
                # Assume it's a YouTube video ID
                trailer_url = f"https://www.youtube.com/watch?v={anime.yt_trailer}"
        
        # Fallback to Jikan API using MAL ID
        if not trailer_url and anime.mal_id and anime.mal_id not in ["0", "N/A", "None", None, ""]:
            try:
                jikan_response = requests.get(
                    f"https://api.jikan.moe/v4/anime/{anime.mal_id}",
                    timeout=10
                )
                if jikan_response.status_code == 200:
                    jikan_data = jikan_response.json()
                    trailer_data = jikan_data.get('data', {}).get('trailer', {})
                    embed_url = trailer_data.get('embed_url', '')
                    
                    if embed_url:
                        # Extract YouTube ID from embed URL
                        match = re.search(r'/embed/([a-zA-Z0-9_-]+)', embed_url)
                        if match:
                            yt_id = match.group(1)
                            trailer_url = f"https://www.youtube.com/watch?v={yt_id}"
            except Exception:
                pass
        
        if not trailer_url:
            self.ui.render_message("Error", "No trailer available for this anime.", "error")
            return
        
        self.ui.clear()
        
        message_text = Text()
        message_text.append("Trailer Launched!\n\n", style="bold green")
        message_text.append("Playing trailer in MPV window...\n", style="info")
        message_text.append("Close MPV to return to episodes list.", style="secondary")
        
        panel = Panel(
            Align.center(message_text, vertical="middle"),
            title=Text("Trailer", style="title"),
            box=HEAVY,
            border_style=COLOR_BORDER,
            padding=(2, 6),
            width=60
        )
        
        self.ui.console.print(Align.center(panel, vertical="middle", height=self.ui.console.height))
        
        self.player.play(trailer_url, f"Trailer - {anime.title_en}")

    def handle_episode_selection(self, selected_anime, episodes):
        current_idx = 0 
        
        while True:
            last_watched = self.history.get_last_watched(selected_anime.id)
            is_fav = self.favorites.is_favorite(selected_anime.id)
            
            anime_details = {
                'score': selected_anime.score,
                'rank': selected_anime.rank,
                'popularity': selected_anime.popularity,
                'rating': selected_anime.rating,
                'type': selected_anime.type,
                'episodes': selected_anime.episodes,
                'status': selected_anime.status,
                'studio': selected_anime.creators,
                'genres': selected_anime.genres,
                'trailer': selected_anime.trailer,
                'yt_trailer': selected_anime.yt_trailer
            }

            ep_idx = self.ui.episode_selection_menu(
                selected_anime.title_en, 
                episodes, 
                self.rpc, 
                selected_anime.thumbnail,
                last_watched_ep=last_watched,
                is_favorite=is_fav,
                anime_details=anime_details
            )
            
            if ep_idx == -1:
                sys.exit(0)
            elif ep_idx is None:
                self.rpc.update_browsing()
                return True
            elif ep_idx == 'toggle_fav':
                if is_fav:
                    self.favorites.remove(selected_anime.id)
                else:
                    self.favorites.add(selected_anime.id, selected_anime.title_en, selected_anime.thumbnail)
                continue
            elif ep_idx == 'batch_mode':
                self.handle_batch_download(selected_anime, episodes)
                continue
            elif ep_idx == 'trailer':
                self.play_trailer(selected_anime)
                continue
            
            current_idx = ep_idx
            
            while True:
                selected_ep = episodes[current_idx]
                
                server_data = self.ui.run_with_loading(
                    "Loading servers...",
                    self.api.get_streaming_servers,
                    selected_anime.id, 
                    selected_ep.number,
                    selected_anime.type
                )
                
                if not server_data:
                    self.ui.render_message(
                        "✗ No Servers", 
                        "No servers available for this episode.",
                        "error"
                    )
                    break
                
                action_taken = self.handle_quality_selection(selected_anime, selected_ep, server_data)
                
                if action_taken == "watch" or action_taken == "download":
                    auto_next = self.settings.get('auto_next')
                    if auto_next and action_taken == "watch":
                        if current_idx + 1 < len(episodes):
                            current_idx += 1
                            continue
                        else:
                            self.ui.render_message("Info", "No more episodes!", "info")
                            break

                    next_action = self.ui.post_watch_menu()
                    
                    if next_action == "Next Episode":
                        if current_idx + 1 < len(episodes):
                            current_idx += 1
                            continue
                        else:
                            self.ui.render_message("Info", "No more episodes!", "info")
                            break
                    elif next_action == "Previous Episode":
                        if current_idx > 0:
                            current_idx -= 1
                            continue
                        else:
                            self.ui.render_message("Info", "This is the first episode.", "info")
                            break
                    elif next_action == "Replay":
                        continue
                    else:
                        break
                else:
                    break

    def handle_batch_download(self, selected_anime, episodes):
        selected_indices = self.ui.batch_selection_menu(episodes)
        if not selected_indices:
            return

        self.ui.print(f"\n[info]Preparing to download {len(selected_indices)} episodes...[/info]")
        
        for idx in selected_indices:
            ep = episodes[idx]
            self.ui.print(f"Processing Episode {ep.display_num}...")
            
            server_data = self.api.get_streaming_servers(selected_anime.id, ep.number, selected_anime.type)
            if not server_data:
                self.ui.print(f"[error]Skipping Ep {ep.display_num}: No servers found[/error]")
                continue
            
            current_ep_data = server_data.get('CurrentEpisode', {})
            qualities = [
                QualityOption("1080p", 'FRFhdQ', "info"),
                QualityOption("720p", 'FRLink', "info"),
                QualityOption("480p", 'FRLowQ', "info"),
            ]
            
            target_quality = self.settings.get('default_quality')
            selected_q = None
            
            for q in qualities:
                if target_quality in q.name and current_ep_data.get(q.server_key):
                    selected_q = q
                    break
            
            # Fallback to best available
            if not selected_q:
                for q in qualities:
                    if current_ep_data.get(q.server_key):
                        selected_q = q
                        break
            
            if selected_q:
                server_id = current_ep_data.get(selected_q.server_key)
                direct_url = self.api.extract_mediafire_direct(self.api.build_mediafire_url(server_id))
                
                if direct_url:
                    filename = f"{selected_anime.title_en} - Ep {ep.display_num} [{selected_q.name}].mp4"
                    download_file(direct_url, filename, self.ui.console)
                    self.history.mark_watched(selected_anime.id, ep.display_num, selected_anime.title_en)
                else:
                    self.ui.print(f"[error]Failed to extract link for Ep {ep.display_num}[/error]")
            else:
                self.ui.print(f"[error]No suitable quality found for Ep {ep.display_num}[/error]")
        
        self.ui.render_message("Success", "Batch download completed!", "success")

    def handle_quality_selection(self, selected_anime, selected_ep, server_data):
        current_ep_data = server_data.get('CurrentEpisode', {})
        qualities = [
            QualityOption("SD • 480p (Low Quality)", 'FRLowQ', "info"),
            QualityOption("HD • 720p (Standard Quality)", 'FRLink', "info"),
            QualityOption("FHD • 1080p (Full HD)", 'FRFhdQ', "info"),
        ]
        
        available = [q for q in qualities if current_ep_data.get(q.server_key)]
        
        if not available:
            self.ui.render_message(
                "✗ No Links", 
                "No MediaFire servers found for this episode.", 
                "error"
            )
            return None

        result = self.ui.quality_selection_menu(
            selected_anime.title_en, 
            selected_ep.display_num, 
            available, 
            self.rpc,
            selected_anime.thumbnail
        )
        
        if result == -1:
            sys.exit(0)
        if result is None:
            return None
            
        idx, action = result
        quality = available[idx]
        server_id = current_ep_data.get(quality.server_key)
        
        direct_url = self.ui.run_with_loading(
            "Extracting direct link...",
            self.api.extract_mediafire_direct,
            self.api.build_mediafire_url(server_id)
        )
        
        if direct_url:
            filename = f"{selected_anime.title_en} - Ep {selected_ep.display_num} [{quality.name.split()[1]}].mp4"
            
            if action == 'download':
                download_file(direct_url, filename, self.ui.console)
                self.history.mark_watched(selected_anime.id, selected_ep.display_num, selected_anime.title_en)
                return "download"
            else:
                player_type = self.settings.get('player')
                
                from rich.text import Text
                from rich.panel import Panel
                from rich.align import Align
                from rich.box import HEAVY
                from .config import COLOR_BORDER, COLOR_TITLE
                
                watching_text = Text()
                watching_text.append("▶ ", style=COLOR_TITLE + " blink")
                watching_text.append(selected_anime.title_en, style="bold")
                watching_text.append("\nEpisode ", style="secondary")
                watching_text.append(str(selected_ep.display_num), style=COLOR_TITLE + " bold")
                watching_text.append(" ◀", style=COLOR_TITLE + " blink")
                watching_text.append(f"\n\n{quality.name}", style="dim")
                
                watching_panel = Panel(
                    Align.center(watching_text, vertical="middle"),
                    title=Text("NOW PLAYING", style=COLOR_TITLE + " bold"),
                    box=HEAVY,
                    border_style=COLOR_BORDER,
                    padding=(2, 4),
                    width=60
                )
                
                self.ui.clear()
                self.ui.console.print(Align.center(watching_panel, vertical="middle", height=self.ui.console.height))
                
                self.rpc.update_watching(selected_anime.title_en, str(selected_ep.display_num), selected_anime.thumbnail)
                
                monitor.track_video_play(selected_anime.title_en, str(selected_ep.display_num))
                
                self.player.play(direct_url, f"{selected_anime.title_en} - Ep {selected_ep.display_num} ({quality.name})", player_type=player_type)
                self.ui.clear()
                self.history.mark_watched(selected_anime.id, selected_ep.display_num, selected_anime.title_en)
                self.rpc.update_selecting_episode(selected_anime.title_en, selected_anime.thumbnail)
                return "watch"
        else:
            self.ui.render_message(
                "✗ Error", 
                "Failed to extract direct link from MediaFire.", 
                "error"
            )
            return None

    def handle_exit(self):
        self.ui.clear()
        
        panel = Panel(
            Text("👋 Interrupted - Goodbye!", justify="center", style="info"),
            title=Text("EXIT", style="title"),
            box=HEAVY,
            padding=1,
            border_style=COLOR_BORDER
        )
        
        self.ui.print(Align.center(panel, vertical="middle", height=self.ui.console.height))

    def handle_error(self, e):
        self.ui.clear()
        self.ui.console.print_exception()
        
        panel = Panel(
            Text(f"✗ Unexpected error: {e}", justify="center", style="error"),
            title=Text("CRITICAL ERROR", style="title"),
            box=HEAVY,
            padding=1,
            border_style=COLOR_BORDER
        )
        
        self.ui.print(Align.center(panel, vertical="middle", height=self.ui.console.height))
        input("\nPress ENTER to exit...")

    def cleanup(self):
        try:
            self.rpc.disconnect()
        except Exception:
            pass
        
        try:
            self.player.cleanup_temp_mpv()
        except Exception:
            pass
        
        # Only show TUI goodbye if we are NOT in CLI mode
        if self.current_mode != "cli":
            self.ui.clear()
            from .config import COLOR_ASCII
            
            self.ui.print("\n" * 2)
            self.ui.print(Align.center(Text(GOODBYE_ART, style=COLOR_ASCII)))
            self.ui.print("\n")


def main():
    home_dir = Path.home()
    db_dir = home_dir / ".ani-cli-arabic" / "database"
    db_dir.mkdir(parents=True, exist_ok=True)
    
    app = AniCliArApp()
    app.run()


if __name__ == "__main__":
    main()
