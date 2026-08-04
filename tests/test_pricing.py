"""Tests for cost calculation."""

from free_claude_gateway.core.pricing import calc_cost_usd, get_price


def test_free_model_zero_cost():
    cost = calc_cost_usd("deepseek/deepseek-chat:free", 1000, 500)
    assert cost == 0.0


def test_known_model_cost():
    cost = calc_cost_usd("deepseek-chat", 1_000_000, 1_000_000)
    assert cost == 0.14 + 0.28


def test_unknown_model_uses_default():
    price = get_price("some-unknown-model-xyz")
    assert price.input_per_million == 0.50
    assert price.output_per_million == 1.50


def test_zero_tokens():
    assert calc_cost_usd("deepseek-chat", 0, 0) == 0.0
