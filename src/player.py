import os
import sys
import time
import shutil
import subprocess
import tempfile
from typing import Optional
from .utils import is_bundled

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
                    
                    # Ensure executable permissions on Linux/macOS
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

            # Check system PATH
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

    def play(self, url: str, title: str, player_type: str = 'mpv'):
        try:
            if player_type == 'vlc':
                self._play_vlc(url, title)
            else:
                self._play_mpv(url, title)

        except FileNotFoundError:
            if self.console:
                from rich.text import Text
                self.console.print(Text(f"{player_type.upper()} executable not found. Please install it or check path.", style="bold red"))
                input("Press Enter to continue...")
            else:
                print(f"{player_type.upper()} executable not found. Please install it or check path.", file=sys.stderr)
                input("Press Enter to continue...")
        except Exception as e:
            if self.console:
                from rich.text import Text
                self.console.print(Text(f"Error launching player: {str(e)}", style="bold red"))
                input("Press Enter to continue...")
            else:
                print(f"Error launching player: {str(e)}", file=sys.stderr)
                input("Press Enter to continue...")

    def _play_vlc(self, url: str, title: str):
        # Check for VLC in common paths if not in PATH
        vlc_path = shutil.which('vlc')
        if not vlc_path:
            if os.name == 'nt':
                # Common Windows paths
                paths = [
                    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
                ]
                for p in paths:
                    if os.path.exists(p):
                        vlc_path = p
                        break
            elif sys.platform == 'darwin':
                # Common macOS paths
                paths = [
                    "/Applications/VLC.app/Contents/MacOS/VLC",
                    os.path.expanduser("~/Applications/VLC.app/Contents/MacOS/VLC")
                ]
                for p in paths:
                    if os.path.exists(p):
                        vlc_path = p
                        break
        
        if not vlc_path:
            raise FileNotFoundError("VLC not found")

        vlc_args = [
            vlc_path,
            '--fullscreen',
            '--play-and-exit',
            '--meta-title', title,
            url
        ]
        
        subprocess.run(
            vlc_args,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def _play_mpv(self, url: str, title: str):
        mpv_path = self.get_mpv_path()
        
        if mpv_path != 'mpv' and not os.path.exists(mpv_path):
            raise FileNotFoundError(f"MPV not found at: {mpv_path}")

        mpv_args = [
            mpv_path,
            '--fullscreen',
            '--fs-screen=0',
            '--keep-open=yes',
            '--ontop',
            '--cache=yes',
            '--cache-pause=yes',
            '--cache-pause-initial=yes',
            '--cache-pause-wait=3',
            '--demuxer-max-bytes=256M',
            '--demuxer-max-back-bytes=128M',
            '--cache-secs=30',
            '--hwdec=auto-safe',
            '--vo=gpu',
            '--profile=gpu-hq',
            '--ytdl',
            '--ytdl-format=bestvideo[height<=?1080]+bestaudio/best',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--sub-auto=fuzzy',
            '--sub-file-paths=subs',
            '--slang=ara,ar,eng,en',
            '--alang=jpn,ja,eng,en',
            '--title=' + title,
            url
        ]
        
        # Remove aggressive options that might cause issues with some drivers/setup
        # '--gpu-api=d3d11' caused issues on some systems, letting MPV choose is safer
        
        # Add force-window to ensure window appears even if audio-only (rare for anime but good safety)
        mpv_args.append('--force-window=yes')

        result = subprocess.run(
            mpv_args,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        
        if result.returncode != 0:
            if self.console:
                from rich.text import Text
                self.console.print(Text(f"MPV exited with error code {result.returncode}", style="bold red"))
                input("Press Enter to continue...")