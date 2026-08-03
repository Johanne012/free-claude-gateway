from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class ProviderStats:
    requests: int = 0
    successes: int = 0
    failures: int = 0
    rate_limits: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    last_used: float | None = None
    last_error: str | None = None
    cooldown_until: float = 0.0


class StatsCollector:
    """Simple in-memory usage tracker (resets on restart)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.started_at = time.time()
        self.total_requests = 0
        self.providers: dict[str, ProviderStats] = defaultdict(ProviderStats)

    def record_success(
        self,
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        with self._lock:
            self.total_requests += 1
            s = self.providers[provider]
            s.requests += 1
            s.successes += 1
            s.total_input_tokens += input_tokens
            s.total_output_tokens += output_tokens
            s.last_used = time.time()
            s.last_error = None

    def record_failure(self, provider: str, error: str, is_rate_limit: bool = False) -> None:
        with self._lock:
            self.total_requests += 1
            s = self.providers[provider]
            s.requests += 1
            s.failures += 1
            s.last_used = time.time()
            s.last_error = error[:200]
            if is_rate_limit:
                s.rate_limits += 1
                s.cooldown_until = time.time() + 60  # 60s cooldown

    def is_in_cooldown(self, provider: str) -> bool:
        with self._lock:
            s = self.providers.get(provider)
            if not s:
                return False
            return time.time() < s.cooldown_until

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            uptime = int(time.time() - self.started_at)
            providers_data = {}
            for name, s in self.providers.items():
                providers_data[name] = {
                    "requests": s.requests,
                    "successes": s.successes,
                    "failures": s.failures,
                    "rate_limits": s.rate_limits,
                    "input_tokens": s.total_input_tokens,
                    "output_tokens": s.total_output_tokens,
                    "last_used": s.last_used,
                    "last_error": s.last_error,
                    "in_cooldown": time.time() < s.cooldown_until,
                    "cooldown_remaining_sec": max(0, int(s.cooldown_until - time.time())),
                }
            return {
                "uptime_seconds": uptime,
                "total_requests": self.total_requests,
                "providers": providers_data,
            }


stats = StatsCollector()
