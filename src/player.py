import os
import sys
import time
import shutil
import subprocess
import tempfile
import threading
import socket
import json
from typing import Optional
from .utils import is_bundled
from .logger import logger

class MpvTracker:
    """
    High-performance real-time MPV IPC state tracker.
    Continuously queries and observes playback position, duration, percentage,
    paused state, and completion status.
    """
    def __init__(self, sock_path: str):
        self.sock_path = sock_path
        self.state = {
            'time_pos': 0.0,
            'duration': 0.0,
            'percent': 0.0,
            'paused': False,
            'completed': False
        }
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self):
        s = None
        is_windows = (os.name == 'nt')
        
        # Connect to MPV IPC socket (retry up to 30 times / 3 seconds)
        for _ in range(30):
            if self._stop_event.is_set():
                return
            try:
                if is_windows:
                    s = open(self.sock_path, 'r+b', buffering=0)
                    break
                else:
                    if os.path.exists(self.sock_path):
                        import socket
                        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        s.settimeout(0.5)
                        s.connect(self.sock_path)
                        break
            except Exception:
                pass
            time.sleep(0.1)

        if not s:
            return

        import json

        def send_data(payload: dict):
            try:
                raw = (json.dumps(payload) + "\n").encode('utf-8')
                if is_windows:
                    s.write(raw)
                    s.flush()
                else:
                    s.sendall(raw)
            except Exception:
                pass

        # Register observe_property subscriptions
        for sub_id, prop_name in [
            (1, "time-pos"),
            (2, "duration"),
            (3, "percent-pos"),
            (4, "pause"),
            (5, "eof-reached"),
        ]:
            send_data({"command": ["observe_property", sub_id, prop_name]})

        buffer = ""

        try:
            while not self._stop_event.is_set():
                # 1. Query properties via heartbeat request IDs
                send_data({"command": ["get_property", "time-pos"], "request_id": 101})
                send_data({"command": ["get_property", "duration"], "request_id": 102})
                send_data({"command": ["get_property", "percent-pos"], "request_id": 103})
                send_data({"command": ["get_property", "pause"], "request_id": 104})
                send_data({"command": ["get_property", "eof-reached"], "request_id": 105})

                # 2. Read available incoming responses
                try:
                    if is_windows:
                        chunk = s.read(2048)
                        if not chunk:
                            break
                        chunk_str = chunk.decode('utf-8', errors='ignore')
                    else:
                        chunk = s.recv(4096)
                        if not chunk:
                            break
                        chunk_str = chunk.decode('utf-8', errors='ignore')

                    buffer += chunk_str
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            msg = json.loads(line)
                        except Exception:
                            continue

                        req_id = msg.get("request_id")
                        name = msg.get("name")
                        val = msg.get("data")

                        if val is not None:
                            if req_id == 101 or name == "time-pos":
                                try:
                                    self.state["time_pos"] = round(float(val), 1)
                                except (ValueError, TypeError):
                                    pass
                            elif req_id == 102 or name == "duration":
                                try:
                                    self.state["duration"] = round(float(val), 1)
                                except (ValueError, TypeError):
                                    pass
                            elif req_id == 103 or name == "percent-pos":
                                try:
                                    self.state["percent"] = round(float(val), 1)
                                except (ValueError, TypeError):
                                    pass
                            elif req_id == 104 or name == "pause":
                                self.state["paused"] = bool(val)
                            elif req_id == 105 or name == "eof-reached":
                                if bool(val):
                                    self.state["completed"] = True

                        if msg.get("event") == "end-file" and msg.get("reason") == "eof":
                            self.state["completed"] = True

                except (socket.timeout, TimeoutError):
                    pass
                except Exception:
                    break

                # 3. Calculate derived percentage and completion
                t_pos = self.state["time_pos"]
                t_dur = self.state["duration"]
                t_pct = self.state["percent"]

                if t_pct <= 0 and t_dur > 0 and t_pos > 0:
                    self.state["percent"] = round((t_pos / t_dur) * 100, 1)

                if self.state["percent"] >= 85 or (t_dur > 0 and t_dur - t_pos < 35):
                    self.state["completed"] = True

                time.sleep(0.4)

        finally:
            try:
                s.close()
            except Exception:
                pass

