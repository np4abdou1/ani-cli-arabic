import sys
import re
import platform
import subprocess
import requests
from pathlib import Path

from .version import __version__, APP_VERSION, API_RELEASES_URL
from .config import COLOR_PROMPT
from .utils import is_bundled


from rich.console import Console
console = Console()

def _print_header(title):
    console.print(f"\n[bold magenta]{title}[/bold magenta]\n")

def _print_info(text):
    console.print(f"  {text}")

def _print_success(text):
    console.print(f"  [green]✓[/green] {text}")

def _print_error(text):
    console.print(f"  [red]✗[/red] {text}")

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
        path_str = Path(__file__).resolve().as_posix()
        
        # System-managed check
        if '/usr/lib/python' in path_str and ('site-packages' in path_str or 'dist-packages' in path_str):
             return 'pkged'
        
        # Check pipx
        if 'pipx' in path_str:
            return 'pip'
        
        if '/.local/lib/python' in path_str or 'site-packages' in path_str or 'dist-packages' in path_str:
            return 'pip'
            
    except Exception:
        pass
    
    try:
        if Path(__file__).resolve().parent.name == 'src':
            if (Path(__file__).resolve().parent.parent / 'main.py').exists():
                return 'source'
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
            sys.stdout.write("\033[2J\033[H")  # Clear screen for better UI
            sys.stdout.flush()
            _print_header("Update Required")
            _print_info(f"Current version: {__version__}  →  Latest version: {latest_version}")
            print()
            _print_info("A mandatory update is available. Please update to continue using the application.")
            print()
            
            # Auto-update without asking
            try:
                pip_cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', 'ani-cli-arabic']
                
                # Safely handle pipx and user installs
                path_str = str(Path(__file__).resolve())
                if 'pipx' in path_str:
                    _print_error("Cannot automatically update a pipx-managed installation.")
                    _print_info("Please execute the following command to update:")
                    _print_info("  pipx upgrade ani-cli-arabic")
                    print()
                    sys.exit(1)
                
                is_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
                if platform.system() != 'Windows' and not is_venv:
                    # System python on Linux/Mac, try using --user first 
                    pip_cmd.append('--user')
                
                _print_info("Downloading and installing the update...")
                result = subprocess.run(
                    pip_cmd,
                    capture_output=True,
                    text=True
                )
                
                # If it fails with PEP 668 internally managed error, retry aggressively with break-system-packages
                if result.returncode != 0 and 'externally-managed-environment' in result.stderr:
                    _print_info("Restricted package environment detected. Re-attempting installation...")
                    # Remove --user if appending break-system-packages for cleaner retry, though both can work.
                    if '--user' in pip_cmd:
                        pip_cmd.remove('--user')
                    pip_cmd.append('--break-system-packages')
                    
                    result = subprocess.run(
                        pip_cmd,
                        capture_output=True,
                        text=True
                    )

                if result.returncode == 0:
                    _print_success("Update installed successfully.")
                    print()
                    _print_info("The application will now safely terminate.")
                    _print_info("Please restart the application to apply the changes.")
                    print()
                    sys.exit(0)
                else:
                    _print_error(f"Automated update failed. (Exit code: {result.returncode})")
                    if "externally-managed-environment" in result.stderr:
                        _print_info("Your system utilizes a restricted Python environment.")
                        _print_info("Please run: pipx upgrade ani-cli-arabic")
                    else:
                        _print_info("Please try installing the update manually: pip install --upgrade ani-cli-arabic")
                    print()
                    _print_error("Error details:")
                    print(result.stderr.strip()[:500])  # print up to 500 chars of error
                    print()
                    sys.exit(1)
            except Exception as e:
                _print_error(f"An unexpected error occurred during the update process: {e}")
                _print_info("Please try installing the update manually: pip install --upgrade ani-cli-arabic")
                print()
                sys.exit(1)
            
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
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
            _print_header("Update Required")
            _print_info(f"Current version: {__version__}  →  Latest version: {latest_tag.lstrip('v')}")
            print()
            _print_error("Standalone executables are no longer supported and cannot be automatically updated.")
            _print_info("Please uninstall this version and reinstall using one of the following methods:")
            _print_info("  - Pip: pip install ani-cli-arabic")
            _print_info("  - AUR: yay -S ani-cli-arabic")
            print()
            sys.exit(1)
        
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
                    sys.stdout.write("\033[2J\033[H")
                    sys.stdout.flush()
                    _print_header("Update Required")
                    _print_info(f"Current version: {current}  →  Latest version: {latest_tag}")
                    print()
                    _print_info("Your installation is managed by a system package manager (e.g., AUR, APT).")
                    _print_info("A mandatory update is available. Please update to continue using the application.")
                    _print_error("Kindly update using your package manager (e.g., yay -Syu ani-cli-arabic).")
                    print()
                    sys.exit(1)
        elif install_type == 'source':
            pass
    except Exception:
        pass
    
    return False
