"""
Debug Logging System for ani-cli-arabic
Provides comprehensive, zero-overhead debug logging for CLI events, API requests,
crypto/token operations, player launches/exits, download tasks, and uncaught crashes.
Turned OFF by default.
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List


class DebugLogger:
    """
    Centralized Debug Logger.
    When enabled (via settings or --debug flag), writes timestamped structured logs
    to ~/.ani-cli-arabic/debug.log and optionally mirrors to stderr.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DebugLogger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._enabled = False
        self._console_mirror = False
        self._log_file: Optional[Path] = None
        self._logger = logging.getLogger("ani_cli_arabic")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False
        self._file_handler: Optional[logging.FileHandler] = None

    def _setup_log_file(self) -> Path:
        log_dir = Path.home() / ".ani-cli-arabic"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "debug.log"

    def enable(self, console_mirror: bool = False):
        """Enable debug logging and initialize file handler."""
        self._enabled = True
        self._console_mirror = console_mirror

        if self._file_handler is None:
            self._log_file = self._setup_log_file()
            # Append mode with clean utf-8 formatting
            self._file_handler = logging.FileHandler(self._log_file, mode="a", encoding="utf-8")
            formatter = logging.Formatter(
                fmt="[%(asctime)s.%(msecs)03d] [%(levelname)-7s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            self._file_handler.setFormatter(formatter)
            self._logger.addHandler(self._file_handler)

        self.info(f"=== Debug Logging Initialized (PID: {os.getpid()}, Python: {sys.version.split()[0]}, Platform: {sys.platform}) ===")

    def disable(self):
        """Disable debug logging."""
        if self._enabled:
            self.info("=== Debug Logging Disabled ===")
            self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled

    def get_log_file_path(self) -> Optional[str]:
        return str(self._log_file) if self._log_file else str(self._setup_log_file())

    def _format_msg(self, category: str, message: str) -> str:
        return f"[{category.upper()}] {message}"

    def debug(self, category: str, message: str):
        if not self._enabled:
            return
        formatted = self._format_msg(category, message)
        self._logger.debug(formatted)
        if self._console_mirror:
            print(f"\033[90m[DEBUG] {formatted}\033[0m", file=sys.stderr)

    def info(self, category_or_msg: str, message: Optional[str] = None):
        if not self._enabled:
            return
        if message is None:
            cat = "SYSTEM"
            msg = category_or_msg
        else:
            cat = category_or_msg
            msg = message
        formatted = self._format_msg(cat, msg)
        self._logger.info(formatted)
        if self._console_mirror:
            print(f"\033[36m[INFO] {formatted}\033[0m", file=sys.stderr)

    def warning(self, category: str, message: str):
        if not self._enabled:
            return
        formatted = self._format_msg(category, message)
        self._logger.warning(formatted)
        if self._console_mirror:
            print(f"\033[33m[WARN] {formatted}\033[0m", file=sys.stderr)

    def error(self, category: str, message: str, exc_info: bool = False):
        if not self._enabled:
            return
        formatted = self._format_msg(category, message)
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
        """Log outgoing network and API request lifecycle."""
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
        """Log cryptography, token generation, seed fetch, or RNCryptor decryption."""
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
        """Log player launch, command arguments, and exit code."""
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
        """Log download task initiation, engine, and completion."""
        if not self._enabled:
            return
        if success:
            self.info("DOWNLOAD", f"[{mode}] Successfully downloaded '{filename}' from {url[:60]}...")
        else:
            self.error("DOWNLOAD", f"[{mode}] Download failed for '{filename}' from {url[:60]}... Reason: {error or 'Unknown'}")

    def log_exception(self, exc: Exception, context: str = ""):
        """Log uncaught exception with full stack trace."""
        if not self._enabled:
            return
        ctx_str = f" in {context}" if context else ""
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self.error("CRASH", f"Unhandled Exception{ctx_str}: {exc}\n{tb}")


# Global logger instance
logger = DebugLogger()


def install_global_exception_handler():
    """Install top-level exception handler to capture unhandled crashes into debug.log."""
    original_excepthook = sys.excepthook

    def custom_excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            original_excepthook(exc_type, exc_value, exc_traceback)
            return
        
        logger.log_exception(exc_value, context="global_unhandled")
        original_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = custom_excepthook
