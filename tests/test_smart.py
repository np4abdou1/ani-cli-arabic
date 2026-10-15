"""
Smart Diagnostics & Regression Test Suite for ani-cli-arabic
Tests provider contracts, scrapers, CLI/TUI logic, settings, history, and player args.
"""

import sys
import tempfile
from pathlib import Path

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import AnimeResult, QualityOption
from src.providers.base import BaseAnimeProvider
from src.providers.manager import ProviderManager
from src.settings import SettingsManager
from src.storage import atomic_write_json
from src.history import HistoryManager
from src.cli import clean_season, clean_episodes, AniCliWrapper


class TestProviderArchitecture:
    """Verifies provider registry, contracts, and method signatures."""

    def test_registered_providers_subclass_base(self):
        choices = ProviderManager.get_provider_choices()
        assert len(choices) >= 4, f"Expected at least 4 provider choices, found {len(choices)}"
        
        for pid in choices:
            prov = ProviderManager.get_provider(pid)
            assert isinstance(prov, BaseAnimeProvider), f"Provider '{pid}' does not inherit from BaseAnimeProvider"
            assert hasattr(prov, "id") and prov.id
            assert hasattr(prov, "name") and prov.name
            assert hasattr(prov, "search_anime")
            assert hasattr(prov, "get_episodes")
            assert hasattr(prov, "get_streaming_servers")

    def test_provider_manager_list_providers(self):
        provs = ProviderManager.list_providers()
        assert isinstance(provs, list)
        assert len(provs) >= 4
        ids = [p["id"] for p in provs]
        assert "anime3rb" in ids
        assert "hianime" in ids

    def test_provider_manager_get_available_providers_bug_reproduction(self):
        """
        Validates whether get_available_providers exists on ProviderManager.
        This reproduces the critical bug reported in -i mode.
        """
        has_attr = hasattr(ProviderManager, "get_available_providers")
        # Record assertion: This should fail until fixed or alias added
        assert has_attr, (
            "CRITICAL BUG REPRODUCED: ProviderManager has no attribute 'get_available_providers'. "
            "Calling this in -i mode crashes with AttributeError!"
        )


class TestScrapersLiveSanity:
    """Live smoke tests for primary providers to verify scraper resilience."""

    def test_anime3rb_search(self):
        p = ProviderManager.get_provider("anime3rb")
        results = p.search_anime("Naruto")
        assert results is not None
        assert len(results) > 0
        first = results[0]
        assert isinstance(first, AnimeResult)
        assert first.id
        assert "naruto" in first.title_en.lower() or "ناروتو" in (first.title_ar or "")

    def test_hianime_search(self):
        p = ProviderManager.get_provider("hianime")
        results = p.search_anime("Naruto")
        assert results is not None
        assert len(results) > 0
        first = results[0]
        assert isinstance(first, AnimeResult)
        assert first.id
        assert "naruto" in first.title_en.lower()

    def test_anime_slayer_search(self):
        p = ProviderManager.get_provider("anime_slayer")
        results = p.search_anime("Naruto")
        assert results is not None
        assert len(results) > 0

    def test_animeify_search(self):
        p = ProviderManager.get_provider("animeify")
        results = p.search_anime("Naruto")
        assert results is not None
        assert len(results) > 0


class TestCliLogicAndHelpers:
    """Tests CLI formatting, season cleaner, and episode sanitizer."""

    def test_clean_season_removes_rtl_and_replaces_arabic(self):
        assert clean_season("خريف 2023") == "Fall 2023"
        assert clean_season("ربيع 2024") == "Spring 2024"
        assert clean_season("صيف 2022") == "Summer 2022"
        assert clean_season("شتاء 2025") == "Winter 2025"
        assert clean_season("N/A") == ""
        assert clean_season("0") == ""
        assert clean_season("?") == ""
        assert clean_season(None) == ""

    def test_clean_episodes(self):
        assert clean_episodes("24") == "24 eps"
        assert clean_episodes("0") == ""
        assert clean_episodes("N/A") == ""
        assert clean_episodes("?") == ""
        assert clean_episodes(None) == ""

    def test_cli_wrapper_initialization(self):
        prov = ProviderManager.get_provider("anime3rb")
        settings = SettingsManager()
        history = HistoryManager()
        wrapper = AniCliWrapper(
            api=prov,
            player=None,
            history=history,
            settings=settings,
            rpc=None
        )
        assert wrapper.api is not None
        assert wrapper.get_theme_color("title") is not None
        assert isinstance(wrapper.autoplay, bool)


