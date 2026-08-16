# Roadmap

## v0.1 — Google Sheets pilot

Sidebar, selection-first context, read/plan/preview/apply, P0 tools, formula preservation, audit/undo, limits, compatible providers, router, and Hermes planner mode.

## v0.2 — team-ready Google Sheets

Standalone Editor Add-on packaging, domain auth, admin provider profiles, streaming/cancel, templates, richer context expansion, comments/notes, charts, better preview diffs, telemetry controls, and PostgreSQL option.

## v0.3 — files and knowledge

Read/import PDF, XLSX, and CSV through `ContextSource` adapters; provenance/citations; workbook artifact generation; optional object storage; explicit retention controls. No file content is silently added to provider context.

## v0.4 — Excel client

Office.js task pane implementing the same client capabilities/action schema, Excel formula dialect handling, range fingerprints, snapshots, apply/undo, and compatibility tests shared with Google Sheets.

## v0.5 — MCP and Hermes tools

Expose read-only context resources and safe spreadsheet tools through MCP; map Hermes read tools through Tool Registry; introduce scoped capability grants and per-tool budgets. Write tools retain preview/approval and cannot be invoked autonomously.

## v0.6 — external data

Read-only SQL/database connectors, parameterized queries, provenance, data-class routing, and refreshable extracts. Later write support requires a separate transaction/approval design.

## Scale triggers

Replace SQLite with PostgreSQL when multiple backend replicas, organization tenancy, or write concurrency is required. Add a queue only for jobs that exceed request deadlines. Add object storage only when snapshot/file retention exceeds database limits. Add vector retrieval only after measured workbook-context needs justify it.

## Deferred research

- Formula dialect translation between Sheets and Excel.
- Large-workbook indexing and incremental fingerprints.
- Multi-user collaborative reconciliation.
- Agent evaluation set and plan-quality scoring.
- Privacy-preserving local model routing.
- Reusable skills/templates and enterprise policy packs.

Each roadmap item must preserve the P0 invariants: structured actions, explicit write approval, deterministic policy, formula preservation, bounded context/cost, audit, and conflict-aware undo.

