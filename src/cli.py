"""
ani-cli-arabic CLI Launcher
Fast, native, organic terminal interface with pure fzf and full-screen parity.
Zero details preview split, zero RTL Arabic season glitches.
Interactive action menu on selection: Play, Change Quality, Download, Batch Download.
"""

import os
import sys
import subprocess
import shutil
import time
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from rich.console import Console
from rich.text import Text

from src.version import APP_VERSION
from src.config import DEFAULT_HEADER_ART, GOODBYE_ART, THEMES, POPULAR_GENRES
from src.models import QualityOption, Episode, AnimeResult
from src.providers import ProviderManager
from src.utils import download_file
from src.history import HistoryManager, format_seconds
from src.favorites import FavoritesManager


def clean_season(season_str: Optional[str]) -> str:
    """Removes Arabic RTL characters from season text to prevent terminal alignment glitches."""
    if not season_str:
        return ""
    val = str(season_str).strip()
    if val.upper() in ["0", "N/A", "NONE", "UNKNOWN", "", "?"]:
        return ""
    s = val.replace("خريف", "Fall").replace("ربيع", "Spring").replace("صيف", "Summer").replace("شتاء", "Winter")
    m_year = re.search(r"\b(19\d{2}|20\d{2})\b", s)
    year = m_year.group(0) if m_year else ""
    for term in ["Fall", "Spring", "Summer", "Winter"]:
        if term in s:
            return f"{term} {year}".strip() if year else term
    return year or s


def clean_episodes(ep_str: Optional[str]) -> str:
    """Formats episode count, never displaying 'N/A' or '0'."""
    if not ep_str:
        return ""
    val = str(ep_str).strip()
    if val.upper() in ["?", "0", "N/A", "NONE", "UNKNOWN", ""]:
        return ""
    m = re.search(r"\d+", val)
    if m and int(m.group(0)) > 0:
        return f"{m.group(0)} eps"
    return ""


