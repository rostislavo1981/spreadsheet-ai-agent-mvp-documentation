"""AgentPlan wire model + provider request/response normalized contracts."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Risk(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ActionType(str, Enum):
    SET_VALUES = "SET_VALUES"
    SET_FORMULAS = "SET_FORMULAS"
    CLEAR_RANGE = "CLEAR_RANGE"
    FORMAT_RANGE = "FORMAT_RANGE"
    ADD_SHEET = "ADD_SHEET"
    NO_OP = "NO_OP"


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheet_id: int
    sheet_name: str
    a1_range: str


class SetValuesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: list[list[Any]] = Field(min_items=1)
    overwrite_formulas: bool = False


class SetFormulasArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    formulas: list[list[str]] = Field(min_items=1)
    notation: Literal["A1"] = "A1"
    fill_mode: Literal["exact"] | None = None


class ClearRangeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contents: Literal[True] = True


class FormatRangeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", min_properties=1)
    background: str | None = None
    font_color: str | None = None
    font_weight: Literal["normal", "bold"] | None = None
    number_format: str | None = None
    horizontal_alignment: Literal["left", "center", "right"] | None = None
    wrap: bool | None = None


class AddSheetArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=100)
    rows: int | None = Field(default=None, ge=1, le=10000)
    columns: int | None = Field(default=None, ge=1, le=1000)


class NoOpArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Action(BaseModel):
    """Discriminated by `type`; oneOf in schema maps to explicit variants here."""

    model_config = ConfigDict(extra="forbid")
    action_id: str = Field(pattern=r"^act_[A-Za-z0-9_-]+$")
    tool_version: Literal["1.0"] = "1.0"
    type: ActionType
    target: Target | None = None
    arguments: Any
    rationale: str = Field(min_length=1, max_length=2000)
    risk: Risk
    expected_target_fingerprint: str | None = Field(default=None, max_length=200)


class AgentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    summary: str = Field(max_length=2000)
    answer: str = Field(max_length=20000)
    actions: list[Action] = Field(default_factory=list, max_items=100)
    warnings: list[str] = Field(default_factory=list, max_items=50)
    assumptions: list[str] = Field(default_factory=list, max_items=50)
    context_used: list[str] = Field(default_factory=list, max_items=100)
    requires_confirmation: bool


# --- Provider normalized contracts (PROVIDER_ADAPTERS.md §3-4) ---


class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    task: str = "spreadsheet_plan"
    messages: list[dict[str, str]]
    response_schema: dict[str, Any]
    temperature: float = 0.1
    max_output_tokens: int = 2000
    timeout_ms: int = 45_000
    metadata: dict[str, Any] = Field(default_factory=dict)
    tool_policy: dict[str, Any] = Field(default_factory=lambda: {"mode": "none", "allowed_tools": []})


class Usage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None


class Cost(BaseModel):
    amount_usd: float | None = None
    estimated: bool = False


class ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_id: str
    model: str | None = None
    content: str = ""
    structured: dict[str, Any] = Field(default_factory=dict)
    finish_reason: str | None = None
    usage: Usage = Field(default_factory=Usage)
    cost: Cost = Field(default_factory=Cost)
    latency_ms: int | None = None
    provider_request_id: str | None = None
    route_metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderCapabilities(BaseModel):
    provider_id: str
    structured_output: bool = True
    streaming: bool = False
    tool_calling: bool = False
    max_context_tokens: int = 128_000
    max_output_tokens: int = 8_000
    local_execution: bool = False
    health: str = "ok"


class ModelDescriptor(BaseModel):
    id: str
    profiles: list[str] = Field(default_factory=list)
    context_window: int | None = None


class CostEstimate(BaseModel):
    amount_usd: float | None = None
    estimated_cost_usd: float | None = None
