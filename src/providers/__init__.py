"""
ani-cli-arabic Providers Package
"""

from .base import BaseAnimeProvider
from .anime3rb import Anime3rbProvider
from .anime_slayer import AnimeSlayerProvider
from .hianime import HiAnimeProvider
from .animeify import AnimeifyProvider
from .manager import ProviderManager

__all__ = [
    "BaseAnimeProvider",
    "Anime3rbProvider",
    "AnimeSlayerProvider",
    "HiAnimeProvider",
    "AnimeifyProvider",
    "ProviderManager",
]
