"""
Opt-in live smoke tests for Stardima.

Run with:
    STARDIMA_LIVE_TEST=1 pytest -q tests/test_stardima_live.py
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.providers import ProviderManager


pytestmark = pytest.mark.skipif(
    not os.getenv("STARDIMA_LIVE_TEST"),
    reason="set STARDIMA_LIVE_TEST=1 to run live Stardima tests",
)


def test_live_anime_search():
    provider = ProviderManager.get_provider("stardima")
    results = provider.search_anime("ناروتو")
    assert results
    assert any(result.language == "dub" for result in results)
    assert all(result.content_type in ("anime", "unknown") for result in results)


def test_live_kids_search():
    provider = ProviderManager.get_provider("stardima_kids")
    results = provider.search_anime("سبونج بوب")
    assert results
    assert all(result.content_type in ("cartoon", "unknown") for result in results)


def test_live_episode_and_backup_stream():
    provider = ProviderManager.get_provider("stardima")
    details = provider.get_anime_details("1068")
    assert details.id == "1068"
    episodes = provider.get_episodes("1068")
    assert episodes
    data = provider.get_streaming_servers("1068", episodes[0].number, details.type)
    assert data
    qualities = data["Qualities"]
    assert len(qualities) >= 1
    quality = qualities[0]
    assert quality.direct_url.startswith("http")
    assert quality.audio_lang == "ara,ar"
    assert data["CurrentEpisode"]["FRFhdQ"] == quality.direct_url
