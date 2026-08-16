"""Core helpers: id generation, hashing, logging, limits enforcement."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from .settings import Settings


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


_ID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford-ish ULID-like


def new_id(prefix: str) -> str:
    """Generate an opaque ULID-like identifier with a semantic prefix."""
    rand = secrets.token_hex(16)
    return f"{prefix}_{rand}"


def sha256_hex(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
    return f"sha256:{h.hexdigest()}"


def hash_identifier(value: str, salt: str) -> str:
    """One-way, salted hash for workbook/user identifiers in audit metadata."""
    return hmac.new(salt.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def sign_value(value: str, secret: str) -> str:
    """Constant-time-safe HMAC signature (used for approval tokens)."""
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


# A1 range parsing: e.g. "D4:I148" -> (start_row, start_col, end_row, end_col).
_COL_RE = re.compile(r"^[A-Za-z]+$")
_COL_TO_NUM = {c: i + 1 for i, c in enumerate(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ")}


def column_to_number(col: str) -> int:
    n = 0
    for ch in col.upper():
        n = n * 26 + _COL_TO_NUM.get(ch, 0)
    return n


def parse_a1(a1: str) -> tuple[int, int, int, int]:
    """Parse an A1 range into (start_row, start_col, end_row, end_col)."""
    if ":" in a1:
        left, right = a1.split(":", 1)
    else:
        left, right = a1, a1
    lm = re.match(r"([A-Za-z]+)(\d+)", left)
    rm = re.match(r"([A-Za-z]+)(\d+)", right)
    if not lm or not rm:
        raise ValueError(f"Invalid A1 range: {a1}")
    sr, sc = int(lm.group(2)), column_to_number(lm.group(1))
    er, ec = int(rm.group(2)), column_to_number(rm.group(1))
    if sr > er or sc > ec:
        sr, er = min(sr, er), max(sr, er)
        sc, ec = min(sc, ec), max(sc, ec)
    return sr, sc, er, ec


def cell_count(a1: str) -> int:
    sr, sc, er, ec = parse_a1(a1)
    return (er - sr + 1) * (ec - sc + 1)


def rect_dimensions(rows: list[list[Any]]) -> tuple[int, int]:
    return len(rows), max((len(r) for r in rows), default=0)


def get_logger(name: str):  # pragma: no cover - thin wrapper
    import logging

    return logging.getLogger(name)


def redact(value: str, limit: int = 64) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "…<redacted>"


def enforce_limits(settings: Settings, *, selected_cells: int, context_cells: int) -> None:
    """Raise a typed error if hard limits are exceeded before any provider call."""
    from .errors import HardLimitError

    if selected_cells > settings.max_selected_cells:
        raise HardLimitError(
            f"selected_cells={selected_cells} exceeds max {settings.max_selected_cells}"
        )
    if context_cells > settings.max_context_cells:
        raise HardLimitError(
            f"context_cells={context_cells} exceeds max {settings.max_context_cells}"
        )


class require_settings:  # context manager / function decorator helper
    def __init__(self, fn: Callable) -> None:
        self.fn = fn

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)