class AniCliWrapper:
    """Pure native fzf CLI interface for ani-cli-arabic."""

    def __init__(self, api, player, history, settings, rpc):
        self.api = api
        self.player = player
        self.history = history
        self.settings_manager = settings
        self.rpc = rpc
        self.favorites = FavoritesManager()
        self.fzf_available = shutil.which('fzf') is not None
        self.console = Console()
        self.autoplay = bool(self.settings_manager.get("auto_next", False))

    def get_theme_color(self, key: str = "ascii") -> str:
        t_name = self.settings_manager.get("theme", "blue") or "blue"
        theme = THEMES.get(t_name, THEMES.get("auto", THEMES["blue"]))
        return theme.get(key, "#7eb3d4")

    def _get_rpc_status_text(self) -> Text:
        if not self.settings_manager.get('discord_rpc', False):
            return Text("")
        if getattr(self.rpc, 'connected', False):
            return Text("RPC: Connected", style="green")
        return Text("")

    def _launcher(
        self,
        items: List[str],
        prompt_text: str,
        multi: bool = False
    ) -> List[str]:
        """
        Native fzf launcher: pure, fast, organic list selection.
        No preview pane, no terminal split, no key collisions.
        """
        if not items:
            return []

        if not self.fzf_available:
            return self._fallback_launcher(items, prompt_text, multi=multi)

        args = [
            'fzf',
            '--ansi',
            '--reverse',
            '--cycle',
            '--height=85%',
            '--prompt', f"{prompt_text} > ",
            '--bind', 'esc:abort,left:abort'
        ]

        if multi:
            args.append('-m')

        try:
            result = subprocess.run(
                args,
                input="\n".join(items),
                text=True,
                encoding='utf-8',
                stdout=subprocess.PIPE,
                stderr=None,
                check=False
            )
            if result.returncode != 0:
                return []

            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            return lines
        except Exception:
            return self._fallback_launcher(items, prompt_text, multi=multi)

    def _fallback_launcher(
        self,
        items: List[str],
        prompt_text: str,
        multi: bool = False
    ) -> List[str]:
        """Native inline numbered menu when fzf is unavailable."""
        self.console.print(f"\n[bold cyan]─ {prompt_text} ─[/bold cyan]")
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        for i, item in enumerate(items, 1):
            clean_item = ansi_escape.sub('', item)
            self.console.print(f"  [cyan]{i:>2}.[/cyan] {clean_item}")

        try:
            self.console.print("\n[dim]Enter selection number (or 'b' to back):[/dim] ╰─> ", end="")
            choice = input().strip()
        except (KeyboardInterrupt, EOFError):
            return []

        if not choice or choice.lower() in ['b', 'back', 'q', 'quit']:
            return []

        selected = []
        for p in choice.split():
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
        return selected

    def get_quality_preference(self, server_data: Any) -> List[QualityOption]:
        if isinstance(server_data, dict):
            qualities = server_data.get('Qualities')
            if qualities:
                return qualities
            current_ep_data = server_data.get('CurrentEpisode', {})
        else:
            current_ep_data = server_data or {}

        fallback_qualities = [
            QualityOption("1080p", 'FRFhdQ', "info"),
            QualityOption("720p", 'FRLink', "info"),
            QualityOption("480p", 'FRLowQ', "info"),
        ]
        return [q for q in fallback_qualities if current_ep_data.get(q.server_key)]

    def play_video(self, anime: Any, ep: Any, quality_override: Optional[str] = None) -> bool:
        server_data = None
        with self.console.status(f"[bold blue]Fetching servers for Episode {ep.number}...[/bold blue]"):
            server_data = self.api.get_streaming_servers(anime.id, ep.number, getattr(anime, 'type', 'SERIES'))

        if not server_data:
            self.console.print("[bold red]No streaming servers found.[/bold red]")
            time.sleep(1.0)
            return False

        available = self.get_quality_preference(server_data)
        if not available:
            self.console.print("[bold red]No streamable qualities available.[/bold red]")
            time.sleep(1.0)
            return False

        selected_q = None
        if quality_override:
            for q in available:
                if quality_override.lower() in getattr(q, 'name', '').lower():
                    selected_q = q
                    break

        if not selected_q:
            default_q = self.settings_manager.get('default_quality', '1080p') or '1080p'
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
            self.console.print("[bold red]Failed to resolve direct video link.[/bold red]")
            time.sleep(1.0)
            return False

        start_time = 0.0
        ep_prog = self.history.get_episode_progress(anime.id, ep.display_num)
        if ep_prog and 0 < ep_prog.get('percent', 0) < 90 and ep_prog.get('time_pos', 0) > 10:
            start_time = ep_prog['time_pos']
        elif getattr(self.api, 'id', '') == 'anime3rb' or 'vid3rb.com' in direct_url:
            start_time = 5.0

        if self.rpc:
            self.rpc.update_watching(anime.title_en, str(ep.number), getattr(anime, 'thumbnail', ''))

        player_type = self.settings_manager.get('player')
        playback_info = self.player.play(
            direct_url,
            f"{anime.title_en} - Episode {ep.number}",
            player_type=player_type,
            start_time=start_time
        )

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
            server_data = self.api.get_streaming_servers(anime.id, ep.number, getattr(anime, 'type', 'SERIES'))

        if not server_data:
            self.console.print("[red]No download links found.[/red]")
            return False

        available = self.get_quality_preference(server_data)
        if not available:
            self.console.print("[red]No suitable download quality found.[/red]")
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
        mode = self.settings_manager.get('download_mode', 'internal') or 'internal'
        d_dir = self.settings_manager.get('download_directory', 'downloads') or 'downloads'

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

        clean_titles = []
        for res in results:
            t = res.title_en or getattr(res, 'title', 'Unknown')
            if len(t) > 55:
                t = t[:52] + "..."
            clean_titles.append(t)

        max_len = max((len(t) for t in clean_titles), default=30)
        max_len = min(50, max_len)

        for idx, res in enumerate(results):
            t_str = clean_titles[idx]
            padding = " " * max(1, (max_len - len(t_str) + 3))

            meta = []
            ep_clean = clean_episodes(getattr(res, 'episodes', ''))
            if ep_clean:
                meta.append(ep_clean)

            season_clean = clean_season(getattr(res, 'premiered', ''))
            if season_clean:
                meta.append(season_clean)

            meta_str = ""
            if meta:
                meta_inner = " \033[90m|\033[0m ".join(meta)
                meta_str = f"\033[90m[\033[0m {meta_inner} \033[90m]\033[0m"

            score_str = ""
            score = getattr(res, 'score', '')
            if score and str(score) not in ["0", "N/A", "None", "", "?"]:
                score_str = f"  \033[33m★ {score}\033[0m"

            fav_str = " \033[35m♥\033[0m" if self.favorites.is_favorite(res.id) else ""

            line = f"\033[36m{t_str}\033[0m{padding}{meta_str}{score_str}{fav_str}"
            display_lines.append(line)
            anime_map[line] = res

            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_line = ansi_escape.sub('', line)
            anime_map[clean_line] = res

        while True:
            selected_lines = self._launcher(display_lines, title)
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

            self._select_episodes(selected_anime)

    def _select_episodes(self, anime: Any):
        if self.rpc:
            self.rpc.update_viewing_anime(anime.title_en, getattr(anime, 'thumbnail', ''))

        with self.console.status(f"[bold blue]Fetching episodes for {anime.title_en}...[/bold blue]"):
            episodes = self.api.get_episodes(anime.id)

        if not episodes:
            self.console.print("[bold red]No episodes found.[/bold red]")
            time.sleep(1.0)
            return

        last_watched = self.history.get_last_watched(anime.id)

        while True:
            ep_map: Dict[str, Any] = {}
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

            prompt = f"{anime.title_en} (1-{len(episodes)})"
            selected_lines = self._launcher(ep_lines, prompt, multi=True)

            if not selected_lines:
                break

            queue = []
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            for line in selected_lines:
                ep_obj = ep_map.get(line) or ep_map.get(ansi_escape.sub('', line))
                if ep_obj:
                    queue.append(ep_obj)

            if not queue:
                continue

            # Interactive action menu for selected episode(s)
            ep_label = f"Episode {queue[0].display_num}" if len(queue) == 1 else f"{len(queue)} Episodes"
            action_opts = [
                "▶ Play",
                "⚙ Change Quality",
                "📥 Download",
                "📦 Batch Download",
                "♥ Favorite Toggle",
                "← Back"
            ]

            action_sel = self._launcher(action_opts, f"{anime.title_en} • {ep_label}")
            if not action_sel:
                continue

            act = action_sel[0]

            if "Back" in act:
                continue

            if "Favorite" in act:
                if self.favorites.is_favorite(anime.id):
                    self.favorites.remove(anime.id)
                    self.console.print(f"[dim]Removed from favorites: {anime.title_en}[/dim]")
                else:
                    self.favorites.add(anime.id, anime.title_en, getattr(anime, 'thumbnail', ''))
                    self.console.print(f"[magenta]♥ Added to favorites: {anime.title_en}[/magenta]")
                time.sleep(0.5)
                continue

            if "Batch" in act:
                self.batch_download(anime, episodes)
                continue

            if "Download" in act:
                for q_ep in queue:
                    self.download_video(anime, q_ep)
                continue

            current_quality = None
            if "Quality" in act:
                # Fetch available qualities to let user pick
                with self.console.status(f"[bold blue]Resolving stream qualities...[/bold blue]"):
                    s_data = self.api.get_streaming_servers(anime.id, queue[0].number, getattr(anime, 'type', 'SERIES'))
                avail_q = self.get_quality_preference(s_data) if s_data else []
                if avail_q:
                    q_choices = [getattr(q, 'name', 'HD') for q in avail_q]
                    q_sel = self._launcher(q_choices, "Select Stream Quality")
                    if q_sel:
                        current_quality = q_sel[0]
                        sub_act = self._launcher(["▶ Play with " + current_quality, "📥 Download with " + current_quality, "← Back"], "Action")
                        if sub_act and "Download" in sub_act[0]:
                            for q_ep in queue:
                                self.download_video(anime, q_ep, quality_override=current_quality)
                            continue
                        elif not sub_act or "Back" in sub_act[0]:
                            continue
                else:
                    self.console.print("[yellow]Could not pre-fetch quality options. Playing with default...[/yellow]")
                    time.sleep(0.8)

            # Playback Loop
            played_idx = 0

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

                # Interactive post-playback menu
                action_opts = ["▶ Next Episode", "🔁 Replay", "◀ Previous Episode", "📋 Select Episode", "← Back"]
                act_lines = self._launcher(action_opts, f"Episode {ep.number} Finished")
                if act_lines:
                    act_post = act_lines[0]
                    if "Next" in act_post:
                        next_ep_num = self._get_next_ep_num(episodes, ep)
                        if next_ep_num:
                            next_ep = next((e for e in episodes if e.number == next_ep_num), None)
                            if next_ep:
                                queue = [next_ep]
                                played_idx = 0
                                continue
                    elif "Replay" in act_post:
                        queue = [ep]
                        played_idx = 0
                        continue
                    elif "Previous" in act_post:
                        prev_ep_num = self._get_prev_ep_num(episodes, ep)
                        if prev_ep_num:
                            prev_ep = next((e for e in episodes if e.number == prev_ep_num), None)
                            if prev_ep:
                                queue = [prev_ep]
                                played_idx = 0
                                continue
                    elif "Select" in act_post:
                        break
                break

    def _get_next_ep_num(self, episodes: List[Any], current_ep: Any) -> Optional[str]:
        try:
            cur = int(current_ep.number)
            for ep in episodes:
                if int(ep.number) == cur + 1:
                    return str(ep.number)
        except Exception:
            pass
        return None

    def _get_prev_ep_num(self, episodes: List[Any], current_ep: Any) -> Optional[str]:
        try:
            cur = int(current_ep.number)
            if cur > 1:
                for ep in episodes:
                    if int(ep.number) == cur - 1:
                        return str(ep.number)
        except Exception:
            pass
        return None

    def _show_history(self):
        items = self.history.get_history()
        if not items:
            self.console.print("\n[yellow]Watch history is empty.[/yellow]")
            time.sleep(1.0)
            return

        lines = []
        map_h = {}
        for h in items:
            t = h.get('title', 'Unknown')
            ep_n = h.get('last_episode', '?')
            pct = h.get('percent', 0)
            pct_str = f"[✓ {pct}%]" if pct >= 90 else (f"[{pct}%]" if pct > 0 else "")
            line = f"\033[36m{t[:50]}\033[0m  \033[33mEp {ep_n}\033[0m  \033[32m{pct_str}\033[0m"
            lines.append(line)
            map_h[line] = h

            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_line = ansi_escape.sub('', line)
            map_h[clean_line] = h

        sel = self._launcher(lines, "Watch History")
        if sel:
            chosen = map_h.get(sel[0]) or map_h.get(re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', sel[0]))
            if chosen:
                mock_anime = AnimeResult(
                    id=chosen.get('anime_id', ''),
                    title_en=chosen.get('title', ''),
                    title_jp='',
                    type='SERIES',
                    episodes='',
                    status='',
                    genres='',
                    mal_id='0',
                    relation_id='',
                    score='',
                    rank='',
                    popularity='',
                    rating='',
                    premiered='',
                    creators='',
                    duration='',
                    thumbnail=chosen.get('poster_url', '')
                )
                self._select_episodes(mock_anime)

    def _show_favorites(self):
        favs = self.favorites.get_favorites()
        if not favs:
            self.console.print("\n[yellow]No favorite anime saved yet.[/yellow]")
            time.sleep(1.0)
            return

        lines = []
        map_f = {}
        for f in favs:
            t = f.get('title', 'Unknown')
            line = f"\033[35m♥\033[0m \033[36m{t[:55]}\033[0m"
            lines.append(line)
            map_f[line] = f

            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_line = ansi_escape.sub('', line)
            map_f[clean_line] = f

        sel = self._launcher(lines, "Favorites")
        if sel:
            chosen = map_f.get(sel[0]) or map_f.get(re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', sel[0]))
            if chosen:
                mock_anime = AnimeResult(
                    id=chosen.get('id', ''),
                    title_en=chosen.get('title', ''),
                    title_jp='',
                    type='SERIES',
                    episodes='',
                    status='',
                    genres='',
                    mal_id='0',
                    relation_id='',
                    score='',
                    rank='',
                    popularity='',
                    rating='',
                    premiered='',
                    creators='',
                    duration='',
                    thumbnail=chosen.get('thumbnail', '')
                )
                self._select_episodes(mock_anime)

    def _switch_provider(self):
        provs = ProviderManager.get_available_providers()
        p_lines = [f"\033[1m{p['id']}\033[0m: {p['name']} ({p['description']})" for p in provs]
        sel = self._launcher(p_lines, "Select Provider")
        if sel:
            p_id = sel[0].split(":")[0].strip()
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            p_id = ansi_escape.sub('', p_id)
            ProviderManager.set_active_provider(p_id)
            self.api = ProviderManager.get_provider(p_id)
            self.settings_manager.set("anime_provider", p_id)
            self.console.print(f"\n[green]Switched active provider to: {self.api.name}[/green]")
            time.sleep(0.8)

    def _toggle_autoplay(self):
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
                if eps:
                    animes = [
                        AnimeResult(
                            id=e.url.split('/')[-2] if '/episode/' in e.url else e.url,
                            title_en=e.title or f"Episode {e.number}",
                            title_jp='',
                            type='SERIES',
                            episodes='',
                            status='',
                            genres='',
                            mal_id='0',
                            relation_id='',
                            score='',
                            rank='',
                            popularity='',
                            rating='',
                            premiered='',
                            creators='',
                            duration=e.duration,
                            thumbnail=e.thumbnail
                        ) for e in eps
                    ]
                    self._process_anime_list(animes, "Latest Episodes")
                continue

            if cmd == 'm':
                with self.console.status("[bold blue]Fetching movies...[/bold blue]"):
                    movies = self.api.get_movies(limit=40)
                if movies:
                    self._process_anime_list(movies, "Anime Movies")
                continue

            if cmd == 't':
                with self.console.status("[bold blue]Fetching trending anime...[/bold blue]"):
                    trending = self.api.get_trending_anime(limit=40)
                if trending:
                    self._process_anime_list(trending, "Trending Anime")
                continue

            if cmd == 'p':
                with self.console.status("[bold blue]Fetching popular anime...[/bold blue]"):
                    pinned = self.api.get_pinned_anime(limit=40)
                if pinned:
                    self._process_anime_list(pinned, "Popular Anime")
                continue

            if cmd == 'r':
                with self.console.status("[bold blue]Fetching top rated anime...[/bold blue]"):
                    top = self.api.get_top_rated_anime(limit=40)
                if top:
                    self._process_anime_list(top, "Top Rated Anime")
                continue

            if cmd == 'f':
                self._show_favorites()
                continue

            if cmd == 'h':
                self._show_history()
                continue

            if cmd == 'a':
                self._toggle_autoplay()
                continue

            if cmd == 'c':
                self._switch_provider()
                continue

            if cmd == 'g':
                genres = POPULAR_GENRES
                sel_g = self._launcher(genres, "Select Genre")
                if sel_g:
                    g_slug = sel_g[0].lower().replace(" ", "-")
                    with self.console.status(f"[bold blue]Fetching {sel_g[0]} anime...[/bold blue]"):
                        g_results = self.api.get_genre_anime(g_slug, limit=40)
                    if g_results:
                        self._process_anime_list(g_results, f"Genre: {sel_g[0]}")
                continue

            if cmd == 's':
                from src.config import POPULAR_STUDIOS_MAP
                studios = list(POPULAR_STUDIOS_MAP.keys())
                sel_s = self._launcher(studios, "Select Studio")
                if sel_s:
                    s_name = sel_s[0]
                    with self.console.status(f"[bold blue]Fetching anime from {s_name}...[/bold blue]"):
                        s_results = self.api.get_studio_anime(s_name, limit=40)
                    if s_results:
                        self._process_anime_list(s_results, f"Studio: {s_name}")
                continue

            # Standard Search Query
            with self.console.status(f"[bold blue]Searching for '{cmd}'...[/bold blue]"):
                results = self.api.search_anime(cmd)

            if not results:
                self.console.print(f"[yellow]No anime found matching '{cmd}'.[/yellow]")
                time.sleep(1.0)
                continue

            self._process_anime_list(results, f"Results for '{cmd}'")


def run_simple_cli(query: Optional[str] = None, deps: Optional[Dict[str, Any]] = None):
    """Entry point for standalone simple CLI runner."""
    from src.providers import ProviderManager
    from src.player import PlayerManager
    from src.history import HistoryManager
    from src.settings import SettingsManager
    from src.discord_rpc import DiscordRPCManager

    if deps:
        api = deps.get('api') or ProviderManager.get_provider()
        player = deps.get('player') or PlayerManager()
        history = deps.get('history') or HistoryManager()
        settings = deps.get('settings') or SettingsManager()
        rpc = deps.get('rpc') or DiscordRPCManager()
    else:
        api = ProviderManager.get_provider()
        settings = SettingsManager()
        rpc = DiscordRPCManager()
        player = PlayerManager(rpc_manager=rpc)
        history = HistoryManager()

    wrapper = AniCliWrapper(api, player, history, settings, rpc)
    return wrapper.run(query)
