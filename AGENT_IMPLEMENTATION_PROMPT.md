# Agent Implementation Prompt

Copy the prompt below into Codex, Claude Code, OpenCode, Hermes coding agent, or another repository-aware coding agent.

---

You are implementing the Spreadsheet AI Agent MVP in this repository. Read, in order:

1. `AGENTS.md`
2. `README.md`
3. `MVP_SCOPE.md`
4. `ARCHITECTURE.md`
5. `API_CONTRACTS.md`
6. `TOOL_REGISTRY.md`
7. `PROVIDER_ADAPTERS.md`
8. `HERMES_INTEGRATION.md`
9. `PLANNER_PROMPT.md`
10. `GOOGLE_SHEETS_ADDON.md`
11. `SECURITY_GUARDRAILS.md`
12. `TEST_PLAN.md`
13. `ACCEPTANCE_CRITERIA.md`
14. `IMPLEMENTATION_PLAN.md`
15. `REPO_STRUCTURE.md`
16. `schemas/*.json` and `.env.example`

Goal: implement the next incomplete phase in `IMPLEMENTATION_PLAN.md` as a working vertical slice, with tests and documentation synchronized. If no code exists, start with Phase 0. Do not implement later roadmap features unless explicitly requested.

Non-negotiable invariants:

- Selection-first bounded context; never default to the whole workbook.
- Every write uses versioned structured actions, deterministic validation, Preview, explicit Apply, immediate fingerprint check, snapshot, audit, and conflict-aware undo.
- Model or Hermes output is untrusted. Never execute generated code or arbitrary tool names.
- Preserve formulas outside exact targets. Reject formula overwrites unless explicitly represented, risk-elevated, and confirmed.
- Backend does not mutate Google Sheets in MVP; Apps Script executes approved bundles locally.
- Provider-specific code stays behind `ProviderAdapter`. Hermes is an adapter/meta-provider and receives no side-effect tools in P0.
- Enforce token, context, action, cell, attempt, timeout, and cost limits. Unknown cost is not zero.
- Never commit secrets or log raw cell matrices/snapshots by default.
- Core tests require no network, Google account, Hermes instance, or paid key.

Working method:

1. Inspect the existing repository and preserve user changes.
2. State which implementation phase and acceptance criteria you will complete.
3. Prefer the smallest coherent vertical slice; do not create speculative infrastructure.
4. Implement domain interfaces before vendor transports.
5. Use JSON schemas as compatibility artifacts and add drift/round-trip tests.
6. Use the fake provider and fake spreadsheet executor for deterministic tests.
7. Add typed errors and redacted structured logs.
8. Run the relevant lint, type, unit, contract, and integration checks.
9. Report changed files, verified behavior, remaining acceptance gaps, and exact next step.

For ambiguous details, choose the simplest solution consistent with documented ADRs. Record any material new decision under `docs/decisions/ADR-NNN-title.md` and link it from `ARCHITECTURE.md`. Do not weaken safety rules to resolve ambiguity. Ask for user input only if the choice changes product scope, security boundary, external credentials, or destructive behavior.

Initial technical defaults unless repository code already establishes alternatives: Python 3.12, FastAPI, Pydantic v2, httpx, SQLAlchemy/Alembic, SQLite, pytest/respx, Ruff, mypy; Apps Script HTML Service and matrix-based Range calls.

Completion for a phase requires code, automated tests, updated docs/contracts, and passing phase exit criteria. A mocked test is not a live-provider claim; label live Hermes/Google verification accurately.

---
