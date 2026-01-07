import os
import sys
import time
import shutil
import subprocess
import threading
import platform
import requests
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.prompt import Confirm

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

def is_bundled():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def _enter_raw_mode():
    """Enter raw mode for the terminal (Linux/macOS only). Called once at start of menu."""
    global _linux_terminal_fd, _linux_old_settings, _linux_raw_mode
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


def restore_terminal_for_input():
    """Temporarily restore normal terminal mode for user input (like Prompt.ask).
    
    Call this before using Rich's Prompt.ask() or similar input functions
    while inside a RawTerminal context. Call enter_raw_mode_after_input() after.
    """
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

def download_file(url, filename, console):
    # Use absolute path for compatibility with external tools (IDM/aria2)
    download_dir = os.path.abspath("downloads")
    os.makedirs(download_dir, exist_ok=True)
    filepath = os.path.join(download_dir, filename)

    # 1. Check for IDM (Windows Only)
    idm_path = get_idm_path()
    if idm_path:
        # Prompt the user to use IDM if found
        use_idm = Confirm.ask("[bold cyan]Internet Download Manager detected.[/bold cyan] Use it?", default=True, console=console)
        
        if use_idm:
            try:
                console.print("[green]Sending to IDM...[/green]")
                # /d: URL, /p: Local Path, /f: Local Filename, /n: Silent
                # /a: Add to queue, /s: Start queue
                subprocess.Popen([
                    idm_path, 
                    '/d', url, 
                    '/p', download_dir, 
                    '/f', filename,
                    '/n', 
                    '/a', # Add to queue
                    '/s'  # Start queue
                ])
                console.print("[bold green]✓ Added to IDM Queue.[/bold green]")
                console.print(f"[dim]File: {filename}[/dim]")
                
                # Added Manual Start Message
                console.print("[yellow]⚠ Note: If the download does not start automatically, please open IDM and click 'Start Queue'.[/yellow]")
                
                input("\nPress ENTER to continue...")
                return True
            except Exception as e:
                console.print(f"[red]Failed to start IDM: {e}[/red]")
                # Fallback to other methods if IDM fails

    # 2. Try using aria2c (Fast Method) with cleaner output
    aria2_path = shutil.which("aria2c")
    if aria2_path:
        console.print("[bold green]🚀 Starting aria2c download...[/bold green]")
        try:
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
            
            subprocess.run(cmd, check=True)
            
            console.print(f"\n[bold green]✓ Download complete:[/bold green] {filepath}")
            input("\nPress ENTER to continue...")
            return True
            
        except subprocess.CalledProcessError:
             console.print("[yellow]⚠ aria2c error. Switching to standard downloader...[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠ Error running aria2c: {e}. Switching...[/yellow]")

    # 3. Fallback to Requests (Standard Clean UI)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        with requests.get(url, stream=True, headers=headers) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                TransferSpeedColumn(),
                "•",
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task_id = progress.add_task("download", filename=filename, total=total_size)
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        progress.update(task_id, advance=len(chunk))
            
            console.print(f"\n[bold green]✓ Download complete:[/bold green] {filepath}")
            input("\nPress ENTER to continue...")
            return True
    except Exception as e:
        console.print(f"\n[bold red]✗ Download failed:[/bold red] {e}")
        input("\nPress ENTER to continue...")
        return False