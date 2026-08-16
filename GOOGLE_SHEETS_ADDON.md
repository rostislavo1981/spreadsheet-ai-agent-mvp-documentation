# Google Sheets Client (Apps Script Sidebar)

## 1. MVP packaging

Use a container-bound Apps Script project attached to a copied pilot workbook. This avoids Marketplace review and OAuth backend work. Keep the client modules portable to a standalone Editor Add-on later.

Files should include `Code.gs`, `Sidebar.html`, small HTML partials, client JavaScript/CSS, `ContextCapture.gs`, `ActionExecutor.gs`, `Fingerprint.gs`, `ApiClient.gs`, `Properties.gs`, and `appsscript.json`.

## 2. Menu and sidebar

`onOpen` adds:

- **Spreadsheet AI → Open assistant**
- **Spreadsheet AI → Settings**
- **Spreadsheet AI → Audit history**

Sidebar states: empty, ready, planning, context-needed, preview, approving, applying, success, conflict, and error. Disable duplicate submission while a request is in flight.

## 3. Primary UI

- Selection chip: `Quotes · D4:H148 · 725 cells`.
- Prompt box with Enter-to-send and multiline support.
- Context selector: selection (default), selection + headers/neighbors, approved custom ranges.
- Profile selector: Auto, Fast, Quality, Private, Hermes—only values advertised by `/capabilities`.
- Response area with cell/range references.
- Preview cards with action, target, affected cells, old/new sample, rationale, warnings, and total impact.
- Buttons: Apply, Cancel, Refresh preview; after success, Undo.
- Compact usage disclosure: provider/route, tokens, cost when known.

## 4. Context capture

Capture server-side through Apps Script:

1. Active spreadsheet ID is hashed before sending; title is optional/configurable.
2. Active sheet ID/name and A1 selection.
3. `getValues`, `getDisplayValues`, and `getFormulas` as distinct matrices.
4. Locale/timezone and optional number formats under budget.
5. Merged-range intersection, protected-range intersection, hidden rows/columns, and filter metadata required for guardrails.
6. Header candidates: up to configured rows immediately above and columns left of selection.
7. Fingerprint over canonical sheet ID, A1 range, dimensions, typed values, and formulas.

Never infer formulas from display strings. Preserve dates as typed tagged values or ISO values plus timezone; do not rely on JSON serialization of Apps Script `Date` objects.

## 5. Selection-first and truncation

Before upload, estimate cell and byte count. Keep headers and non-empty selected cells; never truncate coordinates without recording an omission. If a selection exceeds the hard limit, ask the user to select a smaller range. Whole-workbook context requires an explicit future feature.

## 6. Apply algorithm

```text
validate bundle/version/action types
resolve every sheet by immutable sheet_id
normalize and validate every target range
read all target ranges
compare current fingerprints with approved expectations
capture before snapshot (values + formulas + allowlisted formats + cell-kind mask)
execute ordered batched actions
flush spreadsheet
capture after snapshot
report APPLIED
```

If validation or fingerprint comparison fails, write nothing. If execution fails after a write, restore the captured snapshot, flush, and report the actual rollback state.

## 7. Executor mapping

- `SET_VALUES` → rectangular `Range.setValues`, after formula-overwrite validation.
- `SET_FORMULAS` → `Range.setFormulas` with exact dimensions.
- `CLEAR_RANGE` → `Range.clearContent` only.
- `FORMAT_RANGE` → specific allowlisted setters only.
- `ADD_SHEET` → `Spreadsheet.insertSheet` with sanitized title and bounded dimensions.

Never use `eval`, dynamically generated Apps Script, arbitrary method names, or URLs from model output.

## 8. Formula handling

- Context carries formulas separately.
- Preview labels formulas clearly and shows a bounded sample.
- When restoring mixed cells, use a cell-kind mask to write formulas as formulas and literals as values.
- Literal text that may trigger formula interpretation is prefixed/escaped safely.
- The client detects locale incompatibility and returns a typed action error; it does not silently rewrite formulas.
- Existing formulas outside exact targets are never touched.

## 9. Settings and secrets

Store backend URL and pilot client token in User Properties via a settings dialog. Do not put them in source, Document Properties, sheet cells, or logs. Validate HTTPS except localhost development. Provider keys never enter Apps Script.

## 10. Audit and undo UI

Show last 20 sanitized runs: time, prompt summary, status, ranges, provider, affected cells, and cost. Undo is enabled only when backend reports eligibility. On conflict, explain which ranges changed and offer a new preview; do not force overwrite in MVP.

## 11. Performance

- Use range matrices and batched calls.
- Make one planning request, one approval request, and one result request per normal run.
- Cache `/capabilities` briefly in User Properties.
- Avoid serializing unused formatting.
- Render large previews as summaries with small before/after samples, not thousands of DOM rows.

## 12. Installation for pilot

1. Create a copy of a non-sensitive test workbook.
2. Open Extensions → Apps Script and add the client files.
3. Set least-privilege manifest scopes and deploy/test as the current user.
4. Open Spreadsheet AI settings and enter backend URL/client token.
5. Reload the workbook, open the assistant, and verify `/capabilities`.
6. Run read-only, preview/apply, conflict, and undo smoke tests.

## 13. Add-on evolution

Marketplace packaging later adds standard OAuth verification, domain administration, privacy/support pages, deployment configuration, and telemetry consent. None changes the action or backend contracts.

