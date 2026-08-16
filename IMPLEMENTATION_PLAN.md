# Implementation Plan

## Delivery strategy

Build vertical slices that remain demoable. Use the fake provider first, then real providers. Do not wait for all infrastructure before testing in Sheets.

## Phase 0 — repository and contracts (0.5–1 day)

- Create structure, Python project, lint/type/test configuration, and Apps Script skeleton.
- Copy JSON schemas into runtime packages and add schema validation tests.
- Implement settings validation and typed problem responses.
- Add CI for lint, unit tests, schema validation, and secret scanning.

**Exit:** backend starts, `/health/*` and `/v1/capabilities` pass; schema examples validate.

## Phase 1 — read-only vertical slice (1–2 days)

- Implement context wire models and selection capture.
- Implement Context Engine packing and prompt template.
- Implement fake and OpenAI-compatible adapters.
- Implement registry/router with one target and cost/token limits.
- Implement `POST /runs:plan` for `NO_OP` answers.
- Build sidebar prompt/response/provider UI.

**Exit:** a selected real range can be explained with cited coordinates and zero sheet writes.

## Phase 2 — Plan → Preview → Apply (2–3 days)

- Implement AgentPlan parse, one repair attempt, Tool Registry, semantic/policy validation.
- Add P0 value/formula/clear/format actions.
- Render preview cards, samples, warnings, and impact.
- Implement approval token and run state transitions.
- Implement client preflight, snapshot, batch executor, rollback, and result reporting.

**Exit:** formulas and values can be previewed/applied; stale plan writes nothing; all supported actions are audited.

## Phase 3 — audit and undo (1–2 days)

- Add SQLite repositories/migration.
- Persist route/usage/plan/apply results.
- Implement audit endpoints/UI.
- Build snapshot-derived undo with after-state conflict checks.
- Add retention/size enforcement.

**Exit:** applied runs survive restart, appear in history, and undo safely.

## Phase 4 — routing and Hermes (1–2 days)

- Complete adapter contract suite and routing profiles/fallback.
- Implement Hermes Mode A; create Mode B transport interface and fake contract tests.
- Capture route metadata, deadlines, cancellation, unknown usage/cost.
- Verify Hermes `planner_only` tool policy and session isolation.

**Exit:** user can choose Hermes; direct and Hermes routes produce identical validated plan contracts; fallback is audited.

## Phase 5 — pilot hardening (2–3 days)

- Add `ADD_SHEET`, context expansion, limits, injection fixtures, redacted logs, and rate limiting.
- Test dates, locales, formula errors, blanks, protected/merged cells, large selections, concurrent edits, and partial rollback.
- Prepare pilot runbook, sample workbook, telemetry dashboard/query, and feedback form.
- Run every P0 acceptance criterion on a non-sensitive workbook copy.

**Exit:** release candidate tagged `v0.1.0-pilot`; no open P0 defects.

## Suggested issue breakdown

| Epic | Issue | Depends on |
|---|---|---|
| Contracts | Validate schemas/examples in CI | none |
| Backend | Run state machine + repositories | Contracts |
| Context | Capture and pack selection | Contracts |
| Providers | Protocol + fake + compatible adapter | Contracts |
| Router | profiles, budget, fallback, audit | Providers |
| Planner | prompt, parse, repair, validation | Context, Tools, Providers |
| Tools | registry + P0 validators | Contracts |
| Client | sidebar + context | Contracts |
| Apply | approval + executor + snapshots | Client, Tools, Runs |
| Undo | inverse bundle + conflict handling | Apply, Audit |
| Hermes | adapter + transports + tests | Providers, Router |
| Hardening | security and acceptance suite | all |

## Engineering constraints

- Domain tests must run without network, Google, or paid credentials.
- Keep provider SDKs optional; prefer `httpx` for compatible endpoints.
- Do not implement unsupported features opportunistically.
- Do not weaken a guardrail to make a demo pass.
- Update contracts/docs/tests in the same change as behavior.

## Pilot observability

Track request latency, provider latency, preview/apply/undo outcomes, fallback count, schema repair rate, stale conflicts, changed cells, input/output tokens, estimated/actual cost, and typed error codes. Do not track cell content.

## Release checklist

1. All P0 acceptance tests pass.
2. `.env.example` and provider config match settings code.
3. No credentials or workbook data in repository/log fixtures.
4. Database migration upgrades a clean and previous pilot DB.
5. Client/backend schema compatibility check passes.
6. Formula preservation and stale/undo conflict tests pass on real Sheets.
7. Direct provider and Hermes smoke tests pass or are explicitly marked unavailable.
8. Pilot rollback and data-retention instructions are documented.

