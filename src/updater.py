"""
Auto-updater for ani-cli-arabic across platforms and package managers.
Supports PyPI (pip/pipx), Arch Linux (AUR yay/paru), macOS (Homebrew),
Windows (winget/scoop/standalone binary), and direct GitHub releases.
"""

import os
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


def get_latest_pypi_version(timeout: float = 4.0) -> Optional[str]:
    """Fetches the latest version published on PyPI."""
    try:
        resp = requests.get("https://pypi.org/pypi/ani-cli-arabic/json", timeout=timeout)
        if resp.status_code == 200:
            return resp.json().get("info", {}).get("version")
    except Exception:
        pass
    return None


def get_latest_aur_version(timeout: float = 4.0) -> Optional[str]:
    """Fetches the latest version published in Arch Linux AUR."""
    try:
        resp = requests.get("https://aur.archlinux.org/rpc/v5/info?arg[]=ani-cli-arabic", timeout=timeout)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                raw_ver = results[0].get("Version", "")
                return raw_ver.split("-")[0].strip()
    except Exception:
        pass
    return None


def get_latest_github_release(timeout: float = 4.0) -> Optional[Dict[str, Any]]:
    """Fetches the latest release payload from GitHub Releases API."""
    try:
        resp = requests.get(API_RELEASES_URL, timeout=timeout)
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


