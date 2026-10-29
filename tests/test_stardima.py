"""
Offline tests for the Stardima providers.

No live HTTP is performed here.  The provider tests inject a fake client,
classifier cache, extractor, and settings object.
"""

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import normalize_latest_episodes
from src.models import AnimeResult, Episode, QualityOption
from src.providers.base import BaseAnimeProvider
from src.providers.manager import ProviderManager
from src.providers.stardima import StardimaKidsProvider, StardimaProvider
from src.providers.stardima_client import (
    StardimaAuth,
    StardimaClassifier,
    StardimaClient,
    StardimaExtractor,
    unpack_dean_edwards,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


class FakeSettings:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakeExtractor:
    def backup_url(self, servers):
        for server in servers or []:
            if str(server.get("label", "")).lower() == "backup" and server.get("url"):
                return server["url"]
        return None

    def verify(self, url):
        return True

    def guess_res(self, url):
        if "1080" in url:
            return "1080p"
        if "720" in url:
            return "720p"
        return "Auto"

    def guess_ext(self, url):
        for extension in ("mkv", "mpg", "mp4"):
            if str(url).lower().endswith("." + extension):
                return extension
        return "mp4"

    def mixdrop(self, url):
        return None

    def hls_from_page(self, url, referer):
        return None


class FakeClient:
    def __init__(self):
        self.search_calls = []
        self.server_calls = []
        self.detail_calls = []
        self.details = {
            "1": {
                "id": 1,
                "title": "أنمي",
                "type": "series",
                "video_quality": "مدبلج",
                "poster_url": "https://img.test/anime.jpg",
                "year": "2024",
                "description": "anime",
                "category": [],
                "review_stats": {"average": 8.5},
                "seasons": [{"id": 11}, {"id": 12}],
            },
            "2": {
                "id": 2,
                "title": "كرتون",
                "type": "series",
                "video_quality": "مدبلج",
                "poster_url": "https://img.test/cartoon.jpg",
                "year": "2023",
                "description": "cartoon",
                "category": [],
                "review_stats": {"average": 7.5},
                "seasons": [{"id": 21}],
            },
            "3": {
                "id": 3,
                "title": "غير معروف",
                "type": "series",
                "video_quality": "مترجم",
                "poster_url": "https://img.test/unknown.jpg",
                "year": "2022",
                "description": "unknown",
                "category": [],
                "seasons": [{"id": 31}],
            },
            "4": {
                "id": 4,
                "title": "فيلم أنمي",
                "type": "movie",
                "video_quality": "مدبلج",
                "poster_url": "https://img.test/movie.jpg",
                "year": "2025",
                "description": "movie",
                "category": [],
                "review_stats": {"average": 9.0},
                "servers": [
                    {"label": "backup", "url": "https://cdn.test/movie-1080.mp4"},
                ],
            },
            "5": {
                "id": 5,
                "title": "فيلم كرتون",
                "type": "movie",
                "video_quality": "مدبلج",
                "poster_url": "https://img.test/movie2.jpg",
                "year": "2025",
                "description": "movie2",
                "category": [],
                "servers": [
                    {"label": "backup", "url": "https://cdn.test/movie2-720.mp4"},
                ],
            },
        }
        self.seasons = {
            "11": [
                {"id": 101, "episode_number": 4, "season_number": 1, "title": "S1 ح4 - أربعة"},
                {"id": 102, "episode_number": 5, "season_number": 1, "title": "S1 ح5 - خمسة"},
                {"id": 103, "episode_number": 6, "season_number": 1, "title": "S1 ح6 - ستة"},
                {"id": 104, "episode_number": 6, "season_number": 1, "title": "S1 ح6.5 - ستة ونصف"},
                {"id": 105, "episode_number": 7, "season_number": 1, "title": "S1 ح7 - سبعة"},
            ],
            "12": [
                {"id": 106, "episode_number": 13, "season_number": 2, "title": "S2 ح13 - ثلاثة عشر"},
                {"id": 107, "episode_number": 14, "season_number": 2, "title": "S2 ح14 - أربعة عشر"},
            ],
            "21": [
                {"id": 201, "episode_number": 1, "season_number": 1, "title": "Ep001"},
            ],
            "31": [
                {"id": 301, "episode_number": 1, "season_number": 1, "title": "Ep001"},
            ],
        }
        self.search_results = [
            {
                "id": 1,
                "title": "أنمي",
                "video_quality": "مدبلج",
                "is_series": True,
                "year": "2024",
                "poster_url": "https://img.test/anime.jpg",
                "category": [],
            },
            {
                "id": 2,
                "title": "كرتون",
                "video_quality": "مدبلج",
                "is_series": True,
                "year": "2023",
                "poster_url": "https://img.test/cartoon.jpg",
                "category": [],
            },
            {
                "id": 3,
                "title": "غير معروف",
                "video_quality": "مترجم",
                "is_series": True,
                "year": "2022",
                "poster_url": "https://img.test/unknown.jpg",
                "category": [],
            },
        ]
        self.movie_results = [
            {
                "id": 4,
                "title": "فيلم أنمي",
                "video_quality": "مدبلج",
                "is_series": False,
                "year": "2025",
                "poster_url": "https://img.test/movie.jpg",
                "category": [],
            },
            {
                "id": 5,
                "title": "فيلم كرتون",
                "video_quality": "مدبلج",
                "is_series": False,
                "year": "2025",
                "poster_url": "https://img.test/movie2.jpg",
                "category": [],
            },
        ]
        self.latest = [
            {
                "id": 1,
                "episode_number": 15,
                "series_title": "أنمي",
                "video_quality": "مدبلج",
                "poster_url": "https://img.test/anime.jpg",
            },
            {
                "id": 2,
                "episode_number": 3,
                "series_title": "كرتون",
                "video_quality": "مدبلج",
                "poster_url": "https://img.test/cartoon.jpg",
            },
            {
                "id": 3,
                "episode_number": 1,
                "series_title": "غير معروف",
                "video_quality": "مترجم",
                "poster_url": "https://img.test/unknown.jpg",
            },
        ]
        self.trending = [
            self.search_results[0],
            {
                "id": 6,
                "title": "أنمي مترجم",
                "video_quality": "مترجم",
                "is_series": True,
                "year": "2024",
                "poster_url": "https://img.test/anime-sub.jpg",
                "category": [],
            },
            self.search_results[1],
        ]

    def search(self, query="", language=None, media=None, categories=None, page=1, per_page=50):
        self.search_calls.append(
            {
                "query": query,
                "language": language,
                "media": media,
                "categories": list(categories) if categories else None,
                "page": page,
                "per_page": per_page,
            }
        )
        videos = self.movie_results if media == "movies" else self.search_results
        return {"videos": videos, "pagination": {"last_page": 1}}

    def video(self, video_id):
        self.detail_calls.append(str(video_id))
        return self.details.get(str(video_id))

    def episodes(self, season_id, page=1, per_page=100):
        data = self.seasons.get(str(season_id), [])
        return {"data": data, "total": len(data)}

    def servers(self, episode_id):
        self.server_calls.append(str(episode_id))
        return [
            {"label": "Uqload", "url": "https://uqload.test/e/x"},
            {"label": "backup", "url": f"https://cdn.test/{episode_id}-1080.mkv"},
            {"label": "Mixdrop", "url": "https://mixdrop.test/e/x"},
        ]

    def latest_episodes(self, page=1, per_page=100):
        return {"videos": self.latest, "pagination": {"last_page": 1}}

    def search_by_option(self, option_type="trending", page=1, per_page=30):
        return {"videos": self.trending, "pagination": {"last_page": 1}}


@pytest.fixture
def classifier(tmp_path):
    cache_file = tmp_path / "stardima_catalog.json"
    cache_file.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-10-28",
                "items": {
                    "1": {"t": "anime", "title": "Anime EN", "vote": 8.5},
                    "2": {"t": "cartoon", "title": "Cartoon EN", "vote": 7.5},
                    "3": {"t": "unknown", "title": "Unknown EN", "vote": 0},
                    "4": {"t": "anime", "title": "Anime Movie EN", "vote": 9.0},
                    "5": {"t": "cartoon", "title": "Cartoon Movie EN", "vote": 6.0},
                    "6": {"t": "anime", "title": "Anime Sub EN", "vote": 7.0},
                },
            }
        ),
        encoding="utf-8",
    )
    return StardimaClassifier(cache_file=cache_file)


