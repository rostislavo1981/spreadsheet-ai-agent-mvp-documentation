"""Deterministic, provider-independent policy validation (ARCHITECTURE.md §2)."""
from __future__ import annotations

from ..core.errors import PolicyViolationError
from ..core.ids import parse_a1, rect_dimensions
from ..core.settings import Settings, get_settings
from ..domain.models import PlanRequest
from ..domain.provider_models import Action, ActionType, Risk
from ..tools.registry import get_tool, plan_changed_cells


def validate_action_dimensions(action: Action) -> None:
    """Matrix dimensions must exactly match the target range."""
    if action.target is None:
        return
    sr, sc, er, ec = parse_a1(action.target.a1_range)
    expected_rows = er - sr + 1
    expected_cols = ec - sc + 1
    if action.type == ActionType.SET_VALUES:
        rows = action.arguments.get("values", [])
    elif action.type == ActionType.SET_FORMULAS:
        rows = action.arguments.get("formulas", [])
    else:
        return
    r, c = rect_dimensions(rows)
    if r != expected_rows or c != expected_cols:
        raise PolicyViolationError(
            f"{action.type.value} {action.action_id}: matrix {r}x{c} != target {expected_rows}x{expected_cols}"
        )


def validate_formula_prefixes(action: Action) -> None:
    if action.type != ActionType.SET_FORMULAS:
        return
    for row in action.arguments.get("formulas", []):
        for cell in row:
            if not isinstance(cell, str) or not cell.startswith("="):
                raise PolicyViolationError(
                    f"SET_FORMULAS {action.action_id}: every entry must begin with '='"
                )


def validate_scope(action: Action, allowed: list[str]) -> None:
    """Writes must target ranges present in the allowed write scope (selection)."""
    if action.target is None:
        return
    if action.target.a1_range not in allowed:
        raise PolicyViolationError(
            f"{action.type.value} {action.action_id}: target {action.target.a1_range} outside allowed scope"
        )


def _ranges_overlap(a: str, b: str) -> bool:
    try:
        asr, asc, aer, aec = parse_a1(a)
        bsr, bsc, ber, bec = parse_a1(b)
    except ValueError:
        return False
    return not (aer < bsr or ber < asr or aec < bsc or bec < asc)


def validate_protected_merged(action: Action, protected: list[str], merged: list[str]) -> None:
    """Reject any write that touches protected or merged cell regions (TOOL_REGISTRY §3)."""
    if action.target is None or action.type in (ActionType.NO_OP, ActionType.ADD_SHEET):
        return
    tgt = action.target.a1_range
    for p in protected:
        if _ranges_overlap(tgt, p):
            raise PolicyViolationError(
                f"{action.type.value} {action.action_id}: target {tgt} intersects protected range {p}"
            )
    for m in merged:
        if _ranges_overlap(tgt, m):
            raise PolicyViolationError(
                f"{action.type.value} {action.action_id}: target {tgt} intersects merged range {m} (cannot partially write)"
            )


def recalc_risk(action: Action) -> Risk:
    """Never trust model-declared risk; recompute deterministically."""
    return Risk(get_tool(action.type.value).default_risk)


def validate_plan(plan, req: PlanRequest, settings: Settings | None = None) -> None:
    """Pipeline: known type → scope → dimensions → formula rules → limits → risk."""
    settings = settings or get_settings()

    # NO_OP plans cannot contain write actions (TOOL_REGISTRY §3).
    if plan.actions and all(a.type == ActionType.NO_OP for a in plan.actions):
        return

    allowed_scope = [req.selection.a1_range]
    # Collect protected/merged regions across all context ranges (defense in depth).
    protected: list[str] = []
    merged: list[str] = []
    for r in req.context.ranges:
        protected.extend(getattr(r, "protected_intersections", []) or [])
        merged.extend(getattr(r, "merged_intersections", []) or [])
    # P0 rejects protected/merged targets; we model that via metadata checks.
    for action in plan.actions:
        get_tool(action.type.value)  # raises on unknown/unsupported
        validate_scope(action, allowed_scope)
        validate_protected_merged(action, protected, merged)
        validate_action_dimensions(action)
        validate_formula_prefixes(action)
        action.risk = recalc_risk(action)  # overwrite model-declared risk

    changed = plan_changed_cells(plan.actions)
    if changed > settings.max_changed_cells:
        raise PolicyViolationError(
            f"changed_cells={changed} exceeds max {settings.max_changed_cells}"
        )
    if len(plan.actions) > settings.max_actions:
        raise PolicyViolationError(
            f"actions={len(plan.actions)} exceeds max {settings.max_actions}"
        )
