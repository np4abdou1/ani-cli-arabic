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
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn

console = Console()
#OFFICIAL_MPV_MIRROR
DEPS_DIR = Path.cwd() / "deps"
MPV_URL = "https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260105/mpv-i686-20260105-git-0035bb7.7z"
FZF_URL = "https://github.com/junegunn/fzf/releases/download/v0.67.0/fzf-0.67.0-windows_amd64.zip"
SEVENZIP_URL = "https://www.7-zip.org/a/7zr.exe"  # Standalone 7z extractor (~600KB)


def is_installed(tool):
    """Check if a tool is available on PATH."""
    return shutil.which(tool) is not None


def _clean_deps_keep_important():
    """Clean up deps folder but keep mpv, fzf and 7zr."""
    if not DEPS_DIR.exists():
        return
        
    for item in DEPS_DIR.iterdir():
        if item.name.lower() in ("mpv.exe", "fzf.exe", "7zr.exe"):
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


def _windows_local_deps_root() -> Path | None:
    """Return the local deps folder if mpv.exe or fzf.exe is present."""
    if (DEPS_DIR / "mpv.exe").exists() or (DEPS_DIR / "fzf.exe").exists():
        return DEPS_DIR
    return None


def check_dependencies_status():
    """Check if required tools are installed."""
    # Add local deps/mpv.exe and fzf.exe to PATH on Windows
    if platform.system() == "Windows":
        deps_root = _windows_local_deps_root()
        if deps_root:
            _prepend_to_path(deps_root)

    return {
        "mpv": is_installed("mpv"),
        "ffmpeg": is_installed("ffmpeg"),
        "yt-dlp": is_installed("yt-dlp"),
        "fzf": is_installed("fzf")
    }

def print_explanation(tool):
    """Returns a short explanation of what the tool does."""
    explanations = {
        "mpv": "Media player for streaming",
        "ffmpeg": "Video/audio processing",
        "yt-dlp": "Stream URL extraction",
        "fzf": "Command-line fuzzy finder"
    }
    return explanations.get(tool, "")

def print_status(status):
    """Prints minimal dependency status."""
    console.print("\n[bold magenta]Dependency Check[/bold magenta]")
    
    all_good = True
    for tool, installed in status.items():
        if installed:
            console.print(f"  [green]✔[/green] {tool}")
        else:
            console.print(f"  [red]✘[/red] {tool} [dim]({print_explanation(tool)})[/dim]")
            all_good = False
    
    return all_good

def download_file_with_progress(url, dest_path, description="Downloading"):
    """Download a file with a progress bar."""
    try:
        response = requests.get(url, stream=True, timeout=30)
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
        console.print(f"[red]Download error: {e}[/red]")
        return False

def install_ytdlp():
    with console.status("[cyan]Installing yt-dlp...[/cyan]", spinner="dots"):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], 
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            console.print("[green]✔[/green] yt-dlp installed")
            return True
        except Exception:
            console.print("[red]✘[/red] yt-dlp installation failed")
            return False

def get_7z_extractor():
    """Get path to 7z extractor, downloading if needed."""
    # Check if 7z is already on PATH
    if is_installed("7z"):
        return "7z"
    if is_installed("7za"):
        return "7za"
    
    # Check our deps folder
    local_7z = DEPS_DIR / "7zr.exe"
    if local_7z.exists():
        return str(local_7z)
    
    # Download 7zr.exe (standalone extractor)
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    console.print("[dim]Downloading 7z extractor...[/dim]")
    
    try:
        response = requests.get(SEVENZIP_URL, timeout=30)
        local_7z.write_bytes(response.content)
        return str(local_7z)
    except Exception:
        return None