def update_aur(latest_ver: str, interactive: bool = False, force: bool = False) -> bool:
    """Handles AUR updates without clobbering background TUI processes."""
    console.print(f"\n[cyan]Update available: v{__version__} → v{latest_ver}[/cyan]")
    console.print("[dim]Detected Arch Linux package (AUR).[/dim]\n")

    helper = None
    for h in ["yay", "paru", "pamac"]:
        if shutil.which(h):
            helper = h
            break

    if not helper:
        console.print("[yellow]Please update using your preferred AUR helper:[/yellow]")
        console.print("  yay -S ani-cli-arabic")
        console.print("  paru -S ani-cli-arabic\n")
        return False

    if force:
        cmd = [helper, "-S", "--noconfirm", "ani-cli-arabic"]
        console.print(f"[cyan]Executing: {' '.join(cmd)}[/cyan]")
        res = subprocess.run(cmd)
        if res.returncode == 0:
            console.print(f"[green]✓ Updated successfully via {helper}.[/green]")
            return True
        else:
            console.print(f"[yellow]{helper} exited with status {res.returncode}.[/yellow]")
            return False

    cmd = [helper, "-S", "ani-cli-arabic"]

    if interactive:
        try:
            choice = input(f"Run '{' '.join(cmd)}' now? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                console.print(f"[cyan]Executing: {' '.join(cmd)}[/cyan]")
                res = subprocess.run(cmd)
                if res.returncode == 0:
                    console.print(f"[green]✓ Updated successfully via {helper}.[/green]")
                    console.print("Please restart the application.")
                    sys.exit(0)
                else:
                    console.print(f"[yellow]{helper} exited with status {res.returncode}.[/yellow]")
            else:
                console.print("[dim]Update skipped.[/dim]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Update cancelled.[/dim]")
    else:
        console.print(f"[yellow]To update, please run:[/yellow] [bold]{' '.join(cmd)}[/bold]\n")

    return False


def update_brew(latest_ver: str, interactive: bool = False, force: bool = False) -> bool:
    """Handles Homebrew updates."""
    console.print(f"\n[cyan]Update available: v{__version__} → v{latest_ver}[/cyan]")
    console.print("[dim]Detected Homebrew installation.[/dim]\n")

    if force:
        console.print("[dim]Updating via Homebrew...[/dim]\n")
        res = subprocess.run(["brew", "upgrade", "ani-cli-arabic"])
        if res.returncode == 0:
            console.print("[green]✓ Updated successfully via Homebrew.[/green]")
            return True
        return False

    if interactive:
        try:
            choice = input("Run 'brew upgrade ani-cli-arabic' now? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                console.print("[dim]Updating via Homebrew...[/dim]\n")
                res = subprocess.run(["brew", "upgrade", "ani-cli-arabic"])
                if res.returncode == 0:
                    console.print("[green]✓ Updated successfully via Homebrew.[/green]")
                    sys.exit(0)
            else:
                console.print("[dim]Update skipped.[/dim]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Update cancelled.[/dim]")
    else:
        console.print("[yellow]To update, please run:[/yellow] [bold]brew upgrade ani-cli-arabic[/bold]\n")

    return False


def update_pipx(latest_ver: str, interactive: bool = False, force: bool = False) -> bool:
    """Handles pipx updates."""
    console.print(f"\n[cyan]Update available: v{__version__} → v{latest_ver}[/cyan]")
    console.print("[dim]Detected pipx installation.[/dim]\n")

    if force:
        console.print("[dim]Updating via pipx...[/dim]\n")
        res = subprocess.run(["pipx", "upgrade", "ani-cli-arabic"])
        if res.returncode == 0:
            console.print("[green]✓ Updated successfully via pipx.[/green]")
            return True
        return False

    if interactive:
        try:
            choice = input("Run 'pipx upgrade ani-cli-arabic' now? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                console.print("[dim]Updating via pipx...[/dim]\n")
                res = subprocess.run(["pipx", "upgrade", "ani-cli-arabic"])
                if res.returncode == 0:
                    console.print("[green]✓ Updated successfully via pipx.[/green]")
                    sys.exit(0)
            else:
                console.print("[dim]Update skipped.[/dim]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Update cancelled.[/dim]")
    else:
        console.print("[yellow]To update, please run:[/yellow] [bold]pipx upgrade ani-cli-arabic[/bold]\n")

    return False


def update_pip(latest_ver: str, interactive: bool = False, force: bool = False) -> bool:
    """Handles standard pip updates."""
    console.print(f"\n[cyan]Update available: v{__version__} → v{latest_ver}[/cyan]")

    if force or interactive:
        if interactive and not force:
            try:
                choice = input(f"Update to v{latest_ver} via pip now? [Y/n]: ").strip().lower()
                if choice not in ("", "y", "yes"):
                    console.print("[dim]Update skipped.[/dim]")
                    return False
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Update cancelled.[/dim]")
                return False

        console.print("[dim]Downloading update from PyPI...[/dim]\n")
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir", "ani-cli-arabic"]
        is_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
        if platform.system() != "Windows" and not is_venv:
            cmd.append("--user")

        res = subprocess.run(cmd, capture_output=True, text=True)

        # Handle PEP 668 (externally-managed-environment on Arch/Debian/Ubuntu)
        if res.returncode != 0 and "externally-managed-environment" in res.stderr:
            console.print("[dim]System-managed Python environment detected; retrying with user override...[/dim]")
            if "--user" not in cmd and not is_venv:
                cmd.append("--user")
            if "--break-system-packages" not in cmd:
                cmd.append("--break-system-packages")
            res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode == 0:
            console.print(f"[green]✓ Successfully updated to v{latest_ver}.[/green]")
            if interactive and not force:
                console.print("Please restart the application.")
                sys.exit(0)
            return True

        console.print(f"[red]Update failed: {res.stderr.strip() or 'Unknown error'}[/red]")
        return False
    else:
        console.print("[yellow]To update, please run:[/yellow] [bold]pip install --upgrade ani-cli-arabic[/bold]\n")

    return False


def update_binary(latest_ver: str, release_data: Dict[str, Any], interactive: bool = False, force: bool = False) -> bool:
    """Downloads and replaces bundled standalone binary."""
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
        console.print("[yellow]Please download the latest release manually from:[/yellow]")
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
        if interactive and not force:
            console.print("Please restart the application.")
            sys.exit(0)
        return True
    except Exception as e:
        console.print(f"[red]Binary update failed: {e}[/red]")
        console.print(f"Download manually: {download_url}")
    return False


def check_for_updates(auto_update: bool = False, interactive: bool = False, force: bool = False) -> bool:
    """Checks for newer releases and updates via the appropriate platform package manager."""
    try:
        method = detect_install_method()

        # For AUR, query the AUR RPC directly. If AUR has not been bumped yet,
        # we must never report an update or invoke yay, avoiding infinite reinstall loops.
        if method == "aur":
            latest_version = get_latest_aur_version()
        else:
            latest_version = get_latest_pypi_version()

        release_data = None
        if not latest_version:
            release_data = get_latest_github_release()
            if release_data:
                latest_version = release_data.get("tag_name", "").lstrip("v")

        if not latest_version:
            if interactive:
                console.print("[dim]Unable to fetch latest release version (network timeout or offline).[/dim]")
            return False

        if parse_version(latest_version) <= parse_version(__version__):
            if interactive:
                console.print(f"[green]✓ ani-cli-arabic is up to date (v{__version__}).[/green]")
            return False

        if not auto_update and not interactive and not force:
            return True

        if method == "aur":
            return update_aur(latest_version, interactive=interactive, force=force)
        elif method == "brew":
            return update_brew(latest_version, interactive=interactive, force=force)
        elif method == "pipx":
            return update_pipx(latest_version, interactive=interactive, force=force)
        elif method == "executable":
            if not release_data:
                release_data = get_latest_github_release()
            if release_data:
                return update_binary(latest_version, release_data, interactive=interactive, force=force)
        elif method == "source":
            if interactive:
                console.print(f"\n[cyan]Update available: v{__version__} → v{latest_version}[/cyan]")
                console.print("[dim]Running from local git source checkout. Run 'git pull' to update.[/dim]\n")
            return False
        else:
            return update_pip(latest_version, interactive=interactive, force=force)
    except Exception:
        pass

    return False


def perform_auto_update(timeout: float = 3.0) -> bool:
    """
    Forced automatic updater invoked at launch before the TUI initializes.
    Returns True if an update was applied and the application should restart.
    """
    try:
        method = detect_install_method()
        if method == "source":
            return False

        if method == "aur":
            latest_version = get_latest_aur_version(timeout=timeout)
        else:
            latest_version = get_latest_pypi_version(timeout=timeout)

        release_data = None
        if not latest_version:
            release_data = get_latest_github_release(timeout=timeout)
            if release_data:
                latest_version = release_data.get("tag_name", "").lstrip("v")

        if not latest_version:
            return False

        if parse_version(latest_version) <= parse_version(__version__):
            return False

        console.print(f"\n[bold cyan]⚡ New update detected: v{__version__} → v{latest_version}[/bold cyan]")
        console.print("[dim]Performing automatic update...[/dim]")

        if method == "aur":
            return update_aur(latest_version, interactive=False, force=True)
        elif method == "brew":
            return update_brew(latest_version, interactive=False, force=True)
        elif method == "pipx":
            return update_pipx(latest_version, interactive=False, force=True)
        elif method == "executable":
            if not release_data:
                release_data = get_latest_github_release(timeout=6.0)
            if release_data:
                return update_binary(latest_version, release_data, interactive=False, force=True)
        else:
            return update_pip(latest_version, interactive=False, force=True)
    except Exception as e:
        console.print(f"[yellow]Auto-update check encountered error: {e}[/yellow]")
        return False

    return False


def restart_application():
    """Restarts the application after an update."""
    try:
        from .utils import show_cursor
        show_cursor()
        console.print("[cyan]Restarting ani-cli-arabic...[/cyan]\n")
        sys.stdout.flush()
        sys.stderr.flush()

        if is_bundled():
            os.execv(sys.executable, sys.argv)
        elif sys.argv[0] and Path(sys.argv[0]).exists() and os.access(sys.argv[0], os.X_OK):
            os.execv(sys.argv[0], sys.argv)
        else:
            os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception:
        console.print("[green]Please restart ani-cli-arabic to launch the new version.[/green]")
        sys.exit(0)


def get_version_status() -> Optional[Dict[str, Any]]:
    """Returns structured version and update status for the active installation method."""
    try:
        method = detect_install_method()
        if method == "aur":
            latest_ver = get_latest_aur_version() or "N/A"
        else:
            latest_ver = get_latest_pypi_version() or "N/A"

        is_outdated = False
        if latest_ver != "N/A" and parse_version(latest_ver) > parse_version(__version__):
            is_outdated = True

        return {
            "current": __version__,
            "latest": latest_ver,
            "is_outdated": is_outdated,
            "install_method": method
        }
    except Exception:
        return None
