"""Phase 2 types: action bundle, approval token, apply/undo results."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..core.ids import sign_value, utc_now
from ..domain.provider_models import Action


class ActionBundle(BaseModel):
    """Approved, expiring executable representation of a plan (ARCHITECTURE §3)."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    plan_hash: str
    actions: list[Action] = Field(default_factory=list, max_items=100)


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_hash: str
    current_fingerprints: list[dict[str, Any]] = Field(default_factory=list)
    confirmation: dict[str, Any] = Field(default_factory=dict)


class ApprovalResponse(BaseModel):
    run_id: str
    apply_attempt_id: str
    approval_token: str
    expires_at: str
    action_bundle: ActionBundle


class ApplyResultStatus(str):
    APPLIED = "APPLIED"
    FAILED_ROLLED_BACK = "FAILED_ROLLED_BACK"
    FAILED_PARTIAL = "FAILED_PARTIAL"
    STALE_CONTEXT = "STALE_CONTEXT"
    CANCELLED = "CANCELLED"


class ApplyResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    apply_attempt_id: str
    approval_token: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    action_results: list[dict[str, Any]] = Field(default_factory=list)
    before_snapshot: dict[str, Any] | None = None
    after_snapshot: dict[str, Any] | None = None
    error: str | None = None


def build_approval_token(run_id: str, plan_hash: str, workbook_hash: str,
                          action_targets: list[str], secret: str, ttl_seconds: int) -> tuple[str, str]:
    """Opaque signed token bound to run/plan/workbook/targets/expiry (SECURITY §4)."""
    expires_at = (utc_now() + timedelta(seconds=ttl_seconds)).isoformat()
    payload = f"{run_id}|{plan_hash}|{workbook_hash}|{','.join(sorted(action_targets))}|{expires_at}"
    sig = sign_value(payload, secret)
    # separator '|' to avoid ambiguity with timestamps containing '.'
    token = f"{sig}|{expires_at}"
    return token, expires_at


def verify_approval_token(token: str, run_id: str, plan_hash: str, workbook_hash: str,
                           action_targets: list[str], secret: str) -> bool:
    if "|" not in token:
        return False
    sig, expires_at = token.rsplit("|", 1)
    # expired?
    try:
        exp = datetime.fromisoformat(expires_at)
    except ValueError:
        return False
    if exp < utc_now():
        return False
    payload = f"{run_id}|{plan_hash}|{workbook_hash}|{','.join(sorted(action_targets))}|{expires_at}"
    expected = sign_value(payload, secret)
    return expected == sig


class PrepareUndoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    before_snapshot: dict[str, Any]  # client-held snapshot taken BEFORE apply
    approval_token: str | None = None  # ignored on prepare; issued by server in response


class UndoResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    undo_attempt_id: str
    approval_token: str
    status: str  # RESTORED | FAILED
    error: str | None = None
