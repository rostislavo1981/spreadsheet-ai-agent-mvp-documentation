"""Provider adapter base protocol + shared helpers (PROVIDER_ADAPTERS.md §2)."""
from __future__ import annotations

import abc
from collections.abc import AsyncIterator

from ..domain.provider_models import (
    ModelDescriptor,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
)


class ProviderAdapter(abc.ABC):
    """Core depends only on this interface, never on vendor SDK classes."""

    @property
    @abc.abstractmethod
    def provider_id(self) -> str: ...

    @abc.abstractmethod
    async def capabilities(self) -> ProviderCapabilities: ...

    @abc.abstractmethod
    async def list_models(self) -> list[ModelDescriptor]: ...

    @abc.abstractmethod
    async def health(self) -> ProviderCapabilities: ...

    @abc.abstractmethod
    async def complete(self, request: ModelRequest) -> ModelResponse: ...

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelResponse]:
        raise NotImplementedError("streaming not supported in P0")

    @abc.abstractmethod
    def estimate_cost(self, request: ModelRequest): ...
