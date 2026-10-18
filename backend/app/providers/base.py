from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Transcription:
    """Transcript text plus the runtime's confidence signals, when it reports them."""

    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None


class Transcriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> Transcription:
        """Transcribe the audio file at *audio_path*."""
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
