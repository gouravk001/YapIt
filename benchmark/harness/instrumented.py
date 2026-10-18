"""Wraps an LLM to count calls, malformed replies and time spent per call."""

from __future__ import annotations

import time

from app.providers.base import LLM


class InstrumentedLLM(LLM):
    def __init__(self, inner: LLM) -> None:
        self._inner = inner
        self.calls = 0
        self.malformed = 0
        self.call_seconds: list[float] = []

    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        started = time.perf_counter()
        result = self._inner.generate(prompt, json_schema)
        self.call_seconds.append(time.perf_counter() - started)
        self.calls += 1
        if json_schema is not None and not isinstance(result, dict):
            self.malformed += 1
        return result
