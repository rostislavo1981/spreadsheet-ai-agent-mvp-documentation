"""Unit tests: context engine, ids/limits, policy validation."""
from __future__ import annotations

import pytest

from app.context.engine import build_messages, count_context_cells, pack_context
from app.core.errors import HardLimitError, PolicyViolationError
from app.core.ids import cell_count, parse_a1
from app.domain.models import PlanRequest
from app.policy.service import validate_action_dimensions, validate_plan, validate_scope
from app.tools.registry import get_tool, plan_changed_cells


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
    from app.core.settings import Settings
    from app.core.ids import enforce_limits
    s = Settings(max_selected_cells=10)
    with pytest.raises(HardLimitError):
        enforce_limits(s, selected_cells=11, context_cells=5)
