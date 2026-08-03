from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from free_claude_gateway.core.balancer import parse_weighted_chain

BalanceStrategy = Literal["priority", "round_robin", "random", "weighted"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "127.0.0.1"
    port: int = 8082
    auth_token: Optional[str] = "fcc"

    # Routing – primary models per Claude tier
    model_opus: str = "openrouter/deepseek/deepseek-chat:free"
    model_sonnet: str = "openrouter/deepseek/deepseek-chat:free"
    model_haiku: str = "ollama/llama3.2"
    model_fallback: str = "nvidia_nim/nvidia/nemotron"

    # Balancing strategy: priority | round_robin | random | weighted
    balance_strategy: BalanceStrategy = "priority"

    # Fallback / balance chain
    # For weighted: append :weight  e.g. openrouter/xxx:3,deepseek/yyy:2
    fallback_chain: str = (
        "openrouter/deepseek/deepseek-chat:free,"
        "deepseek/deepseek-chat,"
        "kimi/kimi-k2.5,"
        "ollama/llama3.2"
    )

    # Provider keys
    nvidia_nim_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    kimi_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None

    # Local
    ollama_base_url: str = "http://localhost:11434"
    lmstudio_base_url: str = "http://localhost:1234"

    def get_fallback_list(self) -> list[str]:
        candidates, _ = parse_weighted_chain(self.fallback_chain)
        return candidates

    def get_weights(self) -> dict[str, int]:
        _, weights = parse_weighted_chain(self.fallback_chain)
        return weights


@lru_cache
def get_settings() -> Settings:
    return Settings()
