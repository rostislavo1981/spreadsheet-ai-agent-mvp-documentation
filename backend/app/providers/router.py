"""Model Router: filter → score → attempt → fallback (PROVIDER_ADAPTERS §7).

Configured priority order (`ENABLED_PROVIDER_TARGETS`) is authoritative; score
is only a future tie-breaker. On any provider failure we attempt the next
target up to `max_provider_attempts` (fail-closed: non-provider errors propagate).
"""
from __future__ import annotations

from collections.abc import Callable

from ..core.errors import ProviderError, ProvidersExhaustedError
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

# Score only used as a secondary tie-breaker within equal priority.
_SCORE = {"fake": 0.5, "compatible": 0.7}


def _score(provider_id: str, profile: str) -> float:
    w = _PROFILE_WEIGHTS.get(profile, _PROFILE_WEIGHTS["auto"])
    base = _SCORE.get(provider_id.split("-")[0], 0.6)
    return round(base * (w["quality"] + w["cost"] + w["latency"] + w["health"]), 4)


class ModelRouter:
    def __init__(self, registry: ProviderRegistry, settings: Settings | None = None):
        self.registry = registry
        self.settings = settings or get_settings()

    def rank(self, profile: str) -> list[str]:
        # Configured priority order is authoritative.
        ordered = self.registry.ordered_targets()
        if profile == "hermes":
            ordered = [t for t in ordered if t in ("hermes", self.settings.hermes_profile)]
        # stable secondary sort by score (keeps configured order on ties)
        return sorted(ordered, key=lambda t: _score(t, profile), reverse=True)

    def rank_keep_order(self, profile: str) -> list[str]:
        ordered = self.registry.ordered_targets()
        if profile == "hermes":
            ordered = [t for t in ordered if t in ("hermes", self.settings.hermes_profile)]
        return ordered

    async def route(
        self, request: ModelRequest, profile: str | None = None,
        *, on_delta: Callable[[str], None] | None = None,
        on_attempt_start: Callable[[], None] | None = None,
    ) -> ModelResponse:
        """on_attempt_start, if given, is called before each fallback attempt
        (including the first) so the caller can discard any partial text a
        prior failed attempt streamed via on_delta before this one starts
        streaming its own — otherwise a caller that appends deltas would
        concatenate the failed attempt's text with the retry's text."""
        profile = profile or self.settings.default_routing_profile
        ranked = self.rank_keep_order(profile)
        attempts: list[str] = []
        last_err: BaseException | None = None
        max_attempts = min(self.settings.max_provider_attempts, len(ranked)) or 1
        for target in ranked[:max_attempts]:
            attempts.append(target)
            if on_attempt_start:
                on_attempt_start()
            try:
                adapter = self.registry.get(target)
                resp = await adapter.complete(request, on_delta=on_delta)
                resp.route_metadata = {
                    **resp.route_metadata,
                    "profile": profile,
                    "attempts": attempts,
                    "fallback_count": max(0, len(attempts) - 1),
                }
                return resp
            except ProviderError as exc:
                # Any provider failure falls through to the next target.
                last_err = exc
                continue
            except Exception as exc:  # noqa: BLE001 - wrap unexpected upstream failures
                last_err = ProviderError(
                    f"unexpected provider error from {target}: {exc}",
                    provider_id=target, retryable=True,
                )
                continue
        raise ProvidersExhaustedError(f"all targets failed: {attempts}") from last_err
