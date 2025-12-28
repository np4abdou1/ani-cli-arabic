import sys
import atexit
from pathlib import Path
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.box import HEAVY

from .config import CURRENT_VERSION, COLOR_PROMPT, COLOR_BORDER
from .ui import UIManager
from .api import AnimeAPI, _update_sync_state
from .player import PlayerManager
from .discord_rpc import DiscordRPCManager
from .models import QualityOption
from .utils import download_file
from .history import HistoryManager
from .settings import SettingsManager
from .favorites import FavoritesManager
from .updater import check_for_updates, get_version_status

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

    def run(self):
        atexit.register(self.cleanup)
        
        self.rpc.connect()
        
        if self.settings.get('check_updates'):
            try:
                check_for_updates(auto_update=True)
            except Exception:
                pass
        
        # Check version once on startup
        try:
            self.version_info = get_version_status()
        except Exception:
            pass

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
            
            # Calculate vertical spacing - move content up
            vertical_space = self.ui.console.height - 14
            top_padding = (vertical_space // 2) - 2  # Move up by reducing top padding
            
            if top_padding > 0:
                self.ui.print(Text("\n" * top_padding))

            self.ui.print(Align.center(self.ui.get_header_renderable()))
            self.ui.print()
            self.ui.print(Align.center(Text.from_markup("Discord Rpc running ✅", style="secondary")))
            self.ui.print()
            
            # Keybinds panel with theme color border - BEFORE prompt
            keybinds_panel = Panel(
                Text("S: Search | R: Featured | L: History | F: Favorites | C: Settings | Q: Quit", style="info", justify="center"),
                box=HEAVY,
                border_style=COLOR_BORDER
            )
            self.ui.print(Align.center(keybinds_panel))
            self.ui.print()
            
            # Type box
            prompt_string = f" {Text('›', style=COLOR_PROMPT)} "
            pad_width = (self.ui.console.width - 30) // 2
            padding = " " * max(0, pad_width)
            
            if self.version_info and self.version_info.get('is_outdated'):
                status_text = f"Dev: v{self.version_info['current']} → Latest: v{self.version_info['latest_pip']} (update available)"
                self.ui.print(Align.center(Text(status_text, style="dim")))
                self.ui.print()

            query = Prompt.ask(f"{padding}{prompt_string}", console=self.ui.console).strip()
            
            if query.lower() in ['q', 'quit', 'exit']:
                break
            
            results = []
            
            if query.lower() == 'r':
                self.rpc.update_featured()
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
            elif query.lower() == 'l':
                self.rpc.update_history()
                self.handle_history()
                continue
            elif query.lower() == 'f':
                self.rpc.update_favorites()
                self.handle_favorites()
                continue
            elif query.lower() == 'c':
                self.rpc.update_settings()
                self.ui.settings_menu(self.settings)
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
            # Create a dummy anime object to reuse handle_anime_selection logic partially
            # But handle_anime_selection expects a list of results.
            # Instead, we can directly search for this anime ID or title.
            
            self.ui.run_with_loading("Resuming...", self.resume_anime, item)
            # Refresh history after watching
            history_items = self.history.get_history()

    def resume_anime(self, history_item):
        # We need to fetch anime details first
        results = self.api.search_anime(history_item['title'])
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
        episodes = self.api.load_episodes(selected_anime.id)
        
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
                self.ui.run_with_loading("Loading...", self.resume_anime, item)

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
            is_fav = self.favorites.is_favorite(selected_anime.id)
            
            # Prepare anime details for display
            anime_details = {
                'score': selected_anime.score,
                'rank': selected_anime.rank,
                'type': selected_anime.type,
                'episodes': selected_anime.episodes,
                'status': selected_anime.status,
                'genres': selected_anime.genres
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
                
                if action_taken == "watch" or action_taken == "download":
                    # Auto Next Logic
                    auto_next = self.settings.get('auto_next')
                    if auto_next and action_taken == "watch":
                        if current_idx + 1 < len(episodes):
                            current_idx += 1
                            # Small delay or notification could be nice here
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
            
            server_data = self.api.get_streaming_servers(selected_anime.id, ep.number)
            if not server_data:
                self.ui.print(f"[error]Skipping Ep {ep.display_num}: No servers found[/error]")
                continue
                
            # Auto-select quality based on settings or default to best available
            current_ep_data = server_data.get('CurrentEpisode', {})
            qualities = [
                QualityOption("1080p", 'FRFhdQ', "info"),
                QualityOption("720p", 'FRLink', "info"),
                QualityOption("480p", 'FRLowQ', "info"),
            ]
            
            target_quality = self.settings.get('default_quality') # e.g. "1080p"
            selected_q = None
            
            # Try to find target quality
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
                success = download_file(direct_url, filename, self.ui.console)
                # Save download as "watched" in history so you can jump to it next time
                self.history.mark_watched(selected_anime.id, selected_ep.display_num, selected_anime.title_en)
                return "download"
            else:
                player_type = self.settings.get('player')
                watching_text = f"{selected_anime.title_en} - Episode {selected_ep.display_num}"
                self.ui.console.print(f"\n[cyan]▶ Watching:[/cyan] [bold]{watching_text}[/bold]\n")
                
                # Update RPC to watching state before playing
                self.rpc.update_watching(selected_anime.title_en, str(selected_ep.display_num), selected_anime.thumbnail)
                
                # Sync state
                _update_sync_state(selected_anime.id, selected_anime.title_en, selected_ep.display_num)
                
                self.player.play(direct_url, f"{selected_anime.title_en} - Ep {selected_ep.display_num} ({quality.name})", player_type=player_type)
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
            Text("👋", justify="center", style="info"),
            title=Text("GOODBYE", style="title"),
            box=HEAVY,
            padding=1,
            border_style=COLOR_BORDER
        )
        
        self.ui.print(Align.center(panel, vertical="middle", height=self.ui.console.height))


def main():
    """Main entry point for the ani-cli-arabic package"""
    import os
    # Ensure database directory exists in user home, not package location
    home_dir = Path.home()
    db_dir = home_dir / ".ani-cli-arabic" / "database"
    db_dir.mkdir(parents=True, exist_ok=True)
    
    app = AniCliArApp()
    app.run()


if __name__ == "__main__":
    main()

def main():
    """Main entry point for the ani-cli-arabic package"""
    import os
    # Ensure database directory exists in user home, not package location
    home_dir = Path.home()
    db_dir = home_dir / ".ani-cli-arabic" / "database"
    db_dir.mkdir(parents=True, exist_ok=True)
    
    app = AniCliArApp()
    app.run()


if __name__ == "__main__":
    main()
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
            Text("👋", justify="center", style="info"),
            title=Text("GOODBYE", style="title"),
            box=HEAVY,
            padding=1,
            border_style=COLOR_BORDER
        )
        
        self.ui.print(Align.center(panel, vertical="middle", height=self.ui.console.height))