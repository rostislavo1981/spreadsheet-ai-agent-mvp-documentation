# Provider Adapters and Model Router

## 1. Design goal

Spreadsheet behavior must not depend on any provider SDK. The core imports only provider-domain types and the `ProviderAdapter` protocol. Vendor packages live under `backend/app/providers/implementations/`.

## 2. Python interface

```python
from collections.abc import AsyncIterator
from typing import Protocol

class ProviderAdapter(Protocol):
    @property
    def provider_id(self) -> str: ...

    async def capabilities(self) -> ProviderCapabilities: ...
    async def list_models(self) -> list[ModelDescriptor]: ...
    async def health(self) -> ProviderHealth: ...
    async def complete(self, request: ModelRequest) -> ModelResponse: ...
    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelChunk]: ...
    def estimate_cost(self, request: ModelRequest) -> CostEstimate: ...
```

`stream` may raise `CapabilityNotSupported`; planning must always work through `complete` in P0.

## 3. Normalized request

```json
{
  "request_id": "req_01J...",
  "task": "spreadsheet_plan",
  "messages": [{"role": "user", "content": "..."}],
  "response_schema": {"name": "agent_plan_v1", "schema": {}},
  "temperature": 0.1,
  "max_output_tokens": 2000,
  "timeout_ms": 45000,
  "metadata": {"run_id": "run_01J...", "data_class": "internal"},
  "tool_policy": {"mode": "none", "allowed_tools": []}
}
```

The request contains no provider model name. The router resolves a `ModelTarget` before calling the adapter.

## 4. Normalized response

```json
{
  "provider_id": "openrouter",
  "model": "anthropic/claude-sonnet-x",
  "content": "{...json...}",
  "structured": {},
  "finish_reason": "stop",
  "usage": {"input_tokens": 1840, "output_tokens": 612, "cached_tokens": 0},
  "cost": {"amount_usd": 0.0123, "estimated": false},
  "latency_ms": 4310,
  "provider_request_id": "...",
  "route_metadata": {}
}
```

Unknown usage or cost fields are `null`, never invented as zero.

## 5. Capabilities

Adapters declare: structured JSON support, streaming, tool calling, max context/output, vision, local/private execution, usage reporting, cancellation, model listing, and health semantics. Capability discovery is cached with a short TTL and can be overridden by configuration.

## 6. Error taxonomy

All vendor errors map to:

- `AUTHENTICATION_ERROR` — do not retry or fall back across a forbidden boundary.
- `RATE_LIMITED` — retry only within deadline or route onward.
- `TIMEOUT` / `UNAVAILABLE` — eligible for fallback.
- `CONTEXT_TOO_LARGE` — repack once; do not blindly retry.
- `INVALID_REQUEST` — developer/configuration issue.
- `INVALID_STRUCTURED_OUTPUT` — Planner may attempt one repair.
- `CONTENT_BLOCKED` — surface safely; fallback only if policy permits.
- `BUDGET_EXCEEDED` — stop before provider call.
- `CAPABILITY_NOT_SUPPORTED` — router configuration error.

Errors retain provider ID, model, safe message, retryability, status code, and request ID. Raw bodies and credentials are not logged.

## 7. Model Router

### Inputs

- requested profile: `auto`, `fast`, `quality`, `cheap`, `private`, `hermes`, or an admin-defined profile;
- required capabilities;
- data classification and allowed egress destinations;
- estimated input/output tokens;
- per-run and daily budget;
- health/circuit state and latency statistics.

### Algorithm

1. Load enabled targets in configured priority order.
2. Eliminate targets that violate privacy, capability, context, or budget constraints.
3. Score eligible targets by profile weights for quality, expected cost, latency, and health.
4. Attempt the top target with the remaining deadline.
5. Fall back only for retryable failures and only to another policy-eligible target.
6. Stop at `MAX_PROVIDER_ATTEMPTS` and record every decision.

Tie-breaking must be deterministic. No model call is used to select a model in MVP.

### Routing pseudocode

```python
candidates = policy.filter(registry.targets(), request)
ranked = scorer.rank(candidates, profile=request.profile)
for target in ranked[:limits.max_provider_attempts]:
    budget.reserve(target.estimate(request))
    try:
        return await registry[target.provider].complete(request.for_target(target))
    except ProviderError as exc:
        budget.reconcile(exc.usage)
        if not exc.retryable or deadline.expired:
            raise
raise ProvidersExhausted(attempts=audit.attempts)
```

## 8. Initial implementations

- `FakeProviderAdapter`: fixture-driven plans, delays, failures, usage; mandatory for tests.
- `OpenAICompatibleAdapter`: configurable base URL/path/headers; supports OpenAI, OpenRouter, Ollama-compatible gateways, and similar servers where their behavior matches the configured dialect.
- Optional thin native adapters: add only when a provider's auth or structured-output behavior cannot be represented safely by the compatible adapter.
- `HermesAdapter`: specified separately in `HERMES_INTEGRATION.md`.

## 9. Configuration

Provider definitions are server-side. Environment variables may enable a few pilot targets; production should load a validated config file or secret manager. API keys never cross to Apps Script.

Example logical configuration:

```yaml
providers:
  - id: openrouter
    kind: openai_compatible
    base_url: https://openrouter.ai/api/v1
    api_key_env: OPENROUTER_API_KEY
    models:
      - id: configured-model-name
        profiles: [auto, quality]
        context_window: 128000
  - id: hermes
    kind: hermes
    mode: openai_compatible
    profiles: [hermes, auto]
```

Do not commit real model names as product assumptions; operators configure deployed targets and capabilities.

## 10. Adapter contract tests

Every adapter must pass the same suite: normalized success, schema request, usage normalization, timeout, 401, 429, 5xx, malformed JSON, cancellation, redacted logging, health, unknown-cost handling, and router fallback. Network tests are opt-in; mocked HTTP tests are mandatory.