def install_mpv_windows():
    """Downloads and extracts MPV for Windows."""
    console.print("[cyan]Installing MPV...[/cyan]")
    
    existing_root = _windows_local_deps_root()
    if existing_root:
        _clean_deps_keep_important()
        _prepend_to_path(existing_root)
        if shutil.which("mpv") or (existing_root / "mpv.exe").exists():
            console.print("[green]✔[/green] MPV ready")
            return True
    
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    
    extractor = get_7z_extractor()
    if not extractor:
        console.print("[red]✘[/red] Could not get 7z extractor")
        return False
    
    archive_name = MPV_URL.split("/")[-1]
    archive_path = DEPS_DIR / archive_name
    
    if not download_file_with_progress(MPV_URL, archive_path, "MPV"):
        return False
    
    console.print("[dim]Extracting...[/dim]")
    try:
        result = subprocess.run(
            [extractor, "x", str(archive_path), f"-o{DEPS_DIR}", "-y"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[red]✘[/red] Extraction failed: {result.stderr}")
            return False
        
        console.print("[green]✔[/green] Extracted")
        archive_path.unlink()
        
    except Exception as e:
        console.print(f"[red]✘[/red] Extraction error: {e}")
        return False

    mpv_root = _windows_local_deps_root()
    if not mpv_root:
        console.print("[red]✘[/red] mpv.exe not found after extraction")
        return False

    # Make mpv portable: move to deps root if nested
    if mpv_root != DEPS_DIR:
        try:
            shutil.move(str(mpv_root / "mpv.exe"), str(DEPS_DIR / "mpv.exe"))
            mpv_root = DEPS_DIR
        except Exception:
            pass  # Keep using detected folder

    _clean_deps_keep_important()
    _prepend_to_path(mpv_root)
    
    # Verify installation
    mpv_exe = mpv_root / "mpv.exe"
    if mpv_exe.exists():
        console.print("[green]✔[/green] MPV ready")
        return True

    console.print("[red]✘[/red] mpv.exe not found")
    return False

def install_fzf_windows():
    """Downloads and extracts fzf for Windows."""
    console.print("[cyan]Installing fzf...[/cyan]")
    
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if existing
    if (DEPS_DIR / "fzf.exe").exists():
        console.print("[green]✔[/green] fzf already present")
        _prepend_to_path(DEPS_DIR)
        return True

    extractor = get_7z_extractor()
    if not extractor:
        return False

    archive_name = "fzf.zip"
    archive_path = DEPS_DIR / archive_name
    
    if not download_file_with_progress(FZF_URL, archive_path, "fzf"):
        return False
    
    console.print("[dim]Extracting fzf...[/dim]")
    try:
        result = subprocess.run(
            [extractor, "x", str(archive_path), f"-o{DEPS_DIR}", "-y"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[red]✘[/red] Extraction failed: {result.stderr}")
            return False
            
        archive_path.unlink()
        
        if (DEPS_DIR / "fzf-0.67.0-windows_amd64").exists():
             # Move nested binary
             nested = DEPS_DIR / "fzf-0.67.0-windows_amd64" / "fzf.exe"
             if nested.exists():
                 shutil.move(str(nested), str(DEPS_DIR / "fzf.exe"))
                 try:
                     shutil.rmtree(str(DEPS_DIR / "fzf-0.67.0-windows_amd64"))
                 except (OSError, PermissionError):
                     pass

        if (DEPS_DIR / "fzf.exe").exists():
            console.print("[green]✔[/green] fzf ready")
            _prepend_to_path(DEPS_DIR)
            return True
            
    except Exception as e:
        console.print(f"[red]✘[/red] Install error: {e}")
        return False
        
    return False

def install_deps_windows():
    """Windows Installation Logic"""
    success = True
    
    if not is_installed("ffmpeg"):
        console.print("[cyan]Installing FFmpeg...[/cyan]")
        try:
            result = subprocess.run(
                ["winget", "install", "-e", "--id", "Gyan.FFmpeg", 
                 "--accept-source-agreements", "--accept-package-agreements"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True
            )
            if result.returncode == 0:
                console.print("[green]✔[/green] FFmpeg installed")
            else:
                console.print("[red]✘[/red] FFmpeg installation failed")
                success = False
        except Exception:
            console.print("[red]✘[/red] FFmpeg installation failed")
            success = False

    if not is_installed("mpv"):
        if not install_mpv_windows():
            success = False

    if not is_installed("fzf"):
        if not install_fzf_windows():
            success = False
    
    return success

def install_deps_linux():
    """Linux Auto-Installation"""
    distro_id = "linux"
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    distro_id = line.strip().split("=")[1].strip('"')
                    break
    except (IOError, OSError, FileNotFoundError, PermissionError):
        pass

    console.print(f"[dim]Detected: {distro_id}[/dim]")
    
    if distro_id in ["debian", "ubuntu", "kali", "linuxmint", "pop"]:
        cmd = "sudo apt update && sudo apt install -y mpv ffmpeg fzf"
    elif distro_id in ["arch", "manjaro", "endeavouros"]:
        # Arch usually has fzf in community or extra, standard pacman works
        cmd = "sudo pacman -S --noconfirm mpv ffmpeg fzf"
    elif distro_id in ["fedora"]:
        cmd = "sudo dnf install -y mpv ffmpeg fzf"
    else:
        # Fallback for others
        console.print(f"[red]Unsupported distro. Install mpv, ffmpeg, and fzf manually.[/red]")
        return False

    console.print(f"[dim]Running: {cmd}[/dim]")
    return os.system(cmd) == 0

def ensure_dependencies():
    """Check and install missing dependencies (mpv, ffmpeg, yt-dlp, fzf)."""
    # Quick check
    if all(check_dependencies_status().values()):
        return True

    status = check_dependencies_status()
    print_status(status)
    
    console.print("\n[dim]Auto-install available (mostly works)[/dim]")
    
    if platform.system() == "Darwin":
        console.print("[yellow]Run: brew install mpv ffmpeg yt-dlp[/yellow]")
        console.input("Press Enter after installation...")
        return check_dependencies_status()["mpv"]

    try:
        choice = console.input("\nInstall missing? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print("\n[red]Exiting.[/red]")
        sys.exit(1)
    
    if choice == 'n':
        console.print("[red]Exiting.[/red]")
        sys.exit(1)

    # Install yt-dlp
    if not status["yt-dlp"]:
        install_ytdlp()

    # Platform-specific
    if not (status["mpv"] and status["ffmpeg"] and status["fzf"]):
        if platform.system() == "Windows":
            install_deps_windows()
        elif platform.system() == "Linux":
            install_deps_linux()
    
    # Verify
    console.print("\n[dim]Checking installation...[/dim]")
    new_status = check_dependencies_status()
    
    if all(new_status.values()):
        console.print("[green]✔ All dependencies ready![/green]\n")
        return True
    
    # Show what's still missing
    console.print("\n[yellow]Still missing:[/yellow]")
    for tool, installed in new_status.items():
        if not installed:
            console.print(f"  [red]✘[/red] {tool}")
    
    # On Windows, some tools might need PATH refresh
    if platform.system() == "Windows" and not new_status["mpv"]:
        console.print("\n[yellow]MPV might need a terminal restart to be detected.[/yellow]")
        console.print("[dim]Try running 'mpv --version' in a new terminal.[/dim]")
    
    console.print("\n[red]Installation incomplete.[/red]")
    console.input("Press Enter to exit...")
    sys.exit(1)

