"""
Dependency management and automated installation for ani-cli-arabic.
Installs and verifies media playback dependencies: mpv, ffmpeg, and fzf.
"""

import os
import sys
import shutil
import zipfile
import platform
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn

console = Console()

try:
    DEPS_DIR = Path.home() / ".ani-cli-arabic" / "deps"
except Exception:
    DEPS_DIR = Path(tempfile.gettempdir()) / ".ani-cli-arabic" / "deps"

# Verified mirrors for direct Windows/fallback downloads
SEVENZIP_URL = "https://www.7-zip.org/a/7zr.exe"
FZF_WIN_URL = "https://github.com/junegunn/fzf/releases/download/v0.67.0/fzf-0.67.0-windows_amd64.zip"
FFMPEG_WIN_MIRRORS = [
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
]
MPV_WIN_MIRRORS = [
    "https://sourceforge.net/projects/mpv-player-windows/files/64bit/mpv-x86_64-20261011-git-accb7b2821.7z/download",
    "https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20261015/mpv-x86_64-20261015-git-492bae0768.7z"
]


def get_mpv_mirrors() -> List[str]:
    mirrors = []
    try:
        r = requests.get("https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest", timeout=5)
        if r.status_code == 200:
            for asset in r.json().get("assets", []):
                name = asset.get("name", "")
                if name.startswith("mpv-x86_64-") and not name.startswith("mpv-x86_64-v3-") and name.endswith(".7z"):
                    mirrors.append(asset.get("browser_download_url"))
    except Exception:
        pass
    for m in MPV_WIN_MIRRORS:
        if m not in mirrors:
            mirrors.append(m)
    return mirrors


def is_installed(tool: str) -> bool:
    return shutil.which(tool) is not None


def is_termux() -> bool:
    return "ANDROID_ROOT" in os.environ or "com.termux" in os.environ.get("PREFIX", "")


def get_platform_name() -> str:
    if is_termux():
        return "Android (Termux)"
    sys_name = platform.system()
    if sys_name == "Darwin":
        return "macOS"
    if sys_name == "Windows":
        rel = platform.release()
        return f"Windows {rel}" if rel else "Windows"
    if sys_name == "Linux":
        try:
            os_info = platform.freedesktop_os_release()
            name = os_info.get("NAME") or os_info.get("ID")
            if name:
                return f"Linux ({name})"
        except Exception:
            pass
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("NAME="):
                            distro_name = line.split("=", 1)[1].strip('"\'')
                            return f"Linux ({distro_name})"
            except Exception:
                pass
        return "Linux"
    return sys_name or "Unknown"


def _prepend_to_path(dir_path: Path) -> None:
    dir_str = str(dir_path)
    current = os.environ.get("PATH", "")
    if dir_str and dir_str not in current:
        os.environ["PATH"] = dir_str + os.pathsep + current


def _local_deps_root() -> Optional[Path]:
    executables = ["mpv.exe", "fzf.exe", "ffmpeg.exe", "mpv", "fzf", "ffmpeg"]
    if any((DEPS_DIR / f).exists() for f in executables):
        return DEPS_DIR
    return None


def _clean_deps_directory():
    if not DEPS_DIR.exists():
        return
    keep = {"mpv.exe", "fzf.exe", "7zr.exe", "ffmpeg.exe", "ffprobe.exe", "mpv", "ffmpeg", "fzf"}
    for item in DEPS_DIR.iterdir():
        if item.name.lower() in keep:
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        except (OSError, PermissionError):
            pass


def check_dependencies_status() -> Dict[str, bool]:
    if platform.system() != "Windows":
        local_bin = str(Path.home() / ".local" / "bin")
        if local_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")

    deps_root = _local_deps_root()
    if deps_root:
        _prepend_to_path(deps_root)

    return {
        "mpv": is_installed("mpv"),
        "ffmpeg": is_installed("ffmpeg"),
        "fzf": is_installed("fzf")
    }


