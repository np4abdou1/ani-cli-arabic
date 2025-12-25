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
from rich.prompt import Confirm

from .version import __version__, APP_VERSION, API_RELEASES_URL, RELEASES_URL
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
                f.write('title ani-cli-arabic Update\n')
                f.write('color 0A\n')
                f.write('echo.\n')
                f.write('echo ========================================\n')
                f.write('echo   Applying Update...\n')
                f.write('echo ========================================\n')
                f.write('echo.\n')
                f.write('echo Waiting for application to close...\n')
                f.write('timeout /t 3 /nobreak >nul\n')
                f.write('echo.\n')
                
                # Delete old backup if exists
                f.write(f'if exist "{backup_path}" (\n')
                f.write(f'    echo Removing old backup...\n')
                f.write(f'    del /f /q "{backup_path}" 2>nul\n')
                f.write(')\n')
                f.write('echo.\n')
                
                # Backup current exe
                f.write(f'echo Backing up current version...\n')
                f.write(f'move /y "{current_exe}" "{backup_path}" >nul 2>&1\n')
                f.write('if errorlevel 1 (\n')
                f.write('    echo ERROR: Failed to backup current exe\n')
                f.write('    pause\n')
                f.write('    exit /b 1\n')
                f.write(')\n')
                f.write('echo Done.\n')
                f.write('echo.\n')
                
                # Move new exe
                f.write(f'echo Installing new version...\n')
                f.write(f'move /y "{new_file_path}" "{current_exe}" >nul 2>&1\n')
                f.write('if errorlevel 1 (\n')
                f.write('    echo ERROR: Failed to install new exe\n')
                f.write('    echo Restoring backup...\n')
                f.write(f'    move /y "{backup_path}" "{current_exe}" >nul 2>&1\n')
                f.write('    pause\n')
                f.write('    exit /b 1\n')
                f.write(')\n')
                f.write('echo Done.\n')
                f.write('echo.\n')
                
                # Verify the new exe exists
                f.write(f'if not exist "{current_exe}" (\n')
                f.write('    echo ERROR: New exe not found after installation!\n')
                f.write('    pause\n')
                f.write('    exit /b 1\n')
                f.write(')\n')
                
                # Change to app directory and launch
                f.write('echo Update successful!\n')
                f.write('echo Starting application...\n')
                f.write('echo.\n')
                f.write(f'cd /D "{current_dir}"\n')
                
                # Use START with /B to run in background and /D for directory
                f.write(f'start "" /B /D "{current_dir}" "{current_exe}"\n')
                f.write('if errorlevel 1 (\n')
                f.write('    echo ERROR: Failed to start application\n')
                f.write('    pause\n')
                f.write('    exit /b 1\n')
                f.write(')\n')
                
                # Wait and cleanup
                f.write('timeout /t 2 /nobreak >nul\n')
                f.write('echo.\n')
                f.write('echo Application started! Cleaning up...\n')
                f.write(f'if exist "{backup_path}" del /f /q "{backup_path}" 2>nul\n')
                f.write('echo.\n')
                f.write('echo Update complete!\n')
                f.write('timeout /t 2 /nobreak >nul\n')
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


def get_installation_type():
    """
    Detect installation type: 'pip', 'executable', or 'source'
    Priority: Check executable first (most reliable), then pip
    """
    # Check if bundled executable (PyInstaller sets sys.frozen)
    if getattr(sys, 'frozen', False):
        return 'executable'
    
    # Check if installed via pip
    try:
        # Method 1: Try importlib.metadata (Python 3.8+)
        try:
            from importlib.metadata import distribution
            distribution('ani-cli-arabic')
            return 'pip'
        except ImportError:
            # Method 2: Fallback to pkg_resources
            import pkg_resources
            pkg_resources.get_distribution('ani-cli-arabic')
            return 'pip'
    except Exception:
        pass
    
    # Running from source (development)
    return 'source'


