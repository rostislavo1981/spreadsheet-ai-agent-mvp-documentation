"""Client bearer-token authentication middleware (SECURITY_GUARDRAILS.md §6,
PILOT_RUNBOOK.md). Fail-closed: any configured token hash makes every /v1/*
request require a matching Authorization: Bearer header. When no token hash
is configured (dev default), auth is not enforced.
"""
from __future__ import annotations

import hashlib
import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ClientAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, token_hashes_csv: str = "") -> None:
        super().__init__(app)
        self.token_hashes = {h.strip() for h in token_hashes_csv.split(",") if h.strip()}

    def _authenticated(self, request: Request) -> bool:
        if not self.token_hashes:
            return True
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            return False
        token = header.removeprefix("Bearer ").strip()
        if not token:
            return False
        presented_hash = _hash_token(token)
        return any(hmac.compare_digest(presented_hash, known) for known in self.token_hashes)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in ("/health/live", "/health/ready", "/logo.png") or path.startswith("/static/"):
            return await call_next(request)
        if not self._authenticated(request):
            return JSONResponse(
                status_code=401,
                content={
                    "type": "https://spreadsheet-agent.local/problems/unauthenticated",
                    "title": "AuthenticationError", "status": 401, "code": "UNAUTHENTICATED",
                    "detail": "missing or invalid client token", "retryable": False, "field_errors": [],
                },
            )
        return await call_next(request)
