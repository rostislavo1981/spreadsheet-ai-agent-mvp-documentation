"""Model Router: filter → score → attempt → fallback (PROVIDER_ADAPTERS §7).

Deterministic tie-breaking. No model call to select a model in MVP.
"""
from __future__ import annotations

from ..core.settings import Settings, get_settings
from ..domain.provider_models import ModelRequest, ModelResponse
from .registry import ProviderRegistry

# Simple deterministic profile weights (quality/cost/latency/health).
_PROFILE_WEIGHTS = {
    "auto": {"quality": 0.4, "cost": 0.3, "latency": 0.2, "health": 0.1},
    "quality": {"quality": 0.7, "cost": 0.1, "latency": 0.1, "health": 0.1},
    "cheap": {"quality": 0.1, "cost": 0.7, "latency": 0.1, "health": 0.1},
    "fast": {"quality": 0.2, "cost": 0.2, "latency": 0.5, "health": 0.1},
    "private": {"quality": 0.3, "cost": 0.2, "latency": 0.2, "health": 0.3},
    "hermes": {"quality": 0.4, "cost": 0.3, "latency": 0.2, "health": 0.1},
}


def _score(provider_id: str, profile: str) -> float:
    w = _PROFILE_WEIGHTS.get(profile, _PROFILE_WEIGHTS["auto"])
    base = {"fake": 0.5, "compatible": 0.7}.get(provider_id.split("-")[0], 0.6)
    return round(base * 10 * (w["quality"] + w["cost"] + w["latency"] + w["health"]), 4)


class ModelRouter:
    def __init__(self, registry: ProviderRegistry, settings: Settings | None = None):
        self.registry = registry
        self.settings = settings or get_settings()

    def rank(self, profile: str) -> list[str]:
        ordered = self.registry.ordered_targets()
        # Hermes profile => only hermes-eligible targets (openai_compatible hermes id or 'hermes')
        if profile == "hermes":
            ordered = [t for t in ordered if t in ("hermes", self.settings.hermes_profile)]
        scored = sorted(ordered, key=lambda t: _score(t, profile), reverse=True)
        return scored

    async def route(self, request: ModelRequest, profile: str | None = None) -> ModelResponse:
        profile = profile or self.settings.default_routing_profile
        ranked = self.rank(profile)
        attempts: list[str] = []
        last_err = None
        max_attempts = self.settings.max_provider_attempts
        for target in ranked[:max_attempts]:
            attempts.append(target)
            try:
                adapter = self.registry.get(target)
                resp = await adapter.complete(request)
                resp.route_metadata = {
                    **resp.route_metadata,
                    "profile": profile,
                    "attempts": attempts,
                    "fallback_count": max(0, len(attempts) - 1),
                }
                return resp
            except Exception as exc:
                from ..core.errors import ProviderError, ProvidersExhaustedError

                last_err = exc
                retryable = isinstance(exc, ProviderError) and exc.retryable
                if not retryable:
                    raise
        raise ProvidersExhaustedError(f"all targets failed: {attempts}") from last_err
