from __future__ import annotations

import pytest

from app.config.loader import load_types
from app.config.models_config import TranscriptQualityRules
from app.errors import NotANoteError, UnclearAudioError
from app.providers.base import LLM, Transcriber, Transcription
from app.services.pipeline_service import PipelineService

CAPTURED_AT = "2026-10-17T10:00:00+05:30"
TZ = "Asia/Kolkata"
RULES = TranscriptQualityRules(
    min_words=2,
    max_seconds=180,
    min_avg_logprob=-1.0,
    max_no_speech_prob=0.6,
    known_hallucinations=["you"],
)


class FixedTranscriber(Transcriber):
    def __init__(self, transcription: Transcription) -> None:
        self.transcription = transcription

    def transcribe(self, audio_path: str) -> Transcription:
        return self.transcription


class StepLLM(LLM):
    """Answers each pipeline step from a per-step queue, keyed by the schema it receives."""

    def __init__(self, classify=(), extract=(), refine=(), plausibility=()):
        self.queues = {
            "classify": list(classify),
            "extract": list(extract),
            "refine": list(refine),
            "plausibility": list(plausibility),
        }
        self.calls: list[str] = []

    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        properties = (json_schema or {}).get("properties", {})
        if "kind" in properties:
            step = "classify"
        elif "verdict" in properties:
            step = "plausibility"
        elif "summary" in properties:
            step = "refine"
        else:
            step = "extract"
        self.calls.append(step)
        return self.queues[step].pop(0)


def _service(llm: LLM, transcription: Transcription | None = None) -> PipelineService:
    transcriber = FixedTranscriber(transcription or Transcription(text="unused"))
    return PipelineService(transcriber, llm, load_types(), RULES)


GENERAL_FIELDS = {"content": "Buy groceries"}
GENERAL_REFINED = {"content": "Buy groceries", "summary": "Buy groceries"}


async def test_not_a_note_is_rejected_with_transcript():
    llm = StepLLM(classify=[{"kind": "question_or_command", "type_name": "general"}])
    with pytest.raises(NotANoteError) as caught:
        await _service(llm).process_text("What's the weather today?", CAPTURED_AT, TZ)
    assert caught.value.extra == {"transcript": "What's the weather today?"}
    assert llm.calls == ["classify"]


async def test_malformed_classification_does_not_discard_the_note():
    llm = StepLLM(
        classify=["oops", "still oops"], extract=[GENERAL_FIELDS], refine=[GENERAL_REFINED]
    )
    draft = await _service(llm).process_text("buy groceries", CAPTURED_AT, TZ)
    assert draft.type_name == "general"
    assert llm.calls == ["classify", "classify", "extract", "refine"]


async def test_unclear_audio_is_rejected_before_any_llm_call():
    llm = StepLLM()
    mumble = Transcription(text="raw vee", avg_logprob=-1.6, no_speech_prob=0.1)
    with pytest.raises(UnclearAudioError) as caught:
        await _service(llm, mumble).process_audio("x.webm", CAPTURED_AT, TZ)
    assert caught.value.extra == {"transcript": "raw vee"}
    assert llm.calls == []


async def test_refine_corrects_the_extracted_draft():
    llm = StepLLM(
        classify=[{"kind": "note", "type_name": "payment"}],
        extract=[{"person": "ram", "direction": "they_owe_me", "amount": "200 rupees"}],
        refine=[
            {
                "person": "Ram",
                "direction": "i_owe_them",
                "amount": "₹200",
                "due_date": "tomorrow",
                "note": "",
                "summary": "Pay Ram ₹200 tomorrow",
            }
        ],
    )
    draft = await _service(llm).process_text(
        "I have to give Ram 200 rupees tomorrow", CAPTURED_AT, TZ
    )

    assert draft.fields["direction"] == "i_owe_them"
    assert draft.fields["due_date"] == {"spoken": "tomorrow", "resolved": "2026-10-18"}
    assert draft.summary == "Pay Ram ₹200 tomorrow"
    assert draft.missing_fields == []


async def test_failed_refine_keeps_extraction_and_summarises_transcript():
    llm = StepLLM(
        classify=[{"kind": "note", "type_name": "general"}],
        extract=[GENERAL_FIELDS],
        refine=["bad", "bad"],
    )
    draft = await _service(llm).process_text("buy groceries", CAPTURED_AT, TZ)
    assert draft.fields == {"content": "Buy groceries"}
    assert draft.summary == "buy groceries"


async def test_retype_skips_the_note_gate():
    llm = StepLLM(extract=[GENERAL_FIELDS], refine=[GENERAL_REFINED])
    draft = await _service(llm).retype("hello there", "general", CAPTURED_AT, TZ)
    assert draft.type_name == "general"
    assert llm.calls == ["extract", "refine"]


def _event_llm(date_words: str, concern: str) -> StepLLM:
    fields = {"title": "Wedding", "date": date_words, "time": "", "people": []}
    verdict = {"verdict": "unlikely" if concern else "ordinary", "reason": concern}
    return StepLLM(
        classify=[{"kind": "note", "type_name": "event"}],
        extract=[fields],
        refine=[{"restatement": "x", **fields, "summary": "Wedding"}],
        plausibility=[verdict],
    )


def _checked_service(llm: LLM) -> PipelineService:
    from app.config.loader import load_checks

    return PipelineService(
        FixedTranscriber(Transcription(text="unused")), llm, load_types(), RULES, load_checks()
    )


async def test_rule_warning_wins_over_model_concern():
    llm = _event_llm("in 40 years", "A wedding 40 years away seems unlikely")
    draft = await _checked_service(llm).process_text("wedding in 40 years", CAPTURED_AT, TZ)
    assert [(w.field, w.message) for w in draft.warnings] == [
        ("date", "Date is about 40 years away (Sun 17 Oct 2066).")
    ]
    assert "plausibility" not in llm.calls


async def test_model_concern_is_used_when_rules_find_nothing():
    llm = _event_llm("tomorrow", "A 25 PM start time isn't a real time")
    draft = await _checked_service(llm).process_text("wedding tomorrow 25 pm", CAPTURED_AT, TZ)
    assert [(w.field, w.message) for w in draft.warnings] == [
        (None, "A 25 PM start time isn't a real time")
    ]


async def test_ordinary_note_has_no_warnings():
    llm = _event_llm("tomorrow", "")
    draft = await _checked_service(llm).process_text("wedding tomorrow", CAPTURED_AT, TZ)
    assert draft.warnings == []
    assert llm.calls == ["classify", "extract", "refine", "plausibility"]


async def test_unusable_plausibility_answer_counts_as_ordinary():
    llm = _event_llm("tomorrow", "")
    llm.queues["plausibility"] = ["bad", "bad"]
    draft = await _checked_service(llm).process_text("wedding tomorrow", CAPTURED_AT, TZ)
    assert draft.warnings == []
