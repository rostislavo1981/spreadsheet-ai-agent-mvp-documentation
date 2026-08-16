"""Endpoint coverage for run status + sanitized audit (Phase 3/5 additions)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.settings import Settings, reset_settings
from app.main import create_app


def make_settings(fixture: str, db_path: str) -> Settings:
    return Settings(
        app_env="development", app_signing_secret="t"*20, app_id_hash_salt="s"*20,
        sqlite_db_path=db_path, enabled_provider_targets="fake",
        fake_provider_enabled=True, fake_provider_fixture=fixture,
        openai_compatible_enabled=False, hermes_enabled=False,
    )


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
    return TestClient(create_app(make_settings(fx, tmpdb)))


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


def test_get_run_and_audit(client):
    r = client.post("/v1/runs:plan", json=_req())
    run_id = r.json()["run_id"]
    gr = client.get(f"/v1/runs/{run_id}")
    assert gr.status_code == 200
    assert gr.json()["status"] == "PREVIEW_READY"
    assert gr.json()["undo_available"] is False
    # audit visible, sanitized
    au = client.get("/v1/audit")
    assert au.status_code == 200
    assert any(e["run_id"] == run_id for e in au.json()["entries"])


def test_get_run_404(client):
    assert client.get("/v1/runs/nonexistent").status_code == 404
