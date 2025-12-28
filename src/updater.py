import sys
import os
import re
import platform
import subprocess
import tempfile
import shutil
import time
import requests
from pathlib import Path

from .version import __version__, APP_VERSION, API_RELEASES_URL, RELEASES_URL
from .utils import is_bundled
from .config import COLOR_PROMPT, COLOR_BORDER


def _get_ansi_color(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:], 16)
    return f'\033[38;2;{r};{g};{b}m'

def _reset_color():
    return '\033[0m'

def _print_header(title):
    color = _get_ansi_color(COLOR_PROMPT)
    reset = _reset_color()
    print(f"\n{color}{title}{reset}\n")

def _print_info(text):
    print(f"  {text}")

def _print_success(text):
    color = _get_ansi_color(COLOR_PROMPT)
    reset = _reset_color()
    print(f"  {color}✓{reset} {text}")

def _print_error(text):
    print(f"  ✗ {text}")

def _format_bytes(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f}TB"

def _format_speed(bytes_per_sec):
    return f"{_format_bytes(bytes_per_sec)}/s"

def _draw_progress_bar(progress, total, width=40):
    if total == 0:
        return "  [" + " " * width + "] 0%"
    filled = int(width * progress / total)
    percent = int(100 * progress / total)
    color = _get_ansi_color(COLOR_PROMPT)
    reset = _reset_color()
    bar = color + "█" * filled + reset + "░" * (width - filled)
    return f"  [{bar}] {percent}%"

def parse_version(ver_string):
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
    try:
        resp = requests.get(API_RELEASES_URL, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def get_download_url(release_data):
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


def download_update(url):
    try:
        temp_dir = tempfile.gettempdir()
        filename = os.path.basename(url)
        temp_file = os.path.join(temp_dir, filename)
        
        _print_info("Downloading update...")
        
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        
        total_size = int(resp.headers.get('content-length', 0))
        downloaded = 0
        start_time = time.time()
        last_update = start_time
        
        with open(temp_file, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Update progress every 0.1 seconds
                    current_time = time.time()
                    if current_time - last_update >= 0.1:
                        elapsed = current_time - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        
                        bar = _draw_progress_bar(downloaded, total_size)
                        info = f"{_format_bytes(downloaded)} / {_format_bytes(total_size)} | {_format_speed(speed)}"
                        
                        # Clear line and print progress
                        print(f"\r{bar} {info}", end='', flush=True)
                        last_update = current_time
        
        # Final progress update
        print(f"\r{_draw_progress_bar(total_size, total_size)} {_format_bytes(total_size)} / {_format_bytes(total_size)}")
        print()
        
        return temp_file
    except Exception as e:
        _print_error(f"Download failed: {e}")
        return None


def apply_update_and_restart(new_file_path):
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
            
            _print_success("Update will be applied. Restarting in a new window...")
            print()
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
            _print_success("Update applied. Restarting...")
            print()
            time.sleep(0.5)
            sys.exit(0)
        
    except Exception as e:
        _print_error(f"Failed to apply update: {e}")
        _print_info("Please manually replace the executable.")
        return False
        return False
    
    return True


def get_installation_type():
    if getattr(sys, 'frozen', False):
        return 'executable'
    
    try:
        file_path = Path(__file__).resolve()
        if file_path.parent.name == 'src':
            project_root = file_path.parent.parent
            if (project_root / 'main.py').exists():
                return 'source'
    except Exception:
        pass
    
    try:
        file_path = Path(__file__).resolve()
        path_str = str(file_path)
        if 'site-packages' in path_str or 'dist-packages' in path_str:
            return 'pip'
    except Exception:
        pass
    
    return 'source'


def get_pypi_latest_version():
    try:
        resp = requests.get('https://pypi.org/pypi/ani-cli-arabic/json', timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data['info']['version']
    except Exception:
        pass
    return None


def check_pip_update():
    try:
        latest_version = get_pypi_latest_version()
        if not latest_version:
            return False
        
        current = parse_version(__version__)
        latest = parse_version(latest_version)
        
        if latest > current:
            _print_header("Update Available")
            _print_info(f"Current: {__version__}  →  Latest: {latest_version}")
            print()
            _print_info("Installing update...")
            print()
            
            # Auto-update without asking
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', '--upgrade', 'ani-cli-arabic'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    _print_success("Update successful! Restarting application...")
                    print()
                    time.sleep(1)
                    
                    # Restart using the entry point command
                    # Determine which command was used to launch
                    script_name = Path(sys.argv[0]).stem if sys.argv else 'ani-cli-arabic'
                    if 'ani-cli-ar' in str(sys.argv[0]).lower():
                        cmd = 'ani-cli-ar'
                    else:
                        cmd = 'ani-cli-arabic'
                    
                    # Restart via subprocess instead of exec (cleaner)
                    if sys.platform == 'win32':
                        subprocess.Popen([cmd], creationflags=subprocess.CREATE_NEW_CONSOLE)
                    else:
                        subprocess.Popen([cmd])
                    
                    sys.exit(0)
                else:
                    _print_error(f"Update failed: {result.stderr}")
                    _print_info("Please try manually: pip install --upgrade ani-cli-arabic")
                    print()
                    input("Press ENTER to continue...")
            except Exception as e:
                _print_error(f"Update failed: {e}")
                _print_info("Please try manually: pip install --upgrade ani-cli-arabic")
                print()
                input("Press ENTER to continue...")
            
            return True
    except Exception:
        pass
    
    return False


def check_executable_update():
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
            
            _print_header("Update Available")
            _print_info(f"Current: {__version__}  →  Latest: {latest_tag.lstrip('v')}")
            _print_info(f"Platform: {system_name}")
            print()
            
            # Get download url
            download_url = get_download_url(release_data)
            if not download_url:
                _print_error(f"Could not find {system_name} executable in release")
                print()
                input("Press ENTER to continue...")
                return False
            
            # Download the update
            new_file = download_update(download_url)
            if not new_file:
                input("Press ENTER to continue...")
                return False
            
            _print_success("Download complete")
            print()
            
            # Apply update and restart
            return apply_update_and_restart(new_file)
        
    except Exception:
        pass
    
    return False


def get_version_status():
    install_type = get_installation_type()
    if install_type != 'source':
        return None
    
    try:
        release_data = get_latest_release()
        pypi_version = get_pypi_latest_version()
        
        if release_data or pypi_version:
            latest_exe_tag = release_data.get('tag_name', 'N/A') if release_data else 'N/A'
            latest_pip_version = pypi_version or 'N/A'
            
            current = parse_version(__version__)
            latest_exe = parse_version(latest_exe_tag) if latest_exe_tag != 'N/A' else (0, 0, 0)
            latest_pip = parse_version(latest_pip_version) if latest_pip_version != 'N/A' else (0, 0, 0)
            
            is_outdated = (latest_exe > current) or (latest_pip > current)
            
            return {
                'current': __version__,
                'latest_exe': latest_exe_tag.lstrip('v') if latest_exe_tag != 'N/A' else 'N/A',
                'latest_pip': latest_pip_version if latest_pip_version != 'N/A' else 'N/A',
                'is_outdated': is_outdated
            }
    except Exception:
        pass
    
    return None


def check_for_updates(console=None, auto_update=True):
    install_type = get_installation_type()
    
    try:
        if install_type == 'pip':
            return check_pip_update()
        elif install_type == 'executable':
            return check_executable_update()
        elif install_type == 'source':
            pass
    except Exception:
        pass
    
    return False
