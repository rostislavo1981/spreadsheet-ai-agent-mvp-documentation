# Spreadsheet AI Agent — Backend (MVP)

Provider-independent AI copilot backend for Google Sheets, built from the
`spreadsheet-ai-agent-mvp-documentation` spec. Plan → Preview → explicit Apply,
structured allowlisted actions only, selection-first, formula-preserving,
snapshot-derived undo, provider-agnostic (OpenAI / OpenRouter / Ollama /
**Hermes**).

## Layout
```
app/
  core/        settings (startup validation), errors (problem+json), ids (limits/hash/sign)
  domain/      wire models: context, provider contracts, AgentPlan
  context/     Context Engine: selection-first packing + provider-neutral prompt
  planning/    Planner: provider call, schema validation, 1 repair, policy check, injection scan
  policy/      deterministic provider-independent policy validation
  providers/   ProviderAdapter protocol + fake / openai_compatible / hermes adapters + registry + router
  tools/       Tool Registry (only vocabulary the planner may use)
  runs/        Run lifecycle state machine, undo service
  audit/       sanitized audit store interface
  persistence/ SQLite repositories (runs + audit) behind the same interface
  api/         FastAPI routes: /v1/runs:plan, :approve, :result, :prepare-undo, :undo-result, /v1/capabilities, ratelimit
apps-script/  Google Sheets sidebar client (capture, preview, apply, undo) + ActionExecutor
tests/         unit / contract (offline, no network or keys) / integration
```

## Quickstart
```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
cp .env.example .env   # adjust secrets
# run
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
# test (offline, no keys)
python -m pytest tests -q
```

## Safety invariants (enforced)
- Read auto, write only on explicit Apply with a signed, expiring approval token.
- Only allowlisted P0 actions; model output is untrusted + schema-validated.
- Selection-first bounded context; formulas preserved; snapshot-derived undo.
- Prompt-injection scan (fail-closed); rate limit; hard caps on cells/tokens/cost.
- Provider & Hermes secrets server-side; client never sees them. Raw logging off by default.

## Implemented phases
- Phase 0: repo skeleton, JSON schemas in runtime, settings validation, CI.
- Phase 1: read-only vertical slice (fake provider; NO_OP analysis).
- Phase 2: Plan → Preview → Apply (P0 actions, approval token, client executor).
- Phase 3: SQLite persistence (survives restart) + audit + snapshot-derived undo.
- Phase 4: Hermes adapter (Mode A) + routing/fallback parity.
- Phase 5: pilot hardening — ADD_SHEET, limits, injection defense, redacted logs, rate limit.

## Not yet implemented
Real Google Apps Script deployment wiring, full OpenAI/OpenRouter live calls
(only offline fake + contract-mocked Hermes tested), browser-based e2e on a live
sheet, async job queue, multi-tenant auth. These are Phase 5 pilot hardening
items left for live pilot.
