import sys
import atexit
import re
from pathlib import Path
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.box import HEAVY

from .config import COLOR_PROMPT, COLOR_BORDER, COLOR_TITLE, GOODBYE_ART, POPULAR_GENRES
from .ui import UIManager
from .api import AnimeAPI, get_trailers_base
from .providers import ProviderManager
from .monitoring import monitor
from .player import PlayerManager
from .discord_rpc import DiscordRPCManager
from .models import QualityOption
from .utils import download_file, flush_stdin, show_cursor, hide_cursor
from .history import HistoryManager, format_seconds
from .settings import SettingsManager
from .favorites import FavoritesManager
from .updater import check_for_updates, get_version_status
from .deps import ensure_dependencies
from .cli import run_simple_cli
from .logger import logger, install_global_exception_handler
import shutil
import argparse

class AniCliArApp:
    def __init__(self):
        install_global_exception_handler()
        atexit.register(show_cursor)
        hide_cursor()
        self.ui = UIManager()
        self.settings = SettingsManager()
        if self.settings.get("debug_logging"):
            logger.enable()
        active_provider_id = self.settings.get("anime_provider") or "anime3rb"
        self.provider = ProviderManager.get_provider(active_provider_id)
        self.api = self.provider
        ProviderManager.set_active_provider(active_provider_id)
        self.rpc = DiscordRPCManager()
        self.player = PlayerManager(rpc_manager=self.rpc, console=self.ui.console)
        self.history = HistoryManager()
        self.favorites = FavoritesManager()
        self.version_info = None
        self.current_mode = "tui"
        self.force_cli = False
        self._cleaned_up = False

    def run(self):
        parser = argparse.ArgumentParser(
            description="ani-cli-arabic: A CLI tool to browse and watch anime in Arabic.",
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument('-i', '--interactive', action='store_true', help="Force minimal interactive CLI mode")
        parser.add_argument('-p', '--provider', choices=ProviderManager.get_provider_choices(), help="Specify active anime provider (anime3rb, anime_slayer, anidb)")
        parser.add_argument('-d', '--debug', action='store_true', help="Enable verbose debug logging to file and console")
        parser.add_argument('-v', '--version', action='store_true', help="Show version information")
        parser.add_argument('query', nargs='*', help="Anime name to search for")
        
        args = parser.parse_args()
        
        if args.debug:
            logger.enable(console_mirror=True)
            logger.debug("APP", "CLI flag --debug specified, verbose console mirror enabled")

        if args.provider:
            self.provider = ProviderManager.get_provider(args.provider)
            self.api = self.provider
            ProviderManager.set_active_provider(args.provider)
            logger.debug("APP", f"CLI flag --provider specified, active provider set to {args.provider}")
            
        if args.version:
            from .version import __version__
            print(f"ani-cli-arabic v{__version__}")
            sys.exit(0)
            
        self.force_cli = args.interactive
        initial_query = " ".join(args.query) if args.query else None
        
        logger.debug("APP", f"App starting | interactive={args.interactive} | debug={args.debug} | provider={ProviderManager.get_active_provider_id()} | query={initial_query}")

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
        
        def run_cleanup_bg():
            try:
                from .storage import cleanup_temporary_files
                cleanup_temporary_files()
            except Exception:
                pass
        threading.Thread(target=run_cleanup_bg, daemon=True).start()

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
                query = None # Clear query after first run
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

    def run_tui_mode(self, initial_query=None):
        query_override = initial_query
        
        while True:
            if '-i' not in sys.argv and shutil.get_terminal_size().columns < 80:
                return "SWITCH_TO_CLI"

            # Always synchronize active provider directly from settings before home screen/actions
            active_provider_id = self.settings.get("anime_provider") or "anime3rb"
            self.provider = ProviderManager.get_provider(active_provider_id)
            self.api = self.provider
            ProviderManager.set_active_provider(active_provider_id)

            if query_override:
                action, payload = "search", query_override
                query_override = None
            else:
                provider_name = getattr(self.api, 'name', 'Unknown')
                action, payload = self.ui.home_screen_menu(
                    rpc_status=getattr(self, 'rpc_status', None),
                    version_info=self.version_info,
                    active_provider=provider_name
                )

            if action in ["quit", "exit"] or action is None:
                break

            results = []

            if action == "latest":
                self.handle_latest_episodes()
                continue

            elif action == "movies":
                self.handle_movies()
                continue

            elif action == "top_rated":
                self.handle_top_rated()
                continue

            elif action == "trending":
                self.handle_trending()
                continue

            elif action == "popular":
                self.handle_popular()
                continue

            elif action == "genres":
                self.handle_genres()
                continue

            elif action == "studios":
                self.rpc.update_studios()
                self.handle_studios()
                continue

            elif action == "history":
                self.rpc.update_history()
                self.handle_history()
                continue

            elif action == "favorites":
                self.rpc.update_favorites()
                self.handle_favorites()
                continue

            elif action == "settings":
                self.rpc.update_settings()
                self.ui.settings_menu(self.settings)
                active_provider_id = self.settings.get("anime_provider") or "anime3rb"
                self.provider = ProviderManager.get_provider(active_provider_id)
                self.api = self.provider
                ProviderManager.set_active_provider(active_provider_id)
                continue

            elif action == "donate":
                import webbrowser
                webbrowser.open("https://paypal.me/np4abdou")
                continue

            elif action == "search":
                search_query = payload
                if not search_query:
                    continue
                self.rpc.update_searching()
                results = self.ui.run_with_loading("Searching...", self.api.search_anime, search_query)
                if not results:
                    q_clean = re.sub(r'[:\-!?,._\(\)\[\]]', ' ', search_query).strip()
                    q_clean = re.sub(r'\s+', ' ', q_clean)
                    variants = []
                    if q_clean and q_clean.lower() != search_query.lower():
                        variants.append(q_clean)
                    ar_norm = search_query.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه').replace('ى', 'ي')
                    if ar_norm != search_query and ar_norm not in variants:
                        variants.append(ar_norm)
                    words = q_clean.split()
                    if len(words) > 3:
                        variants.append(' '.join(words[:3]))

                    for alt_q in variants:
                        results = self.api.search_anime(alt_q)
                        if results:
                            break

                if not results:
                    self.ui.render_message(
                        "✗ No Anime Found", 
                        f"No anime matching '{search_query}' was found.\n\nTry:\n• Checking spelling\n• Using English or Romaji name\n• Using Arabic title", 
                        "error"
                    )
                    continue
                self.handle_anime_selection(results)
                continue

    def handle_anime_selection_with_lazy_load(self, results, load_more_callback):
        while True:
            anime_idx = self.ui.anime_selection_menu(results, load_more_callback=load_more_callback, api=self.api)
            
            if anime_idx == -1:
                sys.exit(0)
            if anime_idx is None:
                return
            
            selected_anime = results[anime_idx]

            self.rpc.update_viewing_anime(selected_anime.title_en, selected_anime.thumbnail)
            
            episodes = self.ui.run_with_loading(
                "Loading episodes & poster...",
                lambda: self._fetch_episodes_and_poster(selected_anime)
            )
            
            if not episodes:
                self.ui.render_message(
                    "✗ No Episodes", 
                    f"No episodes found for '{selected_anime.title_en}'.", 
                    "error"
                )
                continue
            
            self.handle_episode_selection(selected_anime, episodes)

    def handle_latest_episodes(self):
        episodes = self.ui.run_with_loading(
            "Fetching latest episodes...",
            self.api.get_latest_episodes,
            40
        )
        if not episodes:
            self.ui.render_message("Info", "No recent episodes found.", "info")
            return

        while True:
            res = self.ui.latest_episodes_menu(episodes)
            if res is None:
                break
            idx, act = res
            ep_info = episodes[idx]

            selected_anime = self.ui.run_with_loading(
                f"Loading {ep_info['title']}...",
                self.api.get_anime_details,
                ep_info["slug"]
            )
            if not selected_anime:
                continue

            all_episodes = self.ui.run_with_loading(
                "Loading episode list...",
                self.api.get_episodes,
                selected_anime.id
            )
            if not all_episodes:
                continue

            if act == 'play':
                initial_idx = self._find_episode_index(all_episodes, ep_info["ep_num"])
                self.handle_episode_selection(selected_anime, all_episodes, initial_selected=initial_idx)
            else:
                self.handle_episode_selection(selected_anime, all_episodes)

    def handle_movies(self):
        results = self.ui.run_with_loading(
            "Fetching anime movies...",
            self.api.get_movies,
            0,
            20
        )
        if results:
            def load_more_movies(current_count):
                return self.api.get_movies(current_count, 20)
            self.handle_anime_selection_with_lazy_load(results, load_more_movies)
        else:
            self.ui.render_message("Info", "No anime movies found.", "info")

    def handle_top_rated(self):
        results = self.ui.run_with_loading(
            "Fetching top-rated anime (9-10)...",
            self.api.get_top_rated_anime,
            0,
            20,
            "9-10"
        )
        if results:
            def load_more_top(current_count):
                return self.api.get_top_rated_anime(current_count, 20, "9-10")
            self.handle_anime_selection_with_lazy_load(results, load_more_top)
        else:
            self.ui.render_message("Info", "No top-rated anime found.", "info")

    def handle_trending(self):
        self.rpc.update_trending()
        results = self.ui.run_with_loading(
            "Fetching trending anime...",
            self.api.get_trending_anime,
            0,
            20
        )
        if results:
            def load_more_trending(current_count):
                return self.api.get_trending_anime(current_count, 20)
            self.handle_anime_selection_with_lazy_load(results, load_more_trending)
        else:
            self.ui.render_message("Info", "No trending anime found.", "info")

    def handle_popular(self):
        self.rpc.update_popular()
        results = self.ui.run_with_loading(
            "Fetching spotlight & popular anime...",
            self.api.get_pinned_anime
        )
        if not results:
            results = self.ui.run_with_loading(
                "Fetching popular anime...",
                self.api.get_trending_anime,
                0,
                20
            )
        if results:
            def load_more_popular(current_count):
                return self.api.get_trending_anime(current_count, 20)
            self.handle_anime_selection_with_lazy_load(results, load_more_popular)
        else:
            self.ui.render_message("Info", "No popular anime found.", "info")

    def handle_genres(self):
        self.rpc.update_genres()
        selected_genre = self.ui.genre_selection_menu(POPULAR_GENRES)
        if selected_genre:
            genre_name = selected_genre["name_en"] if isinstance(selected_genre, dict) else str(selected_genre)
            genre_slug = selected_genre.get("slug", genre_name.lower()) if isinstance(selected_genre, dict) else genre_name.lower()

            results = self.ui.run_with_loading(
                f"Fetching {genre_name} anime...",
                self.api.get_genre_anime,
                genre_slug,
                0,
                20
            )
            if results:
                def load_more_genre(current_count):
                    return self.api.get_genre_anime(genre_slug, current_count, 20)
                self.handle_anime_selection_with_lazy_load(results, load_more_genre)
            else:
                self.ui.render_message("Info", f"No anime found for genre: {genre_name}", "info")

    def handle_studios(self):
        studios = [
            "Toei Animation", "Sunrise", "Madhouse", "Production I.G", "J.C.Staff", 
            "TMS Entertainment", "Studio Pierrot", "Studio Deen", "A-1 Pictures", 
            "Bones", "Kyoto Animation", "MAPPA", "Wit Studio", "ufotable", 
            "White Fox", "David Production", "Shaft", "Trigger", "CloverWorks", 
            "Lerche", "P.A. Works", "CoMix Wave Films", "Gainax", "Studio Ghibli"
        ]
        studios.sort()
        
        selected_studio = self.ui.selection_menu(studios, title="Select Studio")
        if selected_studio:
            results = self.ui.run_with_loading(
                f"Fetching {selected_studio} anime...",
                self.api.get_studio_anime,
                selected_studio,
                0,
                20
            )
            if results:
                def load_more_studio(current_count):
                    return self.api.get_studio_anime(selected_studio, current_count, 20)
                self.handle_anime_selection_with_lazy_load(results, load_more_studio)
            else:
                self.ui.render_message("Info", f"No anime found for studio: {selected_studio}", "info")

    def handle_history(self):
        while True:
            history_items = self.history.get_history()
            if not history_items:
                self.ui.render_message("Info", "No history found.", "info")
                return

            result = self.ui.history_menu(history_items)
            if result is None:
                break
            
            selected_idx, action = result
            item = history_items[selected_idx]
            
            if action == 'remove':
                self.history.remove(item['anime_id'])
                continue
            elif action == 'resume':
                self.resume_anime(item, direct_watch=True)
            elif action == 'episodes':
                self.resume_anime(item, direct_watch=False)

    def _find_episode_index(self, episodes, episode_value):
        if episode_value is None:
            return 0

        target_raw = str(episode_value).strip()
        if not target_raw:
            return 0

        for idx, ep in enumerate(episodes):
            if str(ep.display_num) == target_raw or str(ep.number) == target_raw:
                return idx

        try:
            target_float = float(target_raw)
            for idx, ep in enumerate(episodes):
                try:
                    if float(ep.display_num) == target_float:
                        return idx
                except (TypeError, ValueError):
                    continue
        except (TypeError, ValueError):
            pass

        return 0

    def resume_anime(self, history_item, direct_watch=True):
        results = self.ui.run_with_loading("Resuming...", self.api.search_anime, history_item['title'])
        if not results:
            self.ui.render_message("Error", "Could not find anime details.", "error")
            return

        target_anime_id = str(history_item.get('anime_id') or history_item.get('id') or "")
        selected_anime = None
        for res in results:
            if target_anime_id and str(res.id) == target_anime_id:
                selected_anime = res
                break
        
        if not selected_anime:
            selected_anime = results[0] # Fallback

        self.rpc.update_viewing_anime(selected_anime.title_en, selected_anime.thumbnail)
        episodes = self.ui.run_with_loading(
            "Loading episodes...", 
            self.api.get_episodes, 
            selected_anime.id
        )
        
        if episodes:
            initial_idx = self._find_episode_index(episodes, history_item.get('episode'))
            if direct_watch:
                target_ep = episodes[initial_idx]
                server_data = self.ui.run_with_loading(
                    f"Loading servers for Ep {target_ep.display_num}...",
                    self.api.get_streaming_servers,
                    selected_anime.id, 
                    target_ep.number,
                    selected_anime.type
                )
                if not server_data:
                    self.ui.render_message("Error", "No servers available for this episode.", "error")
                    return

                action_taken = self.handle_quality_selection(selected_anime, target_ep, server_data)
                if not action_taken:
                    # User cancelled quality selection -> return cleanly to caller
                    return

                if action_taken == "watch":
                    current_idx = initial_idx
                    while True:
                        auto_next = self.settings.get('auto_next')
                        if auto_next:
                            if current_idx + 1 < len(episodes):
                                current_idx += 1
                                selected_ep = episodes[current_idx]
                                s_data = self.ui.run_with_loading(
                                    "Loading servers...",
                                    self.api.get_streaming_servers,
                                    selected_anime.id,
                                    selected_ep.number,
                                    selected_anime.type
                                )
                                if s_data:
                                    act = self.handle_quality_selection(selected_anime, selected_ep, s_data)
                                    if act == "watch":
                                        continue
                            else:
                                self.ui.render_message("Info", "No more episodes!", "info")
                            break
                        
                        next_action = self.ui.post_watch_menu(selected_anime.title_en, str(episodes[current_idx].display_num))
                        if next_action == "Next Episode":
                            if current_idx + 1 < len(episodes):
                                current_idx += 1
                                selected_ep = episodes[current_idx]
                                s_data = self.ui.run_with_loading(
                                    "Loading servers...",
                                    self.api.get_streaming_servers,
                                    selected_anime.id,
                                    selected_ep.number,
                                    selected_anime.type
                                )
                                if s_data:
                                    act = self.handle_quality_selection(selected_anime, selected_ep, s_data)
                                    if act == "watch":
                                        continue
                            else:
                                self.ui.render_message("Info", "No more episodes!", "info")
                            break
                        elif next_action == "Previous Episode":
                            if current_idx > 0:
                                current_idx -= 1
                                selected_ep = episodes[current_idx]
                                s_data = self.ui.run_with_loading(
                                    "Loading servers...",
                                    self.api.get_streaming_servers,
                                    selected_anime.id,
                                    selected_ep.number,
                                    selected_anime.type
                                )
                                if s_data:
                                    act = self.handle_quality_selection(selected_anime, selected_ep, s_data)
                                    if act == "watch":
                                        continue
                            else:
                                self.ui.render_message("Info", "This is the first episode.", "info")
                            break
                        elif next_action == "Replay":
                            selected_ep = episodes[current_idx]
                            s_data = self.ui.run_with_loading(
                                "Loading servers...",
                                self.api.get_streaming_servers,
                                selected_anime.id,
                                selected_ep.number,
                                selected_anime.type
                            )
                            if s_data:
                                act = self.handle_quality_selection(selected_anime, selected_ep, s_data, start_time=0.001)
                                if act == "watch":
                                    continue
                            break
                        elif next_action == "Back to Episodes":
                            self.handle_episode_selection(selected_anime, episodes, initial_idx=current_idx)
                            return
                        else:
                            # User pressed Back/ESC/q: return cleanly to History
                            return
                    return
            else:
                self.handle_episode_selection(selected_anime, episodes, initial_idx=initial_idx)

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
            anime_idx = self.ui.anime_selection_menu(results, api=self.api)
            
            if anime_idx == -1:
                sys.exit(0)
            if anime_idx is None:
                return
            
            selected_anime = results[anime_idx]

            self.rpc.update_viewing_anime(selected_anime.title_en, selected_anime.thumbnail)
            
            
            episodes = self.ui.run_with_loading(
                "Loading episodes & poster...",
                lambda: self._fetch_episodes_and_poster(selected_anime)
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
    

    def _fetch_episodes_and_poster(self, selected_anime):
        # Fetch rich anime details and update model
        detailed = self.api.get_anime_details(selected_anime.id)
        if detailed:
            selected_anime.score = detailed.score
            selected_anime.genres = detailed.genres
            selected_anime.status = detailed.status
            selected_anime.premiered = detailed.premiered
            selected_anime.creators = detailed.creators
            selected_anime.synopsis = detailed.synopsis
            selected_anime.trailer = detailed.trailer
            selected_anime.yt_trailer = detailed.yt_trailer
            selected_anime.trailers = detailed.trailers
            if detailed.thumbnail:
                selected_anime.thumbnail = detailed.thumbnail

        eps = self.api.get_episodes(selected_anime.id) or []

        if selected_anime.thumbnail:
            screen_height = self.ui.console.height
            target_height = min(screen_height, 50)
            poster_height = target_height - 8
            if poster_height > 0:
                self.ui._generate_poster_ansi(selected_anime.thumbnail, poster_height)
        return eps

    def play_trailer(self, anime):
        import requests
        
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
                trailer_url = f"https://www.youtube.com/watch?v={anime.yt_trailer}"
        
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
        
        self.ui.render_now_playing(anime.title_en, "Official Trailer", "YouTube / Direct Stream")
        self.player.play(trailer_url, f"Trailer - {anime.title_en}")

    def handle_episode_selection(self, selected_anime, episodes, initial_idx=0):
        current_idx = max(0, min(int(initial_idx or 0), len(episodes) - 1))
        
        while True:
            last_watched = self.history.get_last_watched(selected_anime.id)
            episodes_prog = self.history.get_all_episodes_progress(selected_anime.id)
            is_fav = self.favorites.is_favorite(selected_anime.id)
            default_download_quality = self._get_default_download_quality()
            download_mode = self._get_download_mode()
            
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
                anime_details=anime_details,
                default_download_quality=default_download_quality,
                download_mode=download_mode,
                download_path=self._get_download_directory(),
                initial_selected=current_idx,
                episodes_progress=episodes_prog
            )
            
            if ep_idx == -1:
                sys.exit(0)
            elif ep_idx is None:
                self.rpc.update_browsing()
                return True
            elif isinstance(ep_idx, tuple) and ep_idx[0] == 'download_current':
                target_idx = ep_idx[1]
                if 0 <= target_idx < len(episodes):
                    self.download_episode_with_defaults(selected_anime, episodes[target_idx])
                continue
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
                
                if action_taken == "watch":
                    auto_next = self.settings.get('auto_next')
                    if auto_next:
                        if current_idx + 1 < len(episodes):
                            current_idx += 1
                            continue
                        else:
                            self.ui.render_message("Info", "No more episodes!", "info")
                            break

                    next_action = self.ui.post_watch_menu(selected_anime.title_en, str(selected_ep.display_num))
                    
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
                elif action_taken == "download":
                    # For downloads, return directly to the episodes list instead of watch navigation.
                    break
                else:
                    break

    def _get_default_download_quality(self):
        return self.settings.get('default_download_quality') or self.settings.get('default_quality') or "1080p"

    def _get_download_mode(self):
        return (self.settings.get('download_mode') or "internal").lower()

    def _get_download_directory(self):
        return self.settings.get('download_directory') or "downloads"

    def _extract_quality_tag(self, quality_name):
        quality_match = re.search(r"\b(\d{3,4}p)\b", quality_name or "")
        return quality_match.group(1) if quality_match else (quality_name or "auto")

    def _pick_default_download_quality_option(self, server_data):
        if isinstance(server_data, dict):
            qualities = server_data.get('Qualities')
            if qualities:
                preferred = self._get_default_download_quality()
                for q in qualities:
                    if preferred in (q.res or q.name or ""):
                        return q
                return qualities[0]
            current_ep_data = server_data.get('CurrentEpisode', {})
        else:
            current_ep_data = server_data

        qualities = [
            QualityOption("1080p", 'FRFhdQ', "info"),
            QualityOption("720p", 'FRLink', "info"),
            QualityOption("480p", 'FRLowQ', "info"),
        ]

        preferred_quality = self._get_default_download_quality()

        for quality in qualities:
            if preferred_quality in quality.name and current_ep_data.get(quality.server_key):
                return quality

        for quality in qualities:
            if current_ep_data.get(quality.server_key):
                return quality

        return None

    def resolve_default_download_target(self, selected_anime, selected_ep, show_loading=False):
        if show_loading:
            server_data = self.ui.run_with_loading(
                "Loading servers...",
                self.api.get_streaming_servers,
                selected_anime.id,
                selected_ep.number,
                selected_anime.type
            )
        else:
            server_data = self.api.get_streaming_servers(selected_anime.id, selected_ep.number, selected_anime.type)

        if not server_data:
            return None, None, "No servers found for this episode."

        selected_quality = self._pick_default_download_quality_option(server_data)
        if not selected_quality:
            return None, None, "No suitable quality found for this episode."

        current_ep_data = server_data.get('CurrentEpisode', {}) if isinstance(server_data, dict) else {}
        direct_url = selected_quality.direct_url or current_ep_data.get(selected_quality.server_key)
        if not direct_url or not direct_url.startswith("http"):
            return None, None, "Failed to resolve direct video stream."

        quality_tag = self._extract_quality_tag(selected_quality.name)
        filename = f"{selected_anime.title_en} - Ep {selected_ep.display_num} [{quality_tag}].mp4"
        return direct_url, filename, None

    def download_episode_with_defaults(self, selected_anime, selected_ep):
        direct_url, filename, error = self.resolve_default_download_target(selected_anime, selected_ep, show_loading=True)

        if error:
            self.ui.render_message("✗ Download Error", error, "error")
            return False

        success = download_file(
            direct_url,
            filename,
            self.ui.console,
            mode=self._get_download_mode(),
            download_dir=self._get_download_directory()
        )

        if success:
            self.history.mark_watched(selected_anime.id, selected_ep.display_num, selected_anime.title_en)

        return success

    def handle_batch_download(self, selected_anime, episodes):
        selected_indices = self.ui.batch_selection_menu(episodes)
        if not selected_indices:
            return

        self.ui.render_timed_message(
            "Batch Download",
            f"Preparing {len(selected_indices)} episode(s) for download...",
            "info",
            duration=1.0
        )
        download_mode = self._get_download_mode()
        download_directory = self._get_download_directory()
        success_count = 0
        failed_count = 0
        
        for idx in selected_indices:
            ep = episodes[idx]
            direct_url, filename, error = self.resolve_default_download_target(selected_anime, ep, show_loading=True)

            if error:
                failed_count += 1
                continue

            success = download_file(
                direct_url,
                filename,
                self.ui.console,
                mode=download_mode,
                download_dir=download_directory
            )
            if success:
                success_count += 1
                self.history.mark_watched(selected_anime.id, ep.display_num, selected_anime.title_en)
            else:
                failed_count += 1
        
        summary_style = "error" if success_count == 0 else "info"
        summary_message = f"Completed: {success_count}"
        if failed_count:
            summary_message += f" | Failed: {failed_count}"

        self.ui.render_timed_message(
            "Batch Download Finished",
            summary_message,
            summary_style,
            duration=1.6
        )

    def handle_quality_selection(self, selected_anime, selected_ep, server_data, start_time=None):
        current_ep_data = server_data.get('CurrentEpisode', {})
        available = server_data.get('Qualities')
        if not available:
            qualities = [
                QualityOption("480p", 'FRLowQ', "info"),
                QualityOption("720p", 'FRLink', "info"),
                QualityOption("1080p", 'FRFhdQ', "info"),
            ]
            available = [q for q in qualities if current_ep_data.get(q.server_key)]
        
        if not available:
            self.ui.render_message(
                "✗ No Links", 
                "No video streams found for this episode.", 
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
        direct_url = getattr(quality, 'direct_url', '') or getattr(quality, 'url', '') or current_ep_data.get(getattr(quality, 'server_key', ''))
        
        if direct_url and direct_url.startswith("http"):
            quality_match = re.search(r"\b(\d{3,4}p)\b", quality.name)
            quality_tag = quality_match.group(1) if quality_match else quality.name
            filename = f"{selected_anime.title_en} - Ep {selected_ep.display_num} [{quality_tag}].mp4"
            
            if action == 'download':
                success = download_file(
                    direct_url,
                    filename,
                    self.ui.console,
                    mode=self._get_download_mode(),
                    download_dir=self._get_download_directory()
                )
                if success:
                    self.history.mark_watched(selected_anime.id, selected_ep.display_num, selected_anime.title_en)
                    return "download"
                return None
            else:
                player_type = self.settings.get('player')
                
                # Determine resume timestamp
                actual_start = 0.0
                if start_time is not None and start_time > 0:
                    actual_start = start_time
                else:
                    ep_prog = self.history.get_episode_progress(selected_anime.id, selected_ep.display_num)
                    if ep_prog and 0 < ep_prog.get('percent', 0) < 90 and ep_prog.get('time_pos', 0) > 10:
                        actual_start = ep_prog['time_pos']

                time_hint = f" • Resuming at {format_seconds(actual_start)}" if (actual_start > 0) else ""
                self.ui.render_now_playing(selected_anime.title_en, f"Episode {selected_ep.display_num}{time_hint}", quality.name)
                
                self.rpc.update_watching(selected_anime.title_en, str(selected_ep.display_num), selected_anime.thumbnail)
                monitor.track_video_play(selected_anime.title_en, str(selected_ep.display_num))
                
                playback_info = self.player.play(
                    direct_url, 
                    f"{selected_anime.title_en} - Ep {selected_ep.display_num} ({quality.name})", 
                    player_type=player_type,
                    start_time=actual_start
                )
                self.ui.clear()
                
                pos = playback_info.get('time_pos', 0.0) if isinstance(playback_info, dict) else 0.0
                dur = playback_info.get('duration', 0.0) if isinstance(playback_info, dict) else 0.0
                pct = playback_info.get('percent', 0.0) if isinstance(playback_info, dict) else 0.0
                self.history.mark_watched(
                    selected_anime.id, 
                    selected_ep.display_num, 
                    selected_anime.title_en,
                    time_pos=pos,
                    duration=dur,
                    percent=pct,
                    poster_url=getattr(selected_anime, 'thumbnail', ''),
                    provider=getattr(self.provider, 'id', '')
                )
                self.rpc.update_selecting_episode(selected_anime.title_en, selected_anime.thumbnail)
                return "watch"
        else:
            self.ui.render_message(
                "✗ Error", 
                "Failed to resolve direct video stream for this quality.", 
                "error"
            )
            return None

    def handle_exit(self):
        self.ui.clear()
        
        panel = Panel(
            Text("👋 Goodbye! See you next time.", justify="center", style="bold white"),
            title=f"[bold {COLOR_TITLE}]Session Ended[/bold {COLOR_TITLE}]",
            box=HEAVY,
            padding=(1, 4),
            border_style=COLOR_BORDER,
            width=min(50, self.ui.console.width - 4)
        )
        
        self.ui.print(Align.center(panel, vertical="middle", height=self.ui.console.height))

    def handle_error(self, e):
        self.ui.clear()
        self.ui.console.print_exception()
        
        panel = Panel(
            Text(f"✗ Unexpected error: {e}", justify="center", style="bold #ff6b6b"),
            title=f"[bold #ff6b6b]Critical Error[/bold #ff6b6b]",
            box=HEAVY,
            padding=(1, 4),
            border_style="#ff6b6b",
            width=min(60, self.ui.console.width - 4)
        )
        
        self.ui.print(Align.center(panel, vertical="middle", height=self.ui.console.height))
        input("\nPress ENTER to exit...")

    def cleanup(self):
        if self._cleaned_up:
            return
        self._cleaned_up = True

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
        show_cursor()


def main():
    home_dir = Path.home()
    db_dir = home_dir / ".ani-cli-arabic" / "database"
    db_dir.mkdir(parents=True, exist_ok=True)
    
    app = AniCliArApp()
    app.run()


if __name__ == "__main__":
    main()