def download_file_with_progress(urls: List[str] | str, dest_path: Path, description: str = "Downloading") -> bool:
    if isinstance(urls, str):
        urls = [urls]

    headers = {"User-Agent": "Mozilla/5.0 (ani-cli-arabic dependency installer)"}
    for url in urls:
        if not url:
            continue
        try:
            response = requests.get(url, stream=True, timeout=30, headers=headers)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[cyan]{task.description}"),
                BarColumn(bar_width=30),
                "[progress.percentage]{task.percentage:>3.0f}%",
                DownloadColumn(),
                TransferSpeedColumn(),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(description, total=total_size)
                with open(dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=16384):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))
            return True
        except Exception:
            continue

    if dest_path.exists():
        try:
            dest_path.unlink()
        except Exception:
            pass
    return False



def get_7z_extractor() -> Optional[str]:
    for tool in ("7z", "7za"):
        if is_installed(tool):
            return tool
    local_7z = DEPS_DIR / "7zr.exe"
    if local_7z.exists():
        return str(local_7z)

    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(SEVENZIP_URL, timeout=20)
        local_7z.write_bytes(resp.content)
        return str(local_7z)
    except Exception:
        return None


def install_mpv_windows() -> bool:
    console.print("[cyan]Installing MPV player...[/cyan]")
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    extractor = get_7z_extractor()
    if not extractor:
        console.print("[red]✗[/red] 7z extractor unavailable")
        return False

    archive_path = DEPS_DIR / "mpv.7z"
    if not download_file_with_progress(get_mpv_mirrors(), archive_path, "MPV"):
        return False

    try:
        res = subprocess.run([extractor, "x", str(archive_path), f"-o{DEPS_DIR}", "-y"], capture_output=True)
        archive_path.unlink(missing_ok=True)
        if res.returncode != 0:
            return False

        for item in DEPS_DIR.rglob("mpv.exe"):
            if item.parent != DEPS_DIR:
                shutil.move(str(item), str(DEPS_DIR / "mpv.exe"))
                break

        _clean_deps_directory()
        _prepend_to_path(DEPS_DIR)
        if (DEPS_DIR / "mpv.exe").exists():
            console.print("[green]✓[/green] MPV installed successfully")
            return True
    except Exception as e:
        console.print(f"[red]✗[/red] Extraction error: {e}")
    return False


def install_fzf_windows() -> bool:
    console.print("[cyan]Installing fzf...[/cyan]")
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = DEPS_DIR / "fzf.zip"

    if not download_file_with_progress(FZF_WIN_URL, archive_path, "fzf"):
        return False

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(DEPS_DIR)
        archive_path.unlink(missing_ok=True)

        for item in DEPS_DIR.rglob("fzf.exe"):
            if item.parent != DEPS_DIR:
                shutil.move(str(item), str(DEPS_DIR / "fzf.exe"))
                break

        _prepend_to_path(DEPS_DIR)
        if (DEPS_DIR / "fzf.exe").exists():
            console.print("[green]✓[/green] fzf installed successfully")
            return True
    except Exception as e:
        console.print(f"[red]✗[/red] fzf error: {e}")
    return False


