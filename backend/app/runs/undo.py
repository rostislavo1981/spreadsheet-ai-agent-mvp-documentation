"""Undo service (Phase 3): snapshot-derived, client-held undo bundles.

Server stores only a reference id + availability flag; the actual snapshot
payload (cell matrix) lives encrypted in client app storage and is supplied
back by the client on undo. This enforces: undo is never model-generated,
undo requires the same approval token, undo is stale-checked against live
fingerprints (ARCHITECTURE.md §3, SECURITY §6).
"""
from __future__ import annotations

from ..core.ids import utc_now
from ..persistence.db import connection


class UndoService:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path

    def mark_available(self, run_id: str, snapshot_ref: str) -> None:
        with connection(self._db_path) as conn:
            conn.execute(
                """INSERT INTO undo_state (run_id, available, snapshot_ref, created_at)
                   VALUES (?,1,?,?) ON CONFLICT(run_id) DO UPDATE SET
                   available=1, snapshot_ref=excluded.snapshot_ref, created_at=excluded.created_at""",
                (run_id, snapshot_ref, utc_now().isoformat()),
            )
            conn.commit()

    def is_available(self, run_id: str) -> bool:
        with connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT available FROM undo_state WHERE run_id=?", (run_id,)
            ).fetchone()
        return bool(row and row["available"])

    def consume(self, run_id: str) -> None:
        with connection(self._db_path) as conn:
            conn.execute("UPDATE undo_state SET available=0 WHERE run_id=?", (run_id,))
            conn.commit()
