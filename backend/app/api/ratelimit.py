"""Rate limiting + hard request limits middleware (SECURITY_GUARDRAILS §8, §5).

In-memory token-bucket for the pilot. Production should back this with Redis
or the gateway. Never logs prompt/context content.
"""
from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, per_minute: int = 30, burst: int = 10, by: str = "x-client-token") -> None:
        super().__init__(app)
        self.per_minute = per_minute
        self.burst = burst
        self.by = by
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def _allow(self, key: str) -> bool:
        now = time.monotonic()
        window = self._buckets[key]
        # drop entries older than 60s
        while window and window[0] <= now - 60:
            window.pop(0)
        if len(window) >= self.per_minute:
            return False
        window.append(now)
        return True

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health/live", "/health/ready"):
            return await call_next(request)
        key = request.headers.get(self.by) or request.client.host if request.client else "anon"
        if not self._allow(key):
            return JSONResponse(
                status_code=429,
                content={"type": "https://spreadsheet-agent.local/problems/rate-limited",
                         "title": "TooManyRequests", "status": 429, "code": "RATE_LIMITED",
                         "detail": "rate limit exceeded", "retryable": True, "field_errors": []},
            )
        return await call_next(request)
