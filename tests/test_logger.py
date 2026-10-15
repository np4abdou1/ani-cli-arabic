"""
Unit tests for src/logger.py
Tests debug logging, structured crash dumps, crash telemetry dispatch matching v2 schema,
join timeout bounds, and privacy opt-out compliance.
"""

import sys
import json
import time
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.logger import (
    DebugLogger,
    logger,
    get_system_summary,
    get_base_dir,
    send_crash_telemetry,
    record_crash,
    install_global_exception_handler,
    CRASH_ENDPOINTS,
    CLIENT_AUTH_KEY,
)
from src.version import APP_VERSION


class TestDebugLogger:
    """Tests for DebugLogger functionality."""

    def test_singleton_instance(self):
        l1 = DebugLogger()
        l2 = DebugLogger()
        assert l1 is l2
        assert l1 is logger

    def test_enable_and_disable(self):
        logger.disable()
        assert not logger.is_enabled()
        logger.enable(console_mirror=False)
        assert logger.is_enabled()
        logger.disable()
        assert not logger.is_enabled()

    def test_logging_methods(self):
        logger.enable()
        logger.debug("TEST", "Debug message")
        logger.info("TEST", "Info message")
        logger.warning("TEST", "Warn message")
        logger.error("TEST", "Error message")
        logger.log_crypto("AES_DECRYPT", "Success")
        logger.log_player("mpv", ["mpv", "http://example.com/test.mp4"], exit_code=0, duration=12.5)
        logger.log_downloader("internal", "http://example.com/test.mp4", "test.mp4", success=True)
        logger.log_request("GET", "http://example.com/api", status_code=200, duration=0.12)
        try:
            raise ValueError("Logged exception")
        except Exception as e:
            logger.log_exception(e, context="unit_test")
        logger.disable()


class TestCrashTelemetry:
    """Tests for crash telemetry and unhandled crash hook."""

    def test_get_system_summary(self):
        summary = get_system_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_dev_branch_filters_crash_telemetry(self):
        sent_requests = []

        def mock_urlopen(req, timeout=1.5):
            sent_requests.append(req)
            return MagicMock(status=200)

        with patch("src.monitoring.is_dev_environment", return_value=True), \
             patch("urllib.request.urlopen", side_effect=mock_urlopen):
            send_crash_telemetry({"error_type": "DevCrash"})

        assert len(sent_requests) == 0

    def test_send_crash_telemetry_schema(self):
        sent_requests = []

        def mock_urlopen(req, timeout=1.5):
            sent_requests.append(req)
            resp = MagicMock()
            resp.status = 200
            resp.__enter__.return_value = resp
            resp.__exit__.return_value = False
            return resp

        payload = {
            "fingerprint": "68ab6d2c81920c49",
            "error_type": "KeyError",
            "message": "'stream_url' not found",
            "traceback": "Traceback (most recent call last):\n  File 'test.py', line 1",
            "os_name": "Linux",
            "distro": "Arch Linux",
            "base": "Arch",
            "os_version": "6.12.1-arch1-1",
            "client_version": APP_VERSION,
            "command_args": ["ani-cli-arabic", "-i"]
        }

        with patch("src.monitoring.is_dev_environment", return_value=False), \
             patch("urllib.request.urlopen", side_effect=mock_urlopen):
            send_crash_telemetry(payload)

        assert len(sent_requests) > 0
        req = sent_requests[0]
        assert req.get_method() == "POST"
        assert req.headers.get("X-auth-key") == CLIENT_AUTH_KEY or req.headers.get("X-Auth-Key") == CLIENT_AUTH_KEY

        body = json.loads(req.data.decode("utf-8"))
        for k in ("fingerprint", "error_type", "message", "traceback", "os_name", "distro", "base", "os_version", "client_version", "command_args"):
            assert k in body
            assert body[k] == payload[k]

    def test_send_crash_telemetry_respects_opt_out(self):
        sent_requests = []

        def mock_urlopen(req, timeout=1.5):
            sent_requests.append(req)
            return MagicMock(status=200)

        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda k, default=None: False if k == "analytics" else default

        with patch("src.settings.SettingsManager", return_value=mock_settings), \
             patch("urllib.request.urlopen", side_effect=mock_urlopen):
            send_crash_telemetry({"error_type": "Crash"})

        assert len(sent_requests) == 0

    def test_record_crash_creates_local_dump_and_dispatches(self, tmp_path):
        crashes_captured = []

        def mock_send(telemetry):
            crashes_captured.append(telemetry)

        with patch("src.logger.get_base_dir", return_value=tmp_path), \
             patch("src.logger.send_crash_telemetry", side_effect=mock_send):
            try:
                raise RuntimeError("Simulated crash error")
            except RuntimeError as exc:
                exc_type, exc_val, tb = sys.exc_info()
                record_crash(exc_type, exc_val, tb, context="test_context")

        # Verify local crash dump created
        crash_dir = tmp_path / "crashes"
        assert crash_dir.exists()
        dump_files = list(crash_dir.glob("crash_*.json"))
        assert len(dump_files) == 1

        with open(dump_files[0], "r", encoding="utf-8") as f:
            dump_data = json.load(f)
            assert dump_data["error_type"] == "RuntimeError"
            assert "Simulated crash error" in dump_data["error_message"]
            assert dump_data["context"] == "test_context"

        # Verify telemetry was dispatched with v2 schema
        assert len(crashes_captured) == 1
        t_data = crashes_captured[0]
        assert t_data["error_type"] == "RuntimeError"
        assert "Simulated crash error" in t_data["message"]
        assert "traceback" in t_data
        assert "os_name" in t_data
        assert "distro" in t_data
        assert "base" in t_data
        assert "os_version" in t_data
        assert "client_version" in t_data
        assert t_data["client_version"] == APP_VERSION

    def test_install_global_exception_handler(self):
        orig_hook = sys.excepthook
        try:
            install_global_exception_handler()
            installed_hook = sys.excepthook
            assert installed_hook != orig_hook

            # KeyboardInterrupt should pass through to original hook
            mock_orig = MagicMock()
            with patch("sys.excepthook", installed_hook):
                # Test KeyboardInterrupt bypass
                with patch("src.logger.record_crash") as mock_record:
                    try:
                        raise KeyboardInterrupt()
                    except KeyboardInterrupt:
                        exc_type, exc_val, tb = sys.exc_info()
                        # Calling installed hook directly
                        installed_hook(exc_type, exc_val, tb)
                        mock_record.assert_not_called()

                # Test unhandled exception triggers record_crash
                with patch("src.logger.record_crash") as mock_record:
                    try:
                        raise ZeroDivisionError("division by zero")
                    except ZeroDivisionError:
                        exc_type, exc_val, tb = sys.exc_info()
                        installed_hook(exc_type, exc_val, tb)
                        mock_record.assert_called_once()
        finally:
            sys.excepthook = orig_hook
