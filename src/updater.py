import sys
import os
import re
import platform
import subprocess
import tempfile
import shutil
import requests
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, DownloadColumn, BarColumn, TransferSpeedColumn, TimeRemainingColumn

from .version import APP_VERSION, API_RELEASES_URL, RELEASES_URL
from .utils import is_bundled


def parse_version(ver_string):
    """
    Parse version string like v1.2.3, v1.2, or v1 into tuple of ints.
    Returns tuple for comparison, e.g. (1, 2, 3)
    """
    ver_string = ver_string.strip().lower()
    if ver_string.startswith('v'):
        ver_string = ver_string[1:]
    
    parts = ver_string.split('.')
    result = []
    for p in parts:
        digits = re.match(r'(\d+)', p)
        if digits:
            result.append(int(digits.group(1)))
    
    while len(result) < 3:
        result.append(0)
    
    return tuple(result[:3])


def get_latest_release():
    """
    Fetch the latest release info from GitHub.
    Returns dict with tag_name and assets or None on failure.
    """
    try:
        resp = requests.get(API_RELEASES_URL, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def get_download_url(release_data):
    """
    Find the correct download URL for the current OS.
    Returns the browser_download_url or None.
    """
    if not release_data or 'assets' not in release_data:
        return None
    
    system = platform.system().lower()
    assets = release_data['assets']
    version = release_data.get('tag_name', '')
    
    # determine which asset to download based on OS
    # format: ani-cli-arabic-{os}-{arch}-{version}.{ext}
    target_pattern = None
    if system == 'windows':
        # prefer non-mpv version for smaller download
        target_pattern = f'ani-cli-arabic-windows-x64-{version}.exe'
    elif system == 'linux':
        target_pattern = f'ani-cli-arabic-linux-x64-{version}'
    else:
        return None
    
    for asset in assets:
        if asset['name'] == target_pattern:
            return asset['browser_download_url']
    
    return None


def download_update(url, console):
    """
    Download the update file to a temporary location.
    Returns path to downloaded file or None on failure.
    """
    try:
        temp_dir = tempfile.gettempdir()
        filename = os.path.basename(url)
        temp_file = os.path.join(temp_dir, filename)
        
        from rich.progress import TextColumn, ProgressColumn
        
        with Progress(
            TextColumn("[cyan]Downloading update..."),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=False
        ) as progress:
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            
            total_size = int(resp.headers.get('content-length', 0))
            task = progress.add_task("download", total=total_size)
            
            with open(temp_file, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))
        
        return temp_file
    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        return None


