# MVP Scope

## P0 — included

### Client

- Container-bound Google Apps Script for fastest pilot installation.
- Sidebar chat, selection summary, provider/profile selector, and context scope.
- Context capture for active selection plus configurable header/neighbor window.
- Preview grouped by action, range, impact, warning, and rationale.
- Explicit Apply, stale-context check, progress, result, audit list, and Undo.
- Batch use of Sheets `Range` APIs; no cell-by-cell network calls.

### Backend

- FastAPI endpoints for health, capabilities, planning, approval, result, audit, and undo bundle.
- Context Engine with selection-first packing and hard limits.
- Provider Adapter Interface, router, OpenAI-compatible adapter, deterministic fake adapter, and Hermes adapter.
- Structured response validation, repair retry (maximum one), policy validation, and cost accounting.
- SQLite persistence for runs, attempts, plans, action results, snapshots, and audit metadata.

### Structured actions

- `SET_VALUES`
- `SET_FORMULAS`
- `CLEAR_RANGE`
- `FORMAT_RANGE` with an allowlisted subset
- `ADD_SHEET`
- `NO_OP` / read-only response

Every action has a stable ID, target, dimensions, rationale, risk, and optional expected fingerprint.

### Safety

- Preview/Apply split and expiring approval token.
- Spreadsheet/sheet/range allowlists derived from the submitted context.
- Formula-injection handling for model-generated literal strings.
- Maximum ranges, cells, payload, output tokens, spend, and attempts.
- Redacted logs; secrets only on backend.
- Formula-preserving snapshots and reversible MVP actions.

## P1 — implement if pilot needs it

- Streaming answers and cancel.
- Named reusable prompt templates.
- Provider configuration UI for admins.
- Comments/notes actions.
- Insert/delete rows or columns with enhanced confirmation.
- Charts through constrained chart specifications.
- Multi-turn expansion requests for additional ranges.

## Out of scope for MVP

- Google Workspace Marketplace publication and domain-wide installation.
- Direct backend access to Google Drive/Sheets OAuth.
- Autonomous changes, scheduled agents, or background monitoring.
- Arbitrary Apps Script, Python, SQL, shell, or model-provided code execution.
- Macros, pivot tables, protected-range administration, conditional-format rule editing, merged-cell mutation.
- External browsing, arbitrary URLs, email, or third-party side effects.
- Full workbook upload by default.
- Collaborative merge resolution beyond fingerprint conflict detection.
- Guaranteed undo after subsequent structural workbook changes.
- Billing, organizations, RBAC, SSO, HA deployment, Redis, queues, Kubernetes, or vector databases.

## Pilot constraints and defaults

| Limit | Default | Hard maximum in MVP |
|---|---:|---:|
| Selected cells submitted | 2,000 | 10,000 |
| Context payload | 1 MB | 4 MB |
| Actions per plan | 20 | 100 |
| Cells changed per plan | 2,000 | 10,000 |
| Provider attempts | 2 | 3 |
| Output tokens | 2,000 | 8,000 |
| Context expansion rounds | 1 | 2 |
| Preview lifetime | 10 min | 30 min |
| Conversation turns retained | 6 | 12 |

Exceeding a hard maximum returns a typed error and guidance to reduce the selection; it never silently truncates action targets.

## Boundary rule

If a requested feature needs infrastructure not listed above, preserve an interface seam and document it in `ROADMAP.md`; do not add the infrastructure to MVP without an explicit decision record.

