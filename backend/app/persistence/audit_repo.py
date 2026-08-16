"""SQLite-backed audit store (sanitized metadata only)."""
from __future__ import annotations

import json

from ..audit.store import AuditEntry, AuditStore
from ..domain.types import RunStatus
from ..persistence.db import connection


class SqliteAuditStore(AuditStore):
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path

    def record(
        self,
        run_id: str,
        subject_hash: str,
        workbook_hash: str,
        status: object,
        route_provider: str | None = None,
        route_model: str | None = None,
        plan_hash: str | None = None,
        warnings: list[str] | None = None,
        affected_cells: int = 0,
    ) -> AuditEntry:
        from ..core.ids import new_id, utc_now

        entry = AuditEntry(
            entry_id=new_id("aud"),
            run_id=run_id, subject_hash=subject_hash, workbook_hash=workbook_hash,
            status=RunStatus(str(getattr(status, "value", status))),
            route_provider=route_provider, route_model=route_model,
            plan_hash=plan_hash, warnings=warnings or [],
            affected_cells=affected_cells or 0,
            created_at=utc_now().isoformat(),
        )
        with connection(self._db_path) as conn:
            conn.execute(
                """INSERT INTO audit (run_id, subject_hash, workbook_hash, status,
                   route_provider, route_model, plan_hash, affected_cells, warnings, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    entry.run_id, entry.subject_hash, entry.workbook_hash, entry.status,
                    entry.route_provider, entry.route_model, entry.plan_hash,
                    entry.affected_cells, json.dumps(entry.warnings), entry.created_at,
                ),
            )
            conn.commit()
        return entry

    def list(self, limit: int = 50, subject_hash: str | None = None) -> list[AuditEntry]:
        with connection(self._db_path) as conn:
            if subject_hash:
                rows = conn.execute(
                    "SELECT * FROM audit WHERE subject_hash=? ORDER BY created_at DESC LIMIT ?",
                    (subject_hash, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM audit ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        out = []
        for r in rows:
            out.append(AuditEntry(
                entry_id=f"aud_{r['id']}",
                run_id=r["run_id"], subject_hash=r["subject_hash"], workbook_hash=r["workbook_hash"],
                status=RunStatus(r["status"]), route_provider=r["route_provider"], route_model=r["route_model"],
                plan_hash=r["plan_hash"], warnings=json.loads(r["warnings"] or "[]"),
                affected_cells=r["affected_cells"], created_at=r["created_at"],
            ))
        return out