def apply_update_and_restart(new_file_path, console):
    """
    Replace the current executable with the new one and restart.
    """
    try:
        current_exe = sys.executable
        current_path = Path(current_exe)
        current_dir = current_path.parent
        
        # backup current exe
        backup_path = current_path.with_suffix('.old')
        
        # on windows, we need to use a batch script to replace the running exe
        if platform.system().lower() == 'windows':
            # create update batch script
            batch_script = os.path.join(tempfile.gettempdir(), 'update_ani_cli.bat')
            with open(batch_script, 'w') as f:
                f.write('@echo off\n')
                f.write('echo.\n')
                f.write('echo ========================================\n')
                f.write('echo   Applying Update...\n')
                f.write('echo ========================================\n')
                f.write('echo.\n')
                f.write('timeout /t 2 /nobreak >nul\n')
                f.write(f'if exist "{backup_path}" (\n')
                f.write(f'    del /f /q "{backup_path}" 2>nul\n')
                f.write(')\n')
                f.write(f'move /y "{current_exe}" "{backup_path}" >nul 2>&1\n')
                f.write('if errorlevel 1 (\n')
                f.write('    echo Failed to backup current exe\n')
                f.write('    pause\n')
                f.write('    exit /b 1\n')
                f.write(')\n')
                f.write(f'move /y "{new_file_path}" "{current_exe}" >nul 2>&1\n')
                f.write('if errorlevel 1 (\n')
                f.write('    echo Failed to move new exe\n')
                f.write(f'    move /y "{backup_path}" "{current_exe}" >nul 2>&1\n')
                f.write('    pause\n')
                f.write('    exit /b 1\n')
                f.write(')\n')
                f.write('echo Update successful!\n')
                f.write('echo Starting application...\n')
                f.write('echo.\n')
                f.write(f'cd /d "{current_dir}"\n')
                f.write(f'start "ani-cli-arabic" /d "{current_dir}" "{current_exe}"\n')
                f.write('timeout /t 3 /nobreak >nul\n')
                f.write(f'if exist "{backup_path}" del /f /q "{backup_path}" 2>nul\n')
                f.write('del /f /q "%~f0" 2>nul\n')
            
            # start the batch script in a new window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(
                ['cmd', '/c', batch_script],
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            
            console.print("\n[green]✓ Update will be applied. Restarting in a new window...[/green]\n")
            import time
            time.sleep(0.5)
            sys.exit(0)
        
        else:  # linux
            # create update script
            update_script = os.path.join(tempfile.gettempdir(), 'update_ani_cli.sh')
            with open(update_script, 'w') as f:
                f.write('#!/bin/bash\n')
                f.write('sleep 2\n')
                f.write(f'[ -f "{backup_path}" ] && rm -f "{backup_path}"\n')
                f.write(f'if mv "{current_path}" "{backup_path}"; then\n')
                f.write(f'    if mv "{new_file_path}" "{current_path}"; then\n')
                f.write(f'        chmod +x "{current_path}"\n')
                f.write(f'        cd "{current_dir}"\n')
                f.write(f'        nohup "{current_path}" > /dev/null 2>&1 &\n')
                f.write(f'        sleep 2\n')
                f.write(f'        [ -f "{backup_path}" ] && rm -f "{backup_path}"\n')
                f.write(f'    else\n')
                f.write(f'        mv "{backup_path}" "{current_path}"\n')
                f.write(f'    fi\n')
                f.write(f'fi\n')
                f.write('rm -f "$0"\n')
            
            os.chmod(update_script, 0o755)
            subprocess.Popen(['/bin/bash', update_script])
            console.print("\n[green]✓ Update applied. Restarting...[/green]\n")
            import time
            time.sleep(0.5)
            sys.exit(0)
        
    except Exception as e:
        console.print(f"[red]Failed to apply update: {e}[/red]")
        console.print("[yellow]Please manually replace the executable.[/yellow]")
        return False
    
    return True


def check_for_updates(console=None):
    """
    Check if there's a newer version available and automatically update.
    Only runs when app is bundled as exe.
    Returns True if update was applied, False otherwise.
    """
    if not is_bundled():
        return False
    
    if console is None:
        console = Console()
    
    try:
        # fetch latest release
        release_data = get_latest_release()
        if not release_data:
            return False
        
        latest_tag = release_data.get('tag_name')
        if not latest_tag:
            return False
        
        # compare versions
        current = parse_version(APP_VERSION)
        latest = parse_version(latest_tag)
        
        if latest > current:
            # new version available - show message
            msg = Text()
            msg.append("Update Available!\n\n", style="bold yellow")
            msg.append(f"Current: ", style="dim")
            msg.append(f"{APP_VERSION}\n", style="cyan")
            msg.append(f"Latest:  ", style="dim")
            msg.append(f"{latest_tag}\n\n", style="green bold")
            msg.append("Downloading update automatically...", style="yellow")
            
            panel = Panel(
                msg,
                title="[bold]Auto-Update[/bold]",
                border_style="yellow",
                padding=(1, 2)
            )
            console.print()
            console.print(panel)
            console.print()
            
            # get download url
            download_url = get_download_url(release_data)
            if not download_url:
                console.print("[red]Could not find download for your OS[/red]")
                return False
            
            # download the update
            new_file = download_update(download_url, console)
            if not new_file:
                return False
            
            console.print("[green]✓ Download complete[/green]")
            console.print()
            
            # apply update and restart
            return apply_update_and_restart(new_file, console)
        
    except Exception as e:
        # silently fail on any error - don't interrupt user
        pass
    
    return False
