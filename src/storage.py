import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: Any, indent: int = 4, ensure_ascii: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=indent, ensure_ascii=ensure_ascii)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass


def cleanup_temporary_files() -> None:
    """Safely cleans up stale sockets, temp files, and prunes old logs on startup."""
    import glob
    import time
    
    # 1. Clean stale MPV IPC sockets older than 1 hour or unlinked
    try:
        tmp_dir = tempfile.gettempdir()
        now = time.time()
        for sock in glob.glob(os.path.join(tmp_dir, "ani_mpv_*.sock")):
            try:
                if now - os.path.getmtime(sock) > 3600:
                    os.remove(sock)
            except OSError:
                pass
    except Exception:
        pass

    # 2. Clean orphaned .tmp database files
    try:
        db_dir = Path.home() / ".ani-cli-arabic" / "database"
        if db_dir.exists():
            for tmp_file in db_dir.glob(".*.tmp"):
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass
    except Exception:
        pass

    # 3. Prune old log files (keep latest 20)
    try:
        log_dir = Path.home() / ".ani-cli-arabic" / "logs"
        if log_dir.exists():
            log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old_log in log_files[20:]:
                try:
                    old_log.unlink(missing_ok=True)
                except OSError:
                    pass
    except Exception:
        pass