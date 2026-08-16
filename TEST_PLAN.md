# Test Plan

## 1. Principles

Core behavior is deterministic and testable without live providers or Google. Use fixtures for provider responses and a spreadsheet emulator/fake for most execution tests; reserve a small manual/live suite for Apps Script semantics.

## 2. Test layers

### Unit

- A1 parsing/normalization and rectangular dimensions.
- Typed value/date serialization and canonical fingerprints.
- Context packing, headers, omissions, and token estimates.
- Action schema/semantic validation and risk recalculation.
- Formula overwrite/preservation and literal injection escaping.
- Run state machine and approval token binding/expiry.
- Cost reservation/reconciliation and router scoring.
- Snapshot inverse generation and conflict detection.

### Contract

- JSON examples validate against schemas.
- Pydantic serialization round-trips with cross-client fixtures.
- Every provider adapter passes the common adapter suite.
- Hermes Mode A/Mode B fake transports normalize identical outputs.
- Client capability/tool-version negotiation rejects mismatches.

### Integration

- Plan endpoint with fake provider through policy to persisted preview.
- Approval/result/undo lifecycle with SQLite.
- Router fallback for timeout/429/5xx and no fallback for policy/auth/budget.
- Malformed output → one repair → success/failure.
- Stale fingerprint → zero writes.
- Partial executor failure → rollback/report/audit.

### Apps Script/live Google Sheets

Use a disposable workbook copy with fixtures for literals, formulas, dates, blanks, errors, hidden rows, protected ranges, merged cells, filters, and multiple sheets. Verify matrix reads/writes, locale formulas, batching, rollback, and UI states.

### Security

- Cell prompt injection attempts to reveal secrets or call tools.
- Unknown fields/tools, traversal-like sheet names, invalid A1, overlapping actions.
- Token replay across run/workbook/expired preview.
- Oversized body, cell/action/formula limits, rate limiting.
- SSRF via requested provider URL or model output.
- Secret/raw-context log scanning and error redaction.
- Hermes tool escalation and persistent-session leakage.

### Performance

Benchmark 100, 2,000, and 10,000 selected cells; preview with 1, 20, and 100 actions; audit pagination; snapshot size; concurrent planning; provider timeout. Separate backend overhead from provider latency.

## 3. Critical scenario matrix

| Scenario | Expected result |
|---|---|
| Read-only question | answer, cited ranges, no Apply button/actions |
| Set values over blank cells | exact preview, apply, audit, undo |
| Target contains formula | blocked unless explicit elevated overwrite |
| Change outside approved scope | backend rejects plan |
| Target edited after preview | apply writes zero cells, `STALE_CONTEXT` |
| Formula matrix wrong size | schema/semantic rejection |
| Literal starts with `=` | remains literal under `SET_VALUES` |
| Provider timeout | eligible fallback within attempt/deadline limit |
| Hermes returns malformed JSON | one repair maximum, then typed failure |
| Undo after later edit | `UNDO_CONFLICT`, no overwrite |
| Executor fails mid-run | rollback attempted, actual status/audit retained |
| Unknown provider cost | conservative estimate/cap, never treated as zero |

## 4. Fixtures

- `quotes_small`: headers, currencies, blanks, formulas.
- `sales_dates_locale`: dates/decimal separators/timezone.
- `mixed_formula_values`: formula-preservation matrix.
- `hostile_cells`: prompt injections and formula-like literals.
- `protected_merged`: protected and merged target conflicts.
- Provider recordings contain synthetic data only and have secrets removed.

## 5. Quality gates

- All unit/contract/integration P0 tests pass.
- Coverage target: ≥85% domain/policy/router/tool code; 100% run state transitions and risk rules.
- Ruff, formatting, mypy, JSON Schema validation, dependency audit, and secret scan pass.
- No flaky network tests in required CI.
- Manual Apps Script checklist passes for each supported locale in the pilot.

## 6. Defect severity

- **P0:** unpreviewed/out-of-range write, formula loss, cross-user leak, secret exposure, incorrect success after partial write, undo overwrite on conflict.
- **P1:** supported task cannot apply, router violates profile/budget, audit missing, sidebar blocked.
- **P2:** preview/usability issue with safe workaround, inaccurate cost marked as estimate.

Any open P0 blocks pilot release.

