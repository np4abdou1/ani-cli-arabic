import os
import sys
import shutil
import subprocess
import requests
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.prompt import Confirm

if os.name == 'nt':
    import msvcrt
else:
    import tty
    import termios
    import select

def is_bundled():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_key():
    if os.name == 'nt':
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\xe0' or key == b'\x00':
                key2 = msvcrt.getch()
                if key2 == b'H': return 'UP'
                elif key2 == b'P': return 'DOWN'
                elif key2 == b'M': return 'RIGHT'
                elif key2 == b'K': return 'LEFT'
            elif key == b'\r': return 'ENTER'
            elif key == b'\x1b': return 'ESC'
            elif key == b'q' or key == b'Q': return 'q'
            elif key == b'g' or key == b'G': return 'g'
            elif key == b'b' or key == b'B': return 'b'
            elif key == b'd' or key == b'D': return 'd'
            elif key == b'l' or key == b'L': return 'l'  # <--- Added 'L' key
            elif key == b'/' or key == b'?': return '/'
            else: return key.decode('utf-8', errors='ignore')
        return None
    else:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            if select.select([sys.stdin], [], [], 0.01)[0]:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A': return 'UP'
                        elif ch3 == 'B': return 'DOWN'
                        elif ch3 == 'C': return 'RIGHT'
                        elif ch3 == 'D': return 'LEFT'
                    return 'ESC'
                elif ch == '\r' or ch == '\n': return 'ENTER'
                elif ch == 'q' or ch == 'Q': return 'q'
                elif ch == 'g' or ch == 'G': return 'g'
                elif ch == 'b' or ch == 'B': return 'b'
                elif ch == 'd' or ch == 'D': return 'd'
                elif ch == 'l' or ch == 'L': return 'l'  # <--- Added 'L' key
                elif ch == '/' or ch == '?': return '/'
                return ch
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def get_idm_path():
    """Check for Internet Download Manager executable on Windows."""
    if os.name != 'nt':
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
        use_idm = Confirm.ask(f"[bold cyan]Internet Download Manager detected.[/bold cyan] Use it?", default=True, console=console)
        
        if use_idm:
            try:
                console.print(f"[green]Sending to IDM...[/green]")
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
                console.print(f"[bold green]✓ Added to IDM Queue.[/bold green]")
                console.print(f"[dim]File: {filename}[/dim]")
                
                # Added Manual Start Message
                console.print(f"[yellow]⚠ Note: If the download does not start automatically, please open IDM and click 'Start Queue'.[/yellow]")
                
                input("\nPress ENTER to continue...")
                return True
            except Exception as e:
                console.print(f"[red]Failed to start IDM: {e}[/red]")
                # Fallback to other methods if IDM fails

    # 2. Try using aria2c (Fast Method) with cleaner output
    aria2_path = shutil.which("aria2c")
    if aria2_path:
        console.print(f"[bold green]🚀 Starting aria2c download...[/bold green]")
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