"""Adapter contract + router tests. Offline; fake provider only (PROVIDER_ADAPTERS §10)."""
from __future__ import annotations

import pytest

from app.core.errors import ProviderError, ProvidersExhaustedError
from app.core.ids import new_id
from app.domain.provider_models import ModelRequest
from app.providers.implementations.fake import FakeProviderAdapter
from app.providers.registry import ProviderRegistry
from app.providers.router import ModelRouter
from app.core.settings import Settings


def _settings(failure=None):
    fix = {"plan": {"schema_version": "1.0", "summary": "x", "answer": "y", "actions": [],
                    "warnings": [], "assumptions": [], "context_used": [], "requires_confirmation": False},
           "failure": failure}
    import json, tempfile, os
    fd, path = tempfile.mkstemp(suffix=".json")
    os.write(fd, json.dumps(fix).encode())
    os.close(fd)
    s = Settings(fake_provider_enabled=True, fake_provider_fixture=path, enabled_provider_targets="fake")
    return s, path


def _req():
    return ModelRequest(request_id=new_id("req"), messages=[{"role": "user", "content": "hi"}], response_schema={"name": "x"})


@pytest.mark.asyncio
async def test_fake_success():
    s, p = _settings()
    try:
        ad = FakeProviderAdapter(s, p)
        resp = await ad.complete(_req())
        assert resp.provider_id == "fake"
        assert resp.structured["answer"] == "y"
        assert resp.usage.input_tokens is not None
    finally:
        import os; os.remove(p)


@pytest.mark.asyncio
async def test_fake_failure_maps_retryable():
    s, p = _settings(failure="timeout")
    try:
        ad = FakeProviderAdapter(s, p)
        with pytest.raises(ProviderError) as ei:
            await ad.complete(_req())
        assert ei.value.retryable is True
    finally:
        import os; os.remove(p)


@pytest.mark.asyncio
async def test_router_fallback_exhausted():
    s, p = _settings(failure="authentication")  # non-retryable -> no fallback target
    try:
        reg = ProviderRegistry(s)
        router = ModelRouter(reg, s)
        with pytest.raises(ProvidersExhaustedError):
            await router.route(_req(), "auto")
    finally:
        import os; os.remove(p)


@pytest.mark.asyncio
async def test_router_falls_back_hermes_to_fake():
    """When Hermes (first in config) errors, router falls back to fake."""
    s, p = _settings()  # fake will succeed
    try:
        # Build a registry with hermes first (unreachable) then fake.
        s.enabled_provider_targets = ["hermes", "fake"]
        s.hermes_enabled = True
        s.hermes_base_url = "http://127.0.0.1:1/v1"  # closed port -> connection error
        s.hermes_api_key = "x"
        from app.providers.implementations.hermes import HermesAdapter
        reg = ProviderRegistry(s)
        # inject a hermes adapter (registry skips it without proper env, so add manually)
        reg._adapters["hermes"] = HermesAdapter(s, base_url="http://127.0.0.1:1/v1", api_key="x")
        router = ModelRouter(reg, s)
        resp = await router.route(_req(), "auto")
        # Must have fallen back to fake and produced a plan.
        assert resp.provider_id == "fake"
        assert resp.route_metadata.get("fallback_count", 0) >= 1
    finally:
        import os; os.remove(p)
