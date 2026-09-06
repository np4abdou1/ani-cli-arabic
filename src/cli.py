import os
import sys
import subprocess
import shutil
import time
import re
import tempfile
import platform
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from src.version import APP_VERSION
from src.config import DEFAULT_HEADER_ART, GOODBYE_ART, THEMES, POPULAR_GENRES
from src.models import QualityOption, Episode, AnimeResult
from src.providers import ProviderManager
from src.utils import download_file
from src.history import HistoryManager, format_seconds
from src.favorites import FavoritesManager


class AniCliWrapper:
    def __init__(self, api, player, history, settings, rpc, favorites=None):
        self.api = api
        self.player = player
        self.history = history
        self.settings_manager = settings
        self.rpc = rpc
        self.favorites = favorites or FavoritesManager()
        self.fzf_available = shutil.which('fzf') is not None
        self.console = Console()
        self.provider = getattr(self.api, 'name', 'Anime3rb')
        self.autoplay = bool(self.settings_manager.get('auto_next') or False)

    def get_theme_color(self, key: str = "ascii") -> str:
        t_name = self.settings_manager.get("theme")
        theme = THEMES.get(t_name, THEMES.get("auto", THEMES["blue"]))
        return theme.get(key, "#7eb3d4")

    def _get_rpc_status_text(self) -> Text:
        if not self.settings_manager.get('discord_rpc'):
            return Text("")
        if getattr(self.rpc, 'connected', False):
            return Text("RPC: Connected", style="green")
        return Text("")

    def _generate_anime_preview(self, anime: Any) -> str:
        """Generates structured ANSI text for fzf's left preview pane."""
        C_RESET = "\033[0m"
        C_BOLD = "\033[1m"
        C_CYAN = "\033[36m"
        C_YELLOW = "\033[33m"
        C_GREEN = "\033[32m"
        C_MAGENTA = "\033[35m"
        C_DIM = "\033[90m"

        lines = []
        lines.append(f"{C_BOLD}{C_CYAN}{anime.title_en}{C_RESET}")
        title_ar = getattr(anime, 'title_ar', '') or getattr(anime, 'title_romaji', '')
        if title_ar and title_ar != anime.title_en:
            lines.append(f"{C_DIM}{title_ar}{C_RESET}")
        lines.append(f"{C_DIM}{'─' * 46}{C_RESET}")

        score_val = getattr(anime, 'score', 'N/A')
        eps_val = getattr(anime, 'episodes', '?')
        season_val = getattr(anime, 'premiered', 'N/A')
        status_val = getattr(anime, 'status', 'N/A')
        studio_val = getattr(anime, 'creators', '') or getattr(anime, 'studio', 'N/A')
        genres_val = getattr(anime, 'genres', 'N/A')

        lines.append(f"{C_YELLOW}★ Score:{C_RESET} {score_val}    {C_CYAN}Episodes:{C_RESET} {eps_val}")
        lines.append(f"{C_GREEN}Status:{C_RESET} {status_val}    {C_MAGENTA}Season:{C_RESET} {season_val}")
        if studio_val and studio_val != "N/A":
            lines.append(f"{C_CYAN}Studio:{C_RESET} {studio_val}")
        if genres_val and genres_val != "N/A":
            lines.append(f"{C_DIM}Genres:{C_RESET} {genres_val}")

        # Watch history check
        last_ep = self.history.get_last_watched(anime.id)
        if last_ep:
            ep_prog = self.history.get_episode_progress(anime.id, last_ep)
            pct = ep_prog.get('percent', 0)
            bar_len = 16
            filled = int((pct / 100) * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            status_tag = f"{C_GREEN}✓ Completed{C_RESET}" if ep_prog.get('completed') else f"{pct}%"
            lines.append(f"{C_DIM}{'─' * 46}{C_RESET}")
            lines.append(f"{C_BOLD}Watched:{C_RESET} Ep {last_ep} [{C_CYAN}{bar}{C_RESET}] {status_tag}")

        # Favorite status
        is_fav = self.favorites.is_favorite(anime.id)
        if is_fav:
            lines.append(f"{C_MAGENTA}♥ Saved in Favorites{C_RESET}")

        # Synopsis
        synopsis = getattr(anime, 'synopsis', '')
        if synopsis:
            lines.append(f"{C_DIM}{'─' * 46}{C_RESET}")
            lines.append(f"{C_BOLD}Story:{C_RESET}")
            clean_syn = re.sub(r'<[^>]+>', '', synopsis).strip()
            # Wrap nicely to 44 chars
            words = clean_syn.split()
            cur_line = ""
            syn_lines = []
            for w in words:
                if len(cur_line) + len(w) + 1 <= 44:
                    cur_line += (" " if cur_line else "") + w
                else:
                    syn_lines.append(cur_line)
                    cur_line = w
                if len(syn_lines) >= 8:
                    break
            if cur_line and len(syn_lines) < 8:
                syn_lines.append(cur_line)
            for sl in syn_lines:
                lines.append(f"  {sl}")
            if len(words) > 50:
                lines.append(f"  {C_DIM}...{C_RESET}")

        # Keybind hints on bottom of preview
        lines.append(f"{C_DIM}{'─' * 46}{C_RESET}")
        lines.append(f"{C_DIM}[↵ Select] [^D Download] [^F Fav] [Esc Back]{C_RESET}")

        return "\n".join(lines)

    def _generate_episode_preview(self, anime: Any, ep: Any, prog: Dict[str, Any]) -> str:
        """Generates structured ANSI text for episode left preview pane."""
        C_RESET = "\033[0m"
        C_BOLD = "\033[1m"
        C_CYAN = "\033[36m"
        C_YELLOW = "\033[33m"
        C_GREEN = "\033[32m"
        C_MAGENTA = "\033[35m"
        C_DIM = "\033[90m"

        lines = []
        lines.append(f"{C_BOLD}{C_CYAN}{anime.title_en}{C_RESET}")
        lines.append(f"{C_BOLD}Episode {ep.number}{C_RESET} - {ep.title or 'الحلقة ' + str(ep.number)}")
        lines.append(f"{C_DIM}{'─' * 44}{C_RESET}")

        dur = ep.duration or prog.get('duration') or "N/A"
        if isinstance(dur, (int, float)) and dur > 0:
            dur = format_seconds(dur)
        lines.append(f"{C_YELLOW}Duration:{C_RESET} {dur}")

        pct = prog.get('percent', 0)
        t_pos = format_seconds(prog.get('time_pos', 0.0))
        t_dur = format_seconds(prog.get('duration', 0.0))
        bar_len = 18
        filled = int((pct / 100) * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        tag = f"{C_GREEN}Watched{C_RESET}" if prog.get('completed') else (f"{pct}%" if pct > 0 else "Unwatched")
        lines.append(f"{C_BOLD}Progress:{C_RESET} [{C_CYAN}{bar}{C_RESET}] {tag}")
        if pct > 0 and t_dur != "00:00":
            lines.append(f"{C_DIM}Resume at {t_pos} / {t_dur}{C_RESET}")

        lines.append(f"{C_DIM}{'─' * 44}{C_RESET}")
        lines.append(f"{C_BOLD}Actions & Keybinds:{C_RESET}")
        lines.append(f"  {C_GREEN}↵ Enter{C_RESET}   : Play stream")
        lines.append(f"  {C_CYAN}^D / d{C_RESET}    : Download episode")
        lines.append(f"  {C_MAGENTA}^F / f{C_RESET}    : Toggle favorite")
        lines.append(f"  {C_YELLOW}^G / g{C_RESET}    : Jump to episode number")
        lines.append(f"  {C_CYAN}^M / m{C_RESET}    : Batch download episodes")
        lines.append(f"  {C_DIM}Esc / b{C_RESET}   : Back to anime selection")

        return "\n".join(lines)

    def _fzf_launcher(
        self,
        items: List[str],
        prompt_text: str,
        preview_map: Optional[Dict[str, str]] = None,
        multi: bool = False,
        expect_keys: Optional[List[str]] = None
    ) -> Tuple[List[str], str]:
        """
        Native fzf launcher with preview window on left, no full screen, and keybinds.
        """
        if not items:
            return [], ""

        temp_dir = None
        preview_arg = []
        if preview_map:
            temp_dir = tempfile.TemporaryDirectory(prefix="anicli_pv_")
            for idx, key in enumerate(preview_map):
                pv_file = Path(temp_dir.name) / f"{idx}.txt"
                pv_file.write_text(preview_map[key], encoding="utf-8")

            cat_cmd = "type" if platform.system() == "Windows" else "cat"
            preview_arg = [
                f"--preview={cat_cmd} {temp_dir.name}/{{1}}.txt",
                "--preview-window=right:50%:wrap"
            ]

        args = [
            'fzf',
            '--ansi',
            '--reverse',
            '--cycle',
            '--height=85%',
            '--prompt', f"{prompt_text} > ",
            '--bind', 'esc:abort,left:abort'
        ]

        if preview_map:
            args.extend([
                '--delimiter=\t',
                '--with-nth=2..',
                *preview_arg
            ])

        if multi:
            args.append('-m')

        expects = expect_keys or ['ctrl-d', 'ctrl-f', 'ctrl-m', 'ctrl-g', 'enter']
        args.append(f"--expect={','.join(expects)}")

        # Build raw lines for fzf
        if preview_map:
            raw_lines = []
            for idx, itm in enumerate(items):
                raw_lines.append(f"{idx}\t{itm}")
            input_str = "\n".join(raw_lines)
        else:
            input_str = "\n".join(items)

        try:
            result = subprocess.run(
                args,
                input=input_str,
                text=True,
                encoding='utf-8',
                stdout=subprocess.PIPE,
                stderr=None
            )
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                if not lines:
                    return [], ""

                first_line = lines[0].strip()
                if first_line in expects or first_line == "":
                    key_pressed = first_line.lower() if first_line else "enter"
                    raw_selected = lines[1:]
                else:
                    key_pressed = "enter"
                    raw_selected = lines

                selected = []
                for line in raw_selected:
                    line_clean = line.strip()
                    if preview_map and '\t' in line_clean:
                        line_clean = line_clean.split('\t', 1)[1]
                    if line_clean:
                        selected.append(line_clean)
                return selected, key_pressed
            return [], ""
        finally:
            if temp_dir:
                temp_dir.cleanup()

    def _fallback_launcher(
        self,
        items: List[str],
        prompt_text: str,
        preview_map: Optional[Dict[str, str]] = None,
        multi: bool = False
    ) -> Tuple[List[str], str]:
        """Native inline numbered menu when fzf is unavailable."""
        self.console.print(f"\n[bold cyan]─ {prompt_text} ─[/bold cyan]")

        # Print items
        for i, item in enumerate(items, 1):
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_item = ansi_escape.sub('', item)
            self.console.print(f"  [cyan]{i:>2}.[/cyan] {clean_item}")

        self.console.print("[dim]Actions: <num> to select | 'd <num>' download | 'f <num>' favorite | 'm' batch | 'b' back[/dim]")
        try:
            self.console.print("╰─> ", end="")
            choice = input().strip()
        except (KeyboardInterrupt, EOFError):
            return [], "esc"

        if not choice or choice.lower() in ['b', 'back', 'q', 'quit']:
            return [], "esc"

        parts = choice.split()
        if parts[0].lower() in ['d', 'dl', 'download'] and len(parts) > 1 and parts[1].isdigit():
            idx = int(parts[1]) - 1
            if 0 <= idx < len(items):
                return [items[idx]], "ctrl-d"

        if parts[0].lower() in ['f', 'fav', 'favorite'] and len(parts) > 1 and parts[1].isdigit():
            idx = int(parts[1]) - 1
            if 0 <= idx < len(items):
                return [items[idx]], "ctrl-f"

        if parts[0].lower() == 'm':
            return [], "ctrl-m"

        if parts[0].lower() == 'g':
            return [], "ctrl-g"

        selected = []
        for p in parts:
            if '-' in p:
                try:
                    s, e = map(int, p.split('-'))
                    for j in range(s, e + 1):
                        if 1 <= j <= len(items):
                            selected.append(items[j - 1])
                except ValueError:
                    pass
            elif p.isdigit():
                idx = int(p) - 1
                if 0 <= idx < len(items):
                    selected.append(items[idx])
        return selected, "enter"

    def _launcher(
        self,
        items: List[str],
        prompt_text: str,
        preview_map: Optional[Dict[str, str]] = None,
        multi: bool = False
    ) -> Tuple[List[str], str]:
        if self.fzf_available:
            return self._fzf_launcher(items, prompt_text, preview_map=preview_map, multi=multi)
        return self._fallback_launcher(items, prompt_text, preview_map=preview_map, multi=multi)

    def get_quality_preference(self, server_data: Any) -> List[QualityOption]:
        if isinstance(server_data, dict):
            qualities = server_data.get('Qualities')
            if qualities:
                return qualities
            current_ep_data = server_data.get('CurrentEpisode', {})
        else:
            current_ep_data = server_data

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

    def play_video(self, anime: Any, ep: Any, quality_override: Optional[str] = None) -> bool:
        with self.console.status(f"[bold blue]Fetching links for Episode {ep.number}...[/bold blue]", spinner="bouncingBar"):
            server_data = self.api.get_streaming_servers(anime.id, ep.number, anime.type)

        if not server_data:
            self.console.print("\033[1;31mNo servers found.\033[0m")
            return False

        available = self.get_quality_preference(server_data)
        if not available:
            self.console.print("\033[1;31mNo streamable qualities found.\033[0m")
            return False

        selected_q = None
        if quality_override:
            for q in available:
                if quality_override.lower() in getattr(q, 'name', '').lower():
                    selected_q = q
                    break

        if not selected_q:
            default_q = self.settings_manager.get('default_quality') or '1080p'
            for q in available:
                if default_q in getattr(q, 'name', ''):
                    selected_q = q
                    break
            if not selected_q:
                selected_q = available[0]

        direct_url = getattr(selected_q, 'direct_url', None)
        if not direct_url and isinstance(server_data, dict):
            current_ep_data = server_data.get('CurrentEpisode', {})
            direct_url = current_ep_data.get(selected_q.server_key)

        if not direct_url or not direct_url.startswith("http"):
            self.console.print(f"\033[1;31mFailed to resolve direct video link.\033[0m")
            return False

        start_time = 0.0
        ep_prog = self.history.get_episode_progress(anime.id, ep.display_num)
        if ep_prog and 0 < ep_prog.get('percent', 0) < 90 and ep_prog.get('time_pos', 0) > 10:
            start_time = ep_prog['time_pos']
        elif 'vid3rb.com' in direct_url:
            start_time = 5.0

        if self.rpc:
            self.rpc.update_watching(anime.title_en, ep.number, anime.thumbnail)

        playback_info = self.player.play(direct_url, f"{anime.title_en} - Episode {ep.number}", start_time=start_time)

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
            provider=getattr(self.api, 'name', 'Anime3rb')
        )
        return True

    def download_video(self, anime: Any, ep: Any, quality_override: Optional[str] = None) -> bool:
        with self.console.status(f"[bold blue]Resolving download link for Episode {ep.number}...[/bold blue]"):
            server_data = self.api.get_streaming_servers(anime.id, ep.number, anime.type)

        if not server_data:
            self.console.print("[red]No download links found.[/red]")
            return False

        available = self.get_quality_preference(server_data)
        if not available:
            self.console.print("[red]No qualities available for download.[/red]")
            return False

        selected_q = available[0]
        if quality_override:
            for q in available:
                if quality_override.lower() in getattr(q, 'name', '').lower():
                    selected_q = q
                    break

        direct_url = getattr(selected_q, 'direct_url', None)
        if not direct_url and isinstance(server_data, dict):
            current_ep_data = server_data.get('CurrentEpisode', {})
            direct_url = current_ep_data.get(selected_q.server_key)

        if not direct_url or not direct_url.startswith("http"):
            self.console.print("[red]Failed to extract direct download link.[/red]")
            return False

        q_tag = getattr(selected_q, 'name', 'HD')
        filename = f"{anime.title_en} - Ep {ep.display_num} [{q_tag}].mp4"
        mode = self.settings_manager.get('download_mode') or 'internal'
        d_dir = self.settings_manager.get('download_directory') or 'downloads'

        return download_file(direct_url, filename, self.console, mode=mode, download_dir=d_dir)

    def batch_download(self, anime: Any, episodes: List[Any]):
        self.console.print(f"\n[bold cyan]Batch Download: {anime.title_en}[/bold cyan]")
        self.console.print(f"[dim]Total available episodes: 1 to {len(episodes)}[/dim]")
        try:
            prompt = self.console.input("Enter range (e.g. 1-12, 1 3 5) or 'all': ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return

        if not prompt:
            return

        target_eps = []
        if prompt == 'all':
            target_eps = episodes
        else:
            nums = set()
            for part in prompt.split():
                if '-' in part:
                    try:
                        s, e = map(int, part.split('-'))
                        nums.update(range(s, e + 1))
                    except ValueError:
                        pass
                elif part.isdigit():
                    nums.add(int(part))
            target_eps = [e for e in episodes if e.display_num in nums]

        if not target_eps:
            self.console.print("[yellow]No matching episodes specified.[/yellow]")
            return

        self.console.print(f"[green]Starting batch download of {len(target_eps)} episodes...[/green]")
        for idx, ep in enumerate(target_eps, 1):
            self.console.print(f"\n[cyan][{idx}/{len(target_eps)}] Downloading Episode {ep.display_num}...[/cyan]")
            self.download_video(anime, ep)
        self.console.print("\n[bold green]✓ Batch download process finished.[/bold green]")

    def _process_anime_list(self, results: List[Any], title: str = "Select Anime"):
        if not results:
            return

        anime_map: Dict[str, Any] = {}
        display_lines: List[str] = []

        max_len = min(50, max(len(r.title_en) for r in results))

        for idx, res in enumerate(results):
            t_str = res.title_en[:47] + "..." if len(res.title_en) > 50 else res.title_en
            padding = " " * max(1, (max_len - len(t_str) + 2))

            meta = []
            if res.episodes and str(res.episodes) not in ["?", "0"]:
                meta.append(f"{res.episodes} eps")
            if res.premiered and str(res.premiered) not in ["0", "N/A", "None", "", "?"]:
                meta.append(f"{res.premiered}")

            meta_str = f" \033[90m|\033[0m ".join(meta)
            if meta_str:
                meta_str = f"\033[90m[\033[0m {meta_str} \033[90m]\033[0m"

            score_str = ""
            if res.score and str(res.score) not in ["0", "N/A", "None", ""]:
                score_str = f"  \033[33m★ {res.score}\033[0m"

            fav_str = " \033[35m♥\033[0m" if self.favorites.is_favorite(res.id) else ""

            line = f"\033[36m{t_str}\033[0m{padding}{meta_str}{score_str}{fav_str}"
            display_lines.append(line)
            anime_map[line] = res

            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_line = ansi_escape.sub('', line)
            anime_map[clean_line] = res

        while True:
            selected_lines, key = self._launcher(display_lines, title)
            if not selected_lines:
                break

            sel_text = selected_lines[0]
            selected_anime = anime_map.get(sel_text)
            if not selected_anime:
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                clean = ansi_escape.sub('', sel_text)
                selected_anime = anime_map.get(clean)

            if not selected_anime:
                continue

            if key == 'ctrl-f':
                # Toggle favorite
                if self.favorites.is_favorite(selected_anime.id):
                    self.favorites.remove(selected_anime.id)
                    self.console.print(f"[dim]Removed from favorites: {selected_anime.title_en}[/dim]")
                else:
                    self.favorites.add(selected_anime.id, selected_anime.title_en, getattr(selected_anime, 'thumbnail', ''))
                    self.console.print(f"[magenta]♥ Added to favorites: {selected_anime.title_en}[/magenta]")
                time.sleep(0.5)
                continue

            # Fetch detailed anime info and episodes
            with self.console.status(f"[bold blue]Loading episodes for {selected_anime.title_en}...[/bold blue]"):
                detailed = self.api.get_anime_details(selected_anime.id)
                if detailed:
                    selected_anime.score = detailed.score
                    selected_anime.synopsis = detailed.synopsis
                    selected_anime.status = detailed.status
                    selected_anime.premiered = detailed.premiered
                    selected_anime.creators = detailed.creators
                    selected_anime.genres = detailed.genres
                episodes = self.api.get_episodes(selected_anime.id)

            if not episodes:
                self.console.print("[red]No episodes found for this anime.[/red]")
                time.sleep(1)
                continue

            if key == 'ctrl-d':
                # Quick download first or last watched episode
                last_ep_num = self.history.get_last_watched(selected_anime.id) or "1"
                chosen_ep = next((e for e in episodes if str(e.number) == str(last_ep_num)), episodes[0])
                self.download_video(selected_anime, chosen_ep)
                continue

            if key == 'ctrl-m':
                self.batch_download(selected_anime, episodes)
                continue

            self._process_episodes(selected_anime, episodes)

    def _process_episodes(self, anime: Any, episodes: List[Any], initial_idx: int = 0):
        if not episodes:
            return

        last_watched = self.history.get_last_watched(anime.id)

        while True:
            ep_map: Dict[str, Any] = {}
            preview_map: Dict[str, str] = {}
            ep_lines: List[str] = []

            for ep in episodes:
                prog = self.history.get_episode_progress(anime.id, ep.display_num)
                pct = prog.get('percent', 0)
                is_last = str(ep.number) == str(last_watched)

                star_tag = "\033[33m★ Recent\033[0m " if is_last else ""
                prog_tag = f"\033[32m[✓ {pct}%]\033[0m" if prog.get('completed') else (f"\033[36m[{pct}%]\033[0m" if pct > 0 else "")

                line = f"\033[1mEpisode {str(ep.number):>3}\033[0m  {star_tag}{prog_tag}"
                ep_lines.append(line)
                ep_map[line] = ep

                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                clean_line = ansi_escape.sub('', line)
                ep_map[clean_line] = ep

                preview_map[line] = self._generate_episode_preview(anime, ep, prog)

            prompt = f"{anime.title_en} (1-{len(episodes)})"
            selected_lines, key = self._launcher(
                ep_lines,
                prompt,
                preview_map=preview_map,
                multi=True
            )

            if not selected_lines:
                break

            if key == 'ctrl-g':
                # Jump to episode by number
                try:
                    target_str = self.console.input("\n[bold cyan]Jump to Episode #[/bold cyan]: ").strip()
                    target_num = int(target_str)
                    target_ep = next((e for e in episodes if e.display_num == target_num or str(e.number) == target_str), None)
                    if target_ep:
                        self.play_video(anime, target_ep)
                except (ValueError, KeyboardInterrupt, EOFError):
                    pass
                continue

            if key == 'ctrl-m':
                self.batch_download(anime, episodes)
                continue

            if key == 'ctrl-f':
                if self.favorites.is_favorite(anime.id):
                    self.favorites.remove(anime.id)
                    self.console.print(f"[dim]Removed from favorites: {anime.title_en}[/dim]")
                else:
                    self.favorites.add(anime.id, anime.title_en, getattr(anime, 'thumbnail', ''))
                    self.console.print(f"[magenta]♥ Added to favorites: {anime.title_en}[/magenta]")
                time.sleep(0.5)
                continue

            queue = []
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            for line in selected_lines:
                ep_obj = ep_map.get(line) or ep_map.get(ansi_escape.sub('', line))
                if ep_obj:
                    queue.append(ep_obj)

            if not queue:
                continue

            if key == 'ctrl-d':
                # Download queued episodes
                for q_ep in queue:
                    self.download_video(anime, q_ep)
                continue

            # Playback Loop
            played_idx = 0
            current_quality = None

            while played_idx < len(queue):
                ep = queue[played_idx]
                self.play_video(anime, ep, current_quality)
                played_idx += 1

                if played_idx < len(queue):
                    continue

                if self.autoplay:
                    next_ep_num = self._get_next_ep_num(episodes, ep)
                    if next_ep_num:
                        next_ep = next((e for e in episodes if e.number == next_ep_num), None)
                        if next_ep:
                            self.console.print(f"[cyan]Autoplaying Episode {next_ep.number}...[/cyan]")
                            queue = [next_ep]
                            played_idx = 0
                            continue

                # Interactive Player Menu with same full-screen shortcuts
                while True:
                    self.console.print(f"\n[bold cyan]Episode {ep.number} finished.[/bold cyan]")
                    self.console.print("[dim]Actions: [N]ext  [R]eplay  [P]rev  [S]elect  [Q]uality  [D]ownload  [F]av  [B]ack[/dim]")
                    menu_opts = [
                        "Next Episode [N]",
                        "Replay Episode [R]",
                        "Previous Episode [P]",
                        "Select Episode [S]",
                        "Change Quality [Q]",
                        "Download Episode [D]",
                        "Toggle Favorite [F]",
                        "Back to Episodes [B]"
                    ]
                    sel, _ = self._launcher(menu_opts, f"Played Ep {ep.number} of {anime.title_en}")
                    if not sel:
                        break

                    cmd = sel[0]
                    if cmd.startswith("Next"):
                        next_ep_num = self._get_next_ep_num(episodes, ep)
                        if next_ep_num:
                            next_ep = next((e for e in episodes if e.number == next_ep_num), None)
                            if next_ep:
                                ep = next_ep
                                self.play_video(anime, ep, current_quality)
                        else:
                            self.console.print("[yellow]No next episode available.[/yellow]")
                    elif cmd.startswith("Previous"):
                        prev_ep_num = self._get_prev_ep_num(episodes, ep)
                        if prev_ep_num:
                            prev_ep = next((e for e in episodes if e.number == prev_ep_num), None)
                            if prev_ep:
                                ep = prev_ep
                                self.play_video(anime, ep, current_quality)
                        else:
                            self.console.print("[yellow]No previous episode available.[/yellow]")
                    elif cmd.startswith("Replay"):
                        self.play_video(anime, ep, current_quality)
                    elif cmd.startswith("Select"):
                        break
                    elif cmd.startswith("Change"):
                        qs = ["1080p", "720p", "480p"]
                        q_sel, _ = self._launcher(qs, "Select Quality")
                        if q_sel:
                            current_quality = q_sel[0]
                            self.console.print(f"[green]Quality switched to {current_quality}[/green]")
                            self.play_video(anime, ep, current_quality)
                    elif cmd.startswith("Download"):
                        self.download_video(anime, ep, current_quality)
                    elif cmd.startswith("Toggle"):
                        if self.favorites.is_favorite(anime.id):
                            self.favorites.remove(anime.id)
                            self.console.print(f"[dim]Removed from favorites.[/dim]")
                        else:
                            self.favorites.add(anime.id, anime.title_en, getattr(anime, 'thumbnail', ''))
                            self.console.print(f"[magenta]♥ Added to favorites.[/magenta]")
                    elif cmd.startswith("Back"):
                        break
                break

    def show_favorites(self):
        fav_items = self.favorites.get_all()
        if not fav_items:
            self.console.print("\n[yellow]No saved favorites found.[/yellow]")
            time.sleep(1)
            return

        fav_results = []
        for itm in fav_items:
            fav_results.append(AnimeResult(
                id=itm['anime_id'],
                title_en=itm['title'],
                title_ar=itm['title'],
                thumbnail=itm.get('thumbnail', '')
            ))
        self._process_anime_list(fav_results, title="Favorites")

    def show_history(self):
        hist_items = self.history.get_history()
        if not hist_items:
            self.console.print("\n[yellow]No watch history recorded yet.[/yellow]")
            time.sleep(1)
            return

        display_items = []
        item_map = {}
        for itm in hist_items:
            pct = itm.get('percent', 0)
            tag = "\033[32m[✓]\033[0m" if itm.get('completed') else f"\033[36m[{pct}%]\033[0m"
            line = f"{tag} \033[1m{itm['title']}\033[0m \033[90m• Ep {itm['episode']} ({itm['time_str']})\033[0m"
            display_items.append(line)
            item_map[line] = itm

        selected, _ = self._launcher(display_items, "Watch History (Select to Resume)")
        if selected:
            chosen = item_map.get(selected[0])
            if chosen:
                with self.console.status(f"[bold blue]Resuming {chosen['title']}...[/bold blue]"):
                    res = self.api.search_anime(chosen['title'])
                    if res:
                        selected_anime = res[0]
                        eps = self.api.get_episodes(selected_anime.id)
                        if eps:
                            target_ep = next((e for e in eps if str(e.number) == str(chosen['episode'])), eps[0])
                            self.play_video(selected_anime, target_ep)

    def switch_provider(self):
        choices = ProviderManager.get_provider_choices()
        cur_id = ProviderManager.get_active_provider_id()

        labels = []
        p_map = {}
        for cid in choices:
            prov = ProviderManager.get_provider(cid)
            name = getattr(prov, 'name', cid)
            marker = " \033[32m(active)\033[0m" if cid == cur_id else ""
            line = f"{name} \033[90m[{cid}]\033[0m{marker}"
            labels.append(line)
            p_map[line] = cid

        selected, _ = self._launcher(labels, "Select Anime Provider")
        if selected and selected[0] in p_map:
            new_id = p_map[selected[0]]
            ProviderManager.set_active_provider(new_id)
            self.api = ProviderManager.get_provider(new_id)
            self.settings_manager.set("anime_provider", new_id)
            self.provider = getattr(self.api, 'name', new_id)
            self.console.print(f"[green]Active provider switched to: {self.provider}[/green]")
            time.sleep(0.8)

    def toggle_autoplay(self):
        self.autoplay = not self.autoplay
        self.settings_manager.set("auto_next", self.autoplay)
        status_str = "[green]Enabled[/green]" if self.autoplay else "[yellow]Disabled[/yellow]"
        self.console.print(f"\nAutoplay Next Episode is now: {status_str}")
        time.sleep(0.8)

    def _print_header(self):
        title_col = self.get_theme_color("title")
        border_col = self.get_theme_color("border")
        bolt_col = self.get_theme_color("bolt")
        lines = DEFAULT_HEADER_ART.strip().split("\n")
        self.console.print(f"       [bold {bolt_col}]⚡[/bold {bolt_col}]")
        if len(lines) >= 2:
            self.console.print(f"  [bold {title_col}]{lines[0]}[/bold {title_col}]")
            self.console.print(f"  [bold {border_col}]{lines[1]}[/bold {border_col}]")
        else:
            self.console.print(f"  [bold {title_col}]{DEFAULT_HEADER_ART.strip()}[/bold {title_col}]")
        active_prov = getattr(self.api, 'name', 'Anime3rb')
        self.console.print(
            f"  [dim]{APP_VERSION}[/dim] • [cyan]Provider: {active_prov}[/cyan] • [dim]gh:np4abdou1/ani-cli-arabic[/dim]"
        )

    def run(self, query: Optional[str] = None) -> Optional[str]:
        border_color = self.get_theme_color("border")

        # Native startup: print header inline without wiping scrollback
        print()
        self._print_header()

        while True:
            if '-i' not in sys.argv:
                cols = shutil.get_terminal_size().columns
                if cols >= 80:
                    return "SWITCH_TO_TUI"

            if not query:
                rpc_text = self._get_rpc_status_text()
                if rpc_text.plain:
                    self.console.print(Text("  ") + rpc_text)

                margin = "  "
                self.console.print(
                    margin + "[cyan]E[/cyan]: Latest  [cyan]M[/cyan]: Movies   [cyan]T[/cyan]: Trending  [cyan]P[/cyan]: Popular   [cyan]R[/cyan]: Top Rated",
                    style="dim"
                )
                self.console.print(
                    margin + "[cyan]F[/cyan]: Favs    [cyan]H[/cyan]: History  [cyan]G[/cyan]: Genres    [cyan]S[/cyan]: Studios   [cyan]C[/cyan]: Provider",
                    style="dim"
                )
                self.console.print(
                    margin + f"[cyan]A[/cyan]: Autoplay ({'ON' if self.autoplay else 'OFF'})  [cyan]Q[/cyan]: Quit",
                    style="dim"
                )
                print()

                try:
                    self.console.print(f"  [{border_color}]╭─  Search[/{border_color}]")
                    self.console.print(f"  [{border_color}]╰─>[/{border_color}] ", end="")
                    query = input().strip()
                except (KeyboardInterrupt, EOFError):
                    print()
                    return None

                if not query:
                    continue

                if query.lower() in ['q', 'quit', 'exit']:
                    return None

            cmd = query.lower()
            query = None

            if cmd == 'e':
                with self.console.status("[bold blue]Fetching latest episodes...[/bold blue]"):
                    eps = self.api.get_latest_episodes(limit=50)
                if not eps:
                    self.console.print("[red]No recent episodes found.[/red]")
                    continue
                ep_items = [f"EP {str(e['ep_num']).zfill(2)} • {e['title']}" for e in eps]
                sel, _ = self._launcher(ep_items, "Latest Episodes")
                if sel and sel[0]:
                    sel_idx = ep_items.index(sel[0]) if sel[0] in ep_items else 0
                    chosen_ep = eps[sel_idx]
                    with self.console.status(f"[bold blue]Loading {chosen_ep['title']}...[/bold blue]"):
                        anime_obj = self.api.get_anime_details(chosen_ep['slug'])
                        all_eps = self.api.get_episodes(chosen_ep['slug'])
                    if anime_obj and all_eps:
                        self._process_episodes(anime_obj, all_eps)
                self._print_header()
                continue

            if cmd == 'm':
                with self.console.status("[bold blue]Fetching anime movies...[/bold blue]"):
                    results = self.api.get_movies(limit=100)
                self._process_anime_list(results, "Anime Movies")
                self._print_header()
                continue

            if cmd == 't':
                with self.console.status("[bold blue]Fetching trending anime...[/bold blue]"):
                    if self.rpc:
                        self.rpc.update_trending()
                    results = self.api.get_trending_anime(limit=100)
                self._process_anime_list(results, "Trending Anime")
                self._print_header()
                continue

            if cmd == 'p':
                with self.console.status("[bold blue]Fetching popular anime...[/bold blue]"):
                    results = self.api.get_pinned_anime()
                    if not results:
                        results = self.api.get_trending_anime(limit=100)
                self._process_anime_list(results, "Popular Anime")
                self._print_header()
                continue

            if cmd == 'r':
                with self.console.status("[bold blue]Fetching top rated masterpieces...[/bold blue]"):
                    results = self.api.get_top_rated_anime(limit=100, rate_tier="9-10")
                self._process_anime_list(results, "Top Rated Anime")
                self._print_header()
                continue

            if cmd == 'f':
                self.show_favorites()
                self._print_header()
                continue

            if cmd == 'h':
                self.show_history()
                self._print_header()
                continue

            if cmd == 'c':
                self.switch_provider()
                self._print_header()
                continue

            if cmd == 'a':
                self.toggle_autoplay()
                self._print_header()
                continue

            if cmd == 'g':
                genre_labels = [f"{g['name_en']} • {g['name_ar']}" for g in POPULAR_GENRES]
                sel, _ = self._launcher(genre_labels, "Select Genre")
                if sel and sel[0]:
                    sel_idx = genre_labels.index(sel[0]) if sel[0] in genre_labels else 0
                    genre_obj = POPULAR_GENRES[sel_idx]
                    with self.console.status(f"[bold blue]Fetching {genre_obj['name_en']} anime...[/bold blue]"):
                        results = self.api.get_genre_anime(genre_obj['slug'], limit=100)
                    self._process_anime_list(results, f"Genre: {genre_obj['name_en']}")
                self._print_header()
                continue

            if cmd == 's':
                studios = [
                    "Toei Animation", "Sunrise", "Madhouse", "Production I.G", "J.C.Staff",
                    "TMS Entertainment", "Studio Pierrot", "Studio Deen", "A-1 Pictures",
                    "Bones", "Kyoto Animation", "MAPPA", "Wit Studio", "ufotable",
                    "White Fox", "David Production", "Shaft", "Trigger", "CloverWorks"
                ]
                studios.sort()
                sel, _ = self._launcher(studios, "Select Studio")
                if sel and sel[0]:
                    studio = sel[0]
                    with self.console.status(f"[bold blue]Fetching {studio} anime...[/bold blue]"):
                        results = self.api.get_anime_list("STUDIOS", studio, "SERIES", limit=100)
                    self._process_anime_list(results, f"Studio: {studio}")
                self._print_header()
                continue

            search_q = cmd
            results = []
            with self.console.status(f"[bold green]Searching for '{search_q}'...[/bold green]"):
                if self.rpc:
                    self.rpc.update_searching()
                results = self.api.search_anime(search_q)

            if not results:
                self.console.print(f"[red]No results found for '{search_q}'[/red]")
                continue

            self._process_anime_list(results, f"Search: {search_q}")
            self._print_header()

    def _get_next_ep_num(self, all_episodes: List[Any], current_ep: Any) -> Optional[str]:
        for i, e in enumerate(all_episodes):
            if e.number == current_ep.number:
                if i + 1 < len(all_episodes):
                    return all_episodes[i + 1].number
        return None

    def _get_prev_ep_num(self, all_episodes: List[Any], current_ep: Any) -> Optional[str]:
        for i, e in enumerate(all_episodes):
            if e.number == current_ep.number:
                if i - 1 >= 0:
                    return all_episodes[i - 1].number
        return None


def run_simple_cli(query: Optional[str] = None, deps: Optional[Dict[str, Any]] = None) -> Optional[str]:
    if deps:
        cli = AniCliWrapper(
            deps['api'],
            deps['player'],
            deps['history'],
            deps['settings'],
            deps['rpc'],
            favorites=deps.get('favorites')
        )
    else:
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
        is_switching = result == "SWITCH_TO_TUI"
        if not is_switching:
            print(f"\033[1;36m{GOODBYE_ART.strip()}\033[0m")
            sys.exit(exit_code)