def install_ffmpeg_windows() -> bool:
    console.print("[cyan]Installing FFmpeg...[/cyan]")
    DEPS_DIR.mkdir(parents=True, exist_ok=True)

    # Package managers check
    for pm, args in [
        ("winget", ["install", "-e", "--id", "Gyan.FFmpeg", "--accept-source-agreements", "--accept-package-agreements"]),
        ("scoop", ["install", "ffmpeg"]),
        ("choco", ["install", "ffmpeg", "-y"])
    ]:
        if is_installed(pm):
            try:
                res = subprocess.run([pm] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res.returncode == 0:
                    console.print(f"[green]✓[/green] FFmpeg installed via {pm}")
                    return True
            except Exception:
                pass

    # Direct zip fallback
    archive_path = DEPS_DIR / "ffmpeg.zip"
    if not download_file_with_progress(FFMPEG_WIN_MIRRORS, archive_path, "FFmpeg"):
        return False

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(DEPS_DIR)
        archive_path.unlink(missing_ok=True)

        for item in DEPS_DIR.rglob("ffmpeg.exe"):
            shutil.move(str(item), str(DEPS_DIR / "ffmpeg.exe"))
        for item in DEPS_DIR.rglob("ffprobe.exe"):
            shutil.move(str(item), str(DEPS_DIR / "ffprobe.exe"))

        _prepend_to_path(DEPS_DIR)
        _clean_deps_directory()
        if (DEPS_DIR / "ffmpeg.exe").exists():
            console.print("[green]✓[/green] FFmpeg installed successfully")
            return True
    except Exception as e:
        console.print(f"[red]✗[/red] FFmpeg error: {e}")
    return False


def install_deps_windows() -> bool:
    ok = True
    if not is_installed("ffmpeg") and not install_ffmpeg_windows():
        ok = False
    if not is_installed("mpv") and not install_mpv_windows():
        ok = False
    if not is_installed("fzf") and not install_fzf_windows():
        ok = False
    return ok


def install_deps_linux() -> bool:
    console.print("[cyan]Detecting package manager...[/cyan]")

    if is_termux():
        console.print("[cyan]Android Termux detected. Running: pkg install mpv ffmpeg fzf[/cyan]")
        res = subprocess.run(["pkg", "install", "-y", "mpv", "ffmpeg", "fzf"])
        return res.returncode == 0

    managers = [
        ("pacman", "sudo pacman -S --needed --noconfirm mpv ffmpeg fzf"),
        ("apt", "sudo apt update && sudo apt install -y mpv ffmpeg fzf"),
        ("dnf", "sudo dnf install -y mpv ffmpeg fzf"),
        ("zypper", "sudo zypper install -y mpv ffmpeg fzf"),
        ("apk", "sudo apk add mpv ffmpeg fzf"),
        ("xbps-install", "sudo xbps-install -Sy mpv ffmpeg fzf"),
        ("emerge", "sudo emerge -av media-video/mpv media-video/ffmpeg app-shells/fzf"),
        ("nix-env", "nix-env -iA nixpkgs.mpv nixpkgs.ffmpeg nixpkgs.fzf"),
        ("pkg", "sudo pkg install -y mpv ffmpeg fzf")
    ]

    for pm, cmd in managers:
        if is_installed(pm):
            console.print(f"[dim]Executing: {cmd}[/dim]")
            res = subprocess.run(cmd, shell=True)
            if res.returncode == 0:
                console.print(f"[green]✓ Dependencies installed via {pm}[/green]")
                return True

    console.print("[red]Automatic package installation failed. Please install mpv, ffmpeg, and fzf manually.[/red]")
    return False


def install_deps_macos() -> bool:
    if is_installed("brew"):
        console.print("[dim]Executing: brew install mpv ffmpeg fzf[/dim]")
        res = subprocess.run(["brew", "install", "mpv", "ffmpeg", "fzf"])
        if res.returncode == 0:
            console.print("[green]✓ Dependencies installed via Homebrew[/green]")
            return True
    elif is_installed("port"):
        console.print("[dim]Executing: sudo port install mpv ffmpeg fzf[/dim]")
        res = subprocess.run(["sudo", "port", "install", "mpv", "ffmpeg", "fzf"])
        if res.returncode == 0:
            console.print("[green]✓ Dependencies installed via MacPorts[/green]")
            return True

    console.print("[yellow]Please install Homebrew (https://brew.sh) and run: brew install mpv ffmpeg fzf[/yellow]")
    return False


def ensure_dependencies() -> bool:
    status = check_dependencies_status()
    if all(status.values()):
        return True

    console.print("\n[bold]System Dependency Check[/bold]")
    for tool, present in status.items():
        if present:
            console.print(f"  [green]✓[/green] {tool}")
        else:
            console.print(f"  [red]✗[/red] {tool} (missing)")

    try:
        ans = console.input("\nInstall missing media tools? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        sys.exit(1)

    if ans == "n":
        return False

    sys_platform = platform.system()
    if sys_platform == "Windows":
        install_deps_windows()
    elif sys_platform == "Darwin":
        install_deps_macos()
    else:
        install_deps_linux()

    updated = check_dependencies_status()
    if all(updated.values()):
        console.print("[green]✓ All dependencies ready.[/green]\n")
        return True

    missing = [t for t, p in updated.items() if not p]
    console.print(f"\n[yellow]Warning: Missing dependencies: {', '.join(missing)}[/yellow]")
    return False
