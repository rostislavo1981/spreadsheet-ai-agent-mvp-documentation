# Acceptance Criteria

## P0 product acceptance

- [ ] Sidebar opens in a real Google Sheet and accurately shows sheet, A1 selection, and cell count.
- [ ] User can ask a read-only question about ≤2,000 selected cells and receives a grounded answer with range/cell references.
- [ ] User can request values or formulas, see an exact target/sample/impact preview, and no write happens before Apply.
- [ ] Supported plans apply only to previewed ranges and report actual affected cells.
- [ ] A change to any target after preview causes atomic preflight failure with zero new writes.
- [ ] Existing formulas outside exact targets remain byte-for-byte unchanged.
- [ ] `SET_VALUES` does not overwrite formulas unless explicitly allowed and prominently confirmed.
- [ ] Literal formula-like strings remain literals.
- [ ] Applied runs appear in audit with prompt summary, targets, status, route, usage/cost when available, and timestamps.
- [ ] Undo restores exact values/formulas/formats when current after-state still matches; otherwise it writes nothing and reports conflict.

## P0 architecture acceptance

- [ ] Core planning code depends only on `ProviderAdapter`, not provider SDK classes.
- [ ] Fake, OpenAI-compatible, and Hermes adapters pass the same contract suite.
- [ ] Router filters by capability, privacy, context, and budget before scoring.
- [ ] Retryable provider failure can fall back within attempt/deadline limits; forbidden boundaries never fall back.
- [ ] Hermes can be selected explicitly and returns the same `AgentPlan` contract.
- [ ] Hermes P0 requests have no side-effect tools and use isolated/ephemeral sessions.
- [ ] All actions pass JSON Schema plus deterministic semantic/policy validation.
- [ ] Client rejects unknown tool types/versions even if backend returned them.
- [ ] Run state transitions and mutating endpoints are idempotent.

## P0 safety and operations acceptance

- [ ] Provider/Hermes credentials never appear in Apps Script, API responses, fixtures, or ordinary logs.
- [ ] Prompt injection in cells cannot expand context, tools, target ranges, or reveal secrets.
- [ ] Payload, cells, actions, tokens, attempts, timeout, and cost limits produce typed failures.
- [ ] Unknown provider cost is handled conservatively.
- [ ] Raw cell matrices and snapshots are absent from ordinary application logs.
- [ ] Backend restarts preserve runs/audit in SQLite.
- [ ] Health and capabilities endpoints function without contacting every provider synchronously.
- [ ] Required test suite runs without internet or paid credentials.

## Pilot success criteria

After at least 30 representative tasks from real users on non-sensitive workbook copies:

- ≥70% supported-task plans accepted without manual recreation.
- ≥90% accepted plans apply on first attempt.
- 0 unpreviewed or out-of-scope writes.
- ≥95% eligible undos succeed.
- Median preview time <12 seconds for ≤2,000 cells on healthy routes.
- Median usefulness rating ≥4/5.

## Release sign-off evidence

Attach CI run, manual Google Sheets matrix, direct-provider smoke result, Hermes smoke result, sample redacted audit record, formula-preservation diff, stale-preview proof, undo proof, and known limitations. If Hermes is unavailable in the test environment, contract tests may pass but the pilot release must state that live Hermes verification is pending.

