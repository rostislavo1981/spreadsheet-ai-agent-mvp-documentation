# Product Requirements Document

## 1. Product statement

Spreadsheet AI Agent is a conversational copilot embedded in Google Sheets. It combines the low-friction interaction of ChatGPT for Excel and Claude for Excel with a provider-independent backend, explicit change control, and spreadsheet-aware actions.

The MVP validates one hypothesis: users can safely complete meaningful analysis and editing tasks faster by selecting cells, asking in natural language, reviewing an exact preview, and applying structured changes.

## 2. Target users

- Analysts and operators working with pricing, procurement, finance, sales, and reporting sheets.
- Power users who understand formulas but want faster transformations and explanations.
- Teams that need provider choice, private models, or an existing Hermes deployment.
- Developers testing a reusable spreadsheet-agent backend before an Excel client exists.

## 3. Jobs to be done

1. Explain or summarize a selected range without editing it.
2. Create or repair formulas while preserving unrelated formulas and formatting.
3. Normalize, classify, or enrich selected rows into a chosen output column.
4. Find anomalies, duplicates, missing data, and price deviations.
5. Preview every proposed write by sheet, range, old value/formula, and new value/formula.
6. Apply approved changes and undo an applied run.
7. Choose a provider/model or let a router choose by capability, privacy, latency, and budget.

## 4. UX principles

- **In-place:** the sidebar lives beside the active workbook.
- **Context visible:** show workbook, sheet, selection, row/column count, and context scope.
- **Conversational:** retain a short run conversation and offer concise explanations.
- **Actionable:** preview cards group edits by sheet/range and explain intent.
- **Progressive:** selection is enough for most tasks; the agent may request bounded additional ranges.
- **Trustworthy:** destructive or broad changes are blocked or require stronger confirmation.
- **Fast:** first useful response target is under 8 seconds at p50 for small selections, excluding provider outages.

## 5. Core user flow

1. User selects `D4:I148` (including the intended blank output column) and opens the sidebar.
2. Client captures values, formulas, display values, basic types, headers, locale, and selection fingerprint.
3. User asks: “Add deviation from the cheapest quote in column I and flag values over 15%.”
4. Backend builds bounded context, routes the model, validates structured actions, and runs policy checks.
5. Sidebar renders summary, warnings, estimated affected cells, formulas/values, model, tokens, and cost.
6. User clicks **Apply**.
7. Client rechecks the fingerprint, snapshots target cells, applies batched actions, and reports the result.
8. Sidebar shows success and **Undo**. Undo uses the recorded pre-apply snapshot.

## 6. User scenarios

### S1 — Read-only analysis

Given a selected sales table, when the user asks for trends and anomalies, the agent returns an answer with cell/range references and zero write actions.

### S2 — Formula creation

Given headers and rows with quantity and unit price, the user asks for a total column. Preview shows `SET_FORMULAS` for the target range using locale-appropriate formulas; Apply fills the formulas without touching existing formulas elsewhere.

### S3 — Cleanup

The user asks to normalize supplier names in the selection. Preview shows exact old/new cells. Blank cells and formulas are preserved unless explicitly targeted.

### S4 — Stale preview

Another person edits a target cell after planning. Apply detects a changed fingerprint, writes nothing, and asks the user to refresh the preview.

### S5 — Hermes routing

The user selects the Hermes profile. The backend sends a normalized request to Hermes; Hermes may choose among its configured providers. The UI identifies the route as Hermes and records returned provider/model metadata when available.

### S6 — Provider failure

The preferred provider times out before a plan is produced. If policy permits and no data-boundary rule is violated, the router attempts the next eligible provider and records the fallback.

## 7. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Sidebar chat with selection metadata and context-scope control | P0 |
| FR-02 | Read-only answers grounded in supplied cells | P0 |
| FR-03 | Structured plan validated against JSON Schema | P0 |
| FR-04 | Preview and explicit Apply for all writes | P0 |
| FR-05 | Values, formulas, clear, safe formatting, and add-sheet tools | P0 |
| FR-06 | Audit log and undo for latest compatible applied runs | P0 |
| FR-07 | Provider adapter interface and model router | P0 |
| FR-08 | Hermes adapter as provider/orchestrator | P0 |
| FR-09 | Token, selection-size, action-count, cell-count, and cost limits | P0 |
| FR-10 | Stop/cancel for in-flight planning | P1 |
| FR-11 | Streaming assistant prose | P1 |
| FR-12 | Whole-workbook semantic retrieval | Later |

## 8. Non-functional requirements

- API p95 overhead excluding provider time: <500 ms for payloads under 1 MB.
- No secrets in Apps Script source, client payload logs, or audit records.
- Schema validation and policy checks are deterministic and provider-independent.
- One request ID traces client, backend, provider attempt, plan, apply, and undo.
- Runs survive backend restart; SQLite is acceptable for MVP.
- All model calls are mockable; core tests do not require internet or paid APIs.

## 9. Success metrics for pilot

- ≥70% of supported tasks accepted without manual plan correction.
- ≥90% of accepted plans apply successfully on first attempt.
- 0 silent writes and 0 writes outside previewed targets.
- 100% of applied MVP actions represented in audit history.
- ≥95% successful undo in non-conflicting workbooks.
- Median time from prompt to usable preview <12 seconds for ≤2,000 selected cells on a healthy provider.
- User-rated usefulness ≥4/5 across at least 30 real tasks.

## 10. Explicit non-goals

See `MVP_SCOPE.md`. In particular, MVP is not a marketplace-published add-on, autonomous background agent, full spreadsheet calculation engine, or general-purpose code execution system.
