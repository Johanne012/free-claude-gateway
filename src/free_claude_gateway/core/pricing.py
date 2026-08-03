"""
Model pricing table (USD per 1M tokens).
Used for real cost tracking and budget enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float


PRICING: dict[str, ModelPrice] = {
    "deepseek-chat": ModelPrice(0.14, 0.28),
    "deepseek-coder": ModelPrice(0.14, 0.28),
    "deepseek-reasoner": ModelPrice(0.55, 2.19),
    "kimi-k2.5": ModelPrice(0.30, 0.30),
    "moonshot-v1-8k": ModelPrice(0.30, 0.30),
    "moonshot-v1-32k": ModelPrice(0.30, 0.30),
    "deepseek/deepseek-chat": ModelPrice(0.14, 0.28),
    "deepseek/deepseek-chat:free": ModelPrice(0.0, 0.0),
    "qwen/qwen3-coder": ModelPrice(0.20, 0.20),
    "google/gemini-2.0-flash-exp:free": ModelPrice(0.0, 0.0),
    "meta/llama-3.1-70b-instruct": ModelPrice(0.0, 0.0),
    "meta/llama-3.3-70b-instruct": ModelPrice(0.0, 0.0),
    "mistralai/mistral-large": ModelPrice(0.0, 0.0),
    "llama-3.3-70b-versatile": ModelPrice(0.59, 0.79),
    "llama-3.1-8b-instant": ModelPrice(0.05, 0.08),
    "mixtral-8x7b-32768": ModelPrice(0.24, 0.24),
    "llama3.2": ModelPrice(0.0, 0.0),
    "llama3.1": ModelPrice(0.0, 0.0),
    "qwen2.5-coder": ModelPrice(0.0, 0.0),
    "codellama": ModelPrice(0.0, 0.0),
}

DEFAULT_PRICE = ModelPrice(0.50, 1.50)


def get_price(model: str) -> ModelPrice:
    if not model:
        return DEFAULT_PRICE
    lower = model.lower().strip()
    if lower in PRICING:
        return PRICING[lower]
    if "/" in lower:
        short = lower.split("/")[-1]
        if short in PRICING:
            return PRICING[short]
        if ":" in short:
            base = short.split(":")[0]
            if base in PRICING:
                return PRICING[base]
    for key, price in PRICING.items():
        if key in lower or lower in key:
            return price
    return DEFAULT_PRICE


def calc_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = get_price(model)
    cost = (input_tokens / 1_000_000) * price.input_per_million
    cost += (output_tokens / 1_000_000) * price.output_per_million
    return round(cost, 8)
