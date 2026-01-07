import sys
import os
import re
import platform
import subprocess
import tempfile
import time
import requests
from pathlib import Path

from .version import __version__, APP_VERSION, API_RELEASES_URL
from .config import COLOR_PROMPT
from .utils import is_bundled


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

def get_installation_type():
    if is_bundled():
        return 'executable'
    
    # Check for AUR/System installation
    try:
        file_path = Path(__file__).resolve()
        path_str = str(file_path)
        
        # System-managed check
        if '/usr/lib/python' in path_str and ('site-packages' in path_str or 'dist-packages' in path_str):
             return 'pkged'
        
        if '/home/' in path_str and '/.local/lib/python' in path_str:
            return 'pip'
            
    except Exception:
        pass
    
    try:
        file_path = Path(__file__).resolve()
        if file_path.parent.name == 'src':
            project_root = file_path.parent.parent
            if (project_root / 'main.py').exists():
                return 'source'
    except Exception:
        pass
    
    # Fallback to general pip check if not caught above
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
                    input("Press Enter to restart...")
                    
                    # Restart using the entry point command
                    # Determine which command was used to launch
                    if 'ani-cli-ar' in str(sys.argv[0]).lower():
                        cmd = 'ani-cli-ar'
                    else:
                        cmd = 'ani-cli-arabic'
                    
                    # Restart application
                    if platform.system() == 'Windows':
                        subprocess.Popen([cmd], creationflags=subprocess.CREATE_NEW_CONSOLE)
                        sys.exit(0)
                    else:
                        # On Unix, replace the process
                        try:
                            os.execvp(cmd, [cmd] + sys.argv[1:])
                        except FileNotFoundError:
                            subprocess.Popen([sys.executable] + sys.argv)
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
    # Handling legacy executable installations
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
            _print_header("Update Available")
            _print_info(f"Current: {__version__}  →  Latest: {latest_tag.lstrip('v')}")
            print()
            _print_error("Standalone executables are no longer supported.")
            _print_info("Please uninstall this version and reinstall via:")
            _print_info("  - Pip: pip install ani-cli-arabic")
            _print_info("  - AUR: yay -S ani-cli-arabic")
            print()
            input("Press ENTER to continue...")
            return False
        
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
        elif install_type == 'pkged':
            release_data = get_latest_release()
            if release_data:
                latest_tag = release_data.get('tag_name', '').lstrip('v')
                current = __version__
                if parse_version(latest_tag) > parse_version(current):
                    _print_header("Update Available")
                    _print_info(f"Current: {current}  →  Latest: {latest_tag}")
                    _print_info("You installed via a package manager (AUR/System).")
                    _print_info("Please update using your package manager (e.g., yay -Syu).")
                    print()
                    if console:
                        input("Press Enter to continue...")
                    return True
        elif install_type == 'source':
            pass
    except Exception:
        pass
    
    return False
