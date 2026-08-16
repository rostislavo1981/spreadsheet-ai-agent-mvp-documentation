"""API router for plan/approve/result endpoints (Phase 1 + Phase 2)."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..core.errors import ContextRequiredError, SpreadsheetAgentError
from ..core.ids import hash_identifier, utc_now
from ..domain.models import PlanRequest
from ..domain.types import RunStatus
from ..planning.planner import Planner, plan_hash
from ..tools.registry import plan_changed_cells
from .contracts import (
    ActionBundle,
    ApplyResultRequest,
    ApprovalRequest,
    PrepareUndoRequest,
    UndoResultRequest,
    build_approval_token,
    verify_approval_token,
)

router = APIRouter(prefix="/v1")


def _risk_of(plan) -> str:
    if not plan or not plan.actions:
        return "none"
    if any(a.risk == "high" for a in plan.actions):
        return "high"
    if any(a.risk == "medium" for a in plan.actions):
        return "medium"
    return "low"


def _build_response(req: PlanRequest | None, plan, route: dict, run, status: str, expires_at=None):
    changed = plan_changed_cells(plan.actions) if plan else 0
    return {
        "run_id": run.run_id,
        "status": status,
        "assistant_message": (plan.answer or plan.summary) if plan else "",
        "plan": plan.model_dump(mode="json") if plan else None,
        "preview": {
            "plan_hash": plan_hash(plan) if plan else None,
            "changed_cells": changed,
            "risk": _risk_of(plan),
            "expires_at": expires_at,
        } if plan and status == "PREVIEW_READY" else None,
        "context_requests": [],
        "route": {
            "provider": route.get("provider"),
            "model": route.get("model"),
            "fallback_count": route.get("fallback_count", 0),
        },
        "usage": {
            "input_tokens": route.get("usage", {}).get("input_tokens"),
            "output_tokens": route.get("usage", {}).get("output_tokens"),
            "cost_usd": route.get("cost"),
            "cost_estimated": route.get("cost_estimated", True),
        },
    }


@router.post("/runs:plan")
async def create_plan(request: Request):
    svc = request.app.state.services
    settings = svc["settings"]
    body = await request.body()
    if len(body) > settings.max_request_bytes:
        return JSONResponse(status_code=413, content={
            "type": "https://spreadsheet-agent.local/problems/hard-limit",
            "title": "PayloadTooLarge", "status": 413, "code": "HARD_LIMIT_EXCEEDED",
            "detail": "request exceeds max bytes", "retryable": False, "field_errors": [],
        })

    req = PlanRequest.model_validate_json(body)
    run = svc["runs"].create(parent_run_id=req.parent_run_id)
    run.transition(RunStatus.PLANNING)

    planner = Planner(svc["router"], settings)
    try:
        plan, route = await planner.plan(req)
    except ContextRequiredError:
        run.transition(RunStatus.REJECTED)
        return _build_response(req, None, {"provider": None, "model": None, "fallback_count": 0},
                               run, "CONTEXT_REQUIRED")
    except SpreadsheetAgentError:
        run.transition(RunStatus.REJECTED)
        raise

    phash = plan_hash(plan)
    expires = (utc_now() + timedelta(seconds=settings.preview_ttl_seconds)).isoformat()
    run.plan = plan
    run.plan_hash = phash
    run.preview_expires_at = expires
    run.route = {**route, "workbook_hash": req.workbook.workbook_id_hash}
    run.usage = route.get("usage", {})
    run.transition(RunStatus.PREVIEW_READY)
    svc["runs"].update(run)

    subject_hash = hash_identifier("pilot-user", settings.app_id_hash_salt)
    svc["audit"].record(
        run_id=run.run_id, subject_hash=subject_hash,
        workbook_hash=req.workbook.workbook_id_hash, status=run.status,
        route_provider=route.get("provider"), route_model=route.get("model"),
        plan_hash=phash, warnings=plan.warnings,
        affected_cells=plan_changed_cells(plan.actions),
    )
    return _build_response(req, plan, route, run, "PREVIEW_READY", expires_at=expires)


@router.post("/runs/{run_id}:approve")
async def approve_plan(run_id: str, request: Request):
    svc = request.app.state.services
    settings = svc["settings"]
    try:
        run = svc["runs"].get(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="run not found")

    if run.status != RunStatus.PREVIEW_READY:
        raise HTTPException(status_code=409, detail=f"run status is {run.status}, expected PREVIEW_READY")

    body = await request.body()
    areq = ApprovalRequest.model_validate_json(body)

    # Validate plan hash + expiry + fingerprints coverage.
    if areq.plan_hash != run.plan_hash:
        raise HTTPException(status_code=409, detail="plan hash mismatch")
    # staleness: preview expired?
    if run.preview_expires_at and utc_now().isoformat() > run.preview_expires_at:
        raise HTTPException(status_code=409, detail="preview expired; refresh required")

    targets = []
    for a in (run.plan.actions if run.plan else []):
        if a.target is not None:
            targets.append(f"{a.target.sheet_id}:{a.target.a1_range}")

    token, expires_at = build_approval_token(
        run_id=run.run_id, plan_hash=run.plan_hash,
        workbook_hash=run.route.get("workbook_hash", ""),
        action_targets=targets, secret=settings.app_signing_secret,
        ttl_seconds=settings.approval_ttl_seconds,
    )
    apply_attempt_id = f"apply_{run.run_id}"
    bundle = ActionBundle(plan_hash=run.plan_hash, actions=run.plan.actions if run.plan else [])
    run.approved_at = utc_now().isoformat()
    run.apply_attempt_id = apply_attempt_id
    run.approval_token = token
    run.action_targets = targets
    run.transition(RunStatus.APPROVED)
    svc["runs"].update(run)

    return {
        "run_id": run.run_id,
        "apply_attempt_id": apply_attempt_id,
        "approval_token": token,
        "expires_at": expires_at,
        "action_bundle": bundle.model_dump(mode="json"),
    }


@router.post("/runs/{run_id}:result")
async def report_result(run_id: str, request: Request):
    svc = request.app.state.services
    settings = svc["settings"]
    try:
        run = svc["runs"].get(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="run not found")

    body = await request.body()
    rreq = ApplyResultRequest.model_validate_json(body)

    # Verify token (fail closed).
    if not verify_approval_token(
        rreq.approval_token, run.run_id, run.plan_hash or "",
        run.route.get("workbook_hash", ""), run.action_targets, settings.app_signing_secret,
    ):
        raise HTTPException(status_code=401, detail="invalid or expired approval token")

    if rreq.status == "APPLIED":
        run.transition(RunStatus.APPLIED)
    elif rreq.status in ("FAILED_ROLLED_BACK", "FAILED_PARTIAL") or rreq.status == "STALE_CONTEXT" or rreq.status == "CANCELLED":
        run.transition(RunStatus.FAILED)
    run.applied_at = rreq.finished_at or utc_now().isoformat()
    run.last_result = rreq.model_dump(mode="json")
    svc["runs"].update(run)

    subject_hash = hash_identifier("pilot-user", settings.app_id_hash_salt)
    affected = sum(a.get("affected_cells", 0) for a in rreq.action_results)
    svc["audit"].record(
        run_id=run.run_id, subject_hash=subject_hash,
        workbook_hash=run.route.get("workbook_hash", ""), status=run.status,
        route_provider=run.route.get("provider"), route_model=run.route.get("model"),
        plan_hash=run.plan_hash, warnings=[], affected_cells=affected,
    )
    # On a successful apply, mark undo availability (snapshot held client-side).
    if rreq.status == "APPLIED":
        svc["undo"].mark_available(run.run_id, rreq.after_snapshot.get("ref") if rreq.after_snapshot else run.run_id)
    return {"run_id": run.run_id, "status": run.status.value}


@router.post("/runs/{run_id}:prepare-undo")
async def prepare_undo(run_id: str, request: Request):
    svc = request.app.state.services
    settings = svc["settings"]
    try:
        run = svc["runs"].get(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="run not found")

    body = await request.body()
    ureq = PrepareUndoRequest.model_validate_json(body)
    if not verify_approval_token(
        ureq.approval_token, run.run_id, run.plan_hash or "",
        run.route.get("workbook_hash", ""), run.action_targets, settings.app_signing_secret,
    ):
        raise HTTPException(status_code=401, detail="invalid or expired approval token")

    if not svc["undo"].is_available(run.run_id):
        raise HTTPException(status_code=409, detail="undo not available")

    # Build a snapshot-derived undo bundle (no model involvement).
    bundle = build_undo_bundle(run, ureq.snapshot)
    return {
        "run_id": run.run_id,
        "undo_attempt_id": f"undo_{run.run_id}",
        "undo_bundle": bundle,
        "approver_count_required": 1,
    }


@router.post("/runs/{run_id}:undo-result")
async def undo_result(run_id: str, request: Request):
    svc = request.app.state.services
    settings = svc["settings"]
    try:
        run = svc["runs"].get(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="run not found")

    body = await request.body()
    ures = UndoResultRequest.model_validate_json(body)
    if not verify_approval_token(
        ures.approval_token, run.run_id, run.plan_hash or "",
        run.route.get("workbook_hash", ""), run.action_targets, settings.app_signing_secret,
    ):
        raise HTTPException(status_code=401, detail="invalid or expired approval token")

    svc["undo"].consume(run.run_id)
    return {"run_id": run.run_id, "status": "UNDONE" if ures.status == "RESTORED" else "UNDO_FAILED"}


def build_undo_bundle(run, snapshot: dict) -> dict:
    """Derive undo actions from the before-snapshot (client-supplied)."""
    return {
        "schema_version": "1.0",
        "derived_from": "before_snapshot",
        "actions": [
            {
                "action_id": "undo_001",
                "type": "RESTORE_RANGE",
                "target": r.get("target") or {"sheet_id": r.get("sheet_id"), "a1_range": r.get("a1_range")},
                "arguments": {"values": r.get("values"), "formulas": r.get("formulas")},
                "rationale": "Undo of applied run " + run.run_id,
                "risk": "medium",
            }
            for r in (snapshot.get("ranges") or [])
        ],
    }

