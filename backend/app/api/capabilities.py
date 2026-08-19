"""Public capabilities: schema/tool versions, profiles, limits, features.

Never returns keys, internal URLs, or hidden model configuration (API_CONTRACTS §3).
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..core.settings import Settings, get_settings
from ..tools.registry import P0_TOOL_VERSIONS

router = APIRouter(prefix="/v1", tags=["capabilities"])


def build_capabilities(settings: Settings | None = None, hermes_models: list[dict] | None = None) -> dict:
    settings = settings or get_settings()
    tools = [{"type": t, "version": v} for t, v in P0_TOOL_VERSIONS.items()]
    profiles = [
        {"id": "auto", "label": "Auto", "data_classes": ["public", "internal"]},
        {"id": "hermes", "label": "Hermes", "data_classes": ["public", "internal"]},
    ]
    return {
        "api_version": "1.0",
        "action_schema_versions": ["1.0"],
        "profiles": profiles,
        "tools": tools,
        "hermes_models": hermes_models or [],
        "limits": {
            "max_selected_cells": settings.max_selected_cells,
            "max_actions": settings.max_actions,
            "max_changed_cells": settings.max_changed_cells,
        },
        "features": {"streaming": False, "context_expansion": True},
    }


@router.get("/capabilities")
async def get_capabilities(request: Request):
    svc = request.app.state.services
    settings = svc["settings"]
    hermes_models: list[dict] = []
    if settings.hermes_enabled:
        registry = svc["registry"]
        adapter = registry.get("hermes")
        models = await adapter.list_models()
        hermes_models = [{"id": m.id} for m in models]
    return build_capabilities(settings, hermes_models)
