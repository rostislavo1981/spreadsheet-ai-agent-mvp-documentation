"""Run service: lifecycle state machine + in-memory store (Phase 1/2).

Phase 3 swaps to SQLite repositories behind the same interface (ARCHITECTURE §2).
Transitions are server-validated and idempotent (ARCHITECTURE §4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.ids import new_id, utc_now
from ..domain.provider_models import AgentPlan
from ..domain.types import RunStatus


@dataclass
class Run:
    run_id: str
    status: RunStatus = RunStatus.CREATED
    plan: AgentPlan | None = None
    plan_hash: str | None = None
    preview_expires_at: str | None = None
    route: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    context_requests: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: utc_now().isoformat())
    supersedes_run_id: str | None = None
    parent_run_id: str | None = None
    # Phase 2 additions
    approved_at: str | None = None
    apply_attempt_id: str | None = None
    approval_token: str | None = None
    action_targets: list[str] = field(default_factory=list)
    applied_at: str | None = None
    last_result: dict[str, Any] | None = None

    def transition(self, to: RunStatus) -> None:
        # Idempotent: cannot return to an earlier state.
        order = list(RunStatus)
        if order.index(to) < order.index(self.status):
            raise ValueError(f"cannot transition {self.status} -> {to}")
        self.status = to


class RunStore:
    """In-memory run repository (Phase 1). Replaceable by SQLite in Phase 3."""

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}

    def create(self, parent_run_id: str | None = None) -> Run:
        run = Run(run_id=new_id("run"), parent_run_id=parent_run_id)
        self._runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> Run:
        if run_id not in self._runs:
            raise KeyError(run_id)
        return self._runs[run_id]

    def list(self, limit: int = 20, cursor: str | None = None) -> list[Run]:
        runs = list(self._runs.values())
        runs.sort(key=lambda r: r.created_at, reverse=True)
        if cursor:
            runs = [r for r in runs if r.run_id != cursor]
        return runs[:limit]
