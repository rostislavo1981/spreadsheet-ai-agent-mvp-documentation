# API Contracts

## 1. Conventions

- Base path: `/v1`; JSON UTF-8; timestamps RFC 3339 UTC; IDs are opaque ULID-like strings.
- `X-Request-ID` accepted or generated and returned.
- Mutating requests require `Idempotency-Key`.
- Authentication: pilot bearer token or reverse-proxy identity; never place provider keys in client requests.
- Errors use `application/problem+json`.
- Schema versions are explicit. Unknown major versions are rejected.
- Payload limits are checked before parsing large matrices.

## 2. Error envelope

```json
{
  "type": "https://spreadsheet-agent.local/problems/stale-context",
  "title": "The sheet changed after preview",
  "status": 409,
  "code": "STALE_CONTEXT",
  "detail": "Refresh the preview before applying.",
  "request_id": "req_01J...",
  "retryable": true,
  "field_errors": []
}
```

Do not expose stack traces, raw provider bodies, prompts, or credentials.

## 3. Capabilities

### `GET /v1/capabilities`

Returns API/action schema versions, enabled public profiles, client limits, and feature flags. It never returns keys, internal URLs, or hidden model configuration.

```json
{
  "api_version": "1.0",
  "action_schema_versions": ["1.0"],
  "profiles": [
    {"id": "auto", "label": "Auto", "data_classes": ["public", "internal"]},
    {"id": "hermes", "label": "Hermes", "data_classes": ["public", "internal"]}
  ],
  "tools": [{"type": "SET_VALUES", "version": "1.0"}],
  "limits": {"max_selected_cells": 10000, "max_actions": 100, "max_changed_cells": 10000},
  "features": {"streaming": false, "context_expansion": true}
}
```

## 4. Create a plan

### `POST /v1/runs:plan`

Request conforms to `schemas/plan-request.schema.json`.

```json
{
  "schema_version": "1.0",
  "client": {"type": "google_sheets", "version": "0.1.0", "tool_versions": {"SET_VALUES": "1.0", "SET_FORMULAS": "1.0"}},
  "workbook": {"workbook_id_hash": "sha256:...", "title": "Supplier quotes", "locale": "en_US", "timezone": "Europe/Moscow"},
  "selection": {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "D4:I148"},
  "context": {
    "ranges": [{
      "sheet_id": 12345,
      "sheet_name": "Quotes",
      "a1_range": "D4:I4",
      "start_row": 4,
      "start_column": 4,
      "row_count": 1,
      "column_count": 6,
      "values": [["Vendor A", 12.5, 11.9, null, 12.1, null]],
      "display_values": [["Vendor A", "12.50", "11.90", "", "12.10", ""]],
      "formulas": [["", "", "", "", "", ""]],
      "fingerprint": "sha256:..."
    }],
    "omissions": [{"reason": "selection_truncated", "original_range": "D4:I148"}]
  },
  "prompt": "Add deviation from the cheapest quote in column I.",
  "conversation": [],
  "options": {"profile": "auto", "data_class": "internal", "max_cost_usd": 0.05, "context_scope": "selection"}
}
```

Response conforms to `schemas/plan-response.schema.json`.

```json
{
  "run_id": "run_01J...",
  "status": "PREVIEW_READY",
  "assistant_message": "I prepared formulas for column I.",
  "plan": {
    "schema_version": "1.0",
    "summary": "Add deviation formulas.",
    "answer": "",
    "actions": [],
    "warnings": [],
    "assumptions": [],
    "context_used": ["Quotes!D4:I148"],
    "requires_confirmation": true
  },
  "preview": {"plan_hash": "sha256:...", "changed_cells": 144, "risk": "medium", "expires_at": "2026-08-16T12:10:00Z"},
  "route": {"provider": "hermes", "model": null, "fallback_count": 0},
  "usage": {"input_tokens": 2100, "output_tokens": 700, "cost_usd": null, "cost_estimated": true}
}
```

If context is insufficient and the expansion budget remains, return `status=CONTEXT_REQUIRED`, no actions, and bounded requests such as `{sheet_id, a1_range, reason}`. The client asks the user if the requested range exceeds current scope, captures it, and resubmits with `parent_run_id`.

## 5. Approve a plan

### `POST /v1/runs/{run_id}:approve`

```json
{
  "plan_hash": "sha256:...",
  "current_fingerprints": [{"sheet_id": 12345, "a1_range": "D4:I148", "fingerprint": "sha256:..."}],
  "confirmation": {"accepted_warnings": ["formula_overwrite"], "confirmed_at": "2026-08-16T12:04:00Z"}
}
```

The backend validates state, expiry, plan hash, fingerprint coverage, warnings, and limits. Response:

```json
{
  "run_id": "run_01J...",
  "apply_attempt_id": "apply_01J...",
  "approval_token": "opaque-signed-token",
  "expires_at": "2026-08-16T12:06:00Z",
  "action_bundle": {"schema_version": "1.0", "plan_hash": "sha256:...", "actions": []}
}
```

Approval is not proof of execution. The client must still re-read target ranges and validate fingerprints immediately before writing.

## 6. Report execution

### `POST /v1/runs/{run_id}:result`

```json
{
  "apply_attempt_id": "apply_01J...",
  "approval_token": "opaque-signed-token",
  "status": "APPLIED",
  "started_at": "2026-08-16T12:04:05Z",
  "finished_at": "2026-08-16T12:04:06Z",
  "action_results": [{"action_id": "act_001", "status": "APPLIED", "affected_cells": 144}],
  "before_snapshot": {"encoding": "cell-matrix-v1", "ranges": []},
  "after_snapshot": {"encoding": "cell-matrix-v1", "ranges": []},
  "error": null
}
```

Allowed statuses: `APPLIED`, `FAILED_ROLLED_BACK`, `FAILED_PARTIAL`, `STALE_CONTEXT`, `CANCELLED`. Snapshot size and retention limits apply. A partial failure is visible and never automatically marked undo-ready until its actual after-state is recorded.

## 7. Audit

### `GET /v1/runs?workbook_id_hash=...&limit=20&cursor=...`

Returns sanitized run summaries scoped to the authenticated user/workbook. Raw contexts and provider prompts are excluded.

### `GET /v1/runs/{run_id}`

Returns run state, preview, route, usage, action results, and undo eligibility. Snapshot contents require the dedicated undo flow.

## 8. Undo

### `POST /v1/runs/{run_id}:prepare-undo`

Request includes current target fingerprints. The backend checks the current state against the recorded after-state and returns an expiring snapshot-derived inverse action bundle or `409 UNDO_CONFLICT`.

### `POST /v1/runs/{run_id}:undo-result`

Reports `UNDONE`, `UNDO_FAILED_ROLLED_BACK`, `UNDO_FAILED_PARTIAL`, or `UNDO_CONFLICT`, using the same idempotency and snapshot principles as apply.

## 9. Health

- `GET /health/live`: process only.
- `GET /health/ready`: database and configuration; provider failures do not necessarily make the service unready.
- `GET /v1/providers/health`: admin-only sanitized adapter health.

## 10. Authentication and CORS

For a personal pilot, use a backend-issued client token stored in Apps Script User Properties, not source code. For a shared pilot, place the API behind an identity-aware proxy. Restrict CORS even though Apps Script server-side requests are not browser CORS calls. Rotate tokens and rate-limit per user/workbook.
