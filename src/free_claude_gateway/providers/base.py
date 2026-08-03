from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from free_claude_gateway.core.models import AnthropicRequest


class BaseProvider(ABC):
    """Base class for all upstream providers."""

    name: str = "base"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def chat(
        self,
        request: AnthropicRequest,
        model: str,
    ) -> dict[str, Any]:
        """Non-streaming chat completion in Anthropic-like response format."""
        ...

    @abstractmethod
    async def stream(
        self,
        request: AnthropicRequest,
        model: str,
    ) -> AsyncIterator[str]:
        """Yield SSE-formatted chunks compatible with Anthropic streaming."""
        ...

    def is_available(self) -> bool:
        """Return True if the provider has the required credentials / is reachable."""
        return True
