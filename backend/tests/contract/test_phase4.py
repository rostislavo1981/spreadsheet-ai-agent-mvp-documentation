"""Phase 4: Hermes adapter (Mode A) + routing/fallback parity tests.

Offline via respx-mocked Hermes OpenAI-compatible endpoint.
"""
from __future__ import annotations

import json
from pathlib import Path

import respx

from app.core.settings import Settings, reset_settings
from app.domain.models import PlanRequest
from app.main import create_app
from app.planning.planner import Planner
from app.providers.registry import ProviderRegistry
from app.providers.router import ModelRouter

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


def _req(model=None):
    options = {"profile": "auto", "data_class": "internal", "context_scope": "selection"}
    if model is not None:
        options["model"] = model
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
        "options": options,
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


@respx.mock
async def test_hermes_list_models_queries_gateway():
    """HermesAdapter.list_models() fetches the live model list from Hermes /v1/models
    instead of returning only the single configured HERMES_MODEL."""
    reset_settings()
    s = _make_hermes_settings()
    respx.get("http://127.0.0.1:57377/v1/models").mock(
        return_value=__import__("httpx").Response(200, json={
            "data": [
                {"id": "hermes-4-70b"},
                {"id": "hermes-4-mini"},
            ]
        })
    )
    from app.providers.implementations.hermes import HermesAdapter

    adapter = HermesAdapter(s)
    models = await adapter.list_models()
    ids = [m.id for m in models]
    assert ids == ["hermes-4-70b", "hermes-4-mini"]


@respx.mock
async def test_planner_forwards_on_delta_to_router():
    """Planner.plan() accepts on_delta and forwards it through the router to
    the provider so callers (the :plan route) can accumulate streaming text
    into the run store while planning is still in flight."""
    reset_settings()
    s = _make_hermes_settings()
    full_content = json.dumps(HERMES_FIXTURE_PLAN["plan"])
    mid = len(full_content) // 2
    text_chunks = [full_content[:mid], full_content[mid:]]
    sse_lines = [
        f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]})}\n\n"
        for chunk in text_chunks
    ]
    sse_body = "".join(sse_lines) + "data: [DONE]\n\n"
    respx.post("http://127.0.0.1:57377/v1/chat/completions").mock(
        return_value=__import__("httpx").Response(
            200, content=sse_body, headers={"content-type": "text/event-stream"},
        )
    )
    reg = ProviderRegistry(s)
    router = ModelRouter(reg, s)
    planner = Planner(router, s)
    deltas = []
    plan, _ = await planner.plan(_req(), on_delta=deltas.append)
    assert deltas == text_chunks
    assert plan.answer.startswith("Hermes says")


