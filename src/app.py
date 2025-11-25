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

class AniCliArApp:
    def __init__(self):
        self.ui = UIManager()
        self.api = AnimeAPI()
        self.rpc = DiscordRPCManager()
        self.player = PlayerManager(rpc_manager=self.rpc, console=self.ui.console)

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
            vertical_padding = (self.ui.console.height - content_height) // 2
            
            if vertical_padding > 0:
                self.ui.print(Text("\n" * vertical_padding))

            self.ui.print(Align.center(self.ui.get_header_renderable()))
            self.ui.print()

            search_prompt = Panel(
                Text("Search Anime (or 'q' to quit)", style="info", justify="center"),
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
            
            if not query:
                continue
            
            self.rpc.update_searching()
            
            results = self.ui.run_with_loading(
                "Searching anime...",
                self.api.search_anime,
                query
            )
            
            if not results:
                self.ui.render_message("✗ No Results", f"No results found for '{query}'", "error")
                continue
            
            self.handle_anime_selection(results)

    def handle_anime_selection(self, results):
        while True:
            anime_idx = self.ui.anime_selection_menu(results)
            
            if anime_idx == -1: # Quit
                sys.exit(0)
            if anime_idx is None: # Back
                return
            
            selected_anime = results[anime_idx]
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
        while True:
            ep_idx = self.ui.episode_selection_menu(selected_anime.title_en, episodes, self.rpc, selected_anime.thumbnail)
            
            if ep_idx == -1: # Quit
                sys.exit(0)
            elif ep_idx is None: # Back
                self.rpc.update_browsing()
                return True # Signal to go back
            
            selected_ep = episodes[ep_idx]
            
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
                continue
            
            self.handle_quality_selection(selected_anime, selected_ep, server_data)

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
            return

        idx = self.ui.quality_selection_menu(
            selected_anime.title_en, 
            selected_ep.display_num, 
            available, 
            self.rpc,
            selected_anime.thumbnail
        )
        
        if idx == -1:
            sys.exit(0)
        if idx is None:
            return
            
        quality = available[idx]
        server_id = current_ep_data.get(quality.server_key)
        
        direct_url = self.ui.run_with_loading(
            "Extracting direct link...",
            self.api.extract_mediafire_direct,
            self.api.build_mediafire_url(server_id)
        )
        
        if direct_url:
            self.player.play(direct_url, f"{selected_anime.title_en} - Ep {selected_ep.display_num} ({quality.name})")
            self.rpc.update_selecting_episode(selected_anime.title_en, selected_anime.thumbnail)
        else:
            self.ui.render_message(
                "✗ Error", 
                "Failed to extract direct link from MediaFire.", 
                "error"
            )

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