"""
Auto-updater for ani-cli-arabic across platforms and package managers.
Supports PyPI (pip/pipx), Arch Linux (AUR yay/paru), macOS (Homebrew),
Windows (winget/scoop/standalone binary), and direct GitHub releases.
"""

import sys
import shutil
import platform
import subprocess
import requests
from pathlib import Path
from typing import Optional, Dict, Any

from .version import __version__, parse_version, API_RELEASES_URL
from .utils import is_bundled
from rich.console import Console

console = Console()


def get_latest_pypi_version() -> Optional[str]:
    try:
        resp = requests.get("https://pypi.org/pypi/ani-cli-arabic/json", timeout=6)
        if resp.status_code == 200:
            return resp.json().get("info", {}).get("version")
    except Exception:
        pass
    return None


def get_latest_github_release() -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(API_RELEASES_URL, timeout=6)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def detect_install_method() -> str:
    """
    Detects how the application was installed on the user's system:
    - 'aur': Arch Linux package (managed by pacman/yay/paru)
    - 'brew': Homebrew package
    - 'pipx': Isolated pipx installation
    - 'pip': Standard pip installation
    - 'executable': Bundled standalone binary (PyInstaller)
    - 'source': Running from local git/source checkout
    """
    if is_bundled():
        return "executable"

    try:
        path_str = Path(__file__).resolve().as_posix()

        # Check if managed by Arch pacman / AUR
        if platform.system() == "Linux" and "/usr/lib/python" in path_str:
            try:
                res = subprocess.run(["pacman", "-Q", "ani-cli-arabic"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res.returncode == 0:
                    return "aur"
            except Exception:
                pass
            return "system_package"

        # Check Homebrew
        if "Cellar/ani-cli-arabic" in path_str or "homebrew" in path_str:
            return "brew"

        # Check pipx
        if "pipx" in path_str or "pipx" in sys.prefix:
            return "pipx"

        # Check standard pip
        if "site-packages" in path_str or "dist-packages" in path_str:
            return "pip"

        # Check local source tree
        if Path(__file__).resolve().parent.name == "src":
            if (Path(__file__).resolve().parent.parent / "main.py").exists():
                return "source"
    except Exception:
        pass

    return "pip"


def update_aur(latest_ver: str) -> bool:
    console.print(f"\n[cyan]Update available: v{__version__} → v{latest_ver}[/cyan]")
    console.print("[dim]Detected Arch Linux package (AUR).[/dim]\n")

    # AUR helpers do NOT use sudo to invoke; they build as user and prompt for sudo internally
    helpers = [
        ("yay", ["yay", "-S", "--noconfirm", "ani-cli-arabic"]),
        ("paru", ["paru", "-S", "--noconfirm", "ani-cli-arabic"]),
        ("pamac", ["pamac", "upgrade", "--no-confirm", "ani-cli-arabic"])
    ]

    for name, cmd in helpers:
        if shutil.which(name):
            console.print(f"[cyan]Executing: {' '.join(cmd)}[/cyan]")
            try:
                res = subprocess.run(cmd)
                if res.returncode == 0:
                    console.print("[green]✓ Updated successfully via " + name + ".[/green]")
                    console.print("Please restart the application.")
                    sys.exit(0)
            except Exception as e:
                console.print(f"[yellow]Warning: {name} failed: {e}[/yellow]")

    console.print("[yellow]No supported AUR helper found (yay/paru/pamac).[/yellow]")
    console.print("Please update using your preferred AUR tool:")
    console.print("  yay -S ani-cli-arabic")
    console.print("  paru -S ani-cli-arabic\n")
    return False


def update_brew(latest_ver: str) -> bool:
    console.print(f"\n[cyan]Update available: v{__version__} → v{latest_ver}[/cyan]")
    console.print("[dim]Updating via Homebrew...[/dim]\n")
    try:
        res = subprocess.run(["brew", "upgrade", "ani-cli-arabic"])
        if res.returncode == 0:
            console.print("[green]✓ Updated successfully via Homebrew.[/green]")
            sys.exit(0)
    except Exception as e:
        console.print(f"[red]Homebrew upgrade error: {e}[/red]")
    return False


def update_pipx(latest_ver: str) -> bool:
    console.print(f"\n[cyan]Update available: v{__version__} → v{latest_ver}[/cyan]")
    console.print("[dim]Updating via pipx...[/dim]\n")
    try:
        res = subprocess.run(["pipx", "upgrade", "ani-cli-arabic"])
        if res.returncode == 0:
            console.print("[green]✓ Updated successfully via pipx.[/green]")
            sys.exit(0)
    except Exception as e:
        console.print(f"[red]pipx upgrade error: {e}[/red]")
    return False


def update_pip(latest_ver: str) -> bool:
    console.print(f"\n[cyan]Update available: v{__version__} → v{latest_ver}[/cyan]")
    console.print("[dim]Downloading update from PyPI...[/dim]\n")

    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir", "ani-cli-arabic"]
    is_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if platform.system() != "Windows" and not is_venv:
        cmd.append("--user")

    res = subprocess.run(cmd, capture_output=True, text=True)

    # Handle PEP 668 (externally-managed-environment)
    if res.returncode != 0 and "externally-managed-environment" in res.stderr:
        console.print("[dim]System-managed Python environment detected; retrying with override...[/dim]")
        if "--user" in cmd:
            cmd.remove("--user")
        cmd.append("--break-system-packages")
        res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0:
        console.print(f"[green]✓ Successfully updated to v{latest_ver}.[/green]")
        console.print("Please restart the application.")
        sys.exit(0)

    console.print(f"[red]Update failed: {res.stderr.strip() or 'Unknown error'}[/red]")
    console.print("Try running manually: pip install --upgrade ani-cli-arabic")
    return False


def update_binary(latest_ver: str, release_data: Dict[str, Any]) -> bool:
    console.print(f"\n[cyan]Update available: v{__version__} → v{latest_ver}[/cyan]")
    console.print("[dim]Downloading executable update from GitHub...[/dim]\n")

    sys_name = platform.system()
    target_name = "windows" if sys_name == "Windows" else "linux"
    download_url = None

    for asset in release_data.get("assets", []):
        name = asset.get("name", "").lower()
        if target_name in name and name.endswith((".exe" if sys_name == "Windows" else "")):
            download_url = asset.get("browser_download_url")
            break

    if not download_url:
        console.print(f"[yellow]Please download the latest release manually from:[/yellow]")
        console.print(f"  {release_data.get('html_url', 'https://github.com/np4abdou1/ani-cli-arabic/releases')}")
        return False

    try:
        current_exe = Path(sys.executable).resolve()
        temp_exe = current_exe.with_suffix(".new")
        old_exe = current_exe.with_suffix(".old")

        resp = requests.get(download_url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(temp_exe, "wb") as f:
            for chunk in resp.iter_content(chunk_size=32768):
                f.write(chunk)

        if sys_name != "Windows":
            temp_exe.chmod(0o755)

        # In-place executable replacement
        if old_exe.exists():
            old_exe.unlink(missing_ok=True)
        current_exe.rename(old_exe)
        temp_exe.rename(current_exe)

        console.print(f"[green]✓ Successfully replaced binary with v{latest_ver}.[/green]")
        console.print("Please restart the application.")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Binary update failed: {e}[/red]")
        console.print(f"Download manually: {download_url}")
    return False


def check_for_updates(auto_update: bool = True) -> bool:
    """Checks for newer releases and updates via the appropriate platform package manager."""
    try:
        latest_version = get_latest_pypi_version()
        release_data = None

        if not latest_version:
            release_data = get_latest_github_release()
            if release_data:
                latest_version = release_data.get("tag_name", "").lstrip("v")

        if not latest_version:
            return False

        if parse_version(latest_version) <= parse_version(__version__):
            return False

        if not auto_update:
            return True

        method = detect_install_method()
        if method == "aur":
            return update_aur(latest_version)
        elif method == "brew":
            return update_brew(latest_version)
        elif method == "pipx":
            return update_pipx(latest_version)
        elif method == "executable":
            if not release_data:
                release_data = get_latest_github_release()
            if release_data:
                return update_binary(latest_version, release_data)
        elif method == "source":
            return False
        else:
            return update_pip(latest_version)
    except Exception:
        pass

    return False


def get_version_status() -> Optional[Dict[str, Any]]:
    try:
        latest_pip = get_latest_pypi_version() or "N/A"
        is_outdated = False
        if latest_pip != "N/A" and parse_version(latest_pip) > parse_version(__version__):
            is_outdated = True

        return {
            "current": __version__,
            "latest": latest_pip,
            "is_outdated": is_outdated,
            "install_method": detect_install_method()
        }
    except Exception:
        return None
