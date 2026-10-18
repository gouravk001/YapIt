from __future__ import annotations

import json
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from app.config.loader import load_checks, load_types
from app.main import app
from app.providers.base import LLM, Transcriber, Transcription
from app.services.pipeline_service import PipelineService

CAPTURED = {"captured_at": "2026-10-17T10:00:00+05:30", "timezone": "Asia/Kolkata"}
PAYMENT = {
    "person": "Ravi",
    "direction": "they_owe_me",
    "amount": "₹500",
    "due_date": "",
    "note": "",
}


class ScriptLLM(LLM):
    def __init__(self, kind: str = "note", fail: bool = False) -> None:
        self.kind = kind
        self.fail = fail

    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        if self.fail:
            raise RuntimeError("secret internal detail")
        properties = (json_schema or {}).get("properties", {})
        if "kind" in properties:
            return {"kind": self.kind, "type_name": "payment"}
        if "verdict" in properties:
            return {"verdict": "ordinary", "reason": ""}
        if "summary" in properties:
            return {"restatement": "x", **PAYMENT, "summary": "Ravi owes ₹500"}
        return PAYMENT


class FixedTranscriber(Transcriber):
    def transcribe(self, audio_path: str) -> Transcription:
        return Transcription(text="Ravi owes me 500 rupees", avg_logprob=-0.2, no_speech_prob=0.0)


def _use(llm: LLM) -> None:
    app.state.pipeline_service = PipelineService(
        FixedTranscriber(), llm, load_types(), plausibility_rules=load_checks()
    )


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _lines(res) -> list[dict]:
    assert res.headers["content-type"].startswith("application/x-ndjson")
    return [json.loads(line) for line in res.text.splitlines()]


async def test_text_stream_reports_each_stage_then_the_draft(client):
    _use(ScriptLLM())
    res = await client.post(
        "/notes/process-text/stream", json={"transcript": "Ravi owes me 500", **CAPTURED}
    )
    lines = _lines(res)
    assert [line["stage"] for line in lines[:-1]] == ["classify", "extract", "refine", "check"]
    assert lines[-1]["draft"]["summary"] == "Ravi owes ₹500"
    assert lines[-1]["draft"]["fields"]["amount"] == {"amount": 500.0, "currency": "INR"}


async def test_rejection_arrives_as_an_error_line_with_the_transcript(client):
    _use(ScriptLLM(kind="question_or_command"))
    res = await client.post(
        "/notes/process-text/stream", json={"transcript": "play music", **CAPTURED}
    )
    lines = _lines(res)
    assert lines[0] == {"stage": "classify"}
    assert lines[-1]["error"] == "NotANote"
    assert lines[-1]["transcript"] == "play music"


async def test_unexpected_failure_does_not_leak_details(client):
    _use(ScriptLLM(fail=True))
    res = await client.post("/notes/process-text/stream", json={"transcript": "x y", **CAPTURED})
    assert _lines(res)[-1] == {
        "error": "InternalServerError",
        "detail": "An unexpected error occurred.",
    }


async def test_audio_stream_starts_with_transcribe_and_removes_the_upload(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    _use(ScriptLLM())
    res = await client.post(
        "/notes/process/stream",
        files={"audio": ("rec.webm", b"fake audio", "audio/webm")},
        data=CAPTURED,
    )
    lines = _lines(res)
    assert lines[0] == {"stage": "transcribe"}
    assert "draft" in lines[-1]
    assert list(tmp_path.iterdir()) == []
