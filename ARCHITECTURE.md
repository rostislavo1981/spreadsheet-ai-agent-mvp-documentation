# Architecture

## 1. System context

```text
Google Sheets sidebar
  ├─ captures selection/context
  ├─ renders conversation and preview
  └─ applies validated action bundle locally
            │ HTTPS
            ▼
FastAPI backend
  ├─ Run service / audit store (SQLite)
  ├─ Context Engine
  ├─ Model Router ── Provider Adapters ── LLM APIs
  │                                  └── Hermes Agent
  ├─ Planner / structured-output validator
  ├─ Spreadsheet Tool Registry
  └─ Policy + cost + approval service
```

Google authorization stays inside Apps Script in MVP. The backend never receives a Google refresh token and cannot independently mutate a workbook.

## 2. Component responsibilities

### Apps Script client

Owns workbook interaction, context serialization, active-user intent, pre-apply snapshot, fingerprint verification, batched execution, and outcome reporting. It accepts only action bundles returned by the backend and revalidates dimensions/targets before execution.

### Context Engine

Converts `SpreadsheetContext` into a provider-neutral prompt context. It prioritizes the active selection, headers, formulas, types, and a small neighbor window. It drops empty trailing cells, compresses repeated values, and reports all omissions. It never changes action boundaries.

### Model Router

Filters candidates by requested profile, capabilities, privacy class, context window, availability, and budget; scores the remainder; attempts providers in deterministic order; and records reasons. Routing is separate from adapters and planning.

### Provider adapters

Translate a normalized `ModelRequest` into a provider call and return `ModelResponse`. They handle authentication, HTTP mapping, structured-output hints, usage normalization, and provider-specific errors—not business policy or spreadsheet execution.

### Hermes adapter

Treats Hermes as either an OpenAI-compatible meta-provider or a native agent-run orchestrator. It preserves the same normalized response contract and captures Hermes route/tool metadata without exposing Hermes-specific semantics to the planner.

### Planner

Requests an `AgentPlan`, validates it against schema, permits one constrained repair attempt, normalizes ranges, checks formula/action dimensions, and sends the plan to policy evaluation. It never executes actions.

### Tool Registry

Defines each action's schema, risk, validator, preview formatter, executor capability name, and inverse/snapshot requirements. Clients advertise supported tool versions.

### Policy and approval service

Rejects unknown tools, out-of-context targets, oversized writes, unsafe formulas, protected/merged cells, stale inputs, and unapproved high-risk actions. It signs an expiring approval token over the canonical plan hash, workbook ID hash, and fingerprints.

### Audit store

Stores run state, provider attempts, canonical plan, approval, apply result, and encrypted or TTL-limited snapshots according to deployment policy. MVP uses SQLite behind repository interfaces.

## 3. End-to-end sequence

1. Client creates `SpreadsheetContext` and `context_fingerprint`.
2. `POST /v1/runs:plan` validates request, packs context, and creates a run. Allowed write scope starts as the selection and may include only user-approved, fingerprinted expansion ranges.
3. Router calls a provider; Planner receives structured JSON.
4. Schema and policy validation produce a preview or a typed rejection.
5. Client displays preview. No writes have occurred.
6. `POST /v1/runs/{id}:approve` checks the plan hash and returns a short-lived execution bundle. If a requested output range was outside supplied scope, the backend first returns `CONTEXT_REQUIRED`; it cannot be approved until the client supplies that range.
7. Client re-reads target ranges, compares fingerprints, and captures `before_snapshot`.
8. Client executes actions in order, stopping and rolling back locally on failure where possible.
9. `POST /v1/runs/{id}:result` records before/after snapshots and status.
10. Undo request returns an inverse bundle; client performs the same conflict checks and reports the undo result.

## 4. Run state machine

```text
CREATED → PLANNING → PREVIEW_READY → APPROVED → APPLYING → APPLIED
                    ↘ REJECTED       ↘ EXPIRED      ↘ FAILED
APPLIED → UNDO_READY → UNDOING → UNDONE
                              ↘ UNDO_CONFLICT / UNDO_FAILED
```

Transitions are server-validated and idempotent. A run cannot return to an earlier state. Replanning creates a new run linked by `supersedes_run_id`.

## 5. Context representation

The wire model carries separate matrices:

- `values`: raw typed values safe for JSON.
- `display_values`: user-visible strings when materially different.
- `formulas`: exact formulas or empty strings.
- `number_formats`: optional and omitted under budget pressure.
- `headers`: inferred candidates with confidence, not authoritative truth.
- `metadata`: A1 range, dimensions, locale, timezone, merged/protected flags.

The model sees formulas distinctly from displayed results. Empty formulas are not inferred. Context includes stable row/column coordinates so output can cite cells.

## 6. Formula preservation

- Actions target exact ranges and exact matrices.
- `SET_VALUES` is rejected if a target currently contains formulas unless `overwrite_formulas=true` and the preview marks elevated risk.
- `SET_FORMULAS` never writes empty strings outside its declared matrix.
- Client snapshots both formulas and values immediately before apply.
- Range fingerprints include formulas, values, sheet ID, range, and dimensions.
- Undo restores formulas with `setFormulas` and literal values with `setValues` using a cell-kind mask.

## 7. Consistency and idempotency

- Mutating API calls require `Idempotency-Key`.
- The approval token is bound to `run_id`, canonical action hash, workbook hash, and expiration.
- Apply is local but result reporting is idempotent by `apply_attempt_id`.
- Client must not execute the same action bundle twice; it stores recent attempt IDs in document properties.
- Fingerprints provide optimistic concurrency, not distributed locking.

## 8. Extension seams

| Future capability | Existing seam |
|---|---|
| Excel | `SpreadsheetClient` capabilities + same action schemas |
| MCP | Tool Registry adapter exposing safe tools/resources |
| Hermes tools | Hermes adapter tool policy and registry mapping |
| PDF/XLSX/CSV | `ContextSource` parser to `TabularContext` |
| External DB | Read-only `ContextSource`, later approved write tools |
| Direct Google API | `SpreadsheetExecutor` backend implementation |
| Durable scale | Audit/run repositories swapped from SQLite |

## 9. Architectural decision records

### ADR-001 — local Google execution

**Decision:** Apps Script executes actions. **Why:** quickest pilot, least OAuth infrastructure, narrow backend privilege. **Tradeoff:** sidebar must remain open and client code bears execution logic.

### ADR-002 — action DSL, not generated code

**Decision:** allowlisted JSON actions only. **Why:** deterministic validation, preview, portability, and undo. **Tradeoff:** fewer operations until tools are deliberately added.

### ADR-003 — Hermes is an adapter

**Decision:** Hermes implements the provider contract even when it internally orchestrates models/tools. **Why:** preserves router, audit, budgets, and UI behavior. **Tradeoff:** Hermes-native features require explicit capability extensions.

### ADR-004 — SQLite for MVP

**Decision:** repository interfaces backed by SQLite. **Why:** one-process deployment and durable audit with minimal operations. **Exit trigger:** multiple replicas, high write concurrency, or organization tenancy.

### ADR-005 — no full-workbook default

**Decision:** selection-first bounded context. **Why:** speed, cost, privacy, and accuracy. **Tradeoff:** the agent may need a single explicit context expansion.
