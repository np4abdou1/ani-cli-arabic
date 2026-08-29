"""
Provider Manager for ani-cli-arabic
Handles provider registry, discovery, dynamic switching, and lifecycle management.
"""

from typing import Dict, List, Type, Optional
from .base import BaseAnimeProvider
from .anime3rb import Anime3rbProvider
from .anime_slayer import AnimeSlayerProvider


class ProviderManager:
    """Registry and factory for all available anime providers."""

    _PROVIDERS: Dict[str, Type[BaseAnimeProvider]] = {
        "anime3rb": Anime3rbProvider,
        "anime_slayer": AnimeSlayerProvider,
    }

    _INSTANCES: Dict[str, BaseAnimeProvider] = {}
    _ACTIVE_ID: str = "anime3rb"

    @classmethod
    def register_provider(cls, provider_id: str, provider_cls: Type[BaseAnimeProvider]):
        """Register a new anime provider."""
        cls._PROVIDERS[provider_id.lower()] = provider_cls

    @classmethod
    def get_provider(cls, provider_id: Optional[str] = None) -> BaseAnimeProvider:
        """Get an instantiated provider instance by ID (or currently active provider)."""
        pid = (provider_id or cls._ACTIVE_ID).lower()
        
        if pid not in cls._PROVIDERS:
            pid = "anime3rb"

        if pid not in cls._INSTANCES:
            provider_cls = cls._PROVIDERS[pid]
            cls._INSTANCES[pid] = provider_cls()

        return cls._INSTANCES[pid]

    @classmethod
    def set_active_provider(cls, provider_id: str):
        """Set the active default provider."""
        pid = provider_id.lower()
        if pid in cls._PROVIDERS:
            cls._ACTIVE_ID = pid

    @classmethod
    def get_active_provider_id(cls) -> str:
        """Get current active provider ID."""
        return cls._ACTIVE_ID

    @classmethod
    def list_providers(cls) -> List[Dict[str, str]]:
        """List all available providers with their metadata."""
        providers = []
        for pid, p_cls in cls._PROVIDERS.items():
            providers.append({
                "id": pid,
                "name": getattr(p_cls, "name", pid.title()),
                "description": getattr(p_cls, "description", "")
            })
        return providers

    @classmethod
    def get_provider_choices(cls) -> List[str]:
        """Get list of valid provider IDs."""
        return list(cls._PROVIDERS.keys())
