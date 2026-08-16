# Repository Instructions for Coding Agents

## Mission

Implement a safe, provider-independent Spreadsheet AI Agent MVP for Google Sheets. Treat the documentation and JSON schemas in this repository as the product/architecture source of truth.

## Required reading order

Read `README.md`, `MVP_SCOPE.md`, `ARCHITECTURE.md`, the contract/tool/provider/Hermes/client/security documents, then `IMPLEMENTATION_PLAN.md`, `TEST_PLAN.md`, and `ACCEPTANCE_CRITERIA.md` before changing behavior.

## Scope discipline

- Implement only the current MVP phase or explicit user request.
- Preserve seams for roadmap features without adding their infrastructure.
- Do not introduce direct backend Google OAuth, queues, Kubernetes, Redis, vector stores, arbitrary code execution, or autonomous writes in MVP.

## Safety invariants

- Plan → Preview → explicit Apply for every write.
- Structured allowlisted actions only; model output is untrusted.
- Apps Script revalidates and applies; backend plans/approves/audits.
- Selection-first bounded context and formula preservation.
- Fingerprint conflict detection before apply and undo.
- Snapshot-derived undo; never model-generated undo.
- Provider and Hermes secrets remain server-side.
- Hermes side-effect tools are disabled in P0.
- Hard token, cost, context, action, cell, attempt, and timeout limits.

## Code boundaries

Follow `REPO_STRUCTURE.md` dependency rules. Domain code must not import web frameworks, vendor SDKs, or persistence implementations. Add providers only through `ProviderAdapter`; add spreadsheet behavior only through Tool Registry plus both backend and client validation/execution.

## Change requirements

- Update schemas, examples, generated types, docs, and tests together.
- Add an ADR for material changes to trust boundaries, execution location, action semantics, storage, or provider/Hermes behavior.
- Keep fixtures synthetic and secrets absent.
- Preserve existing user changes and avoid unrelated rewrites.

## Verification

Run targeted tests during work and the full offline quality suite before handoff. Live Google/provider/Hermes smoke tests are separate, opt-in, and must be reported as such. Any failing P0 acceptance criterion must be stated clearly.

