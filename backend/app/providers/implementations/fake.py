"""Deterministic fake provider; mandatory for offline tests (PROVIDER_ADAPTERS §8).

Returns fixture-driven plans with deterministic usage. Supports injecting failures
via fixture for contract tests. Implements `planner_only` — no side-effect tools.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...core.ids import new_id
from ...core.settings import Settings, get_settings
from ...domain.provider_models import (
    Cost,
    CostEstimate,
    ModelDescriptor,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    Usage,
)
from ..base import ProviderAdapter


class FakeProviderAdapter(ProviderAdapter):
    def __init__(self, settings: Settings | None = None, fixture_path: str | None = None):
        self.settings = settings or get_settings()
        self.fixture_path = fixture_path or self.settings.fake_provider_fixture
        self._fixture = self._load_fixture()

    @property
    def provider_id(self) -> str:
        return "fake"

    def _load_fixture(self) -> dict[str, Any]:
        path = Path(self.fixture_path)
        if not path.exists():
            # Default read-only NO_OP plan used by Phase 1 vertical slice.
            return {
                "plan": {
                    "schema_version": "1.0",
                    "summary": "Read-only analysis (fake provider).",
                    "answer": "This is a deterministic fake-provider answer.",
                    "actions": [],
                    "warnings": [],
                    "assumptions": [],
                    "context_used": [],
                    "requires_confirmation": False,
                },
                "failure": None,
            }
        return json.loads(path.read_text(encoding="utf-8"))

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(provider_id=self.provider_id, local_execution=True)

    async def health(self) -> ProviderCapabilities:
        return await self.capabilities()

    async def list_models(self) -> list[ModelDescriptor]:
        return [ModelDescriptor(id="fake-planner", profiles=["auto", "fast"])]

    def estimate_cost(self, request: ModelRequest) -> CostEstimate:
        return CostEstimate(estimated_cost_usd=0.0)

    async def complete(self, request: ModelRequest) -> ModelResponse:
        failure = self._fixture.get("failure")
        if failure:
            from ...core.errors import ProviderError

            raise ProviderError(
                f"fake failure: {failure}",
                provider_id=self.provider_id,
                retryable=failure in ("timeout", "unavailable", "rate_limited"),
            )
        plan = self._fixture.get("plan", {})
        content = json.dumps(plan, ensure_ascii=False)
        return ModelResponse(
            provider_id=self.provider_id,
            model="fake-planner",
            content=content,
            structured=plan,
            finish_reason="stop",
            usage=Usage(input_tokens=1240, output_tokens=420),
            cost=Cost(amount_usd=0.0, estimated=True),
            latency_ms=120,
            provider_request_id=new_id("fake"),
            route_metadata={"plan_hash_kind": "fake"},
        )
