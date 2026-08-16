"""SQLite-backed repositories matching the in-memory store interface."""
from __future__ import annotations

import json

from ..domain.provider_models import AgentPlan
from ..domain.types import RunStatus
from ..persistence.db import connection
from ..runs.service import Run, RunStore


class SqliteRunStore(RunStore):
    """Persistence for runs; survives restart (Phase 3 exit criterion).

    The structured plan (no raw context) is kept in an in-process overlay so
    the approve/result flow can read action targets without re-persisting the
    full plan. Status + audit metadata are durable in SQLite.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._plan_cache: dict[str, AgentPlan] = {}

    def create(self, parent_run_id: str | None = None) -> Run:
        from ..core.ids import new_id

        run = Run(run_id=new_id("run"), parent_run_id=parent_run_id)
        with connection(self._db_path) as conn:
            conn.execute(
                "INSERT INTO runs (run_id, parent_run_id, status, created_at) VALUES (?,?,?,?)",
                (run.run_id, parent_run_id, run.status.value, run.created_at),
            )
            conn.commit()
        return run

    def get(self, run_id: str) -> Run:
        with connection(self._db_path) as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if not row:
                raise KeyError(run_id)
            run = self._row_to_run(row)
        if run.run_id in self._plan_cache:
            run.plan = self._plan_cache[run.run_id]
        return run

    def update(self, run: Run) -> None:
        if run.plan is not None:
            self._plan_cache[run.run_id] = run.plan
        with connection(self._db_path) as conn:
            conn.execute(
                """UPDATE runs SET status=?, plan_hash=?, workbook_hash=?, route_provider=?,
                   route_model=?, usage_input_tokens=?, usage_output_tokens=?, usage_cost_usd=?,
                   preview_expires_at=?, approved_at=?, applied_at=?, apply_attempt_id=?,
                   action_targets=?, last_result_status=?, supersedes_run_id=?
                   WHERE run_id=?""",
                (
                    run.status.value, run.plan_hash, run.route.get("workbook_hash"),
                    run.route.get("provider"), run.route.get("model"),
                    run.usage.get("input_tokens"), run.usage.get("output_tokens"),
                    run.usage.get("cost_usd"), run.preview_expires_at, run.approved_at,
                    run.applied_at, run.apply_attempt_id,
                    json.dumps(run.action_targets), run.last_result.get("status") if run.last_result else None,
                    run.supersedes_run_id, run.run_id,
                ),
            )
            conn.commit()

    def list(self, limit: int = 20, cursor: str | None = None) -> list[Run]:
        with connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_run(r) for r in rows]

    @staticmethod
    def _row_to_run(row) -> Run:
        run = Run(run_id=row["run_id"], parent_run_id=row["parent_run_id"])
        run.status = RunStatus(row["status"])
        run.plan_hash = row["plan_hash"]
        run.preview_expires_at = row["preview_expires_at"]
        run.route = {
            "provider": row["route_provider"], "model": row["route_model"],
            "workbook_hash": row["workbook_hash"],
        }
        run.usage = {
            "input_tokens": row["usage_input_tokens"],
            "output_tokens": row["usage_output_tokens"],
            "cost_usd": row["usage_cost_usd"],
        }
        run.approved_at = row["approved_at"]
        run.applied_at = row["applied_at"]
        run.apply_attempt_id = row["apply_attempt_id"]
        run.action_targets = json.loads(row["action_targets"] or "[]")
        run.supersedes_run_id = row["supersedes_run_id"]
        run.created_at = row["created_at"]
        return run
