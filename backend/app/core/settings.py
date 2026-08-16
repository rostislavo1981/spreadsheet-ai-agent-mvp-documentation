"""Settings loaded from environment with startup validation.

Mirrors `.env.example` groups. Code validates on startup and rejects unsafe
combinations (ENVIRONMENT.md / SECURITY_GUARDRAILS.md).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import PositiveInt, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # Runtime
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_log_level: str = "INFO"
    app_database_url: str = "sqlite:///./spreadsheet_agent.db"
    app_signing_secret: str = "replace-with-random-secret"
    app_id_hash_salt: str = "replace-with-different-random-salt"
    app_client_token_hashes: str = ""
    sqlite_db_path: str | None = None  # None -> default data/agent.sqlite3

    # Limits
    max_request_bytes: PositiveInt = 4_194_304
    max_selected_cells: PositiveInt = 10_000
    max_context_cells: PositiveInt = 10_000
    max_actions: PositiveInt = 100
    max_changed_cells: PositiveInt = 10_000
    max_input_tokens: PositiveInt = 50_000
    max_output_tokens: PositiveInt = 8_000
    max_provider_attempts: PositiveInt = 3
    provider_timeout_seconds: PositiveInt = 45
    preview_ttl_seconds: PositiveInt = 600
    approval_ttl_seconds: PositiveInt = 120
    max_run_cost_usd: float = 0.10
    daily_user_cost_usd: float = 2.00
    audit_retention_days: PositiveInt = 30
    snapshot_retention_days: PositiveInt = 7

    # Routing
    enabled_provider_targets: str = "fake"
    default_routing_profile: str = "auto"
    allow_unknown_provider_cost: bool = False

    # Fake provider
    fake_provider_enabled: bool = True
    fake_provider_fixture: str = "tests/fixtures/provider/read_only.json"

    # OpenAI-compatible
    openai_compatible_enabled: bool = False
    openai_compatible_provider_id: str = "compatible"
    openai_compatible_base_url: str = "http://127.0.0.1:11434/v1"
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = ""
    openai_compatible_extra_headers_json: str = "{}"

    # Hermes
    hermes_enabled: bool = False
    hermes_mode: str = "openai_compatible"
    hermes_base_url: str = "http://127.0.0.1:4012/v1"
    hermes_api_key: str = ""
    hermes_model: str = "spreadsheet-planner"
    hermes_profile: str = "spreadsheet-planner"
    hermes_tool_policy: str = "planner_only"
    hermes_session_mode: str = "ephemeral"
    hermes_timeout_seconds: PositiveInt = 45

    # Observability (raw logging must stay false in normal use)
    otel_exporter_otlp_endpoint: str = ""
    log_prompts: bool = False
    log_spreadsheet_context: bool = False
    log_snapshots: bool = False
    rate_limit_per_minute: int = 30
    rate_limit_burst: int = 10

    @field_validator("enabled_provider_targets")
    @classmethod
    def split_targets(cls, v: str) -> list[str]:
        return [t.strip() for t in v.split(",") if t.strip()]

    @field_validator("app_signing_secret", "app_id_hash_salt")
    @classmethod
    def strong_secret(cls, v: str, info: ValidationInfo) -> str:
        if info.data.get("app_env") == "production" and (
            not v or v.startswith("replace-with") or len(v) < 16
        ):
            raise ValueError(
                f"{info.field_name} must be a strong random value in production"
            )
        return v

    @field_validator("hermes_base_url", "openai_compatible_base_url")
    @classmethod
    def https_unless_loopback(cls, v: str, info: ValidationInfo) -> str:
        env = info.data.get("app_env", "development")
        if env != "development" and v.startswith("http://") and "127.0.0.1" not in v:
            raise ValueError("Provider/Hermes base URLs require HTTPS except loopback dev")
        return v

    @field_validator("hermes_tool_policy")
    @classmethod
    def hermes_p0_policy(cls, v: str, info: ValidationInfo) -> str:
        if info.data.get("app_env") == "production" and v != "planner_only":
            raise ValueError("HERMES_TOOL_POLICY must be planner_only in P0 production")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings() -> None:
    get_settings.cache_clear()
