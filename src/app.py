import sys
import atexit
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.box import HEAVY

from .config import CURRENT_VERSION, COLOR_PROMPT, COLOR_BORDER
from .ui import UIManager
from .api import AnimeAPI
from .player import PlayerManager
from .discord_rpc import DiscordRPCManager
from .models import QualityOption
from .utils import download_file
from .history import HistoryManager

class AniCliArApp:
    def __init__(self):
        self.ui = UIManager()
        self.api = AnimeAPI()
        self.rpc = DiscordRPCManager()
        self.player = PlayerManager(rpc_manager=self.rpc, console=self.ui.console)
        self.history = HistoryManager()

    def run(self):
        atexit.register(self.cleanup)
        
        self.rpc.connect()

        try:
            self.main_loop()
        except KeyboardInterrupt:
            self.handle_exit()
        except Exception as e:
            self.handle_error(e)
        finally:
            self.cleanup()

    def main_loop(self):
        while True:
            self.ui.clear()
            
            content_height = 16
            vertical_padding = (self.ui.console.height - content_height) // 3
            
            if vertical_padding > 0:
                self.ui.print(Text("\n" * vertical_padding))

            self.ui.print(Align.center(self.ui.get_header_renderable()))
            self.ui.print()

            search_prompt = Panel(
                Text("S Search | R Relevant/Featured (MAL) | Q Quit", style="info", justify="center"),
                box=HEAVY,
                padding=(0, 4),
                border_style=COLOR_BORDER
            )
            
            self.ui.print(Align.center(search_prompt))
            self.ui.print(Align.center(Text.from_markup("Discord Rpc running ✅", style="secondary")))
            self.ui.print()
            
            prompt_string = f" {Text('›', style=COLOR_PROMPT)} "
            pad_width = (self.ui.console.width - 30) // 2
            padding = " " * max(0, pad_width)

            query = Prompt.ask(f"{padding}{prompt_string}", console=self.ui.console).strip()
            
            if query.lower() in ['q', 'quit', 'exit']:
                break
            
            results = []
            
            if query.lower() == 'r':
                self.rpc.update_searching()
                # Fetching from Jikan (MAL) with auto-SFW filtering
                results = self.ui.run_with_loading(
                    "Fetching currently airing anime from MAL...",
                    self.api.get_mal_season_now
                )
            elif query.lower() == 's':
                 term = Prompt.ask(f"{padding} Enter Search Term: ", console=self.ui.console).strip()
                 if term:
                    self.rpc.update_searching()
                    results = self.ui.run_with_loading("Searching...", self.api.search_anime, term)
            elif query:
                self.rpc.update_searching()
                results = self.ui.run_with_loading("Searching...", self.api.search_anime, query)
            else:
                continue
            
            if not results:
                self.ui.render_message("✗ No Results", f"No results found.", "error")
                continue
            
            self.handle_anime_selection(results)

    def handle_anime_selection(self, results):
        while True:
            anime_idx = self.ui.anime_selection_menu(results)
            
            if anime_idx == -1:
                sys.exit(0)
            if anime_idx is None:
                return
            
            selected_anime = results[anime_idx]

            # --- BRIDGE LOGIC: MAL to Internal API ---
            if not selected_anime.id:
                internal_results = self.ui.run_with_loading(
                    f"Syncing '{selected_anime.title_en}'...",
                    self.api.search_anime,
                    selected_anime.title_en
                )
                
                if not internal_results:
                     self.ui.render_message("✗ Not Found", f"Sorry, '{selected_anime.title_en}' hasn't been uploaded to the server yet.", "error")
                     continue
                
                selected_anime = internal_results[0]
            # -----------------------------------------

            self.rpc.update_viewing_anime(selected_anime.title_en, selected_anime.thumbnail)
            
            episodes = self.ui.run_with_loading(
                "Loading episodes...",
                self.api.load_episodes,
                selected_anime.id
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

    def handle_episode_selection(self, selected_anime, episodes):
        current_idx = 0 
        
        while True:
            last_watched = self.history.get_last_watched(selected_anime.id)

            ep_idx = self.ui.episode_selection_menu(
                selected_anime.title_en, 
                episodes, 
                self.rpc, 
                selected_anime.thumbnail,
                last_watched_ep=last_watched
            )
            
            if ep_idx == -1:
                sys.exit(0)
            elif ep_idx is None:
                self.rpc.update_browsing()
                return True
            
            current_idx = ep_idx
            
            while True:
                selected_ep = episodes[current_idx]
                
                server_data = self.ui.run_with_loading(
                    "Loading servers...",
                    self.api.get_streaming_servers,
                    selected_anime.id, 
                    selected_ep.number
                )
                
                if not server_data:
                    self.ui.render_message(
                        "✗ No Servers", 
                        "No servers available for this episode.",
                        "error"
                    )
                    break
                
                action_taken = self.handle_quality_selection(selected_anime, selected_ep, server_data)
                
                # --- UPDATED LOGIC HERE ---
                # Check for both "watch" AND "download"
                if action_taken == "watch" or action_taken == "download":
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

    def handle_quality_selection(self, selected_anime, selected_ep, server_data):
        current_ep_data = server_data.get('CurrentEpisode', {})
        qualities = [
            QualityOption("📱 480p (Low Quality)", 'FRLowQ', "info"),
            QualityOption("🎬 720p (Standard Quality)", 'FRLink', "info"),
            QualityOption("🎞️  1080p (Full HD)", 'FRFhdQ', "info"),
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
                success = download_file(direct_url, filename, self.ui.console)
                # Save download as "watched" in history so you can jump to it next time
                self.history.mark_watched(selected_anime.id, selected_ep.display_num, selected_anime.title_en)
                return "download"
            else:
                self.player.play(direct_url, f"{selected_anime.title_en} - Ep {selected_ep.display_num} ({quality.name})")
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
        self.rpc.disconnect()
        self.player.cleanup_temp_mpv()
        self.ui.clear()
        
        panel = Panel(
            Text("👋 Thanks for using ani-cli-arabic!", justify="center", style="info"),
            title=Text("GOODBYE", style="title"),
            box=HEAVY,
            padding=1,
            border_style=COLOR_BORDER
        )
        
        self.ui.print(Align.center(panel, vertical="middle", height=self.ui.console.height))