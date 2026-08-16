"""Tool Registry: the only vocabulary the planner may use (TOOL_REGISTRY.md).

Each tool definition: type, version, risk, validator, snapshot requirement, inverse
strategy. Domain-only. Adding a tool requires schema + validator + risk rule + tests.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.errors import PolicyViolationError
from ..core.ids import cell_count, rect_dimensions
from ..domain.provider_models import Action, ActionType


@dataclass(frozen=True)
class ToolDefinition:
    type: ActionType
    version: str = "1.0"
    default_risk: str = "low"
    # whether the action writes to the spreadsheet (NO_OP is read-only)
    writes: bool = True
    requires_target: bool = True
    snapshot: bool = True  # snapshot before apply for undo


# P0 tools from TOOL_REGISTRY.md §3
TOOL_DEFINITIONS: dict[ActionType, ToolDefinition] = {
    ActionType.NO_OP: ToolDefinition(ActionType.NO_OP, writes=False, requires_target=False, snapshot=False),
    ActionType.SET_VALUES: ToolDefinition(ActionType.SET_VALUES, default_risk="medium"),
    ActionType.SET_FORMULAS: ToolDefinition(ActionType.SET_FORMULAS, default_risk="medium"),
    ActionType.CLEAR_RANGE: ToolDefinition(ActionType.CLEAR_RANGE, default_risk="medium"),
    ActionType.FORMAT_RANGE: ToolDefinition(ActionType.FORMAT_RANGE, default_risk="low"),
    ActionType.ADD_SHEET: ToolDefinition(ActionType.ADD_SHEET, requires_target=False, default_risk="low"),
}

P0_TOOL_VERSIONS = {t.value: "1.0" for t in TOOL_DEFINITIONS}


def get_tool(type_name: str) -> ToolDefinition:
    try:
        at = ActionType(type_name)
    except ValueError as exc:
        raise PolicyViolationError(f"unknown tool type: {type_name}") from exc
    if at not in TOOL_DEFINITIONS:
        raise PolicyViolationError(f"tool not supported in MVP: {type_name}")
    return TOOL_DEFINITIONS[at]


# Allowlist of formula-trigger characters for literal escaping (SECURITY §7).
_FORMULA_TRIGGERS = ("=", "+", "-", "@")


def plan_changed_cells(actions: list[Action]) -> int:
    total = 0
    for a in actions:
        if a.type == ActionType.SET_VALUES:
            rows = a.arguments.get("values", [])
            r, c = rect_dimensions(rows)
            total += r * c
        elif a.type == ActionType.SET_FORMULAS:
            rows = a.arguments.get("formulas", [])
            r, c = rect_dimensions(rows)
            total += r * c
        elif a.type == ActionType.CLEAR_RANGE and a.target is not None or a.type == ActionType.FORMAT_RANGE and a.target is not None:
            total += cell_count(a.target.a1_range)
        elif a.type == ActionType.ADD_SHEET:
            total += 0  # structural add; no existing cells changed
    return total
