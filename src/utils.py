import os
import sys
import time
from typing import Optional, List, Dict, Any
import shutil
import subprocess
import threading
import platform
import re
import requests
from rich.progress import Progress, BarColumn, TextColumn, TransferSpeedColumn, TimeRemainingColumn, DownloadColumn
from rich.live import Live
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.box import HEAVY
from .config import COLOR_BORDER, COLOR_TITLE, COLOR_SUBTITLE, COLOR_BOLT

if os.name == 'nt':
    import msvcrt
else:
    import tty
    import termios
    import select

# Global terminal state for Linux (keeps terminal in raw mode for better performance)
_linux_terminal_fd = None
_linux_old_settings = None
_linux_raw_mode = False

_WINDOWS_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED_FILENAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

def is_bundled():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def hide_cursor():
    """Hide terminal cursor across Linux, macOS, and Windows ANSI."""
    try:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
    except Exception:
        pass

def show_cursor():
    """Show terminal cursor across Linux, macOS, and Windows ANSI."""
    try:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
    except Exception:
        pass

def _enter_raw_mode():
    """Enter raw mode for the terminal (Linux/macOS only). Called once at start of menu."""
    global _linux_terminal_fd, _linux_old_settings, _linux_raw_mode
    hide_cursor()
    if os.name == 'nt' or _linux_raw_mode:
        return
    try:
        _linux_terminal_fd = sys.stdin.fileno()
        _linux_old_settings = termios.tcgetattr(_linux_terminal_fd)
        tty.setcbreak(_linux_terminal_fd)  # setcbreak is better than setraw for our use case
        _linux_raw_mode = True
    except Exception:
        pass

def _exit_raw_mode():
    """Exit raw mode and restore terminal settings."""
    global _linux_terminal_fd, _linux_old_settings, _linux_raw_mode
    show_cursor()
    if os.name == 'nt' or not _linux_raw_mode:
        return
    try:
        if _linux_old_settings is not None:
            termios.tcsetattr(_linux_terminal_fd, termios.TCSADRAIN, _linux_old_settings)
        _linux_raw_mode = False
    except Exception:
        pass

