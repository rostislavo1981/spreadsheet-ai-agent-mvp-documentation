"""Hermes provider adapter (Mode A: openai_compatible to Hermes Gateway).

In Mode A the Hermes Gateway exposes an OpenAI-compatible /v1/chat/completions
endpoint, so we reuse the OpenAICompatibleAdapter's request/response handling with
Hermes-specific defaults (HERMES_INTEGRATION.md §4). Provider/Hermes secrets stay
server-side; the client never sees them. Tool policy is enforced server-side
(planner_only in P0).
"""
from __future__ import annotations

from typing import Any

from ...core.settings import Settings
from ...domain.provider_models import ModelDescriptor, ProviderCapabilities
from .openai_compatible import OpenAICompatibleAdapter


class HermesAdapter(OpenAICompatibleAdapter):
    """Talks to the Hermes Gateway as an OpenAI-compatible endpoint (Mode A)."""

    def __init__(self, settings: Settings | None = None, client: Any = None, **overrides: Any) -> None:
        # Bypass the base __init__ defaults by constructing a compatible settings view.
        self.settings = settings or Settings()
        self.provider_id = "hermes"
        self.base_url = (overrides.get("base_url") or self.settings.hermes_base_url or "http://127.0.0.1:8001/v1").rstrip("/")
        self.api_key = overrides.get("api_key", self.settings.hermes_api_key)
        self.model = overrides.get("model", self.settings.hermes_model or "spreadsheet-planner")
        self._profile = overrides.get("profile", self.settings.hermes_profile or "spreadsheet-planner")
        self._client = client

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
        return [ModelDescriptor(id=self.model, profiles=[self._profile])]
