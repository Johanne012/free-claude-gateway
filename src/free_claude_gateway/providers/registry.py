from __future__ import annotations

from typing import Dict

from free_claude_gateway.config import Settings, get_settings
from free_claude_gateway.providers.base import BaseProvider
from free_claude_gateway.providers.openai_compatible import OpenAICompatibleProvider


def build_providers(settings: Settings | None = None) -> Dict[str, BaseProvider]:
    settings = settings or get_settings()
    providers: Dict[str, BaseProvider] = {}

    providers["openrouter"] = OpenAICompatibleProvider(
        name="openrouter",
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/Johanne012/free-claude-gateway",
            "X-Title": "Free Claude Gateway",
        },
    )

    providers["deepseek"] = OpenAICompatibleProvider(
        name="deepseek",
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )

    providers["kimi"] = OpenAICompatibleProvider(
        name="kimi",
        api_key=settings.kimi_api_key,
        base_url="https://api.moonshot.ai/v1",
    )

    providers["groq"] = OpenAICompatibleProvider(
        name="groq",
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    providers["nvidia_nim"] = OpenAICompatibleProvider(
        name="nvidia_nim",
        api_key=settings.nvidia_nim_api_key,
        base_url="https://integrate.api.nvidia.com/v1",
    )

    providers["ollama"] = OpenAICompatibleProvider(
        name="ollama",
        api_key=None,
        base_url=f"{settings.ollama_base_url.rstrip('/')}/v1",
    )

    providers["lmstudio"] = OpenAICompatibleProvider(
        name="lmstudio",
        api_key=None,
        base_url=f"{settings.lmstudio_base_url.rstrip('/')}/v1",
    )

    return providers


def parse_model_ref(ref: str) -> tuple[str, str]:
    """Parse 'provider/model-id' into (provider, model_id)."""
    if "/" not in ref:
        return "openrouter", ref
    provider, model = ref.split("/", 1)
    return provider.lower(), model
