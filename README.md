# Spreadsheet AI Agent MVP

Provider-independent AI copilot for Google Sheets with a ChatGPT/Claude-for-Excel-style workflow: ask in a sidebar, inspect a concrete change preview, then explicitly apply or undo it.

This repository is an implementation-ready specification. Google Sheets is the first client; the backend contracts deliberately separate spreadsheet access, model providers, context assembly, planning, policy, and execution so Excel, MCP, files, databases, and Hermes tools can be added later.

## MVP outcome

A tester can install the Apps Script client in a real Google Sheet, select a range, ask a question or request an edit, preview structured changes, apply them, and undo the last applied run. Existing formulas outside explicitly targeted cells are never overwritten.

## Product invariants

1. **Selection first.** The selected range is the default context and initial action boundary; any expansion is explicit, bounded, and fingerprinted.
2. **Read is automatic; writes are explicit.** No write occurs before Preview and Apply.
3. **Structured actions only.** Model prose is never evaluated as code or sent directly to Sheets.
4. **Formula preservation.** Context carries values and formulas separately; untouched formulas remain untouched.
5. **Provider independence.** OpenAI, Anthropic, OpenRouter, Ollama, compatible endpoints, and Hermes implement one adapter contract.
6. **Optimistic safety.** Apply fails if the relevant sheet fingerprint changed after planning.
7. **Auditable and reversible.** Applied actions record before/after state and produce an undo bundle.
8. **Bounded cost.** Context, turns, output, provider choices, and spend have hard limits.

## Start here

- Product definition: [PRD.md](PRD.md)
- MVP boundaries: [MVP_SCOPE.md](MVP_SCOPE.md)
- Architecture and decisions: [ARCHITECTURE.md](ARCHITECTURE.md)
- Repository layout: [REPO_STRUCTURE.md](REPO_STRUCTURE.md)
- Build sequence: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
- Backend/API contracts: [API_CONTRACTS.md](API_CONTRACTS.md)
- Provider and Hermes integration: [PROVIDER_ADAPTERS.md](PROVIDER_ADAPTERS.md), [HERMES_INTEGRATION.md](HERMES_INTEGRATION.md)
- Apps Script client: [GOOGLE_SHEETS_ADDON.md](GOOGLE_SHEETS_ADDON.md)
- Actions and tools: [TOOL_REGISTRY.md](TOOL_REGISTRY.md)
- Provider-neutral planner prompt: [PLANNER_PROMPT.md](PLANNER_PROMPT.md)
- Safety, tests, acceptance: [SECURITY_GUARDRAILS.md](SECURITY_GUARDRAILS.md), [TEST_PLAN.md](TEST_PLAN.md), [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md)
- Agent handoff: [AGENT_IMPLEMENTATION_PROMPT.md](AGENT_IMPLEMENTATION_PROMPT.md)
- Environment variables: [ENVIRONMENT.md](ENVIRONMENT.md)

## Fastest implementation path

1. Scaffold the repository exactly as described in `REPO_STRUCTURE.md`.
2. Implement Pydantic models from `schemas/*.json` and API endpoints from `API_CONTRACTS.md`.
3. Implement one OpenAI-compatible provider plus deterministic fake provider.
4. Build selection capture, sidebar chat, preview cards, local apply, and result reporting.
5. Add snapshots, audit, undo, router, and Hermes adapter.
6. Run the acceptance suite on a copy of a real workbook.

## Local configuration

Copy `.env.example` to `.env`. Never commit `.env`. The MVP needs one enabled provider; Hermes can be the only provider if desired. See [PROVIDER_ADAPTERS.md](PROVIDER_ADAPTERS.md) for precedence and [HERMES_INTEGRATION.md](HERMES_INTEGRATION.md) for modes.

## Recommended MVP stack

- Python 3.12, FastAPI, Pydantic v2, httpx
- SQLite + SQLAlchemy/Alembic for runs and audit
- pytest, respx, Ruff, mypy
- Google Apps Script, HTML/CSS/vanilla TypeScript or JavaScript
- JSON Schema Draft 2020-12 for cross-client contracts

## Definition of done

The MVP is done only when every item in `ACCEPTANCE_CRITERIA.md` marked **P0** passes, including stale-preview rejection, formula preservation, undo, provider fallback, Hermes contract tests, and token/cost enforcement.
