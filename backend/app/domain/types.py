"""Core domain types and settings for the Spreadsheet AI Agent backend.

Domain code must not import FastAPI, vendor SDKs, persistence, or Apps Script.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, NewType

# Opaque identifier aliases (strings at runtime).
RunId = NewType("RunId", str)
PlanHash = NewType("PlanHash", str)



class RunStatus(str, Enum):
    """Server-validated run lifecycle states (ARCHITECTURE.md §4)."""

    CREATED = "CREATED"
    PLANNING = "PLANNING"
    PREVIEW_READY = "PREVIEW_READY"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    APPROVED = "APPROVED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    UNDO_READY = "UNDO_READY"
    UNDOING = "UNDOING"
    UNDONE = "UNDONE"
    UNDO_CONFLICT = "UNDO_CONFLICT"
    UNDO_FAILED = "UNDO_FAILED"


class ActionType(str, Enum):
    SET_VALUES = "SET_VALUES"
    SET_FORMULAS = "SET_FORMULAS"
    CLEAR_RANGE = "CLEAR_RANGE"
    FORMAT_RANGE = "FORMAT_RANGE"
    ADD_SHEET = "ADD_SHEET"
    NO_OP = "NO_OP"


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DataClass(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class ProfileId(str, Enum):
    """User-facing routing profiles (PROVIDER_ADAPTERS.md §7)."""

    AUTO = "auto"
    FAST = "fast"
    QUALITY = "quality"
    CHEAP = "cheap"
    PRIVATE = "private"
    HERMES = "hermes"


class PlanResponseStatus(str, Enum):
    PREVIEW_READY = "PREVIEW_READY"
    CONTEXT_REQUIRED = "CONTEXT_REQUIRED"
    REJECTED = "REJECTED"


# Reusable JSON-cell type (plan-request schema $defs.json_cell).
JSONCell = Any
