"""
Unit tests for src/monitoring.py
Tests deep OS detection, deterministic fingerprinting, event telemetry dispatching,
non-blocking execution, and privacy opt-out compliance.
"""

import os
import json
import time
import platform
import threading
import urllib.request
import urllib.error
import sys
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.monitoring import (
    get_os_info,
    get_detailed_os,
    get_hardware_fingerprint,
    get_base_dir,
    MonitoringSystem,
    monitor,
    ANALYTICS_ENDPOINTS,
    CLIENT_AUTH_KEY,
)
from src.version import APP_VERSION


class TestDeepOSDetection:
    """Test deep OS and Linux distribution identification."""

    def test_get_os_info_real_system(self):
        info = get_os_info()
        assert isinstance(info, dict)
        for key in ("os_name", "distro", "base", "os_version"):
            assert key in info
            assert isinstance(info[key], str)
            assert len(info[key]) > 0

    def test_get_os_info_arch_linux(self):
        mock_data = {
            "ID": "arch",
            "NAME": "Arch Linux",
            "PRETTY_NAME": "Arch Linux",
            "BUILD_ID": "rolling"
        }
        with patch("platform.system", return_value="Linux"), \
             patch("platform.freedesktop_os_release", return_value=mock_data), \
             patch("platform.release", return_value="6.12.1-arch1-1"):
            info = get_os_info()
            assert info["os_name"] == "Linux"
            assert info["distro"] == "Arch Linux"
            assert info["base"] == "Arch"
            assert info["os_version"] == "6.12.1-arch1-1"

    def test_get_os_info_debian_ubuntu_family(self):
        ubuntu_data = {
            "ID": "ubuntu",
            "ID_LIKE": "debian",
            "NAME": "Ubuntu",
            "VERSION_ID": "24.04"
        }
        with patch("platform.system", return_value="Linux"), \
             patch("platform.freedesktop_os_release", return_value=ubuntu_data), \
             patch("platform.release", return_value="6.8.0-generic"):
            info = get_os_info()
            assert info["os_name"] == "Linux"
            assert info["distro"] == "Ubuntu"
            assert info["base"] == "Debian"

        debian_data = {
            "ID": "debian",
            "NAME": "Debian GNU/Linux",
            "VERSION_ID": "12"
        }
        with patch("platform.system", return_value="Linux"), \
             patch("platform.freedesktop_os_release", return_value=debian_data):
            info = get_os_info()
            assert info["distro"] == "Debian"
            assert info["base"] == "Debian"

    def test_get_os_info_redhat_fedora_family(self):
        fedora_data = {
            "ID": "fedora",
            "NAME": "Fedora Linux",
            "VERSION_ID": "40"
        }
        with patch("platform.system", return_value="Linux"), \
             patch("platform.freedesktop_os_release", return_value=fedora_data):
            info = get_os_info()
            assert info["os_name"] == "Linux"
            assert info["distro"] == "Fedora"
            assert info["base"] == "RedHat"

        rhel_data = {
            "ID": "rhel",
            "ID_LIKE": "fedora",
            "NAME": "Red Hat Enterprise Linux"
        }
        with patch("platform.system", return_value="Linux"), \
             patch("platform.freedesktop_os_release", return_value=rhel_data):
            info = get_os_info()
            assert info["distro"] == "RHEL"
            assert info["base"] == "RedHat"

    def test_get_os_info_suse_family(self):
        suse_data = {
            "ID": "opensuse-tumbleweed",
            "ID_LIKE": "opensuse suse",
            "NAME": "openSUSE Tumbleweed"
        }
        with patch("platform.system", return_value="Linux"), \
             patch("platform.freedesktop_os_release", return_value=suse_data):
            info = get_os_info()
            assert info["os_name"] == "Linux"
            assert info["distro"] == "openSUSE"
            assert info["base"] == "SUSE"

    def test_get_os_info_independent_distros(self):
        for distro_id, distro_name in [("alpine", "Alpine"), ("nixos", "NixOS"), ("void", "Void"), ("gentoo", "Gentoo")]:
            data = {"ID": distro_id, "NAME": f"{distro_name} Linux"}
            with patch("platform.system", return_value="Linux"), \
                 patch("platform.freedesktop_os_release", return_value=data):
                info = get_os_info()
                assert info["base"] == "Independent"
                assert info["distro"] == distro_name

    def test_get_os_info_macos(self):
        with patch("platform.system", return_value="Darwin"), \
             patch("platform.mac_ver", return_value=("14.4.1", ("", "", ""), "")), \
             patch.dict(os.environ, {}, clear=True):
            info = get_os_info()
            assert info["os_name"] == "macOS"
            assert info["distro"] == "macOS"
            assert info["base"] == "Darwin"
            assert info["os_version"] == "14.4.1"

    def test_get_os_info_windows(self):
        with patch("platform.system", return_value="Windows"), \
             patch("platform.release", return_value="11"), \
             patch("platform.version", return_value="10.0.22631"), \
             patch.dict(os.environ, {}, clear=True):
            info = get_os_info()
            assert info["os_name"] == "Windows"
            assert info["distro"] == "Windows 11"
            assert info["base"] == "Windows NT"
            assert info["os_version"] == "10.0.22631"

    def test_get_os_info_android_termux(self):
        with patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}):
            info = get_os_info()
            assert info["os_name"] == "Android"
            assert info["distro"] == "Termux"
            assert info["base"] == "Linux"

    def test_get_detailed_os_helper(self):
        with patch("src.monitoring.get_os_info", return_value={
            "os_name": "Linux", "distro": "Arch Linux", "base": "Arch", "os_version": "6.12.1"
        }):
            assert get_detailed_os() == "Linux (Arch Linux)"

        with patch("src.monitoring.get_os_info", return_value={
            "os_name": "macOS", "distro": "macOS", "base": "Darwin", "os_version": "14.4"
        }):
            assert get_detailed_os() == "macOS"

        with patch("src.monitoring.get_os_info", return_value={
            "os_name": "Windows", "distro": "Windows 11", "base": "Windows NT", "os_version": "10.0"
        }):
            assert get_detailed_os() == "Windows 11"

        with patch("src.monitoring.get_os_info", return_value={
            "os_name": "Android", "distro": "Termux", "base": "Linux", "os_version": "6.1"
        }):
            assert get_detailed_os() == "Android (Termux)"


