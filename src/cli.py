import os
import sys
import subprocess
import shutil
import time
import re
from src.api import AnimeAPI
from src.player import PlayerManager
from src.models import QualityOption
from src.history import HistoryManager
from src.version import APP_VERSION
from src.config import MINIMAL_ASCII_ART, GOODBYE_ART, THEMES, POPULAR_GENRES
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

class AniCliWrapper:
    def __init__(self, api, player, history, settings, rpc):
        self.api = api
        self.player = player
        self.history = history
        self.settings_manager = settings
        self.rpc = rpc
        self.fzf_available = shutil.which('fzf') is not None
        self.console = Console()
        
    def get_theme_color(self, key="ascii"):
        t_name = self.settings_manager.get("theme")
        theme = THEMES.get(t_name, THEMES.get("auto", THEMES["blue"]))
        return theme.get(key, "#7eb3d4")

    def _get_rpc_status_text(self):
        if not self.settings_manager.get('discord_rpc'):
             return Text("")
        
        if self.rpc.connected:
             return Text("RPC: Connected", style="green")
        else:
             return Text("")
    
    def _die(self, msg):
        """Exit with error message."""
        print(f"\033[1;31m{msg}\033[0m", file=sys.stderr)
        sys.exit(1)

    def _launcher(self, items, prompt_text, multi=False):
        if not items:
            return []

        if self.fzf_available:
            # fzf mode
            args = ['fzf', '--ansi', '--reverse', '--cycle', '--prompt', f"{prompt_text} > ", '--bind', 'esc:abort,left:abort']
            if multi:
                args.append('-m')
            
            input_str = "\n".join(items)
            
            try:
                result = subprocess.run(
                    args,
                    input=input_str,
                    text=True,
                    encoding='utf-8',
                    stdout=subprocess.PIPE,
                    stderr=None  # Let fzf render UI to terminal
                )
                if result.returncode == 0:
                    out = result.stdout.strip()
                    if not out:
                        return []
                    return out.split('\n')
                return None
            except Exception as e:
                self._die(f"Error running fzf: {e}")
        else:
            print(f"\033[1;36m{prompt_text}\033[0m")
            for i, item in enumerate(items, 1):
                print(f"{i}. {item}")
            
            try:
                print("\nEnter selection (e.g. 1, 1-3) or 'b'/'q' to back: ", end='')
                selection = input().strip()
                
                if selection.lower() in ['b', 'q', 'back']:
                    return None

                files = []
                
                parts = selection.split()
                for part in parts:
                    if '-' in part:
                         try:
                             start, end = map(int, part.split('-'))
                             for idx in range(start, end + 1):
                                 if 1 <= idx <= len(items):
                                     files.append(items[idx-1])
                         except (ValueError, IndexError):
                             pass
                    elif part.isdigit():
                        idx = int(part) - 1
                        if 0 <= idx < len(items):
                            files.append(items[idx])
                return files
            except Exception:
                return []
    
    def get_quality_preference(self, server_data):
        current_ep_data = server_data.get('CurrentEpisode', {})
        qualities = [
            QualityOption("1080p", 'FRFhdQ', "info"),
            QualityOption("720p", 'FRLink', "info"),
            QualityOption("480p", 'FRLowQ', "info"),
        ]
        
        available = []
        for q in qualities:
            if current_ep_data.get(q.server_key):
                available.append(q)
        return available

    def play_video(self, anime, ep, quality_override=None):
        server_data = None
        
        with self.console.status(f"[bold blue]Fetching links for Episode {ep.number}...[/bold blue]", spinner="bouncingBar"):
            server_data = self.api.get_streaming_servers(anime.id, ep.number, anime.type)
            
        if not server_data:
            print("\033[1;31mNo servers found.\033[0m")
            return False

        available = self.get_quality_preference(server_data)
        if not available:
            print("\033[1;31mNo streamable qualities found.\033[0m")
            return False
            
        selected_q = None
        if quality_override:
            for q in available:
                if quality_override.lower() in q.name.lower():
                    selected_q = q
                    break
        
        if not selected_q:
            selected_q = available[0]

        current_ep_data = server_data.get('CurrentEpisode', {})
        server_id = current_ep_data.get(selected_q.server_key)
        
        direct_url = selected_q.direct_url or server_id
        
        if not direct_url or not direct_url.startswith("http"):
            print(f"\033[1;31mFailed to extract direct link for {selected_q.name}\033[0m")
            return False

        print(f"\033[1;34mPlaying episode {ep.number} ({selected_q.name})...\033[0m")
        
        playback_info = self.player.play(direct_url, f"{anime.title_en} - Episode {ep.number}")
        
        pos = playback_info.get('time_pos', 0.0) if isinstance(playback_info, dict) else 0.0
        dur = playback_info.get('duration', 0.0) if isinstance(playback_info, dict) else 0.0
        pct = playback_info.get('percent', 0.0) if isinstance(playback_info, dict) else 0.0
        self.history.mark_watched(
            anime.id, 
            ep.display_num, 
            anime.title_en,
            time_pos=pos,
            duration=dur,
            percent=pct,
            poster_url=getattr(anime, 'thumbnail', ''),
            provider=getattr(self.provider, 'id', '')
        )
        return True

    def _process_anime_list(self, results, title="Select Anime"):
        anime_map = {}
        display_lines = []
        
        # Calculate alignment padding
        max_len = 0
        clean_titles = []
        for res in results:
            t = res.title_en
            if len(t) > 60: t = t[:57] + "..."
            clean_titles.append(t)
            if len(t) > max_len: max_len = len(t)
        
        for idx, res in enumerate(results):
            C_CYAN = "\033[36m"
            C_RESET = "\033[0m"
            C_DIM = "\033[90m"
            C_YELLOW = "\033[33m"
            C_GREEN = "\033[32m"
            
            t_str = clean_titles[idx]
            padding = " " * (max_len - len(t_str) + 3)
            
            # Metadata
            meta = []
            if res.episodes and str(res.episodes) not in ["?", "0"]:
                meta.append(f"{res.episodes} eps")
            
            if res.premiered and str(res.premiered) not in ["0", "N/A", "None", "", "?"]:
                meta.append(f"{res.premiered}")
            
            meta_str = ""
            if meta:
                meta_str = f" {C_DIM}|{C_RESET} ".join(meta)
                meta_str = f"{C_DIM}[{C_RESET} {meta_str} {C_DIM}]{C_RESET}"
            
            score_str = ""
            if res.score and str(res.score) not in ["0", "N/A", "None", ""]:
                 score_str = f"   {C_YELLOW}★ {res.score}{C_RESET}"
            
            line = f"{C_CYAN}{t_str}{C_RESET}{padding}{meta_str}{score_str}"
            display_lines.append(line)
            
            # Map the exact line
            anime_map[line] = res
            
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_line = ansi_escape.sub('', line)
            anime_map[clean_line] = res

        while True:
            selection = self._launcher(display_lines, title)
            if selection is None:
                # Back
                break
            
            if not selection:
                continue

            sel_text = selection[0]
            if sel_text not in anime_map:
                # Try stripping ANSI if direct lookup fails
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                sel_text = ansi_escape.sub('', sel_text)
            
            if sel_text not in anime_map:
                print("\033[1;31mSelection error: Item not found in map.\033[0m")
                continue

            selected_anime = anime_map[sel_text]
            
            # RPC Update
            if self.rpc:
                self.rpc.update_viewing_anime(selected_anime.title_en, selected_anime.thumbnail)

            episodes = []
            with self.console.status("[bold blue]Fetching episodes...[/bold blue]", spinner="bouncingBar"):
                episodes = self.api.get_episodes(selected_anime.id)
                
            if not episodes:
                print("\033[1;31mNo episodes found.\033[0m")
                continue

            ep_map = {}
            ep_lines = []
            for ep in episodes:
                line = f"Episode {ep.number}"
                ep_lines.append(line)
                ep_map[line] = ep
            
            # Loop for Episode Selection
            while True:
                selected_ep_lines = self._launcher(ep_lines, f"Select Episode ({selected_anime.title_en})", multi=True)
                if selected_ep_lines is None:
                    # Back to Anime Selection
                    break
                
                if not selected_ep_lines:
                    continue
                    
                try:
                    queue = [ep_map[line] for line in selected_ep_lines if line in ep_map]
                    if not queue:
                        continue
                except (KeyError, ValueError):
                    continue
                
                current_idx = 0
                current_quality = None
                
                # Playback Loop
                played_idx = 0
                while played_idx < len(queue):
                    ep = queue[played_idx]
                    
                    if self.rpc:
                        self.rpc.update_watching(selected_anime.title_en, ep.number, selected_anime.thumbnail)

                    if not self.play_video(selected_anime, ep, current_quality):
                        pass
                    played_idx += 1
                    
                    # Continue queue
                    if played_idx < len(queue):
                        continue
                        
                    # Interactive Player Menu
                    while True:
                        menu_opts = ["Next", "Replay", "Previous", "Select", "Change Quality", "Quit"]
                        sel = self._launcher(menu_opts, f"Playing episode {ep.number} of {selected_anime.title_en}")
                        
                        if not sel: 
                            break
                            
                        cmd = sel[0]
                        
                        if cmd == "Next":
                            next_ep_num = self._get_next_ep_num(episodes, ep)
                            if next_ep_num:
                                next_ep = next((e for e in episodes if e.number == next_ep_num), None)
                                if next_ep:
                                    ep = next_ep
                                    self.play_video(selected_anime, ep, current_quality)
                            else:
                                print("\033[1;33mNo next episode.\033[0m")
                        
                        elif cmd == "Previous":
                            prev_ep_num = self._get_prev_ep_num(episodes, ep)
                            if prev_ep_num:
                                prev_ep = next((e for e in episodes if e.number == prev_ep_num), None)
                                if prev_ep:
                                    ep = prev_ep
                                    self.play_video(selected_anime, ep, current_quality)
                            else:
                                print("\033[1;33mNo previous episode.\033[0m")

                        elif cmd == "Replay":
                            self.play_video(selected_anime, ep, current_quality)
                        
                        elif cmd == "Select":
                                # Open episode selector again
                                new_sel = self._launcher(ep_lines, "Select Episode")
                                if new_sel:
                                    # Convert selection to ep object
                                    new_ep_line = new_sel[0]
                                    if new_ep_line in ep_map:
                                        ep = ep_map[new_ep_line]
                                        self.play_video(selected_anime, ep, current_quality)
                        
                        elif cmd == "Change Quality":
                            qs = ["1080p", "720p", "480p"]
                            q_sel = self._launcher(qs, "Select Quality")
                            if q_sel:
                                current_quality = q_sel[0]
                                print(f"\033[1;32mQuality set to {current_quality} (will apply on next play)\033[0m")
                                self.play_video(selected_anime, ep, current_quality)
                        
                        elif cmd == "Quit":
                            sys.exit(0)
                    
                    # If we break from "while True" (Back/ESC), we exit the queue loop completely
                    break
                
                # Back to Episode Selection
                continue

    def _print_header(self):
        ascii_color = self.get_theme_color("ascii")
        self.console.print(MINIMAL_ASCII_ART.strip(), style=ascii_color)
        self.console.print(f"  {APP_VERSION} | gh:np4abdou1/ani-cli-arabic", style="dim")

    def run(self, query=None):
        ascii_color = self.get_theme_color("ascii")
        border_color = self.get_theme_color("border")
        
        # Initial Clear
        os.system('cls' if os.name == 'nt' else 'clear') 
        self._print_header()

        while True:
            if '-i' not in sys.argv:
                cols = shutil.get_terminal_size().columns
                if cols >= 80:
                    return "SWITCH_TO_TUI"

            if not query:
                # Show RPC Status
                status_text = self._get_rpc_status_text()
                if status_text.plain:
                    self.console.print(Text("            ") + status_text)
                    self.console.print()
                else:
                    self.console.print() # Spacer if no RPC status
                
                if self.settings_manager.get('show_donation'):
                    donation_markup = "   💖 [bold magenta dim]Support the project:[/bold magenta dim] [link=https://paypal.me/np4abdou][cyan underline dim]Donate via PayPal[/cyan underline dim][/link] ☕"
                    self.console.print(Text.from_markup(donation_markup))
                    self.console.print()
                
                # Show Menu / Prompt
                margin = "   "
                self.console.print(margin + "[cyan]E[/cyan]: Latest Eps  [cyan]M[/cyan]: Movies   [cyan]T[/cyan]: Trending", style="dim")
                self.console.print(margin + "[cyan]P[/cyan]: Popular     [cyan]R[/cyan]: Top Rated [cyan]G[/cyan]: Genres", style="dim")
                self.console.print(margin + "[cyan]S[/cyan]: Studios     [cyan]D[/cyan]: 💖 Donate", style="dim")
                self.console.print()

                # Input
                try:
                    self.console.print(f"  [{border_color}]╭─   Search (or E,M,T,P,R,G,S)[/{border_color}]")
                    self.console.print(f"  [{border_color}]╰─>[/{border_color}] ", end="")
                    query = input().strip()
                except (KeyboardInterrupt, EOFError):
                    print()
                    return 
                
                if query.lower() in ['q', 'quit', 'exit']:
                    return 

            if not query:
                continue

            # Command Handling
            cmd = query.lower()
            query = None # Consume query

            if cmd == 'e':
                with self.console.status("[bold blue]Fetching latest episodes...[/bold blue]", spinner="bouncingBar"):
                    eps = self.api.get_latest_episodes(limit=50)
                if not eps:
                    self.console.print("[red]No recent episodes found.[/red]")
                    continue
                ep_items = [f"EP {str(e['ep_num']).zfill(2)} • {e['title']}" for e in eps]
                sel = self._launcher(ep_items, "Select Latest Episode to Play")
                if sel and sel[0]:
                    sel_idx = ep_items.index(sel[0]) if sel[0] in ep_items else 0
                    chosen_ep = eps[sel_idx]
                    # Fetch details and play
                    with self.console.status(f"[bold blue]Loading {chosen_ep['title']}...[/bold blue]", spinner="bouncingBar"):
                        anime_obj = self.api.get_anime_details(chosen_ep['slug'])
                        all_eps = self.api.get_episodes(chosen_ep['slug'])
                    if anime_obj and all_eps:
                        self._process_episodes(anime_obj, all_eps)
                os.system('cls' if os.name == 'nt' else 'clear')
                self._print_header()
                continue

            if cmd == 'm':
                with self.console.status("[bold blue]Fetching anime movies...[/bold blue]", spinner="bouncingBar"):
                    results = self.api.get_movies(limit=100)
                self.console.print(f"[green]Got {len(results)} movies[/green]")
                self._process_anime_list(results, "Anime Movies")
                os.system('cls' if os.name == 'nt' else 'clear')
                self._print_header()
                continue

            if cmd == 'r':
                with self.console.status("[bold blue]Fetching top-rated masterpieces (9-10)...[/bold blue]", spinner="bouncingBar"):
                    results = self.api.get_top_rated_anime(limit=100, rate_tier="9-10")
                self.console.print(f"[green]Got {len(results)} top-rated results[/green]")
                self._process_anime_list(results, "Top Rated Anime (9-10)")
                os.system('cls' if os.name == 'nt' else 'clear')
                self._print_header()
                continue
            
            if cmd == 't':
                with self.console.status("[bold blue]Fetching trending...[/bold blue]", spinner="bouncingBar"):
                    if self.rpc: self.rpc.update_trending()
                    results = self.api.get_trending_anime(limit=100)
                self.console.print(f"[green]Got {len(results)} trending results[/green]")
                self._process_anime_list(results, "Trending Anime")
                # Clear after return
                os.system('cls' if os.name == 'nt' else 'clear')
                self._print_header()
                continue
                
            if cmd == 'p':
                 with self.console.status("[bold blue]Fetching popular & spotlight...[/bold blue]", spinner="bouncingBar"):
                    results = self.api.get_pinned_anime()
                    if not results:
                        results = self.api.get_trending_anime(limit=100)
                 self.console.print(f"[green]Got {len(results)} popular results[/green]")
                 self._process_anime_list(results, "Popular Anime")
                 os.system('cls' if os.name == 'nt' else 'clear')
                 self._print_header()
                 continue
                 
            if cmd == 'g':
                genre_labels = [f"{g['name_en']} • {g['name_ar']}" for g in POPULAR_GENRES]
                sel = self._launcher(genre_labels, "Select Genre")
                if sel and sel[0]:
                    sel_idx = genre_labels.index(sel[0]) if sel[0] in genre_labels else 0
                    genre_obj = POPULAR_GENRES[sel_idx]
                    with self.console.status(f"[bold blue]Fetching {genre_obj['name_en']} anime...[/bold blue]", spinner="bouncingBar"):
                         results = self.api.get_genre_anime(genre_obj['slug'], limit=100)
                    self.console.print(f"[green]Got {len(results)} results for {genre_obj['name_en']}[/green]")
                    self._process_anime_list(results, f"Genre: {genre_obj['name_en']}")
                
                os.system('cls' if os.name == 'nt' else 'clear')
                self._print_header()
                continue
            
            if cmd == 's':
                studios = [
                    "Toei Animation", "Sunrise", "Madhouse", "Production I.G", "J.C.Staff",
                    "TMS Entertainment", "Studio Pierrot", "Studio Deen", "A-1 Pictures",
                    "Bones", "Kyoto Animation", "MAPPA", "Wit Studio", "ufotable",
                    "White Fox", "David Production", "Shaft", "Trigger", "CloverWorks",
                    "Lerche", "P.A. Works", "CoMix Wave Films", "Gainax", "Tatsunoko Production"
                ]
                studios.sort()
                sel = self._launcher(studios, "Select Studio")
                if sel and sel[0]:
                    studio = sel[0]
                    with self.console.status(f"[bold blue]Fetching {studio} anime...[/bold blue]", spinner="bouncingBar"):
                         results = self.api.get_anime_list("STUDIOS", studio, "SERIES", limit=100)
                    self.console.print(f"[green]Got {len(results)} results for {studio}[/green]")
                    self._process_anime_list(results, f"Studio: {studio}")

                os.system('cls' if os.name == 'nt' else 'clear')
                self._print_header()
                continue
                
            if cmd == 'd':
                import webbrowser
                webbrowser.open("https://paypal.me/np4abdou")
                # Clear and redisplay
                os.system('cls' if os.name == 'nt' else 'clear')
                self._print_header()
                continue

            search_q = cmd

            results = []
            with self.console.status(f"[bold green]Searching for: {search_q}...[/bold green]", spinner="bouncingBar"):
                if self.rpc: self.rpc.update_searching()
                results = self.api.search_anime(search_q)
            
            if not results:
                print(f"\033[1;31mNo results found for '{search_q}'\033[0m")
                continue
            
            self._process_anime_list(results, f"Search: {search_q}")
            
            os.system('cls' if os.name == 'nt' else 'clear')
            self._print_header() 




    def _get_next_ep_num(self, all_episodes, current_ep):
        for i, e in enumerate(all_episodes):
            if e.number == current_ep.number:
                if i + 1 < len(all_episodes):
                    return all_episodes[i+1].number
        return None

    def _get_prev_ep_num(self, all_episodes, current_ep):
        for i, e in enumerate(all_episodes):
            if e.number == current_ep.number:
                if i - 1 >= 0:
                    return all_episodes[i-1].number
        return None

