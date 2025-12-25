import os
import sys
import shutil
import subprocess
import requests
import tempfile
from typing import Optional

class PlayerManager:
    def __init__(self, rpc_manager=None, console=None):
        self.temp_mpv_path = None
        self.rpc_manager = rpc_manager
        self.console = console

    def is_bundled(self):
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    def get_mpv_path(self) -> Optional[str]:
        if self.is_bundled():
            bundled_mpv = os.path.join(sys._MEIPASS, 'mpv', 'mpv.exe')
            if os.path.exists(bundled_mpv):
                if not self.temp_mpv_path or not os.path.exists(self.temp_mpv_path):
                    temp_dir = tempfile.mkdtemp(prefix='anime_browser_mpv_')
                    self.temp_mpv_path = os.path.join(temp_dir, 'mpv.exe')
                    shutil.copy2(bundled_mpv, self.temp_mpv_path)
                return self.temp_mpv_path
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dev_mpv = os.path.join(base_dir, 'mpv', 'mpv.exe')
            if os.path.exists(dev_mpv):
                return dev_mpv
            
            local_mpv = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mpv', 'mpv.exe')
            if os.path.exists(local_mpv):
                return local_mpv

            return 'mpv'
        return 'mpv'

    def cleanup_temp_mpv(self):
        if self.temp_mpv_path and os.path.exists(self.temp_mpv_path):
            try:
                temp_dir = os.path.dirname(self.temp_mpv_path)
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
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
                import time
                time.sleep(2)
        except Exception as e:
            if self.console:
                from rich.text import Text
                self.console.print(Text(f"Error launching player: {str(e)}", style="bold red"))
                import time
                time.sleep(2)

    def _play_vlc(self, url: str, title: str):
        # Check for VLC in common paths if not in PATH
        vlc_path = shutil.which('vlc')
        if not vlc_path:
            # Common Windows paths
            paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
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
            '--force-window=immediate',
            '--ontop',
            '--cache=yes',
            '--demuxer-max-bytes=150M',
            '--demuxer-max-back-bytes=75M',
            '--cache-secs=10',
            '--hwdec=auto',
            '--vo=gpu',
            '--profile=gpu-hq',
            '--video-sync=display-resample',
            '--interpolation',
            '--ytdl',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--title=' + title,
            url
        ]
        
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

                time.sleep(2)