def make_provider(classifier, cls=StardimaProvider, settings=None, client=None, extractor=None):
    return cls(
        client=client or FakeClient(),
        classifier=classifier,
        extractor=extractor or FakeExtractor(),
        settings=settings
        if settings is not None
        else FakeSettings({"stardima_language": "dub", "stardima_include_unknown": False}),
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestStardimaAuth:
    def test_env_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STARDIMA_API_KEY", "env-key")
        monkeypatch.setenv("STARDIMA_SERVER_URL", "https://env.test")
        auth = StardimaAuth(cache_file=tmp_path / "auth.json")
        assert auth.get() == ("env-key", "https://env.test")

    def test_fresh_cache_used_without_network(self, tmp_path, monkeypatch):
        monkeypatch.delenv("STARDIMA_API_KEY", raising=False)
        monkeypatch.delenv("STARDIMA_SERVER_URL", raising=False)
        cache = tmp_path / "auth.json"
        cache.write_text(
            json.dumps(
                {
                    "api_key": "cached-key",
                    "server_url": "https://cached.test",
                    "fetched_at": time.time(),
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr("requests.post", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no network")))
        monkeypatch.setattr("requests.get", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no network")))
        auth = StardimaAuth(cache_file=cache)
        assert auth.get() == ("cached-key", "https://cached.test")

    def test_remote_config_bootstrap_writes_cache(self, tmp_path, monkeypatch):
        monkeypatch.delenv("STARDIMA_API_KEY", raising=False)
        monkeypatch.delenv("STARDIMA_SERVER_URL", raising=False)
        cache = tmp_path / "auth.json"

        monkeypatch.setattr(
            "requests.post",
            lambda *a, **k: FakeResponse(payload={"entries": {"API_KEY": "new-key"}}),
        )
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **k: FakeResponse(payload={"data": {"server_url": "https://new.test/"}}),
        )

        auth = StardimaAuth(cache_file=cache)
        assert auth.get(force_refresh=True) == ("new-key", "https://new.test")
        saved = json.loads(cache.read_text(encoding="utf-8"))
        assert saved["api_key"] == "new-key"
        assert saved["server_url"] == "https://new.test"

    def test_stale_cache_fallback(self, tmp_path, monkeypatch):
        monkeypatch.delenv("STARDIMA_API_KEY", raising=False)
        monkeypatch.delenv("STARDIMA_SERVER_URL", raising=False)
        cache = tmp_path / "auth.json"
        cache.write_text(
            json.dumps(
                {
                    "api_key": "old-key",
                    "server_url": "https://old.test",
                    "fetched_at": 0,
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse(status_code=500))
        monkeypatch.setattr("requests.get", lambda *a, **k: FakeResponse(status_code=500))
        auth = StardimaAuth(cache_file=cache)
        assert auth.get() == ("old-key", "https://old.test")

    def test_failure_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.delenv("STARDIMA_API_KEY", raising=False)
        monkeypatch.delenv("STARDIMA_SERVER_URL", raising=False)
        monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse(status_code=500))
        monkeypatch.setattr("requests.get", lambda *a, **k: FakeResponse(status_code=500))
        auth = StardimaAuth(cache_file=tmp_path / "auth.json")
        assert auth.get(force_refresh=True) == (None, None)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class TestStardimaClient:
    def test_servers_reads_episode_envelope(self):
        payload = {
            "id": 101,
            "servers": [
                {"label": "backup", "url": "https://cdn.test/101.mp4"},
            ],
        }

        class FakeAuth:
            def get(self, force_refresh=False):
                return "key", "https://api.test"

        class FakeSession:
            def __init__(self):
                self.headers = {}

            def get(self, url, params=None, timeout=None):
                return FakeResponse(payload=payload)

        client = StardimaClient(auth=FakeAuth(), session=FakeSession())
        assert client.servers(101) == payload["servers"]

    def test_search_builds_language_and_category_params(self):
        captured = {}

        class FakeAuth:
            def get(self, force_refresh=False):
                return "key", "https://api.test"

        class FakeSession:
            def __init__(self):
                self.headers = {}

            def get(self, url, params=None, timeout=None):
                captured.update(params or {})
                return FakeResponse(payload={"videos": []})

        client = StardimaClient(auth=FakeAuth(), session=FakeSession())
        client.search(query="x", language="dub", media="movies", categories=["anmy"], page=2)
        assert captured["language"] == "dub"
        assert captured["media"] == "movies"
        assert captured["categories[]"] == ["anmy"]
        assert captured["page"] == 2


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


class TestStardimaClassifier:
    def test_cache_hit(self, classifier):
        assert classifier.classify("1") == "anime"
        assert classifier.classify("2") == "cartoon"
        assert classifier.classify("3") == "unknown"

    def test_exact_anime_tag(self, classifier):
        assert classifier.classify("999", {"tags": "magic, anime, shounen"}) == "anime"

    def test_anime_inspired_tag_is_not_anime(self, classifier):
        assert classifier.classify("999", {"tags": "anime inspired, magic"}) == "unknown"

    def test_category_fallback(self, classifier):
        assert classifier.classify("999", {"category": [{"slug": "anmy"}]}) == "anime"
        assert classifier.classify("999", {"category": [{"slug": "krton"}]}) == "cartoon"

    def test_language_detection(self):
        assert StardimaClassifier.language_of("مدبلج فصحى") == "dub"
        assert StardimaClassifier.language_of("مدبلج مصري") == "dub"
        assert StardimaClassifier.language_of("مترجم") == "sub"
        assert StardimaClassifier.language_of("") == ""

    def test_scope_matching(self):
        assert StardimaClassifier.matches_scope("anime", "anime")
        assert not StardimaClassifier.matches_scope("cartoon", "anime")
        assert StardimaClassifier.matches_scope("unknown", "anime", include_unknown=True)
        assert not StardimaClassifier.matches_scope("unknown", "anime", include_unknown=False)


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class TestStardimaProvider:
    def test_search_separates_anime_and_cartoon(self, classifier):
        anime = make_provider(classifier, StardimaProvider)
        kids = make_provider(classifier, StardimaKidsProvider)
        assert [a.id for a in anime.search_anime("x")] == ["1"]
        assert [a.id for a in kids.search_anime("x")] == ["2"]

    def test_unknown_titles_can_be_included(self, classifier):
        settings = {"stardima_language": "both", "stardima_include_unknown": True}
        anime = make_provider(classifier, StardimaProvider, settings=settings)
        kids = make_provider(classifier, StardimaKidsProvider, settings=settings)
        assert {a.id for a in anime.search_anime("x")} == {"1", "3"}
        assert {a.id for a in kids.search_anime("x")} == {"2", "3"}

    def test_language_filter_is_sent_to_api(self, classifier):
        client = FakeClient()
        provider = make_provider(classifier, StardimaProvider, client=client)
        provider.search_anime("x")
        assert client.search_calls[0]["language"] == "dub"

    def test_settings_reload_between_calls(self, classifier):
        class ReloadableSettings(FakeSettings):
            def __init__(self):
                super().__init__(
                    {"stardima_language": "dub", "stardima_include_unknown": False}
                )
                self.reloads = 0

            def reload(self):
                self.reloads += 1

        settings = ReloadableSettings()
        client = FakeClient()
        provider = make_provider(
            classifier,
            StardimaProvider,
            settings=settings,
            client=client,
        )
        provider.search_anime("x")
        assert settings.reloads == 1
        settings.values["stardima_language"] = "sub"
        provider.search_anime("x")
        assert settings.reloads == 2
        assert client.search_calls[-1]["language"] == "sub"

    def test_both_language_omits_param(self, classifier):
        client = FakeClient()
        provider = make_provider(
            classifier,
            StardimaProvider,
            settings={"stardima_language": "both", "stardima_include_unknown": False},
            client=client,
        )
        provider.search_anime("x")
        assert client.search_calls[0]["language"] is None

    def test_trending_respects_language_filter(self, classifier):
        dub = make_provider(classifier, StardimaProvider)
        assert [a.id for a in dub.get_trending_anime(limit=10)] == ["1"]

        sub = make_provider(
            classifier,
            StardimaProvider,
            settings={"stardima_language": "sub", "stardima_include_unknown": False},
        )
        assert [a.id for a in sub.get_trending_anime(limit=10)] == ["6"]

        both = make_provider(
            classifier,
            StardimaProvider,
            settings={"stardima_language": "both", "stardima_include_unknown": False},
        )
        assert {a.id for a in both.get_trending_anime(limit=10)} == {"1", "6"}

    def test_episodes_flatten_seasons_and_specials(self, classifier):
        provider = make_provider(classifier, StardimaProvider)
        episodes = provider.get_episodes("1")
        assert [e.number for e in episodes] == ["4", "5", "6", "6.5", "7", "13", "14"]
        assert [e.display_num for e in episodes] == [4, 5, 6, 6.5, 7, 13, 14]
        assert episodes[0].anime_id == "1"
        assert episodes[0].url == "101"

    def test_find_episode_by_number_and_url(self, classifier):
        provider = make_provider(classifier, StardimaProvider)
        episodes = provider.get_episodes("1")
        # Match by episode number
        ep_by_num = provider._find_episode(episodes, "4")
        assert ep_by_num is not None
        assert ep_by_num.url == "101"
        # Match by episode url (ID)
        ep_by_url = provider._find_episode(episodes, "101")
        assert ep_by_url is not None
        assert ep_by_url.number == "4"

    def test_special_episode_resolves_correct_server(self, classifier):
        client = FakeClient()
        provider = make_provider(classifier, StardimaProvider, client=client)
        data = provider.get_streaming_servers("1", "6.5", "SERIES")
        assert data is not None
        assert client.server_calls[-1] == "104"
        quality = data["Qualities"][0]
        assert quality.direct_url == "https://cdn.test/104-1080.mkv"
        assert quality.audio_lang == "ara,ar"
        assert quality.ext == "mkv"
        assert data["CurrentEpisode"]["FRFhdQ"] == quality.direct_url

    def test_subtitled_title_uses_japanese_audio(self, classifier):
        provider = make_provider(
            classifier,
            StardimaProvider,
            settings={"stardima_language": "sub", "stardima_include_unknown": False},
        )
        data = provider.get_streaming_servers("3", "1", "SERIES")
        assert data["Qualities"][0].audio_lang == "jpn,ja"

    def test_movie_stream_uses_detail_servers(self, classifier):
        provider = make_provider(classifier, StardimaProvider)
        data = provider.get_streaming_servers("4", "1", "MOVIE")
        assert data["Qualities"][0].direct_url == "https://cdn.test/movie-1080.mp4"
        assert data["Qualities"][0].audio_lang == "ara,ar"

    def test_latest_episodes_filter_by_scope_and_language(self, classifier):
        anime = make_provider(classifier, StardimaProvider)
        kids = make_provider(classifier, StardimaKidsProvider)
        assert [e.anime_id for e in anime.get_latest_episodes(10)] == ["1"]
        assert [e.anime_id for e in kids.get_latest_episodes(10)] == ["2"]

    def test_latest_sub_filter(self, classifier):
        provider = make_provider(
            classifier,
            StardimaProvider,
            settings={"stardima_language": "sub", "stardima_include_unknown": True},
        )
        latest = provider.get_latest_episodes(10)
        assert [e.anime_id for e in latest] == ["3"]

    def test_movies_are_scoped(self, classifier):
        anime = make_provider(classifier, StardimaProvider)
        kids = make_provider(classifier, StardimaKidsProvider)
        assert [a.id for a in anime.get_movies(limit=10)] == ["4"]
        assert [a.id for a in kids.get_movies(limit=10)] == ["5"]

    def test_genre_mapping(self, classifier):
        client = FakeClient()
        provider = make_provider(classifier, StardimaProvider, client=client)
        provider.get_genre_anime("action")
        assert client.search_calls[-1]["categories"] == ["akshn"]

    def test_anime_list_dispatcher(self, classifier):
        provider = make_provider(classifier, StardimaProvider)
        assert [a.id for a in provider.get_anime_list("SEARCH", "x")] == ["1"]
        assert [a.id for a in provider.get_anime_list("MOVIE")] == ["4"]

    def test_no_backup_returns_none(self, classifier):
        class NoBackupClient(FakeClient):
            def servers(self, episode_id):
                return [{"label": "Uqload", "url": "https://uqload.test/e/x"}]

        provider = make_provider(classifier, StardimaProvider, client=NoBackupClient())
        assert provider.get_streaming_servers("1", "4", "SERIES") is None

    def test_episode_streams_uses_anime_id(self, classifier):
        provider = make_provider(classifier, StardimaProvider)
        episode = Episode(number="4", display_num=4, anime_id="1", url="101")
        qualities = provider.get_episode_streams(episode)
        assert len(qualities) == 1
        assert qualities[0].direct_url.endswith("101-1080.mkv")

    def test_refresh_anime_cache_drops_stale_episodes(self, classifier):
        provider = make_provider(classifier, StardimaProvider)
        assert provider.get_episodes("1")
        assert "1" in provider._episode_cache
        provider.refresh_anime_cache("1")
        assert "1" not in provider._episode_cache
        assert "1" not in provider._detail_cache


# ---------------------------------------------------------------------------
# Registry / models
# ---------------------------------------------------------------------------


class TestStardimaRegistry:
    def test_providers_registered(self):
        anime = ProviderManager.get_provider("stardima")
        kids = ProviderManager.get_provider("stardima_kids")
        assert isinstance(anime, BaseAnimeProvider)
        assert isinstance(kids, BaseAnimeProvider)
        assert isinstance(anime, StardimaProvider)
        assert isinstance(kids, StardimaKidsProvider)
        assert anime.content_scope == "anime"
        assert kids.content_scope == "cartoon"

    def test_provider_list_contains_both(self):
        names = {provider["name"] for provider in ProviderManager.list_providers()}
        assert "Stardima Anime (Dub)" in names
        assert "Stardima Kids (Cartoon)" in names

    def test_packaged_classification_cache_is_present(self):
        classifier = StardimaClassifier()
        assert len(classifier.items) > 3000
        assert classifier.get("4009")["t"] == "anime"

    def test_models_have_language_fields(self):
        anime = AnimeResult(id="1", title_en="x")
        assert anime.language == ""
        assert anime.content_type == ""
        quality = QualityOption("1080p", "FRFhdQ")
        assert quality.audio_lang == ""
        assert quality.ext == "mp4"

    def test_latest_episode_normalization(self):
        episode = Episode(
            number="15",
            display_num=15,
            title="Show",
            anime_id="4009",
            url="1",
        )
        assert normalize_latest_episodes([episode]) == [
            {
                "title": "Show",
                "slug": "4009",
                "ep_num": 15,
                "url": "1",
                "number": "15",
            }
        ]
        anime_entry = AnimeResult(id="42", title_en="Anime Entry")
        assert normalize_latest_episodes([anime_entry]) == [
            {
                "title": "Anime Entry",
                "slug": "42",
                "ep_num": 1,
                "url": "42",
                "number": "1",
            }
        ]


# ---------------------------------------------------------------------------
# Player args
# ---------------------------------------------------------------------------


class TestPlayerAudio:
    def _run_mpv(self, monkeypatch, **kwargs):
        import src.player as player_module

        captured = {}

        class FakeTracker:
            def __init__(self, sock_path):
                self.state = {"time_pos": 0.0, "duration": 0.0, "percent": 0.0, "completed": False}

            def start(self):
                pass

            def stop(self):
                pass

        def fake_run(args, **run_kwargs):
            captured["args"] = args
            return SimpleNamespace(returncode=0, stderr="")

        import src.utils as utils_module

        monkeypatch.setattr(player_module, "MpvTracker", FakeTracker)
        monkeypatch.setattr(player_module.subprocess, "run", fake_run)
        monkeypatch.setattr(utils_module, "restore_terminal_for_input", lambda: None)
        monkeypatch.setattr(utils_module, "enter_raw_mode_after_input", lambda: None)
        monkeypatch.setattr(utils_module, "show_cursor", lambda: None)
        monkeypatch.setattr(utils_module, "hide_cursor", lambda: None)

        player = player_module.PlayerManager()
        player._play_mpv("https://cdn.test/a.mkv", "title", mpv_path="mpv", **kwargs)
        return captured["args"]

    def test_dub_audio_and_headers(self, monkeypatch):
        args = self._run_mpv(
            monkeypatch,
            audio_lang="ara,ar",
            headers={"Referer": "https://stardima.test/", "X-Custom": "val123"},
        )
        assert "--alang=ara,ar" in args
        assert "--referrer=https://stardima.test/" in args
        assert "--http-header-fields=X-Custom: val123" in args

    def test_default_audio_preserved(self, monkeypatch):
        args = self._run_mpv(monkeypatch)
        assert "--alang=jpn,ja,eng,en" in args


class TestStardimaServerExtractors:
    def test_extract_backup(self, monkeypatch):
        extractor = StardimaExtractor()
        monkeypatch.setattr(extractor, "verify", lambda url: True)
        res = extractor.extract_backup("https://cdn.test/anime_1080.mkv")
        assert res is not None
        stream_url, headers, quality = res
        assert stream_url == "https://cdn.test/anime_1080.mkv"
        assert quality == "1080p"

    def test_extract_uqload_direct(self, monkeypatch):
        extractor = StardimaExtractor()
        fake_html = 'sources: ["https://strm.uqload.vc/v/12345/video.mp4"]'

        class FakeSession:
            def get(self, url, **kwargs):
                return FakeResponse(status_code=200, text=fake_html)

        extractor.session = FakeSession()
        res = extractor.extract_uqload("https://uqload.vc/embed-123456789012.html")
        assert res is not None
        stream_url, headers, quality = res
        assert stream_url == "https://strm.uqload.vc/v/12345/video.mp4"
        assert "uqload.vc" in headers.get("Referer", "")

    def test_extract_uqload_packed_hls(self, monkeypatch):
        extractor = StardimaExtractor()
        fake_packed = (
            "eval(function(p,a,c,k,e,d){while(c--)if(k[c])p=p.replace(new RegExp('\\\\b'+c.toString(a)+'\\\\b','g'),k[c]);return p}"
            "('0(\"1\").2({3:[{4:\"5://6.7/8/9.m3u8\"}]});',10,10,'jwplayer|vplayer|setup|sources|file|https|strm|uqload|hls|master'.split('|')))"
        )

        class FakeSession:
            def get(self, url, **kwargs):
                return FakeResponse(status_code=200, text=fake_packed)

        extractor.session = FakeSession()
        res = extractor.extract_uqload("https://uqload.vc/embed-123456789012.html")
        assert res is not None
        stream_url, headers, quality = res
        assert stream_url == "https://strm.uqload/hls/master.m3u8"
        assert "m3u8" in stream_url

    def test_extract_savefiles(self):
        extractor = StardimaExtractor()
        fake_response = 'sources: [{file: "https://s1.savefiles.com/hls/master.m3u8"}]'

        class FakeSession:
            def post(self, url, data=None, **kwargs):
                assert data and data.get("file_code") == "abcd1234efgh"
                return FakeResponse(status_code=200, text=fake_response)

        extractor.session = FakeSession()
        res = extractor.extract_savefiles("https://savefiles.com/e/abcd1234efgh")
        assert res is not None
        stream_url, headers, quality = res
        assert stream_url == "https://s1.savefiles.com/hls/master.m3u8"
        assert "savefiles.com" in headers.get("Referer", "")

    def test_extract_mixdrop(self, monkeypatch):
        extractor = StardimaExtractor()
        fake_html = 'MDCore.wurl = "//a-delivery.mxcontent.net/v/test.mp4";'

        def fake_get(self, url, **kwargs):
            return FakeResponse(status_code=200, text=fake_html)

        monkeypatch.setattr("requests.Session.get", fake_get)
        res = extractor.extract_mixdrop("https://mixdrop.top/e/abcdef123456")
        assert res is not None
        stream_url, headers, quality = res
        assert stream_url == "https://a-delivery.mxcontent.net/v/test.mp4"
        assert "mixdrop.top" in headers.get("Referer", "")

    def test_extract_lulustream(self):
        extractor = StardimaExtractor()
        fake_html = 'sources: [{file: "https://lulu.test/master.m3u8"}]'

        class FakeSession:
            def get(self, url, **kwargs):
                return FakeResponse(status_code=200, text=fake_html)

        extractor.session = FakeSession()
        res = extractor.extract_lulustream("https://lulustream.com/e/abcdef123456")
        assert res is not None
        stream_url, headers, quality = res
        assert stream_url == "https://lulu.test/master.m3u8"

    def test_extract_mp4upload(self):
        extractor = StardimaExtractor()
        fake_html = 'player.src("https://mp4upload.test/files/1/video.mp4");'

        class FakeSession:
            def get(self, url, **kwargs):
                return FakeResponse(status_code=200, text=fake_html)

        extractor.session = FakeSession()
        res = extractor.extract_mp4upload("https://mp4upload.com/embed-xyz.html")
        assert res is not None
        stream_url, headers, quality = res
        assert stream_url == "https://mp4upload.test/files/1/video.mp4"

    def test_extract_forafile(self):
        extractor = StardimaExtractor()
        fake_html = 'file: "https://forafile.test/stream.m3u8"'

        class FakeSession:
            def get(self, url, **kwargs):
                return FakeResponse(status_code=200, text=fake_html)

        extractor.session = FakeSession()
        res = extractor.extract_forafile("https://forafile.com/embed-123.html")
        assert res is not None
        stream_url, headers, quality = res
        assert stream_url == "https://forafile.test/stream.m3u8"

    def test_extract_firestream(self):
        extractor = StardimaExtractor()
        fake_html = '<script id="video-data" type="application/json">{"file": "https://firestream.test/video.mp4"}</script>'

        class FakeSession:
            def get(self, url, **kwargs):
                return FakeResponse(status_code=200, text=fake_html)

        extractor.session = FakeSession()
        res = extractor.extract_firestream("https://firestream.to/embed-xyz")
        assert res is not None
        stream_url, headers, quality = res
        assert stream_url == "https://firestream.test/video.mp4"

    def test_extract_all_priority_and_multi_servers(self, monkeypatch):
        extractor = StardimaExtractor()
        monkeypatch.setattr(
            extractor,
            "extract_server",
            lambda s: {
                "label": s["label"],
                "url": f"https://cdn.test/{s['label'].lower()}.mp4",
                "headers": {"Referer": s["url"]},
                "res": "1080p",
                "server_key": s["label"].replace(" ", "_"),
            }
            if s.get("url")
            else None,
        )

        servers = [
            {"label": "Uqload", "url": "https://uqload.vc/embed-1.html"},
            {"label": "Mixdrop", "url": "https://mixdrop.top/e/1"},
            {"label": "backup", "url": "https://cdn.test/backup.mkv"},
            {"label": "EmptyServer", "url": ""},
        ]

        extracted = extractor.extract_all(servers)
        assert len(extracted) == 3
        # Backup must be prioritized first
        assert extracted[0]["label"] == "backup"
        assert extracted[1]["label"] == "Uqload"
        assert extracted[2]["label"] == "Mixdrop"


class TestMultiServerStreaming:
    def test_get_streaming_servers_returns_all_extracted_servers(self, classifier):
        class MultiServerExtractor:
            def extract_all(self, servers):
                return [
                    {
                        "label": "Backup",
                        "url": "https://cdn.test/backup.mkv",
                        "headers": {},
                        "res": "1080p",
                        "server_key": "Backup",
                    },
                    {
                        "label": "Uqload",
                        "url": "https://strm.uqload.vc/master.m3u8",
                        "headers": {"Referer": "https://uqload.vc/"},
                        "res": "720p",
                        "server_key": "Uqload",
                    },
                    {
                        "label": "Savefiles",
                        "url": "https://s1.savefiles.com/master.m3u8",
                        "headers": {"Referer": "https://savefiles.com/"},
                        "res": "720p",
                        "server_key": "Savefiles",
                    },
                    {
                        "label": "Mixdrop",
                        "url": "https://mixdrop.test/video.mp4",
                        "headers": {"Referer": "https://mixdrop.top/"},
                        "res": "480p",
                        "server_key": "Mixdrop",
                    },
                ]

        client = FakeClient()
        provider = make_provider(
            classifier,
            StardimaProvider,
            client=client,
            extractor=MultiServerExtractor(),
        )

        data = provider.get_streaming_servers("1", "4", "SERIES")
        assert data is not None
        qualities = data["Qualities"]
        assert len(qualities) == 4

        # Check names & properties of all servers
        assert qualities[0].name == "1080p • Backup"
        assert qualities[0].direct_url == "https://cdn.test/backup.mkv"
        assert qualities[0].ext == "mkv"

        assert qualities[1].name == "720p • Uqload"
        assert qualities[1].direct_url == "https://strm.uqload.vc/master.m3u8"
        assert qualities[1].ext == "m3u8"
        assert qualities[1].headers == {"Referer": "https://uqload.vc/"}

        assert qualities[2].name == "720p • Savefiles"
        assert qualities[2].direct_url == "https://s1.savefiles.com/master.m3u8"

        assert qualities[3].name == "480p • Mixdrop"
        assert qualities[3].direct_url == "https://mixdrop.test/video.mp4"
        assert qualities[3].ext == "mp4"

        # Compatibility keys
        assert data["CurrentEpisode"]["FRFhdQ"] == qualities[0].direct_url
        assert data["CurrentEpisode"]["Backup"] == qualities[0].direct_url
        assert data["CurrentEpisode"]["Uqload"] == qualities[1].direct_url
