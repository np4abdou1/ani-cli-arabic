"""
Dependency Manager
Auto-installs media tools: mpv (streaming), ffmpeg (helper), yt-dlp (trailers)
"""

import os
import sys
import shutil
import subprocess
import platform
import requests
import zipfile
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn

console = Console()
try:
    DEPS_DIR = Path.home() / ".ani-cli-arabic" / "deps"
except RuntimeError:
    import tempfile
    DEPS_DIR = Path(tempfile.gettempdir()) / ".ani-cli-arabic" / "deps"
MPV_FALLBACK = "https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260307/mpv-x86_64-v3-20260307-git-f9190e5.7z"
FZF_FALLBACK = "https://github.com/junegunn/fzf/releases/download/v0.67.0/fzf-0.67.0-windows_amd64.zip"
FFMPEG_FALLBACK = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
SEVENZIP_URL = "https://www.7-zip.org/a/7zr.exe"


def is_installed(tool):
    return shutil.which(tool) is not None


def _clean_deps_keep_important():
    if not DEPS_DIR.exists():
        return
        
    for item in DEPS_DIR.iterdir():
        if item.name.lower() in ("mpv.exe", "fzf.exe", "7zr.exe", "ffmpeg.exe", "ffprobe.exe", "yt-dlp.exe", "yt-dlp"):
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        except (OSError, PermissionError):
            pass


def _prepend_to_path(dir_path: Path) -> None:
    dir_str = str(dir_path)
    current = os.environ.get("PATH", "")
    if dir_str and dir_str not in current:
        os.environ["PATH"] = dir_str + os.pathsep + current


def _local_deps_root() -> Path | None:
    executables = ["mpv.exe", "fzf.exe", "ffmpeg.exe", "yt-dlp.exe", "mpv", "fzf", "ffmpeg", "yt-dlp"]
    if any((DEPS_DIR / f).exists() for f in executables):
        return DEPS_DIR
    return None


def check_dependencies_status():
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
        "yt-dlp": is_installed("yt-dlp"),
        "fzf": is_installed("fzf")
    }


def print_explanation(tool):
    explanations = {
        "mpv": "Media player for streaming",
        "ffmpeg": "Video/audio processing",
        "yt-dlp": "Stream URL extraction",
        "fzf": "Command-line fuzzy finder"
    }
    return explanations.get(tool, "")


def print_status(status):
    console.print("\n[bold magenta]Dependency Check[/bold magenta]")
    all_good = True
    for tool, installed in status.items():
        if installed:
            console.print(f"  [green]✔[/green] {tool}")
        else:
            console.print(f"  [red]✘[/red] {tool} [dim]({print_explanation(tool)})[/dim]")
            all_good = False
    return all_good


def get_latest_github_release(repo, asset_filter):
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            for asset in response.json().get("assets", []):
                if asset_filter in asset.get("name", ""):
                    return asset.get("browser_download_url")
    except Exception:
        pass
    return None


def download_file_with_progress(urls, dest_path, description="Downloading"):
    if isinstance(urls, str):
        urls = [urls]

    for url in urls:
        if not url:
            continue
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]{task.description}"),
                BarColumn(bar_width=30),
                "[progress.percentage]{task.percentage:>3.0f}%",
                DownloadColumn(),
                TransferSpeedColumn(),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(description, total=total_size)
                
                with open(dest_path, "wb") as file:
                    for data in response.iter_content(chunk_size=8192):
                        file.write(data)
                        progress.update(task, advance=len(data))
            return True
        except Exception as e:
            console.print(f"[dim]Download failed from {url}: {e}[/dim]")
            continue
            
    console.print(f"[red]Failed to download {description} from all available mirrors.[/red]")
    if Path(dest_path).exists():
        Path(dest_path).unlink()
    return False


def install_ytdlp():
    console.print("[cyan]Installing yt-dlp...[/cyan]")
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    
    system = platform.system()
    filename = "yt-dlp.exe" if system == "Windows" else "yt-dlp"
    
    if (DEPS_DIR / filename).exists():
        console.print("[green]✔[/green] yt-dlp already present")
        _prepend_to_path(DEPS_DIR)
        return True
        
    if system == "Windows":
        asset_name = "yt-dlp.exe"
        fallback_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    elif system == "Darwin":
        asset_name = "yt-dlp_macos"
        fallback_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
    else:
        asset_name = "yt-dlp_linux"
        fallback_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux"
        
    urls = [
        get_latest_github_release("yt-dlp/yt-dlp", asset_name),
        fallback_url
    ]
    
    dest_path = DEPS_DIR / filename
    if download_file_with_progress(urls, dest_path, "yt-dlp"):
        if system != "Windows":
            try:
                os.chmod(dest_path, 0o755)  # Make it executable for Linux/Mac
            except (OSError, PermissionError) as e:
                console.print(f"[yellow]⚠ Could not make yt-dlp executable: {e}[/yellow]")
        console.print("[green]✔[/green] yt-dlp ready")
        _prepend_to_path(DEPS_DIR)
        _clean_deps_keep_important()
        return True
        
    return False


