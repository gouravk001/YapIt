from __future__ import annotations

from abc import ABC, abstractmethod


class Transcriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        """Transcribe the audio file at *audio_path* and return the full text."""
        ...


class LLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        """
        Generate a completion for *prompt*.

        When *json_schema* is provided the implementation should request
        structured JSON output and return a parsed ``dict``.
        Without a schema it returns the raw response string.
        """
        ...
