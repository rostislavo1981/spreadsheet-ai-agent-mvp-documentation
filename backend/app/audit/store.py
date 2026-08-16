"""Audit store interface + in-memory implementation (Phase 1).

Stores sanitized run metadata only (no raw contexts/prompts/snapshots).
Phase 3 persists via SQLite behind the same interface (SECURITY §10, ARCHITECTURE §2).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.ids import new_id, utc_now
from ..domain.types import RunStatus


@dataclass
class AuditEntry:
    entry_id: str
    run_id: str
    subject_hash: str
    workbook_hash: str
    status: RunStatus
    route_provider: str | None
    route_model: str | None
    plan_hash: str | None
    warnings: list[str]
    affected_cells: int | None
    created_at: str = field(default_factory=lambda: utc_now().isoformat())


class AuditStore:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, *, run_id: str, subject_hash: str, workbook_hash: str,
               status: RunStatus, route_provider: str | None, route_model: str | None,
               plan_hash: str | None, warnings: list[str], affected_cells: int | None) -> AuditEntry:
        entry = AuditEntry(
            entry_id=new_id("aud"),
            run_id=run_id,
            subject_hash=subject_hash,
            workbook_hash=workbook_hash,
            status=status,
            route_provider=route_provider,
            route_model=route_model,
            plan_hash=plan_hash,
            warnings=warnings,
            affected_cells=affected_cells,
        )
        self._entries.append(entry)
        return entry

    def list(self, workbook_hash: str | None = None, limit: int = 20) -> list[AuditEntry]:
        out = self._entries
        if workbook_hash:
            out = [e for e in out if e.workbook_hash == workbook_hash]
        return out[-limit:][::-1]
