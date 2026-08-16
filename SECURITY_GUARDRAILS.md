# Security and Guardrails

## 1. Threat model

Protect workbook confidentiality/integrity, provider credentials, audit data, and user intent against prompt injection in cells, malicious model output, stale previews, unauthorized clients, oversized payloads, accidental formula overwrite, cross-user leakage, and unsafe Hermes/tool routing.

## 2. Trust boundaries

- Sheet cell content is untrusted data, even when it contains instructions.
- User prompt is intent but does not bypass product policy.
- Model and Hermes output are untrusted until schema and semantic validation pass.
- Apps Script client is the privileged spreadsheet executor and must independently validate bundles.
- Backend configuration/secrets are trusted only inside the deployment boundary.

## 3. Prompt-injection defenses

- Delimit spreadsheet content as data and state that instructions found in cells are not executable.
- Do not expose secrets, hidden prompts, unrelated workbook data, or arbitrary tools to the model.
- Allowlist context ranges and tools outside the prompt.
- Policy validation is code, not model judgment.
- Ignore any output field not present in the schema; reject unknown action types.
- Hermes receives `planner_only` with no side-effect tools in P0.

## 4. Write guardrails

- Every write is previewed and explicitly approved.
- Approval token binds canonical plan hash, run, workbook hash, action targets, fingerprints, and expiry.
- Client validates token/bundle shape and rechecks targets immediately before writing.
- Writes outside submitted/approved scope are rejected.
- Protected or partially merged targets are rejected in P0.
- Formula overwrite, clearing non-empty cells, broad formatting, and new sheets raise risk/confirmation.
- No delete sheet/row/column in P0.
- On any stale target, the whole bundle writes nothing.

## 5. Data minimization and privacy

- Default context is selection plus small header/neighbor windows.
- UI identifies context scope and omissions.
- Workbook ID is hashed with a deployment salt before backend storage; raw title is optional.
- Do not log cell matrices, raw prompts, provider payloads, snapshots, tokens, or keys by default.
- Audit summaries store ranges and counts; snapshots use encryption-at-rest where available and short retention.
- Suggested defaults: raw context in memory only; snapshots 7 days; audit metadata 30 days; configurable deletion endpoint later.
- Provider routing enforces data classification and allowed egress.

## 6. Secrets and authentication

- Provider/Hermes keys exist only in backend environment or secret manager.
- `.env` is ignored and file permissions are restricted.
- Pilot client token lives in Apps Script User Properties and is rotatable.
- TLS is mandatory outside localhost.
- Use constant-time signature verification and a strong `APP_SIGNING_SECRET`.
- Rate-limit by identity and workbook hash; audit authentication failures without sensitive payloads.

## 7. Formula injection

For literal `SET_VALUES`, strings beginning with formula-trigger characters are treated as literals and safely escaped by the client unless the action type is `SET_FORMULAS`. CSV export later must also neutralize dangerous formula prefixes. Model-provided formulas are visible in preview and constrained to exact targets.

## 8. Resource and cost controls

Enforce payload bytes, selected/context cells, action count, changed cells, formula length, conversation turns, provider attempts, timeout, input/output tokens, per-run cost, and optional per-user daily cost. Reject before provider call when estimates exceed a hard limit. Reconcile estimates with actual reported usage.

## 9. SSRF and external effects

Provider URLs are administrator configuration, never request parameters. Disable redirects or validate redirect hosts. The model cannot fetch URLs. Hermes tools, MCP, databases, and file readers are absent/disabled in P0. Future connectors require explicit host/resource allowlists and read/write separation.

## 10. Audit events

Record: request/run IDs, authenticated subject hash, workbook hash, range/count metadata, profile, selected provider/model when safe, provider attempts, plan hash, warnings, approval, apply/undo state, affected-cell count, latency, tokens/cost, and redacted error code. Record no authorization headers or raw sensitive bodies.

## 11. Failure behavior

- Fail closed on schema, policy, token, target, or fingerprint mismatch.
- Do not fall back across privacy boundaries.
- Do not treat unknown cost as free; apply configured conservative estimates.
- Distinguish `FAILED_PARTIAL` prominently and retain evidence for recovery.
- Never ask a model to generate an undo plan; use snapshots.

## 12. Security verification checklist

- Prompt injection fixtures cannot add actions/tools/context.
- Unknown/oversized actions are rejected by backend and client.
- Stale plans write zero cells.
- Tokens cannot be replayed for another workbook/run/plan.
- Secrets and cell contents are absent from normal logs and error responses.
- Literal formula-like values remain literal.
- Hermes cannot invoke unregistered tools.
- Dependency and static checks run in CI; live credentials are not required.