def get_7z_extractor():
    if is_installed("7z"): return "7z"
    if is_installed("7za"): return "7za"
    
    local_7z = DEPS_DIR / "7zr.exe"
    if local_7z.exists(): return str(local_7z)
    
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    console.print("[dim]Downloading 7z extractor...[/dim]")
    try:
        response = requests.get(SEVENZIP_URL, timeout=30)
        local_7z.write_bytes(response.content)
        return str(local_7z)
    except Exception:
        return None


def install_mpv_windows():
    console.print("[cyan]Installing MPV...[/cyan]")
    
    existing_root = _local_deps_root()
    if existing_root and (existing_root / "mpv.exe").exists():
        _prepend_to_path(existing_root)
        console.print("[green]✔[/green] MPV ready")
        return True
    
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    extractor = get_7z_extractor()
    if not extractor:
        console.print("[red]✘[/red] Could not get 7z extractor")
        return False
    
    urls = [
        get_latest_github_release("shinchiro/mpv-winbuild-cmake", "mpv-x86_64-v3"),
        get_latest_github_release("shinchiro/mpv-winbuild-cmake", "mpv-x86_64-"),
        get_latest_github_release("shinchiro/mpv-winbuild-cmake", "mpv-i686-"),
        MPV_FALLBACK
    ]
    
    archive_path = DEPS_DIR / "mpv.7z"
    if not download_file_with_progress(urls, archive_path, "MPV"): return False
    
    console.print("[dim]Extracting...[/dim]")
    try:
        if subprocess.run([extractor, "x", str(archive_path), f"-o{DEPS_DIR}", "-y"], capture_output=True).returncode != 0:
            console.print("[red]✘[/red] Extraction failed")
            return False
            
        archive_path.unlink()
        
        # Flatten directory
        for item in DEPS_DIR.rglob("mpv.exe"):
            if item.parent != DEPS_DIR:
                shutil.move(str(item), str(DEPS_DIR / "mpv.exe"))
                break
                
        _clean_deps_keep_important()
        _prepend_to_path(DEPS_DIR)
        
        if (DEPS_DIR / "mpv.exe").exists():
            console.print("[green]✔[/green] MPV ready")
            return True
            
    except Exception as e:
        console.print(f"[red]✘[/red] MPV Install Error: {e}")
    return False


def install_fzf_windows():
    console.print("[cyan]Installing fzf...[/cyan]")
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    
    if (DEPS_DIR / "fzf.exe").exists():
        console.print("[green]✔[/green] fzf already present")
        _prepend_to_path(DEPS_DIR)
        return True

    urls = [get_latest_github_release("junegunn/fzf", "windows_amd64.zip"), FZF_FALLBACK]
    archive_path = DEPS_DIR / "fzf.zip"
    
    if not download_file_with_progress(urls, archive_path, "fzf"): return False
    
    console.print("[dim]Extracting fzf...[/dim]")
    try:
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(DEPS_DIR)
        archive_path.unlink()
        
        for item in DEPS_DIR.rglob("fzf.exe"):
            if item.parent != DEPS_DIR:
                shutil.move(str(item), str(DEPS_DIR / "fzf.exe"))
                break

        if (DEPS_DIR / "fzf.exe").exists():
            console.print("[green]✔[/green] fzf ready")
            _prepend_to_path(DEPS_DIR)
            _clean_deps_keep_important()
            return True
    except Exception as e:
        console.print(f"[red]✘[/red] fzf Install error: {e}")
    return False


def install_ffmpeg_windows_direct():
    """Fallback direct download for ffmpeg if package managers fail."""
    urls = [get_latest_github_release("BtbN/FFmpeg-Builds", "ffmpeg-master-latest-win64-gpl.zip"), FFMPEG_FALLBACK]
    archive_path = DEPS_DIR / "ffmpeg.zip"
    
    if not download_file_with_progress(urls, archive_path, "FFmpeg"): return False
    console.print("[dim]Extracting FFmpeg...[/dim]")
    try:
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(DEPS_DIR)
        archive_path.unlink()
        
        for item in DEPS_DIR.rglob("ffmpeg.exe"):
            shutil.move(str(item), str(DEPS_DIR / "ffmpeg.exe"))
        for item in DEPS_DIR.rglob("ffprobe.exe"):
            shutil.move(str(item), str(DEPS_DIR / "ffprobe.exe"))

        if (DEPS_DIR / "ffmpeg.exe").exists():
            console.print("[green]✔[/green] FFmpeg downloaded directly")
            _prepend_to_path(DEPS_DIR)
            _clean_deps_keep_important()
            return True
    except Exception:
        pass
    return False