def get_key():
    """
    Get a single keypress. Returns immediately if no key is available.
    
    On Linux, this function assumes the terminal is already in raw/cbreak mode
    (via RawTerminal context manager or _enter_raw_mode).
    """
    if platform.system() == 'Windows':
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\xe0' or key == b'\x00':
                key2 = msvcrt.getch()
                if key2 == b'H':
                    return 'UP'
                elif key2 == b'P':
                    return 'DOWN'
                elif key2 == b'M':
                    return 'RIGHT'
                elif key2 == b'K':
                    return 'LEFT'
            elif key == b'\r':
                return 'ENTER'
            elif key == b'\x1b':
                # Handle ANSI escape sequences on Windows (e.g. VS Code terminal)
                start_time = time.time()
                seq = b'\x1b'
                while (time.time() - start_time) < 0.05:
                    if msvcrt.kbhit():
                        seq += msvcrt.getch()
                        if len(seq) >= 3:
                            if seq.startswith(b'\x1b[') or seq.startswith(b'\x1bO'):
                                last = seq[-1:]
                                if last == b'A':
                                    return 'UP'
                                if last == b'B':
                                    return 'DOWN'
                                if last == b'C':
                                    return 'RIGHT'
                                if last == b'D':
                                    return 'LEFT'
                            break
                    else:
                        time.sleep(0.001)
                
                if seq == b'\x1b':
                    return 'ESC'
                return None
            elif key == b'q' or key == b'Q':
                return 'q'
            elif key == b'g' or key == b'G':
                return 'g'
            elif key == b'b' or key == b'B':
                return 'b'
            elif key == b'd' or key == b'D':
                return 'd'
            elif key == b'l' or key == b'L':
                return 'l'
            elif key == b'/' or key == b'?':
                return '/'
            else:
                return key.decode('utf-8', errors='ignore')
        return None
    else:
        # Linux/macOS implementation - optimized for responsiveness
        fd = sys.stdin.fileno()
        
        # Use a longer timeout (0.05s) for better CPU usage while still being responsive
        if not select.select([fd], [], [], 0.05)[0]:
            return None
        
        # Read available data
        try:
            ch_bytes = os.read(fd, 1)
        except (OSError, IOError):
            return None
            
        if not ch_bytes:
            return None
            
        ch = ch_bytes.decode('utf-8', errors='ignore')
        
        if ch == '\x03':  # Ctrl+C
            raise KeyboardInterrupt
        
        if ch == '\x1b':
            # Escape sequence - read the rest quickly
            seq = ch
            # Give a short window to read the rest of the escape sequence
            # Arrow keys send sequences like: ESC [ A
            end_time = time.time() + 0.02  # 20ms window for escape sequences
            
            while time.time() < end_time:
                if select.select([fd], [], [], 0.005)[0]:
                    try:
                        next_byte = os.read(fd, 1)
                        if next_byte:
                            seq += next_byte.decode('utf-8', errors='ignore')
                            # Check if we have a complete sequence
                            if len(seq) >= 3:
                                last = seq[-1]
                                # Standard arrow keys: ESC [ A/B/C/D or ESC O A/B/C/D
                                if (seq.startswith('\x1b[') or seq.startswith('\x1bO')) and last in 'ABCD':
                                    if last == 'A':
                                        return 'UP'
                                    if last == 'B':
                                        return 'DOWN'
                                    if last == 'C':
                                        return 'RIGHT'
                                    if last == 'D':
                                        return 'LEFT'
                                # Extended sequences like ESC [ 1 ; 5 A (Ctrl+Arrow)
                                if len(seq) >= 6 and seq.startswith('\x1b[1;'):
                                    if last == 'A':
                                        return 'UP'
                                    if last == 'B':
                                        return 'DOWN'
                                    if last == 'C':
                                        return 'RIGHT'
                                    if last == 'D':
                                        return 'LEFT'
                    except (OSError, IOError):
                        break
                else:
                    # No more data, check what we have
                    break
            
            # If only ESC was pressed (no following chars)
            if seq == '\x1b':
                return 'ESC'
            
            # Check final sequence
            if len(seq) >= 3:
                last = seq[-1]
                if (seq.startswith('\x1b[') or seq.startswith('\x1bO')) and last in 'ABCD':
                    if last == 'A':
                        return 'UP'
                    if last == 'B':
                        return 'DOWN'
                    if last == 'C':
                        return 'RIGHT'
                    if last == 'D':
                        return 'LEFT'
            
            # Unknown escape sequence, ignore
            return None
        
        elif ch == '\r' or ch == '\n':
            return 'ENTER'
        elif ch in 'qQ':
            return 'q'
        elif ch in 'gG':
            return 'g'
        elif ch in 'bB':
            return 'b'
        elif ch in 'dD':
            return 'd'
        elif ch in 'lL':
            return 'l'
        elif ch in 'fF':
            return 'f'
        elif ch in 'mM':
            return 'm'
        elif ch == '/' or ch == '?':
            return '/'
        
        return ch

class RawTerminal:
    """Context manager to set terminal to cbreak mode (POSIX only).
    
    Uses cbreak instead of raw mode to allow signal handling (Ctrl+C).
    On Windows, this is a no-op since msvcrt handles input differently.
    """
    _active_instance = None
    _lock = threading.Lock() if 'threading' in dir() else None
    
    def __init__(self):
        self.fd = None
        self.old_settings = None

    def __enter__(self):
        hide_cursor()
        if platform.system() != 'Windows':
            try:
                self.fd = sys.stdin.fileno()
                self.old_settings = termios.tcgetattr(self.fd)
                tty.setcbreak(self.fd)
                if RawTerminal._lock:
                    with RawTerminal._lock:
                        RawTerminal._active_instance = self
                else:
                    RawTerminal._active_instance = self
            except (termios.error, OSError, ValueError):
                self.old_settings = None
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        show_cursor()
        if RawTerminal._lock:
            with RawTerminal._lock:
                RawTerminal._active_instance = None
        else:
            RawTerminal._active_instance = None
        if platform.system() != 'Windows' and self.old_settings is not None:
            try:
                termios.tcflush(self.fd, termios.TCIFLUSH)
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
            except (termios.error, OSError):
                pass


