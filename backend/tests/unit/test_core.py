"""Unit tests: context engine, ids/limits, policy validation."""
from __future__ import annotations

import pytest

from app.context.engine import build_messages
from app.core.errors import HardLimitError, PolicyViolationError
from app.core.ids import cell_count, parse_a1
from app.domain.models import PlanRequest
from app.policy.service import validate_action_dimensions, validate_scope
from app.tools.registry import get_tool


def test_parse_a1():
    assert parse_a1("A1:B2") == (1, 1, 2, 2)
    assert cell_count("D4:I148") == (148 - 4 + 1) * (9 - 4 + 1)


def test_build_messages_contains_prompt():
    from tests.integration.test_phase1 import _sample_plan_request
    req = PlanRequest.model_validate(_sample_plan_request())
    msgs = build_messages(req)
    assert msgs[0]["role"] == "system"
    assert "untrusted_data" in msgs[1]["content"]
    assert "Explain the deviation" in msgs[1]["content"]


def test_get_tool_unknown_rejected():
    with pytest.raises(PolicyViolationError):
        get_tool("DELETE_EVERYTHING")


def test_validate_scope_outside():
    from app.domain.provider_models import Action, ActionType, Target
    a = Action(action_id="act_1", type=ActionType.SET_VALUES, target=Target(sheet_id=1, sheet_name="S", a1_range="Z1:Z2"),
               arguments={"values": [[1], [2]]}, rationale="x", risk="low")
    with pytest.raises(PolicyViolationError):
        validate_scope(a, allowed=["A1:B2"])


def test_validate_dimensions_mismatch():
    from app.domain.provider_models import Action, ActionType, Target
    a = Action(action_id="act_1", type=ActionType.SET_VALUES, target=Target(sheet_id=1, sheet_name="S", a1_range="A1:B2"),
               arguments={"values": [[1]]}, rationale="x", risk="low")
    with pytest.raises(PolicyViolationError):
        validate_action_dimensions(a)


def test_enforce_limits_raises():
    from app.core.ids import enforce_limits
    from app.core.settings import Settings
    s = Settings(max_selected_cells=10)
    with pytest.raises(HardLimitError):
        enforce_limits(s, selected_cells=11, context_cells=5)


def test_run_store_resolves_client_run_token():
    """A client-generated token registered against a run_id lets the client poll
    for streaming status before the :plan call that created the run has returned."""
    from app.runs.service import RunStore

    store = RunStore()
    run = store.create()
    store.register_token("client-token-abc", run.run_id)
    assert store.resolve_token("client-token-abc") == run.run_id


def test_run_store_resolve_unknown_token_raises():
    from app.runs.service import RunStore

    store = RunStore()
    with pytest.raises(KeyError):
        store.resolve_token("does-not-exist")


def test_run_store_streaming_text_accumulates():
    from app.runs.service import RunStore

    store = RunStore()
    run = store.create()
    assert store.get_stream_text(run.run_id) == ""
    store.append_stream_text(run.run_id, "Hello")
    store.append_stream_text(run.run_id, ", world")
    assert store.get_stream_text(run.run_id) == "Hello, world"


def test_parse_plan_wraps_schema_validation_error():
    """parse_plan() must wrap jsonschema.ValidationError (valid JSON that
    doesn't match the AgentPlan schema, e.g. a real model ignoring the
    schema) into our SchemaValidationError -- otherwise Planner.plan()'s
    `except SchemaValidationError` never fires, the repair attempt never
    runs, and the raw jsonschema error propagates as an unhandled 500."""
    import json as json_module

    from app.core.errors import SchemaValidationError
    from app.planning.planner import parse_plan

    invalid_but_valid_json = json_module.dumps({"not_a_valid_plan": True})
    with pytest.raises(SchemaValidationError):
        parse_plan(invalid_but_valid_json)


def test_parse_plan_wraps_json_decode_error():
    """parse_plan() must also wrap malformed (non-JSON) content between the
    extracted braces into SchemaValidationError, not a raw JSONDecodeError."""
    from app.core.errors import SchemaValidationError
    from app.planning.planner import parse_plan

    with pytest.raises(SchemaValidationError):
        parse_plan("{not valid json at all}")


def test_run_store_clear_stream_text():
    from app.runs.service import RunStore

    store = RunStore()
    run = store.create()
    store.append_stream_text(run.run_id, "partial from a failed attempt")
    store.clear_stream_text(run.run_id)
    assert store.get_stream_text(run.run_id) == ""