def install_ffmpeg_windows():
    console.print("[cyan]Installing FFmpeg...[/cyan]")
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    
    if (DEPS_DIR / "ffmpeg.exe").exists():
        _prepend_to_path(DEPS_DIR)
        console.print("[green]✔[/green] FFmpeg ready")
        return True

    # Try winget
    if is_installed("winget"):
        console.print("[dim]Trying winget...[/dim]")
        if subprocess.run(["winget", "install", "-e", "--id", "Gyan.FFmpeg", "--accept-source-agreements", "--accept-package-agreements"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            console.print("[green]✔[/green] FFmpeg installed via winget")
            return True

    # Try scoop
    if is_installed("scoop"):
        console.print("[dim]Trying scoop...[/dim]")
        if subprocess.run(["scoop", "install", "ffmpeg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            console.print("[green]✔[/green] FFmpeg installed via scoop")
            return True

    # Try choco
    if is_installed("choco"):
        console.print("[dim]Trying choco...[/dim]")
        if subprocess.run(["choco", "install", "ffmpeg", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            console.print("[green]✔[/green] FFmpeg installed via choco")
            return True

    console.print("[dim]Package managers failed or missing. falling back to direct download...[/dim]")
    return install_ffmpeg_windows_direct()


def install_deps_windows():
    success = True
    if not is_installed("ffmpeg"):
        if not install_ffmpeg_windows(): success = False
    if not is_installed("mpv"):
        if not install_mpv_windows(): success = False
    if not is_installed("fzf"):
        if not install_fzf_windows(): success = False
    return success


def install_deps_linux():
    console.print("[cyan]Detecting package manager...[/cyan]")
    
    pm_commands = [
        {"pm": "apt", "cmd": "sudo apt update && sudo apt install -y mpv ffmpeg fzf"},
        {"pm": "pacman", "cmd": "sudo pacman -Sy --noconfirm mpv ffmpeg fzf"},
        {"pm": "dnf", "cmd": "sudo dnf install -y mpv ffmpeg fzf"},
        {"pm": "zypper", "cmd": "sudo zypper install -y mpv ffmpeg fzf"},
        {"pm": "apk", "cmd": "sudo apk add mpv ffmpeg fzf"},
        {"pm": "yum", "cmd": "sudo yum install -y mpv ffmpeg fzf"},
        {"pm": "nix-env", "cmd": "nix-env -iA nixpkgs.mpv nixpkgs.ffmpeg nixpkgs.fzf"}
    ]
    
    for pm in pm_commands:
        if is_installed(pm["pm"]):
            console.print(f"[dim]Running: {pm['cmd']}[/dim]")
            if subprocess.run(pm['cmd'], shell=True, check=False).returncode == 0:
                console.print(f"[green]✔ Dependencies installed via {pm['pm']}[/green]")
                return True
            else:
                console.print(f"[red]Installation via {pm['pm']} failed, trying fallbacks if any...[/red]")
                
    console.print("[red]Could not determine package manager or installation failed. Please install mpv, ffmpeg, and fzf manually.[/red]")
    return False


def ensure_dependencies():
    if all(check_dependencies_status().values()):
        return True

    status = check_dependencies_status()
    print_status(status)
    
    console.print("\n[dim]Auto-install available (mostly works)[/dim]")
    
    if platform.system() == "Darwin":
        if is_installed("brew"):
            console.print("[dim]Running: brew install mpv ffmpeg yt-dlp fzf[/dim]")
            if subprocess.run(["brew", "install", "mpv", "ffmpeg", "yt-dlp", "fzf"]).returncode == 0:
                console.print("[green]✔ Dependencies installed via brew[/green]")
                return True
        console.print("[yellow]Please run: brew install mpv ffmpeg yt-dlp fzf[/yellow]")
        console.input("Press Enter after installation...")
        return all(check_dependencies_status().values())

    try:
        choice = console.input("\nInstall missing? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print("\n[red]Exiting.[/red]")
        sys.exit(1)
    
    if choice == 'n':
        console.print("[red]Exiting.[/red]")
        sys.exit(1)

    if not status["yt-dlp"]:
        install_ytdlp()

    if not (status["mpv"] and status["ffmpeg"] and status["fzf"]):
        if platform.system() == "Windows":
            install_deps_windows()
        elif platform.system() == "Linux":
            install_deps_linux()
    
    console.print("\n[dim]Checking installation...[/dim]")
    new_status = check_dependencies_status()
    
    if all(new_status.values()):
        console.print("[green]✔ All dependencies ready![/green]\n")
        return True
    
    console.print("\n[yellow]Still missing:[/yellow]")
    for tool, installed in new_status.items():
        if not installed:
            console.print(f"  [red]✘[/red] {tool}")
    
    if platform.system() == "Windows":
        console.print("\n[yellow]Note: Some tools might need a terminal restart to be detected.[/yellow]")
    
    console.print("\n[red]Installation incomplete. You may need to install them manually.[/red]")
    console.input("Press Enter to exit...")
    sys.exit(1)
