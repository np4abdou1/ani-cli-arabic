"""
Logging and crash reporting system for ani-cli-arabic.
Captures local debug logs, records structured crash dumps, and dispatches
diagnostic crash telemetry to the operational dashboard.
"""

import os
import sys
import json
import time
import logging
import platform
import traceback
import threading
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any, Dict, List

from .version import APP_VERSION

CRASH_ENDPOINTS = [
    "https://anicliar-dashboard.pages.dev/monitor",
    "https://ani-cli-arabic-analytics.talego4955.workers.dev/monitor"
]
CLIENT_AUTH_KEY = "6rK9z0XyW8vQ3J7pL2mN4sB1tH5gD0fA"


def get_base_dir() -> Path:
    try:
        base = Path.home() / ".ani-cli-arabic"
    except Exception:
        import tempfile
        base = Path(tempfile.gettempdir()) / ".ani-cli-arabic"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_system_summary() -> str:
    if "ANDROID_ROOT" in os.environ or "com.termux" in os.environ.get("PREFIX", ""):
        return "Android (Termux)"
    sys_name = platform.system()
    if sys_name == "Darwin":
        return "macOS"
    if sys_name == "Windows":
        rel = platform.release()
        return f"Windows {rel}" if rel else "Windows"
    if sys_name == "Linux":
        try:
            info = platform.freedesktop_os_release()
            name = info.get("NAME") or info.get("ID")
            if name:
                return f"Linux ({name})"
        except Exception:
            pass
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("NAME="):
                            return f"Linux ({line.split('=', 1)[1].strip('\"\'')})"
            except Exception:
                pass
        return "Linux"
    return sys_name or "Unknown"


class DebugLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DebugLogger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._enabled = False
        self._console_mirror = False
        self._log_file: Optional[Path] = None
        self._logger = logging.getLogger("ani_cli_arabic")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False
        self._file_handler: Optional[logging.FileHandler] = None

    def enable(self, console_mirror: bool = False):
        self._enabled = True
        self._console_mirror = console_mirror

        if self._file_handler is None:
            self._log_file = get_base_dir() / "debug.log"
            self._file_handler = logging.FileHandler(self._log_file, mode="a", encoding="utf-8")
            formatter = logging.Formatter(
                fmt="[%(asctime)s.%(msecs)03d] [%(levelname)-7s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            self._file_handler.setFormatter(formatter)
            self._logger.addHandler(self._file_handler)

        self.info(f"Debug logger initialized (PID: {os.getpid()}, Python: {sys.version.split()[0]}, Platform: {get_system_summary()})")

    def disable(self):
        self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled

    def _format_msg(self, category: str, message: str) -> str:
        return f"[{category.upper()}] {message}"

    def debug(self, category_or_msg: str, message: Optional[str] = None):
        if not self._enabled:
            return
        cat = "SYSTEM" if message is None else category_or_msg
        msg = category_or_msg if message is None else message
        formatted = self._format_msg(cat, msg)
        self._logger.debug(formatted)
        if self._console_mirror:
            print(f"\033[90m[DEBUG] {formatted}\033[0m", file=sys.stderr)

    def info(self, category_or_msg: str, message: Optional[str] = None):
        if not self._enabled:
            return
        cat = "SYSTEM" if message is None else category_or_msg
        msg = category_or_msg if message is None else message
        formatted = self._format_msg(cat, msg)
        self._logger.info(formatted)
        if self._console_mirror:
            print(f"\033[36m[INFO] {formatted}\033[0m", file=sys.stderr)

    def warning(self, category_or_msg: str, message: Optional[str] = None):
        if not self._enabled:
            return
        cat = "SYSTEM" if message is None else category_or_msg
        msg = category_or_msg if message is None else message
        formatted = self._format_msg(cat, msg)
        self._logger.warning(formatted)
        if self._console_mirror:
            print(f"\033[33m[WARN] {formatted}\033[0m", file=sys.stderr)

    def error(self, category_or_msg: str, message: Optional[str] = None, exc_info: bool = False):
        cat = "SYSTEM" if message is None else category_or_msg
        msg = category_or_msg if message is None else message
        formatted = self._format_msg(cat, msg)
        if self._enabled:
            self._logger.error(formatted, exc_info=exc_info)
        if self._console_mirror:
            print(f"\033[31m[ERROR] {formatted}\033[0m", file=sys.stderr)

    def log_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        duration: Optional[float] = None,
        error: Optional[Exception] = None
    ):
        if not self._enabled:
            return
        dur_str = f" in {duration:.3f}s" if duration is not None else ""
        if error:
            self.error("API", f"{method} {url}{dur_str} -> FAILED: {error}")
        else:
            status_str = f" -> HTTP {status_code}" if status_code is not None else ""
            self.debug("API", f"{method} {url}{dur_str}{status_str}")
            if params:
                self.debug("API", f"  Params: {params}")

    def log_crypto(self, action: str, details: str = ""):
        if not self._enabled:
            return
        self.debug("CRYPTO", f"{action} | {details}" if details else action)

    def log_player(
        self,
        player_name: str,
        cmd_args: List[str],
        exit_code: Optional[int] = None,
        stderr_output: Optional[str] = None,
        duration: Optional[float] = None
    ):
        if not self._enabled:
            return
        dur_str = f" duration: {duration:.1f}s," if duration is not None else ""
        if exit_code is not None:
            level = "PLAYER" if exit_code == 0 else "PLAYER_ERR"
            msg = f"{player_name} exited with code {exit_code} ({dur_str} args: {cmd_args})"
            if exit_code == 0:
                self.debug(level, msg)
            else:
                self.warning(level, msg)
                if stderr_output:
                    self.warning(level, f"  stderr: {stderr_output.strip()[:400]}")
        else:
            self.debug("PLAYER", f"Spawning {player_name} with command: {' '.join(cmd_args)}")

    def log_downloader(self, mode: str, url: str, filename: str, success: bool, error: Optional[str] = None):
        if not self._enabled:
            return
        if success:
            self.info("DOWNLOAD", f"[{mode}] Successfully downloaded '{filename}' from {url[:60]}...")
        else:
            self.error("DOWNLOAD", f"[{mode}] Download failed for '{filename}' from {url[:60]}... Reason: {error or 'Unknown'}")

    def log_exception(self, exc: Exception, context: str = ""):
        if not self._enabled:
            return
        ctx_str = f" in {context}" if context else ""
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self.error("CRASH", f"Unhandled Exception{ctx_str}: {exc}\n{tb}")


