"""SQLite persistence layer (Phase 3). Replaces in-memory stores behind the
same interface used by services (ARCHITECTURE.md §2).

Sanitization: only metadata is persisted (run_id, status, hashes, sanitized
fingerprints, affected cell counts). Raw contexts, prompts, and cell snapshot
payloads are NEVER written here (SECURITY_GUARDRAILS.md §11). Snapshot-derived
undo bundles are persisted only in encrypted-at-rest app storage on the client;
the server keeps only a boolean `undo_available` + snapshot reference id.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = str(Path(__file__).resolve().parents[2] / "data" / "agent.sqlite3")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            parent_run_id TEXT,
            status TEXT NOT NULL,
            plan_hash TEXT,
            workbook_hash TEXT,
            route_provider TEXT,
            route_model TEXT,
            usage_input_tokens INTEGER,
            usage_output_tokens INTEGER,
            usage_cost_usd REAL,
            preview_expires_at TEXT,
            approved_at TEXT,
            applied_at TEXT,
            apply_attempt_id TEXT,
            action_targets TEXT,
            last_result_status TEXT,
            created_at TEXT NOT NULL,
            supersedes_run_id TEXT
        );
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            subject_hash TEXT,
            workbook_hash TEXT,
            status TEXT,
            route_provider TEXT,
            route_model TEXT,
            plan_hash TEXT,
            affected_cells INTEGER DEFAULT 0,
            warnings TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS undo_state (
            run_id TEXT PRIMARY KEY,
            available INTEGER NOT NULL DEFAULT 0,
            snapshot_ref TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


@contextmanager
def connection(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()
