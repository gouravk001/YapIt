from __future__ import annotations

import re

from app.config.models_config import TranscriptQualityRules
from app.providers.base import Transcription


def _normalise(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s']", " ", text.lower()).split())


def find_transcript_problem(
    transcription: Transcription, rules: TranscriptQualityRules
) -> str | None:
    """Return a user-facing reason the transcript is unusable, or None if it looks fine."""
    if (
        transcription.duration_seconds is not None
        and transcription.duration_seconds > rules.max_seconds
    ):
        minutes = rules.max_seconds / 60
        return f"That recording is longer than {minutes:g} minutes. Please keep a note shorter."

    text = _normalise(transcription.text)
    if not text:
        return "I didn't catch any speech. Please try recording again."

    hallucinations = {_normalise(phrase) for phrase in rules.known_hallucinations}
    if text in hallucinations or len(text.split()) < rules.min_words:
        return "That was too short or unclear to make a note from. Please try again."

    if (
        transcription.no_speech_prob is not None
        and transcription.no_speech_prob > rules.max_no_speech_prob
    ):
        return "It sounded mostly like background noise. Please try again a little closer."

    if transcription.avg_logprob is not None and transcription.avg_logprob < rules.min_avg_logprob:
        return "I couldn't make out what you said clearly. Please try again."

    return None
