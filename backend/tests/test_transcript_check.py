from __future__ import annotations

import pytest

from app.config.models_config import TranscriptQualityRules
from app.pipeline.transcript_check import find_transcript_problem
from app.providers.base import Transcription

RULES = TranscriptQualityRules(
    min_words=2,
    max_seconds=180,
    min_avg_logprob=-1.0,
    max_no_speech_prob=0.6,
    known_hallucinations=["thanks for watching", "you"],
)


def _clear(text: str) -> Transcription:
    return Transcription(text=text, avg_logprob=-0.3, no_speech_prob=0.05)


def test_clear_note_passes():
    assert find_transcript_problem(_clear("Ravi owes me 500 rupees."), RULES) is None


def test_runtime_without_confidence_passes_on_text_alone():
    assert find_transcript_problem(Transcription(text="Call mom tonight"), RULES) is None


@pytest.mark.parametrize("text", ["", "   ", "..."])
def test_empty_transcript_is_rejected(text):
    assert "didn't catch any speech" in find_transcript_problem(_clear(text), RULES)


@pytest.mark.parametrize("text", ["Thanks for watching!", "  you. ", "Hello"])
def test_hallucinations_and_single_words_are_rejected(text):
    assert "too short or unclear" in find_transcript_problem(_clear(text), RULES)


def test_hallucination_phrase_inside_a_real_note_is_kept():
    assert find_transcript_problem(_clear("Thanks for watching the kids, I owe you"), RULES) is None


def test_mostly_noise_is_rejected():
    noisy = Transcription(text="the the and so", avg_logprob=-0.4, no_speech_prob=0.8)
    assert "background noise" in find_transcript_problem(noisy, RULES)


def test_low_confidence_is_rejected():
    mumbled = Transcription(text="raw vee owes mere", avg_logprob=-1.4, no_speech_prob=0.1)
    assert "couldn't make out" in find_transcript_problem(mumbled, RULES)


def test_too_long_recording_is_rejected():
    long = Transcription(
        text="a long note", avg_logprob=-0.2, no_speech_prob=0.0, duration_seconds=240
    )
    assert "longer than 3 minutes" in find_transcript_problem(long, RULES)
