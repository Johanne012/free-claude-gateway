from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Routing
    model_opus: str = "openrouter/deepseek/deepseek-chat:free"
    model_sonnet: str = "openrouter/deepseek/deepseek-chat:free"
    model_haiku: str = "ollama/llama3.2"
    model_fallback: str = "nvidia_nim/nvidia/nemotron"
    fallback_chain: str = "openrouter/deepseek/deepseek-chat:free,deepseek/deepseek-chat,ollama/llama3.2"

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
        return [m.strip() for m in self.fallback_chain.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