def get_pypi_latest_version():
    """
    Fetch the latest version from PyPI
    Returns version string or None
    """
    try:
        resp = requests.get('https://pypi.org/pypi/ani-cli-arabic/json', timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data['info']['version']
    except Exception:
        pass
    return None


def check_pip_update(console):
    """
    Check PyPI for updates when installed via pip and auto-update
    """
    try:
        latest_version = get_pypi_latest_version()
        if not latest_version:
            return False
        
        current = parse_version(__version__)
        latest = parse_version(latest_version)
        
        if latest > current:
            msg = Text()
            msg.append("Update Available!\n\n", style="bold yellow")
            msg.append(f"Current: ", style="dim")
            msg.append(f"{__version__}\n", style="cyan")
            msg.append(f"Latest:  ", style="dim")
            msg.append(f"{latest_version}\n\n", style="green bold")
            msg.append("Updating automatically...", style="yellow")
            
            panel = Panel(
                msg,
                title="[bold]PyPI Auto-Update[/bold]",
                border_style="yellow",
                padding=(1, 2)
            )
            console.print()
            console.print(panel)
            console.print()
            
            # Auto-update without asking
            console.print("[cyan]Running: pip install --upgrade ani-cli-arabic[/cyan]\n")
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', '--upgrade', 'ani-cli-arabic'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    console.print("[green]✓ Update successful! Restarting application...[/green]\n")
                    import time
                    time.sleep(2)
                    
                    # Restart the application
                    if sys.platform == 'win32':
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                    else:
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    console.print(f"[red]Update failed: {result.stderr}[/red]\n")
                    console.print("[yellow]Please try manually: pip install --upgrade ani-cli-arabic[/yellow]\n")
                    input("Press ENTER to continue...")
            except Exception as e:
                console.print(f"[red]Update failed: {e}[/red]\n")
                console.print("[yellow]Please try manually: pip install --upgrade ani-cli-arabic[/yellow]\n")
                input("Press ENTER to continue...")
            
            return True
    except Exception:
        pass
    
    return False


def check_executable_update(console):
    """
    Check GitHub releases for executable updates
    """
    try:
        release_data = get_latest_release()
        if not release_data:
            return False
        
        latest_tag = release_data.get('tag_name')
        if not latest_tag:
            return False
        
        current = parse_version(APP_VERSION)
        latest = parse_version(latest_tag)
        
        if latest > current:
            system = platform.system().lower()
            system_name = "Windows" if system == "windows" else "Linux"
            
            msg = Text()
            msg.append("Update Available!\n\n", style="bold yellow")
            msg.append(f"Current: ", style="dim")
            msg.append(f"{__version__}\n", style="cyan")
            msg.append(f"Latest:  ", style="dim")
            msg.append(f"{latest_tag.lstrip('v')}\n", style="green bold")
            msg.append(f"Platform: ", style="dim")
            msg.append(f"{system_name}\n\n", style="cyan")
            msg.append("Downloading and installing update...", style="yellow")
            
            panel = Panel(
                msg,
                title="[bold]Executable Auto-Update[/bold]",
                border_style="yellow",
                padding=(1, 2)
            )
            console.print()
            console.print(panel)
            console.print()
            
            # Get download url
            download_url = get_download_url(release_data)
            if not download_url:
                console.print(f"[red]Could not find {system_name} executable in release[/red]\n")
                input("Press ENTER to continue...")
                return False
            
            # Download the update
            new_file = download_update(download_url, console)
            if not new_file:
                input("Press ENTER to continue...")
                return False
            
            console.print("[green]✓ Download complete[/green]")
            console.print()
            
            # Apply update and restart
            return apply_update_and_restart(new_file, console)
        
    except Exception:
        pass
    
    return False


def check_for_updates(console=None, auto_update=True):
    """
    Check for updates based on installation type.
    - pip: Check PyPI and offer to update via pip
    - executable: Check GitHub releases and offer to download/install
    - source: Check GitHub but don't auto-update
    
    Args:
        console: Rich Console instance
        auto_update: Whether to automatically prompt for update (default True)
    
    Returns:
        True if update was found/applied, False otherwise
    """
    if console is None:
        console = Console()
    
    install_type = get_installation_type()
    
    try:
        if install_type == 'pip':
            return check_pip_update(console)
        elif install_type == 'executable':
            return check_executable_update(console)
        elif install_type == 'source':
            # Running from source - just check for new releases
            release_data = get_latest_release()
            if release_data:
                latest_tag = release_data.get('tag_name', '')
                current = parse_version(__version__)
                latest = parse_version(latest_tag)
                
                if latest > current:
                    msg = Text()
                    msg.append("Update Available!\n\n", style="bold yellow")
                    msg.append(f"Current: ", style="dim")
                    msg.append(f"v{__version__}\n", style="cyan")
                    msg.append(f"Latest:  ", style="dim")
                    msg.append(f"{latest_tag}\n\n", style="green bold")
                    msg.append("Visit: ", style="dim")
                    msg.append(RELEASES_URL, style="cyan underline")
                    
                    panel = Panel(
                        msg,
                        title="[bold]Update Available[/bold]",
                        border_style="yellow",
                        padding=(1, 2)
                    )
                    console.print()
                    console.print(panel)
                    console.print()
                    input("Press ENTER to continue...")
                    return True
    except Exception:
        # Silently fail - don't interrupt user
        pass
    
    return False
