"""Tests for JSON schema validity of the source schemas (Phase 0 exit criterion).

Runs without network or paid credentials. Validates every example in API_CONTRACTS
and TOOL_REGISTRY against the schemas where feasible.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "app" / "schemas"


def _load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def test_schemas_present():
    for f in ("common.schema.json", "agent-plan.schema.json",
             "plan-request.schema.json", "plan-response.schema.json"):
        assert (SCHEMA_DIR / f).exists()


def test_agent_plan_example_valid():
    schema = _load("agent-plan.schema.json")
    example = {
        "schema_version": "1.0",
        "summary": "Adds deviation formulas.",
        "answer": "Lowest quote baseline used.",
        "actions": [
            {
                "action_id": "act_001",
                "type": "SET_FORMULAS",
                "tool_version": "1.0",
                "target": {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7"},
                "arguments": {
                    "formulas": [["=1"], ["=2"], ["=3"]],
                    "notation": "A1",
                },
                "rationale": "Row deviation.",
                "risk": "medium",
                "expected_target_fingerprint": None,
            }
        ],
        "warnings": [],
        "assumptions": ["H is compared quote."],
        "context_used": ["Quotes!D4:I7"],
        "requires_confirmation": True,
    }
    jsonschema.validate(instance=example, schema=schema)


def test_plan_request_minimal_valid():
    schema = _load("plan-request.schema.json")
    req = {
        "schema_version": "1.0",
        "client": {"type": "google_sheets", "version": "0.1.0", "tool_versions": {"SET_VALUES": "1.0"}},
        "workbook": {"workbook_id_hash": "sha256:abcdef0123456789", "locale": "en_US", "timezone": "Europe/Moscow"},
        "selection": {"sheet_id": 1, "sheet_name": "S", "a1_range": "A1:B2"},
        "context": {
            "ranges": [{
                "sheet_id": 1, "sheet_name": "S", "a1_range": "A1:B2",
                "start_row": 1, "start_column": 1, "row_count": 2, "column_count": 2,
                "values": [[1, 2], [3, 4]], "display_values": [["1", "2"], ["3", "4"]],
                "formulas": [["", ""], ["", ""]], "fingerprint": "sha256:xyz0123456789",
            }],
            "omissions": [],
        },
        "prompt": "Explain this range.",
        "conversation": [],
        "options": {"profile": "auto", "data_class": "internal", "context_scope": "selection"},
    }
    jsonschema.validate(instance=req, schema=schema)
