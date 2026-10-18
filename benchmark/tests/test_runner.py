from __future__ import annotations

import asyncio

from app.config.loader import load_checks, load_types
from app.providers.base import LLM, Transcriber
from app.services.pipeline_service import PipelineService
from harness.runner import StageTimer, run_case
from harness.scoring import NOT_A_NOTE, Case

CAPTURED_AT = "2026-10-17T10:00:00+05:30"
TZ = "Asia/Kolkata"
PAYMENT = {
    "person": "Ravi",
    "direction": "they_owe_me",
    "amount": "₹500",
    "due_date": "",
    "note": "",
}


class NoTranscriber(Transcriber):
    def transcribe(self, audio_path):
        raise AssertionError("the benchmark only runs the text pipeline")


class ScriptedLLM(LLM):
    def __init__(self, kind="note", fail=False):
        self.kind = kind
        self.fail = fail

    def generate(self, prompt, json_schema=None):
        if self.fail:
            raise ConnectionError("ollama down")
        props = (json_schema or {}).get("properties", {})
        if "kind" in props:
            return {"kind": self.kind, "type_name": "payment"}
        if "verdict" in props:
            return {"verdict": "ordinary", "reason": ""}
        if "summary" in props:
            return {"restatement": "x", **PAYMENT, "summary": "Ravi owes ₹500"}
        return PAYMENT


def _pipeline(llm):
    return PipelineService(NoTranscriber(), llm, load_types(), plausibility_rules=load_checks())


def _case(expected_type="payment"):
    return Case("c1", "direction", "Ravi owes me 500", expected_type, {})


def test_note_outcome_has_fields_and_every_stage_timed():
    outcome = asyncio.run(run_case(_pipeline(ScriptedLLM()), _case(), CAPTURED_AT, TZ))
    assert outcome.error is None
    assert outcome.actual_type == "payment"
    assert outcome.fields["amount"] == {"amount": 500.0, "currency": "INR"}
    assert list(outcome.stage_s) == ["classify", "extract", "refine", "check"]
    assert outcome.latency_s >= sum(outcome.stage_s.values()) - 1e-6


def test_rejected_input_is_recorded_as_not_a_note():
    llm = ScriptedLLM(kind="question_or_command")
    outcome = asyncio.run(run_case(_pipeline(llm), _case(NOT_A_NOTE), CAPTURED_AT, TZ))
    assert outcome.actual_type == NOT_A_NOTE
    assert outcome.error is None


def test_failures_are_recorded_not_raised():
    outcome = asyncio.run(run_case(_pipeline(ScriptedLLM(fail=True)), _case(), CAPTURED_AT, TZ))
    assert outcome.actual_type is None
    assert outcome.error.startswith("ConnectionError")


def test_stage_timer_splits_time_between_stage_starts():
    timer = StageTimer()
    timer._starts = [("classify", 0.0), ("extract", 1.0), ("refine", 3.0)]
    assert timer.durations(finished_at=6.0) == {"classify": 1.0, "extract": 2.0, "refine": 3.0}
