# Hermes Integration

## 1. Purpose

Hermes is supported as a meta-provider/orchestrator so Spreadsheet AI Agent can use the providers, routing, and optionally tools already configured behind a Hermes deployment. Core spreadsheet logic remains independent of Hermes.

Because Hermes deployments may expose different APIs, the adapter supports explicit transport modes rather than assuming one undocumented endpoint.

## 2. Modes

### Mode A — OpenAI-compatible gateway (recommended first)

Use when Hermes exposes a chat-completions-compatible HTTP endpoint. `HermesAdapter` delegates transport to the compatible HTTP client but identifies itself as `provider_id=hermes`, applies Hermes headers/profile, and captures route metadata.

Required configuration:

- `HERMES_BASE_URL`
- `HERMES_API_KEY` or another configured auth header
- `HERMES_MODEL` or profile alias
- `HERMES_MODE=openai_compatible`

### Mode B — native agent runs

Use when Hermes provides an asynchronous run/session API. A `HermesTransport` implementation maps create-run, poll/stream, cancel, and final-output operations to `ModelResponse`.

Required configuration adds endpoint templates or a small deployment-specific transport class. Do not leak sessions into core code.

### Mode C — embedded/local adapter (later)

Use only if the backend and Hermes runtime share a trusted process contract. Keep it behind the same protocol; no direct imports in domain services.

## 3. Interface

```python
class HermesTransport(Protocol):
    async def submit(self, request: HermesRunRequest) -> HermesRunHandle: ...
    async def wait(self, handle: HermesRunHandle, timeout_ms: int) -> HermesRunResult: ...
    async def cancel(self, handle: HermesRunHandle) -> None: ...
    async def health(self) -> ProviderHealth: ...
```

`HermesAdapter` is responsible for mapping normalized messages/schema/budgets into `HermesRunRequest` and mapping final output/usage/route/tool events back into `ModelResponse`.

## 4. Two safe tool policies

### `planner_only` — P0 default

Hermes receives no executable spreadsheet tools. It returns only `AgentPlan` JSON. The local Tool Registry validates and Apps Script executes it. Hermes may internally route among models, but external side-effect tools are disabled.

### `mapped_read_tools` — P1

Hermes may call explicitly mapped, read-only context tools such as `get_range_chunk`. Each call passes the local registry, authorization scope, budgets, and audit. Write tools remain disabled; writes still return as structured actions for Preview/Apply.

Never pass a wildcard tool allowlist. Hermes-native write, shell, browser, messaging, or database tools are disabled unless a future policy explicitly maps them.

## 5. Request metadata

```json
{
  "profile": "spreadsheet-planner",
  "session_key": "ephemeral-run_01J...",
  "response_schema": "agent_plan_v1",
  "limits": {"max_output_tokens": 2000, "deadline_ms": 45000},
  "tool_policy": {"mode": "planner_only", "allowed_tools": []},
  "metadata": {"run_id": "run_01J...", "client": "google_sheets"}
}
```

Use an ephemeral session by default to prevent cross-workbook memory leakage. If persistent Hermes memory is later enabled, partition it by tenant and user, exclude raw cell data from durable memory, and show the behavior in the UI/privacy notice.

## 6. Response handling

The adapter extracts the final assistant result and, when available:

- Hermes run/session ID;
- actual downstream provider and model;
- tokens and cost;
- retry/route path;
- tool call names and outcomes (never secrets or raw sensitive arguments in normal logs).

If Hermes returns prose around JSON, the adapter may extract one fenced/JSON object deterministically. Planner schema validation remains authoritative and permits at most one repair request.

## 7. Routing relationship

The Spreadsheet Model Router treats Hermes as one candidate. Once selected, Hermes may perform its own internal routing. Avoid double fallback explosions:

- outer router `MAX_PROVIDER_ATTEMPTS` includes one Hermes attempt;
- Hermes receives the remaining overall deadline;
- adapter does not retry a completed Hermes run;
- route metadata records both outer and inner choices;
- cost cap applies to the total Hermes run, not each hidden downstream call.

For `profile=hermes`, only Hermes targets are eligible. For `profile=auto`, Hermes competes with direct adapters according to configured scores and data policy.

## 8. Failure mapping

Map Hermes queue timeout, run timeout, upstream exhaustion, schema failure, tool denial, authentication, and cancellation into the common provider taxonomy. A Hermes `needs_input` state is not interactive in P0; return `PROVIDER_NEEDS_INPUT` with a safe prompt for the user to re-run.

## 9. Security requirements

- Hermes credentials stay on backend.
- TLS is mandatory except explicit localhost development.
- Each request sets a deadline, output limit, and tool policy.
- Raw spreadsheet context is not placed in Hermes durable memory by default.
- Data-egress policy must explicitly allow the Hermes deployment.
- Prompt instructions cannot expand the tool allowlist or context scope.

## 10. Test matrix

Test both transport modes with fakes: successful structured plan, downstream route metadata, timeout/cancel, malformed plan, needs-input, denied tool, hidden usage, cost cap, session isolation, and outer-router fallback. A live Hermes smoke test is opt-in and reads configuration from environment variables.

## 11. Deployment checklist

1. Identify actual Hermes API dialect and authentication.
2. Select Mode A or implement the narrow Mode B transport.
3. Configure a `spreadsheet-planner` profile with low temperature and structured output.
4. Disable side-effect tools; enable none in P0.
5. Verify session isolation and logging policy.
6. Run contract and live smoke tests.
7. Record the downstream model route in a pilot audit entry.