class MouseTerminal(RawTerminal):
    """Context manager for Raw Terminal with SGR Mouse tracking enabled."""
    def __enter__(self):
        res = super().__enter__()
        try:
            sys.stdout.write("\033[?1000h\033[?1002h\033[?1006h")
            sys.stdout.flush()
        except Exception:
            pass
        return res
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            sys.stdout.write("\033[?1000l\033[?1002l\033[?1006l")
            sys.stdout.flush()
        except Exception:
            pass
        super().__exit__(exc_type, exc_val, exc_tb)


def get_home_input_event():
    """
    Read keyboard and mouse events for interactive home search.
    Returns:
      ('CHAR', ch)
      ('BACKSPACE', None)
      ('ENTER', None)
      ('ESC', None)
      ('MOUSE_CLICK', x, y)
      ('MOUSE_MOVE', x, y)
      None
    """
    if platform.system() == 'Windows':
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch in [b'\r', b'\n']:
                return ('ENTER', None)
            elif ch in [b'\x08', b'\x7f']:
                return ('BACKSPACE', None)
            elif ch == b'\x1b':
                return ('ESC', None)
            elif ch in [b'\xe0', b'\x00']:
                ch2 = msvcrt.getch()
                if ch2 == b'S':
                    return ('BACKSPACE', None)
                return None
            else:
                try:
                    return ('CHAR', ch.decode('utf-8'))
                except Exception:
                    return None
        return None
    else:
        fd = sys.stdin.fileno()
        if not select.select([fd], [], [], 0.05)[0]:
            return None
        try:
            ch_bytes = os.read(fd, 1)
        except (OSError, IOError):
            return None
        if not ch_bytes:
            return None
            
        if ch_bytes == b'\x03':  # Ctrl+C
            raise KeyboardInterrupt
        if ch_bytes in [b'\r', b'\n']:
            return ('ENTER', None)
        if ch_bytes in [b'\x7f', b'\x08']:
            return ('BACKSPACE', None)
            
        if ch_bytes == b'\x1b':
            seq = ch_bytes.decode('utf-8', errors='ignore')
            end_time = time.time() + 0.03
            while time.time() < end_time:
                if select.select([fd], [], [], 0.005)[0]:
                    try:
                        nb = os.read(fd, 1)
                        if nb:
                            seq += nb.decode('utf-8', errors='ignore')
                            if seq.startswith('\x1b[<') and (seq.endswith('M') or seq.endswith('m')):
                                m = re.match(r'\x1b\[<(\d+);(\d+);(\d+);([Mm])', seq)
                                if m:
                                    btn, x, y, act = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
                                    if act == 'M' and btn == 0:
                                        return ('MOUSE_CLICK', x, y)
                                    elif btn == 35:
                                        return ('MOUSE_MOVE', x, y)
                                break
                            if seq == '\x1b[3~':
                                return ('BACKSPACE', None)
                    except (OSError, IOError):
                        break
                else:
                    break
            if seq == '\x1b':
                return ('ESC', None)
            return None
            
        try:
            char_str = ch_bytes.decode('utf-8')
            if char_str.isprintable() or char_str == ' ':
                return ('CHAR', char_str)
        except Exception:
            pass
        return None


def restore_terminal_for_input():
    """Temporarily restore normal terminal mode for user input (like Prompt.ask).
    
    Call this before using Rich's Prompt.ask() or similar input functions
    while inside a RawTerminal context. Call enter_raw_mode_after_input() after.
    """
    show_cursor()
    if platform.system() == 'Windows':
        return  # Not needed on Windows
    
    instance = RawTerminal._active_instance
    if instance and instance.old_settings is not None:
        try:
            termios.tcsetattr(instance.fd, termios.TCSADRAIN, instance.old_settings)
        except (termios.error, OSError):
            pass


def enter_raw_mode_after_input():
    """Re-enter raw/cbreak mode after using restore_terminal_for_input().
    
    Call this after using Rich's Prompt.ask() or similar input functions.
    """
    hide_cursor()
    if platform.system() == 'Windows':
        return  # Not needed on Windows
    
    instance = RawTerminal._active_instance
    if instance and instance.old_settings is not None:
        try:
            tty.setcbreak(instance.fd)
        except (termios.error, OSError):
            pass


