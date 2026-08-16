"""OpenAI-compatible adapter: OpenAI, OpenRouter, Ollama-compatible, etc.

Uses httpx only (no vendor SDK). Maps normalized ModelRequest → chat-completions
with `response_format: json_schema`. Maps vendor errors into the common taxonomy.
"""
from __future__ import annotations

import httpx

from ...core.errors import ProviderError
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


class OpenAICompatibleAdapter(ProviderAdapter):
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.openai_compatible_base_url.rstrip("/")
        self.api_key = self.settings.openai_compatible_api_key
        self.model = self.settings.openai_compatible_model
        self.provider_id = self.settings.openai_compatible_provider_id
        self._client = client

    @property
    def provider_id(self) -> str:  # type: ignore[no-redef]
        return self._provider_id

    @provider_id.setter
    def provider_id(self, v: str) -> None:
        self._provider_id = v

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        self._client = httpx.AsyncClient(timeout=self.settings.provider_timeout_seconds)
        return self._client

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id=self.provider_id,
            structured_output=True,
            streaming=True,
        )

    async def health(self) -> ProviderCapabilities:
        return await self.capabilities()

    async def list_models(self) -> list[ModelDescriptor]:
        return [ModelDescriptor(id=self.model or "unknown", profiles=["auto"])]

    def estimate_cost(self, request: ModelRequest) -> CostEstimate:
        # Conservative estimate only; unknown real cost is never treated as zero.
        est = (request.max_output_tokens / 1_000_000) * 0.01
        return CostEstimate(estimated_cost_usd=est)

    async def complete(self, request: ModelRequest) -> ModelResponse:
        client = await self._get_client()
        payload = {
            "model": self.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.response_schema.get("name", "agent_plan_v1"),
                    "schema": request.response_schema.get("schema", {}),
                    "strict": True,
                },
            },
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
        except httpx.TimeoutException:
            raise ProviderError("upstream timeout", provider_id=self.provider_id, retryable=True)
        except httpx.HTTPError as exc:
            raise ProviderError(f"http error: {exc}", provider_id=self.provider_id, retryable=True)

        if resp.status_code == 401:
            raise ProviderError("authentication", provider_id=self.provider_id, retryable=False, status_code=401)
        if resp.status_code == 429:
            raise ProviderError("rate limited", provider_id=self.provider_id, retryable=True, status_code=429)
        if resp.status_code >= 500:
            raise ProviderError("upstream 5xx", provider_id=self.provider_id, retryable=True, status_code=resp.status_code)
        if resp.status_code != 200:
            raise ProviderError(f"status {resp.status_code}", provider_id=self.provider_id, retryable=False, status_code=resp.status_code)

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ModelResponse(
            provider_id=self.provider_id,
            model=self.model,
            content=content,
            structured={},
            finish_reason=data["choices"][0].get("finish_reason"),
            usage=Usage(
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
            ),
            cost=Cost(amount_usd=None, estimated=False),
            latency_ms=None,
            provider_request_id=data.get("id"),
        )
