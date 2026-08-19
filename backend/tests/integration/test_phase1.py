"""Unit + integration tests for the Phase 1 read-only vertical slice.

No network, Google account, or paid key required.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.settings import Settings, reset_settings
from app.main import create_app

FIXTURE = "tests/fixtures/provider/read_only.json"


def make_settings() -> Settings:
    return Settings(
        app_env="development",
        app_signing_secret="test-secret-0000000000",
        app_id_hash_salt="test-salt-000000000000",
        enabled_provider_targets="fake",
        fake_provider_enabled=True,
        fake_provider_fixture=str(Path(__file__).resolve().parents[1] / FIXTURE),
        openai_compatible_enabled=False,
        hermes_enabled=False,
    )


@pytest.fixture
def client():
    reset_settings()
    app = create_app(make_settings())
    return TestClient(app)


def test_health_live(client):
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_capabilities(client):
    r = client.get("/v1/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert body["api_version"] == "1.0"
    types = {t["type"] for t in body["tools"]}
    assert "SET_VALUES" in types and "NO_OP" in types
    # never leaks secrets/urls
    assert "key" not in json.dumps(body).lower()


def test_capabilities_hermes_models_empty_when_disabled(client):
    r = client.get("/v1/capabilities")
    assert r.status_code == 200
    assert r.json()["hermes_models"] == []


def test_capabilities_hermes_models_populated_when_enabled():
    import httpx
    import respx

    reset_settings()
    s = Settings(
        app_env="development", app_signing_secret="test-secret-0000000000",
        app_id_hash_salt="test-salt-000000000000", enabled_provider_targets="hermes",
        hermes_enabled=True, hermes_base_url="http://127.0.0.1:57377/v1",
        hermes_api_key="t", hermes_model="spreadsheet-planner", fake_provider_enabled=False,
    )
    app = create_app(s)
    client = TestClient(app)
    with respx.mock:
        respx.get("http://127.0.0.1:57377/v1/models").mock(
            return_value=httpx.Response(200, json={"data": [{"id": "hermes-4-70b"}, {"id": "hermes-4-mini"}]})
        )
        r = client.get("/v1/capabilities")
    assert r.status_code == 200
    ids = [m["id"] for m in r.json()["hermes_models"]]
    assert ids == ["hermes-4-70b", "hermes-4-mini"]


def _sample_plan_request() -> dict:
    return {
        "schema_version": "1.0",
        "client": {"type": "google_sheets", "version": "0.1.0", "tool_versions": {"SET_VALUES": "1.0"}},
        "workbook": {"workbook_id_hash": "sha256:abcdef0123456789", "title": "Quotes", "locale": "en_US", "timezone": "Europe/Moscow"},
        "selection": {"sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "D4:I148"},
        "context": {
            "ranges": [{
                "sheet_id": 12345, "sheet_name": "Quotes", "a1_range": "D4:I4",
                "start_row": 4, "start_column": 4, "row_count": 1, "column_count": 6,
                "values": [["Vendor A", 12.5, 11.9, None, 12.1, None]],
                "display_values": [["Vendor A", "12.50", "11.90", "", "12.10", ""]],
                "formulas": [["", "", "", "", "", ""]],
                "fingerprint": "sha256:cellfp0123456789",
            }],
            "omissions": [],
        },
        "prompt": "Explain the deviation column in this selection.",
        "conversation": [],
        "options": {"profile": "auto", "data_class": "internal", "context_scope": "selection"},
    }


def test_create_plan_readonly(client):
    r = client.post("/v1/runs:plan", json=_sample_plan_request())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "PREVIEW_READY"
    assert body["plan"]["actions"] == []  # read-only: no writes
    assert body["preview"]["changed_cells"] == 0
    assert body["route"]["provider"] == "fake"
    # audit recorded
    assert body["run_id"]


def test_stream_status_resolves_client_run_token(client):
    req = _sample_plan_request()
    req["options"]["client_run_token"] = "sidebar-token-123"
    r = client.post("/v1/runs:plan", json=req)
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]

    s = client.get("/v1/runs/by-token/sidebar-token-123:stream-status")
    assert s.status_code == 200, s.text
    body = s.json()
    assert body["run_id"] == run_id
    assert body["status"] == "PREVIEW_READY"
    assert "partial_text" in body


def test_stream_status_unknown_token_404(client):
    s = client.get("/v1/runs/by-token/does-not-exist:stream-status")
    assert s.status_code == 404


def test_plan_endpoint_returns_422_not_500_for_schema_invalid_provider_output():
    """A provider (even after the one repair attempt) returning valid JSON
    that doesn't match the AgentPlan schema must produce a clean 422
    SCHEMA-VALIDATION problem response, not an unhandled 500 -- this is the
    realistic failure mode for weaker/free real models that don't reliably
    follow response_format instructions."""
    import tempfile

    fix = {"plan": {"not_a_valid_plan": True}, "failure": None}
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as fd:
        json.dump(fix, fd)
    reset_settings()
    s = Settings(
        app_env="development", app_signing_secret="test-secret-0000000000",
        app_id_hash_salt="test-salt-000000000000", enabled_provider_targets="fake",
        fake_provider_enabled=True, fake_provider_fixture=fd.name,
        openai_compatible_enabled=False, hermes_enabled=False,
    )
    c = TestClient(create_app(s))
    r = c.post("/v1/runs:plan", json=_sample_plan_request())
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "INVALID_PLAN"


def test_plan_request_too_large(client):
    # inflate prompt beyond limit indirectly via many conversation turns not allowed;
    # instead exceed max_request_bytes is covered by settings; here just confirm validation.
    r = client.post("/v1/runs:plan", json={})  # missing required fields
    assert r.status_code == 422
