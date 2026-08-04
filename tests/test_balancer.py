"""Basic tests for the provider balancer."""

from free_claude_gateway.core.balancer import ProviderBalancer, parse_weighted_chain


def test_priority_order():
    b = ProviderBalancer(strategy="priority")
    result = b.select(["a", "b", "c"])
    assert result == ["a", "b", "c"]


def test_round_robin_rotates():
    b = ProviderBalancer(strategy="round_robin")
    first = b.select(["a", "b", "c"])
    second = b.select(["a", "b", "c"])
    assert first != second or len(set(first)) == 3
    assert set(first) == {"a", "b", "c"}


def test_random_returns_all():
    b = ProviderBalancer(strategy="random")
    result = b.select(["x", "y", "z"])
    assert set(result) == {"x", "y", "z"}


def test_weighted_prefers_higher_weight():
    b = ProviderBalancer(strategy="weighted")
    weights = {"a": 10, "b": 1, "c": 1}
    results = [b.select(["a", "b", "c"], weights=weights)[0] for _ in range(50)]
    assert results.count("a") > results.count("b")


def test_parse_weighted_chain():
    candidates, weights = parse_weighted_chain(
        "openrouter/deepseek/deepseek-chat:free:3,deepseek/deepseek-chat:2,ollama/llama3.2"
    )
    assert candidates[0] == "openrouter/deepseek/deepseek-chat:free"
    assert weights["openrouter/deepseek/deepseek-chat:free"] == 3
    assert weights["deepseek/deepseek-chat"] == 2
    assert weights["ollama/llama3.2"] == 1


def test_empty_candidates():
    b = ProviderBalancer()
    assert b.select([]) == []
