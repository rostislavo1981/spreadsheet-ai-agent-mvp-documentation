"""Phase 5 extras: protected/merged cell defense, context expansion, metrics."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.settings import Settings, reset_settings
from app.main import create_app
from app.policy.service import validate_plan, validate_protected_merged
from app.domain.models import PlanRequest
from app.domain.provider_models import AgentPlan


def make_settings(fx):
    return Settings(app_env="development", app_signing_secret="t"*20, app_id_hash_salt="s"*20,
                   enabled_provider_targets="fake", fake_provider_enabled=True,
                   fake_provider_fixture=fx, openai_compatible_enabled=False, hermes_enabled=False)


@pytest.fixture
def tmpdb():
    fd = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    p = fd.name; fd.close()
    yield p
    Path(p).unlink(missing_ok=True)


@pytest.fixture
def client(tmpdb):
    reset_settings()
    fx = str(Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "provider" / "write_plan.json")
    return TestClient(create_app(make_settings(fx)))


def _req_with(protected=None, merged=None, scope="selection"):
    return PlanRequest.model_validate({
        "schema_version": "1.0",
        "client": {"type": "google_sheets", "version": "0.1.0", "tool_versions": {"SET_VALUES": "1.0"}},
        "workbook": {"workbook_id_hash": "sha256:abcdef0123456789", "title": "Q", "locale": "en_US", "timezone": "Europe/Moscow"},
        "selection": {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7"},
        "context": {"ranges": [{"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7",
            "start_row": 5, "start_column": 9, "row_count": 3, "column_count": 1,
            "values": [[None], [None], [None]], "display_values": [[""], [""], [""]],
            "formulas": [[""], [""], [""]],
            "protected_intersections": protected or [], "merged_intersections": merged or [],
            "fingerprint": "sha256:cellfp0123456789"}],
            "omissions": []},
        "prompt": "Fill.", "conversation": [],
        "options": {"profile": "auto", "data_class": "internal", "context_scope": scope},
    })


def _plan(target="I5:I7"):
    return AgentPlan.model_validate({
        "schema_version": "1.0", "summary": "x", "answer": "",
        "actions": [{"action_id": "act_1", "type": "SET_VALUES", "tool_version": "1.0",
            "target": {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": target},
            "arguments": {"values": [[0.1], [0.2], [0.3]], "overwrite_formulas": False},
            "rationale": "x", "risk": "medium", "expected_target_fingerprint": None}],
        "warnings": [], "assumptions": [], "context_used": [], "requires_confirmation": True,
    })


def test_protected_rejected():
    req = _req_with(protected=["I5:I7"])
    with pytest.raises(Exception):
        validate_plan(_plan(), req)


def test_merged_rejected():
    req = _req_with(merged=["I5:I7"])
    with pytest.raises(Exception):
        validate_plan(_plan(), req)


def test_overlap_detection():
    from app.core.errors import PolicyViolationError
    a = _plan("I5:I7").actions[0]
    # target I5:I7 overlaps protected I6:I6
    with pytest.raises(PolicyViolationError):
        validate_protected_merged(a, ["I6:I6"], [])


def test_context_expansion_flag():
    from app.context.engine import is_expanded_scope
    assert is_expanded_scope(_req_with(scope="selection_with_neighbors")) is True
    assert is_expanded_scope(_req_with(scope="selection")) is False


def test_metrics_endpoint(client):
    # generate one plan + apply so metrics have data
    r = client.post("/v1/runs:plan", json={
        "schema_version": "1.0",
        "client": {"type": "google_sheets", "version": "0.1.0", "tool_versions": {"SET_VALUES": "1.0"}},
        "workbook": {"workbook_id_hash": "sha256:abcdef0123456789", "title": "Q", "locale": "en_US", "timezone": "Europe/Moscow"},
        "selection": {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7"},
        "context": {"ranges": [{"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7",
            "start_row": 5, "start_column": 9, "row_count": 3, "column_count": 1,
            "values": [[None], [None], [None]], "display_values": [[""], [""], [""]],
            "formulas": [[""], [""], [""]], "fingerprint": "sha256:cellfp0123456789"}],
            "omissions": []},
        "prompt": "Fill.", "conversation": [],
        "options": {"profile": "auto", "data_class": "internal", "context_scope": "selection"},
    })
    run_id = r.json()["run_id"]
    phash = r.json()["preview"]["plan_hash"]
    a = client.post(f"/v1/runs/{run_id}:approve", json={"plan_hash": phash, "current_fingerprints": [], "confirmation": {}})
    token = a.json()["approval_token"]
    client.post(f"/v1/runs/{run_id}:result", json={
        "apply_attempt_id": a.json()["apply_attempt_id"], "approval_token": token,
        "status": "APPLIED", "after_snapshot": {"ref": "s", "ranges": []}})
    m = client.get("/v1/metrics")
    assert m.status_code == 200
    assert m.json()["runs_total"] >= 1
    assert m.json()["applied"] >= 1