class TestSettingsAndStorage:
    """Verifies atomic storage integrity and settings defaults."""

    def test_atomic_write_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "sub" / "data.json"
            sample_data = {"test_key": "test_val", "numbers": [1, 2, 3]}
            atomic_write_json(test_file, sample_data)
            assert test_file.exists()
            import json
            with open(test_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded == sample_data

    def test_settings_manager_defaults(self):
        sm = SettingsManager()
        assert sm.get("default_quality") in ["1080p", "720p", "480p", "best"]
        assert sm.get("anime_provider") is not None
        assert "player" in sm.settings


class TestHistoryAndFavorites:
    """Tests watch history tracking and favorites storage."""

    def test_history_save_and_retrieve(self):
        hm = HistoryManager()
        test_id = "test-anime-slug-999"
        hm.mark_watched(
            anime_id=test_id,
            episode_num="1",
            anime_title="Test Anime Title",
            time_pos=120.0,
            duration=1440.0,
            percent=8.33,
            poster_url="",
            provider="anime3rb"
        )
        history_list = hm.get_history()
        found = any(h.get("anime_id") == test_id for h in history_list)
        assert found, "Recently saved progress should exist in watch history"


class TestNativeDownloader:
    """Tests custom pure-Python downloader parsing, sanitization, and config."""

    def test_parse_speed_limit(self):
        from src.downloader import parse_speed_limit, format_speed
        assert parse_speed_limit("0") is None
        assert parse_speed_limit("unlimited") is None
        assert parse_speed_limit("none") is None
        assert parse_speed_limit("") is None
        assert parse_speed_limit("500K") == 500 * 1024
        assert parse_speed_limit("2M") == 2 * 1024 * 1024
        assert parse_speed_limit("1.5MB") == int(1.5 * 1024 * 1024)

        assert format_speed(None) == "Unlimited"
        assert format_speed(2 * 1024 * 1024) == "2.0 MB/s"
        assert format_speed(512 * 1024) == "512 KB/s"

    def test_sanitize_filename(self):
        from src.downloader import sanitize_filename
        assert sanitize_filename('Naruto: Shippuuden / Ep <1>.mp4') == 'Naruto_ Shippuuden _ Ep _1_.mp4'
        assert sanitize_filename('') == 'download.mp4'

    def test_stream_downloader_resumable_logic(self):
        from unittest.mock import patch, MagicMock
        from src.downloader import StreamDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "test_ep.mp4"
            part = dest.with_suffix(".mp4.part")
            part.write_bytes(b"first_half_")

            downloader = StreamDownloader(speed_limit_bytes=None)

            mock_resp = MagicMock()
            mock_resp.status_code = 206
            mock_resp.headers = {"Content-Length": "11"}
            mock_resp.iter_content.return_value = [b"second_half"]
            mock_resp.__enter__.return_value = mock_resp
            mock_resp.__exit__.return_value = False

            mock_prog = MagicMock()

            with patch("requests.get", return_value=mock_resp) as mock_get:
                ok = downloader.download("http://example.com/video.mp4", dest, mock_prog, 1)
                assert ok is True
                assert dest.exists()
                assert not part.exists()
                assert dest.read_bytes() == b"first_half_second_half"

                mock_get.assert_called_once()
                sent_headers = mock_get.call_args[1].get("headers", {})
                assert sent_headers.get("Range") == f"bytes={len(b'first_half_')}-"

    def test_stream_downloader_skip_existing(self):
        from unittest.mock import MagicMock
        from src.downloader import StreamDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "test_ep.mp4"
            dest.write_bytes(b"complete_file_content")
            downloader = StreamDownloader()
            mock_prog = MagicMock()
            ok = downloader.download("http://example.com/video.mp4", dest, mock_prog, 1)
            assert ok is True
            assert dest.read_bytes() == b"complete_file_content"

    def test_stream_downloader_stop_requested(self):
        from unittest.mock import patch, MagicMock
        from src.downloader import StreamDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "test_ep.mp4"
            downloader = StreamDownloader()
            downloader.stop_requested.set()
            mock_prog = MagicMock()

            with patch("requests.get") as mock_get:
                ok = downloader.download("http://example.com/video.mp4", dest, mock_prog, 1)
                assert ok is False
                mock_get.assert_not_called()

    def test_parse_batch_ranges_comprehensive(self):
        from src.downloader import parse_batch_ranges
        assert parse_batch_ranges("1-5") == [1, 2, 3, 4, 5]
        assert parse_batch_ranges("5-1") == [1, 2, 3, 4, 5]
        assert parse_batch_ranges("1, 3, 5") == [1, 3, 5]
        assert parse_batch_ranges("1,3,5") == [1, 3, 5]
        assert parse_batch_ranges("all", max_eps=5) == [1, 2, 3, 4, 5]
        assert parse_batch_ranges("*", max_eps=3) == [1, 2, 3]
        assert parse_batch_ranges("-3", max_eps=10) == [1, 2, 3]
        assert parse_batch_ranges("8-", max_eps=10) == [8, 9, 10]
        assert parse_batch_ranges("1-3 5 8-10") == [1, 2, 3, 5, 8, 9, 10]
        assert parse_batch_ranges("") == []

    def test_ui_settings_dynamic_providers(self):
        from src.providers.manager import ProviderManager
        prov_list = ProviderManager.list_providers()
        ids = [p["id"] for p in prov_list]
        assert "anime3rb" in ids
        assert "hianime" in ids
        assert "anime_slayer" in ids
        assert "animeify" in ids


class TestNetworkOptimizationAndPooling:
    """Verifies connection pooling, retry backoff, and non-blocking background tasks."""

    def test_hianime_connection_pool_configured(self):
        prov = ProviderManager.get_provider("hianime")
        assert hasattr(prov, "session")
        adapter_https = prov.session.adapters.get("https://")
        assert adapter_https is not None
        assert adapter_https._pool_connections >= 20

    def test_animeify_connection_pool_configured(self):
        prov = ProviderManager.get_provider("animeify")
        assert hasattr(prov, "session")
        adapter_https = prov.session.adapters.get("https://")
        assert adapter_https is not None
        assert adapter_https._pool_connections >= 20

    def test_retry_with_backoff_decorator(self):
        from src.api import retry_with_backoff

        calls = 0

        @retry_with_backoff(retries=3, initial_delay=0.01, backoff_factor=1.1)
        def unstable_func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise ValueError("Temporary failure")
            return "SUCCESS"

        result = unstable_func()
        assert result == "SUCCESS"
        assert calls == 2

    def test_cdn_health_manager(self):
        from src.api import CDNHealthManager
        mgr = CDNHealthManager()
        # Seeded bad host
        assert not mgr.is_host_healthy("files-5.vid3rb.com")
        mgr.mark_unhealthy("test-bad-cdn.com", duration=100.0)
        assert not mgr.is_host_healthy("test-bad-cdn.com")

    def test_get_github_stars_non_blocking(self):
        from src.ui import get_github_stars
        stars = get_github_stars(refresh_if_stale=False)
        assert isinstance(stars, str)
        assert len(stars) > 0


class TestCliSettingsParityAndUtils:
    """Verifies CLI settings dialog capabilities and terminal utilities."""

    def test_settings_dialog_fields(self):
        sm = SettingsManager()
        # Ensure all 8 configurable keys exist and have proper defaults
        assert sm.get("anime_provider") in ["anime3rb", "anime_slayer", "animeify", "hianime", "anidb"]
        assert sm.get("player") in ["mpv", "vlc", "celluloid", "iina", "syncplay", "mpc-hc"]
        assert sm.get("default_quality") in ["1080p", "720p", "480p", "360p", "auto", "best"]
        assert sm.get("default_download_quality") in ["1080p", "720p", "480p", "360p"]
        assert sm.get("download_directory") is not None
        assert isinstance(sm.get("auto_next", False), bool)
        assert isinstance(sm.get("discord_rpc", True), bool)
        assert sm.get("theme") is not None

    def test_clean_genre_and_type(self):
        from src.utils import clean_genre, clean_type, clean_status
        assert clean_genre("اكشن") == "Action"
        assert clean_genre("Action") == "Action"
        assert clean_type("مسلسل") == "TV"
        assert clean_type("TV") == "TV"
        assert clean_status("مكتمل") == "Completed"


class TestEdgeCasesAndBoundaryConditions:
    """Verifies edge cases, fallback paths, and boundary conditions."""

    def test_provider_manager_fallback_on_invalid_id(self):
        prov = ProviderManager.get_provider("completely_invalid_provider_name_xyz")
        assert prov is not None
        assert prov.id == "anime3rb"

    def test_provider_manager_set_active_and_retrieve(self):
        original = ProviderManager.get_active_provider_id()
        try:
            ProviderManager.set_active_provider("hianime")
            assert ProviderManager.get_active_provider_id() == "hianime"
            prov = ProviderManager.get_provider()
            assert prov.id == "hianime"
        finally:
            ProviderManager.set_active_provider(original)

    def test_clean_season_edge_cases(self):
        assert clean_season("") == ""
        assert clean_season("   ") == ""
        assert clean_season("Unknown") == ""
        assert clean_season("خريف 1999") == "Fall 1999"
        assert clean_season("2021") == "2021"

    def test_clean_episodes_edge_cases(self):
        assert clean_episodes("0 episodes") == ""
        assert clean_episodes("N/A") == ""
        assert clean_episodes("Special - 1") == "1 eps"
        assert clean_episodes("100") == "100 eps"

    def test_cli_wrapper_quality_preferences_fallback(self):
        prov = ProviderManager.get_provider("anime3rb")
        sm = SettingsManager()
        hm = HistoryManager()
        wrapper = AniCliWrapper(api=prov, player=None, history=hm, settings=sm, rpc=None)

        # 1. Server data with explicit Qualities
        q1 = QualityOption("1080p", "url_1080", "1080p")
        res1 = wrapper.get_quality_preference({"Qualities": [q1]})
        assert res1 == [q1]

        # 2. Server data with CurrentEpisode dict
        server_data_ce = {
            "CurrentEpisode": {
                "FRFhdQ": "https://cdn.example.com/1080.mp4",
                "FRLink": "https://cdn.example.com/720.mp4"
            }
        }
        res2 = wrapper.get_quality_preference(server_data_ce)
        assert len(res2) == 2
        assert res2[0].name == "1080p"
        assert res2[1].name == "720p"

        # 3. None or empty data
        res3 = wrapper.get_quality_preference(None)
        assert res3 == []

    def test_batch_range_parsing(self):
        from src.downloader import parse_batch_ranges
        assert parse_batch_ranges("1-3 5 8-10") == [1, 2, 3, 5, 8, 9, 10]

