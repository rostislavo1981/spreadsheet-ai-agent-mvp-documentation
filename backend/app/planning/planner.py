"""Planner: request provider, validate AgentPlan schema, one repair, policy check.

Never executes actions. Maps provider output JSON → AgentPlan. Handles read-only
NO_OP answers (Phase 1 vertical slice) and structured plan previews (Phase 2+).
"""
from __future__ import annotations

import json
from typing import Any

import jsonschema

from ..context.engine import build_messages, count_context_cells
from ..core.errors import SchemaValidationError
from ..core.ids import new_id, sha256_hex
from ..core.settings import Settings, get_settings
from ..domain.models import PlanRequest
from ..domain.provider_models import AgentPlan, ModelRequest
from ..policy.service import validate_plan

_SCHEMA_PATH = __import__("pathlib").Path(__file__).resolve().parents[1] / "schemas" / "agent-plan.schema.json"


def _load_plan_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _extract_json(content: str) -> dict[str, Any]:
    """Deterministically extract one JSON object from model content."""
    content = content.strip()
    if content.startswith("```"):
        # strip ```json ... ``` fences
        content = content.split("```", 2)[1]
        content = content.removeprefix("json")
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1:
        raise SchemaValidationError("no JSON object found in provider content")
    return json.loads(content[start:end + 1])


def parse_plan(content: str) -> AgentPlan:
    obj = _extract_json(content)
    jsonschema.validate(instance=obj, schema=_load_plan_schema())
    return AgentPlan.model_validate(obj)


def plan_hash(plan: AgentPlan) -> str:
    return sha256_hex(plan.model_dump_json())


def _changed_cells(plan: AgentPlan) -> int:
    from ..tools.registry import plan_changed_cells

    return plan_changed_cells(plan.actions)


class Planner:
    def __init__(self, router, settings: Settings | None = None):
        self.router = router
        self.settings = settings or get_settings()

    async def plan(self, req: PlanRequest) -> tuple[AgentPlan, dict[str, Any]]:
        ctx_cells = count_context_cells(req.context)
        from ..core.errors import HardLimitError

        if ctx_cells > self.settings.max_context_cells:
            raise HardLimitError(f"context_cells={ctx_cells} exceeds max {self.settings.max_context_cells}")

        messages = build_messages(req)
        model_req = ModelRequest(
            request_id=new_id("req"),
            messages=messages,
            response_schema={"name": "agent_plan_v1", "schema": _load_plan_schema()},
            temperature=0.1,
            max_output_tokens=self.settings.max_output_tokens,
            timeout_ms=self.settings.provider_timeout_seconds * 1000,
            metadata={"run_id": req.parent_run_id or "", "data_class": req.options.data_class.value},
            tool_policy={"mode": "none", "allowed_tools": []},
        )
        resp = await self.router.route(model_req, req.options.profile)
        try:
            plan = parse_plan(resp.content)
        except SchemaValidationError:
            # one constrained repair attempt (PLANNER_PROMPT §5)
            repaired = await self._repair(model_req, resp.content)
            plan = parse_plan(repaired)
        validate_plan(plan, req, self.settings)

        # Defense-in-depth: reject plans attempting to subvert the contract.
        from .safety import scan_plan_text
        inj = scan_plan_text(plan.summary or "", plan.answer or "",
                             *(a.rationale for a in plan.actions))
        if inj:
            from ..core.errors import PolicyViolationError
            raise PolicyViolationError(f"plan rejected: possible prompt injection ({len(inj)} markers)")
        return plan, {
            "provider": resp.provider_id,
            "model": resp.model,
            "usage": resp.usage.model_dump(),
            "cost": resp.cost.amount_usd,
            "cost_estimated": resp.cost.estimated,
            "fallback_count": resp.route_metadata.get("fallback_count", 0),
        }

    async def _repair(self, model_req: ModelRequest, invalid_content: str) -> str:
        repair_msgs = list(model_req.messages) + [
            {"role": "user", "content": "Your previous response did not validate against AgentPlan v1. "
                                        "Return only a corrected JSON object. Do not change user intent or expand ranges/tools."}
        ]
        from ..domain.provider_models import ModelRequest as MR

        mr = MR(request_id=new_id("req"), messages=repair_msgs,
                 response_schema=model_req.response_schema, temperature=0.0,
                 max_output_tokens=model_req.max_output_tokens, timeout_ms=model_req.timeout_ms,
                 metadata=model_req.metadata, tool_policy=model_req.tool_policy)
        resp = await self.router.route(mr, None)
        return resp.content