def run_simple_cli(query=None, deps=None):
    if deps:
        cli = AniCliWrapper(deps['api'], deps['player'], deps['history'], deps['settings'], deps['rpc'])
    else:
        # Fallback for old calls (should not happen with new app structure)
        from src.api import AnimeAPI
        from src.player import PlayerManager
        from src.history import HistoryManager
        from src.settings import SettingsManager
        from src.discord_rpc import DiscordRPCManager
        cli = AniCliWrapper(AnimeAPI(), PlayerManager(console=None), HistoryManager(), SettingsManager(), DiscordRPCManager())

    exit_code = 0
    result = None
    try:
        result = cli.run(query)
        if result == "SWITCH_TO_TUI":
            return "SWITCH_TO_TUI"
    except SystemExit as e:
        if isinstance(e.code, int):
            exit_code = e.code
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n\033[1;31mCritical Error: {e}\033[0m")
        input("Press Enter to continue...")
        exit_code = 1
    finally:
        # Check if we are switching modes (no goodbye needed)
        is_switching = result == "SWITCH_TO_TUI"
        
        if not is_switching:
            # Print goodbye art with system accent color (cyan) like ani-cli
            print(f"\033[1;36m{GOODBYE_ART.strip()}\033[0m")
            sys.exit(exit_code)
