# Spreadsheet Tool Registry

## 1. Purpose

The Tool Registry is the only vocabulary the planner may use to propose spreadsheet changes. It is versioned, provider-neutral, deterministic, and executable by any compatible client.

Each tool definition supplies: JSON schema, semantic validator, risk level, capability/version, preview renderer metadata, snapshot requirement, and inverse strategy.

## 2. Common action envelope

```json
{
  "action_id": "act_001",
  "type": "SET_FORMULAS",
  "tool_version": "1.0",
  "target": {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7"},
  "arguments": {},
  "rationale": "Calculate deviation from the minimum quote in each row.",
  "risk": "medium",
  "expected_target_fingerprint": "sha256:..."
}
```

Sheet ID is authoritative; name is display/context metadata. A1 ranges must be normalized, bounded, and single-sheet.

## 3. P0 tools

### `SET_VALUES`

Arguments: `values` rectangular JSON matrix and `overwrite_formulas` defaulting to `false`. Strings beginning with `=`, `+`, `-`, or `@` that are intended as literals are escaped according to client rules. Matrix dimensions must exactly match the target.

### `SET_FORMULAS`

Arguments: `formulas` rectangular matrix, `notation` (`A1` in P0), and optional `fill_mode=exact`. Every non-empty entry begins with `=`. Formula locale strategy is client-normalized; previews show exact formulas to be written.

### `CLEAR_RANGE`

Arguments: `contents=true`; clearing formats is not permitted in P0. Preview includes the number of non-empty values and formulas affected.

### `FORMAT_RANGE`

Allowlisted arguments only: `background`, `font_color`, `font_weight`, `number_format`, `horizontal_alignment`, `wrap`. No arbitrary style objects. Invalid colors/formats are rejected.

### `ADD_SHEET`

Arguments: sanitized unique `title`, optional bounded `rows` and `columns`. No deletion or rename collision. Undo deletes the added sheet only if it is still empty except for actions in the same run; otherwise undo conflicts.

### `NO_OP`

No target or arguments. Used for read-only answers; a plan containing `NO_OP` cannot contain write actions.

## 4. Example plan

```json
{
  "schema_version": "1.0",
  "summary": "Adds deviation formulas and highlights results above 15%.",
  "answer": "The lowest quote in each row is used as the baseline.",
  "actions": [
    {
      "action_id": "act_001",
      "type": "SET_FORMULAS",
      "tool_version": "1.0",
      "target": {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7"},
      "arguments": {
        "notation": "A1",
        "formulas": [["=IFERROR((H5-MIN($D5:$H5))/MIN($D5:$H5),\"\")"],["=IFERROR((H6-MIN($D6:$H6))/MIN($D6:$H6),\"\")"],["=IFERROR((H7-MIN($D7:$H7))/MIN($D7:$H7),\"\")"]]
      },
      "rationale": "Calculate row-level deviation.",
      "risk": "medium"
    },
    {
      "action_id": "act_002",
      "type": "FORMAT_RANGE",
      "tool_version": "1.0",
      "target": {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7"},
      "arguments": {"number_format": "0.0%", "background": "#FCE8E6"},
      "rationale": "Make deviations visible.",
      "risk": "low"
    }
  ],
  "warnings": [],
  "context_used": ["Quotes!D4:I7"],
  "assumptions": ["Column H is the quote being compared."],
  "requires_confirmation": true
}
```

## 5. Validation pipeline

1. JSON Schema validation.
2. Known type and supported tool version.
3. Sheet ID/name consistency.
4. A1 parse, rectangular dimensions, and context/action-boundary policy.
5. Formula/value semantic rules.
6. Protected, merged, filtered, and maximum-cell policy checks.
7. Overlap analysis and deterministic action order.
8. Risk recalculation; never trust model-declared risk.
9. Canonicalization and SHA-256 plan hash.

Overlapping writes are rejected unless the registry explicitly declares them compatible (for example values followed by formatting on the same range).

## 6. Execution semantics

Action order is preserved. The client validates all actions before the first write, snapshots all targets, then executes batched calls. If an action fails, it attempts rollback from the snapshot and reports `FAILED_ROLLED_BACK` or `FAILED_PARTIAL`; neither is reported as success.

## 7. Undo

Undo is snapshot-based, not model-generated. For cell actions, restore exact formulas, values, and allowlisted formats from `before_snapshot`. For `ADD_SHEET`, enforce the special conflict rule above. Undo also uses fingerprints: if current target state differs from the recorded `after_snapshot`, stop with `UNDO_CONFLICT`.

## 8. Adding a tool

Adding a tool requires a schema, backend validator, risk rule, preview representation, client executor, snapshot/inverse semantics, capability version, unit tests, integration tests, security review, and documentation. A provider prompt change alone cannot add a tool.
