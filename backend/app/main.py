"""FastAPI application wiring + dependency injection of services."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .api import capabilities, routes
from .core.errors import SpreadsheetAgentError
from .core.settings import Settings, get_settings
from .providers.registry import ProviderRegistry
from .providers.router import ModelRouter

logging.basicConfig(level=logging.INFO)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Spreadsheet AI Agent", version="0.1.0-pilot")

    registry = ProviderRegistry(settings)
    router = ModelRouter(registry, settings)

    from .api.auth import ClientAuthMiddleware
    from .api.ratelimit import RateLimitMiddleware
    from .audit.store import AuditStore
    from .persistence.audit_repo import SqliteAuditStore
    from .persistence.runs_repo import SqliteRunStore
    from .runs.service import RunStore
    from .runs.undo import UndoService

    # Phase 3: SQLite-backed persistence (survives restart).
    db_path = settings.sqlite_db_path
    runs_store: RunStore = SqliteRunStore(db_path)
    audit_store: AuditStore = SqliteAuditStore(db_path)
    undo_service = UndoService(db_path)

    state = {
        "settings": settings,
        "registry": registry,
        "router": router,
        "runs": runs_store,
        "audit": audit_store,
        "undo": undo_service,
    }
    app.state.services = state

    app.include_router(routes.router)
    app.include_router(capabilities.router)
    app.add_middleware(RateLimitMiddleware, per_minute=settings.rate_limit_per_minute, burst=settings.rate_limit_burst)
    app.add_middleware(ClientAuthMiddleware, token_hashes_csv=settings.app_client_token_hashes)

    @app.exception_handler(SpreadsheetAgentError)
    async def handle_domain_error(request, exc: SpreadsheetAgentError):
        problem = exc.to_problem()
        problem["request_id"] = problem.get("request_id") or request.headers.get("x-request-id")
        return JSONResponse(status_code=exc.status, content=problem)

    from pydantic import ValidationError as PydanticValidationError

    @app.exception_handler(PydanticValidationError)
    async def handle_validation_error(request, exc: PydanticValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "type": "https://spreadsheet-agent.local/problems/invalid-request",
                "title": "ValidationError",
                "status": 422,
                "code": "INVALID_REQUEST",
                "detail": "request body failed validation",
                "request_id": request.headers.get("x-request-id"),
                "retryable": False,
                "field_errors": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()],
            },
        )

    @app.get("/health/live")
    async def health_live():
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready():
        return {"status": "ok", "providers": registry.targets()}

    return app
