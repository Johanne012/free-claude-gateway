from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator

import httpx
from loguru import logger

from free_claude_gateway.core.models import AnthropicRequest
from free_claude_gateway.providers.base import BaseProvider


def _anthropic_to_openai_messages(request: AnthropicRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    if request.system:
        system_content = request.system
        if isinstance(system_content, list):
            texts = []
            for block in system_content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif isinstance(block, str):
                    texts.append(block)
            system_content = "\n".join(texts)
        messages.append({"role": "system", "content": system_content})

    for msg in request.messages:
        content = msg.content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        parts.append(json.dumps(block))
                else:
                    parts.append(str(block))
            content = "\n".join(parts)
        messages.append({"role": msg.role, "content": content})

    return messages


def _openai_to_anthropic_response(data: dict[str, Any], model: str) -> dict[str, Any]:
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content") or ""
    finish_reason = choice.get("finish_reason") or "end_turn"

    stop_reason = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
        "content_filter": "end_turn",
    }.get(finish_reason, "end_turn")

    return {
        "id": data.get("id") or f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": content}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": data.get("usage", {}).get("prompt_tokens", 0),
            "output_tokens": data.get("usage", {}).get("completion_tokens", 0),
        },
    }


class OpenAICompatibleProvider(BaseProvider):
    """Generic OpenAI-compatible chat completions provider."""

    def __init__(
        self,
        name: str,
        api_key: str | None,
        base_url: str,
        default_headers: dict[str, str] | None = None,
    ):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name
        self.default_headers = default_headers or {}

    def is_available(self) -> bool:
        if self.name in ("ollama", "lmstudio"):
            return True
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            **self.default_headers,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat(self, request: AnthropicRequest, model: str) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": _anthropic_to_openai_messages(request),
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = request.tools

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            if resp.status_code >= 400:
                logger.error(f"[{self.name}] error {resp.status_code}: {resp.text[:500]}")
                resp.raise_for_status()
            data = resp.json()
            return _openai_to_anthropic_response(data, model)

    async def stream(self, request: AnthropicRequest, model: str) -> AsyncIterator[str]:
        """Stream with best-effort usage in final message_delta for cost tracking."""
        messages = _anthropic_to_openai_messages(request)
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        msg_id = f"msg_{uuid.uuid4().hex[:24]}"
        approx_input = max(1, len(json.dumps(messages)) // 4)
        output_chars = 0
        input_tokens = 0
        output_tokens = 0

        yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'model': model, 'content': [], 'stop_reason': None}})}\n\n"
        yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

        async with httpx.AsyncClient(timeout=120.0) as client:
            # First try with stream_options; some providers reject it
            resp_ctx = client.stream("POST", url, json=payload, headers=self._headers())
            async with resp_ctx as resp:
                if resp.status_code == 400:
                    payload.pop("stream_options", None)
                    async with client.stream("POST", url, json=payload, headers=self._headers()) as resp2:
                        if resp2.status_code >= 400:
                            err = await resp2.aread()
                            logger.error(f"[{self.name}] stream error {resp2.status_code}: {err[:500]}")
                            resp2.raise_for_status()
                        async for line in resp2.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                usage = chunk.get("usage") or {}
                                if usage:
                                    input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or input_tokens
                                    output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or output_tokens
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    output_chars += len(content)
                                    event = {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": content}}
                                    yield f"event: content_block_delta\ndata: {json.dumps(event)}\n\n"
                            except json.JSONDecodeError:
                                continue
                else:
                    if resp.status_code >= 400:
                        err = await resp.aread()
                        logger.error(f"[{self.name}] stream error {resp.status_code}: {err[:500]}")
                        resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            usage = chunk.get("usage") or {}
                            if usage:
                                input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or input_tokens
                                output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or output_tokens
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                output_chars += len(content)
                                event = {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": content}}
                                yield f"event: content_block_delta\ndata: {json.dumps(event)}\n\n"
                        except json.JSONDecodeError:
                            continue

        if not input_tokens:
            input_tokens = approx_input
        if not output_tokens:
            output_tokens = max(1, output_chars // 4) if output_chars else 0

        yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
        usage_payload = {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        }
        yield f"event: message_delta\ndata: {json.dumps(usage_payload)}\n\n"
        yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"
