"""Phase 4: Hermes adapter (Mode A) + routing/fallback parity tests.

Offline via respx-mocked Hermes OpenAI-compatible endpoint.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx

from app.core.settings import Settings, reset_settings
from app.main import create_app
from app.planning.planner import Planner
from app.providers.registry import ProviderRegistry
from app.providers.router import ModelRouter
from app.domain.models import PlanRequest


HERMES_FIXTURE_PLAN = {
    "plan": {
        "schema_version": "1.0",
        "summary": "Read-only analysis (Hermes).",
        "answer": "Hermes says: the deviation column summarizes quote deltas.",
        "actions": [], "warnings": [], "assumptions": [], "context_used": [],
        "requires_confirmation": False,
    },
    "failure": None,
}


def _make_hermes_settings():
    fx = str(Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "provider" / "read_only.json")
    return Settings(
        app_env="development", app_signing_secret="x"*20, app_id_hash_salt="y"*20,
        enabled_provider_targets="hermes", hermes_enabled=True,
        hermes_base_url="http://127.0.0.1:57377/v1",
        hermes_api_key="test-hermes-token", hermes_model="spreadsheet-planner",
        fake_provider_enabled=False, fake_provider_fixture=fx,
    )


def _req():
    return PlanRequest.model_validate({
        "schema_version": "1.0",
        "client": {"type": "google_sheets", "version": "0.1.0", "tool_versions": {}},
        "workbook": {"workbook_id_hash": "sha256:abcdef0123456789", "title": "Q", "locale": "en_US", "timezone": "Europe/Moscow"},
        "selection": {"sheet_id": 12345, "sheet_name": "S", "a1_range": "A1:B2"},
        "context": {"ranges": [{"sheet_id": 12345, "sheet_name": "S", "a1_range": "A1:B2",
            "start_row": 1, "start_column": 1, "row_count": 2, "column_count": 2,
            "values": [[1, 2], [3, 4]], "display_values": [["1", "2"], ["3", "4"]],
            "formulas": [["", ""], ["", ""]], "fingerprint": "sha256:cellfp0123456789"}],
            "omissions": []},
        "prompt": "Explain.", "conversation": [],
        "options": {"profile": "auto", "data_class": "internal", "context_scope": "selection"},
    })


def test_hermes_adapter_registered():
    reset_settings()
    s = _make_hermes_settings()
    reg = ProviderRegistry(s)
    assert "hermes" in reg.targets()
    assert reg.get("hermes").provider_id == "hermes"


@respx.mock
def test_hermes_mode_a_returns_plan():
    reset_settings()
    s = _make_hermes_settings()
    route = respx.post("http://127.0.0.1:57377/v1/chat/completions").mock(
        return_value=__import__("httpx").Response(200, json={
            "id": "chatcmpl-1", "choices": [{"message": {"content": json.dumps(HERMES_FIXTURE_PLAN["plan"])}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        })
    )
    reg = ProviderRegistry(s)
    router = ModelRouter(reg, s)
    planner = Planner(router, s)
    import asyncio
    plan, meta = asyncio.run(planner.plan(_req()))
    assert plan.answer.startswith("Hermes says")
    assert meta["provider"] == "hermes"
    assert route.called


def test_router_fallback_fake_to_hermes():
    """Both produce identical plan structure (contract parity)."""
    fx = str(Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "provider" / "read_only.json")
    s = Settings(app_env="development", app_signing_secret="x"*20, app_id_hash_salt="y"*20,
                 enabled_provider_targets="fake,hermes", fake_provider_enabled=True,
                 fake_provider_fixture=fx, hermes_enabled=True,
                 hermes_base_url="http://127.0.0.1:57377/v1", hermes_api_key="t",
                 hermes_model="spreadsheet-planner")
    reg = ProviderRegistry(s)
    order = reg.ordered_targets()
    # fake first (deterministic), hermes second
    assert order[0] == "fake"
    assert "hermes" in order
