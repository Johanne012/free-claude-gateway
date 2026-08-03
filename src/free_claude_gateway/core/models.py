from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel


class AnthropicMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Any  # str | list of content blocks


class AnthropicRequest(BaseModel):
    model: str
    messages: list[AnthropicMessage]
    max_tokens: int = 4096
    stream: bool = False
    temperature: Optional[float] = None
    system: Optional[str | list[Any]] = None
    tools: Optional[list[dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    stop_sequences: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    model_config = {"extra": "allow"}


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "free-claude-gateway"