def flush_stdin():
    """Flush any pending input from stdin to prevent buffered keypresses from being read."""
    if platform.system() == 'Windows':
        # Windows: consume all pending input
        while msvcrt.kbhit():
            msvcrt.getch()
    else:
        # Unix: flush input buffer
        try:
            fd = sys.stdin.fileno()
            termios.tcflush(fd, termios.TCIFLUSH)
        except (termios.error, OSError, ValueError):
            pass


def get_idm_path():
    """Check for Internet Download Manager executable on Windows."""
    if platform.system() != 'Windows':
        return None
    
    paths = [
        r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe",
        r"C:\Program Files\Internet Download Manager\IDMan.exe"
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def sanitize_download_filename(filename):
    """Return a filesystem-safe filename for downloads."""
    filename = os.path.basename((filename or "").strip())
    if not filename:
        filename = "download.mp4"

    name, ext = os.path.splitext(filename)
    system = platform.system()

    if system == 'Windows':
        name = _WINDOWS_INVALID_FILENAME_CHARS.sub("_", name).rstrip(" .")
        ext = _WINDOWS_INVALID_FILENAME_CHARS.sub("_", ext).rstrip(" .")

        if not name:
            name = "download"

        if name.upper() in _WINDOWS_RESERVED_FILENAMES:
            name = f"{name}_"
    else:
        name = name.replace("/", "_").replace("\\", "_")
        ext = ext.replace("/", "_").replace("\\", "_")
        if not name:
            name = "download"

    if ext and not ext.startswith("."):
        ext = f".{ext}"

    safe_name = f"{name}{ext}" if ext else name

    # Keep headroom for parent path length on systems with tighter limits.
    if len(safe_name) > 240:
        max_name_len = max(1, 240 - len(ext))
        safe_name = f"{name[:max_name_len]}{ext}" if ext else name[:240]

    return safe_name


def _show_centered_download_message(console, title, message, is_error=False, duration=1.3):
    border_style = "#ff6b6b" if is_error else COLOR_BORDER
    body = Text(message, justify="center", style=f"bold {COLOR_SUBTITLE}" if not is_error else "bold white")
    panel = Panel(
        Align.center(body, vertical="middle"),
        title=f"[bold {COLOR_TITLE}]{title}[/bold {COLOR_TITLE}]",
        box=HEAVY,
        border_style=border_style,
        padding=(1, 4),
        width=min(72, console.width - 4),
    )

    with Live(
        Align.center(panel, vertical="middle", height=console.height),
        console=console,
        refresh_per_second=10,
        screen=True,
    ):
        time.sleep(max(0.5, duration))


def _download_with_idm(url, filename, download_dir):
    idm_path = get_idm_path()
    if not idm_path:
        return False

    try:
        subprocess.Popen([
            idm_path,
            '/d', url,
            '/p', download_dir,
            '/f', filename,
            '/n',
            '/a',
            '/s'
        ])
        return True
    except Exception:
        return False


def _download_with_aria2(url, filename, download_dir, filepath, console):
    aria2_path = shutil.which("aria2c")
    if not aria2_path:
        return False

    spinner = Spinner("bouncingBar", text=Text(" Downloading with aria2c...", style="bold white"))
    panel = Panel(
        Align.center(spinner, vertical="middle"),
        title=f"[bold {COLOR_TITLE}]Accelerated Download[/bold {COLOR_TITLE}]",
        box=HEAVY,
        border_style=COLOR_BORDER,
        padding=(1, 4),
        width=min(72, console.width - 4),
    )

    cmd = [
        aria2_path,
        url,
        "--dir", download_dir,
        "--out", filename,
        "--file-allocation=none",
        "--split=16",
        "--max-connection-per-server=16",
        "--min-split-size=1M",
        "--console-log-level=error",
        "--summary-interval=0",
        "--download-result=hide",
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ]

    try:
        with Live(
            Align.center(panel, vertical="middle", height=console.height),
            console=console,
            refresh_per_second=12,
            screen=True,
        ):
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
    except Exception:
        return False

    _show_centered_download_message(console, "Download Complete", filepath, is_error=False, duration=1.0)
    return True


def _download_with_builtin(url, filename, filepath, console):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    last_error = None

    for _ in range(2):
        try:
            with requests.get(url, stream=True, headers=headers, timeout=(10, 45)) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))

                progress = Progress(
                    TextColumn(f"[bold {COLOR_TITLE}]{{task.fields[filename]}}", justify="center"),
                    BarColumn(bar_width=32, complete_style=f"bold {COLOR_BORDER}", finished_style=f"bold {COLOR_BOLT}"),
                    "[bold white]{task.percentage:>3.1f}%",
                    "•",
                    DownloadColumn(binary_units=True),
                    "•",
                    TransferSpeedColumn(),
                    "•",
                    TimeRemainingColumn(),
                    console=console,
                    expand=False,
                )

                panel = Panel(
                    Align.center(progress, vertical="middle"),
                    title=f"[bold {COLOR_TITLE}]Downloading Episode[/bold {COLOR_TITLE}]",
                    subtitle=Text("saving to downloads directory", style=f"bold {COLOR_SUBTITLE}"),
                    box=HEAVY,
                    border_style=COLOR_BORDER,
                    padding=(1, 3),
                    width=min(88, console.width - 4),
                )

                with Live(
                    Align.center(panel, vertical="middle", height=console.height),
                    console=console,
                    refresh_per_second=16,
                    screen=True,
                ):
                    progress.start()
                    try:
                        task_id = progress.add_task("download", filename=filename, total=total_size if total_size > 0 else None)
                        with open(filepath, 'wb') as file_handle:
                            for chunk in response.iter_content(chunk_size=32768):
                                if not chunk:
                                    continue
                                file_handle.write(chunk)
                                progress.update(task_id, advance=len(chunk))
                    finally:
                        progress.stop()

            _show_centered_download_message(console, "Download Complete", filepath, is_error=False, duration=1.0)
            return True
        except requests.RequestException as error:
            last_error = error

    if last_error:
        raise last_error

    raise RuntimeError("Download failed")

