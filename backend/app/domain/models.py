"""Wire models for the spreadsheet context and plan request/response.

These mirror schemas/*.json. Domain imports only pydantic — no FastAPI/persistence.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ClientType(str, Enum):
    google_sheets = "google_sheets"
    excel = "excel"
    test = "test"


class DataClass(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class ContextScope(str, Enum):
    selection = "selection"
    selection_with_neighbors = "selection_with_neighbors"
    approved_custom_ranges = "approved_custom_ranges"


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheet_id: int
    sheet_name: str = Field(min_length=1, max_length=100)
    a1_range: str = Field(min_length=1, max_length=200)


JSONCell = Any


class RangeContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheet_id: int
    sheet_name: str
    a1_range: str
    start_row: int = Field(ge=1)
    start_column: int = Field(ge=1)
    row_count: int = Field(ge=1, le=10000)
    column_count: int = Field(ge=1, le=1000)
    values: list[list[JSONCell]]
    display_values: list[list[str]] = Field(default_factory=list)
    formulas: list[list[str]] = Field(default_factory=list)
    number_formats: list[list[str]] | None = None
    merged_intersections: list[str] = Field(default_factory=list)
    protected_intersections: list[str] = Field(default_factory=list)
    fingerprint: str = Field(min_length=16, max_length=200)


class Omission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(max_length=200)
    original_range: str | None = None
    detail: str | None = None


class ContextPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ranges: list[RangeContext] = Field(min_length=1, max_length=100)
    omissions: list[Omission] = Field(default_factory=list)


class Workbook(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workbook_id_hash: str = Field(min_length=16, max_length=200)
    title: str | None = None
    locale: str = Field(max_length=30)
    timezone: str = Field(max_length=100)


class ClientInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: ClientType
    version: str = Field(max_length=50)
    tool_versions: dict[str, str] = Field(default_factory=dict, max_length=100)


class ConversationTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(max_length=20000)


class PlanOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: str = Field(min_length=1, max_length=100)
    data_class: DataClass
    max_cost_usd: float | None = Field(default=None, ge=0)
    context_scope: ContextScope
    model: str | None = Field(default=None, max_length=200)
    client_run_token: str | None = Field(default=None, max_length=100)


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    parent_run_id: str | None = Field(default=None, max_length=100)
    parent_run_id_set: bool = Field(default=False, exclude=True)
    client: ClientInfo
    workbook: Workbook
    selection: Target
    context: ContextPayload
    prompt: str = Field(min_length=1, max_length=20000)
    conversation: list[ConversationTurn] = Field(default_factory=list, max_length=12)
    options: PlanOptions

    def model_post_init(self, _ctx: Any) -> None:
        self.parent_run_id_set = self.parent_run_id is not None