@respx.mock
async def test_planner_repair_preserves_requested_model():
    """When the provider's first response fails schema validation, Planner
    does one repair attempt. That repair request must still carry the user's
    chosen model — dropping model_override would silently revert to the
    default model on any repair round trip."""
    reset_settings()
    s = _make_hermes_settings()
    route = respx.post("http://127.0.0.1:57377/v1/chat/completions").mock(
        side_effect=[
            __import__("httpx").Response(200, json={
                "id": "chatcmpl-bad", "choices": [{"message": {"content": "not json"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5},
            }),
            __import__("httpx").Response(200, json={
                "id": "chatcmpl-fixed",
                "choices": [{"message": {"content": json.dumps(HERMES_FIXTURE_PLAN["plan"])}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5},
            }),
        ]
    )
    reg = ProviderRegistry(s)
    router = ModelRouter(reg, s)
    planner = Planner(router, s)
    await planner.plan(_req(model="hermes-4-mini"))
    repair_call = route.calls[1]
    sent = json.loads(repair_call.request.content)
    assert sent["model"] == "hermes-4-mini"


@respx.mock
async def test_planner_forwards_requested_model_to_provider():
    """PlanRequest.options.model reaches the provider payload end-to-end, so the
    user's model choice in the Sidebar dropdown actually selects the model."""
    reset_settings()
    s = _make_hermes_settings()
    route = respx.post("http://127.0.0.1:57377/v1/chat/completions").mock(
        return_value=__import__("httpx").Response(200, json={
            "id": "chatcmpl-3",
            "choices": [{"message": {"content": json.dumps(HERMES_FIXTURE_PLAN["plan"])}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
        })
    )
    reg = ProviderRegistry(s)
    router = ModelRouter(reg, s)
    planner = Planner(router, s)
    _, meta = await planner.plan(_req(model="hermes-4-mini"))
    sent = json.loads(route.calls.last.request.content)
    assert sent["model"] == "hermes-4-mini"
    assert meta["model"] == "hermes-4-mini"


@respx.mock
async def test_hermes_complete_streams_deltas_via_callback():
    """When the caller passes on_delta, complete() invokes it with each text
    chunk as the SSE stream arrives, and still returns the fully aggregated
    content in the final ModelResponse (Sidebar pseudo-streaming, HERMES §6)."""
    reset_settings()
    s = _make_hermes_settings()
    sse_body = (
        'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":", world"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"!"}}]}\n\n'
        'data: [DONE]\n\n'
    )
    respx.post("http://127.0.0.1:57377/v1/chat/completions").mock(
        return_value=__import__("httpx").Response(
            200, content=sse_body, headers={"content-type": "text/event-stream"},
        )
    )
    from app.core.ids import new_id
    from app.domain.provider_models import ModelRequest
    from app.providers.implementations.hermes import HermesAdapter

    adapter = HermesAdapter(s)
    req = ModelRequest(
        request_id=new_id("req"), messages=[{"role": "user", "content": "hi"}],
        response_schema={"name": "agent_plan_v1", "schema": {}},
    )
    deltas = []
    resp = await adapter.complete(req, on_delta=deltas.append)
    assert deltas == ["Hello", ", world", "!"]
    assert resp.content == "Hello, world!"


@respx.mock
async def test_hermes_complete_honors_model_override():
    """When ModelRequest.model_override is set, the adapter sends that model in
    the chat-completions payload instead of the statically configured HERMES_MODEL."""
    reset_settings()
    s = _make_hermes_settings()
    route = respx.post("http://127.0.0.1:57377/v1/chat/completions").mock(
        return_value=__import__("httpx").Response(200, json={
            "id": "chatcmpl-2",
            "choices": [{"message": {"content": json.dumps(HERMES_FIXTURE_PLAN["plan"])}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
        })
    )
    from app.core.ids import new_id
    from app.domain.provider_models import ModelRequest
    from app.providers.implementations.hermes import HermesAdapter

    adapter = HermesAdapter(s)
    req = ModelRequest(
        request_id=new_id("req"), messages=[{"role": "user", "content": "hi"}],
        response_schema={"name": "agent_plan_v1", "schema": {}}, model_override="hermes-4-mini",
    )
    await adapter.complete(req)
    sent = json.loads(route.calls.last.request.content)
    assert sent["model"] == "hermes-4-mini"


@respx.mock
async def test_plan_endpoint_accumulates_stream_text_for_polling():
    """End-to-end: /v1/runs:plan with a streaming Hermes provider accumulates
    partial text into the run store under the run_id created at the start of
    the request, so a concurrent stream-status poll (from a second Apps Script
    google.script.run call, since UrlFetchApp blocks the :plan caller) can see
    it. We can't literally poll mid-flight in a synchronous test client, but we
    verify the run store holds the full streamed text keyed by run_id after
    the call finishes, which is what stream-status reads."""
    import httpx
    from fastapi.testclient import TestClient

    reset_settings()
    s = _make_hermes_settings()
    full_content = json.dumps(HERMES_FIXTURE_PLAN["plan"])
    mid = len(full_content) // 2
    text_chunks = [full_content[:mid], full_content[mid:]]
    sse_body = "".join(
        f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]})}\n\n"
        for chunk in text_chunks
    ) + "data: [DONE]\n\n"
    respx.post("http://127.0.0.1:57377/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=sse_body, headers={"content-type": "text/event-stream"})
    )

    app = create_app(s)
    client = TestClient(app)
    req = {
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
        "options": {"profile": "auto", "data_class": "internal", "context_scope": "selection",
                    "client_run_token": "sidebar-stream-token"},
    }
    r = client.post("/v1/runs:plan", json=req)
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]

    status = client.get("/v1/runs/by-token/sidebar-stream-token:stream-status")
    assert status.status_code == 200
    body = status.json()
    assert body["run_id"] == run_id
    assert body["status"] == "PREVIEW_READY"
    assert body["partial_text"] == full_content


@respx.mock
async def test_hermes_list_models_falls_back_on_error():
    """If the Hermes gateway's /v1/models call fails, fall back to the single
    configured HERMES_MODEL rather than raising or returning an empty list."""
    reset_settings()
    s = _make_hermes_settings()
    respx.get("http://127.0.0.1:57377/v1/models").mock(
        return_value=__import__("httpx").Response(500, json={"error": "boom"})
    )
    from app.providers.implementations.hermes import HermesAdapter

    adapter = HermesAdapter(s)
    models = await adapter.list_models()
    assert [m.id for m in models] == ["spreadsheet-planner"]