def download_file(url, filename, console, mode="internal", download_dir=None):
    from .logger import logger
    filename = sanitize_download_filename(filename)

    # Use absolute path for compatibility with external tools (IDM/aria2)
    resolved_dir = os.path.abspath((download_dir or "downloads").strip() or "downloads")
    download_dir = resolved_dir
    os.makedirs(download_dir, exist_ok=True)
    filepath = os.path.join(download_dir, filename)

    selected_mode = (mode or "internal").lower()
    valid_modes = {"internal", "aria2c", "idm", "auto"}
    if selected_mode not in valid_modes:
        selected_mode = "internal"

    if selected_mode == "auto":
        if get_idm_path():
            selected_mode = "idm"
        elif shutil.which("aria2c"):
            selected_mode = "aria2c"
        else:
            selected_mode = "internal"

    logger.debug("DOWNLOAD", f"Starting download of '{filename}' via mode '{selected_mode}' from {url[:60]}...")
    success = False
    try:
        if selected_mode == "idm":
            if _download_with_idm(url, filename, download_dir):
                _show_centered_download_message(
                    console,
                    "Queued in IDM",
                    f"{filename}\nQueued successfully in Internet Download Manager.",
                    is_error=False,
                    duration=1.2,
                )
                success = True
                return True

            _show_centered_download_message(
                console,
                "IDM Not Found",
                "IDM is not installed. Falling back to built-in downloader.",
                is_error=False,
                duration=1.0,
            )
            selected_mode = "internal"

        if selected_mode == "aria2c":
            if _download_with_aria2(url, filename, download_dir, filepath, console):
                success = True
                return True

            _show_centered_download_message(
                console,
                "aria2c Fallback",
                "aria2c is unavailable or failed. Falling back to built-in downloader.",
                is_error=False,
                duration=1.0,
            )
            selected_mode = "internal"

        if selected_mode == "internal":
            success = _download_with_builtin(url, filename, filepath, console)
            return success

        return False
    except KeyboardInterrupt:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass

        _show_centered_download_message(
            console,
            "Download Cancelled",
            "The download was cancelled by user.",
            is_error=True,
            duration=1.0,
        )
        return False
    except Exception as error:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass

        _show_centered_download_message(
            console,
            "Download Failed",
            str(error),
            is_error=True,
            duration=1.8,
        )
        return False
    finally:
        logger.log_downloader(selected_mode, url, filename, success)

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC_SUPPORT = True
except ImportError:
    HAS_ARABIC_SUPPORT = False