class TestHardwareFingerprinting:
    """Test deterministic hardware fingerprinting."""

    def test_fingerprint_length_and_hex(self):
        fp = get_hardware_fingerprint()
        assert isinstance(fp, str)
        assert len(fp) == 16
        # Must be valid hex
        int(fp, 16)

    def test_fingerprint_deterministic(self):
        fp1 = get_hardware_fingerprint()
        fp2 = get_hardware_fingerprint()
        assert fp1 == fp2

    def test_fingerprint_fallback_file_persistence(self, tmp_path):
        cache_file = tmp_path / "fingerprint"
        real_exists = os.path.exists

        def mock_exists(p):
            if str(p) in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                return False
            return real_exists(p)

        with patch("src.monitoring.get_base_dir", return_value=tmp_path), \
             patch("os.path.exists", side_effect=mock_exists):
            fp = get_hardware_fingerprint()
            assert len(fp) == 16
            assert cache_file.exists()
            assert cache_file.read_text().strip()[:16] == fp

            # Second call reads from cached file
            fp2 = get_hardware_fingerprint()
            assert fp2 == fp


class TestMonitoringSystem:
    """Test MonitoringSystem singleton and event tracking dispatch."""

    def test_singleton_instance(self):
        m1 = MonitoringSystem()
        m2 = MonitoringSystem()
        assert m1 is m2
        assert m1 is monitor

    def test_track_app_start_dispatches_launch_event(self):
        sent_requests = []

        def mock_urlopen(req, timeout=2.0):
            sent_requests.append(req)
            resp = MagicMock()
            resp.status = 200
            resp.__enter__.return_value = resp
            resp.__exit__.return_value = False
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            monitor.track_app_start()
            # Give background thread a moment to execute
            time.sleep(0.1)

        assert len(sent_requests) > 0
        req = sent_requests[0]
        assert req.get_method() == "POST"
        assert req.headers.get("X-auth-key") == CLIENT_AUTH_KEY or req.headers.get("X-Auth-Key") == CLIENT_AUTH_KEY

        payload = json.loads(req.data.decode("utf-8"))
        assert payload["event_type"] == "launch"
        assert "fingerprint" in payload
        assert "os_name" in payload
        assert "distro" in payload
        assert "base" in payload
        assert "os_version" in payload
        assert "python_version" in payload
        assert payload["client_version"] == APP_VERSION

    def test_track_video_play_dispatches_watch_event(self):
        sent_requests = []

        def mock_urlopen(req, timeout=2.0):
            sent_requests.append(req)
            resp = MagicMock()
            resp.status = 200
            resp.__enter__.return_value = resp
            resp.__exit__.return_value = False
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            monitor.track_video_play(
                anime_title="Sousou no Frieren",
                episode=28,
                mode="stream",
                provider="anime3rb",
                duration=1420
            )
            time.sleep(0.1)

        assert len(sent_requests) > 0
        req = sent_requests[0]
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["event_type"] == "watch"
        assert payload["anime_title"] == "Sousou no Frieren"
        assert payload["episode"] == "28"
        assert payload["mode"] == "stream"
        assert payload["provider"] == "anime3rb"
        assert payload["duration"] == 1420
        assert "fingerprint" in payload
        assert "os_name" in payload
        assert "distro" in payload
        assert "base" in payload
        assert "os_version" in payload

    def test_telemetry_respects_opt_out(self):
        sent_requests = []

        def mock_urlopen(req, timeout=2.0):
            sent_requests.append(req)
            return MagicMock(status=200)

        # Mock SettingsManager to return False for analytics
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda k, default=None: False if k == "analytics" else default

        with patch("src.settings.SettingsManager", return_value=mock_settings), \
             patch("urllib.request.urlopen", side_effect=mock_urlopen):
            monitor.track_app_start()
            monitor.track_video_play("Test Anime", 1)
            time.sleep(0.1)

        assert len(sent_requests) == 0

    def test_fail_fast_handles_network_failure(self):
        # Network errors should never raise exceptions in caller
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network unreachable")):
            monitor.track_app_start()
            monitor.track_video_play("Test Anime", 1)
            time.sleep(0.1)
        # Succeeded without raising exception
