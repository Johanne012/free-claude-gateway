from __future__ import annotations

import itertools
import random
from typing import Literal

from loguru import logger

BalanceStrategy = Literal["priority", "round_robin", "random", "weighted"]


class ProviderBalancer:
    """
    Selects the next provider/model according to the configured strategy.

    Strategies:
      - priority   : try in the given order (classic fallback)
      - round_robin: cycle through available candidates evenly
      - random     : pick randomly among available candidates
      - weighted   : pick according to weights (format: provider/model:weight)
    """

    def __init__(self, strategy: BalanceStrategy = "priority"):
        self.strategy = strategy
        self._rr_counter = itertools.count()
        self._lock_counter = 0

    def select(
        self,
        candidates: list[str],
        available: set[str] | None = None,
        weights: dict[str, int] | None = None,
    ) -> list[str]:
        """
        Return an ordered list of candidates to try.
        The first one is the preferred choice; the rest are fallbacks.
        """
        if not candidates:
            return []

        if available is not None:
            filtered = [c for c in candidates if c in available or c.split("/")[0] in available]
            if filtered:
                candidates = filtered

        if self.strategy == "priority":
            return candidates

        if self.strategy == "round_robin":
            if not candidates:
                return []
            start = next(self._rr_counter) % len(candidates)
            return candidates[start:] + candidates[:start]

        if self.strategy == "random":
            shuffled = candidates[:]
            random.shuffle(shuffled)
            return shuffled

        if self.strategy == "weighted":
            return self._weighted_order(candidates, weights or {})

        logger.warning(f"Unknown strategy '{self.strategy}', falling back to priority")
        return candidates

    def _weighted_order(self, candidates: list[str], weights: dict[str, int]) -> list[str]:
        remaining = candidates[:]
        result: list[str] = []

        while remaining:
            w_list = [max(1, weights.get(c, 1)) for c in remaining]
            total = sum(w_list)
            r = random.uniform(0, total)
            upto = 0.0
            chosen_idx = 0
            for i, w in enumerate(w_list):
                upto += w
                if upto >= r:
                    chosen_idx = i
                    break
            result.append(remaining.pop(chosen_idx))

        return result


def parse_weighted_chain(chain: str) -> tuple[list[str], dict[str, int]]:
    """
    Parse a weighted fallback chain.

    Examples:
      "openrouter/deepseek/deepseek-chat:free:3,deepseek/deepseek-chat:2,ollama/llama3.2:1"
    """
    candidates: list[str] = []
    weights: dict[str, int] = {}

    for part in chain.split(","):
        part = part.strip()
        if not part:
            continue

        segments = part.rsplit(":", 1)
        if len(segments) == 2 and segments[1].isdigit():
            ref, weight_str = segments
            weight = int(weight_str)
            candidates.append(ref)
            weights[ref] = weight
        else:
            candidates.append(part)
            weights[part] = 1

    return candidates, weights
