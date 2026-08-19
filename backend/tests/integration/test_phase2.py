"""Phase 2 integration: plan -> approve -> result (apply flow).

Offline; uses write_plan fixture (deterministic SET_VALUES).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.settings import Settings, reset_settings
from app.main import create_app


def make_settings(fixture: str) -> Settings:
    return Settings(
        app_env="development",
        app_signing_secret="test-secret-0000000000000",
        app_id_hash_salt="test-salt-000000000000",
        enabled_provider_targets="fake",
        fake_provider_enabled=True,
        fake_provider_fixture=fixture,
        openai_compatible_enabled=False,
        hermes_enabled=False,
    )


@pytest.fixture
def client():
    reset_settings()
    from pathlib import Path
    fx = str(Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "provider" / "write_plan.json")
    app = create_app(make_settings(fx))
    return TestClient(app)


def _req():
    return {
        "schema_version": "1.0",
        "client": {"type": "google_sheets", "version": "0.1.0", "tool_versions": {"SET_VALUES": "1.0"}},
        "workbook": {"workbook_id_hash": "sha256:abcdef0123456789", "title": "Quotes", "locale": "en_US", "timezone": "Europe/Moscow"},
        "selection": {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7"},
        "context": {
            "ranges": [{
                "sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7",
                "start_row": 5, "start_column": 9, "row_count": 3, "column_count": 1,
                "values": [[None], [None], [None]],
                "display_values": [[""], [""], [""]], "formulas": [[""], [""], [""]],
                "fingerprint": "sha256:cellfp0123456789",
            }],
            "omissions": [],
        },
        "prompt": "Fill deviation in I5:I7.",
        "conversation": [],
        "options": {"profile": "auto", "data_class": "internal", "context_scope": "selection"},
    }


def test_plan_approve_result_flow(client):
    r = client.post("/v1/runs:plan", json=_req())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "PREVIEW_READY"
    assert body["plan"]["actions"][0]["type"] == "SET_VALUES"
    run_id = body["run_id"]
    phash = body["preview"]["plan_hash"]

    # Approve
    a = client.post(f"/v1/runs/{run_id}:approve", json={
        "plan_hash": phash,
        "current_fingerprints": [{"sheet_id": 12345, "a1_range": "I5:I7", "fingerprint": "sha256:cellfp0123456789"}],
        "confirmation": {"accepted_warnings": [], "confirmed_at": "2026-08-16T12:04:00Z"},
    })
    assert a.status_code == 200, a.text
    ad = a.json()
    assert ad["apply_attempt_id"].startswith("apply_")
    token = ad["approval_token"]
    assert ad["action_bundle"]["actions"]

    # Result
    res = client.post(f"/v1/runs/{run_id}:result", json={
        "apply_attempt_id": ad["apply_attempt_id"],
        "approval_token": token,
        "status": "APPLIED",
        "started_at": "2026-08-16T12:04:05Z",
        "finished_at": "2026-08-16T12:04:06Z",
        "action_results": [{"action_id": "act_001", "status": "APPLIED", "affected_cells": 3}],
        "before_snapshot": {"encoding": "cell-matrix-v1", "ranges": []},
        "after_snapshot": {"encoding": "cell-matrix-v1", "ranges": []},
        "error": None,
    })
    assert res.status_code == 200
    assert res.json()["status"] == "APPLIED"


def test_approve_wrong_hash(client):
    r = client.post("/v1/runs:plan", json=_req())
    run_id = r.json()["run_id"]
    a = client.post(f"/v1/runs/{run_id}:approve", json={
        "plan_hash": "sha256:wrong", "current_fingerprints": [], "confirmation": {},
    })
    assert a.status_code == 409


def test_result_bad_token(client):
    r = client.post("/v1/runs:plan", json=_req())
    run_id = r.json()["run_id"]
    a = client.post(f"/v1/runs/{run_id}:approve", json={
        "plan_hash": r.json()["preview"]["plan_hash"], "current_fingerprints": [], "confirmation": {},
    })
    res = client.post(f"/v1/runs/{run_id}:result", json={
        "apply_attempt_id": a.json()["apply_attempt_id"], "approval_token": "bad.token",
        "status": "APPLIED",
    })
    assert res.status_code == 401
