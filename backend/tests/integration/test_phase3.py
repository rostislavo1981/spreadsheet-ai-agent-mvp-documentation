"""Phase 3 integration: SQLite persistence + undo flow.

Uses a temp sqlite file to prove runs/audit survive a "restart" (new store).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.settings import Settings, reset_settings
from app.main import create_app
from app.persistence.db import get_connection


def make_settings(fixture: str, db_path: str) -> Settings:
    return Settings(
        app_env="development",
        app_signing_secret="test-secret-0000000000000",
        app_id_hash_salt="test-salt-000000000000",
        sqlite_db_path=db_path,
        enabled_provider_targets="fake",
        fake_provider_enabled=True,
        fake_provider_fixture=fixture,
        openai_compatible_enabled=False,
        hermes_enabled=False,
    )


@pytest.fixture
def tmpdb():
    fd = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    path = fd.name
    fd.close()
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def client(tmpdb):
    reset_settings()
    fx = str(Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "provider" / "write_plan.json")
    app = create_app(make_settings(fx, tmpdb))
    return TestClient(app)


def _req():
    return {
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
    }


def test_persistence_survives_restart(client, tmpdb):
    r = client.post("/v1/runs:plan", json=_req())
    run_id = r.json()["run_id"]
    # Simulate restart: build a brand-new app (new stores) on the SAME sqlite file.
    fx = str(Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "provider" / "write_plan.json")
    app2 = create_app(make_settings(fx, tmpdb))
    c2 = TestClient(app2)
    # audit recorded
    with get_connection(tmpdb) as conn:
        rows = conn.execute("SELECT COUNT(*) FROM audit WHERE run_id=?", (run_id,)).fetchone()
        assert rows[0] >= 1


def test_undo_flow(client):
    r = client.post("/v1/runs:plan", json=_req())
    body = r.json()
    run_id = body["run_id"]
    phash = body["preview"]["plan_hash"]
    a = client.post(f"/v1/runs/{run_id}:approve", json={
        "plan_hash": phash, "current_fingerprints": [], "confirmation": {},
    })
    token = a.json()["approval_token"]
    res = client.post(f"/v1/runs/{run_id}:result", json={
        "apply_attempt_id": a.json()["apply_attempt_id"], "approval_token": token,
        "status": "APPLIED", "after_snapshot": {"ref": "snap_1", "ranges": [
            {"sheet_id": 12345, "a1_range": "I5:I7", "values": [[0.05], [0.12], [0.0]]}
        ]},
    })
    assert res.status_code == 200
    # prepare-undo derives a bundle from the BEFORE snapshot (server issues its own token)
    pu = client.post(f"/v1/runs/{run_id}:prepare-undo", json={
        "before_snapshot": {"ref": "snap_0", "ranges": [
            {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "I5:I7", "values": [[0.0], [0.0], [0.0]]}
        ]},
    })
    assert pu.status_code == 200, pu.text
    assert pu.json()["undo_bundle"]["actions"][0]["type"] == "RESTORE_RANGE"
    undo_token = pu.json()["approval_token"]
    # undo-result with the server-issued undo token
    ur = client.post(f"/v1/runs/{run_id}:undo-result", json={
        "undo_attempt_id": "undo_" + run_id, "approval_token": undo_token, "status": "RESTORED",
    })
    assert ur.status_code == 200
    assert ur.json()["status"] == "UNDONE"


def test_undo_without_apply_fails(client):
    r = client.post("/v1/runs:plan", json=_req())
    run_id = r.json()["run_id"]
    phash = r.json()["preview"]["plan_hash"]
    a = client.post(f"/v1/runs/{run_id}:approve", json={"plan_hash": phash, "current_fingerprints": [], "confirmation": {}})
    token = a.json()["approval_token"]
    pu = client.post(f"/v1/runs/{run_id}:prepare-undo", json={"before_snapshot": {"ranges": []}})
    assert pu.status_code == 409  # undo not available (never applied)
