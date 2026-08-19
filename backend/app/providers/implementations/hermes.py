"""Hermes provider adapter (Mode A: openai_compatible to Hermes Gateway).

In Mode A the Hermes Gateway exposes an OpenAI-compatible /v1/chat/completions
endpoint, so we reuse the OpenAICompatibleAdapter's request/response handling with
Hermes-specific defaults (HERMES_INTEGRATION.md §4). Provider/Hermes secrets stay
server-side; the client never sees them. Tool policy is enforced server-side
(planner_only in P0).
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from ...core.settings import Settings
from ...domain.provider_models import ModelDescriptor, ProviderCapabilities
from .openai_compatible import OpenAICompatibleAdapter

logger = logging.getLogger(__name__)

_MODEL_LIST_CACHE_TTL_SECONDS = 60


class HermesAdapter(OpenAICompatibleAdapter):
    """Talks to the Hermes Gateway as an OpenAI-compatible endpoint (Mode A)."""

    def __init__(self, settings: Settings | None = None, client: Any = None, **overrides: Any) -> None:
        # Bypass the base __init__ defaults by constructing a compatible settings view.
        self.settings = settings or Settings()
        self.provider_id = "hermes"
        self.base_url = (overrides.get("base_url") or self.settings.hermes_base_url or "http://127.0.0.1:4012/v1").rstrip("/")
        self.api_key = overrides.get("api_key", self.settings.hermes_api_key)
        self.model = overrides.get("model", self.settings.hermes_model or "spreadsheet-planner")
        self._profile = overrides.get("profile", self.settings.hermes_profile or "spreadsheet-planner")
        self._client = client
        self._models_cache: list[ModelDescriptor] | None = None
        self._models_cache_at: float = 0.0

    @property
    def provider_id(self) -> str:
        return "hermes"

    @provider_id.setter
    def provider_id(self, v: str) -> None:
        self._provider_id = v

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(provider_id="hermes", structured_output=True, streaming=True)

    async def health(self) -> ProviderCapabilities:
        return await self.capabilities()

    async def list_models(self) -> list[ModelDescriptor]:
        """Fetch the live model list from the Hermes gateway's /v1/models endpoint.

        Falls back to the single configured HERMES_MODEL on any failure, so the
        rest of the app (capabilities, routing) always has at least one usable
        model even if Hermes is unreachable or the endpoint is unsupported.
        """
        now = time.monotonic()
        if self._models_cache is not None and (now - self._models_cache_at) < _MODEL_LIST_CACHE_TTL_SECONDS:
            return self._models_cache

        fallback = [ModelDescriptor(id=self.model, profiles=[self._profile])]
        try:
            client = await self._get_client()
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = await client.get(f"{self.base_url}/models", headers=headers)
            if resp.status_code != 200:
                logger.warning("hermes list_models non-200 status=%s", resp.status_code)
                return fallback
            data = resp.json().get("data", [])
            models = [ModelDescriptor(id=m["id"], profiles=[self._profile]) for m in data if m.get("id")]
            if not models:
                return fallback
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("hermes list_models failed: %s", exc)
            return fallback

        self._models_cache = models
        self._models_cache_at = now
        return models
