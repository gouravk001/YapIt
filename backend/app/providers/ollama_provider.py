from __future__ import annotations

import json
import logging

import ollama  # type: ignore[import-untyped]

from app.config.models_config import ModelEntry
from app.providers.base import LLM

logger = logging.getLogger(__name__)


class OllamaProvider(LLM):
    """LLM backed by the Ollama Python client."""

    def __init__(self, entry: ModelEntry) -> None:
        self._model_name = entry.model_name
        self._options: dict = {}
        if entry.temperature is not None:
            self._options["temperature"] = entry.temperature
        if entry.top_p is not None:
            self._options["top_p"] = entry.top_p
        if entry.num_ctx is not None:
            self._options["num_ctx"] = entry.num_ctx

    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        kwargs: dict = {
            "model": self._model_name,
            "prompt": prompt,
            "options": self._options,
        }
        if json_schema is not None:
            kwargs["format"] = json_schema

        response = ollama.generate(**kwargs)
        raw: str = response["response"]

        if json_schema is not None:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(
                    "Ollama returned non-JSON despite schema request; raw: %s", raw[:200]
                )
                return raw

        return raw