class PlayerManager:
    def __init__(self, rpc_manager=None, console=None):
        self.temp_mpv_path = None
        self.rpc_manager = rpc_manager
        self.console = console

    def get_mpv_path(self) -> Optional[str]:
        if is_bundled():
            exe_name = 'mpv.exe' if os.name == 'nt' else 'mpv'
            bundled_mpv = os.path.join(sys._MEIPASS, 'mpv', exe_name)
            if os.path.exists(bundled_mpv):
                if not self.temp_mpv_path or not os.path.exists(self.temp_mpv_path):
                    temp_dir = tempfile.mkdtemp(prefix='anime_browser_mpv_')
                    self.temp_mpv_path = os.path.join(temp_dir, exe_name)
                    shutil.copy2(bundled_mpv, self.temp_mpv_path)
                    
                    if os.name != 'nt':
                        st = os.stat(self.temp_mpv_path)
                        os.chmod(self.temp_mpv_path, st.st_mode | 0o111)
                        
                return self.temp_mpv_path
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            exe_name = 'mpv.exe' if os.name == 'nt' else 'mpv'
            
            dev_mpv = os.path.join(base_dir, 'mpv', exe_name)
            if os.path.exists(dev_mpv):
                return dev_mpv
            
            local_mpv = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mpv', exe_name)
            if os.path.exists(local_mpv):
                return local_mpv

            if shutil.which('mpv'):
                return 'mpv'
            
            return 'mpv'
        
        return 'mpv'

    def cleanup_temp_mpv(self):
        if self.temp_mpv_path and os.path.exists(self.temp_mpv_path):
            try:
                temp_dir = os.path.dirname(self.temp_mpv_path)
                shutil.rmtree(temp_dir, ignore_errors=True)
            except (OSError, PermissionError):
                pass

    def get_available_players(self) -> dict:
        players = {}
        
        # Check VLC
        vlc_path = shutil.which('vlc')
        if not vlc_path:
            if os.name == 'nt':
                paths = [
                    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
                ]
                for p in paths:
                    if os.path.exists(p):
                        vlc_path = p
                        break
            elif sys.platform == 'darwin':
                paths = [
                    "/Applications/VLC.app/Contents/MacOS/VLC",
                    os.path.expanduser("~/Applications/VLC.app/Contents/MacOS/VLC")
                ]
                for p in paths:
                    if os.path.exists(p):
                        vlc_path = p
                        break
        if vlc_path:
            players['VLC'] = vlc_path

        # Check MPV
        mpv_path = self.get_mpv_path()
        if mpv_path == 'mpv':
            if shutil.which('mpv'):
                 players['MPV'] = 'mpv'
        elif os.path.exists(mpv_path):
            players['MPV'] = mpv_path

        # Check MPC-HC
        mpc_path = shutil.which('mpc-hc64') or shutil.which('mpc-hc')
        if not mpc_path and os.name == 'nt':
            paths = [
                r"C:\Program Files\MPC-HC\mpc-hc64.exe",
                r"C:\Program Files\MPC-HC\mpc-hc.exe",
                r"C:\Program Files (x86)\MPC-HC\mpc-hc.exe",
                r"C:\Program Files\K-Lite Codec Pack\MPC-HC64\mpc-hc64.exe"
            ]
            for p in paths:
                if os.path.exists(p):
                    mpc_path = p
                    break
        if mpc_path:
            players['MPC-HC'] = mpc_path

        return players

    def play(self, url: str, title: str, player_type: str = 'ask', start_time: float = 0.0) -> dict:
        available_players = self.get_available_players()
        default_result = {'time_pos': 0.0, 'duration': 0.0, 'percent': 0.0, 'completed': False}
        
        if not available_players:
            msg = "No video players found on your computer. Please download and install MPV or VLC Media Player."
            if self.console:
                from rich.text import Text
                self.console.print(Text(msg, style="bold red"))
                input("Press Enter to continue...")
            else:
                print(msg, file=sys.stderr)
                input("Press Enter to continue...")
            return default_result

        player_names = list(available_players.keys())
        selected_player = None

        if len(player_names) == 1:
            selected_player = player_names[0]
        else:
            if 'MPV' in available_players and player_type == 'mpv':
                selected_player = 'MPV'
            elif 'VLC' in available_players and player_type == 'vlc':
                selected_player = 'VLC'
            elif self.console:
                from rich.prompt import Prompt
                from rich.panel import Panel
                from rich.text import Text
                from rich.align import Align
                
                options_text = "\n".join([f"[{i+1}] {name}" for i, name in enumerate(player_names)])
                panel = Panel(options_text, title=Text("Select Video Player", style="bold cyan"), border_style="cyan", padding=(1, 4))
                self.console.print()
                self.console.print(Align.center(panel))
                
                choice = Prompt.ask(
                    "Enter the number of the player", 
                    choices=[str(i+1) for i in range(len(player_names))], 
                    default="1", 
                    console=self.console
                )
                selected_player = player_names[int(choice)-1]
            else:
                selected_player = player_names[0]

        try:
            if selected_player == 'VLC':
                return self._play_vlc(url, title, available_players['VLC'], start_time=start_time)
            elif selected_player == 'MPV':
                return self._play_mpv(url, title, available_players['MPV'], start_time=start_time)
            elif selected_player == 'MPC-HC':
                return self._play_mpc(url, title, available_players['MPC-HC'])
        except Exception as e:
            if self.console:
                from rich.text import Text
                self.console.print(Text(f"Error launching player: {str(e)}", style="bold red"))
                input("Press Enter to continue...")
            else:
                print(f"Error launching player: {str(e)}", file=sys.stderr)
                input("Press Enter to continue...")
        return default_result

    def _play_vlc(self, url: str, title: str, vlc_path: str = None, start_time: float = 0.0) -> dict:
        if not vlc_path:
            vlc_path = self.get_available_players().get('VLC')
        
        if not vlc_path:
            raise FileNotFoundError("VLC not found")

        vlc_args = [
            vlc_path,
            '--fullscreen',
            '--play-and-exit',
            '--meta-title', title,
        ]
        if start_time and start_time > 0:
            vlc_args.append(f'--start-time={int(start_time)}')
            
        vlc_args.append(url)
        
        t_start = time.time()
        subprocess.run(
            vlc_args,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        elapsed = time.time() - t_start
        return {'time_pos': start_time + elapsed, 'duration': 0.0, 'percent': 0.0, 'completed': False}

    def _play_mpv(self, url: str, title: str, mpv_path: str = None, start_time: float = 0.0) -> dict:
        if not mpv_path:
            mpv_path = self.get_available_players().get('MPV')
        
        if not mpv_path or (mpv_path != 'mpv' and not os.path.exists(mpv_path)):
            raise FileNotFoundError(f"MPV not found at: {mpv_path}")

        # Determine dynamic referer per provider
        referer = None
        if "vid3rb.com" in url:
            referer = "https://video.vid3rb.com/"
        elif "mediafire.com" in url:
            referer = "https://www.mediafire.com/"
        elif "ok.ru" in url:
            referer = "https://ok.ru/"
        elif "ab-hunter.com" in url or "anslayer.com" in url:
            referer = "https://anslayer.com/"

        # Setup IPC Socket
        is_win = (os.name == 'nt')
        ipc_id = f"ani_mpv_{os.getpid()}_{int(time.time()*1000)}"
        if is_win:
            sock_path = f"\\\\.\\pipe\\{ipc_id}"
        else:
            sock_path = os.path.join(tempfile.gettempdir(), f"{ipc_id}.sock")
            if os.path.exists(sock_path):
                try:
                    os.remove(sock_path)
                except Exception:
                    pass

        # High-performance stream caching & hardware decoding for MPV
        mpv_args = [
            mpv_path,
            '--fullscreen',
            '--force-window=yes',
            '--keep-open=yes',
            '--ontop',
            '--cache=yes',
            '--demuxer-max-bytes=300MiB',
            '--demuxer-max-back-bytes=100MiB',
            '--demuxer-readahead-secs=600',
            '--cache-secs=600',
            '--cache-pause=yes',
            '--cache-pause-wait=3',
            '--cache-pause-initial=no',
            f'--input-ipc-server={sock_path}',
            '--hr-seek=yes',
            '--hr-seek-framedrop=yes',
            '--stream-buffer-size=16MiB',
            '--network-timeout=30',
            '--tls-verify=no',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            '--hwdec=auto-safe',
            '--vo=gpu',
            '--profile=fast',
            '--sub-auto=fuzzy',
            '--slang=ara,ar,eng,en',
            '--alang=jpn,ja,eng,en',
            '--really-quiet',
            '--terminal=no',
            '--msg-level=all=no',
            f'--force-media-title={title}',
        ]
        
        if start_time and start_time > 0:
            mpv_args.append(f'--start={start_time}')
        else:
            mpv_args.append('--start=0')

        if referer:
            mpv_args.append(f'--referrer={referer}')

        mpv_args.append(url)

        from .utils import restore_terminal_for_input, enter_raw_mode_after_input, show_cursor, hide_cursor
        restore_terminal_for_input()
        show_cursor()

        tracker = MpvTracker(sock_path)
        tracker.start()

        logger.log_player("MPV", mpv_args)
        t_start = time.time()
        result = subprocess.run(
            mpv_args,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        duration = time.time() - t_start
        logger.log_player("MPV", mpv_args, exit_code=result.returncode, duration=duration)
        
        tracker.stop()
        enter_raw_mode_after_input()
        hide_cursor()

        if not is_win and os.path.exists(sock_path):
            try:
                os.remove(sock_path)
            except Exception:
                pass

        if result.returncode != 0:
            if self.console:
                from rich.text import Text
                self.console.print(Text("⚠ Stream closed or unreachable. Select another server if playback failed.", style="bold yellow"))
                time.sleep(0.6)

        return tracker.state

    def _play_mpc(self, url: str, title: str, mpc_path: str = None):
        if not mpc_path:
            mpc_path = self.get_available_players().get('MPC-HC')
            
        if not mpc_path:
            raise FileNotFoundError("MPC-HC not found")
            
        mpc_args = [
            mpc_path,
            url,
            '/fullscreen',
            '/play',
            '/close'
        ]
        
        subprocess.run(
            mpc_args,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