def ar(text: Optional[str]) -> str:
    """Proper Arabic shaping and BiDi reordering for terminal display."""
    if not text or not HAS_ARABIC_SUPPORT:
        return str(text or "").strip()
    try:
        raw_str = str(text).strip()
        if any("\u0600" <= c <= "\u06FF" or "\u0750" <= c <= "\u077F" or "\u08A0" <= c <= "\u08FF" or "\uFB50" <= c <= "\uFDFF" or "\uFE70" <= c <= "\uFEFF" for c in raw_str):
            reshaper = arabic_reshaper.ArabicReshaper(
                configuration={
                    'delete_harakat': True,
                    'support_ligatures': True,
                    'shift_harakat_position': False,
                    'language': 'Arabic'
                }
            )
            reshaped = reshaper.reshape(raw_str)
            return get_display(reshaped)
    except Exception:
        pass
    return str(text or "").strip()


def ar_wrap(text: Optional[str], width: int = 34) -> str:
    """Wrap Arabic text on word boundaries and shape each line with BiDi without double-wrap overflow."""
    if not text:
        return ""
    import textwrap
    clean_text = " ".join(str(text).split())
    safe_width = max(16, width)
    lines = textwrap.wrap(clean_text, width=safe_width)
    return "\n".join(ar(line) for line in lines)


AR_TO_EN_GENRES = {
    "أكشن": "Action",
    "مغامرات": "Adventure",
    "كوميديا": "Comedy",
    "دراما": "Drama",
    "خيال": "Fantasy",
    "خارق للطبيعة": "Supernatural",
    "سحر": "Magic",
    "غموض": "Mystery",
    "رعب": "Horror",
    "نفسي": "Psychological",
    "رومانسي": "Romance",
    "خيال علمي": "Sci-Fi",
    "شريحة من الحياة": "Slice of Life",
    "رياضي": "Sports",
    "إثارة": "Suspense",
    "تشويق": "Thriller",
    "شونين": "Shounen",
    "شوجو": "Shoujo",
    "سينين": "Seinen",
    "جوسي": "Josei",
    "ميكا": "Mecha",
    "موسيقى": "Music",
    "عسكري": "Military",
    "مدرسي": "School",
    "تاريخي": "Historical",
    "فضاء": "Space",
    "حريم": "Harem",
    "إيسيكاي": "Isekai",
    "ألعاب": "Game",
    "فنون قتالية": "Martial Arts",
    "مصاصو دماء": "Vampires",
    "شياطين": "Demons",
    "ساموراي": "Samurai",
    "قوى خارقة": "Super Power",
    "محاكاة ساخرة": "Parody",
    "بوليسي": "Police",
    "أنثروبولوجي": "Anthropology",
    "إياشيكي": "Iyashikei",
    "الحياة اليومية": "Daily Life",
}

AR_TO_EN_TYPES = {
    "مسلسل": "TV",
    "فيلم": "Movie",
    "أوفا": "OVA",
    "أونا": "ONA",
    "خاصة": "Special",
    "حلقة خاصة": "Special",
    "حلقة خاصة تلفزيونية": "TV Special",
    "مستمر": "Airing",
    "مكتمل": "Completed",
}

def clean_genre(g: Optional[str]) -> str:
    """Return clean standard English/Latin genre label to avoid terminal font spacing bugs."""
    if not g:
        return ""
    g_str = str(g).strip()
    return AR_TO_EN_GENRES.get(g_str, g_str)

def clean_type(t: Optional[str]) -> str:
    """Return clean standard type label (TV, Movie, OVA, Special, etc.)."""
    if not t:
        return "TV"
    t_str = str(t).strip()
    return AR_TO_EN_TYPES.get(t_str, t_str)

def clean_status(s: Optional[str]) -> str:
    """Return clean standard status label (Completed, Airing, etc.)."""
    if not s:
        return "Completed"
    s_str = str(s).strip()
    return AR_TO_EN_TYPES.get(s_str, s_str)
