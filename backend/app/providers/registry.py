"""Provider registry: server-side configured targets (PROVIDER_ADAPTERS §9)."""
from __future__ import annotations

from ..core.errors import ProviderError
from ..core.settings import Settings, get_settings
from .base import ProviderAdapter
from .implementations.fake import FakeProviderAdapter
from .implementations.hermes import HermesAdapter
from .implementations.openai_compatible import OpenAICompatibleAdapter


class ProviderRegistry:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._adapters: dict[str, ProviderAdapter] = {}
        self._build()

    def _build(self) -> None:
        if self.settings.fake_provider_enabled:
            self._adapters["fake"] = FakeProviderAdapter(self.settings)
        if self.settings.openai_compatible_enabled:
            if not self.settings.openai_compatible_model:
                raise ProviderError(
                    "OPENAI_COMPATIBLE enabled but OPENAI_COMPATIBLE_MODEL missing",
                    provider_id="config", retryable=False,
                )
            ad = OpenAICompatibleAdapter(self.settings)
            ad.provider_id = self.settings.openai_compatible_provider_id
            self._adapters[self.settings.openai_compatible_provider_id] = ad
        if self.settings.hermes_enabled:
            # Mode A: Hermes Gateway as OpenAI-compatible endpoint.
            hermes = HermesAdapter(self.settings)
            self._adapters["hermes"] = hermes

    def get(self, provider_id: str) -> ProviderAdapter:
        if provider_id not in self._adapters:
            raise ProviderError(
                f"unknown provider target: {provider_id}", provider_id=provider_id, retryable=False,
            )
        return self._adapters[provider_id]

    def targets(self) -> list[str]:
        return list(self._adapters.keys())

    def ordered_targets(self) -> list[str]:
        """Enabled targets in configured priority order (PROVIDER_ADAPTERS §7)."""
        out = []
        for t in self.settings.enabled_provider_targets:
            if t in self._adapters:
                out.append(t)
        # include any configured adapter not explicitly listed
        for t in self._adapters:
            if t not in out:
                out.append(t)
        return out

    def enabled(self) -> bool:
        return bool(self._adapters)