logger = DebugLogger()


def send_crash_telemetry(payload_dict: Dict[str, Any]):
    """Sends crash diagnostics asynchronously to the dashboard worker."""
    def _worker():
        try:
            data = json.dumps(payload_dict).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "X-Auth-Key": CLIENT_AUTH_KEY,
                "User-Agent": f"AniCliAr-CrashReporter/1.0 ani-cli-arabic/{APP_VERSION}"
            }
            for endpoint in CRASH_ENDPOINTS:
                try:
                    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=3.0) as resp:
                        if resp.status in (200, 204):
                            return
                except Exception:
                    continue
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=1.5)


def record_crash(exc_type, exc_value, exc_traceback, context: str = "unhandled"):
    """
    Writes a local crash dump and transmits crash telemetry to the dashboard.
    """
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    iso_timestamp = datetime.now(timezone.utc).isoformat()
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    # Retrieve hardware fingerprint if available
    fingerprint = "unknown"
    try:
        from .monitoring import monitor
        fingerprint = monitor.user_fingerprint
    except Exception:
        pass

    crash_data = {
        "timestamp": iso_timestamp,
        "app_version": APP_VERSION,
        "python_version": platform.python_version(),
        "os": get_system_summary(),
        "platform_raw": platform.platform(),
        "context": context,
        "command_args": sys.argv,
        "error_type": getattr(exc_type, "__name__", "Exception"),
        "error_message": str(exc_value),
        "traceback": tb_str,
        "fingerprint": fingerprint
    }

    # Save to local ~/.ani-cli-arabic/crashes/
    crash_dir = get_base_dir() / "crashes"
    crash_dir.mkdir(parents=True, exist_ok=True)
    dump_file = crash_dir / f"crash_{timestamp_str}.json"

    try:
        with open(dump_file, "w", encoding="utf-8") as f:
            json.dump(crash_data, f, indent=2)
    except Exception:
        pass

    # Append to debug.log
    logger.error("CRASH", f"Unhandled Exception ({crash_data['error_type']}): {crash_data['error_message']}\n{tb_str}")

    # Dispatch to remote analytics worker
    telemetry_payload = {
        "fingerprint": fingerprint,
        "timestamp": iso_timestamp,
        "action": "error_crash",
        "details": {
            "error_type": crash_data["error_type"],
            "message": crash_data["error_message"],
            "traceback": tb_str,
            "version": APP_VERSION,
            "os": crash_data["os"],
            "args": sys.argv,
            "context": context
        }
    }
    send_crash_telemetry(telemetry_payload)

    # Terminal alert
    print(f"\n\033[1;31m[!] ani-cli-arabic encountered an unexpected error:\033[0m")
    print(f"    \033[31m{crash_data['error_type']}: {crash_data['error_message']}\033[0m")
    print(f"\033[90m    Crash dump saved to: {dump_file}\033[0m")
    print(f"\033[90m    Crash report automatically submitted to diagnostics center.\033[0m\n")


def install_global_exception_handler():
    """Installs sys.excepthook to trap and report any unhandled crashes."""
    original_excepthook = sys.excepthook

    def custom_excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            original_excepthook(exc_type, exc_value, exc_traceback)
            return

        record_crash(exc_type, exc_value, exc_traceback, context="global_unhandled")

    sys.excepthook = custom_excepthook
