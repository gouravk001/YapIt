"""The benchmark's own Ollama client, so the app's provider needs no benchmark-only options."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import ollama  # type: ignore[import-untyped]

from app.providers.base import LLM

# keep_alive=0 asks Ollama to unload the model right after the call.
UNLOAD_NOW = 0
UNLOAD_POLL_SECONDS = 0.5


class OllamaClient(LLM):
    def __init__(self, tag: str, options: dict[str, Any], think: bool | None = None) -> None:
        self.tag = tag
        self._options = options
        self._think = think

    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        kwargs: dict[str, Any] = {"model": self.tag, "prompt": prompt, "options": self._options}
        if json_schema is not None:
            kwargs["format"] = json_schema
        if self._think is not None:
            kwargs["think"] = self._think
        raw: str = ollama.generate(**kwargs)["response"]
        if json_schema is None:
            return raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def unload(self) -> None:
        ollama.generate(model=self.tag, keep_alive=UNLOAD_NOW)


def unload_all_models() -> list[str]:
    """Unload every model Ollama has in memory, so VRAM readings start from a clean slate."""
    loaded = [m.model for m in ollama.ps().models]
    for tag in loaded:
        ollama.generate(model=tag, keep_alive=UNLOAD_NOW)
    return loaded


def ollama_reachable() -> bool:
    try:
        ollama.list()
    except ConnectionError:
        return False
    return True


def is_downloaded(tag: str) -> bool:
    available = {m.model for m in ollama.list().models}
    return tag in available or f"{tag}:latest" in available


def ensure_downloaded(tag: str, on_progress: Callable[[int, int], None]) -> bool:
    """Pull the model unless Ollama already has it. Returns True if it had to download."""
    if is_downloaded(tag):
        return False
    for event in ollama.pull(tag, stream=True):
        if event.total:
            on_progress(event.completed or 0, event.total)
    return True


def model_capabilities(tag: str) -> list[str]:
    return list(ollama.show(tag).capabilities or [])


def wait_until_unloaded(timeout_s: float) -> None:
    """Block until Ollama reports no models in memory. Unloading happens in the background, so
    reading VRAM straight after asking for it would still count the previous model."""
    deadline = time.monotonic() + timeout_s
    while True:
        loaded = [m.model for m in ollama.ps().models]
        if not loaded:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Models still loaded after {timeout_s}s: {', '.join(loaded)}")
        time.sleep(UNLOAD_POLL_SECONDS)
