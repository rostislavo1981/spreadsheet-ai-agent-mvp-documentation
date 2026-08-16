"""Typed, redacted errors mapped to RFC7807 problem+json.

Errors never expose stack traces, raw provider bodies, prompts, or credentials
(API_CONTRACTS.md §1, SECURITY_GUARDRAILS.md §11).
"""
from __future__ import annotations

from typing import Any


class SpreadsheetAgentError(Exception):
    """Base for all domain errors with a stable `code` and HTTP `status`."""

    code: str = "INTERNAL_ERROR"
    status: int = 500
    retryable: bool = False
    type_uri: str = "https://spreadsheet-agent.local/problems/internal-error"

    def __init__(self, detail: str, *, request_id: str | None = None, field_errors: list[Any] | None = None):
        super().__init__(detail)
        self.detail = detail
        self.request_id = request_id
        self.field_errors = field_errors or []

    def to_problem(self) -> dict[str, Any]:
        return {
            "type": self.type_uri,
            "title": self.__class__.__name__,
            "status": self.status,
            "code": self.code,
            "detail": self.detail,
            "request_id": self.request_id,
            "retryable": self.retryable,
            "field_errors": self.field_errors,
        }


class HardLimitError(SpreadsheetAgentError):
    code = "HARD_LIMIT_EXCEEDED"
    status = 413
    type_uri = "https://spreadsheet-agent.local/problems/hard-limit"


class SchemaValidationError(SpreadsheetAgentError):
    code = "INVALID_PLAN"
    status = 422
    type_uri = "https://spreadsheet-agent.local/problems/invalid-plan"


class PolicyViolationError(SpreadsheetAgentError):
    code = "POLICY_VIOLATION"
    status = 422
    type_uri = "https://spreadsheet-agent.local/problems/policy-violation"


class StaleContextError(SpreadsheetAgentError):
    code = "STALE_CONTEXT"
    status = 409
    retryable = True
    type_uri = "https://spreadsheet-agent.local/problems/stale-context"


class ContextRequiredError(SpreadsheetAgentError):
    """Raised when planning needs a range outside submitted scope."""

    code = "CONTEXT_REQUIRED"
    status = 200  # business status CONTEXT_REQUIRED, not an HTTP error
    type_uri = "https://spreadsheet-agent.local/problems/context-required"


class ProviderError(SpreadsheetAgentError):
    code = "PROVIDER_ERROR"

    def __init__(self, detail: str, *, provider_id: str | None = None, retryable: bool = False,
                 status_code: int | None = None, request_id: str | None = None):
        super().__init__(detail, request_id=request_id)
        self.provider_id = provider_id
        self.retryable = retryable
        self.status_code = status_code


class ProvidersExhaustedError(SpreadsheetAgentError):
    code = "PROVIDERS_EXHAUSTED"
    status = 502
    type_uri = "https://spreadsheet-agent.local/problems/providers-exhausted"


class AuthenticationError(SpreadsheetAgentError):
    code = "UNAUTHENTICATED"
    status = 401
    type_uri = "https://spreadsheet-agent.local/problems/unauthenticated"
